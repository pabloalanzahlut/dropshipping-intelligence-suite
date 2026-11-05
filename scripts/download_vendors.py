"""
download_vendors.py — Descarga librerías JS/CSS a app/static/vendor/
Ejecutar una vez antes de desplegar sin acceso a CDN.

Uso:
    python scripts/download_vendors.py
"""
import pathlib
import urllib.request

VENDORS = [
    (
        "https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js",
        "app/static/vendor/alpine.min.js",
    ),
]

BASE = pathlib.Path(__file__).parent.parent

for url, dest in VENDORS:
    out = BASE / dest
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        print(f"  ✓ ya existe: {dest}")
        continue
    print(f"  ↓ descargando {dest} …", end=" ", flush=True)
    urllib.request.urlretrieve(url, out)
    print(f"{out.stat().st_size // 1024} KB")

print("Done.")
