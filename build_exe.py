"""
Compilador Automatizado con PyInstaller — GEM OS Suite
=========================================================
Empaqueta toda la suite dropshipping en un ejecutable .exe para
Windows con configuración avanzada:

  • Entry point Tkinter  →  app/main.py
  • FastAPI dashboard    →  app/services/dashboard_server.py (hidden import)
  • Datos adicionales    →  config.json, youtube_channels.json, queue_state.json
  • --noconsole          →  Interfaz limpia sin ventana CMD negra
  • Uvicorn en segundo plano sin ventanas de comando externas

Uso:
    python build_exe.py              # Compilación en carpeta (--onedir)
    python build_exe.py --onefile     # Ejecutable único portable
    python build_exe.py --debug       # Conserva artefactos .spec y build/
"""

import os
import sys
import subprocess
import argparse
import shutil
from datetime import datetime
from pathlib import Path

# Forzar UTF-8 en stdout para emojis en Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path.cwd()

ENTRY_POINT = "app/main.py"
ICON_PATH = "app/ui/resources/app_icon.ico"

# Archivos de configuración que deben viajar junto al .exe
# Busca primero en data/ (estructura actual), luego en raíz (legacy)
CONFIG_FILES = [
    "data/config.json",
    "data/youtube_channels.json",
    "data/queue_state.json",
]

# Hidden imports: módulos que PyInstaller no detecta automáticamente
# porque se importan dinámicamente o se lanzan en threads/hilos.
HIDDEN_IMPORTS = [
    # Servicios añadidos en la auditoría de transcripciones (importados desde dashboard_server)
    "app.services.transcript_store",
    "app.services.topic_filter",
    "app.services.agent_router",
    "app.services.channel_store",
    "app.services.kb_maintenance",
    "app.services.product_catalog",
    "app.services.business_metrics",
    "app.services.exports",
    "app.services.log_viewer",
    "app.services.web_auth",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "fastapi",
    "fastapi.routing",
    "fastapi.openapi",
    "starlette",
    "starlette.routing",
    "pydantic",
    "pydantic.json",
    "pydantic.types",
    "youtube_transcript_api",
    "yt_dlp",
    "dotenv",
    "markdown",
    "requests",
    "openai",
    "apscheduler",
    "apscheduler.schedulers.background",
    "apscheduler.triggers.interval",
    "tkinter",
    "tkinter.ttk",
    "tkinter.scrolledtext",
    "xml.etree.ElementTree",
]

# Paquetes de datos que PyInstaller debe escanear en profundidad
COLLECT_ALL = [
    "app.services",
    "app.ui.components",
    "app.database",
    "app.utils",
]

# ---------------------------------------------------------------------------
# Utilidades de ayuda
# ---------------------------------------------------------------------------


def _log(emoji: str, tag: str, message: str) -> None:
    """Imprime un mensaje estructurado con emoji y tag."""
    print(f"{emoji} [{tag}] {message}")


def _add_data(options: list, src: str, dst: str, tag: str) -> bool:
    """Añade un --add-data si el origen existe. Retorna True si se incluyó."""
    src_path = PROJECT_ROOT / src
    if src_path.exists():
        options.append(f"--add-data={src}{os.pathsep}{dst}")
        _log("\u2705", tag, f"Incluido: {src} \u2192 {dst}")
        return True
    return False


def _ensure_build_dir(args) -> None:
    """Limpia artefactos previos si no estamos en modo debug."""
    if not args.debug:
        for folder in ["build", "__pycache__"]:
            shutil.rmtree(PROJECT_ROOT / folder, ignore_errors=True)
        spec_file = PROJECT_ROOT / "GEM_OS_Suite.spec"
        if spec_file.exists():
            spec_file.unlink()


# ---------------------------------------------------------------------------
# Orquestador principal
# ---------------------------------------------------------------------------


