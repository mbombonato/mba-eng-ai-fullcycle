# 0001. Aceitar só OpenAI e Anthropic, via gateway da empresa, com teto mensal de gasto

- Status: aceita
- Data: 2026-11-09
- Nível: corporativa

## Contexto

O helpdesk colocou IA em quatro pontos sem nenhuma regra da empresa: cada feature escolheu o provider "que funcionou melhor no teste", as chaves ficaram na configuração da aplicação e ninguém sabia quanto se gastava. O diagnóstico da v1 mostrou o custo disso: um único pedido do relatório do mês consome ~222 mil tokens de entrada e ~12 mil de saída no `claude-fake-large` (≈ US$ 0,85) e continua gastando por mais de 5 minutos depois que a borda já devolveu `504` para quem pediu. Nada impedia isso de se repetir indefinidamente.

A pergunta aqui não é técnica ("como chamar o modelo"), é de negócio: com quais fornecedores a empresa aceita mandar dados de clientes e quanto ela aceita gastar com IA no atendimento.

## Opções consideradas

1. Deixar cada time escolher o provider e pagar a conta do próprio centro de custo.
2. Homologar os dois providers já usados (OpenAI e Anthropic), sempre por meio de um gateway da empresa, com um teto mensal de gasto para o helpdesk.
3. Escolher um único provider para tudo.

## Decisão

Opção 2.

- Providers aceitos: OpenAI e Anthropic. Os dois já têm contrato e já recebem dados do helpdesk; ter dois permite que um cubra a indisponibilidade do outro (ADR 0005). Um provider único (opção 3) faria de qualquer instabilidade dele uma parada total do atendimento, que é exatamente a dor do cenário.
- Nenhum sistema chama provider diretamente: o acesso é só pelo AI Gateway (ADR 0002), que é o único lugar com credencial de provider.
- Teto de gasto do helpdesk com IA: US$ 50 por mês, dividido em US$ 30 para as features em tempo real (F1, F2, F4) e US$ 20 para os relatórios (F3). O valor cobre com folga o uso esperado com os preços da tabela do provider e transforma um vazamento (como o relatório que roda depois do `504`) em recusa explícita em vez de fatura.

## Consequências

- Incluir um terceiro provider passa a ser uma decisão corporativa (revisar esta ADR), não uma linha de código.
- O teto é aplicado tecnicamente pelas chaves virtuais do gateway (ADR 0006). Ao atingir o teto, a feature é recusada até o próximo ciclo ou até alguém aprovar aumento: o atendimento perde a IA, não o atendimento.
- Alguém precisa ser dono do orçamento (aprovar aumento, olhar o gasto do mês).

## Evidência

- `gateway/keys.json`: `max_budget` 30 e 20, `budget_duration` 30d.
- `grep -rE "FAKE_OPENAI_KEY|FAKE_ANTHROPIC_KEY" app/ compose.yaml`: as chaves de provider só aparecem no serviço `gateway` do compose.
- Roteiro de governança do README: recusa por orçamento sem nova chamada em `/admin/calls`.
