# PRD — Sistema de Webhooks de Notificação de Pedidos

| Campo | Valor |
| --- | --- |
| **Produto** | Order Management System (OMS) |
| **PM responsável** | Marcos (Product Manager) |
| **Tech Lead** | Larissa |
| **Autor do documento** | Matheus Bombonato |
| **Status** | Rascunho: escopo definido na reunião técnica; aguardando revisão |
| **Documentos relacionados** | [RFC](RFC.md) · [FDD](FDD.md) · [ADRs](adrs/README.md) · [Tracker](TRACKER.md) |

## 1. Resumo e contexto da feature

O OMS passa a **avisar ativamente** os clientes B2B quando o status de um pedido deles muda, enviando uma notificação HTTP (webhook) para um endereço cadastrado pelo próprio cliente. Hoje o OMS não tem nenhum mecanismo de notificação externa: quem quer saber se um pedido mudou precisa consultar a API repetidamente.

A demanda veio formalmente de três clientes B2B — **Atlas Comercial, MaxDistribuição e Nova Cargo** (`[09:00] Marcos`) — e a solução foi definida em reunião técnica com Produto, Tech Lead, Pedidos, Plataforma e Segurança.

## 2. Problema e motivação

- **Integração lenta e cara para o cliente:** os clientes fazem polling periódico em `GET /orders` para descobrir mudanças (`[09:00] Marcos`).
- **Risco comercial:** a Atlas sinalizou que pode migrar para um concorrente se a funcionalidade não for entregue até o fim do trimestre (`[09:00] Marcos`); o prazo pedido é **fim de novembro** (`[09:45] Marcos`).
- **Expectativa de "tempo real":** para esses clientes, qualquer atraso abaixo de 10 segundos é aceitável; o importante é não precisar atualizar manualmente (`[09:02] Marcos`).

## 3. Público-alvo e cenários de uso

**Público-alvo**

| Persona | Necessidade |
| --- | --- |
| Integrador do cliente B2B (Atlas, MaxDistribuição, Nova Cargo) | Receber mudanças de status automaticamente nos seus sistemas. |
| Usuário do OMS que representa o cliente (role `OPERATOR` ou `ADMIN`) | Cadastrar e manter os webhooks do cliente via API (`[09:32] Marcos`). |
| Administrador do OMS (role `ADMIN`) | Reprocessar notificações que falharam definitivamente (`[09:36] Sofia`). |

**Cenários**

| ID | Cenário |
| --- | --- |
| PRD-CEN-01 | Um cliente cadastra um endpoint `https` e escolhe ser avisada apenas quando o pedido vira `SHIPPED` e `DELIVERED` (`[09:33] Marcos`). Quando um operador marca um pedido como enviado, o sistema do cliente recebe o aviso em poucos segundos. |
| PRD-CEN-02 | O sistema de um cliente fica 2 horas fora do ar para manutenção planejada. As notificações do período são reenviadas automaticamente quando ele volta (`[09:16] Diego`). |
| PRD-CEN-03 | Um cliente reclama que "não recebeu" um aviso; o suporte consulta o histórico das últimas entregas daquele webhook, com sucesso/falha e tempo de resposta (`[09:34] Marcos`). |
| PRD-CEN-04 | Um cliente vaza sua secret num log; ele pede uma nova secret pela API e tem 24 horas para trocar nos seus sistemas sem perder notificações (`[09:21] Sofia`, `[09:22] Diego`). |
| PRD-CEN-05 | Uma notificação esgota todas as tentativas; um administrador a reenvia manualmente depois que o cliente corrige o problema (`[09:18] Diego`). |

## 4. Objetivos e métricas de sucesso

| ID | Objetivo | Métrica | Meta | Origem |
| --- | --- | --- | --- | --- |
| PRD-OBJ-01 | Entregar notificações em "tempo real" na percepção do cliente | Tempo entre a mudança de status e a primeira tentativa de entrega (p95) | **< 10 segundos** (espera máxima de 2 s pelo ciclo do worker) | `[09:02] Marcos`, `[09:10] Larissa` |
| PRD-OBJ-02 | Atender os três clientes que fizeram o pedido formal | Clientes com webhook ativo em produção | **3 de 3** (Atlas, MaxDistribuição, Nova Cargo) até **fim de novembro** | `[09:00] Marcos`, `[09:45] Marcos` |
| PRD-OBJ-03 | Não perder nenhuma notificação | Mudanças de status com webhook interessado sem evento registrado | **0** | `[09:40] Bruno` |
| PRD-OBJ-04 | Tolerar indisponibilidade do cliente | Janela coberta por novas tentativas automáticas | **~15 horas** (5 retentativas) | `[09:17] Diego` |
| PRD-OBJ-05 | Entregar no prazo combinado | Sprints até o deploy, incluindo revisão de segurança | **3 sprints** | `[09:47] Larissa` |

