"""
imagenes_panel.py — Panel de escritorio para quitar el fondo de imágenes de producto.

Equivalente de escritorio de /imagenes en la web: usa el mismo servicio
(`app.services.image_remover.ImageRemover`), así que el método activo
(remove.bg vs rembg-local) y la carpeta de salida son idénticos en ambas apps.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Optional

from app.ui.components.panel_kit import (
    COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, PanelBase, boton, etiqueta, tarjeta,
)


def _carpeta_salida() -> Path:
    from app.config.path_manager import PathManager
    carpeta = PathManager.get_paths()["data"] / "imagenes_producto"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def _abrir_carpeta(ruta: Path) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(ruta))          # noqa: S606 — abrir el explorador, no ejecutar código
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(ruta)])
        else:
            subprocess.Popen(["xdg-open", str(ruta)])
    except OSError:
        pass


class ImagenesPanel(PanelBase):
    """Quita el fondo de una imagen de producto (remove.bg o rembg local)."""

    def __init__(self, parent, db_manager=None, **kw):
        super().__init__(parent, db_manager=db_manager, titulo="🖼️ Imágenes de Producto",
                         subtitulo="Quita el fondo y optimiza la imagen para Shopify — mismo servicio que la web.",
                         scroll=False, **kw)
        self._ruta_actual: Optional[Path] = None
        self._carpeta = _carpeta_salida()
        self._construir_ui()
        self._refrescar_estado()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _construir_ui(self) -> None:
        boton(self.acciones, "🔄 Comprobar método activo", self._refrescar_estado, COLOR_PRIMARY).pack(side=tk.RIGHT)

        fila = tk.Frame(self.cuerpo, bg=self.cuerpo["bg"])
        fila.pack(fill=tk.X, pady=(0, 12))

        card_metodo = tarjeta(fila, "Método activo", acento=COLOR_PRIMARY, lado=tk.LEFT, expand=True)
        self._lbl_metodo = etiqueta(card_metodo, "Comprobando…", tipo="suave")
        self._lbl_metodo.pack(fill=tk.X)

        card_archivo = tarjeta(self.cuerpo, "Procesar imagen", acento=COLOR_PRIMARY, expand=False)
        barra = tk.Frame(card_archivo, bg=card_archivo["bg"])
        barra.pack(fill=tk.X, pady=(0, 10))
        boton(barra, "📂 Elegir imagen…", self._elegir_imagen, COLOR_PRIMARY).pack(side=tk.LEFT)
        self._lbl_archivo = etiqueta(barra, "Ningún archivo elegido.", tipo="tenue")
        self._lbl_archivo.pack(side=tk.LEFT, padx=(10, 0))

        self._btn_procesar = boton(card_archivo, "✨ Quitar fondo", self._procesar, COLOR_SUCCESS)
        self._btn_procesar.pack(anchor="w")
        self._btn_procesar.config(state=tk.DISABLED)

        self._resultado = tk.Frame(card_archivo, bg=card_archivo["bg"])
        self._resultado.pack(fill=tk.X, pady=(12, 0))

    # ── acciones ─────────────────────────────────────────────────────────────

    def _refrescar_estado(self) -> None:
        def trabajo():
            from app.services.image_remover import ImageRemover
            remover = ImageRemover()
            try:
                import rembg  # noqa: F401
                rembg_local = True
            except ImportError:
                rembg_local = False
            return {"removebg": bool(remover.removebg_key), "rembg_local": rembg_local}

        def listo(estado):
            if estado["removebg"]:
                self._lbl_metodo.config(text="remove.bg (API) — 50 gratis/mes", fg=COLOR_SUCCESS)
            elif estado["rembg_local"]:
                self._lbl_metodo.config(text="rembg (local) — gratis, sin API", fg=COLOR_SUCCESS)
            else:
                self._lbl_metodo.config(
                    text="Ninguno configurado — añade REMOVEBG_API_KEY o instala rembg", fg=COLOR_WARNING)

        self.en_hilo(trabajo, listo)

    def _elegir_imagen(self) -> None:
        ruta = filedialog.askopenfilename(
            title="Elegir imagen de producto",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.webp"), ("Todos", "*.*")],
        )
        if not ruta:
            return
        self._ruta_actual = Path(ruta)
        self._lbl_archivo.config(text=self._ruta_actual.name, fg="#e8ecff")
        self._btn_procesar.config(state=tk.NORMAL)
        for w in self._resultado.winfo_children():
            w.destroy()

    def _procesar(self) -> None:
        if not self._ruta_actual:
            return
        ruta = self._ruta_actual
        self._btn_procesar.config(state=tk.DISABLED)
        self.aviso("Procesando…", "info")

        def trabajo():
            from app.services.image_remover import ImageRemover
            return ImageRemover().procesar_completo(str(ruta), str(self._carpeta))

        self.en_hilo(trabajo, self._mostrar_resultado, self._mostrar_error)

    def _mostrar_resultado(self, resultado: dict) -> None:
        self._btn_procesar.config(state=tk.NORMAL)
        for w in self._resultado.winfo_children():
            w.destroy()
        if not resultado.get("ok"):
            self._mostrar_error(RuntimeError(resultado.get("error", "Error desconocido")))
            return
        self.aviso(f"Listo — método: {resultado.get('metodo', '—')}", "ok")
        etiqueta(self._resultado, f"✓ PNG: {resultado['png']}", tipo="ok").pack(anchor="w")
        etiqueta(self._resultado, f"✓ WebP: {resultado['webp']} ({resultado.get('size_kb', 0):.0f} KB)",
                 tipo="ok").pack(anchor="w")
        if resultado.get("advertencia"):
            etiqueta(self._resultado, f"⚠ {resultado['advertencia']}", tipo="aviso").pack(anchor="w")
        boton(self._resultado, "📂 Abrir carpeta de salida",
              lambda: _abrir_carpeta(self._carpeta), COLOR_PRIMARY).pack(anchor="w", pady=(8, 0))

    def _mostrar_error(self, exc: Exception) -> None:
        self._btn_procesar.config(state=tk.NORMAL)
        self.aviso(f"Error: {exc}", "error")
        for w in self._resultado.winfo_children():
            w.destroy()
        etiqueta(self._resultado, f"✗ {exc}", tipo="error").pack(anchor="w")
