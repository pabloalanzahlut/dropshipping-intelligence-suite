"""
propuestas_panel.py — Revisión de las propuestas que escribe `self_improve.py`.

Solo lectura y marcado (pendiente/aprobada/rechazada) — nunca ejecuta nada. Equivalente
de escritorio de /propuestas en la web; usa el mismo servicio `propuestas_review`.
"""
from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List

from app.ui.components.panel_kit import (
    COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, Dialogo, PanelBase, boton, etiqueta, llenar_tabla, tabla,
)

_FILTROS = [("", "Todas"), ("pendiente", "Pendientes"), ("aprobada", "Aprobadas"), ("rechazada", "Rechazadas")]


def _resumen_corto(resumen_json: str) -> str:
    try:
        d = json.loads(resumen_json)
        return f"{d.get('productos_evaluados', '—')} productos evaluados · ROAS global {d.get('roas_global', '—')}"
    except (ValueError, TypeError):
        return (resumen_json or "")[:120]


class PropuestasPanel(PanelBase):
    """Lista las propuestas de self_improve y permite marcarlas tras revisarlas."""

    def __init__(self, parent, db_manager=None, **kw):
        super().__init__(parent, db_manager=db_manager, titulo="📝 Propuestas IA",
                         subtitulo="El loop nocturno (03:00) propone ajustes aquí a partir de métricas reales. "
                                   "Nunca aplica nada solo.", scroll=False, **kw)
        self._filtro = tk.StringVar(value="")
        self._filas: List[Dict[str, Any]] = []
        self._construir_ui()
        self._cargar()

    def _construir_ui(self) -> None:
        barra = tk.Frame(self.cuerpo, bg=self.cuerpo["bg"])
        barra.pack(fill=tk.X, pady=(0, 10))
        for valor, texto in _FILTROS:
            boton(barra, texto, lambda v=valor: self._cambiar_filtro(v), COLOR_PRIMARY).pack(side=tk.LEFT, padx=(0, 6))
        boton(self.acciones, "🔄 Refrescar", self._cargar, COLOR_PRIMARY).pack(side=tk.RIGHT)

        marco, self._tree = tabla(
            self.cuerpo, ["ID", "Fecha", "Resumen", "Estado"], [50, 140, 420, 100], alto=16)
        marco.pack(fill=tk.BOTH, expand=True)
        self._tree.bind("<Double-1>", self._abrir_detalle)

    def _cambiar_filtro(self, valor: str) -> None:
        self._filtro.set(valor)
        self._cargar()

    def _cargar(self) -> None:
        def trabajo():
            from app.services import propuestas_review
            return propuestas_review.listar(self.db_manager.db_path, self._filtro.get())

        self.en_hilo(trabajo, self._pintar)

    def _pintar(self, filas: List[Dict[str, Any]]) -> None:
        self._filas = filas
        etiquetas = ["verde" if f["estado"] == "aprobada" else "rojo" if f["estado"] == "rechazada" else "ambar"
                     for f in filas]
        llenar_tabla(self._tree, [
            (f["id"], f["creado_at"], _resumen_corto(f["resumen"]), f["estado"]) for f in filas
        ], etiquetas)
        self.aviso(f"{len(filas)} propuesta(s).", "info")

    def _abrir_detalle(self, _evt=None) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        idx = self._tree.index(sel[0])
        if idx >= len(self._filas):
            return
        p = self._filas[idx]

        dlg = Dialogo(self, f"Propuesta #{p['id']}", ancho=640)
        texto = tk.Text(dlg.cuerpo, height=18, wrap=tk.WORD, bg="#08091a", fg="#a8b0d8",
                        relief=tk.FLAT, font=("Consolas", 9))
        texto.insert("1.0", p.get("analisis_md", ""))
        texto.config(state=tk.DISABLED)
        texto.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        if p["estado"] == "pendiente":
            fila_botones = tk.Frame(dlg.cuerpo, bg=dlg.cuerpo["bg"])
            fila_botones.pack(fill=tk.X)
            boton(fila_botones, "✓ Aprobar", lambda: self._marcar(p["id"], "aprobada", dlg),
                 COLOR_SUCCESS).pack(side=tk.LEFT)
            boton(fila_botones, "✗ Rechazar", lambda: self._marcar(p["id"], "rechazada", dlg),
                 COLOR_WARNING).pack(side=tk.LEFT, padx=(8, 0))
        else:
            etiqueta(dlg.cuerpo, f"Estado: {p['estado']} · revisado {p.get('revisado_at') or '—'}",
                    tipo="suave").pack(anchor="w")

    def _marcar(self, propuesta_id: int, estado: str, dialogo: Dialogo) -> None:
        def trabajo():
            from app.services import propuestas_review
            return propuestas_review.marcar(self.db_manager.db_path, propuesta_id, estado)

        def listo(_resultado):
            dialogo.destroy()
            self._cargar()

        self.en_hilo(trabajo, listo)
