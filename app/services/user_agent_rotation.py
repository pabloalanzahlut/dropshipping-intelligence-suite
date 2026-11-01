"""
UserAgentRotation — Rotación de User-Agents para Evitar Rate Limits
=====================================================================
Pool de 50+ User-Agents reales (Chrome, Firefox, Safari, Edge) con
soporte de cookies.txt opcional.

Modos:
  - 'random': (default) Agente aleatorio del pool cada vez
  - 'sequential': Siguiente en la lista, circular
"""

import os
import random
from typing import Dict, List, Optional


USER_AGENTS_POOL: List[str] = [
    # Chrome 125+ (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Chrome (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Chrome (Linux)
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Firefox 127+ (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Firefox (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6; rv:126.0) Gecko/20100101 Firefox/126.0",
    # Firefox (Linux)
    "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    # Safari macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.2.15 (KHTML, like Gecko) Version/17.4 Safari/605.2.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.2.15 (KHTML, like Gecko) Version/17.3 Safari/605.2.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.2.15 (KHTML, like Gecko) Version/17.2 Safari/605.2.15",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]


class UserAgentRotator:
    """Rotador de User-Agents con soporte para cookies.txt.

    Modos:
      - 'random': (default) Agente aleatorio del pool
      - 'sequential': Siguiente en la lista, circular
    """

    def __init__(self, user_agents: Optional[List[str]] = None,
                 mode: str = "random",
                 cookies_path: Optional[str] = None):
        self._pool = user_agents or USER_AGENTS_POOL
        self._mode = mode
        self._cookies_path = cookies_path
        self._index = random.randint(0, len(self._pool) - 1)

    @property
    def current_user_agent(self) -> str:
        return self._pool[self._index % len(self._pool)]

    @property
    def has_cookies(self) -> bool:
        return bool(self._cookies_path and os.path.exists(self._cookies_path))

    @property
    def cookies_path(self) -> Optional[str]:
        return self._cookies_path

    def rotate(self) -> str:
        """Rota al siguiente User-Agent y lo retorna."""
        if self._mode == "sequential":
            self._index = (self._index + 1) % len(self._pool)
        else:
            self._index = random.randint(0, len(self._pool) - 1)
        return self.current_user_agent

    def get_headers(self) -> Dict[str, str]:
        """Headers HTTP completos con User-Agent rotado."""
        return {
            "User-Agent": self.current_user_agent,
            "Accept": ("text/html,application/xhtml+xml,application/xml;"
                       "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"),
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1", "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        }

    def get_ytdlp_opts(self) -> Dict[str, any]:
        """Opciones para yt-dlp con User-Agent y cookies."""
        opts: Dict[str, any] = {
            "user_agent": self.current_user_agent,
            "quiet": True, "no_warnings": True, "extract_flat": True,
            "http_headers": self.get_headers(),
        }
        if self.has_cookies:
            opts["cookiefile"] = self._cookies_path
        return opts

    def get_ytdlp_cmd_extras(self) -> List[str]:
        """Argumentos extra para CLI de yt-dlp."""
        extras = ["--user-agent", self.current_user_agent,
                   "--add-header", f"Accept:{self.get_headers()['Accept']}",
                   "--add-header", f"Accept-Language:{self.get_headers()['Accept-Language']}"]
        if self.has_cookies:
            extras.extend(["--cookies", self._cookies_path])
        return extras

    @classmethod
    def create_with_pathmanager(
        cls, mode: str = "random", cookies_filename: str = "cookies.txt"
    ) -> "UserAgentRotator":
        """Crea rotador con PathManager. Busca cookies.txt en data/."""
        cookies_path = None
        try:
            from app.config.path_manager import PathManager
            data_dir = PathManager.get_paths()['data']
            cookies_path = str(data_dir / cookies_filename)
        except Exception:
            pass
        return cls(mode=mode, cookies_path=cookies_path)


# ── Singleton global ─────────────────────────────────────────────────────────
_GLOBAL_ROTATOR: Optional[UserAgentRotator] = None


def get_global_rotator() -> UserAgentRotator:
    """Retorna instancia singleton global del rotador."""
    global _GLOBAL_ROTATOR
    if _GLOBAL_ROTATOR is None:
        _GLOBAL_ROTATOR = UserAgentRotator.create_with_pathmanager()
    return _GLOBAL_ROTATOR


def random_user_agent() -> str:
    """Atajo: retorna un User-Agent aleatorio sin crear rotador."""
    return random.choice(USER_AGENTS_POOL)