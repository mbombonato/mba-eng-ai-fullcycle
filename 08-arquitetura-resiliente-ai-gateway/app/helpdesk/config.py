"""Configuração lida do ambiente. Só o ponto de composição (main) a consome.

Nenhum provider, modelo físico ou chave de provider aparece aqui: a aplicação conhece
apenas o endereço do AI Gateway e as chaves virtuais que ele emitiu para ela.
"""

import os

GATEWAY_URL = os.environ["GATEWAY_URL"]
# Chave das features em tempo real (F1, F2, F4) e chave do relatório (F3).
GATEWAY_REALTIME_KEY = os.environ["GATEWAY_REALTIME_KEY"]
GATEWAY_REPORTS_KEY = os.environ["GATEWAY_REPORTS_KEY"]

# Teto de cada chamada ao gateway, abaixo dos 30 s da borda. Nesta versão todas as
# features ainda são síncronas, como na v1 (o modo de execução muda depois da v2).
GATEWAY_TIMEOUT_SECONDS = float(os.environ.get("GATEWAY_TIMEOUT_SECONDS", "28"))

MAX_OUTPUT_TOKENS = 2000

TICKETS_FILE = os.environ.get("TICKETS_FILE", "/data/tickets.jsonl")
TICKETS_PER_CALL = 150
