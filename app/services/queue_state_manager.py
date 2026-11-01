"""
QueueStateManager — Persistencia Robusta del Estado de Cola de Videos
=======================================================================
Resiliencia y recuperación ante fallos catastróficos del sistema.

Estados: Pendiente → Procesando → Completado | Fallido
Arquitectura:
  - PathManager.get_paths()['queue'] como ruta única (aislamiento total)
  - Atomic Writes (write → temp → rename) para evitar corrupción
  - Thread-safe mediante threading.Lock
  - Auto-recovery: detecta "Procesando" huérfanos y los revierte a "Pendiente"
"""

import json
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


STATUS_PENDING    = "Pendiente"
STATUS_PROCESSING = "Procesando"
STATUS_COMPLETED  = "Completado"
STATUS_FAILED     = "Fallido"


class QueueStateError(Exception):
    """Excepción base para errores del gestor de cola."""


class QueueStateManager:
    """
    Gestor de persistencia del estado de la cola de videos.
    Características: escritura atómica, thread-safe, auto-recovery.
    """

    def __init__(self, queue_path: Optional[str] = None, auto_recover: bool = True):
        if queue_path is None:
            from app.config.path_manager import PathManager
            queue_path = str(PathManager.get_paths()['queue'])

        self._queue_path: str = queue_path
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {"channels": [], "metadata": {}}
        self._load_or_create()
        if auto_recover:
            self._recover_orphaned_states()

    @property
    def channels(self) -> List[Dict[str, Any]]:
        return self._data.get("channels", [])

    @property
    def queue_path(self) -> str:
        return self._queue_path

    # ── Carga / Creación ─────────────────────────────────────────────────

    def _load_or_create(self) -> None:
        """Carga el estado desde disco o crea estructura por defecto."""
        path = Path(self._queue_path)
        if path.exists() and path.stat().st_size > 0:
            try:
                with open(str(path), "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict) and "channels" in loaded:
                    self._data = loaded
                    if "metadata" not in self._data:
                        self._data["metadata"] = {}
                    self._data["metadata"]["last_load"] = datetime.now(timezone.utc).isoformat()
                    return
            except (json.JSONDecodeError, IOError) as exc:
                print(f"⚠️ [QUEUE] Corrupción en {self._queue_path}: {exc}")
                print("🛠️  [QUEUE] Reconstruyendo estructura...")

        self._data = {
            "channels": [],
            "metadata": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "version": "2.0",
                "last_load": datetime.now(timezone.utc).isoformat(),
                "recovered_from_corruption": path.exists(),
            },
        }
        self._atomic_save()

    def _recover_orphaned_states(self) -> None:
        """Revierte 'Procesando' huérfanos (>5min sin update) a 'Pendiente'."""
        now = datetime.now(timezone.utc)
        recovered = 0
        for channel in self._data.get("channels", []):
            for video in channel.get("videos", []):
                if video.get("status") == STATUS_PROCESSING:
                    ts_str = video.get("timestamp", "")
                    if ts_str:
                        try:
                            ts = datetime.fromisoformat(ts_str)
                            if (now - ts).total_seconds() > 300:
                                video["status"] = STATUS_PENDING
                                video["recovered_at"] = now.isoformat()
                                recovered += 1
                        except (ValueError, TypeError):
                            video["status"] = STATUS_PENDING
                            video["recovered_at"] = now.isoformat()
                            recovered += 1
                    else:
                        video["status"] = STATUS_PENDING
                        video["recovered_at"] = now.isoformat()
                        recovered += 1
        if recovered > 0:
            print(f"🛟 [QUEUE] Recuperados {recovered} estado(s) huérfano(s) → Pendiente")
            self._atomic_save()

    # ── Operaciones de Canales ───────────────────────────────────────────────

    def ensure_channel(self, channel_name: str, channel_url: str) -> None:
        """Asegura que un canal exista. Si no existe, lo agrega con estructura inicial."""
        with self._lock:
            for ch in self._data["channels"]:
                if ch.get("nombre") == channel_name:
                    if ch.get("url") != channel_url:
                        ch["url"] = channel_url
                    return
            self._data["channels"].append({
                "nombre": channel_name,
                "url": channel_url,
                "status": STATUS_PENDING,
                "last_scan": None,
                "total_videos": 0,
                "processed_count": 0,
                "failed_count": 0,
                "videos": [],
            })
            self._data["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
            self._atomic_save()

    def remove_channel(self, channel_name: str) -> bool:
        """Elimina un canal y todos sus videos de la cola."""
        with self._lock:
            before = len(self._data["channels"])
            self._data["channels"] = [
                ch for ch in self._data["channels"]
                if ch.get("nombre") != channel_name
            ]
            if len(self._data["channels"]) < before:
                self._data["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
                self._atomic_save()
                return True
            return False

    # ── Operaciones de Videos ─────────────────────────────────────────────────

    def update_video_status(
        self,
        channel_name: str,
        video_id: str,
        status: str,
        title: str = "",
        error_msg: str = "",
    ) -> None:
        """Actualiza el estado de un video en la cola."""
        if status not in (STATUS_PENDING, STATUS_PROCESSING, STATUS_COMPLETED, STATUS_FAILED):
            raise QueueStateError(f"Estado inválido: {status}")
        with self._lock:
            channel = self._find_channel(channel_name)
            if channel is None:
                print(f"⚠️ [QUEUE] Canal '{channel_name}' no encontrado. Saltando.")
                return
            video = self._find_video(channel, video_id)
            now_iso = datetime.now(timezone.utc).isoformat()
            if video is None:
                channel["videos"].append({
                    "video_id": video_id, "title": title, "status": status,
                    "timestamp": now_iso, "error": error_msg,
                })
                channel["total_videos"] = len(channel["videos"])
            else:
                video["status"] = status
                video["timestamp"] = now_iso
                if title: video["title"] = title
                if error_msg: video["error"] = error_msg
            channel["processed_count"] = sum(
                1 for v in channel["videos"] if v["status"] == STATUS_COMPLETED)
            channel["failed_count"] = sum(
                1 for v in channel["videos"] if v["status"] == STATUS_FAILED)
            total_terminal = channel["processed_count"] + channel["failed_count"]
            if total_terminal == channel["total_videos"] and channel["total_videos"] > 0:
                channel["status"] = STATUS_COMPLETED
                channel["last_scan"] = now_iso
            self._data["metadata"]["last_updated"] = now_iso
            self._atomic_save()

    def mark_channel_scan_started(self, channel_name: str) -> None:
        """Marca el inicio de un escaneo de canal."""
        with self._lock:
            channel = self._find_channel(channel_name)
            if channel:
                channel["status"] = STATUS_PROCESSING
                channel["last_scan"] = datetime.now(timezone.utc).isoformat()
                self._atomic_save()

    def get_channel_summary(self, channel_name: str) -> Dict[str, Any]:
        """Retorna resumen del estado de un canal."""
        with self._lock:
            channel = self._find_channel(channel_name)
            if channel is None:
                return {"exists": False, "nombre": channel_name}
            return {"exists": True, "nombre": channel["nombre"], "url": channel["url"],
                    "status": channel["status"], "total_videos": channel["total_videos"],
                    "processed": channel["processed_count"], "failed": channel["failed_count"],
                    "last_scan": channel["last_scan"]}

    def get_pending_videos(self, channel_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retorna próximos N videos pendientes para procesar."""
        with self._lock:
            channel = self._find_channel(channel_name)
            if channel is None: return []
            return [v for v in channel["videos"] if v["status"] == STATUS_PENDING][:limit]

    def get_all_states(self) -> Dict[str, Any]:
        """Retorna copia completa del estado para dashboard/serialización."""
        with self._lock:
            return {
                "channels": [{"nombre": ch["nombre"], "url": ch["url"], "status": ch["status"],
                              "total_videos": ch["total_videos"], "processed_count": ch["processed_count"],
                              "failed_count": ch["failed_count"], "last_scan": ch["last_scan"],
                              "video_count": len(ch["videos"])} for ch in self._data["channels"]],
                "metadata": dict(self._data.get("metadata", {})),
            }

    def reset_failed_videos(self, channel_name: Optional[str] = None) -> int:
        """Reintenta videos fallidos: los mueve a Pendiente."""
        with self._lock:
            reset_count = 0
            channels = ([ch for ch in self._data["channels"] if ch["nombre"] == channel_name]
                        if channel_name else self._data["channels"])
            for ch in channels:
                for video in ch.get("videos", []):
                    if video["status"] == STATUS_FAILED:
                        video["status"] = STATUS_PENDING
                        video["error"] = ""
                        video["retry_at"] = datetime.now(timezone.utc).isoformat()
                        reset_count += 1
                ch["failed_count"] = 0
            if reset_count > 0:
                self._atomic_save()
            return reset_count

    def reset_all(self) -> None:
        """Reinicia toda la cola (borra progreso). Usar con precaución."""
        with self._lock:
            self._data["channels"] = []
            self._data["metadata"]["reset_at"] = datetime.now(timezone.utc).isoformat()
            self._atomic_save()

    # ── Persistencia Atómica ──────────────────────────────────────────────────

    def _atomic_save(self) -> None:
        """Guardado atómico: escribe a .tmp y renombra. Nunca deja archivo corrupto."""
        temp_path = self._queue_path + ".tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, self._queue_path)
        except (IOError, OSError) as exc:
            raise QueueStateError(f"Error escritura atómica: {exc}") from exc

    def save(self) -> None:
        """Grabación explícita (wrapper público)."""
        with self._lock:
            self._atomic_save()

    # ── Helpers Internos ──────────────────────────────────────────────────────

    def _find_channel(self, name: str) -> Optional[Dict[str, Any]]:
        for ch in self._data["channels"]:
            if ch.get("nombre") == name:
                return ch
        return None

    @staticmethod
    def _find_video(channel: Dict[str, Any], video_id: str) -> Optional[Dict[str, Any]]:
        for v in channel.get("videos", []):
            if v.get("video_id") == video_id:
                return v
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.save()
        return False


# ── Atajo de módulo para carga rápida ─────────────────────────────────────────

def get_queue_manager() -> QueueStateManager:
    """Factory de módulo: crea QueueStateManager con rutas PathManager."""
    return QueueStateManager()