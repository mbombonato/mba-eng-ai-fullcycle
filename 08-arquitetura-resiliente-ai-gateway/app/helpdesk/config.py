"""Configuração lida do ambiente. Só o ponto de composição (main) a consome.

Nenhum provider, modelo físico ou chave de provider aparece aqui: a aplicação conhece
apenas o endereço do AI Gateway e as chaves virtuais que ele emitiu para ela.
"""

import os

GATEWAY_URL = os.environ["GATEWAY_URL"]
# Chave das features em tempo real (F1, F2, F4) e chave do relatório (F3): ADR 0006.
GATEWAY_REALTIME_KEY = os.environ["GATEWAY_REALTIME_KEY"]
GATEWAY_REPORTS_KEY = os.environ["GATEWAY_REPORTS_KEY"]

# Teto da espera por uma resposta (ou por cada trecho, no streaming) do gateway. Fica acima
# da cadeia primário -> fallback -> fraco do gateway e abaixo dos 15 s exigidos (ADR 0004).
REALTIME_TIMEOUT_SECONDS = float(os.environ.get("REALTIME_TIMEOUT_SECONDS", "12"))
REPORT_CALL_TIMEOUT_SECONDS = float(os.environ.get("REPORT_CALL_TIMEOUT_SECONDS", "50"))

MAX_OUTPUT_TOKENS = 2000

TICKETS_FILE = os.environ.get("TICKETS_FILE", "/data/tickets.jsonl")
TICKETS_PER_CALL = 150
# 34 lotes no mês; 12 em paralelo terminam em ~3 rodadas de ~10 s.
REPORT_CONCURRENCY = int(os.environ.get("REPORT_CONCURRENCY", "12"))
# Uma tarefa que não termina chega a failed antes de 60 s.
REPORT_DEADLINE_SECONDS = float(os.environ.get("REPORT_DEADLINE_SECONDS", "55"))
REPORT_RETRY_AFTER_SECONDS = 5
