# Da integração frágil à arquitetura resiliente

Desafio referente ao módulo **Arquitetura na Era da IA**.

---

<h1>Da integra&ccedil;&atilde;o fr&aacute;gil &agrave; arquitetura resiliente: IA em produ&ccedil;&atilde;o num helpdesk</h1>

<h2>Descri&ccedil;&atilde;o</h2>

<p>Neste desafio voc&ecirc; recebe uma aplica&ccedil;&atilde;o com IA do jeito que ela costuma nascer (acoplada, s&iacute;ncrona, com o provider espalhado pelo c&oacute;digo), mede o quanto isso custa e a leva, com decis&otilde;es registradas e evid&ecirc;ncia medida, at&eacute; um estado em que trocar de modelo ou de provider &eacute; uma mudan&ccedil;a de configura&ccedil;&atilde;o, e n&atilde;o um projeto.</p>

<p>A aplica&ccedil;&atilde;o &eacute; entregue em Python com FastAPI, e a evolu&ccedil;&atilde;o continua nessa stack. As ferramentas (gateway, testes, medi&ccedil;&atilde;o) ficam a seu crit&eacute;rio. As decis&otilde;es de arquitetura, como o modo de execu&ccedil;&atilde;o de cada feature e a pol&iacute;tica de fallback, partem das caracter&iacute;sticas do contrato e precisam cumprir os crit&eacute;rios de aceite. Cada decis&atilde;o precisa estar registrada, justificada pelos fatos do problema e comprovada por um efeito observ&aacute;vel. O escopo &eacute; o que est&aacute; descrito aqui: componentes, features ou camadas que os requisitos n&atilde;o pedem n&atilde;o s&atilde;o avaliados e s&oacute; aumentam o que voc&ecirc; precisa justificar.</p>

<hr />

<h2>Cen&aacute;rio</h2>

<p>O helpdesk de uma loja online colocou IA em quatro pontos do atendimento. Quem fez foi r&aacute;pido: cada feature chama o SDK do provider direto de dentro do c&oacute;digo, uma usa a OpenAI e outra a Anthropic porque &quot;funcionou melhor no teste&quot;, as chaves ficam na configura&ccedil;&atilde;o da aplica&ccedil;&atilde;o e tudo responde de forma s&iacute;ncrona. Esse c&oacute;digo &eacute; o <code>app/</code> do reposit&oacute;rio base.</p>

<p>Tr&ecirc;s meses depois, a conta chegou. O relat&oacute;rio mensal de temas nunca termina: a requisi&ccedil;&atilde;o morre no proxy da empresa. O atendente olha 15 segundos para uma tela parada esperando a sugest&atilde;o de resposta. Na &uacute;ltima instabilidade de um provider, metade do helpdesk parou junto. E trocar um modelo por outro mais barato exige deploy, porque o nome do modelo est&aacute; no c&oacute;digo.</p>

<p>Voc&ecirc; &eacute; a pessoa de arquitetura que vai conduzir essa virada. Primeiro, reproduz as dores do sistema que herdou e mede o problema. Depois, planeja, refatora com um agente de IA usando a m&eacute;trica como juiz, coloca um gateway na frente dos providers e decide, feature por feature, como cada chamada deve ser executada. No fim, qualquer pessoa do time precisa conseguir trocar um modelo, derrubar um provider ou estourar um or&ccedil;amento e ver o sistema se comportar exatamente como os ADRs dizem.</p>

<hr />

<h2>Sobre o foco do desafio</h2>

<p>O foco &eacute; arquitetura, n&atilde;o prompt nem qualidade de texto gerado. Por isso o reposit&oacute;rio base traz um provider simulado (<code>provider-fake</code>) que imita as APIs da OpenAI e da Anthropic, responde de forma determin&iacute;stica, cobra tokens, tem lat&ecirc;ncia realista e falha sob comando. O fluxo do avaliador roda inteiramente contra ele, sem chave paga. Voc&ecirc; pode usar providers reais durante o desenvolvimento se quiser, mas nada da entrega pode depender deles.</p>

<p>Algumas situa&ccedil;&otilde;es no starter travam de prop&oacute;sito. Cada uma tem uma pista (se&ccedil;&atilde;o Fric&ccedil;&otilde;es propositais): a inten&ccedil;&atilde;o &eacute; voc&ecirc; descobrir a solu&ccedil;&atilde;o, n&atilde;o sofrer no escuro.</p>

<hr />

<h2>Objetivo</h2>

<p>Entregar, num fork p&uacute;blico do reposit&oacute;rio base, o diagn&oacute;stico da aplica&ccedil;&atilde;o recebida, as decis&otilde;es de arquitetura registradas (ADRs e plano de refatora&ccedil;&atilde;o), a medi&ccedil;&atilde;o de acoplamento das tr&ecirc;s vers&otilde;es e a aplica&ccedil;&atilde;o evolu&iacute;da atr&aacute;s de um AI Gateway, com os modos de execu&ccedil;&atilde;o decididos. O detalhe de cada pe&ccedil;a est&aacute; em Entreg&aacute;vel, e os caminhos, em Estrutura obrigat&oacute;ria do entreg&aacute;vel.</p>

<hr />

<h2>Reposit&oacute;rio base</h2>

<p><a href="https://github.com/devfullcycle/desafio-arquitetura-era-ia-1">https://github.com/devfullcycle/desafio-arquitetura-era-ia-1</a></p>

<p>Fa&ccedil;a o fork e trabalhe na <code>main</code> do seu fork. Para conhecer o terreno:</p>

<pre>  
<code>cp .env.example .env  
docker compose up -d --build --wait  
curl -s localhost:8000/health  
curl -s -X POST localhost:8000/tickets/classification -H "Content-Type: application/json" \  
  -d '{"ticket\_id": "TK-00042", "text": "Meu pedido #481516 n&atilde;o chegou e j&aacute; passou do prazo, urgente"}'</code></pre>

<p>O compose sobe o <code>provider-fake</code>, a borda (servi&ccedil;o <code>edge</code>) e a aplica&ccedil;&atilde;o (servi&ccedil;o <code>app</code>). O <code>--wait</code> faz o comando s&oacute; retornar quando os servi&ccedil;os estiverem saud&aacute;veis.</p>

<p>No seu fork, o <code>README.md</code> passa a ser o seu (se&ccedil;&otilde;es obrigat&oacute;rias em Entreg&aacute;vel). O enunciado continua dispon&iacute;vel no reposit&oacute;rio base.</p>

<hr />

<h2>Contexto</h2>

<h3>O que o reposit&oacute;rio base traz</h3>

<ul>  
    <li><code>provider-fake/</code> (n&atilde;o alterar): o provider simulado, em container, exposto em <code>http://localhost:8090</code> (dentro do compose, <code>http://provider-fake:8090</code>). Documenta&ccedil;&atilde;o completa em <code>provider-fake/README.md</code>.</li>  
    <li><code>app/</code> (entregue; &eacute; o que voc&ecirc; evolui): a aplica&ccedil;&atilde;o do helpdesk, descrita em A aplica&ccedil;&atilde;o existente.</li>  
    <li><code>edge/</code> (n&atilde;o alterar): a borda, um nginx que representa o proxy reverso da empresa. Ele &eacute; a porta de entrada oficial do helpdesk em <code>http://localhost:8000</code> e encaminha tudo para <code>http://app:8080</code>. O avaliador usa sempre a borda.</li>  
    <li><code>data/tickets.jsonl</code> (n&atilde;o alterar): 5.000 tickets de agosto de 2026, um JSON por linha, com os campos <code>id</code>, <code>created\_at</code>, <code>customer\_id</code> e <code>text</code>.</li>  
    <li><code>docs/adr/0000-template.md</code>: um template de ADR, que voc&ecirc; pode seguir ou substituir.</li>  
    <li><code>compose.yaml</code> e <code>.env.example</code>: a base que voc&ecirc; estende. As chaves dos providers est&atilde;o no <code>.env.example</code> e chegam hoje &agrave; aplica&ccedil;&atilde;o por <code>env\_file</code>.</li>  
</ul>

<h3>O provider simulado</h3>

<p>Ele imita dois providers distintos, cada um com seu formato nativo:</p>

<p><strong>Provider <code>openai</code></strong></p>

