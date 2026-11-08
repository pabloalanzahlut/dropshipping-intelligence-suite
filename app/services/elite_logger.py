"""
N1 - ELITE LOGGER (Nivel 1: Logging Corporativo)
══════════════════════════════════════════════════
Logging estructurado JSON + correlation IDs + rotación.
Cumple con: Observabilidad & Logging Estructurado (gem-backend.md)
══════════════════════════════════════════════════
"""
import os
import json
import logging
import hashlib
import threading
from datetime import datetime, timezone
from typing import Dict, Optional
from pathlib import Path
from app.config.path_manager import PathManager

# Constantes corporativas usando PathManager
_ELITE_PATHS = PathManager.get_paths()
ELITE_LOG_DIR = _ELITE_PATHS['logs']
ELITE_LOG_FILE = ELITE_LOG_DIR / "elite_suite.log"
ELITE_JSON_LOG = ELITE_LOG_DIR / "elite_suite.jsonl"

# Singleton thread-local para correlation IDs
_local = threading.local()
_local.correlation_id = None


def get_correlation_id() -> str:
    """Obtiene o genera un correlation ID para trazabilidad."""
    if getattr(_local, "correlation_id", None) is None:
        _local.correlation_id = hashlib.sha256(
            f"{datetime.now(timezone.utc).isoformat()}-{threading.get_ident()}".encode()
        ).hexdigest()[:12]
    return _local.correlation_id


def set_correlation_id(cid: str):
    """Fija correlation ID explícito (ej: desde request/transacción)."""
    _local.correlation_id = cid


class EliteJSONFormatter(logging.Formatter):
    """Formatea logs como JSON estructurado con metadata corporativa."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }
        # Agregar extra fields si existen
        if hasattr(record, "extra") and record.extra:
            log_entry.update(record.extra)
        return json.dumps(log_entry, ensure_ascii=False)


class EliteLogger:
    """
    Logger corporativo con salida simultánea:
      - JSON Lines  → elite_suite.jsonl (para ingestion en sistemas)
      - Texto plano → elite_suite.log  (para lectura humana)
      - Consola     → stderr con colores (debug opcional)
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, name: str = "GEM_OS", level: int = logging.INFO, verbose: bool = False):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self.name = name
        self.verbose = verbose
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.propagate = False

        # Asegurar directorio de logs
        ELITE_LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Rotar logs antiguos al iniciar (retención: 30 días)
        try:
            self.rotate_old_logs(days=30)
        except Exception:
            pass

        # Handler JSON (append-only)
        json_handler = logging.FileHandler(str(ELITE_JSON_LOG), encoding="utf-8", mode="a")
        json_handler.setLevel(level)
        json_handler.setFormatter(EliteJSONFormatter())
        self.logger.addHandler(json_handler)

        # Handler texto plano
        txt_handler = logging.FileHandler(str(ELITE_LOG_FILE), encoding="utf-8", mode="a")
        txt_handler.setLevel(level)
        txt_fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        txt_handler.setFormatter(txt_fmt)
        self.logger.addHandler(txt_handler)

        # Handler consola (solo si verbose)
        if verbose:
            console = logging.StreamHandler()
            console.setLevel(level)
            console.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
            )
            self.logger.addHandler(console)

    def info(self, msg: str, **extra):
        self._log(logging.INFO, msg, extra)

    def success(self, msg: str, **extra):
        """Alias para INFO con [OK] visual."""
        self._log(logging.INFO, f"[OK] {msg}", extra)

    def warning(self, msg: str, **extra):
        self._log(logging.WARNING, msg, extra)

    def error(self, msg: str, exc_info: bool = True, **extra):
        self._log(logging.ERROR, msg, extra, exc_info=exc_info)

    def critical(self, msg: str, exc_info: bool = True, **extra):
        self._log(logging.CRITICAL, msg, extra, exc_info=exc_info)

    def _log(self, level: int, msg: str, extra: Dict = None, exc_info: bool = False):
        if extra:
            self.logger.debug(f"_extra:{json.dumps(extra, ensure_ascii=False)}")
        self.logger.log(level, msg, exc_info=exc_info)

    @property
    def log_file(self) -> Path:
        return ELITE_LOG_FILE

    @property
    def json_log_file(self) -> Path:
        return ELITE_JSON_LOG

    @staticmethod
    def rotate_old_logs(days: int = 30, dry_run: bool = False) -> int:
        """
        Rotación de logs antiguos (>days días).
        Comprime logs viejos a .gz y elimina los que excedan retención.

        Args:
            days: Días de retención (default: 30)
            dry_run: Si True, solo muestra qué haría sin ejecutar

        Returns:
            Número de archivos rotados
        """
        import gzip
        import shutil
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(days=days)
        rotated = 0

        for fpath in [ELITE_LOG_FILE, ELITE_JSON_LOG]:
            if not fpath.exists():
                continue
            mtime = datetime.fromtimestamp(fpath.stat().st_mtime)
            if mtime < cutoff:
                if dry_run:
                    logger.info(f"[LOGROTATE] Se rotaría: {fpath.name} ({mtime.date()})")
                    rotated += 1
                    continue
                gz_path = fpath.with_suffix(fpath.suffix + ".gz")
                try:
                    with open(fpath, "rb") as f_in:
                        with gzip.open(gz_path, "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    fpath.write_text("")
                    logger.info(f"[LOGROTATE] Rotado: {fpath.name} -> {gz_path.name}")
                    rotated += 1
                except Exception as e:
                    logger.error(f"[LOGROTATE] Error rotando {fpath.name}: {e}")

        for gz in ELITE_LOG_DIR.glob("*.gz"):
            if datetime.fromtimestamp(gz.stat().st_mtime) < cutoff:
                try:
                    gz.unlink()
                    logger.info(f"[LOGROTATE] Eliminado .gz antiguo: {gz.name}")
                except Exception as e:
                    logger.error(f"[LOGROTATE] Error eliminando {gz.name}: {e}")

        return rotated


# Instancia singleton para import directo
logger = EliteLogger()