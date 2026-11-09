# 0003. Expor capacidades lógicas por feature e mapear para modelos físicos no gateway

- Status: aceita
- Data: 2026-11-09
- Nível: solução

## Contexto

Na v1, `config.py` tem `CLASSIFICATION_MODEL = "gpt-fake-large"` e afins: a aplicação escolhe provider e modelo. Os fatos do provider simulado que pesam no mapeamento:

- `gpt-fake-large` e `claude-fake-large` são equivalentes (mesma saída para a mesma entrada). Isso torna o fallback técnico entre eles transparente.
- Os `mini` são mais rápidos e baratos e piores em pelo menos uma tarefa (medido no ADR 0005: a extração erra o número do pedido).
- A suíte de caracterização fixou as saídas dos `large`. Na `v2-decoupled` cada capacidade precisava continuar num `large`.

## Opções consideradas

1. Um nome lógico por tamanho de modelo (`large`, `small`), escolhido pela feature.
2. Um nome lógico por capacidade de negócio (o que a feature precisa), com primário, fallback e modelo fraco decididos no gateway.
3. Um nome lógico único para tudo.

## Decisão

Opção 2. A aplicação conhece quatro capacidades; o resto é configuração do gateway:

| Capacidade | Feature | Primário | Fallback técnico | Modelo fraco |
|---|---|---|---|---|
| `ticket-classification` | F1 | `openai/gpt-fake-large` | `anthropic/claude-fake-large` | `openai/gpt-fake-mini` |
| `reply-suggestion` | F2 | `anthropic/claude-fake-large` | `openai/gpt-fake-large` | `anthropic/claude-fake-mini` |
| `topics-report` | F3 | `anthropic/claude-fake-large` | `openai/gpt-fake-large` | `anthropic/claude-fake-mini` |
| `order-extraction` | F4 | `openai/gpt-fake-large` | `anthropic/claude-fake-large` | nenhum |

- O primário de cada capacidade mantém o provider da v1, para que a migração não mude custo nem saída.
- Os destinos de fallback são entradas próprias (`<capacidade>-fallback`, `<capacidade>-weak`) ligadas pela lista `fallbacks` do router. As chaves da aplicação só podem chamar os quatro nomes primários (`models` em `gateway/keys.json`); os destinos de fallback são internos.
- Com a opção 1, a decisão "esta tarefa aceita mini?" voltaria para a aplicação. Com a opção 3, não daria para ter política de fallback, timeout e orçamento diferentes por feature.

## Consequências

- O nome da capacidade é contrato estável entre aplicação e gateway; está como constante `CAPABILITY` no módulo de cada feature.
- Uma capacidade pode trocar de modelo, de provider ou ganhar/perder fallback sem tocar na aplicação.
- O corpo da resposta do gateway ainda traz o nome do modelo físico no campo `model`; a aplicação ignora esse campo.

## Evidência

- `gateway/config.yaml` (`model_list` e `router_settings.fallbacks`).
- README, "Troca de modelo": alterar o `model` de uma capacidade e reiniciar só o gateway muda o modelo registrado em `/admin/calls` na chamada seguinte, sem reiniciar o `app`.
