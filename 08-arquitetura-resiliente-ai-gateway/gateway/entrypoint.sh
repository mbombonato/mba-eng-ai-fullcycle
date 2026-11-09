#!/bin/sh
# Sobe o LiteLLM Proxy e, quando ele responde, provisiona as chaves virtuais
# declaradas em keys.json (sem passo manual). O healthcheck do serviço só fica
# verde depois que as chaves existem, então a aplicação nunca sobe sem elas.
set -eu

rm -f /tmp/keys-ready
litellm --config /gateway/config.yaml --port 4000 &
PID=$!
trap 'kill -TERM "$PID" 2>/dev/null' TERM INT

python /gateway/provision_keys.py && touch /tmp/keys-ready

wait "$PID"
