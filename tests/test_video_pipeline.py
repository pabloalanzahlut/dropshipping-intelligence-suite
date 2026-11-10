import subprocess
from datetime import date
from pathlib import Path

import pytest

from app.services import video_pipeline as vp


def test_rechaza_claims_de_salud():
    assert vp.validar_textos(["Ricrescita dei capelli garantita"])
    assert vp.validar_textos(["Anti hair loss massage"])


def test_rechaza_mas_de_6_palabras():
    assert vp.validar_textos(["uno due tre quattro cinque sei sette"])


def test_acepta_texto_valido():
    assert vp.validar_textos(["Massaggio in 10 secondi"]) == []


def test_cola_14_dias_3_franjas_3_plataformas():
    cola = vp.generar_cola(date(2026, 11, 16), "p", {}, {}, {})
    assert len(cola) == 42
    assert all(set(c["plataformas"]) == set(vp.PLATAFORMAS) for c in cola)
    assert cola[0]["fecha_hora_italia"].endswith("+01:00")


def test_render_demo(tmp_path):
    try:
        exe = vp.ffmpeg_exe()
    except vp.PipelineError:
        pytest.skip("imageio-ffmpeg no instalado")
    clip = tmp_path / "c.mp4"
    subprocess.run([exe, "-y", "-f", "lavfi", "-i", "color=c=black:s=720x1280:d=3:r=30",
                    "-pix_fmt", "yuv420p", str(clip)], check=True, capture_output=True)
    job = vp.VideoJob("p", "DEM", clip, [vp.Segmento("Ciao mondo", 0, 2)])
    out = vp.renderizar(job, tmp_path / "m.mp4")
    assert out.exists() and out.stat().st_size > 0


def test_render_bloquea_texto_con_claim(tmp_path):
    clip = tmp_path / "c.mp4"
    clip.write_bytes(b"x")
    job = vp.VideoJob("p", "DEM", clip, [vp.Segmento("Anticaduta garantita", 0, 2)])
    with pytest.raises(vp.PipelineError):
        vp.renderizar(job, tmp_path / "m.mp4")
