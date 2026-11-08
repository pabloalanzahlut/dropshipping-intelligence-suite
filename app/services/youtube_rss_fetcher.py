"""
YouTubeRSSFetcher - Descarga videos y transcripciones SIN YouTube API key.

Estrategia 100% gratuita:
  - RSS feed de YouTube (xml público, sin autenticación); si no resuelve el
    canal, yt-dlp --flat-playlist como respaldo
  - yt-dlp para subtítulos manuales y automáticos
"""

import html
import os
import shutil
import subprocess
import sys
import json
import hashlib
import re
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime


YOUTUBE_RSS_BASE = "https://www.youtube.com/feeds/videos.xml"
_UA = {"User-Agent": "Mozilla/5.0"}
_CHANNEL_ID_RE = re.compile(r"UC[\w-]{22}")


def _ytdlp_cmd() -> List[str]:
    """Comando base de yt-dlp: ejecutable en PATH o, si no, el módulo de Python."""
    exe = shutil.which("yt-dlp")
    if exe:
        return [exe]
    if not getattr(sys, "frozen", False):
        return [sys.executable, "-m", "yt_dlp"]
    return ["yt-dlp"]


def _run_ytdlp(args: List[str], timeout: int = 60) -> Optional[str]:
    """Ejecuta yt-dlp y devuelve stdout decodificado en UTF-8 (None si falla)."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    try:
        res = subprocess.run(
            _ytdlp_cmd() + args, capture_output=True, timeout=timeout, env=env
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        print(f"[YT-DLP] {exc}")
        return None
    if res.returncode != 0:
        err = res.stderr.decode("utf-8", errors="replace").strip().splitlines()
        print(f"[YT-DLP] código {res.returncode}: {err[-1] if err else ''}")
        return None
    return res.stdout.decode("utf-8", errors="replace")


def _channel_to_rss_url(channel_input: str) -> Optional[str]:
    """
    Convierte handle/URL de canal a URL de feed RSS.
    Soporta UCxxx directo, /channel/UCxxx y @handle (resuelve el channel_id
    leyendo la página pública, donde YouTube lo publica como externalId).
    Devuelve None si no se puede resolver (el llamador cae a yt-dlp).
    """
    channel_input = (channel_input or "").strip()
    if _CHANNEL_ID_RE.fullmatch(channel_input):
        return f"{YOUTUBE_RSS_BASE}?channel_id={channel_input}"

    m = re.search(r"/channel/(UC[\w-]{22})", channel_input)
    if m:
        return f"{YOUTUBE_RSS_BASE}?channel_id={m.group(1)}"

    handle = channel_input.rstrip("/").split("/")[-1].lstrip("@")
    if not handle:
        return None
    try:
        req = urllib.request.Request(f"https://www.youtube.com/@{handle}", headers=_UA)
        with urllib.request.urlopen(req, timeout=15) as resp:
            page = resp.read().decode("utf-8", errors="ignore")
        # externalId es el id del canal de la página; "channelId" puede ser de otro
        m = re.search(r'"externalId":"(UC[\w-]{22})"', page) or re.search(
            r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"', page
        )
        if m:
            return f"{YOUTUBE_RSS_BASE}?channel_id={m.group(1)}"
    except Exception as exc:
        print(f"[RSS] No se pudo resolver {handle}: {exc}")
    return None


def _fetch_videos_ytdlp(channel_url: str, max_videos: int) -> List[Dict]:
    """Respaldo: lista los últimos vídeos del canal con yt-dlp --flat-playlist."""
    base = channel_url.rstrip("/")
    if not base.endswith("/videos"):
        base += "/videos"
    out = _run_ytdlp(
        ["--flat-playlist", "--playlist-end", str(max_videos), "--no-warnings",
         "--print", "%(id)s\t%(title)s", base],
        timeout=90,
    )
    videos = []
    for line in (out or "").splitlines():
        vid, _, title = line.partition("\t")
        vid = vid.strip()
        if re.fullmatch(r"[\w-]{11}", vid):
            videos.append({
                "video_id": vid, "title": title.strip(), "channel": "",
                "published": "", "url": f"https://www.youtube.com/watch?v={vid}",
            })
    return videos


def fetch_channel_videos(channel_url: str, max_videos: int = 15) -> List[Dict]:
    """
    Obtiene lista de vídeos recientes: RSS (rápido, con fecha) y, si falla,
    yt-dlp. Sin API key.

    Returns:
        Lista de dicts: {video_id, title, channel, published, url}
    """
    rss_url = _channel_to_rss_url(channel_url)
    if rss_url:
        try:
            req = urllib.request.Request(rss_url, headers=_UA)
            with urllib.request.urlopen(req, timeout=15) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "yt": "http://www.youtube.com/xml/schemas/2015",
            }
            channel_name = root.findtext("atom:title", default="", namespaces=ns)
            videos = []
            for entry in root.findall("atom:entry", namespaces=ns)[:max_videos]:
                video_id = entry.findtext("yt:videoId", default="", namespaces=ns)
                if video_id:
                    videos.append({
                        "video_id": video_id,
                        "title": entry.findtext("atom:title", default="", namespaces=ns),
                        "channel": channel_name,
                        "published": entry.findtext("atom:published", default="", namespaces=ns),
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                    })
            if videos:
                return videos
        except Exception as exc:
            print(f"[RSS] Error con {rss_url}: {exc}")

    # RSS no resolvió o vino vacío: yt-dlp
    return _fetch_videos_ytdlp(channel_url, max_videos)


def _pick_vtt(files: List[Path], lang: str) -> Optional[Path]:
    """Prefiere el subtítulo exacto del idioma (`id.es.vtt`) sobre variantes."""
    if not files:
        return None

    def rank(f: Path) -> int:
        tag = f.name.rsplit(".vtt", 1)[0].rsplit(".", 1)[-1].lower()
        if tag == lang:
            return 0
        if tag.startswith(lang) and "orig" not in tag:
            return 1
        return 2

    return sorted(files, key=lambda f: (rank(f), f.name))[0]


def download_transcript(video_id: str, lang: str = "es") -> Optional[str]:
    """
    Descarga la transcripción con yt-dlp (gratuito): subtítulos manuales y
    automáticos del idioma pedido y, si no hay, en inglés.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    langs = [lang] if lang == "en" else [lang, "en"]
    with tempfile.TemporaryDirectory() as tmpdir:
        for lg in langs:
            for old in Path(tmpdir).glob("*.vtt"):
                old.unlink(missing_ok=True)
            _run_ytdlp(
                ["--skip-download", "--write-subs", "--write-auto-subs",
                 "--sub-langs", f"{lg}.*,{lg}", "--sub-format", "vtt",
                 "--no-warnings", "--quiet",
                 "--output", str(Path(tmpdir) / video_id), url],
                timeout=90,
            )
            vtt = _pick_vtt(list(Path(tmpdir).glob("*.vtt")), lg)
            if vtt:
                text = _parse_vtt(vtt.read_text(encoding="utf-8", errors="ignore"))
                if text and len(text) > 100:
                    return text
    return None


