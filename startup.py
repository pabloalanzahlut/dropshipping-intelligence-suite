"""
startup.py — Arranque multiplataforma de GEM OS (Windows/Linux/macOS)
=====================================================================
Alternativa Python pura a deploy.sh para desarrollo o arranques rápidos.

Uso:
    python startup.py
    python startup.py --port 8080
    python startup.py --reload          # hot-reload para desarrollo
    python startup.py --workers 4       # producción multi-worker

Variables de entorno relevantes:
    GEM_OS_DATA_DIR   — Ruta de datos (default: ./data)
    DASHBOARD_PORT    — Puerto del servidor (default: 8050)
    DISABLE_OLLAMA    — Desactiva capa Ollama (recomendado en servidor)
"""
import argparse
import logging
import os
import sys
from pathlib import Path

# ── Añadir raíz del proyecto al sys.path ─────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# La consola de Windows usa cp1252 y los logs del engine llevan emojis:
# sin esto, print() lanza UnicodeEncodeError y tumba la ingesta al instanciarse.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("gem_os.startup")


def main():
    parser = argparse.ArgumentParser(description="GEM OS — Arranque del servidor web")
    parser.add_argument("--host", default=os.getenv("GEM_OS_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("DASHBOARD_PORT", "47821")))
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--reload", action="store_true", help="Hot-reload (solo desarrollo)")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"])
    args = parser.parse_args()

    # ── Cargar .env si existe ─────────────────────────────────────────────────
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            log.info(f"Configuración cargada desde {env_file}")
        except ImportError:
            log.warning("python-dotenv no instalado. Instala con: pip install python-dotenv")

    # ── Forzar DISABLE_OLLAMA en entorno servidor ────────────────────────────
    if "DISABLE_OLLAMA" not in os.environ:
        os.environ["DISABLE_OLLAMA"] = "true"

    # ── Inicializar paths y BD ────────────────────────────────────────────────
    log.info("Inicializando PathManager y base de datos...")
    from app.config.path_manager import PathManager
    from app.database.connection import DatabaseConnection

    PathManager.get_paths()      # crea directorios necesarios
    DatabaseConnection()         # init schema + migrations idempotentes
    log.info("Base de datos lista.")

    # ── Lanzar uvicorn ────────────────────────────────────────────────────────
    import uvicorn

    log.info(f"Iniciando GEM OS en http://{args.host}:{args.port}")
    uvicorn.run(
        "app.services.dashboard_server:app",
        host=args.host,
        port=args.port,
        workers=args.workers if not args.reload else 1,
        reload=args.reload,
        log_level=args.log_level,
        access_log=True,
    )


if __name__ == "__main__":
    main()
