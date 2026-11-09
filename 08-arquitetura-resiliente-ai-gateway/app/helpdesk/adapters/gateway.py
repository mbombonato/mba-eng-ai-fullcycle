"""Adaptador do AI Gateway: o único componente que fala com o gateway.

O gateway expõe a API Chat Completions (formato OpenAI) para todas as capacidades,
qualquer que seja o provider por trás. Retry, timeout por destino e fallback moram no
gateway (gateway/config.yaml); aqui ficam só o timeout total da chamada e a tradução das
falhas HTTP para os erros do domínio.
"""

from collections.abc import Iterator

import openai
from openai import OpenAI

from ..errors import GenerationInterrupted, ModelUnavailable, QuotaExceeded
from ..ports import TextModel

QUOTA_ERROR_TYPES = {"budget_exceeded", "throttling_error"}


class GatewayTextModel(TextModel):
    def __init__(self, base_url: str, api_key: str, max_output_tokens: int, timeout: float):
        # max_retries=0: retry é responsabilidade do gateway; repetir aqui multiplicaria as tentativas.
        self._client = OpenAI(base_url=base_url, api_key=api_key, max_retries=0, timeout=timeout)
        self._max_output_tokens = max_output_tokens

    def _request(self, capability: str, task: str, content: str, stream: bool):
        try:
            return self._client.chat.completions.create(
                model=capability,
                max_tokens=self._max_output_tokens,
                messages=[{"role": "user", "content": f"TASK: {task}\n{content}"}],
                stream=stream,
            )
        except openai.APIError as error:
            raise _translate(capability, error) from error

    def complete(self, capability: str, task: str, content: str) -> str:
        response = self._request(capability, task, content, stream=False)
        return response.choices[0].message.content

    def stream(self, capability: str, task: str, content: str) -> Iterator[str]:
        # O pedido é aberto já na primeira iteração: falha antes do primeiro trecho vira
        # ModelUnavailable/QuotaExceeded; falha depois dele vira GenerationInterrupted.
        response = self._request(capability, task, content, stream=True)
        try:
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except openai.APIError as error:
            raise GenerationInterrupted(f"A geração da capacidade {capability} foi interrompida") from error
        finally:
            response.close()


def _translate(capability: str, error: openai.APIError) -> Exception:
    if isinstance(error, openai.APITimeoutError):
        return ModelUnavailable(f"A capacidade {capability} não respondeu dentro do tempo limite")
    body = error.body if isinstance(error.body, dict) else {}
    kind = body.get("type") or (body.get("error") or {}).get("type")
    if isinstance(error, openai.RateLimitError) and kind in QUOTA_ERROR_TYPES:
        reason = "orçamento" if kind == "budget_exceeded" else "limite de requisições"
        return QuotaExceeded(f"O gateway recusou a capacidade {capability}: {reason} esgotado")
    return ModelUnavailable(f"Nenhum modelo disponível para a capacidade {capability} no momento")