<ul>  
    <li>Base URL (dentro do compose): <code>http://provider-fake:8090/openai/v1</code></li>  
    <li>Formato: Chat Completions (<code>/chat/completions</code>)</li>  
    <li>Autentica&ccedil;&atilde;o: <code>Authorization: Bearer &lt;FAKE\_OPENAI\_KEY&gt;</code></li>  
    <li>Modelos: <code>gpt-fake-large</code>, <code>gpt-fake-mini</code></li>  
</ul>

<p><strong>Provider <code>anthropic</code></strong></p>

<ul>  
    <li>Base URL (dentro do compose): <code>http://provider-fake:8090/anthropic</code></li>  
    <li>Formato: Messages (<code>/v1/messages</code>)</li>  
    <li>Autentica&ccedil;&atilde;o: <code>x-api-key: &lt;FAKE\_ANTHROPIC\_KEY&gt;</code></li>  
    <li>Modelos: <code>claude-fake-large</code>, <code>claude-fake-mini</code></li>  
</ul>

<p>Os SDKs oficiais das duas empresas funcionam contra ele apontando a base URL. Os dois formatos suportam streaming (SSE) no padr&atilde;o de cada provider. As chaves aceitas est&atilde;o no <code>.env.example</code>.</p>

<p>O que voc&ecirc; precisa saber para o desafio (o resto est&aacute; no README do provider):</p>

<ul>  
    <li>O modelo simulado entende quatro tarefas. A primeira linha da mensagem do usu&aacute;rio deve ser <code>TASK: classify</code>, <code>TASK: suggest</code>, <code>TASK: topics</code> ou <code>TASK: extract</code>, seguida do conte&uacute;do. O formato exato de entrada e sa&iacute;da de cada tarefa est&aacute; no README do provider. O texto do prompt n&atilde;o &eacute; avaliado.</li>  
    <li>Os modelos <code>large</code> dos dois providers s&atilde;o equivalentes entre si. Os modelos <code>mini</code> s&atilde;o mais r&aacute;pidos e baratos, e piores: a diferen&ccedil;a de qualidade aparece de forma concreta em pelo menos uma das tarefas. Descobrir qual e o quanto importa &eacute; parte do desafio.</li>  
    <li>Cada modelo tem janela de contexto, pre&ccedil;o por token, tempo at&eacute; o primeiro token e velocidade de gera&ccedil;&atilde;o declarados no README do provider. A resposta traz <code>usage</code> com os tokens consumidos.</li>  
    <li>Endpoints de administra&ccedil;&atilde;o controlam o comportamento e registram tudo:</li>  
</ul>

<pre>  
<code>POST /admin/failures   {"provider": "openai", "model": "gpt-fake-large", "mode": "error\_500"}  
                       mode: normal | error\_500 | error\_429 | timeout | slow | midstream\_error  
                       "model" &eacute; opcional; sem ele, vale para o provider inteiro  
GET  /admin/calls      &uacute;ltimas chamadas recebidas: provider, model, task, stream, status, tokens, dura&ccedil;&atilde;o  
POST /admin/reset      volta tudo ao modo normal e limpa o registro de chamadas</code></pre>

<p>O <code>/admin/calls</code> &eacute; o instrumento de prova do desafio: &eacute; por ele que o avaliador confirma para qual provider e modelo cada requisi&ccedil;&atilde;o foi de fato, quantas tentativas aconteceram e se uma chamada recusada chegou ou n&atilde;o ao provider.</p>

<h3>A aplica&ccedil;&atilde;o existente</h3>

<p>Python 3.12 com FastAPI e os SDKs oficiais <code>openai</code> e <code>anthropic</code>. O c&oacute;digo fica em <code>app/helpdesk/</code>:</p>

<ul>  
    <li><code>main.py</code>: as rotas HTTP das quatro features e o <code>GET /health</code></li>  
    <li><code>schemas.py</code>: os tipos de entrada e sa&iacute;da (pydantic)</li>  
    <li><code>config.py</code>: credenciais dos providers, base URLs, nomes dos modelos f&iacute;sicos de cada feature e par&acirc;metros do relat&oacute;rio</li>  
    <li><code>llm.py</code>: um cliente de SDK por provider e as fun&ccedil;&otilde;es <code>call\_openai</code> e <code>call\_anthropic</code></li>  
    <li><code>classification.py</code>, <code>suggestion.py</code>, <code>extraction.py</code> e <code>report.py</code>: uma feature cada</li>  
    <li><code>tickets.py</code>: a leitura de <code>data/tickets.jsonl</code>, montado no container em <code>/data</code></li>  
</ul>

<p>F1 e F4 usam o provider <code>openai</code>; F2 e F3 usam o <code>anthropic</code>, cada um no seu formato nativo. A F3 divide os tickets do per&iacute;odo em lotes de 150 e chama o modelo para cada lote, um depois do outro, porque o per&iacute;odo inteiro n&atilde;o cabe na janela de contexto. Nenhuma chamada tem timeout ou pol&iacute;tica de retry configurados: valem os padr&otilde;es dos SDKs.</p>

<h3>O contrato do helpdesk</h3>

<p>A aplica&ccedil;&atilde;o escuta em <code>8080</code> dentro do compose, como servi&ccedil;o <code>app</code>. As quatro features s&atilde;o fixas no que recebem e no resultado que produzem. Na aplica&ccedil;&atilde;o recebida, as quatro respondem de forma s&iacute;ncrona, com o resultado no corpo da resposta. A forma de entrega (s&iacute;ncrono, streaming ou ass&iacute;ncrono) &eacute; o que pode mudar na <code>main</code> (requisito 6).</p>

<p><strong>F1 Classificar ticket</strong></p>

<ul>  
    <li>Rota: <code>POST /tickets/classification</code></li>  
    <li>Entrada: <code>{"ticket\_id", "text"}</code></li>  
    <li>Resultado: <code>{"ticket\_id", "category", "priority"}</code></li>  
    <li>Caracter&iacute;sticas do neg&oacute;cio: Roda na abertura do ticket, com o cliente esperando a confirma&ccedil;&atilde;o na tela. Sa&iacute;da curta, de valores fixos.</li>  
</ul>

<p><strong>F2 Sugerir resposta</strong></p>

<ul>  
    <li>Rota: <code>POST /tickets/reply-suggestion</code></li>  
    <li>Entrada: <code>{"ticket\_id", "text"}</code></li>  
    <li>Resultado: <code>{"ticket\_id", "suggestion"}</code></li>  
    <li>Caracter&iacute;sticas do neg&oacute;cio: O atendente est&aacute; olhando a tela e come&ccedil;a a ler e editar assim que o texto aparece. Sa&iacute;da longa.</li>  
</ul>

<p><strong>F3 Relat&oacute;rio de temas</strong></p>

<ul>  
    <li>Rota: <code>POST /reports/topics</code></li>  
    <li>Entrada: <code>{"start": "2026-08-01", "end": "2026-08-31"}</code></li>  
    <li>Resultado: <code>{"start", "end", "total\_tickets", "topics": [{"topic", "count", "examples": [ids]}]}</code></li>  
    <li>Caracter&iacute;sticas do neg&oacute;cio: L&ecirc; os tickets do per&iacute;odo em <code>data/tickets.jsonl</code>. O m&ecirc;s inteiro s&atilde;o 5.000 tickets. Quem pede &eacute; um painel interno no navegador, que n&atilde;o exp&otilde;e callback. Ningu&eacute;m fica esperando olhando para ele.</li>  
</ul>

<p><strong>F4 Extrair dados do pedido</strong></p>

<ul>  
    <li>Rota: <code>POST /tickets/extraction</code></li>  
    <li>Entrada: <code>{"ticket\_id", "text"}</code></li>  
    <li>Resultado: <code>{"ticket\_id", "order\_number", "product"}</code></li>  
    <li>Caracter&iacute;sticas do neg&oacute;cio: Alimenta uma automa&ccedil;&atilde;o de troca e devolu&ccedil;&atilde;o sem revis&atilde;o humana. Um campo errado gera uma troca errada, que custa frete, estoque e cliente.</li>  
</ul>

<p>Valores permitidos: <code>category</code> em <code>delivery</code>, <code>payment</code>, <code>exchange\_return</code>, <code>product\_defect</code>, <code>other</code>; <code>priority</code> em <code>low</code>, <code>medium</code>, <code>high</code>; <code>order\_number</code> no formato <code>#</code> seguido de 6 d&iacute;gitos, ou <code>null</code> quando o ticket n&atilde;o cita pedido; <code>product</code> texto ou <code>null</code>.</p>

