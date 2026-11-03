"""
YouTubeRSSFetcher - Descarga videos y transcripciones SIN YouTube API key.

Estrategia 100% gratuita:
  - RSS feed de YouTube (xml público, sin autenticación)
  - yt-dlp para transcripciones automáticas/generadas
  - OpenRouter para limpieza de texto vía LLM
"""

import subprocess
import json
import hashlib
import re
import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime


YOUTUBE_RSS_BASE = "https://www.youtube.com/feeds/videos.xml"


def _channel_to_rss_url(channel_input: str) -> Optional[str]:
    """
    Convierte handle/URL de canal a URL de feed RSS.
    Soporta:
      - @handle  →  resuelve channel_id via scraping ligero
      - UCxxx    →  directo
      - URL completa
    """
    # Si ya es un channel_id (UCxxx...)
    if re.match(r"^UC[\w-]{22}$", channel_input):
        return f"{YOUTUBE_RSS_BASE}?channel_id={channel_input}"

    # Si viene como URL, extraer handle o channel_id
    handle = channel_input.lstrip("@")
    if "/" in handle:
        parts = handle.rstrip("/").split("/")
        handle = parts[-1].lstrip("@")

    # Intentar resolver handle → channel_id via página pública
    try:
        url = f"https://www.youtube.com/@{handle}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        match = re.search(r'"channelId":"(UC[\w-]{22})"', html)
        if match:
            channel_id = match.group(1)
            return f"{YOUTUBE_RSS_BASE}?channel_id={channel_id}"
    except Exception:
        pass
    return None


def fetch_channel_videos(channel_url: str, max_videos: int = 15) -> List[Dict]:
    """
    Obtiene lista de videos recientes via RSS (gratuito, sin API key).

    Returns:
        Lista de dicts: {video_id, title, channel, published, url}
    """
    rss_url = _channel_to_rss_url(channel_url)
    if not rss_url:
        return []

    try:
        req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read()
    except Exception as e:
        print(f"[RSS] Error fetching {rss_url}: {e}")
        return []

    try:
        root = ET.fromstring(xml_data)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
            "media": "http://search.yahoo.com/mrss/",
        }
        channel_name = root.findtext("atom:title", default="", namespaces=ns)
        entries = root.findall("atom:entry", namespaces=ns)[:max_videos]

        videos = []
        for entry in entries:
            video_id = entry.findtext("yt:videoId", default="", namespaces=ns)
            title = entry.findtext("atom:title", default="", namespaces=ns)
            published = entry.findtext("atom:published", default="", namespaces=ns)
            if video_id:
                videos.append({
                    "video_id": video_id,
                    "title": title,
                    "channel": channel_name,
                    "published": published,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                })
        return videos
    except ET.ParseError as e:
        print(f"[RSS] XML parse error: {e}")
        return []


def download_transcript(video_id: str, lang: str = "es") -> Optional[str]:
    """
    Descarga transcripción con yt-dlp (gratuito).
    Intenta: subtítulos manuales → auto-generados → cualquier idioma disponible.

    Requiere: pip install yt-dlp
    """
    import tempfile, os

    url = f"https://www.youtube.com/watch?v={video_id}"
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / video_id

        for lang_opt in [["--sub-lang", lang], ["--sub-lang", "en"], ["--write-auto-subs"]]:
            cmd = [
                "yt-dlp",
                "--skip-download",
                "--write-subs",
                *lang_opt,
                "--sub-format", "vtt",
                "--output", str(base),
                "--quiet",
                url,
            ]
            try:
                subprocess.run(cmd, capture_output=True, timeout=30)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                break

            # Buscar archivo .vtt generado
            for vtt_file in Path(tmpdir).glob("*.vtt"):
                text = _parse_vtt(vtt_file.read_text(encoding="utf-8", errors="ignore"))
                if text and len(text) > 100:
                    return text

    return None


def _parse_vtt(vtt_content: str) -> str:
    """Extrae texto limpio de un archivo VTT."""
    lines = []
    for line in vtt_content.splitlines():
        line = line.strip()
        # Saltar cabeceras, timestamps y líneas vacías
        if not line or line.startswith("WEBVTT") or "-->" in line or re.match(r"^\d+$", line):
            continue
        # Eliminar tags HTML
        clean = re.sub(r"<[^>]+>", "", line)
        if clean:
            lines.append(clean)

    # Deduplicar líneas consecutivas repetidas (VTT duplica líneas en auto-subs)
    deduped = []
    prev = None
    for l in lines:
        if l != prev:
            deduped.append(l)
            prev = l

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
