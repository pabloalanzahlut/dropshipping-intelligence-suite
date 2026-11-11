"""
Publicador Orgánico — GEM OS

Lee cola_publicacion.json, espera el horario de Italia y publica en:
  - Facebook Reels (página NovaBuy, vía Make.com)
  - Instagram Reels (vía Make.com)
  - TikTok (vía Make.com)

Flujo por slot:
  1. Sube el master a Google Drive (carpeta "GEM OS/Videos")
  2. Llama al webhook Make.com con {video_url, caption, hashtags, plataforma}
  3. Actualiza el estado del slot en la cola JSON

Requisitos de entorno (.env):
  GOOGLE_CREDENTIALS_PATH, MAKE_WEBHOOK_PUBLICADOR_FB_IG, MAKE_WEBHOOK_TIKTOK
  GDRIVE_FOLDER_VIDEOS (opcional; si falta se crea "GEM OS/Videos")

Uso:
  python -m app.services.publicador --cola <ruta_cola.json> [--dry-run]
  python -m app.services.publicador --daemon --cola <ruta_cola.json>
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from zoneinfo import ZoneInfo

ZONA_ITALIA = ZoneInfo("Europe/Rome")

# ─── variables de entorno ───────────────────────────────────────────────────

def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _cargar_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


# ─── Google Drive upload ────────────────────────────────────────────────────

def _gdrive_upload(video_path: Path, nombre_en_drive: str) -> str:
    """Sube el vídeo a Google Drive y devuelve una URL de descarga directa."""
    creds_path = _env("GOOGLE_CREDENTIALS_PATH", "ai_workspace/config/google_credentials.json")
    creds_file = Path(creds_path)
    if not creds_file.exists():
        raise RuntimeError(f"Credenciales GDrive no encontradas: {creds_file}")

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError as e:
        raise RuntimeError("Instala: pip install google-api-python-client google-auth") from e

    creds = service_account.Credentials.from_service_account_file(
        str(creds_file), scopes=["https://www.googleapis.com/auth/drive"]
    )
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    folder_id = _env("GDRIVE_FOLDER_VIDEOS") or _obtener_o_crear_carpeta(service, "GEM OS/Videos")

    meta = {"name": nombre_en_drive, "parents": [folder_id]}
    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)
    file = service.files().create(body=meta, media_body=media, fields="id").execute()
    fid = file["id"]

    # Hacer público (lectura) para que Make.com lo descargue
    service.permissions().create(fileId=fid, body={"role": "reader", "type": "anyone"}).execute()

    return f"https://drive.google.com/uc?export=download&id={fid}"


def _obtener_o_crear_carpeta(service, ruta: str) -> str:
    """Crea o localiza una carpeta jerárquica en Drive; devuelve su ID."""
    partes = ruta.split("/")
    parent = "root"
    for nombre in partes:
        q = (f"name='{nombre}' and mimeType='application/vnd.google-apps.folder' "
             f"and '{parent}' in parents and trashed=false")
        res = service.files().list(q=q, fields="files(id)").execute().get("files", [])
        if res:
            parent = res[0]["id"]
        else:
            f = service.files().create(
                body={"name": nombre, "mimeType": "application/vnd.google-apps.folder",
                      "parents": [parent]},
                fields="id"
            ).execute()
            parent = f["id"]
    return parent


# ─── webhooks Make.com ──────────────────────────────────────────────────────

def _llamar_webhook(url: str, payload: dict, dry_run: bool = False) -> dict:
    if dry_run:
        print(f"  [DRY-RUN] POST {url[:60]}… {json.dumps(payload, ensure_ascii=False)[:120]}")
        return {"ok": True, "dry_run": True}
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    try:
        return resp.json()
    except Exception:
        return {"ok": True, "raw": resp.text[:200]}


def publicar_slot(slot: dict, dry_run: bool = False) -> dict:
    """Sube el vídeo y llama los webhooks para un slot. Devuelve resultados."""
    archivo = Path(slot["archivo_master"])
    if not archivo.exists():
        return {"error": f"Archivo master no encontrado: {archivo}"}

    nombre_drive = f"{slot['producto']}_{slot['dia']:02d}_{slot['formula']}_{slot['id'][:8]}.mp4"

    if dry_run:
        video_url = f"https://drive.google.com/uc?export=download&id=DRY_RUN_{slot['id'][:8]}"
    else:
        print(f"  → Subiendo a Drive: {nombre_drive}")
        video_url = _gdrive_upload(archivo, nombre_drive)
        print(f"  ✓ Drive: {video_url[:70]}…")

    resultados: dict = {}

    for plataforma, datos in slot["plataformas"].items():
        if datos.get("publicado"):
            continue

        caption = datos.get("caption", "")
        hashtags = datos.get("hashtags", [])

        if plataforma == "tiktok":
            webhook = _env("MAKE_WEBHOOK_TIKTOK")
        else:
            webhook = _env("MAKE_WEBHOOK_PUBLICADOR_FB_IG")

        if not webhook:
            resultados[plataforma] = {"error": f"Webhook no configurado para {plataforma}"}
            continue

        payload = {
            "video_url": video_url,
            "plataforma": plataforma,
            "caption": caption,
            "hashtags": hashtags,
            "producto": slot["producto"],
            "formula": slot["formula"],
            "slot_id": slot["id"],
        }
        try:
            r = _llamar_webhook(webhook, payload, dry_run=dry_run)
            resultados[plataforma] = r
        except Exception as exc:
            resultados[plataforma] = {"error": str(exc)}

    return resultados


# ─── gestor de cola ─────────────────────────────────────────────────────────

def cargar_cola(ruta: Path) -> list:
    return json.loads(ruta.read_text(encoding="utf-8"))


def guardar_cola(cola: list, ruta: Path) -> None:
    ruta.write_text(json.dumps(cola, ensure_ascii=False, indent=2), encoding="utf-8")


def slots_listos(cola: list) -> list:
    """Devuelve slots cuya hora ya llegó y están en estado listo_para_programar."""
    ahora = datetime.now(tz=timezone.utc)
    listos = []
    for slot in cola:
        if slot.get("estado") != "listo_para_programar":
            continue
        if not slot.get("archivo_master"):
            continue
        try:
            dt = datetime.fromisoformat(slot["fecha_hora_italia"])
        except (KeyError, ValueError):
            continue
        if dt.astimezone(timezone.utc) <= ahora:
            listos.append(slot)
    return listos


def procesar_cola(ruta_cola: Path, dry_run: bool = False) -> None:
    cola = cargar_cola(ruta_cola)
    listos = slots_listos(cola)
    if not listos:
        print("No hay slots listos para publicar ahora.")
        return

    print(f"{len(listos)} slot(s) listo(s).")
    for slot in listos:
        print(f"\n  Slot {slot['id'][:8]} | Día {slot['dia']} | {slot['formula']} | {slot['fecha_hora_italia']}")
        resultados = publicar_slot(slot, dry_run=dry_run)

        # marcar publicado si todos los webhooks respondieron ok
        todo_ok = all("error" not in v for v in resultados.values())
        for plataforma, res in resultados.items():
            if "error" not in res:
                slot["plataformas"][plataforma]["publicado"] = True
                slot["plataformas"][plataforma]["resultado"] = res

        slot["estado"] = "publicado" if todo_ok else "publicado_parcial"
        slot["publicado_en"] = datetime.now(tz=timezone.utc).isoformat()
        print(f"  Estado: {slot['estado']} | Resultados: {json.dumps(resultados, ensure_ascii=False)[:200]}")

    if not dry_run:
        guardar_cola(cola, ruta_cola)
        print(f"\nCola actualizada: {ruta_cola}")


# ─── daemon ─────────────────────────────────────────────────────────────────

def daemon(ruta_cola: Path, intervalo_min: int = 5) -> None:
    print(f"Daemon publicador iniciado. Revisando cada {intervalo_min} min. Ctrl-C para parar.")
    while True:
        try:
            procesar_cola(ruta_cola, dry_run=False)
        except Exception as exc:
            print(f"[ERROR] {exc}")
        time.sleep(intervalo_min * 60)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> int:
    _cargar_dotenv()
    ap = argparse.ArgumentParser(description="Publicador orgánico GEM OS")
    ap.add_argument("--cola", required=True, type=Path, help="Ruta a cola_publicacion.json")
    ap.add_argument("--dry-run", action="store_true", help="Simula sin subir ni publicar")
    ap.add_argument("--daemon", action="store_true", help="Modo continuo (cada 5 min)")
    ap.add_argument("--intervalo", type=int, default=5, help="Minutos entre revisiones (--daemon)")
    a = ap.parse_args()

    if not a.cola.exists():
        print(f"Cola no encontrada: {a.cola}", file=sys.stderr)
        return 1

    if a.daemon:
        daemon(a.cola, a.intervalo)
    else:
        procesar_cola(a.cola, dry_run=a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
