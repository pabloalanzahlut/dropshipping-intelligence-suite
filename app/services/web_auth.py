"""
web_auth — contraseña de acceso opcional para la web.

Se activa definiendo GEM_OS_PASSWORD en .env (sin contraseña, el servidor solo debe usarse en
127.0.0.1). Sesión por cookie firmada (HMAC-SHA256): HttpOnly, SameSite=Lax, 30 días. Cambiar la
contraseña invalida todas las sesiones. Tras 5 intentos fallidos desde la misma IP se bloquea
1 minuto. No usa dependencias externas.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Dict, Optional, Tuple

COOKIE = "gem_session"
DIAS_SESION = 30
MAX_FALLOS = 5
BLOQUEO_SEGUNDOS = 60

# Rutas sin sesión: el login, los estáticos y los webhooks (que se autentican con su firma HMAC)
RUTAS_LIBRES = ("/login", "/api/login", "/static/", "/webhooks/")

_fallos: Dict[str, Tuple[int, float]] = {}


def password() -> str:
    return os.getenv("GEM_OS_PASSWORD", "")


def activa() -> bool:
    return bool(password())


def _clave() -> bytes:
    return hashlib.sha256(("gemos-session:" + password()).encode("utf-8")).digest()


def crear_token(ahora: Optional[float] = None) -> str:
    expira = int((ahora or time.time()) + DIAS_SESION * 86400)
    firma = hmac.new(_clave(), str(expira).encode(), hashlib.sha256).hexdigest()
    return f"{expira}.{firma}"


def token_valido(token: Optional[str], ahora: Optional[float] = None) -> bool:
    if not token or "." not in token or not activa():
        return False
    expira, _, firma = token.partition(".")
    try:
        if int(expira) < (ahora or time.time()):
            return False
    except ValueError:
        return False
    esperada = hmac.new(_clave(), expira.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(firma, esperada)


def password_correcta(intento: str) -> bool:
    return activa() and hmac.compare_digest((intento or "").encode("utf-8"), password().encode("utf-8"))


def bloqueado(ip: str, ahora: Optional[float] = None) -> int:
    """Segundos de bloqueo restantes para esa IP (0 = puede intentarlo)."""
    n, hasta = _fallos.get(ip, (0, 0.0))
    resto = int(hasta - (ahora or time.time()))
    return resto if n >= MAX_FALLOS and resto > 0 else 0


def registrar_fallo(ip: str, ahora: Optional[float] = None) -> None:
    ahora = ahora or time.time()
    n, hasta = _fallos.get(ip, (0, 0.0))
    if n >= MAX_FALLOS and hasta <= ahora:      # el bloqueo ya expiró: empezar de cero
        n = 0
    n += 1
    _fallos[ip] = (n, ahora + BLOQUEO_SEGUNDOS if n >= MAX_FALLOS else hasta)


def limpiar_fallos(ip: str) -> None:
    _fallos.pop(ip, None)


def es_libre(ruta: str) -> bool:
    return ruta == "/login" or any(ruta.startswith(r) for r in RUTAS_LIBRES)
