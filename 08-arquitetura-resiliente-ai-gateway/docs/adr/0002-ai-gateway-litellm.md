# 0002. Colocar o LiteLLM Proxy como AI Gateway entre a aplicação e os providers

- Status: aceita
- Data: 2026-11-09
- Nível: solução

## Contexto

Na v1, a aplicação depende de detalhes concretos e voláteis de cada provider: o SDK (`openai` e `anthropic`), o formato da API, o nome do modelo físico, a credencial e as políticas de retry/timeout padrão dos SDKs (600 s de timeout de leitura e 2 retries em ambos). Trocar o modelo de uma feature exigiu editar `app/helpdesk/config.py`, reconstruir a imagem e recriar o container (`docker compose up -d --build app`: 7,5 s com cache e um container novo; um simples `restart` não muda nada, porque o código está dentro da imagem). Credencial, custo, limite e resiliência estavam espalhados em cada feature.

Requisitos que a peça precisa entregar: nomes lógicos, credenciais fora da aplicação, troca de modelo por configuração, chaves com orçamento e limite, timeout/retry/fallback, tudo self-hosted e subindo com `docker compose up`.

## Opções consideradas

1. Manter o acesso direto aos providers e criar uma camada de abstração dentro da aplicação (um "gateway" em código).
2. LiteLLM Proxy self-hosted como serviço `gateway` no compose.
3. Escrever um gateway próprio (FastAPI) com tradução de formatos, chaves e orçamentos.
4. Gateway SaaS (excluído pelo enunciado: o avaliador precisa subir tudo localmente).

## Decisão

Opção 2: LiteLLM Proxy `ghcr.io/berriai/litellm:v1.102.1` (versão testada com o provider simulado), com a configuração versionada em `gateway/`.

- Posição: a aplicação fala só com o gateway (`http://gateway:4000/v1`, formato Chat Completions da OpenAI para todas as capacidades). O gateway é o único serviço que conhece os providers, os modelos físicos e as chaves `FAKE_*`.
- A opção 1 resolve o acoplamento do código, mas não tira a credencial nem a troca de modelo da aplicação (ainda exige deploy). A opção 3 entregaria o efeito, mas transforma tradução de formatos, streaming, chaves virtuais e contabilidade de custo em código nosso para manter. O LiteLLM já entrega tudo isso; o que é nosso fica em configuração.
- O cliente HTTP do gateway na aplicação é o SDK `openai` (formato compatível), confinado a um único componente, `adapters.gateway` (ADR 0008), com `max_retries=0`.

## Consequências

- Trocar de modelo ou de provider é editar `gateway/config.yaml` e reiniciar só o `gateway` (README, "Troca de modelo").
- Passa a existir uma peça a operar: o gateway e o banco dele (ADR 0007). Enquanto o gateway reinicia (poucos segundos), as features respondem `503` explícito.
- Limitações encontradas e como foram tratadas:
  - O LiteLLM não conhece o preço dos modelos simulados: os preços por token estão declarados em `gateway/config.yaml`, senão o custo seria zero e nenhum orçamento estouraria.
  - Chaves virtuais exigem banco e não são criadas pela configuração: um script de provisionamento roda no boot do próprio container (ADR 0007).
  - O LiteLLM repassa o erro no meio do stream como um `data: {"error": ...}`; a tradução para o evento `error` do contrato do helpdesk fica na aplicação (ADR 0004).

## Evidência

- `docker compose config` mostra `FAKE_OPENAI_KEY`/`FAKE_ANTHROPIC_KEY` só no serviço `gateway` (e no `provider-fake`).
- `grep -rE "gpt-fake|claude-fake" app/` não retorna nada.
- `/admin/calls` registra, para uma chamada da aplicação, o provider e o modelo físico escolhidos pelo gateway.