## 5. Escopo

### 5.1 Incluso

- Cadastro, listagem, edição e remoção de webhooks por cliente, com filtro de status.
- Notificação automática a cada mudança de status de pedido.
- Assinatura de cada notificação, secret exclusiva por webhook e rotação de secret.
- Novas tentativas automáticas, fila de falhas definitivas (DLQ) e reprocessamento manual por administrador.
- Histórico de entregas por webhook.

### 5.2 Fora de escopo

| ID | Item | Situação na reunião | Origem |
| --- | --- | --- | --- |
| PRD-OOS-01 | **E-mail ao cliente quando o webhook falha repetidamente** | Adiado — "talvez próxima fase, depois que a gente medir o impacto". | `[09:37] Larissa`, `[09:38] Marcos` |
| PRD-OOS-02 | **Dashboard/painel visual** para o cliente ver seus webhooks | Descartado nesta fase — "só endpoints"; painel é projeto separado do time de frontend. | `[09:40] Larissa` |
| PRD-OOS-03 | **Rate limiting de envio** para o cliente | Adiado — "observar e decidir depois". | `[09:39] Diego`, `[09:39] Larissa` |
| PRD-OOS-04 | **Webhooks de entrada** (cliente enviando para o OMS) | Descartado — só saída. | `[09:02] Marcos` |
| PRD-OOS-05 | **Garantia de ordenação global** e múltiplos workers | Adiado — limitação conhecida; clientes não pediram. | `[09:13] Larissa`, `[09:14] Marcos` |
| PRD-OOS-06 | **Arquivamento** de notificações entregues (~30 dias) | Fora do escopo desta feature. | `[09:08] Diego` |
| PRD-OOS-07 | **Itens do pedido na notificação** | Descartado — payload enxuto; detalhes via `GET /orders/:id`. | `[09:43] Diego` |
| PRD-OOS-08 | **Garantia exactly-once** | Descartado — entrega é at-least-once. | `[09:25] Diego` |

## 6. Requisitos funcionais

| ID | Requisito | Origem |
| --- | --- | --- |
| PRD-FR-01 | O sistema deve notificar o cliente via HTTP POST sempre que o status de um pedido dele mudar. | `[09:00] Marcos` |
| PRD-FR-02 | O usuário autenticado deve conseguir **cadastrar** um webhook informando a URL, o cliente (`customer_id`) e a lista de status de interesse; o `customer_id` é informado na requisição e não extraído do JWT. | `[09:31] Marcos`, `[09:32] Larissa` |
| PRD-FR-03 | A secret do webhook deve ser **gerada pela plataforma** e devolvida na criação. | `[09:31] Marcos` |
| PRD-FR-04 | Deve ser possível **listar** os webhooks de um cliente, **editar** e **remover** um webhook. | `[09:33] Bruno` |
| PRD-FR-05 | Cada webhook escolhe **quais status** quer receber; status fora da lista não geram notificação. | `[09:33] Marcos`, `[09:34] Bruno` |
| PRD-FR-06 | O cliente deve conseguir **consultar o histórico das últimas 100 entregas** de um webhook, com sucesso/falha, payload, resposta e tempo de resposta. | `[09:34] Marcos` |
| PRD-FR-07 | Notificações que falharem devem ser **reenviadas automaticamente** em intervalos crescentes (1 min, 5 min, 30 min, 2 h, 12 h). | `[09:17] Larissa` |
| PRD-FR-08 | Após esgotar as tentativas, a notificação vai para uma **fila de falhas (DLQ)** com o motivo da falha. | `[09:18] Diego` |
| PRD-FR-09 | Um **administrador (role ADMIN)** deve conseguir **reprocessar** manualmente uma notificação da DLQ; a ação fica registrada com quem a executou. | `[09:18] Diego`, `[09:36] Sofia` |
| PRD-FR-10 | Cada notificação deve ser **assinada** (HMAC-SHA256) para o cliente validar origem e integridade. | `[09:20] Sofia` |
| PRD-FR-11 | O cliente deve conseguir **rotacionar a secret** pela API; a secret antiga continua válida por **24 horas**. | `[09:21] Sofia` |
| PRD-FR-12 | Cada notificação deve carregar um **identificador único do evento** (`X-Event-Id`) e o **identificador do webhook** (`X-Webhook-Id`). | `[09:25] Diego`, `[09:44] Sofia` |
| PRD-FR-13 | A notificação deve conter dados essenciais do pedido (número, status anterior e novo, cliente, valor total), refletindo o estado no momento da mudança, **sem os itens**. | `[09:43] Diego`, `[09:52] Larissa` |

