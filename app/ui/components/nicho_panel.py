"""
nicho_panel.py — Investigar nicho: 10 ángulos de ataque + ranking ponderado.

Equivalente de escritorio de /nicho en la web; usa el mismo servicio `nicho_research`.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List

from app.ui.components.panel_kit import (
    COLOR_PRIMARY, PanelBase, boton, etiqueta, llenar_tabla, tabla, tarjeta,
)


class NichoPanel(PanelBase):
    """Genera y guarda informes de nicho (10 ángulos + ranking)."""

    def __init__(self, parent, db_manager=None, **kw):
        super().__init__(parent, db_manager=db_manager, titulo="🧭 Investigar Nicho",
                         subtitulo="10 ángulos de ataque por nicho — urgencia 40% · facilidad ≥3x 30% "
                                   "· targeting 20% · riesgo logístico 10%.", scroll=False, **kw)
        self._ultimo: Dict[str, Any] = {}
        self._historial: List[Dict[str, Any]] = []
        self._construir_ui()
        self._cargar_historial()

    def _construir_ui(self) -> None:
        card_form = tarjeta(self.cuerpo, "Nueva investigación", acento=COLOR_PRIMARY, expand=False)
        _, self._var_nicho, ent_nicho = self.campo(card_form, "Nicho", ancho=40)
        ent_nicho.focus_set()
        _, self._var_contexto, _ = self.campo(card_form, "Contexto adicional (opcional)", ancho=40)
        boton(card_form, "🔍 Investigar", self._investigar, COLOR_PRIMARY).pack(anchor="w", pady=(10, 0))

        fila = tk.Frame(self.cuerpo, bg=self.cuerpo["bg"])
        fila.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        card_resultado = tarjeta(fila, "Resultado", acento=COLOR_PRIMARY, lado=tk.LEFT, expand=True)
        self._lbl_resumen = etiqueta(card_resultado, "Sin investigar todavía.", tipo="suave", wrap=360)
        self._lbl_resumen.pack(fill=tk.X, pady=(0, 8))
        marco_rank, self._tree_rank = tabla(card_resultado, ["#", "Score", "Problema", "Hook"], [30, 50, 200, 200], alto=10)
        marco_rank.pack(fill=tk.BOTH, expand=True)

        card_hist = tarjeta(fila, "Historial", acento=COLOR_PRIMARY, lado=tk.RIGHT, expand=True)
        marco_h, self._tree_hist = tabla(card_hist, ["Nicho", "Fecha"], [140, 140], alto=10)
        marco_h.pack(fill=tk.BOTH, expand=True)
        self._tree_hist.bind("<Double-1>", self._abrir_historico)

    def _investigar(self) -> None:
        nicho = self._var_nicho.get().strip()
        if not nicho:
            self.aviso("Escribe un nicho antes de investigar.", "aviso")
            return
        contexto = self._var_contexto.get().strip()
        self.aviso("Investigando…", "info")

        def trabajo():
            from app.services import nicho_research
            resultado = nicho_research.investigar(nicho, contexto)
            resultado["id"] = nicho_research.guardar_investigacion(
                self.db_manager.db_path, resultado["nicho"], resultado["resumen"],
                resultado["angulos"], resultado["ranking"])
            return resultado

        self.en_hilo(trabajo, self._pintar_resultado, lambda e: self.aviso(f"Error: {e}", "error"))

    def _pintar_resultado(self, resultado: Dict[str, Any]) -> None:
        self._ultimo = resultado
        self.aviso("Listo." if resultado.get("generado") else "El modelo no respondió.", "ok")
        self._lbl_resumen.config(text=resultado.get("resumen") or "(sin resumen)")
        angulos_por_id = {a.get("id"): a for a in resultado.get("angulos", [])}
        filas = []
        for r in resultado.get("ranking", []):
            a = angulos_por_id.get(r.get("angulo_id"), {})
            filas.append((r.get("angulo_id"), r.get("score"), (a.get("problema") or "")[:60], (a.get("hook") or "")[:60]))
        llenar_tabla(self._tree_rank, filas)
        self._cargar_historial()

    def _cargar_historial(self) -> None:
        def trabajo():
            from app.services import nicho_research
            return nicho_research.listar(self.db_manager.db_path)

        def listo(filas):
            self._historial = filas
            llenar_tabla(self._tree_hist, [(f["nicho"], f["creado_at"]) for f in filas])

        self.en_hilo(trabajo, listo)

    def _abrir_historico(self, _evt=None) -> None:
        sel = self._tree_hist.selection()
        if not sel:
            return
        idx = self._tree_hist.index(sel[0])
        if idx < len(self._historial):
            self._pintar_resultado(self._historial[idx])
