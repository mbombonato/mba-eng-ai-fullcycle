"""Mede o acoplamento dos componentes de app/helpdesk (Ca, Ce, I, A, D).

Régua (requisito 3 do desafio):
- componente: cada módulo .py do pacote, inclusive em subpastas, identificado pelo
  caminho com pontos relativo à raiz do pacote (ex.: adapters.gateway); __init__.py não conta;
- dependência: import (relativo ou absoluto) que resolve para outro componente;
  bibliotecas externas e da biblioteca padrão não contam;
- Ca: quantos componentes importam este; Ce: quantos este importa;
- I = Ce / (Ce + Ca), ou 0 quando ambos são zero;
- A = classes abstratas (herdam de typing.Protocol ou abc.ABC) / total de classes, ou 0 sem classes;
- D = |A + I - 1|; tudo arredondado para 2 casas.

Uso:
    python metrics/coupling.py <caminho/para/app/helpdesk> <nome>

Grava metrics/results/<nome>.csv e metrics/results/<nome>.svg (gráfico A x I com a
Main Sequence). Só usa a biblioteca padrão.
"""

import argparse
import ast
import csv
import sys
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"
ABSTRACT_BASES = {"Protocol", "ABC", "typing.Protocol", "abc.ABC", "typing_extensions.Protocol"}


def discover(root: Path) -> dict[str, Path]:
    modules = {}
    for path in sorted(root.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        rel = path.relative_to(root).with_suffix("")
        modules[".".join(rel.parts)] = path
    return modules


def package_of(component: str, path: Path, root: Path) -> list[str]:
    """Partes do pacote que contém o módulo (relativas à raiz)."""
    return list(path.relative_to(root).parent.parts)


def resolve(base: list[str], name: str | None, components: set[str]) -> set[str]:
    """Resolve 'a.b' a partir de um pacote base para componentes existentes."""
    found = set()
    parts = base + (name.split(".") if name else [])
    # import de um módulo ou de um símbolo dentro de um módulo: o prefixo mais longo que é componente
    for size in range(len(parts), 0, -1):
        candidate = ".".join(parts[:size])
        if candidate in components:
            found.add(candidate)
            break
    return found


def dependencies(component: str, path: Path, root: Path, components: set[str]) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    pkg = package_of(component, path, root)
    root_name = root.name
    deps: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] == root_name:
                    deps |= resolve([], ".".join(parts[1:]) or None, components)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = pkg[: len(pkg) - (node.level - 1)] if node.level - 1 <= len(pkg) else []
                module = node.module
            elif node.module and node.module.split(".")[0] == root_name:
                base = []
                module = ".".join(node.module.split(".")[1:]) or None
            else:
                continue
            target = base + (module.split(".") if module else [])
            # "from . import x" / "from .pkg import mod": cada nome pode ser um submódulo
            for alias in node.names:
                as_module = ".".join(target + [alias.name])
                if as_module in components:
                    deps.add(as_module)
                else:
                    deps |= resolve(target, None, components) if target else set()
    deps.discard(component)
    return deps


def base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Subscript):  # Protocol[T]
        node = node.value
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{base_name(node.value)}.{node.attr}"
    return ""


def abstractness(path: Path) -> float:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    if not classes:
        return 0.0
    abstract = sum(1 for c in classes if any(base_name(b) in ABSTRACT_BASES for b in c.bases))
    return abstract / len(classes)


def measure(root: Path) -> list[dict]:
    modules = discover(root)
    names = set(modules)
    efferent = {c: dependencies(c, p, root, names) for c, p in modules.items()}
    afferent = {c: {o for o, deps in efferent.items() if c in deps} for c in modules}
    rows = []
    for c in sorted(modules):
        ca, ce = len(afferent[c]), len(efferent[c])
        i = ce / (ce + ca) if ce + ca else 0.0
        a = abstractness(modules[c])
        d = abs(a + i - 1)
        rows.append({"component": c, "ca": ca, "ce": ce, "i": round(i, 2), "a": round(a, 2), "d": round(d, 2)})
    return rows


def write_csv(rows: list[dict], target: Path) -> None:
    with target.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["component", "ca", "ce", "i", "a", "d"], lineterminator="\n")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: (f"{v:.2f}" if isinstance(v, float) else v) for k, v in r.items()})


def in_pain_zone(r: dict) -> bool:
    return r["a"] < 0.5 and r["i"] < 0.5 and r["d"] >= 0.5


