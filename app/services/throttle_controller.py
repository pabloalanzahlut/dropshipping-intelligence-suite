"""
ThrottleController — Control de Flujo por Lotes (Rate Limiting)
=================================================================
Limita la ingesta masiva a un Máximo de 10 videos por hora para no
saturar APIs ni violar políticas de YouTube.

Arquitectura:
  - Time-window sliding: seguimiento de slots por hora
  - Política configurable: max_videos_per_hour (default: 10)
  - Thread-safe mediante threading.Lock
  - Persistencia opcional del estado del throttle

Uso:
    throttle = ThrottleController(max_per_hour=10)
    if throttle.can_proceed():
        throttle.register_hit()
        # procesar video...
"""

import json
import os
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional, Any


class ThrottleController:
    """
    Controlador de throttling con ventana deslizante de 1 hora.
    Mantiene un deque de timestamps. Cuando excede max_per_hour, bloquea.
    """

    def __init__(
        self,
        max_per_hour: int = 10,
        window_seconds: int = 3600,
        persist_path: Optional[str] = None,
        auto_persist: bool = True,
    ):
        self.max_per_hour = max_per_hour
        self.window_seconds = window_seconds
        self._persist_path = persist_path
        self._auto_persist = auto_persist
        self._hits: Deque[float] = deque()
        self._lock = threading.Lock()
        self._load_persisted()

    @property
    def hits_in_window(self) -> int:
        self._evict_expired()
        return len(self._hits)

    @property
    def remaining(self) -> int:
        return max(0, self.max_per_hour - self.hits_in_window)

    @property
    def time_until_next_slot(self) -> float:
        """Segundos hasta que se libere el slot más antiguo."""
        with self._lock:
            if len(self._hits) < self.max_per_hour:
                return 0.0
            oldest = self._hits[0]
            return max(0.0, (oldest + self.window_seconds) - time.time())

    def can_proceed(self) -> bool:
        self._evict_expired()
        return len(self._hits) < self.max_per_hour

    def register_hit(self) -> bool:
        """Registra un hit. Retorna False si se excede el límite."""
        self._evict_expired()
        with self._lock:
            if len(self._hits) >= self.max_per_hour:
                return False
            self._hits.append(time.time())
        if self._auto_persist:
            self.persist()
        return True

    def wait_until_available(self, timeout: Optional[float] = None) -> bool:
        """Bloquea hasta que haya slot disponible. Retorna False si timeout."""
        started = time.time()
        while not self.can_proceed():
            if timeout is not None and (time.time() - started) >= timeout:
                return False
            time.sleep(min(self.time_until_next_slot, 5.0))
        return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
        self.persist()

    def _evict_expired(self) -> None:
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            while self._hits and self._hits[0] < cutoff:
                self._hits.popleft()

    def persist(self) -> None:
        if not self._persist_path:
            return
        try:
            tmp_path = self._persist_path + ".tmp"
            with self._lock:
                data = {"max_per_hour": self.max_per_hour,
                        "window_seconds": self.window_seconds,
                        "hits": list(self._hits),
                        "updated_at": datetime.now(timezone.utc).isoformat()}
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, self._persist_path)
        except (IOError, OSError) as exc:
            print(f"⚠️ [THROTTLE] No se pudo persistir: {exc}")

    def _load_persisted(self) -> None:
        if not self._persist_path or not os.path.exists(self._persist_path):
            return
        try:
            with open(self._persist_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            hits = data.get("hits", [])
            now = time.time()
            cutoff = now - self.window_seconds
            with self._lock:
                self._hits.clear()
                self._hits.extend(ts for ts in hits if ts > cutoff)
        except (json.JSONDecodeError, IOError):
            pass


def create_throttle(max_per_hour: int = 10, persist: bool = True) -> ThrottleController:
    """Crea ThrottleController con rutas PathManager."""
    persist_path = None
    if persist:
        from app.config.path_manager import PathManager
        data_dir = PathManager.get_paths()['data']
        persist_path = str(data_dir / "throttle_state.json")
    return ThrottleController(max_per_hour=max_per_hour, persist_path=persist_path)