## 7. Requisitos não funcionais

| ID | Requisito | Origem |
| --- | --- | --- |
| PRD-NFR-01 | **Latência:** notificação iniciada em menos de 10 s após a mudança de status; ciclo de verificação de 2 s. | `[09:02] Marcos`, `[09:10] Larissa` |
| PRD-NFR-02 | **Consistência:** nenhuma mudança de status pode ocorrer sem o registro da notificação correspondente, e uma falha do cliente nunca desfaz a mudança de status. | `[09:04] Bruno`, `[09:40] Bruno` |
| PRD-NFR-03 | **Segurança de transporte:** somente URLs `https`; `http` é recusado. | `[09:23] Sofia` |
| PRD-NFR-04 | **Isolamento de credenciais:** secret exclusiva por webhook, nunca global. | `[09:21] Sofia` |
| PRD-NFR-05 | **Tamanho máximo:** 64 KB por notificação; acima disso, erro (sem truncar). | `[09:24] Larissa` |
| PRD-NFR-06 | **Timeout:** 10 s por tentativa de entrega. | `[09:42] Diego` |
| PRD-NFR-07 | **Garantia de entrega:** at-least-once; o cliente deve deduplicar pelo `X-Event-Id`. | `[09:26] Larissa` |
| PRD-NFR-08 | **Disponibilidade independente:** o envio roda em processo separado da API, para que reinícios da API não interrompam entregas. | `[09:11] Diego` |
| PRD-NFR-09 | **Ordenação:** garantida apenas por pedido e enquanto houver um único worker. | `[09:13] Larissa` |
| PRD-NFR-10 | **Manutenibilidade:** reuso dos padrões do projeto (módulos, erros, logger, middlewares) sem infraestrutura nova. | `[09:30] Larissa` |

## 8. Decisões e trade-offs principais

| ID | Decisão | Trade-off aceito | ADR |
| --- | --- | --- | --- |
| PRD-DEC-01 | Registrar notificações numa outbox no MySQL, na mesma transação da mudança de status. | Menos reatividade que uma fila dedicada, em troca de zero infraestrutura nova e consistência garantida. | [ADR-001](adrs/ADR-001-outbox-transacional-no-mysql.md) |
| PRD-DEC-02 | Worker separado verificando a cada 2 s. | Até 2 s de espera, aceito pelo produto. | [ADR-002](adrs/ADR-002-worker-separado-com-polling.md) |
| PRD-DEC-03 | 5 retentativas em ~15 h e depois DLQ. | Notificação pode chegar bem atrasada; "se o cliente cair 15 h, o problema é sério dele" (`[09:17] Marcos`). | [ADR-003](adrs/ADR-003-retry-com-backoff-exponencial-e-dlq.md) |
| PRD-DEC-04 | HMAC-SHA256 com secret por webhook e rotação de 24 h. | Mais gestão de secrets, em troca de contenção de vazamentos. | [ADR-004](adrs/ADR-004-assinatura-hmac-sha256-com-secret-por-endpoint.md) |
| PRD-DEC-05 | At-least-once com `X-Event-Id`. | Cliente precisa deduplicar; Marcos documenta com destaque no portal (`[09:26] Marcos`). | [ADR-005](adrs/ADR-005-entrega-at-least-once-com-x-event-id.md) |
| PRD-DEC-06 | Reuso dos padrões do projeto. | Sem ferramentas dedicadas de métricas/tracing nesta fase. | [ADR-006](adrs/ADR-006-reuso-dos-padroes-existentes-do-projeto.md) |
| PRD-DEC-07 | Payload enxuto em snapshot, filtrado na inserção. | Cliente que precisa dos itens faz uma chamada extra. | [ADR-007](adrs/ADR-007-snapshot-do-payload-e-filtro-na-insercao.md) |

## 9. Dependências

