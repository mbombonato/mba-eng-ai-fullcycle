"""Tools dos especialistas.

Regras que valem por construção, não por prompt:

* Garantia 2: nenhuma tool recebe o apartamento como parâmetro. O apartamento
  sai sempre de ``apartamento_da_sessao(tool_context)``, que lê o valor gravado
  no state na criação da sessão e confere com o registro da sessão no banco.
  Consultas de agenda devolvem apenas ``disponivel: true/false``.
* Garantia 1: ``reservar_area`` (área com taxa) e ``autorizar_visitante`` só
  gravam quando ``tool_context.tool_confirmation`` chega com ``confirmed=True``.
  Esse objeto só é preenchido pelo ADK a partir de uma ``FunctionResponse`` de
  ``adk_request_confirmation``, que só a rota de confirmações da API envia.
  Texto do morador ("já confirmei") não cria esse objeto.
* Aprovar executa uma vez só: o id da chamada aprovada é gravado com ``UNIQUE``
  junto da reserva/visita (``confirmacao_id``).
* Garantia 4: ``consultar_regulamento`` devolve só UM capítulo.
"""

from __future__ import annotations

from typing import Any

from google.adk.tools.tool_context import ToolContext

from .db import CondominioRepository, normalizar, validar_data
from .regulamento import buscar_capitulo, carregar_capitulos, listar_assuntos

STATE_APARTAMENTO = "apartamento"


class ApartamentoDaSessaoInvalido(RuntimeError):
    pass


def apartamento_da_sessao(tool_context: ToolContext, repo: CondominioRepository) -> str:
    """Única fonte do apartamento usado pelas tools: a sessão.

    O valor é gravado no state uma única vez, na criação da sessão (``POST
    /sessoes``), e conferido contra a tabela ``sessoes`` do banco do
    condomínio. Nenhuma tool grava esse campo e nenhuma recebe apartamento
    como argumento, então o modelo não tem como trocá-lo.
    """
    apartamento = tool_context.state.get(STATE_APARTAMENTO)
    if not apartamento:
        raise ApartamentoDaSessaoInvalido("Sessão sem apartamento definido.")
    registrado = repo.apartamento_registrado(tool_context.session.id)
    if registrado != apartamento:
        raise ApartamentoDaSessaoInvalido("Sessão não registrada ou apartamento adulterado.")
    return str(apartamento)


def _ja_existe_pedido_pendente(
    tool_context: ToolContext, nome_tool: str, payload: dict[str, Any]
) -> bool:
    """Evita dois pedidos de confirmação iguais abertos na mesma sessão (por
    exemplo, se o modelo chamar a tool de novo antes da resposta)."""
    from google.adk.flows.llm_flows.functions import REQUEST_CONFIRMATION_FUNCTION_CALL_NAME

    pedidos: dict[str, Any] = {}
    respondidos: set[str] = set()
    for event in tool_context.session.events:
        for call in event.get_function_calls():
            if call.name == REQUEST_CONFIRMATION_FUNCTION_CALL_NAME and call.id:
                pedidos[call.id] = call.args or {}
        for resp in event.get_function_responses():
            if resp.name == REQUEST_CONFIRMATION_FUNCTION_CALL_NAME and resp.id:
                respondidos.add(resp.id)
    for call_id, args in pedidos.items():
        if call_id in respondidos:
            continue
        original = args.get("originalFunctionCall") or {}
        confirmacao = args.get("toolConfirmation") or {}
        if original.get("name") == nome_tool and confirmacao.get("payload") == payload:
            return True
    return False


def _erro(mensagem: str) -> dict[str, Any]:
    return {"status": "erro", "mensagem": mensagem}