<p>A aplica&ccedil;&atilde;o tamb&eacute;m exp&otilde;e <code>GET /health</code>, que responde <code>200</code>.</p>

<h3>Fric&ccedil;&otilde;es propositais</h3>

<p>S&atilde;o situa&ccedil;&otilde;es intencionais. Cada uma tem uma pista.</p>

<ul>  
    <li><strong>A borda tem paci&ecirc;ncia limitada.</strong> Ela encerra a requisi&ccedil;&atilde;o com <code>504</code> quando a aplica&ccedil;&atilde;o passa 30 segundos sem enviar nenhum byte. Pista: em uma cadeia de proxies, o timeout mais curto vence, e normalmente n&atilde;o &eacute; o seu. Leia <code>edge/nginx.conf</code>.</li>  
    <li><strong>Desistir n&atilde;o &eacute; cancelar.</strong> Quando a borda devolve <code>504</code>, a aplica&ccedil;&atilde;o recebida continua trabalhando. Pista: pe&ccedil;a o relat&oacute;rio do m&ecirc;s, espere o <code>504</code> e acompanhe o <code>/admin/calls</code> pelos minutos seguintes. Quem est&aacute; pagando por esses tokens?</li>  
    <li><strong>Os padr&otilde;es dos SDKs n&atilde;o foram pensados para o seu or&ccedil;amento de lat&ecirc;ncia.</strong> Pista: descubra qual &eacute; o timeout e quantos retries os SDKs <code>openai</code> e <code>anthropic</code> fazem por padr&atilde;o, e compare com os 30 segundos da borda.</li>  
    <li><strong>O modelo barato n&atilde;o &eacute; t&atilde;o bom.</strong> Pista: antes de decidir onde aceitar um fallback com modelo fraco, chame cada tarefa nos dois tamanhos e compare as sa&iacute;das.</li>  
</ul>

<hr />

<h2>Tecnologias obrigat&oacute;rias</h2>

<ul>  
    <li>Docker e Docker Compose v2</li>  
    <li>Git, com as tags exigidas publicadas no fork (<code>git push --tags</code>)</li>  
    <li>Um AI Gateway self-hosted rodando como servi&ccedil;o <code>gateway</code> no compose. O LiteLLM Proxy, visto no curso, &eacute; a sugest&atilde;o; qualquer outro vale se entregar as capacidades do requisito 5. Gateways SaaS n&atilde;o s&atilde;o aceitos, porque o avaliador precisa subir tudo localmente.</li>  
    <li>A aplica&ccedil;&atilde;o continua em Python 3.12 com FastAPI. Biblioteca de testes e ferramenta de medi&ccedil;&atilde;o &agrave; sua escolha.</li>  
</ul>

<p>&Eacute; proibido alterar <code>provider-fake/</code>, <code>edge/</code> e <code>data/</code>.</p>

<hr />

<h2>Requisitos</h2>

<p>Cada requisito est&aacute; amarrado a um conceito dos m&oacute;dulos 01 a 04. Leia o porqu&ecirc; antes da tarefa: &eacute; ele que diz se voc&ecirc; resolveu de verdade ou s&oacute; cumpriu tabela.</p>

<h3>1. Conhecer a aplica&ccedil;&atilde;o recebida</h3>

<p><strong>Por qu&ecirc;.</strong> N&atilde;o d&aacute; para afirmar que uma arquitetura melhorou sem um ponto de partida medido, e n&atilde;o d&aacute; para decidir nada sem entender onde a dor mora. O cen&aacute;rio descreve quatro dores; antes de mexer em qualquer linha, voc&ecirc; as reproduz e as transforma em fatos observ&aacute;veis. &Eacute; desse diagn&oacute;stico que os seus ADRs v&atilde;o partir.</p>

<p><strong>Tarefa.</strong></p>

<ul>  
    <li>Suba o ambiente e exercite as 4 features pela borda (<code>localhost:8000</code>)</li>  
    <li>Reproduza as quatro dores do cen&aacute;rio, usando os modos de falha do provider simulado quando for o caso: o relat&oacute;rio do m&ecirc;s n&atilde;o chega; a sugest&atilde;o de resposta deixa o atendente esperando sem ver nada; com um provider fora do ar ou travado, parte do helpdesk para; trocar o modelo de uma feature exige mudar c&oacute;digo e reconstruir a aplica&ccedil;&atilde;o</li>  
    <li>Registre o diagn&oacute;stico na se&ccedil;&atilde;o &quot;Diagn&oacute;stico da v1&quot; do README: para cada dor, o comando executado, o que foi observado (status, tempo, registros de <code>/admin/calls</code>) e em qual trecho de <code>app/</code> a causa est&aacute;</li>  
    <li>N&atilde;o altere <code>app/</code> nesta etapa. A &uacute;nica exce&ccedil;&atilde;o &eacute; demonstrar a dor da troca de modelo: voc&ecirc; pode alterar <code>app/</code> temporariamente para isso, desde que desfa&ccedil;a a altera&ccedil;&atilde;o antes da tag <code>v1-coupled</code>.</li>  
</ul>

<h3>2. Testes de caracteriza&ccedil;&atilde;o</h3>

<p><strong>Por qu&ecirc;.</strong> Refatora&ccedil;&atilde;o &eacute; mudan&ccedil;a de estrutura sem mudan&ccedil;a de comportamento; se o comportamento mudou, foi reescrita disfar&ccedil;ada. Os testes de caracteriza&ccedil;&atilde;o (Feathers) fixam o que o sistema faz hoje e s&atilde;o a rede de seguran&ccedil;a que permite entregar a refatora&ccedil;&atilde;o a um agente de IA sem medo.</p>

<p><strong>Tarefa.</strong></p>

<ul>  
    <li>Escreva, em <code>tests/characterization/</code>, uma su&iacute;te que exercita as 4 features pela API HTTP e fixa o comportamento observado da <code>v1-coupled</code>, incluindo pelo menos um caso de erro de entrada por feature. A su&iacute;te fixa o corpo das respostas (campos e valores), n&atilde;o s&oacute; o status HTTP.</li>  
    <li>A su&iacute;te roda com um &uacute;nico comando documentado no README, contra a aplica&ccedil;&atilde;o no compose</li>  
    <li>Quando a su&iacute;te passar contra a aplica&ccedil;&atilde;o recebida, marque o commit com a tag <code>v1-coupled</code>. Nesse commit, <code>app/</code> &eacute; exatamente o do reposit&oacute;rio base.</li>  
    <li>A su&iacute;te &eacute; a mesma nas tags <code>v1-coupled</code> e <code>v2-decoupled</code> e passa nas duas. Na <code>main</code>, ela pode ser atualizada para o contrato novo das features que mudaram de modo de execu&ccedil;&atilde;o (requisito 6); a igualdade &eacute; exigida s&oacute; entre as duas tags.</li>  
</ul>

<h3>3. Medir antes de mexer</h3>

<p><strong>Por qu&ecirc;.</strong> Sem n&uacute;mero, &quot;isso est&aacute; acoplado demais&quot; &eacute; opini&atilde;o, e a discuss&atilde;o vira prefer&ecirc;ncia pessoal. O m&oacute;dulo 02 transforma opini&atilde;o em medida com a Main Sequence: cada componente vira um ponto no gr&aacute;fico A &times; I, e a refatora&ccedil;&atilde;o ganha um crit&eacute;rio de pronto observ&aacute;vel.</p>

<p><strong>Tarefa.</strong></p>

