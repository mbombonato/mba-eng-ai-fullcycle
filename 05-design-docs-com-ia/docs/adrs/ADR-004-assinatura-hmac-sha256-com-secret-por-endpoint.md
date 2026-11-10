# ADR-004 — Assinatura HMAC-SHA256 com secret por endpoint e rotação com grace period de 24 h

- **Data da decisão:** reunião técnica de webhooks (decisão fechada em `[09:22] Sofia`)
- **Decisores:** Sofia (Segurança), Larissa (Tech Lead), Bruno (Pedidos), Diego (Plataforma)
- **Relacionados:** [RFC](../RFC.md) · [FDD §6.8 e §6.5](../FDD.md#68-contrato-de-saída-requisição-enviada-ao-cliente) · [ADR-005](ADR-005-entrega-at-least-once-com-x-event-id.md)

## Status

Aceito (sujeito à revisão de segurança da Sofia antes do deploy — `[09:46] Sofia`)

## Contexto

Os webhooks enviam dados de pedidos para endpoints fora da nossa infraestrutura. O cliente precisa conseguir validar que a requisição veio de nós e que o payload não foi adulterado no caminho (`[09:19] Sofia`). Já houve caso de cliente que vazou secret em log da própria aplicação (`[09:22] Diego`). A feature é exclusivamente **outbound** — os clientes só recebem, não enviam (`[09:02] Marcos`, `[09:03] Sofia`).

## Decisão

1. **HMAC-SHA256 sobre o corpo do request**, com a assinatura enviada no header `X-Signature` (`[09:20] Sofia`, `[09:22] Sofia`).
2. **Uma secret única por endpoint de webhook**, nunca uma secret global da plataforma (`[09:21] Sofia`). A secret é **gerada pela plataforma** e devolvida ao cliente na criação do webhook (`[09:31] Marcos`). Ela é armazenada na tabela de configuração junto de `url`, `customer_id` e estado ativo (`[09:21] Bruno`).
3. **Rotação via API**: o cliente pode pedir uma nova secret; a antiga continua válida em paralelo por **24 horas** e depois expira (`[09:21] Sofia`).
4. **TLS obrigatório**: a URL cadastrada precisa ser `https`; `http` é recusado com erro de validação no schema Zod (`[09:23] Sofia`).

## Alternativas Consideradas

| Alternativa | Por que foi descartada |
| --- | --- |
| **Secret global da plataforma** | Se vaza uma, vaza tudo (`[09:21] Sofia`). |
| **Rotação sem período de convivência** | O cliente não teria tempo de migrar seus sistemas; o grace period de 24 h existe exatamente para isso (`[09:21] Sofia`). |
| **Outro algoritmo/esquema de assinatura** (plausível, não detalhado na reunião) | HMAC-SHA256 é o padrão de mercado e todo cliente sério tem biblioteca para validá-lo (`[09:20] Sofia`). |

## Consequências

**Positivas**

- Autenticidade e integridade verificáveis pelo cliente com bibliotecas padrão.
- Vazamento de uma secret afeta apenas um endpoint e pode ser contido com rotação.
- O módulo segue as validações Zod já usadas em todo o projeto (`src/middlewares/validate.middleware.ts`).

**Negativas / trade-offs**

- A secret precisa ser recuperável pelo worker para assinar (não pode ser só hash como `passwordHash` em `prisma/schema.prisma`); o formato de armazenamento (em claro x cifrado) ficou para a revisão de segurança — ver [RFC](../RFC.md#questões-em-aberto).
- Durante as 24 h de grace period há duas secrets válidas para o mesmo endpoint, o que aumenta a complexidade de assinatura e de validação pelo cliente; o mecanismo exato de envio ficou em aberto.
- A secret passa a ser um dado sensível que não pode aparecer em logs — exige ampliar o `redact` do logger em `src/shared/logger/index.ts`.
- Responsabilidade de validação fica do lado do cliente; precisa ser bem documentada no portal (`[09:26] Marcos`).
