#!/usr/bin/env python3
"""Regenera las secciones AUTO del README desde el repo (determinista, sin LLM).

Marcadores en README.md:  <!-- AUTO:nombre -->  ...  <!-- /AUTO:nombre -->
    python scripts/sync_readme.py          # reescribe
    python scripts/sync_readme.py --check  # exit 1 si el README está desfasado
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"


def version() -> str:
    init = (ROOT / "app" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*["\']([^"\']+)', init)
    return f"**Versión de la app:** `{m.group(1)}`" if m else "**Versión de la app:** sin definir"


def _descripcion(md: Path) -> str:
    for linea in md.read_text(encoding="utf-8").splitlines()[1:]:
        linea = linea.strip()
        if linea and not linea.startswith(("#", "-", "`", ">")):
            return re.sub(r"[`|]", "", linea).split(". ")[0][:110].rstrip(".")
    return ""


def skills() -> str:
    comandos = sorted((ROOT / ".claude" / "commands").glob("*.md"))
    filas = ["| Comando | Función |", "|---|---|"]
    filas += [f"| `/{c.stem}` | {_descripcion(c)} |" for c in comandos]
    return f"{len(comandos)} comandos disponibles:\n\n" + "\n".join(filas)


def workflows() -> str:
    filas = ["| Workflow | Disparadores |", "|---|---|"]
    for wf in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        texto = wf.read_text(encoding="utf-8")
        nombre = re.search(r"(?m)^name:\s*(.+)$", texto)
        bloque = re.search(r"(?ms)^on:\s*\n(.*?)(?=^\S)", texto)
        disparadores = re.findall(r"(?m)^  (\w+):", bloque.group(1)) if bloque else []
        filas.append(f"| {nombre.group(1).strip() if nombre else wf.stem} (`{wf.name}`) | {', '.join(disparadores)} |")
    return "\n".join(filas)


def deps() -> str:
    filas = ["| Paquete | Versión fijada |", "|---|---|"]
    for linea in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Za-z0-9_.\-]+)==(\S+)", linea.strip())
        if m:
            filas.append(f"| {m.group(1)} | {m.group(2)} |")
    return "\n".join(filas)


GENERADORES = {"version": version, "skills": skills, "workflows": workflows, "deps": deps}


def renderizar(texto: str) -> str:
    for nombre, fn in GENERADORES.items():
        patron = re.compile(rf"(<!-- AUTO:{nombre} -->)\n.*?(<!-- /AUTO:{nombre} -->)", re.S)
        texto = patron.sub(lambda m: f"{m.group(1)}\n{fn()}\n{m.group(2)}", texto)
    return texto


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    actual = README.read_text(encoding="utf-8")
    nuevo = renderizar(actual)
    if nuevo == actual:
        print("README sincronizado.")
        return 0
    if args.check:
        print("README desfasado: ejecutar python scripts/sync_readme.py", file=sys.stderr)
        return 1
    README.write_text(nuevo, encoding="utf-8")
    print("README actualizado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
