"""
path_manager.py — Gestor Centralizado de Rutas con Aislamiento Estricto
=======================================================================
Implementa las 4 metodologías del flujo de skills/agentes:

[METODOLOGÍA 1] Detección y Validación   → _is_executable()
[METODOLOGÍA 2] Resolución de Rutas Base → _get_base_dir(), _get_data_dir()
[METODOLOGÍA 3] Diferenciación de Datos  → _get_runtime_dir(), get_paths()
[METODOLOGÍA 4] Manejo de Errores        → get_paths() con auto-creación

DOS MODOS (el de desarrollo/servidor no cambia):
- Desarrollo / servidor: la raíz es el proyecto y los datos van en ./data/
  (o en GEM_OS_DATA_DIR, p. ej. /var/www/gem_os/data en Linux).
- .exe de PyInstaller (sys.frozen): la raíz es la carpeta de RECURSOS de solo lectura del
  bundle (sys._MEIPASS) y todo lo que se escribe (datos, logs, copias, ai_workspace) va a
  la carpeta del usuario: %APPDATA%\\GEM_OS_Suite\\. Así el .exe funciona desde cualquier
  carpeta o PC y no arrastra bases de datos ni claves dentro del bundle.
  GEM_OS_DATA_DIR sigue mandando sobre la carpeta de datos.
"""

import os
import sys
from pathlib import Path
from typing import Dict


class PathManager:
    """Gestor centralizado de rutas — desarrollo/servidor y .exe."""

    _APP_NAME = "GEM_OS_Suite"

    # ══════════════════════════════════════════════════════════════════
    # [MÉTODO 1] Detección y Validación (REGLA PRINCIPAL)
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _is_executable() -> bool:
        """True cuando corre dentro de un .exe de PyInstaller."""
        return bool(getattr(sys, "frozen", False))

    @staticmethod
    def user_dir() -> Path:
        """Carpeta de escritura del usuario: %APPDATA%\\GEM_OS_Suite (Windows) o ~/.local/share."""
        if os.name == "nt":
            raiz = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        else:
            raiz = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        return Path(raiz) / PathManager._APP_NAME

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
        """Raíz de recursos: el proyecto (3 niveles arriba de app/config/) o, en el .exe,
        la carpeta del bundle (sys._MEIPASS, solo lectura)."""
        if PathManager._is_executable():
            return Path(getattr(sys, "_MEIPASS", None) or Path(sys.executable).parent).resolve()
        return Path(__file__).parent.parent.parent.resolve()

    @staticmethod
    def _get_data_dir() -> Path:
        """
        Carpeta de datos:
        - Si GEM_OS_DATA_DIR está definida → usa esa ruta.
        - En el .exe → <usuario>/data (nunca dentro del bundle).
        - En otro caso → <base>/data/ (desarrollo local).
        """
        env_data = os.environ.get("GEM_OS_DATA_DIR", "").strip()
        if env_data:
            return Path(env_data)
        if PathManager._is_executable():
            return PathManager.user_dir() / "data"
        return PathManager._get_base_dir() / "data"

    # ══════════════════════════════════════════════════════════════
    # [MÉTODO 3] Diferenciación de Datos (AGENTES ENCADENADOS)
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _get_runtime_dir(folder_name: str) -> Path:
        """Directorios runtime (logs, backups, ai_workspace): la raíz del proyecto o, en el .exe,
        la carpeta del usuario (el bundle es de solo lectura)."""
        if PathManager._is_executable():
            return PathManager.user_dir() / folder_name
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

        # En el .exe el bundle (base/recursos) es de solo lectura: solo se crea lo del usuario
        solo_lectura = ("base", "resources") if cls._is_executable() else ()
        cls._ensure_dirs({k: v for k, v in paths.items() if k not in solo_lectura})
        return paths

    @classmethod
    def get_path_strings(cls) -> Dict[str, str]:
        """Versión string de las rutas para compatibilidad legacy."""
        return {key: str(path) for key, path in cls.get_paths().items()}