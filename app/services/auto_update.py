"""
AutoUpdateChecker — Mecanismo de Auto-Update vía GitHub Releases
=================================================================
GEM OS Suite — Dropshipping Intelligence Suite

Verifica periódicamente si hay nuevas versiones en GitHub Releases
y permite descargar la actualización.

Configuración vía .env:
    GEM_OS_REPO=tu_usuario/tu_repo  (ej: "alan/gem-os-suite")
    GEM_OS_UPDATE_INTERVAL_HOURS=24
"""

import os
import json
import logging
import threading
import requests
from typing import Optional, Dict
from datetime import datetime, timedelta
from pathlib import Path
from packaging.version import Version, InvalidVersion

logger = logging.getLogger(__name__)

# Constantes
GEM_OS_VERSION = "2.0.0"
GEM_OS_REPO = os.getenv("GEM_OS_REPO", "")
UPDATE_INTERVAL = int(os.getenv("GEM_OS_UPDATE_INTERVAL_HOURS", "24"))


class AutoUpdateChecker:
    """
    Verificador de actualizaciones vía GitHub Releases API.

    Uso:
        checker = AutoUpdateChecker()
        if checker.check_for_updates():
            print(f"Nueva versión: {checker.latest_version}")
            checker.download_update()
    """

    def __init__(self, repo: str = ""):
        self.repo = repo or GEM_OS_REPO
        self.latest_version: Optional[str] = None
        self.download_url: Optional[str] = None
        self.release_notes: Optional[str] = None
        self._last_check: Optional[datetime] = None
        self._state_file = Path("data/update_check_state.json")

    def check_for_updates(self, force: bool = False) -> bool:
        """
        Verifica si hay una nueva versión disponible.

        Args:
            force: Si True, ignora el intervalo de caché

        Returns:
            True si hay actualización disponible
        """
        if not self.repo:
            logger.info("[UPDATE] No hay repositorio configurado (GEM_OS_REPO)")
            return False

        if not force and self._last_check:
            elapsed = datetime.now() - self._last_check
            if elapsed < timedelta(hours=UPDATE_INTERVAL):
                logger.debug(f"[UPDATE] Última verificación hace {elapsed.seconds//3600}h, saltando.")
                return self.latest_version is not None

        try:
            url = f"https://api.github.com/repos/{self.repo}/releases/latest"
            headers = {"Accept": "application/vnd.github.v3+json"}
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            latest = data.get("tag_name", "").lstrip("v")
            self.latest_version = latest
            self.download_url = self._find_asset(data)
            self.release_notes = data.get("body", "")[:500]
            self._last_check = datetime.now()

            # Comparar versiones
            try:
                current = Version(GEM_OS_VERSION)
                available = Version(latest)
                has_update = available > current
            except InvalidVersion:
                has_update = latest != GEM_OS_VERSION

            if has_update:
                logger.info(f"[UPDATE] Nueva versión disponible: v{latest} (actual: v{GEM_OS_VERSION})")
            else:
                logger.info(f"[UPDATE] Sin actualizaciones. Última: v{latest}")

            self._save_state()
            return has_update

        except requests.RequestException as e:
            logger.warning(f"[UPDATE] Error verificando actualizaciones: {e}")
            return False
        except (KeyError, json.JSONDecodeError) as e:
            logger.warning(f"[UPDATE] Error parseando respuesta: {e}")
            return False

    def download_update(self, target_dir: Optional[str] = None) -> Optional[str]:
        """
        Descarga la última versión del ejecutable.

        Args:
            target_dir: Directorio destino (default: dist/)

        Returns:
            Ruta al archivo descargado, o None si falla
        """
        if not self.download_url:
            logger.warning("[UPDATE] No hay URL de descarga disponible.")
            return None

        target = Path(target_dir or "dist")
        target.mkdir(parents=True, exist_ok=True)
        local_path = target / f"GEM_OS_Suite_v{self.latest_version}.exe"

        try:
            logger.info(f"[UPDATE] Descargando v{self.latest_version}...")
            resp = requests.get(self.download_url, stream=True, timeout=120)
            resp.raise_for_status()

            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(local_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = downloaded / total * 100
                        if pct % 25 == 0:
                            logger.info(f"[UPDATE] Descargado {pct:.0f}%")

            logger.info(f"[UPDATE] Descarga completa: {local_path} ({downloaded/1024/1024:.1f} MB)")
            return str(local_path)

        except Exception as e:
            logger.error(f"[UPDATE] Error descargando actualización: {e}")
            if local_path.exists():
                local_path.unlink()
            return None

    def get_current_version(self) -> str:
        """Retorna la versión actual del software."""
        return GEM_OS_VERSION

    def _find_asset(self, release_data: Dict) -> Optional[str]:
        """Encuentra el asset .exe en los datos del release."""
        for asset in release_data.get("assets", []):
            name = asset.get("name", "")
            if name.endswith(".exe") and "GEM_OS" in name:
                return asset.get("browser_download_url")
        # Fallback: primer .exe
        for asset in release_data.get("assets", []):
            if asset.get("name", "").endswith(".exe"):
                return asset.get("browser_download_url")
        return None

    def _save_state(self):
        """Persiste el estado de la última verificación."""
        try:
            state = {
                "last_check": self._last_check.isoformat() if self._last_check else None,
                "latest_version": self.latest_version,
                "current_version": GEM_OS_VERSION,
            }
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"[UPDATE] Error guardando estado: {e}")

    def _load_state(self):
        """Carga el estado persistido."""
        if not self._state_file.exists():
            return
        try:
            with open(self._state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            if state.get("last_check"):
                self._last_check = datetime.fromisoformat(state["last_check"])
            self.latest_version = state.get("latest_version")
        except Exception as e:
            logger.warning(f"[UPDATE] Error cargando estado: {e}")


# Instancia singleton
_updater = None
_updater_lock = threading.Lock()


def get_updater() -> AutoUpdateChecker:
    """Singleton del verificador de actualizaciones."""
    global _updater
    if _updater is None:
        with _updater_lock:
            if _updater is None:
                _updater = AutoUpdateChecker()
    return _updater