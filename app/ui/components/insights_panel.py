"""
InsightsPanel — los insights de la KB (productos, fórmulas de conversión, operaciones), como /insights.

Filtra por tipo, canal y texto, con totales reales y paginación. Usa `insights_service`, el mismo
servicio que la web y que el contexto del Agente IA.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List

from app.services import insights_service as ins
from app.ui.components.panel_kit import (
    BG_CARD, BG_PRIMARY, BG_TERTIARY, COLOR_PRIMARY, COLOR_SECONDARY, COLOR_SUCCESS, COLOR_WARNING, FONT_SM, KPI,
    PanelBase, TXT, TXT_2, TXT_3, boton, etiqueta, llenar_tabla, tabla,
)

_TIPOS = [("", "Todos"), ("product_trends", "Productos y tendencias"), ("conversion_formulas", "Fórmulas de conversión"),
          ("operations_traffic", "Operaciones y tráfico")]
_ETIQUETA = {"product_trends": "Producto", "conversion_formulas": "Conversión", "operations_traffic": "Operaciones"}
PAGINA = 50


class InsightsPanel(PanelBase):
    def __init__(self, parent, db_manager=None, **kw):
        super().__init__(parent, db_manager=db_manager, titulo="⚡ Insights de la KB",
                         subtitulo="Lo que la IA extrajo de los vídeos de tus mentores. Busca y filtra por tipo o canal.",
                         scroll=False, **kw)
        self.db = self.db_manager.db_path
        self._filas: List[Dict[str, Any]] = []
        self._total = 0
        boton(self.acciones, "🔄", self.cargar, BG_TERTIARY, TXT_2).pack(side=tk.LEFT)
        self._kpis_marco = tk.Frame(self.cuerpo, bg=BG_PRIMARY)
        self._kpis_marco.pack(fill=tk.X, pady=(0, 8))
        self._kpis: Dict[str, KPI] = {}
        for i, (k, t) in enumerate([("total", "Total"), ("product_trends", "Productos"), ("conversion_formulas", "Fórmulas"),
                                    ("operations_traffic", "Operaciones")]):
            self._kpis_marco.columnconfigure(i, weight=1)
            self._kpis[k] = KPI(self._kpis_marco, t)
            self._kpis[k].grid(row=0, column=i, sticky="nsew", padx=3)

        filtros = tk.Frame(self.cuerpo, bg=BG_PRIMARY)
        filtros.pack(fill=tk.X, pady=(0, 6))
        self._tipo = tk.StringVar(value="Todos")
        cb = ttk.Combobox(filtros, textvariable=self._tipo, values=[n for _, n in _TIPOS], state="readonly", width=24)
        cb.pack(side=tk.LEFT)
        cb.bind("<<ComboboxSelected>>", lambda e: self.cargar())
        self._canal = tk.StringVar(value="Todos los canales")
        self._cb_canal = ttk.Combobox(filtros, textvariable=self._canal, values=["Todos los canales"], state="readonly", width=28)
        self._cb_canal.pack(side=tk.LEFT, padx=6)
        self._cb_canal.bind("<<ComboboxSelected>>", lambda e: self.cargar())
        self._buscar = tk.StringVar()
        ent = ttk.Entry(filtros, textvariable=self._buscar, width=30)
        ent.pack(side=tk.LEFT)
        ent.bind("<Return>", lambda e: self.cargar())
        boton(filtros, "Buscar", self.cargar, COLOR_PRIMARY).pack(side=tk.LEFT, padx=6)
        self._contador = etiqueta(filtros, "", "suave")
        self._contador.pack(side=tk.RIGHT)

        panel = ttk.PanedWindow(self.cuerpo, orient=tk.VERTICAL)
        panel.pack(fill=tk.BOTH, expand=True)
        arriba = tk.Frame(panel, bg=BG_CARD)
        abajo = tk.Frame(panel, bg=BG_CARD, highlightthickness=1, highlightbackground=BG_TERTIARY)
        panel.add(arriba, weight=3)
        panel.add(abajo, weight=1)
        marco, self._tree = tabla(arriba, ["Tipo", "Insight", "Nicho / marco", "Canal", "Vídeo"], [100, 240, 160, 150, 300], alto=12)
        marco.pack(fill=tk.BOTH, expand=True)
        self._tree.bind("<<TreeviewSelect>>", self._detalle)
        self._mas = boton(arriba, "Cargar más", self._cargar_mas, BG_TERTIARY, TXT_2)
        self._texto = tk.Text(abajo, wrap="word", height=6, bg=BG_CARD, fg=TXT, relief=tk.FLAT, font=("Segoe UI", 10), padx=10, pady=8)
        self._texto.pack(fill=tk.BOTH, expand=True)
        self._texto.insert("1.0", "Elige un insight para leerlo completo.")
        self._texto.config(state="disabled")
        self.cargar()

    def _tipo_clave(self) -> str:
        return next(k for k, n in _TIPOS if n == self._tipo.get())

    def cargar(self) -> None:
        res = ins.insights_resumen(self.db)
        self._kpis["total"].set(str(res["total"]), "insights en la KB")
        for k in ("product_trends", "conversion_formulas", "operations_traffic"):
            self._kpis[k].set(str(res["por_tipo"].get(k, 0)))
        nombres = [c["canal"] for c in res["canales"]]
        self._cb_canal.config(values=["Todos los canales"] + nombres)
        self._filas = []
        self._pedir(0)

    def _cargar_mas(self) -> None:
        self._pedir(len(self._filas))

    def _pedir(self, offset: int) -> None:
        canal = "" if self._canal.get() == "Todos los canales" else self._canal.get()
        d = ins.query_insights(self.db, tipo=self._tipo_clave(), buscar=self._buscar.get(), canal=canal,
                               limite=PAGINA, offset=offset, preview_chars=900)
        self._filas += d["items"]
        self._total = d["total"]
        llenar_tabla(self._tree, [[_ETIQUETA.get(f["source_table"], f["source_table"]), f["titulo"] or "—", f["subtitulo"] or "",
                                   f["channel_name"] or "?", f["video_title"] or ""] for f in self._filas])
        self._contador.config(text=f"{len(self._filas)} de {self._total}")
        if len(self._filas) < self._total:
            self._mas.pack(fill=tk.X, pady=(4, 0))
        else:
            self._mas.pack_forget()

    def _detalle(self, _e=None) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        f = self._filas[self._tree.get_children().index(sel[0])]
        url = f"https://www.youtube.com/watch?v={f['video_id']}" if f.get("video_id") else ""
        t = self._texto
        t.config(state="normal")
        t.delete("1.0", tk.END)
        t.insert("1.0", f"{f['titulo']}\n{f['subtitulo'] or ''}\n\n{f['content_preview']}\n\nFuente: {f['channel_name'] or '?'} · "
                        f"«{f['video_title'] or '?'}»" + (f"\n{url}" if url else ""))
        t.config(state="disabled")