<ul>  
    <li>Escreva (ou adapte) um script em <code>metrics/</code> que recebe o caminho do c&oacute;digo a medir (a pasta <code>app/helpdesk/</code> de qualquer checkout) e calcula, por componente, Ca, Ce, I, A e D segundo a r&eacute;gua abaixo</li>  
    <li>O script grava <code>metrics/results/&lt;name&gt;.csv</code> com o cabe&ccedil;alho exato <code>component,ca,ce,i,a,d</code> e um gr&aacute;fico A &times; I com a Main Sequence tra&ccedil;ada</li>  
    <li>A r&eacute;gua &eacute; fixa, para que as medi&ccedil;&otilde;es de todos sejam compar&aacute;veis: componente &eacute; cada m&oacute;dulo <code>.py</code> de <code>app/helpdesk/</code>, incluindo subpastas, identificado pelo caminho com pontos (ex.: <code>adapters.gateway</code>), exceto os <code>\_\_init\_\_.py</code>; uma depend&ecirc;ncia &eacute; um import, relativo ou absoluto, que resolve para outro componente (ex.: <code>from ..ports import Gateway</code> ou <code>from helpdesk import config</code>); bibliotecas externas e da biblioteca padr&atilde;o n&atilde;o contam; Ca &eacute; quantos componentes importam este, Ce &eacute; quantos este importa; I = Ce / (Ce + Ca), ou 0 quando os dois s&atilde;o zero; A &eacute; o n&uacute;mero de classes abstratas (que herdam de <code>typing.Protocol</code> ou <code>abc.ABC</code>) dividido pelo total de classes do m&oacute;dulo, ou 0 quando o m&oacute;dulo n&atilde;o tem classes; D = |A + I - 1|; valores arredondados para 2 casas.</li>  
    <li>Componentes concretos que quase nunca mudam (ex.: tipos de valor do dom&iacute;nio) caem na zona de dor pela f&oacute;rmula sem serem um problema real. Se for o caso, declare-os no ADR da m&eacute;trica como est&aacute;veis por natureza, com justificativa. &Eacute; uma leitura cr&iacute;tica da m&eacute;trica, n&atilde;o uma brecha: o componente que chama o gateway e os componentes das features n&atilde;o entram nessa lista.</li>  
    <li>Me&ccedil;a a <code>v1-coupled</code> e versione o resultado (<code>metrics/results/v1-coupled.csv</code> e o gr&aacute;fico). O script nasce depois da tag: para medir uma tag, rode o script da sua branch sobre um checkout dela (ex.: <code>git worktree add ../v1 v1-coupled</code>).</li>  
</ul>

<h3>4. Planejar, pilotar e refatorar com agente (tag <code>v2-decoupled</code>)</h3>

<p><strong>Por qu&ecirc;.</strong> O agente de IA &eacute; persuasivo, mas n&atilde;o &eacute; confi&aacute;vel para avaliar o pr&oacute;prio trabalho. O ciclo do m&oacute;dulo 02 resolve isso casando o agente, que n&atilde;o &eacute; determin&iacute;stico, com testes e m&eacute;trica, que s&atilde;o. E o primeiro plano quase nunca sobrevive ao contato com a medi&ccedil;&atilde;o: por isso existe piloto antes de escalar.</p>

<p><strong>Tarefa.</strong></p>

<ul>  
    <li>Escreva <code>docs/refactoring-plan.md</code> com os componentes-alvo, a estrat&eacute;gia para cada um (aumentar A, reduzir Ca, inverter a depend&ecirc;ncia, compor em vez de herdar) e o crit&eacute;rio de pronto baseado na m&eacute;trica</li>  
    <li>Execute um piloto em um &uacute;nico componente antes de escalar, e registre no plano a medi&ccedil;&atilde;o antes e depois do piloto</li>  
    <li>Registre no plano pelo menos uma revis&atilde;o (o que mudou do plano original e por qu&ecirc;, com base no que o piloto ou a medi&ccedil;&atilde;o mostrou)</li>  
    <li>Fa&ccedil;a a refatora&ccedil;&atilde;o com um agente de IA de sua escolha. Registre no plano como foi o handoff: o que voc&ecirc; entregou ao agente, como a m&eacute;trica e os testes foram usados para aceitar ou rejeitar o que ele produziu.</li>  
    <li>Coloque o gateway na frente dos providers nesta etapa. O m&iacute;nimo exigido na <code>v2-decoupled</code> &eacute;: a aplica&ccedil;&atilde;o chama os modelos s&oacute; pelo gateway, usando nomes l&oacute;gicos e uma chave do pr&oacute;prio gateway, sem as chaves dos providers. Governan&ccedil;a, resili&ecirc;ncia e fallback (requisito 5) podem entrar depois da tag.</li>  
    <li>Nesta tag, o comportamento externo n&atilde;o muda: mesmas rotas, mesmos modos de resposta, su&iacute;te de caracteriza&ccedil;&atilde;o passando sem altera&ccedil;&atilde;o. Mantenha um modelo <code>large</code> por tr&aacute;s de cada capacidade: os dois <code>large</code> s&atilde;o equivalentes e d&atilde;o a mesma sa&iacute;da, mas um <code>mini</code> muda as sa&iacute;das que a su&iacute;te fixou.</li>  
    <li>Me&ccedil;a com o mesmo script e versione <code>metrics/results/v2-decoupled.csv</code> e o gr&aacute;fico</li>  
    <li>Marque o commit com a tag <code>v2-decoupled</code></li>  
</ul>

<h3>5. O AI Gateway</h3>

<p><strong>Por qu&ecirc;.</strong> Na <code>v1</code>, a aplica&ccedil;&atilde;o depende de detalhes concretos e vol&aacute;teis: o provider, o nome do modelo, o formato da API, a credencial. &Eacute; acoplamento no sentido exato do m&oacute;dulo 02, e o gateway &eacute; a invers&atilde;o de depend&ecirc;ncia aplicada &agrave; IA: a aplica&ccedil;&atilde;o passa a pedir uma capacidade, e quem decide o modelo f&iacute;sico &eacute; a infraestrutura. Credencial, custo, limites e resili&ecirc;ncia saem de cada servi&ccedil;o e v&atilde;o para um lugar s&oacute;.</p>

<p><strong>Tarefa.</strong> O gateway roda como servi&ccedil;o <code>gateway</code> no compose, com a configura&ccedil;&atilde;o versionada em <code>gateway/</code>, e entrega:</p>

<ul>  
    <li><strong>Capacidades l&oacute;gicas:</strong> a aplica&ccedil;&atilde;o s&oacute; conhece nomes l&oacute;gicos definidos por voc&ecirc;. Nenhum nome de modelo f&iacute;sico (<code>gpt-fake-\*</code>, <code>claude-fake-\*</code>) aparece em <code>app/</code>.</li>  
    <li><strong>Credenciais fora da aplica&ccedil;&atilde;o:</strong> as chaves dos providers vivem s&oacute; no gateway. A aplica&ccedil;&atilde;o usa uma chave do pr&oacute;prio gateway (virtual key ou equivalente).</li>  
    <li><strong>Troca de modelo por configura&ccedil;&atilde;o:</strong> mudar o modelo f&iacute;sico por tr&aacute;s de uma capacidade exige alterar s&oacute; a configura&ccedil;&atilde;o do gateway e reiniciar s&oacute; o gateway. A aplica&ccedil;&atilde;o n&atilde;o &eacute; reconstru&iacute;da nem reiniciada.</li>  
    <li><strong>Governan&ccedil;a m&iacute;nima:</strong> pelo menos uma chave com or&ccedil;amento (budget) e uma com limite de requisi&ccedil;&otilde;es. Uma requisi&ccedil;&atilde;o fora do limite &eacute; recusada pelo gateway antes de chegar ao provider.</li>  
    <li><strong>Resili&ecirc;ncia:</strong> timeout expl&iacute;cito, retry limitado e com backoff para falhas transit&oacute;rias, e fallback t&eacute;cnico para um destino equivalente em outro provider, para toda capacidade. O n&uacute;mero m&aacute;ximo de tentativas por destino (prim&aacute;rio, fallback t&eacute;cnico e, se houver, modelo fraco) &eacute; declarado no README.</li>  
    <li><strong>Fallback com modelo fraco:</strong> decidido feature por feature. Para cada feature, voc&ecirc; decide se, sem nenhum modelo <code>large</code> dispon&iacute;vel, vale responder com um <code>mini</code> ou falhar explicitamente. Essa decis&atilde;o &eacute; de produto, n&atilde;o s&oacute; de infra, e precisa estar no ADR com a evid&ecirc;ncia que a sustenta.</li>  
</ul>

<p>Cada mecanismo pode morar no gateway ou na aplica&ccedil;&atilde;o, desde que o efeito observ&aacute;vel aconte&ccedil;a e o ADR diga onde ele est&aacute;.</p>

