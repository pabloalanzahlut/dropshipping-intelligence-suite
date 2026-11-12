#!/usr/bin/env python3
"""Valida la sintaxis YAML de .github/workflows/*.yml y repara el fallo más común (F-013).

F-013: `name: Texto con: dos puntos` (escalar plano con ': ') -> GitHub marca
'Invalid workflow file' sin generar log. El arreglo es entrecomillar el valor.

Uso:
    python scripts/lint_workflows.py            # exit 1 si hay workflows inválidos
    python scripts/lint_workflows.py --fix      # entrecomilla names problemáticos y revalida
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
NAME_PLANO = re.compile(r"^(\s*(?:-\s+)?name:\s+)(?![\"'|>])(.*\S.*)$")


def validar(texto: str) -> str | None:
    """None si es válido; si no, el mensaje de error. Sin PyYAML no se puede validar."""
    try:
        import yaml
    except ImportError:
        return None
    try:
        yaml.safe_load(texto)
    except yaml.YAMLError as e:
        return str(e).replace("\n", " ")
    return None


def entrecomillar_names(texto: str) -> str:
    """Entrecomilla `name:` cuyo valor plano contiene ': ' o ' #'. Cambia ':' por ';' para no alterar sentido."""
    salida = []
    for linea in texto.split("\n"):
        crlf = linea.endswith("\r")
        base = linea.rstrip("\r")
        m = NAME_PLANO.match(base)
        if m and (": " in m.group(2) or " #" in m.group(2)):
            valor = m.group(2).replace(": ", "; ").replace('"', "'")
            base = f'{m.group(1)}"{valor}"'
        salida.append(base + ("\r" if crlf else ""))
    return "\n".join(salida)


def main(argv: list[str]) -> int:
    corregir = "--fix" in argv
    invalidos = 0
    for wf in sorted(WORKFLOWS.glob("*.yml")):
        texto = wf.read_bytes().decode("utf-8")
        error = validar(texto)
        if error and corregir:
            nuevo = entrecomillar_names(texto)
            if nuevo != texto and validar(nuevo) is None:
                wf.write_bytes(nuevo.encode("utf-8"))
                print(f"REPARADO {wf.relative_to(ROOT).as_posix()} (F-013)")
                continue
        if error:
            invalidos += 1
            print(f"INVALIDO {wf.relative_to(ROOT).as_posix()}: {error[:200]}")
    if not invalidos:
        print("Workflows YAML válidos.")
    return 1 if invalidos else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