| ID | Dependência | Origem |
| --- | --- | --- |
| PRD-DEP-01 | Revisão de segurança da Sofia (mínimo 2 dias úteis) antes do deploy, com foco em HMAC e geração de secret. | `[09:46] Sofia` |
| PRD-DEP-02 | Portal do desenvolvedor atualizado por Marcos (integração via API, validação de assinatura e deduplicação). | `[09:26] Marcos`, `[09:40] Marcos` |
| PRD-DEP-03 | Confirmação do prazo com a Atlas e comunicação aos clientes. | `[09:47] Marcos`, `[09:49] Marcos` |
| PRD-DEP-04 | Clientes com endpoint HTTPS capaz de validar HMAC-SHA256 e deduplicar eventos. | `[09:20] Sofia`, `[09:24] Diego` |
| PRD-DEP-05 | Fluxo de mudança de status existente (`PATCH /orders/:id/status`) como gatilho único das notificações. | `[09:40] Bruno` |

## 10. Riscos e mitigação

| ID | Risco | Probabilidade | Impacto | Mitigação |
| --- | --- | --- | --- | --- |
| PRD-RISK-01 | **Prazo:** 3 sprints estimadas contra o prazo da Atlas (fim de novembro); atraso pode levar à perda do cliente. | Média | Alto | Marcos confirma o prazo com a Atlas; escopo enxuto (e-mail, dashboard e rate limiting fora); revisão de segurança reservada desde já. (`[09:45] Marcos`, `[09:47] Larissa`) |
| PRD-RISK-02 | **Cliente processa a mesma notificação duas vezes** por não deduplicar. | Média | Médio | `X-Event-Id` estável e documentação destacada no portal. (`[09:25] Sofia`, `[09:26] Marcos`) |
| PRD-RISK-03 | **Vazamento de secret** de um cliente. | Média | Alto | Secret por webhook, rotação com 24 h de convivência, revisão da Sofia. (`[09:21] Sofia`, `[09:22] Diego`) |
| PRD-RISK-04 | **Cliente "bombardeado"** por muitas notificações em sequência (ex.: 50 em 1 minuto). | Baixa | Médio | Monitorar volume por webhook; decidir rate limiting com dados. (`[09:38] Diego`) |
| PRD-RISK-05 | **Notificações fora de ordem** caso o processamento seja escalado. | Baixa | Médio | Um único worker nesta fase; ordenação por pedido documentada como limitação. (`[09:13] Larissa`) |

## 11. Critérios de aceitação

| ID | Critério |
| --- | --- |
| PRD-CA-01 | Dado um webhook cadastrado para `SHIPPED`, quando um pedido do cliente muda para `SHIPPED`, o endpoint do cliente recebe a notificação em menos de 10 s. |
| PRD-CA-02 | Dado um webhook cadastrado só para `SHIPPED` e `DELIVERED`, quando o pedido muda para `PAID`, nenhuma notificação é enviada. |
| PRD-CA-03 | Tentar cadastrar uma URL `http://` resulta em erro de validação. |
| PRD-CA-04 | A secret é devolvida na criação e a notificação recebida tem assinatura HMAC-SHA256 válida com essa secret. |
| PRD-CA-05 | Com o endpoint do cliente fora do ar, o sistema tenta novamente em 1 min, 5 min, 30 min, 2 h e 12 h; depois disso a notificação aparece na DLQ. |
| PRD-CA-06 | Um usuário `OPERATOR` não consegue reprocessar a DLQ; um `ADMIN` consegue, e a ação fica registrada em log com o usuário. |
| PRD-CA-07 | Após rotacionar a secret, notificações nas 24 h seguintes continuam validáveis com a secret antiga. |
| PRD-CA-08 | O histórico de entregas mostra as últimas 100 tentativas com sucesso/falha, payload, resposta e tempo. |
| PRD-CA-09 | Se o registro da notificação falhar, a mudança de status do pedido também não acontece. |

## 12. Estratégia de testes e validação

| ID | Estratégia |
| --- | --- |
| PRD-TST-01 | **Testes de integração** (Vitest + Supertest, como `tests/orders.test.ts`) para CRUD de webhooks, filtro de status, atomicidade com a mudança de status e permissão `ADMIN` no replay. |
| PRD-TST-02 | **Testes do worker** contra um servidor HTTP falso simulando sucesso, erro 500, lentidão > 10 s e payload > 64 KB, verificando retry, DLQ e assinatura. |
| PRD-TST-03 | **Revisão de segurança** dedicada da Sofia (HMAC e geração de secret) antes do deploy (`[09:46] Sofia`). |
| PRD-TST-04 | **Validação do design antes de codar:** sessão de revisão dos documentos com Bruno e Diego conduzida pela Larissa (`[09:50] Larissa`). |
| PRD-TST-05 | **Acompanhamento pós-lançamento** das métricas de latência, DLQ e volume por webhook, que alimentam as decisões adiadas (e-mail e rate limiting) (`[09:37] Larissa`, `[09:39] Larissa`). |