<p>Pistas de ferramenta, para n&atilde;o perder tempo com o que n&atilde;o &eacute; arquitetura: gateways que oferecem chaves virtuais e or&ccedil;amento costumam precisar de um banco de dados, e as chaves precisam ser criadas sem passo manual; o gateway pode n&atilde;o conhecer o pre&ccedil;o dos modelos simulados e, nesse caso, calcula custo zero e o or&ccedil;amento nunca estoura (os pre&ccedil;os est&atilde;o no README do provider); e retries configurados em mais de um lugar (SDK, gateway, aplica&ccedil;&atilde;o) se multiplicam, o que o <code>/admin/calls</code> mostra na hora.</p>

<h3>6. Decidir o fluxo de cada feature (<code>main</code>)</h3>

<p><strong>Por qu&ecirc;.</strong> Uma chamada a LLM n&atilde;o se comporta como uma chamada HTTP comum: demora segundos, custa por token, chega aos poucos e prende conex&otilde;es. Escolher entre s&iacute;ncrono, streaming e ass&iacute;ncrono &eacute; decis&atilde;o arquitetural, e a pergunta certa n&atilde;o &eacute; &quot;qual adotar&quot;, &eacute; &quot;qual para cada caso de uso&quot;. Cada escolha tem custo: o ass&iacute;ncrono ganha capacidade e paga com estado distribu&iacute;do e pe&ccedil;as a operar.</p>

<p><strong>Tarefa.</strong></p>

<ul>  
    <li>Para cada feature, decida o modo de execu&ccedil;&atilde;o a partir das caracter&iacute;sticas do contrato e registre as quatro decis&otilde;es num &uacute;nico ADR de execu&ccedil;&atilde;o, com uma se&ccedil;&atilde;o por feature e a pergunta da &aacute;rvore de decis&atilde;o que sustentou cada uma (&quot;algu&eacute;m est&aacute; esperando agora?&quot;, &quot;cabe no or&ccedil;amento de lat&ecirc;ncia?&quot;, &quot;&eacute; consum&iacute;vel aos poucos?&quot;)</li>  
    <li>Me&ccedil;a a <code>main</code> com o mesmo script e versione <code>metrics/results/main.csv</code> e o gr&aacute;fico</li>  
</ul>

<p>A vers&atilde;o final precisa cumprir os requisitos de experi&ecirc;ncia abaixo, medidos sempre pela borda (<code>localhost:8000</code>). Os limites de tempo valem com o provider simulado no modo normal, salvo quando o item diz outra coisa.</p>

<ul>  
    <li>F1 entrega o resultado completo em at&eacute; 3 s</li>  
    <li>F2 mostra o primeiro trecho do texto da sugest&atilde;o em at&eacute; 1,5 s, e o texto continua chegando at&eacute; completar</li>  
    <li>F3 aceita o pedido do m&ecirc;s inteiro (<code>2026-08-01</code> a <code>2026-08-31</code>) respondendo em at&eacute; 1 s, e o relat&oacute;rio completo, cobrindo os 5.000 tickets, fica dispon&iacute;vel depois para quem pediu</li>  
    <li>Nenhuma requisi&ccedil;&atilde;o, de nenhuma feature, termina em <code>504</code> da borda, inclusive nos cen&aacute;rios de falha do provider descritos nos crit&eacute;rios</li>  
    <li>Se usar streaming: <code>Content-Type: text/event-stream</code>, e um erro no meio do stream chega ao cliente como evento <code>error</code> dentro do pr&oacute;prio stream, no formato de Contratos sugeridos (o status HTTP j&aacute; foi enviado). O modo <code>midstream\_error</code> do provider simulado provoca exatamente essa falha.</li>  
    <li>Se usar Asynchronous Request-Reply: <code>202 Accepted</code> com os headers <code>Location</code> e <code>Retry-After</code>; a URL de status responde <code>200</code> com o estado (<code>pending</code>, <code>running</code> ou <code>failed</code>, este com o motivo) enquanto a tarefa n&atilde;o termina com sucesso, e <code>303 See Other</code> apontando para o resultado quando ela chega a <code>done</code>. Uma tarefa que n&atilde;o consegue terminar chega a <code>failed</code> em at&eacute; 60 s e nunca fica presa em <code>running</code>.</li>  
    <li>Qualquer feature s&iacute;ncrona tem timeout expl&iacute;cito, e nenhuma fica pendurada quando o provider trava: responde com sucesso (via fallback) ou com erro expl&iacute;cito em at&eacute; 15 s</li>  
</ul>

<p>A mudan&ccedil;a de modo de resposta &eacute; uma evolu&ccedil;&atilde;o deliberada do contrato, e por isso acontece depois da tag <code>v2-decoupled</code>. Atualize (ou complemente) os testes na <code>main</code> para o novo contrato. A su&iacute;te de caracteriza&ccedil;&atilde;o nas tags continua sendo o registro do comportamento antigo.</p>

<h3>7. Decis&otilde;es nos tr&ecirc;s n&iacute;veis</h3>

<p><strong>Por qu&ecirc;.</strong> O mesmo termo &quot;arquiteto&quot; muda de significado conforme o n&iacute;vel: corporativa decide qual problema resolver, solu&ccedil;&atilde;o decide como resolver e software decide como construir. Decis&otilde;es de IA caem nos tr&ecirc;s, e localizar cada uma no n&iacute;vel certo diz quem precisa participar dela e quanto tempo ela deve durar.</p>

<p><strong>Tarefa.</strong></p>

<ul>  
    <li>Registre as decis&otilde;es em <code>docs/adr/</code>, um arquivo por decis&atilde;o, com contexto, op&ccedil;&otilde;es consideradas, decis&atilde;o e consequ&ecirc;ncias. Cada ADR tem uma linha <code>N&iacute;vel: corporativa</code>, <code>N&iacute;vel: solu&ccedil;&atilde;o</code> ou <code>N&iacute;vel: software</code>.</li>  
    <li>Os ADRs cobrem no m&iacute;nimo: a escolha e a posi&ccedil;&atilde;o do gateway; as capacidades l&oacute;gicas e o mapeamento para modelos f&iacute;sicos; o modo de execu&ccedil;&atilde;o, num ADR &uacute;nico com uma se&ccedil;&atilde;o por feature; a pol&iacute;tica de fallback (t&eacute;cnico e com modelo fraco), que pode ser um ADR &uacute;nico com uma se&ccedil;&atilde;o por feature; a governan&ccedil;a de chaves, or&ccedil;amentos e limites; a leitura da m&eacute;trica, com as exce&ccedil;&otilde;es declaradas (se houver)</li>  
    <li>H&aacute; pelo menos uma decis&atilde;o em cada um dos tr&ecirc;s n&iacute;veis (ex.: uma pol&iacute;tica de quais providers a empresa aceita, ou um teto de gasto mensal com IA, cabe no n&iacute;vel corporativo)</li>  
</ul>

<hr />

<h2>Restri&ccedil;&otilde;es (n&atilde;o negoci&aacute;veis)</h2>

<ul>  
    <li><code>provider-fake/</code>, <code>edge/</code> e <code>data/</code> n&atilde;o s&atilde;o alterados. As fric&ccedil;&otilde;es s&atilde;o resolvidas na sua aplica&ccedil;&atilde;o, no seu gateway ou no seu compose.</li>  
    <li>Na <code>v2-decoupled</code> e na <code>main</code>, toda chamada a modelo passa pelo gateway. O c&oacute;digo em <code>app/</code> n&atilde;o chama o <code>provider-fake</code> diretamente. Os testes podem usar os endpoints <code>/admin</code>.</li>  
    <li>Na <code>v2-decoupled</code> e na <code>main</code>, as chaves <code>FAKE\_OPENAI\_KEY</code> e <code>FAKE\_ANTHROPIC\_KEY</code> n&atilde;o aparecem em <code>app/</code> nem no ambiente do servi&ccedil;o <code>app</code>.</li>  
    <li>A refatora&ccedil;&atilde;o evolui o c&oacute;digo de <code>app/</code>. Reescrever a aplica&ccedil;&atilde;o do zero, ou em outra linguagem, descaracteriza a entrega.</li>  
    <li>A r&eacute;gua da m&eacute;trica &eacute; a do requisito 3, nas tr&ecirc;s medi&ccedil;&otilde;es. Um script que mede com outra r&eacute;gua invalida a compara&ccedil;&atilde;o.</li>  
    <li>O fluxo do avaliador n&atilde;o depende de provider real nem de qualquer servi&ccedil;o externo al&eacute;m das imagens p&uacute;blicas usadas no compose.</li>  
    <li>Cada servi&ccedil;o que voc&ecirc; adicionar ao compose al&eacute;m de <code>app</code> e <code>gateway</code> (fila, banco, worker) precisa de um ADR que justifique sua exist&ecirc;ncia a partir de um requisito.</li>  
    <li>Se encontrar uma limita&ccedil;&atilde;o real na ferramenta de gateway escolhida, documente-a no ADR e resolva na aplica&ccedil;&atilde;o em vez de desistir do efeito exigido.</li>  
