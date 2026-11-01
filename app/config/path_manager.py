"""
path_manager.py — Gestor Centralizado de Rutas con Aislamiento Estricto
=======================================================================
Implementa las 4 metodologías del flujo de skills/agentes:

[METODOLOGÍA 1] Detección y Validación   → _is_executable()
[METODOLOGÍA 2] Resolución de Rutas Base → _get_base_dir(), _get_data_dir()
[METODOLOGÍA 3] Diferenciación de Datos  → _get_runtime_dir(), get_paths()
[METODOLOGÍA 4] Manejo de Errores        → get_paths() con auto-creación

ENTORNO WEB (FASE 1 — Refactorización Desktop → Plataforma Web):
- Elimina detección PyInstaller y referencias a %APPDATA% de Windows.
- GEM_OS_DATA_DIR (env var) define la ruta de datos en producción Linux
  (ej: /var/www/gem_os/data). Si no está definida, usa ./data/ relativa
  a la raíz del proyecto (comportamiento de desarrollo local).
"""

import os
from pathlib import Path
from typing import Dict


class PathManager:
    """Gestor centralizado de rutas — modo web/servidor Linux."""

    _APP_NAME = "GEM_OS_Suite"

    # ══════════════════════════════════════════════════════════════════
    # [MÉTODO 1] Detección y Validación (REGLA PRINCIPAL)
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _is_executable() -> bool:
        """Siempre False en entorno web/servidor (no hay PyInstaller)."""
        return False

    @staticmethod
    def _verify_structure() -> Dict[str, bool]:
        """Verifica que directorios críticos existan (pre-flight)."""
        paths = PathManager.get_paths()
        return {
            "base_exists": paths['base'].exists(),
            "data_exists": paths['data'].exists(),
            "logs_exists": paths['logs'].exists(),
            "is_executable": PathManager._is_executable(),
            "db_exists": paths['db'].exists(),
        }

    # ══════════════════════════════════════════════════════════════
    # [MÉTODO 2] Resolución de Rutas Base (HERRAMIENTAS)
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _get_base_dir() -> Path:
        """Raíz del proyecto: 3 niveles arriba desde app/config/."""
        return Path(__file__).parent.parent.parent.resolve()

    @staticmethod
    def _get_data_dir() -> Path:
        """
        Carpeta de datos:
        - Si GEM_OS_DATA_DIR está definida → usa esa ruta (producción Linux).
        - En otro caso → <base>/data/ (desarrollo local).
        """
        env_data = os.environ.get("GEM_OS_DATA_DIR", "").strip()
        if env_data:
            return Path(env_data)
        return PathManager._get_base_dir() / "data"

    # ══════════════════════════════════════════════════════════════
    # [MÉTODO 3] Diferenciación de Datos (AGENTES ENCADENADOS)
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _get_runtime_dir(folder_name: str) -> Path:
        """Directorios runtime (logs, backups, ai_workspace) siempre en la raíz del proyecto."""
        return PathManager._get_base_dir() / folder_name

    @staticmethod
    def _ensure_dirs(paths: Dict[str, Path]) -> None:
        """Crea directorios si no existen (idempotente)."""
        for key, path in paths.items():
            if path.suffix:  # Es archivo → crear parent
                path.parent.mkdir(parents=True, exist_ok=True)
            else:  # Es directorio
                path.mkdir(parents=True, exist_ok=True)

    # ══════════════════════════════════════════════════════════════
    # [MÉTODO 4] Pipeline de Rutas Completas (JSON + Auto-creación)
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def get_paths(cls) -> Dict[str, Path]:
        """Retorna todas las rutas y auto-crea los directorios."""
        data_dir = cls._get_data_dir()
        base_dir = cls._get_base_dir()

        paths = {
            'base': base_dir,
            'data': data_dir,
            'db': data_dir / "dropshipping_suite.db",
            'config': data_dir / "youtube_channels.json",
            'queue': data_dir / "queue_state.json",
            'app_config': data_dir / "config.json",
            'logs': cls._get_runtime_dir("logs") / "elite",
            'backups': cls._get_runtime_dir("backups"),
            'ai_workspace': cls._get_runtime_dir("ai_workspace"),
            'skills': cls._get_runtime_dir("ai_workspace") / "skills",
            'memory': cls._get_runtime_dir("ai_workspace") / "memory",
            'projects': cls._get_runtime_dir("ai_workspace") / "projects",
            'context': cls._get_runtime_dir("ai_workspace") / "context",
            'resources': base_dir / "app" / "ui" / "resources",
        }

        cls._ensure_dirs(paths)
        return paths

    @classmethod
    def get_path_strings(cls) -> Dict[str, str]:
        """Versión string de las rutas para compatibilidad legacy."""
        return {key: str(path) for key, path in cls.get_paths().items()}