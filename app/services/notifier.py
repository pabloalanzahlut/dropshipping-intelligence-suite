"""
notifier — avisos fuera de la app para las alertas del centro de alertas.

Dos canales, ambos opcionales y sin dependencias nuevas:
  · Notificación de Windows (toast): al hacer clic abre el panel en la página de la alerta.
  · Webhook de Make.com (`MAKE_WEBHOOK_ALERTAS`): ahí montas el email, Telegram o WhatsApp que quieras.

Reglas (para no convertirse en ruido):
  · Solo se avisa de alertas de nivel `GEM_OS_AVISOS_NIVEL` o superior (por defecto «aviso»).
  · Una alerta se avisa UNA vez; si reaparece o sube de nivel, otra vez. Las críticas que siguen
    sin verse se recuerdan cada 12 h.
  · Horas de silencio (`GEM_OS_AVISOS_SILENCIO`, por defecto 23-7): ahí solo pasan las críticas;
    el resto espera a la mañana.
  · `GEM_OS_AVISOS=0` lo apaga todo. Solo avisa el proceso del servidor (no la app de escritorio),
    para no duplicar avisos.
  · Nunca se registra la URL del webhook (es un secreto).
"""
from __future__ import annotations

import base64
import logging
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from app.services.alerts import NIVELES

log = logging.getLogger(__name__)

RECORDATORIO_CRITICAS_H = 12
MAX_TOASTS = 3
_AUMID_POWERSHELL = r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"

_PS_TOAST = r"""
$ErrorActionPreference = 'Stop'
[void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
[void][Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime]
$t = [Security.SecurityElement]::Escape($env:GEM_TITULO)
$d = [Security.SecurityElement]::Escape($env:GEM_TEXTO)
$u = [Security.SecurityElement]::Escape($env:GEM_URL)
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml("<toast activationType='protocol' launch='$u'><visual><binding template='ToastGeneric'><text>$t</text><text>$d</text></binding></visual></toast>")
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($env:GEM_AUMID).Show($toast)
"""


# ── configuración ────────────────────────────────────────────────────────────

def _env(nombre: str, defecto: str = "") -> str:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    return (os.getenv(nombre) or defecto).strip()


def configuracion() -> Dict[str, Any]:
    """Estado de los canales para mostrarlo en la interfaz (nunca devuelve la URL)."""
    habilitado = _env("GEM_OS_AVISOS", "1") != "0"
    url = _env("MAKE_WEBHOOK_ALERTAS")
    nivel = _env("GEM_OS_AVISOS_NIVEL", "aviso").lower()
    ini, fin = _silencio()
    return {
        "habilitado": habilitado,
        "nivel_minimo": nivel if nivel in NIVELES else "aviso",
        "silencio": f"{ini:02d}-{fin:02d}" if ini != fin else "sin silencio",
        "windows": {"disponible": sys.platform == "win32", "activo": habilitado and sys.platform == "win32"},
        "make": {"configurado": _webhook_valido(url), "activo": habilitado and _webhook_valido(url)},
    }


def _webhook_valido(url: str) -> bool:
    p = urlparse(url or "")
    return p.scheme == "https" and bool(p.netloc)


def _silencio() -> Tuple[int, int]:
    """Horas de silencio «23-7» → (23, 7). Mismo valor en ambos extremos = sin silencio."""
    try:
        a, b = _env("GEM_OS_AVISOS_SILENCIO", "23-7").split("-")
        return int(a) % 24, int(b) % 24
    except ValueError:
        return 23, 7


def en_silencio(ahora: Optional[datetime] = None) -> bool:
    ini, fin = _silencio()
    h = (ahora or datetime.now()).hour
    if ini == fin:
        return False
    return (h >= ini or h < fin) if ini > fin else (ini <= h < fin)


# ── canales ──────────────────────────────────────────────────────────────────

def _url_panel(enlace: str = "") -> str:
    puerto = _env("DASHBOARD_PORT", "47821") or "47821"
    return f"http://127.0.0.1:{puerto}{enlace if enlace.startswith('/') else '/'}"


def enviar_toast(titulo: str, texto: str, enlace: str = "") -> Dict[str, Any]:
    """Notificación nativa de Windows (PowerShell 5.1 + WinRT; sin instalar nada)."""
    if sys.platform != "win32":
        return {"ok": False, "motivo": "solo en Windows"}
    env = {**os.environ, "GEM_TITULO": titulo[:120], "GEM_TEXTO": texto[:300],
           "GEM_URL": _url_panel(enlace), "GEM_AUMID": _AUMID_POWERSHELL}
    codificado = base64.b64encode(_PS_TOAST.encode("utf-16-le")).decode("ascii")
    try:
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
             "-EncodedCommand", codificado],
            env=env, capture_output=True, text=True, timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "motivo": str(exc)[:120]}
    if r.returncode != 0:
        return {"ok": False, "motivo": (r.stderr or r.stdout or "error desconocido").strip()[:160]}
    return {"ok": True}