</ul>

<hr />

<h2>Fora de escopo</h2>

<ul>  
    <li>Cache de qualquer tipo, RAG, observabilidade al&eacute;m de logs, evals de qualidade e seguran&ccedil;a (prompt injection, guardrails). S&atilde;o temas dos m&oacute;dulos seguintes e do pr&oacute;ximo desafio.</li>  
    <li>Qualidade do texto gerado e escrita de prompts. O provider &eacute; simulado; o texto do prompt n&atilde;o &eacute; avaliado.</li>  
    <li>Autentica&ccedil;&atilde;o dos usu&aacute;rios do helpdesk, frontend e deploy em nuvem.</li>  
    <li>Sobreviver a um rein&iacute;cio da aplica&ccedil;&atilde;o com tarefas ass&iacute;ncronas em andamento. Se voc&ecirc; persistir estado, &oacute;timo, mas n&atilde;o &eacute; cobrado.</li>  
    <li>Cancelar a gera&ccedil;&atilde;o no provider quando o cliente fecha a conex&atilde;o de streaming.</li>  
    <li>Batch API real dos providers. O provider simulado n&atilde;o a implementa.</li>  
    <li>Deduplicar pedidos repetidos de relat&oacute;rio para o mesmo per&iacute;odo.</li>  
    <li>Circuit breaker. Timeout, retry e fallback s&atilde;o exigidos; circuit breaker n&atilde;o &eacute; cobrado.</li>  
</ul>

<hr />

<h2>Contratos sugeridos</h2>

<p>Os exemplos abaixo s&atilde;o o formato de refer&ecirc;ncia de cada modo e a base dos crit&eacute;rios. Siga-os; se precisar de algum campo adicional, documente no README.</p>

<p><strong>S&iacute;ncrono:</strong></p>

<pre>  
<code>POST /tickets/classification  
{"ticket\_id": "TK-00042", "text": "Meu pedido #481516 n&atilde;o chegou e j&aacute; passou do prazo, urgente"}

200 OK  
{"ticket\_id": "TK-00042", "category": "delivery", "priority": "high"}</code></pre>

<p><strong>Streaming:</strong></p>

<pre>  
<code>POST /tickets/reply-suggestion  
{"ticket\_id": "TK-00042", "text": "Meu pedido #481516 n&atilde;o chegou e j&aacute; passou do prazo, urgente"}

200 OK  
Content-Type: text/event-stream

data: {"chunk": "Ol&aacute;! Sinto muito pelo atraso"}  
data: {"chunk": " na entrega do seu pedido"}  
...  
event: end  
data: {"ticket\_id": "TK-00042"}</code></pre>

<p><strong>Falha no meio do stream</strong> (o status <code>200</code> j&aacute; foi enviado; o stream termina logo depois do evento):</p>

<pre>  
<code>data: {"chunk": "Ol&aacute;! Sinto muito pelo atraso"}  
...  
event: error  
data: {"ticket\_id": "TK-00042", "message": "A gera&ccedil;&atilde;o foi interrompida"}</code></pre>

<p><strong>Ass&iacute;ncrono:</strong></p>

<pre>  
<code>POST /reports/topics  
{"start": "2026-08-01", "end": "2026-08-31"}

202 Accepted  
Location: /reports/topics/status/7f3a  
Retry-After: 5

GET /reports/topics/status/7f3a  
200 OK   {"state": "running", "progress": "1800/5000"}

GET /reports/topics/status/7f3a  
303 See Other  
Location: /reports/topics/7f3a

GET /reports/topics/7f3a  
200 OK   {"start": "2026-08-01", "end": "2026-08-31", "total\_tickets": 5000, "topics": [...]}</code></pre>

<hr />

<h2>Crit&eacute;rios de Aceite</h2>

<p>A entrega &eacute; avaliada contra os crit&eacute;rios abaixo. Todos s&atilde;o obrigat&oacute;rios.</p>

<h3>Diagn&oacute;stico e caracteriza&ccedil;&atilde;o</h3>

<ul>  
    <li>A se&ccedil;&atilde;o &quot;Diagn&oacute;stico da v1&quot; do README registra as quatro dores do cen&aacute;rio, cada uma com o comando executado, o resultado observado e o trecho de <code>app/</code> onde est&aacute; a causa</li>  
    <li>A tag <code>v1-coupled</code> existe no fork, e nela <code>app/</code> &eacute; id&ecirc;ntico ao do reposit&oacute;rio base</li>  
    <li>A su&iacute;te de caracteriza&ccedil;&atilde;o fixa o corpo das respostas das 4 features (n&atilde;o s&oacute; o status), roda com o comando documentado e passa na <code>v1-coupled</code> e na <code>v2-decoupled</code></li>  
    <li><code>git diff v1-coupled v2-decoupled -- tests/characterization/</code> n&atilde;o mostra diferen&ccedil;a</li>  
</ul>

<h3>M&eacute;trica de acoplamento</h3>

<ul>  
    <li><code>metrics/results/</code> cont&eacute;m, para <code>v1-coupled</code>, <code>v2-decoupled</code> e <code>main</code>, um CSV com o cabe&ccedil;alho <code>component,ca,ce,i,a,d</code> e um gr&aacute;fico A &times; I com a Main Sequence</li>  
    <li>Rodar o script da <code>main</code> sobre um checkout da <code>v1-coupled</code> reproduz o CSV versionado para essa tag</li>  
    <li>Os CSVs seguem a r&eacute;gua do requisito 3, e a medi&ccedil;&atilde;o da <code>v1-coupled</code> bate com a recalculada pelo avaliador</li>  
    <li>Na <code>main</code>, nenhum componente est&aacute; na zona de dor (ao mesmo tempo A &lt; 0,5, I &lt; 0,5 e D &ge; 0,5), exceto os declarados no ADR da m&eacute;trica como est&aacute;veis por natureza, com justificativa; o componente que chama o gateway e os componentes das features n&atilde;o podem ser exce&ccedil;&atilde;o</li>  
    <li>Na <code>main</code>, o c&oacute;digo que chama o gateway (SDK ou cliente HTTP) fica em um &uacute;nico componente de <code>app/</code>, identificado no README, e nenhum componente de feature o importa; s&oacute; o ponto de composi&ccedil;&atilde;o da aplica&ccedil;&atilde;o (onde os componentes s&atilde;o montados, ex.: <code>main.py</code>) pode depender dele</li>  
</ul>

<h3>Plano e refatora&ccedil;&atilde;o</h3>

<ul>  
    <li><code>docs/refactoring-plan.md</code> cont&eacute;m os componentes-alvo, a estrat&eacute;gia de cada um, o crit&eacute;rio de pronto, o piloto com medi&ccedil;&atilde;o antes e depois, pelo menos uma revis&atilde;o justificada e o registro do handoff para o agente</li>  
    <li>A tag <code>v2-decoupled</code> existe, e nela a aplica&ccedil;&atilde;o j&aacute; chama os modelos exclusivamente pelo gateway</li>  
</ul>

<h3>Gateway</h3>

