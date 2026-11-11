"""Tests para app/services/publicador.py (sin llamadas reales a Drive ni Make)."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services import publicador as pub


# ─── fixtures ───────────────────────────────────────────────────────────────

def _slot(estado="listo_para_programar", offset_min=-1, con_archivo=True, tmp_path=None):
    dt = datetime.now(tz=timezone.utc) + timedelta(minutes=offset_min)
    # convertir a hora Italia para el campo
    from zoneinfo import ZoneInfo
    dt_it = dt.astimezone(ZoneInfo("Europe/Rome"))

    archivo = None
    if con_archivo and tmp_path:
        archivo = tmp_path / "master.mp4"
        archivo.write_bytes(b"fake_video")

    return {
        "id": "aabbccdd-0000-0000-0000-000000000000",
        "dia": 1,
        "formula": "DEM",
        "fecha_hora_italia": dt_it.isoformat(),
        "producto": "peine",
        "archivo_master": str(archivo) if archivo else None,
        "estado": estado,
        "plataformas": {
            "tiktok": {"caption": "Test", "hashtags": ["#test"], "publicado": False},
            "instagram_reels": {"caption": "Test IG", "hashtags": ["#test"], "publicado": False},
            "facebook_reels": {"caption": "Test FB", "hashtags": ["#test"], "publicado": False},
        },
    }


# ─── tests slots_listos ──────────────────────────────────────────────────────

def test_slot_en_el_pasado_aparece(tmp_path):
    cola = [_slot(offset_min=-5, tmp_path=tmp_path)]
    assert len(pub.slots_listos(cola)) == 1


def test_slot_en_el_futuro_no_aparece(tmp_path):
    cola = [_slot(offset_min=+60, tmp_path=tmp_path)]
    assert pub.slots_listos(cola) == []


def test_slot_ya_publicado_se_ignora(tmp_path):
    cola = [_slot(estado="publicado", offset_min=-5, tmp_path=tmp_path)]
    assert pub.slots_listos(cola) == []


def test_slot_sin_archivo_se_ignora(tmp_path):
    cola = [_slot(offset_min=-5, con_archivo=False, tmp_path=tmp_path)]
    assert pub.slots_listos(cola) == []


# ─── tests publicar_slot (dry-run) ───────────────────────────────────────────

def test_publicar_dry_run_sin_archivo_devuelve_error(tmp_path):
    slot = _slot(offset_min=-1, con_archivo=False, tmp_path=tmp_path)
    slot["archivo_master"] = str(tmp_path / "no_existe.mp4")
    res = pub.publicar_slot(slot, dry_run=True)
    assert "error" in res


def test_publicar_dry_run_con_archivo_ok(tmp_path, monkeypatch):
    monkeypatch.setenv("MAKE_WEBHOOK_TIKTOK", "https://hook.test/tok")
    monkeypatch.setenv("MAKE_WEBHOOK_PUBLICADOR_FB_IG", "https://hook.test/fbig")
    slot = _slot(offset_min=-1, con_archivo=True, tmp_path=tmp_path)
    res = pub.publicar_slot(slot, dry_run=True)
    assert "tiktok" in res
    assert res["tiktok"].get("dry_run") is True


# ─── tests procesar_cola ────────────────────────────────────────────────────

def test_procesar_actualiza_estado(tmp_path, monkeypatch):
    monkeypatch.setenv("MAKE_WEBHOOK_TIKTOK", "https://hook.test/tok")
    monkeypatch.setenv("MAKE_WEBHOOK_PUBLICADOR_FB_IG", "https://hook.test/fbig")

    cola = [_slot(offset_min=-5, tmp_path=tmp_path)]
    ruta = tmp_path / "cola.json"
    pub.guardar_cola(cola, ruta)

    # Mock requests.post para no llamar webhooks reales
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"ok": True}

    with patch("app.services.publicador.requests.post", return_value=mock_resp):
        pub.procesar_cola(ruta, dry_run=False)

    cola2 = pub.cargar_cola(ruta)
    assert cola2[0]["estado"] in ("publicado", "publicado_parcial")
