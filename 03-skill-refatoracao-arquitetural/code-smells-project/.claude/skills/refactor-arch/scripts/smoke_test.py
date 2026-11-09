#!/usr/bin/env python3
"""Smoke test HTTP agnóstico de stack (somente stdlib).

Executa, em ordem, uma lista de requisições descrita em um arquivo JSON e
verifica status code e chaves esperadas no corpo da resposta. Serve para:

  1. Capturar o comportamento ANTES da refatoração (baseline) com --record.
  2. Validar o comportamento DEPOIS da refatoração (Fase 3) contra a mesma spec.

Uso:
    python3 smoke_test.py SPEC.json [--base-url URL] [--record OUT.json] [--wait SEGUNDOS]

Formato da spec:
{
  "base_url": "http://127.0.0.1:5000",
  "requests": [
    {
      "name": "Cria produto",
      "method": "POST",
      "path": "/produtos",
      "headers": {"X-Admin-Token": "{{env:ADMIN_TOKEN}}"},
      "body": {"nome": "Teclado"},
      "expect_status": 201,              # int ou lista de ints
      "expect_keys": ["dados", "sucesso"],  # chaves obrigatórias no JSON (suporta "a.b")
      "forbid_keys": ["senha"],          # chaves que NÃO podem aparecer em nenhum nível
      "capture": {"produto_id": "dados.id"}  # salva valores para usar como {{produto_id}}
    }
  ]
}
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

PLACEHOLDER_ENV = "{{env:"


def render(value, variables):
    """Substitui {{var}} e {{env:NOME}} recursivamente em strings/dicts/listas."""
    if isinstance(value, str):
        while PLACEHOLDER_ENV in value:
            start = value.index(PLACEHOLDER_ENV)
            end = value.index("}}", start)
            name = value[start + len(PLACEHOLDER_ENV):end]
            value = value[:start] + os.environ.get(name, "") + value[end + 2:]
        for key, val in variables.items():
            token = "{{" + key + "}}"
            if value == token:
                return val
            value = value.replace(token, str(val))
        return value
    if isinstance(value, dict):
        return {k: render(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [render(v, variables) for v in value]
    return value


def dig(payload, dotted):
    """Navega em 'a.b.0.c' dentro de dicts/listas. Retorna (encontrado, valor)."""
    current = payload
    for part in dotted.split("."):
        if isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return False, None
    return True, current


def contains_key(payload, key):
    if isinstance(payload, dict):
        return key in payload or any(contains_key(v, key) for v in payload.values())
    if isinstance(payload, list):
        return any(contains_key(v, key) for v in payload)
    return False


def do_request(base_url, method, path, headers, body):
    data = None
    headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode()
        headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(base_url + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status, raw = resp.status, resp.read()
    except urllib.error.HTTPError as err:
        status, raw = err.code, err.read()
    text = raw.decode(errors="replace")
    try:
        return status, json.loads(text)
    except ValueError:
        return status, text


def wait_until_up(base_url, seconds):
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            urllib.request.urlopen(base_url + "/", timeout=2)
            return True
        except urllib.error.HTTPError:
            return True  # respondeu, mesmo que com erro HTTP
        except Exception:
            time.sleep(0.3)
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spec")
    parser.add_argument("--base-url")
    parser.add_argument("--record", help="grava status/corpo de cada requisição (baseline)")
    parser.add_argument("--wait", type=float, default=15, help="segundos aguardando a API subir")
    args = parser.parse_args()

    with open(args.spec, encoding="utf-8") as fh:
        spec = json.load(fh)
    base_url = (args.base_url or spec.get("base_url", "http://127.0.0.1:5000")).rstrip("/")

    if not wait_until_up(base_url, args.wait):
        print(f"✗ API não respondeu em {base_url} após {args.wait}s")
        return 2

    variables, recorded, failures = {}, [], 0
    for item in spec["requests"]:
        name = item.get("name", item["path"])
        method = item.get("method", "GET").upper()
        path = render(item["path"], variables)
        status, payload = do_request(
            base_url, method, path, render(item.get("headers"), variables), render(item.get("body"), variables)
        )
        errors = []
        expected = item.get("expect_status")
        if expected is not None:
            allowed = expected if isinstance(expected, list) else [expected]
            if status not in allowed:
                errors.append(f"status {status} (esperado {allowed})")
        for key in item.get("expect_keys", []):
            if not dig(payload, key)[0]:
                errors.append(f"chave ausente '{key}'")
        for key in item.get("forbid_keys", []):
            if contains_key(payload, key):
                errors.append(f"chave proibida presente '{key}'")
        for var, dotted in (item.get("capture") or {}).items():
            found, value = dig(payload, dotted)
            if found:
                variables[var] = value
            else:
                errors.append(f"não capturou '{dotted}'")

        mark = "✓" if not errors else "✗"
        print(f"  {mark} {method:6} {path:45} -> {status}  {name}" + (f"  [{'; '.join(errors)}]" if errors else ""))
        failures += bool(errors)
        recorded.append({"name": name, "method": method, "path": path, "status": status, "body": payload})

    if args.record:
        with open(args.record, "w", encoding="utf-8") as fh:
            json.dump(recorded, fh, ensure_ascii=False, indent=2)

    total = len(spec["requests"])
    print(f"\n{total - failures}/{total} requisições OK")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
