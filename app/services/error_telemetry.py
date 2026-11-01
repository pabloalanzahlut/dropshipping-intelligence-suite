"""
Error Telemetry — Telemetría de Errores Opt-In para GEM OS Suite
==================================================================
Registra errores anónimos localmente con opción de exportar para diagnóstico.
"""

import os
import json
import logging
import platform
import threading
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

TELEMETRY_DIR = Path("logs/telemetry")
TELEMETRY_ENABLED = os.getenv("GEM_OS_TELEMETRY", "false").lower() == "true"


class ErrorTelemetry:
    """Registrador de telemetría de errores opt-in."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        self._enabled = TELEMETRY_ENABLED
        TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._error_count = 0
        logger.info(f"[TELEMETRY] {'Habilitado' if self._enabled else 'Deshabilitado'} (opt-in)")

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self):
        """Activa la telemetría."""
        self._enabled = True
        logger.info("[TELEMETRY] Activado por usuario")

    def disable(self):
        """Desactiva la telemetría."""
        self._enabled = False
        logger.info("[TELEMETRY] Desactivado por usuario")

    def log_error(self, component: str, error: Exception, context: Dict = None):
        """Registra un error anónimo."""
        if not self._enabled:
            return

        self._error_count += 1
        entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self._session_id,
            "component": component,
            "error_type": type(error).__name__,
            "error_msg": str(error)[:200],
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "context": context or {},
        }

        # Guardar en archivo diario
        daily_file = TELEMETRY_DIR / f"errors_{datetime.now().strftime('%Y%m%d')}.jsonl"
        try:
            with open(daily_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"[TELEMETRY] Error guardando telemetría: {e}")

        logger.debug(f"[TELEMETRY] Error registrado: {component} > {type(error).__name__}")

    def get_stats(self) -> Dict:
        """Retorna estadísticas de errores."""
        total_errors = 0
        for f in TELEMETRY_DIR.glob("errors_*.jsonl"):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    total_errors += sum(1 for _ in fh)
            except Exception:
                pass
        return {
            "enabled": self._enabled,
            "session_errors": self._error_count,
            "total_errors_logged": total_errors,
            "session_id": self._session_id,
        }


# Singleton
_telemetry = None


def get_telemetry() -> ErrorTelemetry:
    global _telemetry
    if _telemetry is None:
        _telemetry = ErrorTelemetry()
    return _telemetry