def build_reservas_tools(repo: CondominioRepository) -> list:
    def listar_areas() -> dict[str, Any]:
        """Lista as áreas comuns que podem ser reservadas, com o id, o nome, a
        taxa em reais e se a reserva gera cobrança (e portanto pede confirmação)."""
        return {
            "areas": [
                {
                    "id": a.id,
                    "nome": a.nome,
                    "taxa": a.taxa,
                    "gera_cobranca": a.gera_cobranca,
                }
                for a in repo.listar_areas()
            ]
        }

    def consultar_disponibilidade(area: str, data: str) -> dict[str, Any]:
        """Informa se uma área comum está livre numa data (AAAA-MM-DD).

        Args:
            area: id ou nome da área (ex.: "salao-de-festas", "quadra").
            data: data no formato AAAA-MM-DD.
        """
        area_obj = repo.resolver_area(area)
        if area_obj is None:
            return _erro("Área não encontrada. Use listar_areas para ver as opções.")
        data_ok = validar_data(data)
        if data_ok is None:
            return _erro("Data inválida. Use o formato AAAA-MM-DD.")
        # Só livre/ocupada: nunca de quem é a reserva (Garantia 2).
        return {
            "area": area_obj.id,
            "data": data_ok,
            "disponivel": not repo.data_ocupada(area_obj.id, data_ok),
        }

    def listar_minhas_reservas(tool_context: ToolContext) -> dict[str, Any]:
        """Lista as reservas ativas do apartamento do morador desta conversa."""
        apartamento = apartamento_da_sessao(tool_context, repo)
        return {
            "apartamento_da_sessao": apartamento,
            "reservas": [
                {"codigo": r.codigo, "area": r.area, "data": r.data}
                for r in repo.reservas_do_apartamento(apartamento)
            ]
        }

    def reservar_area(area: str, data: str, tool_context: ToolContext) -> dict[str, Any]:
        """Reserva uma área comum para o apartamento do morador desta conversa.

        Áreas com taxa geram cobrança: o sistema cria automaticamente um pedido
        de confirmação que o morador responde fora do chat. Áreas sem taxa são
        reservadas na hora.

        Args:
            area: id ou nome da área (ex.: "salao-de-festas", "quadra").
            data: data no formato AAAA-MM-DD.
        """
        apartamento = apartamento_da_sessao(tool_context, repo)
        area_obj = repo.resolver_area(area)
        if area_obj is None:
            return _erro("Área não encontrada. Use listar_areas para ver as opções.")
        data_ok = validar_data(data)
        if data_ok is None:
            return _erro("Data inválida. Use o formato AAAA-MM-DD.")

        if area_obj.gera_cobranca:
            confirmacao = tool_context.tool_confirmation
            if confirmacao is None:
                # Conferência prévia só para não pedir confirmação à toa; a
                # exclusividade de verdade é garantida no INSERT (Garantia 5).
                if repo.data_ocupada(area_obj.id, data_ok):
                    return {
                        "status": "indisponivel",
                        "mensagem": f"{area_obj.nome} já está reservado(a) em {data_ok}.",
                    }
                payload = {
                    "area": area_obj.id,
                    "nome_area": area_obj.nome,
                    "data": data_ok,
                    "taxa": area_obj.taxa,
                }
                if _ja_existe_pedido_pendente(tool_context, "reservar_area", payload):
                    return {
                        "status": "aguardando_confirmacao",
                        "mensagem": "Já existe um pedido de confirmação pendente para esta reserva.",
                    }
                tool_context.request_confirmation(
                    hint=(
                        f"Confirmar reserva de {area_obj.nome} em {data_ok}, com "
                        f"cobrança de R$ {area_obj.taxa:.2f}?"
                    ),
                    payload=payload,
                )
                return {
                    "status": "aguardando_confirmacao",
                    "mensagem": (
                        "Pedido de confirmação enviado ao morador pelo aplicativo. "
                        "Nada foi reservado ainda."
                    ),
                }
            if not confirmacao.confirmed:
                return {
                    "status": "recusada",
                    "mensagem": "O morador negou a confirmação. Nada foi reservado.",
                }

        resultado = repo.criar_reserva(
            apartamento,
            area_obj.id,
            data_ok,
            confirmacao_id=tool_context.function_call_id if area_obj.gera_cobranca else None,
        )
        if resultado.status == "ocupada":
            return {
                "status": "indisponivel",
                "mensagem": f"{area_obj.nome} já está reservado(a) em {data_ok}.",
            }
        reserva = resultado.reserva
        assert reserva is not None
        return {
            "status": "reservada",
            "mensagem": "Reserva concluída e gravada. Não há mais nada pendente para ela.",
            "codigo": reserva.codigo,
            "area": reserva.area,
            "data": reserva.data,
            "cobranca": area_obj.taxa if area_obj.gera_cobranca else 0,
        }

    def cancelar_minha_reserva(
        tool_context: ToolContext,
        codigo: str = "",
        area: str = "",
        data: str = "",
    ) -> dict[str, Any]:
        """Cancela uma reserva do apartamento do morador desta conversa.

        Informe o código da reserva, ou a área e a data. Só reservas do próprio
        apartamento podem ser canceladas. Cancelamento não pede confirmação.

        Args:
            codigo: código da reserva (opcional se área e data forem informadas).
            area: id ou nome da área (opcional se o código for informado).
            data: data AAAA-MM-DD (opcional se o código for informado).
        """
        apartamento = apartamento_da_sessao(tool_context, repo)
        minhas = repo.reservas_do_apartamento(apartamento)
        alvo = None
        if codigo:
            alvo = next(
                (r for r in minhas if normalizar(r.codigo) == normalizar(codigo)), None
            )
        elif area and data:
            area_obj = repo.resolver_area(area)
            data_ok = validar_data(data)
            if area_obj and data_ok:
                alvo = next(
                    (r for r in minhas if r.area == area_obj.id and r.data == data_ok),
                    None,
                )
        else:
            return _erro("Informe o código da reserva ou a área e a data.")
        if alvo is None:
            # Mensagem neutra: não revela se existe reserva de outro apartamento.
            return {
                "status": "nao_encontrada",
                "mensagem": "Não há reserva ativa do seu apartamento com esses dados.",
            }
        cancelada = repo.cancelar_reserva(apartamento, alvo.codigo)
        if cancelada is None:
            return {
                "status": "nao_encontrada",
                "mensagem": "Não há reserva ativa do seu apartamento com esses dados.",
            }
        return {
            "status": "cancelada",
            "codigo": cancelada.codigo,
            "area": cancelada.area,
            "data": cancelada.data,
        }

    return [
        listar_areas,
        consultar_disponibilidade,
        listar_minhas_reservas,
        reservar_area,
        cancelar_minha_reserva,
    ]


