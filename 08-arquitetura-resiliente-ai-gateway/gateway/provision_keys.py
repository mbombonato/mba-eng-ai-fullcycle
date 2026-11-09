"""Cria (ou atualiza) as chaves virtuais do gateway a partir de keys.json.

Roda dentro do container do gateway, logo depois que o LiteLLM sobe. É idempotente:
se a chave já existe no banco, só reaplica modelos, orçamento e limites.
O valor de cada chave vem de uma variável de ambiente (nunca fica no arquivo).
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:4000"
MASTER = os.environ["LITELLM_MASTER_KEY"]
KEYS_FILE = os.path.join(os.path.dirname(__file__), "keys.json")


def call(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method, headers={
        "Authorization": f"Bearer {MASTER}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")


def wait_ready(deadline: float) -> None:
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(BASE + "/health/readiness", timeout=3) as response:
                if json.loads(response.read()).get("db") == "connected":
                    return
        except Exception:
            pass
        time.sleep(1)
    sys.exit("gateway não ficou pronto a tempo")


def main() -> None:
    wait_ready(time.time() + 180)
    for spec in json.load(open(KEYS_FILE, encoding="utf-8")):
        spec = dict(spec)
        spec["key"] = os.environ[spec.pop("key_env")]
        status, info = call("GET", f"/key/info?key={spec['key']}")
        if status == 200:
            status, body = call("POST", "/key/update", spec)
            action = "atualizada"
        else:
            status, body = call("POST", "/key/generate", spec)
            action = "criada"
        if status != 200:
            sys.exit(f"falha ao provisionar {spec['key_alias']}: {status} {body}")
        print(f"chave {spec['key_alias']} {action}", flush=True)


if __name__ == "__main__":
    main()
