"""Adaptador do AI Gateway: o único componente que fala com o gateway.

O gateway expõe a API Chat Completions (formato OpenAI) para todas as capacidades,
qualquer que seja o provider por trás. A aplicação manda o nome lógico da capacidade
e a chave virtual dela; provider, modelo físico e credencial ficam no gateway.
"""

from openai import OpenAI

from ..ports import TextModel


class GatewayTextModel(TextModel):
    def __init__(self, base_url: str, api_key: str, max_output_tokens: int, timeout: float):
        # max_retries=0: retry é responsabilidade do gateway; repetir aqui multiplicaria as tentativas.
        self._client = OpenAI(base_url=base_url, api_key=api_key, max_retries=0, timeout=timeout)
        self._max_output_tokens = max_output_tokens

    def complete(self, capability: str, task: str, content: str) -> str:
        response = self._client.chat.completions.create(
            model=capability,
            max_tokens=self._max_output_tokens,
            messages=[{"role": "user", "content": f"TASK: {task}\n{content}"}],
        )
        return response.choices[0].message.content
