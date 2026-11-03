"""
TikTokPublisher - Envía guiones a Make.com para auto-publicación en TikTok.
Requiere MAKE_WEBHOOK_TIKTOK en .env.
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class TikTokPublisher:
    """Envía guiones al webhook de Make.com para publicación automática en TikTok."""

    def __init__(self):
        self.webhook_url = os.getenv("MAKE_WEBHOOK_TIKTOK", "").strip()

    def esta_configurado(self) -> bool:
        return bool(self.webhook_url)

    def publicar(self, guion: dict, producto: str, categoria: str) -> dict:
        """
        Envía guión al webhook Make.com.

        Returns:
            {"ok": True, "mensaje": "..."} o {"ok": False, "error": "..."}
        """
        if not self.esta_configurado():
            return {"ok": False, "error": "MAKE_WEBHOOK_TIKTOK no está configurado en .env"}

        payload = {
            "producto": producto,
            "categoria": categoria,
            "patron_hook": guion.get("patron_hook", ""),
            "hook": guion.get("hook", ""),
            "cuerpo": guion.get("cuerpo", ""),
            "cta": guion.get("cta", ""),
            "duracion_segundos": guion.get("duracion_segundos", 0),
            "timestamp": datetime.now().isoformat(),
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                status = resp.status
                body = resp.read().decode("utf-8", errors="ignore")
                if status in (200, 201, 202):
                    return {"ok": True, "mensaje": f"Enviado a Make.com (HTTP {status}): {body[:200]}"}
                return {"ok": False, "error": f"HTTP {status}: {body[:200]}"}
        except urllib.error.URLError as e:
            return {"ok": False, "error": f"Error de red: {e.reason}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
