"""
Compilador Automatizado con PyInstaller — GEM OS Suite
=========================================================
Empaqueta toda la suite dropshipping en un ejecutable .exe para
Windows con configuración avanzada:

  • Entry point Tkinter  →  app/main.py
  • FastAPI dashboard    →  app/services/dashboard_server.py (hidden import)
  • Datos adicionales    →  plantillas config.json y youtube_channels.json (sin BD, sin claves)
  • --noconsole          →  Interfaz limpia sin ventana CMD negra
  • Uvicorn en segundo plano sin ventanas de comando externas
  • Seguridad            →  .env, credenciales, cookies y bases de datos NUNCA van dentro; el build
                            comprueba el resultado con scripts/verificar_dist.py y falla si encuentra alguno.
                            Las claves se piden en Configuración y viven en %APPDATA%\GEM_OS_Suite\.env.

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
    # Automatización, importación y .exe portable
    "app.services.alerts",
    "app.services.daily_brief",
    "app.services.mantenimiento",
    "app.services.metrics_import",
    "app.services.notifier",
    "app.config.secrets_store",
    "app.config.runtime_setup",
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

# Librerías pesadas instaladas en el entorno que la suite NO usa (el bundle pesaba 800 MB por torch)
EXCLUDES = [
    "torch", "torchvision", "torchaudio", "tensorflow", "tensorboard",
    "matplotlib", "IPython", "notebook", "jupyter", "pytest",
]

# Lo que NUNCA debe viajar dentro del .exe: claves, cookies, credenciales y bases de datos
# (las claves se piden en Configuración y se guardan en %APPDATA%\GEM_OS_Suite\.env).
SECRETOS_EN_AI_WORKSPACE = ("google_credentials.json", "skool_cookies.json", ".env")

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


def _preparar_recursos() -> Path:
    """Copia de `ai_workspace` SIN secretos (ni cookies, ni .zip) en build/_recursos.

    PyInstaller empaqueta carpetas enteras; para excluir archivos hay que darle una copia limpia."""
    destino = PROJECT_ROOT / "build" / "_recursos" / "ai_workspace"
    shutil.rmtree(destino.parent, ignore_errors=True)

    def _ignorar(_dir, nombres):
        return [n for n in nombres
                if n in SECRETOS_EN_AI_WORKSPACE or "cookies" in n.lower() or n.endswith(".zip")
                or n == "__pycache__"]

    shutil.copytree(PROJECT_ROOT / "ai_workspace", destino, ignore=_ignorar)
    return destino


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

    for mod in EXCLUDES:
        options.append(f"--exclude-module={mod}")
    _log("✂️", "EXCLUDE", f"{len(EXCLUDES)} librerías pesadas sin uso excluidas")

    # Plantillas JSON en data_template/: runtime_setup las copia a %APPDATA%\GEM_OS_Suite\data en el
    # primer arranque si faltan. NO se empaqueta ninguna base de datos: se crea y migra sola al abrir
    # (tus datos actuales se traen desde Configuración → «Traer mis datos desde…»).
    cfg_included = 0
    for cfg in CONFIG_FILES:
        if Path(cfg).name == "queue_state.json":
            continue      # estado de ejecución: se genera solo
        if _add_data(options, cfg, "data_template", "CFG"):
            cfg_included += 1
    if cfg_included == 0:
        _log("⚠️", "CFG", "No se incluyo ninguna plantilla de configuracion.")

    # Claves: NUNCA dentro del .exe. Solo la plantilla pública, para que sepas qué variables existen.
    if (PROJECT_ROOT / ".env.example").exists():
        options.append(f"--add-data=.env.example{os.pathsep}.")
        _log("🔐", "ENV", ".env NO se incluye; solo .env.example (las claves se piden en Configuración).")

    recursos = _preparar_recursos()
    options.append(f"--add-data={recursos}{os.pathsep}ai_workspace")
    _log("✅", "AI", "ai_workspace incluido SIN credenciales ni cookies")
    _add_data(options, "agent.md", ".", "AGENT")
    _add_data(options, "app/ui/resources", "app/ui/resources", "UI")
    # La web (FastAPI) necesita sus plantillas y estáticos: PyInstaller no los detecta solo
    _add_data(options, "app/templates", "app/templates", "WEB")
    _add_data(options, "app/static", "app/static", "WEB")

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

        # Los datos, logs y copias viven en %APPDATA%\GEM_OS_Suite (ya no se crean carpetas vacías aquí).
        # Comprobación obligatoria: si hay secretos o bases de datos dentro, el build FALLA.
        if not args.onefile:
            verificar = subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts" / "verificar_dist.py"),
                                        str(output_dir)])
            if verificar.returncode != 0:
                _log("❌", "SEGURIDAD", "El resultado contiene secretos o bases de datos. NO lo distribuyas.")
                sys.exit(2)
            _log("🔒", "SEGURIDAD", "Verificado: sin .env, credenciales, cookies ni bases de datos dentro.")

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