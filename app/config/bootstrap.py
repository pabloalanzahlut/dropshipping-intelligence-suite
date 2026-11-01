"""
bootstrap.py — Inicialización del Sistema GEM OS Suite
========================================================
[METODOLOGÍA 4] Manejo de Errores y Fallbacks

Responsabilidades:
1. Inicializar PathManager y verificar estructura
2. Copiar plantillas seed al directorio data/ (si es primera vez)
3. Verificar integridad de archivos críticos
4. Limpiar rutas legacy (opcional)
"""

import sys
import shutil
from pathlib import Path
from typing import Dict, Optional

from app.config.path_manager import PathManager


def initialize_app_environment() -> Dict[str, bool]:
    """
    Inicializa el entorno de la aplicación.

    Pipeline:
    1. Detecta contexto (dev/executable)
    2. Verifica estructura de directorios
    3. Despliega plantillas seed si es primera ejecución
    4. Retorna estado de inicialización

    Returns:
        dict: Estado de cada paso de inicialización
    """
    status = {
        "context_detected": False,
        "paths_initialized": False,
        "seed_deployed": False,
        "structure_verified": False,
    }

    # 1. Detectar contexto
    is_exe = PathManager._is_executable()
    status["context_detected"] = True
    context = "EXECUTABLE" if is_exe else "DEVELOPMENT"

    # 2. Inicializar paths (auto-crea directorios)
    paths = PathManager.get_paths()
    status["paths_initialized"] = all(
        paths[k].exists() or paths[k].parent.exists()
        for k in ["data", "logs", "backups"]
    )

    # 3. Desplegar plantillas seed si es primera ejecución
    status["seed_deployed"] = _deploy_seed_templates(paths)

    # 4. Verificar estructura final
    structure = PathManager._verify_structure()
    status["structure_verified"] = all(structure.values())

    _log_summary(context, paths, status)
    return status


def _deploy_seed_templates(paths: Dict[str, Path]) -> bool:
    """
    Despliega archivos seed (plantillas) desde el bundle al data/ del usuario.
    Solo se ejecuta en producción (.exe) y solo si los archivos no existen.
    """
    if not PathManager._is_executable():
        return True  # En desarrollo, los archivos ya existen

    deployed = False
    meipass_dir = None

    try:
        # sys._MEIPASS es el directorio temporal donde PyInstaller extrae los datos
        meipass_dir = Path(sys._MEIPASS)
    except AttributeError:
        return True  # No estamos empaquetados

    if not meipass_dir or not meipass_dir.exists():
        return True

    # Mapeo de plantillas empaquetadas → destino en AppData
    templates = [
        ("data_template/dropshipping_suite.db", paths['db']),
        ("data_template/youtube_channels.json", paths['config']),
        ("data_template/config.json", paths['app_config']),
    ]

    for src_rel, dst in templates:
        src = meipass_dir / src_rel
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
            deployed = True

    return deployed


def cleanup_legacy_paths() -> int:
    """
    Limpia archivos legacy de ubicaciones antiguas.
    Opcional: migra datos de app/database/ a data/.
    Returns:
        int: Número de archivos migrados/limpiados
    """
    base_dir = PathManager._get_base_dir()
    data_dir = PathManager._get_data_dir()
    cleaned = 0

    # Legacy: app/database/dropshipping_suite.db → data/
    legacy_db = base_dir / "app" / "database" / "dropshipping_suite.db"
    new_db = data_dir / "dropshipping_suite.db"

    if legacy_db.exists() and not new_db.exists():
        new_db.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(legacy_db), str(new_db))
        cleaned += 1

    # Legacy: queue_state.json en raíz → data/
    legacy_queue = base_dir / "queue_state.json"
    new_queue = data_dir / "queue_state.json"
    if legacy_queue.exists() and not new_queue.exists():
        shutil.copy2(str(legacy_queue), str(new_queue))
        cleaned += 1

    return cleaned


def bootstrap_system() -> Dict:
    """
    Función principal de bootstrap. Se llama al iniciar la app.
    Retorna un resumen completo de inicialización.

    Returns:
        dict: Resumen completo del bootstrap
    """
    import time
    from app.config.path_manager import PathManager

    start = time.time()

    env_status = initialize_app_environment()
    legacy_count = cleanup_legacy_paths()
    paths = PathManager.get_paths()
    structure = PathManager._verify_structure()

    # ── Health-check de Ollama (capa 3 del enrutador híbrido) ──
    ollama_ok = False
    try:
        from app.core.ollama_startup_engine import OllamaStartupEngine
        ollama_ok = OllamaStartupEngine.launch_local_ollama_silently()
    except Exception:
        ollama_ok = False

    elapsed = time.time() - start

    return {
        "status": "OK" if env_status["structure_verified"] else "WARNING",
        "context": "EXECUTABLE" if PathManager._is_executable() else "DEVELOPMENT",
        "base_dir": str(paths['base']),
        "data_dir": str(paths['data']),
        "db_path": str(paths['db']),
        "legacy_migrated": legacy_count,
        "structure": structure,
        "ollama_available": ollama_ok,
        "elapsed_ms": round(elapsed * 1000, 2),
    }


def _log_summary(context: str, paths: Dict[str, Path], status: Dict[str, bool]) -> None:
    """Imprime resumen de inicialización."""
    print(f"\n{'='*60}")
    print(f"  GEM OS Suite — Bootstrap")
    print(f"  Contexto: {context}")
    print(f"  Base:     {paths['base']}")
    print(f"  Data:     {paths['data']}")
    print(f"  Logs:     {paths['logs']}")
    print(f"{'='*60}")
    for key, ok in status.items():
        icon = "✅" if ok else "❌"
        print(f"  {icon} {key}: {ok}")
    print(f"{'='*60}\n")