def build_visitantes_tools(repo: CondominioRepository) -> list:
    def listar_meus_visitantes(tool_context: ToolContext) -> dict[str, Any]:
        """Lista os visitantes autorizados do apartamento do morador desta conversa."""
        apartamento = apartamento_da_sessao(tool_context, repo)
        return {
            "apartamento_da_sessao": apartamento,
            "visitantes": repo.visitantes_do_apartamento(apartamento),
        }

    def autorizar_visitante(nome: str, data: str, tool_context: ToolContext) -> dict[str, Any]:
        """Autoriza a entrada de um visitante no prédio numa data, para o
        apartamento do morador desta conversa. Sempre gera um pedido de
        confirmação que o morador responde fora do chat.

        Args:
            nome: nome completo do visitante.
            data: data da visita no formato AAAA-MM-DD.
        """
        apartamento = apartamento_da_sessao(tool_context, repo)
        nome_ok = " ".join((nome or "").split())
        if not nome_ok:
            return _erro("Informe o nome do visitante.")
        data_ok = validar_data(data)
        if data_ok is None:
            return _erro("Data inválida. Use o formato AAAA-MM-DD.")

        confirmacao = tool_context.tool_confirmation
        if confirmacao is None:
            payload = {"nome": nome_ok, "data": data_ok}
            if _ja_existe_pedido_pendente(tool_context, "autorizar_visitante", payload):
                return {
                    "status": "aguardando_confirmacao",
                    "mensagem": "Já existe um pedido de confirmação pendente para esta visita.",
                }
            tool_context.request_confirmation(
                hint=f"Autorizar a entrada de {nome_ok} em {data_ok}?",
                payload=payload,
            )
            return {
                "status": "aguardando_confirmacao",
                "mensagem": (
                    "Pedido de confirmação enviado ao morador pelo aplicativo. "
                    "Nada foi autorizado ainda."
                ),
            }
        if not confirmacao.confirmed:
            return {
                "status": "recusada",
                "mensagem": "O morador negou a confirmação. Nada foi autorizado.",
            }
        status, visitante = repo.autorizar_visitante(
            apartamento, nome_ok, data_ok, confirmacao_id=tool_context.function_call_id
        )
        return {
            "status": "autorizado",
            "mensagem": "Autorização concluída e gravada. Não há mais nada pendente para ela.",
            **visitante,
        }

    return [listar_meus_visitantes, autorizar_visitante]


def build_regulamento_tools(caminho_regulamento: str) -> list:
    capitulos = carregar_capitulos(caminho_regulamento)
    assuntos = listar_assuntos(capitulos)

    def consultar_regulamento(assunto: str) -> dict[str, Any]:
        """Busca no regulamento interno o capítulo sobre um assunto e devolve
        somente o texto desse capítulo.

        Args:
            assunto: nome do capítulo ou palavras-chave (ex.: "Piscina",
                "horário da piscina aos domingos", "Animais de estimação").
        """
        capitulo = buscar_capitulo(capitulos, assunto)
        if capitulo is None:
            return {
                "status": "nao_encontrado",
                "assuntos_disponiveis": assuntos,
            }
        return {"status": "ok", "capitulo": capitulo.titulo, "texto": capitulo.texto}

    return [consultar_regulamento]