def write_svg(rows: list[dict], name: str, target: Path) -> None:
    size, margin = 520, 70
    span = size - 2 * margin

    def x(i):  # instabilidade no eixo x
        return margin + i * span

    def y(a):  # abstração no eixo y
        return size - margin - a * span

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size + 260}" height="{size}" '
        f'font-family="sans-serif" font-size="11">',
        f'<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{margin}" y="28" font-size="15" font-weight="bold">Main Sequence: {name}</text>',
        # zonas
        f'<polygon points="{x(0)},{y(0)} {x(0.5)},{y(0)} {x(0)},{y(0.5)}" fill="#f8d7da"/>',
        f'<text x="{x(0) + 6}" y="{y(0.3)}" fill="#a33">zona de dor</text>',
        f'<polygon points="{x(1)},{y(1)} {x(0.5)},{y(1)} {x(1)},{y(0.5)}" fill="#fff3cd"/>',
        f'<text x="{x(0.72)}" y="{y(1) + 14}" fill="#963">zona de inutilidade</text>',
        f'<rect x="{x(0)}" y="{y(1)}" width="{span}" height="{span}" fill="none" stroke="#333"/>',
        f'<line x1="{x(0)}" y1="{y(1)}" x2="{x(1)}" y2="{y(0)}" stroke="#2a6" stroke-width="2" '
        f'stroke-dasharray="6 4"/>',
        f'<text x="{x(0.55)}" y="{y(0.5) - 6}" fill="#2a6" transform="rotate(45 {x(0.55)} {y(0.5) - 6})">'
        f'Main Sequence (A + I = 1)</text>',
    ]
    for t in (0, 0.25, 0.5, 0.75, 1):
        out.append(f'<text x="{x(t)}" y="{y(0) + 16}" text-anchor="middle">{t}</text>')
        out.append(f'<text x="{x(0) - 8}" y="{y(t) + 4}" text-anchor="end">{t}</text>')
    out.append(f'<text x="{x(0.5)}" y="{size - 25}" text-anchor="middle">Instabilidade (I)</text>')
    out.append(f'<text x="22" y="{y(0.5)}" text-anchor="middle" transform="rotate(-90 22 {y(0.5)})">'
               f'Abstração (A)</text>')
    # pontos (componentes no mesmo ponto são agrupados num rótulo só)
    groups: dict[tuple, list[str]] = {}
    for r in rows:
        groups.setdefault((r["i"], r["a"]), []).append(r["component"])
    for idx, ((i, a), comps) in enumerate(sorted(groups.items())):
        color = "#c0392b" if any(in_pain_zone(r) for r in rows if r["component"] in comps) else "#1f5fa8"
        out.append(f'<circle cx="{x(i)}" cy="{y(a)}" r="5" fill="{color}"/>')
        out.append(f'<text x="{x(i) + 7}" y="{y(a) - 8 - (idx % 4) * 14}" fill="{color}">'
                   f'{", ".join(comps)}</text>')
    # tabela à direita
    tx = size + 10
    out.append(f'<text x="{tx}" y="60" font-weight="bold">componente  I  A  D</text>')
    for n, r in enumerate(rows):
        color = "#c0392b" if in_pain_zone(r) else "#222"
        out.append(f'<text x="{tx}" y="{78 + n * 15}" fill="{color}">{r["component"]}  '
                   f'{r["i"]:.2f}  {r["a"]:.2f}  {r["d"]:.2f}</text>')
    out.append("</svg>")
    target.write_text("\n".join(out) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path, help="pasta app/helpdesk de qualquer checkout")
    parser.add_argument("name", help="nome da medição (ex.: v1-coupled, v2-decoupled, main)")
    args = parser.parse_args(argv)
    root = args.path.resolve()
    if not root.is_dir():
        parser.error(f"{root} não é uma pasta")
    rows = measure(root)
    RESULTS.mkdir(parents=True, exist_ok=True)
    write_csv(rows, RESULTS / f"{args.name}.csv")
    write_svg(rows, args.name, RESULTS / f"{args.name}.svg")
    for r in rows:
        flag = "  <- zona de dor" if in_pain_zone(r) else ""
        print(f'{r["component"]:<28} ca={r["ca"]} ce={r["ce"]} i={r["i"]:.2f} a={r["a"]:.2f} d={r["d"]:.2f}{flag}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
