"""
Video Pipeline — edita 1 clip a master 9:16 con texto en pantalla y genera la cola
de publicación de 14 días (3 vídeos/día, horario Italia) para TikTok, IG Reels y FB Reels.

El clip de origen es de Higgsfield (higgsfield_client) o grabación real del usuario.
Todo texto pasa por deterministic_gate + lista de claims de salud antes de renderizar.

Uso:
    python -m app.services.video_pipeline --demo
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from app.services.deterministic_gate import verificar_copy

MAX_PALABRAS_FRAME = 6
MAX_DURACION_S = 25
FRANJAS_ITALIA = ("08:00", "13:00", "20:30")
FORMULAS = ("DEM", "REA", "COM", "POV", "UNB")
PLATAFORMAS = ("tiktok", "instagram_reels", "facebook_reels")

# Claims de salud/cosméticos que las plataformas y la normativa UE no admiten sin prueba.
CLAIMS_PROHIBIDOS = (
    "hair growth", "anti hair loss", "hair loss", "regrow", "crecimiento del cabello",
    "caída del cabello", "caida del cabello", "calvicie", "crescita dei capelli",
    "ricrescita", "anticaduta", "caduta dei capelli", "calvizie", "cura", "guarisce",
    "clinicamente", "clínicamente", "terapia", "tratamiento médico",
)

CALENDARIO = {  # espejo de organico/06_plan_14_dias_3_plataformas.md
    1: "DEM POV REA", 2: "COM UNB DEM", 3: "REA DEM POV", 4: "UNB COM REA",
    5: "DEM REA COM", 6: "POV DEM UNB", 7: "COM REA DEM", 8: "UNB POV COM",
    9: "DEM COM REA", 10: "REA UNB POV", 11: "COM DEM UNB", 12: "POV REA DEM",
    13: "DEM UNB COM", 14: "REA COM POV",
}


class PipelineError(Exception):
    pass


@dataclass
class Segmento:
    texto: str
    inicio: float
    fin: float


@dataclass
class VideoJob:
    producto: str
    formula: str
    clip_origen: Path
    segmentos: List[Segmento]
    caption: str = ""
    hashtags: List[str] = field(default_factory=list)


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as e:
        raise PipelineError("Falta imageio-ffmpeg: pip install imageio-ffmpeg") from e


def clip_desde_imagenes(imagenes: List[Path], salida: Path, seg_por_imagen: float = 3.0,
                        variante: int = 0) -> Path:
    """Clip vertical a partir de fotos reales con zoom suave (gratis, local, sin IA de pago).
    variante par = zoom in, impar = zoom out, para que los vídeos no queden idénticos."""
    if not imagenes:
        raise PipelineError("Hacen falta fotos del producto.")
    for im in imagenes:
        if not Path(im).exists():
            raise PipelineError(f"No existe la imagen: {im}")
    fps = 30
    frames = int(seg_por_imagen * fps)
    if variante % 2 == 0:
        z = "min(zoom+0.0015,1.25)"
    else:
        z = "if(eq(on,0),1.25,max(zoom-0.0015,1.0))"
    cmd = [ffmpeg_exe(), "-y"]
    for im in imagenes:
        cmd += ["-i", str(Path(im).resolve())]
    partes = []
    for i in range(len(imagenes)):
        partes.append(
            f"[{i}:v]scale=1296:2304:force_original_aspect_ratio=increase,crop=1296:2304,"
            f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps={fps},"
            f"setsar=1[v{i}]"
        )
    union = "".join(f"[v{i}]" for i in range(len(imagenes)))
    filtro = ";".join(partes) + f";{union}concat=n={len(imagenes)}:v=1:a=0[out]"
    salida.parent.mkdir(parents=True, exist_ok=True)
    cmd += ["-filter_complex", filtro, "-map", "[out]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-t", str(MAX_DURACION_S), str(salida.resolve())]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not salida.exists() or salida.stat().st_size == 0:
        raise PipelineError("ffmpeg (clip desde imágenes) falló:\n" + r.stderr[-800:])
    return salida


def generar_lote(imagenes: List[Path], hooks: Dict[str, List[str]], carpeta: Path, inicio: date,
                 producto: str, caption_base: str, hashtags: List[str]) -> Path:
    """Renderiza un master por cada slot de la cola y deja el JSON listo para programar.
    hooks: {'DEM': [...], 'REA': [...], ...}. Todo texto pasa por validar_textos."""
    todos = [h for lista in hooks.values() for h in lista] + [caption_base]
    violaciones = validar_textos(todos)
    if violaciones:
        raise PipelineError("Hooks/caption rechazados:\n- " + "\n- ".join(violaciones))
    cola = generar_cola(inicio, producto, {}, {p: caption_base for p in PLATAFORMAS},
                        {p: hashtags for p in PLATAFORMAS})
    uso: Dict[str, int] = {}
    for n, slot in enumerate(cola):
        f = slot["formula"]
        lista = hooks.get(f) or [caption_base]
        k = uso.get(f, 0)
        uso[f] = k + 1
        hook = lista[k % len(lista)]
        # rotar subconjunto de fotos para que cada vídeo sea distinto
        fotos = [imagenes[(n + j) % len(imagenes)] for j in range(min(3, len(imagenes)))]
        clip = clip_desde_imagenes(fotos, carpeta / "clips" / f"{n:02d}.mp4", variante=n)
        job = VideoJob(producto, f, clip, [Segmento(hook, 0, 2.5)], caption=caption_base, hashtags=hashtags)
        master = renderizar(job, carpeta / "masters" / f"d{slot['dia']:02d}_{n:02d}_{f}.mp4")
        slot.update(hook=hook, archivo_master=str(master), estado="listo_para_programar")
    ruta = carpeta / "cola_publicacion.json"
    guardar_cola(cola, ruta)
    return ruta


def validar_textos(textos: List[str]) -> List[str]:
    """Devuelve violaciones; lista vacía = aprobado."""
    violaciones: List[str] = []
    for t in textos:
        if len(t.split()) > MAX_PALABRAS_FRAME:
            violaciones.append(f"Más de {MAX_PALABRAS_FRAME} palabras en frame: '{t}'")
        bajo = t.lower()
        for claim in CLAIMS_PROHIBIDOS:
            if re.search(r"\b" + re.escape(claim) + r"\b", bajo):
                violaciones.append(f"Claim de salud no permitido: '{claim}' en '{t}'")
        gate = verificar_copy(t)
        if not gate["passed"]:
            violaciones.extend(gate["violations"])
    return violaciones


def _fuente() -> Optional[str]:
    for ruta in ("C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if Path(ruta).exists():
            return ruta
    return None


def renderizar(job: VideoJob, salida: Path) -> Path:
    """Master 1080x1920, H.264/AAC, texto grande con borde, máx. 25 s, sin marca de agua."""
    violaciones = validar_textos([s.texto for s in job.segmentos] + [job.caption])
    if violaciones:
        raise PipelineError("Texto rechazado:\n- " + "\n- ".join(violaciones))
    if not job.clip_origen.exists():
        raise PipelineError(f"No existe el clip de origen: {job.clip_origen}")

    salida.parent.mkdir(parents=True, exist_ok=True)
    fuente = _fuente()
    with tempfile.TemporaryDirectory() as tmp:
        filtros = ["scale=1080:1920:force_original_aspect_ratio=increase", "crop=1080:1920"]
        for i, seg in enumerate(job.segmentos):
            (Path(tmp) / f"t{i}.txt").write_text(seg.texto, encoding="utf-8")
            f = f"drawtext=textfile=t{i}.txt:fontsize=64:fontcolor=white:borderw=6:bordercolor=black"
            f += ":x=(w-text_w)/2:y=h*0.72"
            if fuente:
                f += ":fontfile='" + fuente.replace(":", "\\:") + "'"
            f += f":enable='between(t,{seg.inicio},{seg.fin})'"
            filtros.append(f)
        cmd = [
            ffmpeg_exe(), "-y", "-i", str(job.clip_origen.resolve()),
            "-vf", ",".join(filtros), "-t", str(MAX_DURACION_S), "-r", "30",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-movflags", "+faststart", str(salida.resolve()),
        ]
        r = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True)
    if r.returncode != 0 or not salida.exists() or salida.stat().st_size == 0:
        raise PipelineError("ffmpeg falló:\n" + r.stderr[-800:])
    return salida


def generar_cola(inicio: date, producto: str, hooks_por_formula: Dict[str, str],
                 captions: Dict[str, str], hashtags: Dict[str, List[str]]) -> List[Dict]:
    """Cola de 14 días x 3 franjas x 3 plataformas. Estado inicial: pendiente_video."""
    tz = ZoneInfo("Europe/Rome")
    cola: List[Dict] = []
    for dia, formulas in CALENDARIO.items():
        for franja, formula in zip(FRANJAS_ITALIA, formulas.split()):
            h, m = map(int, franja.split(":"))
            dt = datetime.combine(inicio + timedelta(days=dia - 1), datetime.min.time()).replace(
                hour=h, minute=m, tzinfo=tz)
            cola.append({
                "id": str(uuid.uuid4()),
                "dia": dia,
                "fecha_hora_italia": dt.isoformat(),
                "producto": producto,
                "formula": formula,
                "hook": hooks_por_formula.get(formula, ""),
                "archivo_master": None,
                "estado": "pendiente_video",
                "plataformas": {
                    p: {"caption": captions.get(p, ""), "hashtags": hashtags.get(p, []), "publicado": False}
                    for p in PLATAFORMAS
                },
            })
    return cola


def guardar_cola(cola: List[Dict], ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(cola, ensure_ascii=False, indent=2), encoding="utf-8")


def _demo() -> int:
    base = Path(tempfile.mkdtemp(prefix="gemos_video_demo_"))
    clip = base / "clip_demo.mp4"
    r = subprocess.run([ffmpeg_exe(), "-y", "-f", "lavfi", "-i", "color=c=0x224466:s=720x1280:d=6:r=30",
                        "-pix_fmt", "yuv420p", str(clip)], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-500:])
        return 1
    job = VideoJob(
        producto="demo", formula="DEM", clip_origen=clip,
        segmentos=[Segmento("Massaggio in 10 secondi", 0, 2), Segmento("Guarda come funziona", 2, 6)],
        caption="Massaggio del cuoio capelluto a casa",
    )
    out = renderizar(job, base / "master_demo.mp4")
    print(f"OK master: {out} ({out.stat().st_size} bytes)")
    cola = generar_cola(date.today(), "demo", {}, {}, {})
    guardar_cola(cola, base / "cola_demo.json")
    print(f"OK cola: {len(cola)} publicaciones x {len(PLATAFORMAS)} plataformas")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    sys.exit(_demo() if a.demo else ap.print_help())
