#!/usr/bin/env python3
"""
Script to extract video data from a YouTube playlist by parsing the page HTML.
Extracts all video titles and channel names from the playlist.
"""

import json
import re
import urllib.request
import urllib.error
import sys
from collections import Counter

PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLrs1PAk24jHeU8waSkHzgQTHmduOk9xMn"

def fetch_page(url):
    """Fetch YouTube playlist page HTML."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.5',
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"Error fetching page: {e}", file=sys.stderr)
def extract_simple(html):
    """Simple regex extraction of video titles and channel names."""
    video_ids = list(set(re.findall(r'"videoId":\s*"([a-zA-Z0-9_-]{11})"', html)))
    
    title_patterns = [
        r'"title"\s*:\s*\{\s*"runs"\s*:\s*\[\s*\{[^}]*"text"\s*:\s*"([^"]+)"',
        r'"title"\s*:\s*\{\s*"simpleText"\s*:\s*"([^"]+)"',
    ]
    titles = []
    for pat in title_patterns:
        titles.extend(re.findall(pat, html))
    
    channel_patterns = [
        r'"shortBylineText"\s*:\s*\{[^}]*"runs"\s*:\s*\[\s*\{[^}]*"text"\s*:\s*"([^"]+)"',
        r'"channelName"\s*:\s*"([^"]+)"',
        r'"author"\s*:\s*"([^"]+)"',
    ]
    channels = []
    for pat in channel_patterns:
        channels.extend(re.findall(pat, html))
    
    seen_t, ut = set(), []
    for t in titles:
        if t not in seen_t and t.strip():
            seen_t.add(t); ut.append(t)
    seen_c, uc = set(), []
    for c in channels:
        if c not in seen_c and c.strip():
            seen_c.add(c); uc.append(c)
    
    return ut, uc, video_ids

def main():
    print("=" * 70)
    print("EXTRACTOR: DROPSHIPPING - NEGOCIO 2")
    print("=" * 70)
    print(f"URL: {PLAYLIST_URL}\n")
    
    html = fetch_page(PLAYLIST_URL)
    if not html:
        print("ERROR: No se pudo obtener la página.")
        sys.exit(1)
    
    print(f"HTML descargado: {len(html)} bytes\n")
    
    titles, channels, video_ids = extract_simple(html)
    
    print(f"Videos encontrados: {len(titles)}")
    print(f"Canales encontrados: {len(channels)}")
    print(f"Video IDs: {len(video_ids)}\n")
    
    if titles:
        print("--- VIDEOS ---")
        for i, t in enumerate(titles[:60], 1):
            print(f"  {i:3d}. {t}")
        if len(titles) > 60:
            print(f"  ... y {len(titles)-60} mas")
    
    if channels:
        print("\n--- CANALES ---")
        for i, c in enumerate(channels, 1):
            print(f"  {i:3d}. {c}")
    
    with open('playlist_results.json', 'w', encoding='utf-8') as f:
        json.dump({'titles': titles, 'channels': channels, 'video_ids': video_ids}, f, ensure_ascii=False, indent=2)
    print("\nGuardado en playlist_results.json")
    
    print("\n" + "=" * 70)
    print("CANALES por frecuencia (favoritos):")
    print("=" * 70)
    for ch, count in Counter(channels).most_common(30):
        print(f"  {ch}: {count} videos")

if __name__ == '__main__':
    main()