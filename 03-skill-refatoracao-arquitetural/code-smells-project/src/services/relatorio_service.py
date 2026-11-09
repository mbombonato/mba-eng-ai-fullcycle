"""Regras do relatório de vendas (desconto por faixa de faturamento)."""
from ..config.constants import FAIXAS_DESCONTO


def calcular_desconto(faturamento):
    for faturamento_minimo, taxa in FAIXAS_DESCONTO:
        if faturamento > faturamento_minimo:
            return faturamento * taxa
    return 0


class RelatorioService:
    def __init__(self, pedido_model):
        self._pedidos = pedido_model

    def vendas(self):
        totais = self._pedidos.sales_totals()
        total_pedidos = totais["total_pedidos"]
        faturamento = totais["faturamento"]
        desconto = calcular_desconto(faturamento)
        return {
            "total_pedidos": total_pedidos,
            "faturamento_bruto": round(faturamento, 2),
            "desconto_aplicavel": round(desconto, 2),
            "faturamento_liquido": round(faturamento - desconto, 2),
            "pedidos_pendentes": totais["pendentes"],
            "pedidos_aprovados": totais["aprovados"],
            "pedidos_cancelados": totais["cancelados"],
            "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0,
        }
