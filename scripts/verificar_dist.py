"""
verificar_dist — comprueba que un .exe recién construido NO lleva secretos ni datos dentro.

Uso:  python scripts/verificar_dist.py [carpeta_dist]        (por defecto dist/GEM_OS_Suite)
Salida: 0 = limpio · 2 = hay secretos o bases de datos · 3 = faltan recursos necesarios

Falla si encuentra, dentro de la carpeta:
  · un `.env` (solo se admite `.env.example`) o cualquier `.env*` con claves
  · `*credentials*.json`, `*cookies*.json`
  · bases de datos (`*.db`, `*.sqlite`, `*.sqlite3`)
  · en archivos de texto pequeños, patrones de claves reales (OpenRouter, Anthropic, Shopify, Google)
Nunca imprime el contenido de nada: solo rutas.
"""
from __future__ import annotations

import fnmatch
import re
import sys
from pathlib import Path
from typing import Dict, List

PROHIBIDOS = ["*credentials*.json", "*cookies*.json", "*.db", "*.sqlite", "*.sqlite3", "*.db-wal", "*.db-shm"]
EXT_TEXTO = {".json", ".txt", ".md", ".py", ".cfg", ".ini", ".yaml", ".yml", ".toml", ".env", ".html", ".js", ".csv"}
MAX_TEXTO = 256 * 1024
PATRONES_CLAVE = [
    re.compile(rb"sk-or-v1-[A-Za-z0-9]{20,}"),
    re.compile(rb"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(rb"shp(?:at|ss|ca|pa)_[A-Fa-f0-9]{20,}"),
    re.compile(rb"AIza[0-9A-Za-z_-]{30,}"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]
NECESARIOS = ["agent.md", "app/templates/base.html", ".env.example"]


def _es_env_prohibido(nombre: str) -> bool:
    n = nombre.lower()
    return (n == ".env" or n.endswith(".env") or (n.startswith(".env.") and n != ".env.example")) and n != ".env.example"


def verificar(dist: Path) -> Dict[str, List[str]]:
    """Devuelve {'prohibidos': [...], 'claves': [...], 'faltan': [...]} con rutas relativas."""
    dist = Path(dist)
    prohibidos: List[str] = []
    claves: List[str] = []
    for ruta in dist.rglob("*"):
        if ruta.is_symlink() or not ruta.is_file():
            continue
        rel = ruta.relative_to(dist).as_posix()
        nombre = ruta.name
        if _es_env_prohibido(nombre) or any(fnmatch.fnmatch(nombre.lower(), p) for p in PROHIBIDOS):
            prohibidos.append(rel)
            continue
        if ruta.suffix.lower() in EXT_TEXTO or nombre.lower().startswith(".env"):
            try:
                if ruta.stat().st_size > MAX_TEXTO:
                    continue
                datos = ruta.read_bytes()
            except OSError:
                continue
            if any(p.search(datos) for p in PATRONES_CLAVE):
                claves.append(rel)
    raices = [dist, dist / "_internal"]
    faltan = [n for n in NECESARIOS if not any((r / n).is_file() for r in raices)]
    return {"prohibidos": sorted(prohibidos), "claves": sorted(claves), "faltan": faltan}


def main(argv: List[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    dist = Path(args[0]) if args else Path("dist") / "GEM_OS_Suite"
    if not dist.is_dir():
        print(f"No existe la carpeta {dist}")
        return 1
    r = verificar(dist)
    for titulo, clave in (("ARCHIVOS PROHIBIDOS", "prohibidos"), ("CLAVES EN TEXTO", "claves"), ("FALTAN RECURSOS", "faltan")):
        if r[clave]:
            print(f"✖ {titulo}:")
            for p in r[clave][:50]:
                print(f"   - {p}")
    if r["prohibidos"] or r["claves"]:
        return 2
    if r["faltan"]:
        return 3
    print(f"✔ {dist}: sin secretos ni bases de datos; recursos necesarios presentes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