<ul>  
    <li><code>grep -rE "gpt-fake|claude-fake" app/</code> n&atilde;o retorna nada na <code>main</code></li>  
    <li><code>grep -rE "FAKE\_OPENAI\_KEY|FAKE\_ANTHROPIC\_KEY|sk-fake-openai|sk-ant-fake" app/</code> n&atilde;o retorna nada, <code>docker compose exec app env</code> n&atilde;o cont&eacute;m as chaves dos providers, e a defini&ccedil;&atilde;o do servi&ccedil;o <code>app</code> em <code>docker compose config</code> n&atilde;o recebe essas chaves por vari&aacute;vel, <code>env\_file</code> ou arquivo montado</li>  
    <li>Seguindo o README, trocar o modelo f&iacute;sico de uma capacidade exige alterar s&oacute; a configura&ccedil;&atilde;o do gateway e reiniciar s&oacute; o servi&ccedil;o <code>gateway</code>; a pr&oacute;xima chamada aparece em <code>/admin/calls</code> com o novo modelo, e o servi&ccedil;o <code>app</code> n&atilde;o foi reiniciado</li>  
    <li>O roteiro de governan&ccedil;a do README, executado como descrito, mostra uma requisi&ccedil;&atilde;o recusada por or&ccedil;amento e outra recusada por limite de requisi&ccedil;&otilde;es, e o n&uacute;mero de chamadas em <code>/admin/calls</code> n&atilde;o aumenta com as requisi&ccedil;&otilde;es recusadas</li>  
    <li>Com o provider prim&aacute;rio de uma capacidade em <code>error\_500</code>, a feature correspondente responde com sucesso, e <code>/admin/calls</code> mostra as tentativas no prim&aacute;rio (no m&aacute;ximo o n&uacute;mero declarado no README) seguidas do sucesso no destino equivalente do outro provider</li>  
    <li>Com os dois modelos <code>large</code> em <code>error\_500</code>, cada uma das 4 features se comporta exatamente como declarado na tabela de fallback do README</li>  
</ul>

<h3>Fluxos de chamada (medidos pela borda, <code>localhost:8000</code>)</h3>

<ul>  
    <li>F1 entrega o resultado completo em at&eacute; 3 s</li>  
    <li><code>curl -N</code> na F2 mostra o primeiro trecho do texto em at&eacute; 1,5 s, e o primeiro trecho chega antes da metade do tempo total da resposta</li>  
    <li>O pedido da F3 para <code>2026-08-01</code> a <code>2026-08-31</code> responde em at&eacute; 1 s, e o relat&oacute;rio obtido depois tem <code>total\_tickets</code> igual a 5000, com as chamadas da tarefa <code>topics</code> que o produziram registradas em <code>/admin/calls</code></li>  
    <li>Com os dois providers inteiros em <code>error\_500</code>, um novo pedido de relat&oacute;rio da F3 chega a um estado de falha vis&iacute;vel ao cliente, com motivo, em at&eacute; 60 s</li>  
    <li>Com o provider prim&aacute;rio da F1 em <code>timeout</code>, a F1 responde (com sucesso via fallback ou com erro expl&iacute;cito) em at&eacute; 15 s</li>  
    <li>Nenhuma das verifica&ccedil;&otilde;es acima produz <code>504</code> da borda</li>  
    <li>Cada modo usado segue o contrato do padr&atilde;o descrito no requisito 6; se a F2 usa streaming, com o provider prim&aacute;rio dela em <code>midstream\_error</code> o cliente recebe um evento <code>error</code> no formato de Contratos sugeridos</li>  
</ul>

<h3>Decis&otilde;es</h3>

<ul>  
    <li><code>docs/adr/</code> cont&eacute;m os ADRs m&iacute;nimos listados no requisito 7, cada um com a linha <code>N&iacute;vel:</code> preenchida</li>  
    <li>Existe pelo menos um ADR em cada n&iacute;vel (corporativa, solu&ccedil;&atilde;o e software)</li>  
    <li>O ADR de fallback traz, para cada feature, a decis&atilde;o sobre o modelo fraco e a evid&ecirc;ncia observada no provider simulado que a sustenta</li>  
    <li>O ADR de execu&ccedil;&atilde;o tem uma se&ccedil;&atilde;o por feature, cada uma citando as caracter&iacute;sticas do contrato que levaram &agrave; decis&atilde;o, e o comportamento implementado bate com ele</li>  
</ul>

<h3>README e consist&ecirc;ncia geral</h3>

<ul>  
    <li>O README cont&eacute;m todas as se&ccedil;&otilde;es listadas em Entreg&aacute;vel</li>  
    <li><code>cp .env.example .env &amp;&amp; docker compose up -d --build --wait</code> na <code>main</code> sobe tudo, e <code>curl -s localhost:8000/health</code> logo em seguida retorna 200, sem passos manuais adicionais</li>  
    <li><code>provider-fake/</code>, <code>edge/</code> e <code>data/</code> n&atilde;o foram alterados</li>  
    <li>Todo servi&ccedil;o do compose al&eacute;m de <code>provider-fake</code>, <code>edge</code>, <code>app</code> e <code>gateway</code> tem um ADR que o justifica a partir de um requisito</li>  
</ul>

<hr />

<h2>Estrutura obrigat&oacute;ria do entreg&aacute;vel</h2>

<pre>  
<code>.  
&#9500;&#9472;&#9472; README.md                      (substitu&iacute;do pelo aluno)  
&#9500;&#9472;&#9472; compose.yaml                   (voc&ecirc; estende)  
&#9500;&#9472;&#9472; .env.example                   (voc&ecirc; estende)  
&#9500;&#9472;&#9472; provider-fake/                 (n&atilde;o alterar)  
&#9500;&#9472;&#9472; edge/                          (n&atilde;o alterar)  
&#9500;&#9472;&#9472; data/  
&#9474;   &#9492;&#9472;&#9472; tickets.jsonl              (n&atilde;o alterar)  
&#9500;&#9472;&#9472; app/                           (entregue; voc&ecirc; evolui) a aplica&ccedil;&atilde;o do helpdesk  
&#9500;&#9472;&#9472; gateway/                       (voc&ecirc; cria) configura&ccedil;&atilde;o do gateway  
&#9500;&#9472;&#9472; tests/  
&#9474;   &#9492;&#9472;&#9472; characterization/          (voc&ecirc; cria)  
&#9500;&#9472;&#9472; metrics/                       (voc&ecirc; cria) o script  
&#9474;   &#9492;&#9472;&#9472; results/                   v1-coupled, v2-decoupled e main (CSV + gr&aacute;fico)  
&#9492;&#9472;&#9472; docs/  
    &#9500;&#9472;&#9472; refactoring-plan.md        (voc&ecirc; cria)  
    &#9492;&#9472;&#9472; adr/                       (voc&ecirc; cria) um arquivo por decis&atilde;o</code></pre>

<p>Outros arquivos que sua solu&ccedil;&atilde;o precisar (Dockerfiles, scripts, testes da <code>main</code>, servi&ccedil;os extras como fila ou banco) podem ficar onde fizer sentido, desde que sejam declarados no compose e no README.</p>

<hr />

<h2>Entreg&aacute;vel</h2>

<p>Voc&ecirc; entrega um link: o seu fork p&uacute;blico no GitHub, com a vers&atilde;o final na branch <code>main</code> e as tags <code>v1-coupled</code> e <code>v2-decoupled</code> publicadas. As tags marcam estados reais da evolu&ccedil;&atilde;o: uma tag sobre um commit que n&atilde;o cumpre o que o requisito dela exige n&atilde;o &eacute; aceita. Dentro do fork, a entrega tem quatro partes.</p>

<p><strong>As decis&otilde;es (documentos):</strong></p>

<ul>  
    <li><code>README.md</code> com o diagn&oacute;stico da aplica&ccedil;&atilde;o recebida e as tabelas das suas decis&otilde;es (se&ccedil;&otilde;es obrigat&oacute;rias listadas abaixo)</li>  
    <li><code>docs/adr/</code>: um arquivo por decis&atilde;o, cada um marcado com o n&iacute;vel (corporativa, solu&ccedil;&atilde;o ou software)</li>  
    <li><code>docs/refactoring-plan.md</code>: o plano, o piloto, a revis&atilde;o do plano e o registro do handoff para o agente de IA</li>  
</ul>

<p><strong>As provas (medi&ccedil;&otilde;es):</strong></p>

<ul>  
    <li><code>metrics/</code>: o script que mede o acoplamento e os resultados das tr&ecirc;s vers&otilde;es (CSV e gr&aacute;fico A &times; I)</li>  
</ul>

<p><strong>A execu&ccedil;&atilde;o (c&oacute;digo e configura&ccedil;&atilde;o):</strong></p>

