"""
ImageRemover — Remoción de fondo de imágenes de producto para Shopify.

Métodos disponibles (en orden de preferencia):
  A) remove.bg API  — mejor calidad, 50 gratis/mes (requiere REMOVEBG_API_KEY)
  B) rembg local    — 100% gratis, sin API, requiere ~200MB modelo U2Net
  C) Fallback       — retorna error descriptivo con instrucciones

Salida siempre: PNG fondo blanco #FFFFFF, listo para Shopify.
"""

import io
import os
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class ImageRemover:
    """Remueve el fondo de imágenes de producto y las optimiza para Shopify."""

    SHOPIFY_MAX_SIZE = (2048, 2048)
    SHOPIFY_QUALITY = 85

    def __init__(self):
        self.removebg_key = os.getenv("REMOVEBG_API_KEY", "").strip()

    # ─────────────────────── API pública ──────────────────────────────

    def remover_fondo(self, imagen_path: str, output_path: str = None) -> dict:
        """
        Remueve el fondo de una imagen. Intenta remove.bg primero, luego rembg local.

        Args:
            imagen_path: ruta al archivo de imagen original
            output_path: ruta de salida (por defecto: mismo nombre con sufijo _nobg.png)

        Returns:
            {"ok": True, "output": "ruta.png", "metodo": "...", "size_kb": float}
            {"ok": False, "error": "..."}
        """
        imagen_path = Path(imagen_path)
        if not imagen_path.exists():
            return {"ok": False, "error": f"Archivo no encontrado: {imagen_path}"}

        if output_path is None:
            output_path = imagen_path.parent / f"{imagen_path.stem}_nobg.png"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if self.removebg_key:
            return self._remover_removebg(imagen_path, output_path)
        return self._remover_local(imagen_path, output_path)

    def convertir_webp(self, input_path: str, output_path: str = None,
                       quality: int = None) -> dict:
        """
        Convierte una imagen PNG a WebP optimizado para Shopify (< 200 KB).
        """
        try:
            from PIL import Image
        except ImportError:
            return {"ok": False, "error": "Pillow no instalado: pip install Pillow"}

        q = quality or self.SHOPIFY_QUALITY
        input_path = Path(input_path)
        if output_path is None:
            output_path = input_path.with_suffix(".webp")
        output_path = Path(output_path)

        try:
            img = Image.open(input_path)
            if img.mode in ("RGBA", "LA", "P"):
                fondo = Image.new("RGB", img.size, (255, 255, 255))
                fondo.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = fondo
            elif img.mode != "RGB":
                img = img.convert("RGB")

            img.thumbnail(self.SHOPIFY_MAX_SIZE, Image.LANCZOS)
            img.save(str(output_path), "WebP", quality=q, method=6)

            size_kb = round(output_path.stat().st_size / 1024, 1)
            return {
                "ok": True,
                "output": str(output_path),
                "size_kb": size_kb,
                "advertencia": "Imagen > 200KB — considera reducir quality" if size_kb > 200 else None,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def procesar_completo(self, imagen_path: str, carpeta_salida: str = None) -> dict:
        """
        Pipeline completo: quitar fondo → guardar PNG → convertir a WebP.
        """
        imagen_path = Path(imagen_path)
        if carpeta_salida:
            out_dir = Path(carpeta_salida)
        else:
            out_dir = imagen_path.parent

        png_path = out_dir / f"{imagen_path.stem}_nobg.png"
        webp_path = out_dir / f"{imagen_path.stem}_shopify.webp"

        paso1 = self.remover_fondo(str(imagen_path), str(png_path))
        if not paso1["ok"]:
            return paso1

        paso2 = self.convertir_webp(str(png_path), str(webp_path))
        if not paso2["ok"]:
            return paso2

        return {
            "ok": True,
            "png": str(png_path),
            "webp": str(webp_path),
            "size_kb": paso2["size_kb"],
            "metodo": paso1.get("metodo", "desconocido"),
            "advertencia": paso2.get("advertencia"),
        }

    # ─────────────────────── Métodos internos ─────────────────────────

    def _remover_removebg(self, imagen_path: Path, output_path: Path) -> dict:
        """Usa remove.bg API (50 gratis/mes)."""
        try:
            with open(imagen_path, "rb") as f:
                imagen_data = f.read()

            boundary = b"----GEMOSBoundary"
            body = (
                b"--" + boundary + b"\r\n"
                b'Content-Disposition: form-data; name="image_file"; filename="image.png"\r\n'
                b"Content-Type: image/png\r\n\r\n"
                + imagen_data + b"\r\n"
                b"--" + boundary + b"\r\n"
                b'Content-Disposition: form-data; name="size"\r\n\r\nauto\r\n'
                b"--" + boundary + b"\r\n"
                b'Content-Disposition: form-data; name="bg_color"\r\n\r\nffffff\r\n'
                b"--" + boundary + b"--\r\n"
            )

            req = urllib.request.Request(
                "https://api.remove.bg/v1.0/removebg",
                data=body,
                headers={
                    "X-Api-Key": self.removebg_key,
                    "Content-Type": f"multipart/form-data; boundary={boundary.decode()}",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status == 200:
                    with open(output_path, "wb") as out:
                        out.write(resp.read())
                    size_kb = round(output_path.stat().st_size / 1024, 1)
                    return {"ok": True, "output": str(output_path),
                            "metodo": "remove.bg", "size_kb": size_kb}
                return {"ok": False, "error": f"remove.bg HTTP {resp.status}"}

        except urllib.error.HTTPError as e:
            if e.code == 402:
                return {"ok": False, "error": "remove.bg: créditos agotados (50/mes gratis). Usa método local."}
            return {"ok": False, "error": f"remove.bg error {e.code}: {e.reason}"}
        except Exception as e:
            return {"ok": False, "error": f"remove.bg excepción: {e}"}

    def _remover_local(self, imagen_path: Path, output_path: Path) -> dict:
        """Usa rembg (modelo U2Net local, 100% gratis). Descarga ~200MB la primera vez."""
        try:
            from rembg import remove
            from PIL import Image
        except ImportError:
            return {
                "ok": False,
                "error": (
                    "Para remoción local instala: pip install rembg Pillow\n"
                    "O configura REMOVEBG_API_KEY en .env para usar remove.bg (50 gratis/mes)."
                ),
            }

        try:
            with open(imagen_path, "rb") as f:
                resultado = remove(f.read())

            img = Image.open(io.BytesIO(resultado)).convert("RGBA")
            fondo = Image.new("RGBA", img.size, (255, 255, 255, 255))
            fondo.paste(img, mask=img.split()[3])
            fondo.convert("RGB").save(str(output_path), "PNG", optimize=True)

            size_kb = round(output_path.stat().st_size / 1024, 1)
            return {"ok": True, "output": str(output_path),
                    "metodo": "rembg-local", "size_kb": size_kb}
        except Exception as e:
            return {"ok": False, "error": f"rembg error: {e}"}