def enviar_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST JSON al webhook de Make. Éxito = respuesta 2xx. No se registra la URL."""
    url = _env("MAKE_WEBHOOK_ALERTAS")
    if not _webhook_valido(url):
        return {"ok": False, "motivo": "MAKE_WEBHOOK_ALERTAS no está definida (o no es https)"}
    try:
        import requests
        r = requests.post(url, json=payload, timeout=10, allow_redirects=False)
    except Exception as exc:
        return {"ok": False, "motivo": f"{type(exc).__name__}"}
    if 200 <= r.status_code < 300:
        return {"ok": True}
    return {"ok": False, "motivo": f"HTTP {r.status_code}"}


def _payload(alertas: List[Dict[str, Any]]) -> Dict[str, Any]:
    marca = {"critico": "CRÍTICA", "aviso": "Aviso", "info": "Info"}
    lineas = [f"[{marca.get(a['nivel'], a['nivel'])}] {a['titulo']}" + (f" — {a['detalle']}" if a["detalle"] else "")
              for a in alertas]
    return {
        "origen": "GEM OS",
        "total": len(alertas),
        "criticas": sum(1 for a in alertas if a["nivel"] == "critico"),
        "asunto": (f"GEM OS: {len(alertas)} alerta(s)" + (" CRÍTICA(S)" if any(a["nivel"] == "critico" for a in alertas) else "")),
        "mensaje": "\n".join(lineas),
        "panel": _url_panel(),
        "alertas": [{"nivel": a["nivel"], "titulo": a["titulo"], "detalle": a["detalle"],
                     "enlace": _url_panel(a["enlace"])} for a in alertas],
    }


def _entregar(alertas: List[Dict[str, Any]], cfg: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    resultado: Dict[str, Dict[str, Any]] = {}
    if cfg["windows"]["activo"]:
        if len(alertas) <= MAX_TOASTS:
            partes = [enviar_toast(("🔴 " if a["nivel"] == "critico" else "🟠 " if a["nivel"] == "aviso" else "") + a["titulo"],
                                   a["detalle"] or "Abre GEM OS para verlo.", a["enlace"]) for a in alertas]
            ok = all(p["ok"] for p in partes)
            resultado["windows"] = {"ok": ok, "motivo": next((p.get("motivo") for p in partes if not p["ok"]), None)}
        else:
            top = "; ".join(a["titulo"] for a in alertas[:3])
            resultado["windows"] = enviar_toast(f"GEM OS: {len(alertas)} alertas nuevas", top + "…")
    if cfg["make"]["activo"]:
        resultado["make"] = enviar_webhook(_payload(alertas))
    return resultado


# ── API ──────────────────────────────────────────────────────────────────────

def enviar_pendientes(db_path: str, ahora: Optional[datetime] = None) -> Dict[str, Any]:
    """Avisa de las alertas activas que aún no se han avisado. Lo llama el servidor tras evaluar."""
    cfg = configuracion()
    if not cfg["habilitado"] or not (cfg["windows"]["activo"] or cfg["make"]["activo"]):
        return {"enviadas": 0, "motivo": "avisos externos desactivados o sin canal"}
    ahora = ahora or datetime.now()
    minimo = NIVELES[cfg["nivel_minimo"]]
    limite_recordatorio = (ahora - timedelta(hours=RECORDATORIO_CRITICAS_H)).isoformat(timespec="seconds")
    with closing(sqlite3.connect(db_path, timeout=30)) as conn:
        conn.row_factory = sqlite3.Row
        filas = [dict(r) for r in conn.execute(
            """SELECT id, nivel, titulo, detalle, enlace FROM alertas
               WHERE resuelta_at IS NULL
                 AND (notificada_at IS NULL
                      OR (nivel = 'critico' AND vista_at IS NULL AND notificada_at <= ?))
               ORDER BY CASE nivel WHEN 'critico' THEN 3 WHEN 'aviso' THEN 2 ELSE 1 END DESC, id""",
            (limite_recordatorio,))]
        pendientes = [a for a in filas if NIVELES.get(a["nivel"], 1) >= minimo]
        if en_silencio(ahora):
            pendientes = [a for a in pendientes if a["nivel"] == "critico"]
        if not pendientes:
            return {"enviadas": 0}
        resultado = _entregar(pendientes, cfg)
        if any(r["ok"] for r in resultado.values()):          # basta un canal para darla por avisada
            conn.executemany("UPDATE alertas SET notificada_at = ? WHERE id = ?",
                             [(ahora.isoformat(timespec="seconds"), a["id"]) for a in pendientes])
            conn.commit()
            log.info(f"[AVISOS] {len(pendientes)} alerta(s) avisadas: "
                     + ", ".join(f"{k}={'ok' if v['ok'] else 'falló'}" for k, v in resultado.items()))
            return {"enviadas": len(pendientes), "canales": resultado}
        log.warning("[AVISOS] No se pudo avisar por ningún canal: "
                    + ", ".join(f"{k}: {v.get('motivo')}" for k, v in resultado.items()))
        return {"enviadas": 0, "canales": resultado}


def enviar_prueba() -> Dict[str, Any]:
    """Aviso de prueba por los canales activos (ignora silencio y nivel)."""
    cfg = configuracion()
    prueba = [{"nivel": "aviso", "titulo": "Prueba de aviso de GEM OS",
               "detalle": "Si lees esto, los avisos fuera de la app funcionan.", "enlace": "/registros"}]
    if not cfg["habilitado"]:
        return {"ok": False, "motivo": "Los avisos están desactivados (GEM_OS_AVISOS=0).", "canales": {}}
    resultado = _entregar(prueba, cfg)
    if not resultado:
        return {"ok": False, "motivo": "No hay ningún canal activo.", "canales": {}}
    return {"ok": all(r["ok"] for r in resultado.values()), "canales": resultado}