<ul>  
    <li><code>app/</code>: a aplica&ccedil;&atilde;o recebida, refatorada, chamando os modelos s&oacute; pelo gateway e entregando cada feature no modo que voc&ecirc; decidiu</li>  
    <li><code>gateway/</code>: a configura&ccedil;&atilde;o do gateway (capacidades, fallback, chaves, or&ccedil;amentos e limites)</li>  
    <li><code>compose.yaml</code>: sobe tudo com um &uacute;nico comando</li>  
    <li><code>tests/characterization/</code>: os testes que garantem que a refatora&ccedil;&atilde;o n&atilde;o mudou o comportamento</li>  
</ul>

<p><strong>Os marcos no git:</strong></p>

<ul>  
    <li>tag <code>v1-coupled</code>: a aplica&ccedil;&atilde;o como voc&ecirc; recebeu, mais a su&iacute;te de caracteriza&ccedil;&atilde;o</li>  
    <li>tag <code>v2-decoupled</code>: a aplica&ccedil;&atilde;o refatorada, j&aacute; atr&aacute;s do gateway, com o mesmo comportamento</li>  
    <li>branch <code>main</code>: a vers&atilde;o final, com o modo de execu&ccedil;&atilde;o de cada feature decidido</li>  
</ul>

<p><strong>Como a entrega &eacute; avaliada:</strong> o corretor clona o seu fork, sobe o ambiente com um comando e provoca situa&ccedil;&otilde;es pelo provider simulado. Ele derruba um provider, derruba os modelos bons, troca um modelo e estoura um or&ccedil;amento, e em cada caso confere se o sistema faz exatamente o que os seus ADRs e o seu README dizem. Em resumo: voc&ecirc; entrega as decis&otilde;es, a prova de que elas funcionam e o c&oacute;digo que as executa.</p>

<p><strong>Se&ccedil;&otilde;es obrigat&oacute;rias do README:</strong></p>

<ul>  
    <li><strong>Vis&atilde;o geral:</strong> a solu&ccedil;&atilde;o em 1 a 2 par&aacute;grafos, incluindo como o sistema se comporta quando um provider cai</li>  
    <li><strong>Diagn&oacute;stico da v1:</strong> as quatro dores reproduzidas, com comando, resultado observado e causa no c&oacute;digo</li>  
    <li><strong>Como rodar:</strong> subida, testes de caracteriza&ccedil;&atilde;o e script de m&eacute;trica, com os comandos exatos</li>  
    <li><strong>M&eacute;trica:</strong> a leitura dos tr&ecirc;s gr&aacute;ficos (o que saiu de onde, e por qu&ecirc;) e as exce&ccedil;&otilde;es declaradas</li>  
    <li><strong>Tabela de capacidades:</strong> capacidade l&oacute;gica, feature que a usa, modelo prim&aacute;rio, fallback t&eacute;cnico, pol&iacute;tica com modelo fraco e n&uacute;mero m&aacute;ximo de tentativas por destino</li>  
    <li><strong>Tabela de fallback:</strong> para cada feature, o que acontece quando n&atilde;o h&aacute; modelo <code>large</code> dispon&iacute;vel (qual resposta, qual status)</li>  
    <li><strong>Fluxos:</strong> para cada feature, o modo escolhido e como consumir o resultado, com o <code>curl</code> exato</li>  
    <li><strong>Troca de modelo:</strong> qual arquivo alterar, o que alterar e qual comando executar</li>  
    <li><strong>Roteiro de governan&ccedil;a:</strong> os comandos que demonstram a recusa por or&ccedil;amento e por limite de requisi&ccedil;&otilde;es</li>  
    <li><strong>Mapa de decis&otilde;es:</strong> tabela com cada ADR, seu n&iacute;vel e uma linha de resumo</li>  
</ul>

<hr />

<h2>Ordem de execu&ccedil;&atilde;o sugerida</h2>

<p><strong>1.</strong> Reconhecimento: suba o ambiente, leia o README do provider simulado, leia o c&oacute;digo de <code>app/</code> e <code>edge/nginx.conf</code>, e chame as quatro tarefas nos modelos <code>large</code> e <code>mini</code> direto no provider.</p>

<p><strong>2.</strong> Diagn&oacute;stico: reproduza as quatro dores do cen&aacute;rio com os modos de falha do provider e registre o que observou e onde est&aacute; a causa.</p>

<p><strong>3.</strong> Testes de caracteriza&ccedil;&atilde;o contra a aplica&ccedil;&atilde;o recebida. Marque a tag <code>v1-coupled</code>.</p>

<p><strong>4.</strong> Escreva o script de m&eacute;trica seguindo a r&eacute;gua do requisito 3 e me&ccedil;a a <code>v1</code>.</p>

<p><strong>5.</strong> Escreva o plano, suba o gateway e fa&ccedil;a o piloto em um componente. Me&ccedil;a, revise o plano.</p>

<p><strong>6.</strong> Escale a refatora&ccedil;&atilde;o com o agente, sempre com testes e m&eacute;trica como ju&iacute;zes. Me&ccedil;a, marque a tag <code>v2-decoupled</code>.</p>

<p><strong>7.</strong> Configure governan&ccedil;a e resili&ecirc;ncia no gateway e teste cada modo de falha do provider simulado.</p>

<p><strong>8.</strong> Decida o fluxo de cada feature, implemente, atualize os testes na <code>main</code> e me&ccedil;a a vers&atilde;o final.</p>

<p><strong>9.</strong> Escreva os ADRs e o README. Se um ADR descreve algo que voc&ecirc; n&atilde;o consegue demonstrar pelo <code>/admin/calls</code> ou pela borda, ou o ADR ou o c&oacute;digo est&atilde;o errados.</p>

<p><strong>10.</strong> Fa&ccedil;a a verifica&ccedil;&atilde;o final do zero: num clone limpo do seu fork, suba o ambiente seguindo apenas o seu README e percorra os crit&eacute;rios de aceite item a item.</p>

<hr />

<h2>Dicas finais</h2>

<p>O <code>/admin/calls</code> &eacute; o seu melhor amigo. Toda afirma&ccedil;&atilde;o sobre fallback, retry, troca de modelo ou or&ccedil;amento pode ser conferida nele em segundos. Se voc&ecirc; acha que o fallback funcionou mas o registro mostra uma &uacute;nica chamada ao provider prim&aacute;rio, quem respondeu n&atilde;o foi quem voc&ecirc; pensa.</p>

<p>A r&eacute;gua da m&eacute;trica &eacute; fixa justamente para que ningu&eacute;m ajuste a medida ao resultado. Se o seu script der, para a <code>v1</code>, n&uacute;meros diferentes dos que a defini&ccedil;&atilde;o produz &agrave; m&atilde;o para dois ou tr&ecirc;s m&oacute;dulos, o erro est&aacute; no script. E n&atilde;o desenhe o c&oacute;digo em fun&ccedil;&atilde;o da f&oacute;rmula (ex.: um import s&oacute; para tirar um m&oacute;dulo da zona): a m&eacute;trica aponta onde olhar, e o ADR precisa explicar por que a estrutura ficou melhor.</p>

<p>Streaming s&oacute; funciona se nada no caminho acumular a resposta. Framework, middleware de compress&atilde;o, gateway e proxy podem segurar os trechos e entregar tudo de uma vez no fim; se o <code>curl -N</code> pela borda mostrar o texto chegando em bloco, procure o buffer na sua pr&oacute;pria cadeia, pe&ccedil;a por pe&ccedil;a.</p>

<p>Streaming e ass&iacute;ncrono resolvem problemas diferentes. Streaming muda a espera percebida, mas a conex&atilde;o continua aberta; ass&iacute;ncrono libera a conex&atilde;o, mas cobra estado e mais pe&ccedil;as. Se uma escolha sua resolve o requisito de experi&ecirc;ncia por acidente, o ADR vai denunciar.</p>

<p>Fallback com modelo fraco n&atilde;o &eacute; um checkbox. Antes de ligar, olhe o que o <code>mini</code> devolve em cada tarefa. A pergunta do ADR n&atilde;o &eacute; &quot;o gateway consegue fazer fallback?&quot;, &eacute; &quot;uma resposta pior &eacute; melhor que nenhuma resposta, para quem consome esta feature?&quot;.</p>

<p>Uma boa entrega &eacute; enxuta: cada pe&ccedil;a existe por causa de um requisito, e cada decis&atilde;o tem nome, n&iacute;vel, motivo e prova.</p>