def build_executable() -> None:
    """Orquestador de compilación avanzada con PyInstaller."""
    parser = argparse.ArgumentParser(
        description="GEM OS Build Tool - Empaquetado de la Suite"
    )
    parser.add_argument(
        "--onefile", action="store_true",
        help="Generar un unico ejecutable portable (--onefile)"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Conservar artefactos de compilacion (.spec, build/)"
    )
    args = parser.parse_args()

    print()
    _log("🚀", "GEM OS", "Dropshipping Intelligence Suite")
    _log("📦", "BUILD", "PyInstaller Advanced Build")
    print(f"   📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # -- Validacion del Entry Point ------------------------------------------
    entry_path = PROJECT_ROOT / ENTRY_POINT
    if not entry_path.exists():
        _log("❌", "ERROR", f"No se encontro el entry point: {entry_path}")
        print("   Asegurate de ejecutar desde la RAIZ del proyecto.")
        sys.exit(1)

    # -- Construccion de opciones base ---------------------------------------
    options = ["pyinstaller", "--noconfirm"]

    if args.onefile:
        options.append("--onefile")
        _log("📦", "MODE", "Ejecutable UNICO (--onefile)")
    else:
        options.append("--onedir")
        _log("📁", "MODE", "Carpeta con dependencias (--onedir)")

    options.append("--noconsole")
    _log("🪟", "MODE", "Consola oculta (--noconsole)")

    options.append("--name=GEM_OS_Suite")

    for mod in HIDDEN_IMPORTS:
        options.append(f"--hidden-import={mod}")
    _log("🧩", "HIDDEN", f"{len(HIDDEN_IMPORTS)} imports ocultos registrados")

    for pkg in COLLECT_ALL:
        options.append(f"--collect-all={pkg}")
    _log("📚", "COLLECT", f"{len(COLLECT_ALL)} paquetes con collect-all")

    # Incluir plantillas en data_template/ (PathManager las copiará a AppData en 1er inicio)
    _add_data(options, "app/database/dropshipping_suite.db",
              "data_template", "DB")

    cfg_included = 0
    for cfg in CONFIG_FILES:
        if _add_data(options, cfg, "data_template", "CFG"):
            cfg_included += 1
        # Fallback: buscar config en raíz (legacy)
        if cfg_included == 0:
            for cfg in ["config.json", "youtube_channels.json", "queue_state.json"]:
                if _add_data(options, cfg, "data_template", "CFG"):
                    cfg_included += 1
        if cfg_included == 0:
            _log("⚠️", "CFG", "No se incluyo ningun archivo de configuracion.")

    if (PROJECT_ROOT / ".env").exists():
        _add_data(options, ".env", ".", "ENV")
    elif (PROJECT_ROOT / ".env.example").exists():
        options.append("--add-data=.env.example;.env")
        _log("⚠️", "ENV", ".env no encontrado, se uso .env.example como plantilla.")
    else:
        _log("⚠️", "ENV", "No se encontro .env ni .env.example.")

    _add_data(options, "ai_workspace", "ai_workspace", "AI")
    _add_data(options, "app/ui/resources", "app/ui/resources", "UI")
    # La web (FastAPI) necesita sus plantillas y estáticos: PyInstaller no los detecta solo
    _add_data(options, "app/templates", "app/templates", "WEB")
    _add_data(options, "app/static", "app/static", "WEB")
    _add_data(options, "data", "data", "DATA")

    if (PROJECT_ROOT / ICON_PATH).exists():
        options.append(f"--icon={ICON_PATH}")
        _log("✅", "ICON", "Icono personalizado incluido")
    else:
        _log("💡", "ICON", "Sin icono personalizado. Default de Windows.")

    options.append(ENTRY_POINT)

    print()
    _log("🛠️", "BUILD", "Ejecutando PyInstaller...")
    print(f"   {' '.join(options)}")
    print()

    try:
        # Configurar STARTUPINFO para Windows: suprime la ventana CMD negra
        # que algunos subprocesos internos de Uvicorn intentan abrir.
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        subprocess.check_call(options, startupinfo=startupinfo)

        print()
        _log("✅", "SUCCESS", "Compilacion finalizada con exito.")
        print()

        if args.onefile:
            output_dir = PROJECT_ROOT / "dist"
        else:
            output_dir = PROJECT_ROOT / "dist" / "GEM_OS_Suite"

        _log("📁", "OUTPUT", f"Ejecutable en: {output_dir}/")

        if not args.onefile:
            for folder in ["data", "logs", "backups"]:
                folder_path = output_dir / folder
                folder_path.mkdir(parents=True, exist_ok=True)
                _log("📁", "POST", f"Carpeta de datos creada: {folder_path}")

        _ensure_build_dir(args)
        print()

    except subprocess.CalledProcessError as exc:
        print()
        _log("❌", "ERROR", f"Fallo critico en PyInstaller: {exc}")
        print("   Revisa los mensajes de error de PyInstaller mas arriba.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    build_executable()