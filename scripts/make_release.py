"""
make_release.py — Publicación de GitHub Releases (FASE 6D)
=====================================================================
Automatiza la creación de una release en GitHub con:
  - Notas extraídas automáticamente del CHANGELOG.md (última versión).
  - Adjunto opcional del ejecutable compilado con build_exe.py.

Requisitos previos:
  - CLI de GitHub instalado y autenticado:  `gh auth login`
  - (Opcional) PyInstaller para compilar el .exe.

Uso:
    python scripts/make_release.py                 # release con .exe (onefile)
    python scripts/make_release.py --skip-build    # solo release, sin compilar
    python scripts/make_release.py --tag v1.1.0    # forzar tag concreto
    python scripts/make_release.py --repo owner/repo  # repositorio destino

El comando interno generado es equivalente a:
    gh release create <tag> dist/GEM_OS_Suite.exe --title "..." --notes "..."
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = PROJECT_ROOT / "CHANGELOG.md"


def extract_latest_release() -> dict:
    """Extrae la última sección '## [x.y.z]' del CHANGELOG y sus notas."""
    if not CHANGELOG.exists():
        print("❌ No se encontró CHANGELOG.md en la raíz del proyecto.")
        sys.exit(1)
    text = CHANGELOG.read_text(encoding="utf-8")
    matches = list(re.finditer(r"^## \[([^\]]+)\]\s*—?\s*([\d-]*)", text, re.MULTILINE))
    if not matches:
        print("❌ No hay secciones de versión en el CHANGELOG.")
        sys.exit(1)
    m = matches[0]
    version = m.group(1)
    date = m.group(2).strip()
    start = m.end()
    end = matches[1].start() if len(matches) > 1 else len(text)
    notes = text[start:end].strip()
    return {"version": version, "date": date, "notes": notes}


def ensure_gh() -> None:
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("❌ La CLI 'gh' de GitHub no está instalada o no está en PATH.")
        print("   Instálala desde https://cli.github.com y ejecuta 'gh auth login'.")
        sys.exit(1)


def build_executable() -> Path:
    print("🛠️  Compilando ejecutable con build_exe.py (--onefile)...")
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "build_exe.py"), "--onefile"],
        cwd=PROJECT_ROOT,
        check=True,
    )
    exe = PROJECT_ROOT / "dist" / "GEM_OS_Suite.exe"
    if not exe.exists():
        print("❌ No se generó dist/GEM_OS_Suite.exe")
        sys.exit(1)
    return exe


def create_release(tag: str, title: str, notes: str, assets: list, repo: str) -> None:
    cmd = ["gh", "release", "create", tag]
    if repo:
        cmd.append("--repo")
        cmd.append(repo)
    cmd.append("--title")
    cmd.append(title)
    cmd.append("--notes")
    cmd.append(notes)
    cmd.extend(assets)
    print(f"\n▶ Ejecutando: {' '.join(cmd[:6])} ...")
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
    print(f"\n✅ Release '{tag}' publicada con éxito.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Publica una GitHub Release (FASE 6D)")
    parser.add_argument("--skip-build", action="store_true",
                        help="No compilar el .exe; publicar solo con CHANGELOG.")
    parser.add_argument("--tag", default=None,
                        help="Tag de la release (por defecto v<versión del CHANGELOG>).")
    parser.add_argument("--repo", default=None,
                        help="Repositorio destino owner/repo (por defecto el configurado en gh).")
    parser.add_argument("--extra-assets", nargs="*", default=[],
                        help="Archivos adicionales para adjuntar a la release.")
    args = parser.parse_args()

    ensure_gh()

    release = extract_latest_release()
    version = release["version"]
    tag = args.tag or f"v{version}"
    title = f"GEM OS Suite v{version}"
    if release["date"]:
        title += f" — {release['date']}"
    notes = release["notes"]

    print(f"📦 Versión detectada: v{version}")
    print(f"🏷️  Tag: {tag}")

    assets = []
    if not args.skip_build:
        exe = build_executable()
        assets.append(str(exe))
    assets.extend(args.extra_assets)

    create_release(tag=tag, title=title, notes=notes, assets=assets, repo=args.repo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