def _parse_vtt(vtt_content: str) -> str:
    """Extrae texto limpio de un archivo VTT (sin timestamps ni duplicados)."""
    lines = []
    for line in vtt_content.splitlines():
        line = line.strip()
        if (not line or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE"))
                or "-->" in line or re.match(r"^\d+$", line)):
            continue
        clean = html.unescape(re.sub(r"<[^>]+>", "", line)).strip()
        if clean:
            lines.append(clean)

    # Los auto-subs repiten líneas en ventana deslizante: quitar repetidas consecutivas
    deduped: List[str] = []
    for l in lines:
        if not deduped or l != deduped[-1]:
            deduped.append(l)
    return " ".join(deduped)


def hash_content(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# ──────────────────────────────────────────────────────────────────────────────
# YouTube Data API v3 (opcional — requiere YOUTUBE_API_KEY en .env)
# Permite búsquedas de videos por keyword, algo que el RSS no puede hacer.
# Si la key no está configurada, todas las funciones de esta sección devuelven [].
# ──────────────────────────────────────────────────────────────────────────────

import os as _os

def _yt_api_key() -> Optional[str]:
    return _os.getenv("YOUTUBE_API_KEY") or None


def search_videos_by_keyword(
    keyword: str,
    max_results: int = 10,
    order: str = "viewCount",
    language: str = "es",
) -> List[Dict]:
    """
    Busca videos en YouTube por keyword usando Data API v3.
    Requiere YOUTUBE_API_KEY en .env.
    order: 'viewCount' | 'relevance' | 'date'

    Returns lista de dicts con: video_id, title, channel, published_at, view_count
    """
    key = _yt_api_key()
    if not key:
        return []

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": keyword,
        "type": "video",
        "order": order,
        "relevanceLanguage": language,
        "maxResults": min(max_results, 50),
        "key": key,
    }
    try:
        query = "&".join(f"{k}={urllib.request.quote(str(v))}" for k, v in params.items())
        req = urllib.request.Request(f"{url}?{query}", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = []
        for item in data.get("items", []):
            results.append({
                "video_id":    item["id"]["videoId"],
                "title":       item["snippet"]["title"],
                "channel":     item["snippet"]["channelTitle"],
                "published_at": item["snippet"]["publishedAt"],
                "url":         f"https://www.youtube.com/watch?v={item['id']['videoId']}",
            })
        return results
    except Exception as e:
        print(f"[YT_API] search error: {e}")
        return []


def get_video_stats(video_ids: List[str]) -> Dict[str, Dict]:
    """
    Obtiene estadísticas (views, likes, comments) para una lista de video_ids.
    Requiere YOUTUBE_API_KEY en .env.
    Returns dict keyed by video_id.
    """
    key = _yt_api_key()
    if not key or not video_ids:
        return {}

    ids_str = urllib.request.quote(",".join(video_ids[:50]))
    url = (
        f"https://www.googleapis.com/youtube/v3/videos"
        f"?part=statistics&id={ids_str}&key={urllib.request.quote(key)}"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        stats = {}
        for item in data.get("items", []):
            s = item.get("statistics", {})
            stats[item["id"]] = {
                "views":    int(s.get("viewCount", 0)),
                "likes":    int(s.get("likeCount", 0)),
                "comments": int(s.get("commentCount", 0)),
            }
        return stats
    except Exception as e:
        print(f"[YT_API] stats error: {e}")
        return {}
