"""
Multi-User Profiles — Perfiles Multi-Usuario para GEM OS Suite
================================================================
Permite múltiples perfiles con configuraciones, API keys y datos aislados.
"""

import os
import json
import logging
import threading
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

PROFILES_DIR = Path("data/profiles")


class UserProfile:
    """Representa un perfil de usuario con su configuración aislada."""

    def __init__(self, profile_id: str, name: str):
        self.profile_id = profile_id
        self.name = name
        self.created_at = datetime.now().isoformat()
        self.last_login = datetime.now().isoformat()
        self.settings: Dict = {}
        self.api_keys: Dict = {}

    def to_dict(self) -> Dict:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "settings": self.settings,
            "api_keys": {k: v[:8] + "..." if len(v) > 8 else "***" for k, v in self.api_keys.items()},
        }


class ProfileManager:
    """Gestor de perfiles multi-usuario (singleton)."""

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
        self._current_profile: Optional[UserProfile] = None
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        self._load_profiles()

    def _load_profiles(self):
        """Carga la lista de perfiles desde disco."""
        self._profiles: Dict[str, UserProfile] = {}
        for f in PROFILES_DIR.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                profile = UserProfile(data["profile_id"], data["name"])
                profile.created_at = data.get("created_at", "")
                profile.last_login = data.get("last_login", "")
                profile.settings = data.get("settings", {})
                profile.api_keys = data.get("api_keys", {})
                self._profiles[profile.profile_id] = profile
            except Exception as e:
                logger.warning(f"[PROFILES] Error cargando {f.name}: {e}")

    def create_profile(self, name: str) -> UserProfile:
        """Crea un nuevo perfil."""
        import uuid
        profile_id = uuid.uuid4().hex[:12]
        profile = UserProfile(profile_id, name)
        self._profiles[profile_id] = profile
        self._save_profile(profile)
        logger.info(f"[PROFILES] Perfil creado: {name} ({profile_id})")
        return profile

    def switch_profile(self, profile_id: str) -> Optional[UserProfile]:
        """Cambia al perfil especificado."""
        profile = self._profiles.get(profile_id)
        if profile:
            profile.last_login = datetime.now().isoformat()
            self._current_profile = profile
            self._save_profile(profile)
            # Aplicar API keys del perfil al entorno
            for key, value in profile.api_keys.items():
                if value and not value.endswith("..."):
                    os.environ[key] = value
            logger.info(f"[PROFILES] Perfil activo: {profile.name}")
        return profile

    def get_current_profile(self) -> Optional[UserProfile]:
        return self._current_profile

    def list_profiles(self) -> List[Dict]:
        return [p.to_dict() for p in self._profiles.values()]

    def delete_profile(self, profile_id: str) -> bool:
        if profile_id in self._profiles:
            del self._profiles[profile_id]
            path = PROFILES_DIR / f"{profile_id}.json"
            if path.exists():
                path.unlink()
            logger.info(f"[PROFILES] Perfil eliminado: {profile_id}")
            return True
        return False

    def _save_profile(self, profile: UserProfile):
        path = PROFILES_DIR / f"{profile.profile_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)