"""
BulkImportPanel — importación masiva por URL: borradores en Shopify con validación sobre coste landed.

Una línea por producto: `URL  coste  envío`. Cada producto lleva SU coste y SU envío (el multiplicador se
mide sobre coste landed). Lo que falte se marca como DATA_GAP y no se crea nada en Shopify.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List

from app.ui.components.panel_kit import (
    BG_CARD, BG_TERTIARY, COLOR_SUCCESS, FONT_BODY, PanelBase, TXT, TXT_2, boton, etiqueta, llenar_tabla, tabla,
    tarjeta,
)

COLUMNAS = ("Estado", "Plataforma", "URL", "PVP", "Borrador Shopify", "Detalle")
_COLOR_ESTADO = {"success": "verde", "skipped": "ambar", "error": "rojo"}
_NOMBRE_ESTADO = {"success": "CREADO", "skipped": "OMITIDO", "error": "ERROR"}


class BulkImportPanel(PanelBase):
    def __init__(self, parent, db_manager=None, **kw):
        super().__init__(parent, db_manager=db_manager, titulo="📥 Importación masiva",
                         subtitulo="Pega una línea por producto con URL, coste y envío del proveedor. "
                                   "Cada uno se valida (mínimo x2 sobre coste landed) y se crea como BORRADOR en Shopify.",
                         scroll=False, **kw)
        self._corriendo = False
        self._construir()

    def _construir(self) -> None:
        entrada = tarjeta(self.cuerpo, "Productos")
        etiqueta(entrada, "Formato por línea:  URL  coste  envío   (envío 0 si es gratis; admite coma decimal)",
                 "suave").pack(fill=tk.X)
        self._texto = tk.Text(entrada, height=7, font=FONT_BODY, bg=BG_TERTIARY, fg=TXT, insertbackground=TXT,
                              relief=tk.FLAT, wrap="none")
        self._texto.pack(fill=tk.X, pady=(4, 8))

        fila = tk.Frame(entrada, bg=BG_CARD)
        fila.pack(fill=tk.X)
        m1, self._moneda, _ = self.campo(fila, "Divisa del proveedor", 10, "USD")
        m1.pack(side=tk.LEFT, padx=(0, 12))
        m2, self._lote, _ = self.campo(fila, "Etiqueta del lote (opcional)", 22)
        m2.pack(side=tk.LEFT, padx=(0, 12))
        self._boton = boton(fila, "▶ Importar como borradores", self._importar, COLOR_SUCCESS)
        self._boton.pack(side=tk.LEFT, pady=(14, 0))

        resultados = tarjeta(self.cuerpo, "Resultado", expand=True)
        marco, self._tree = tabla(resultados, COLUMNAS, (80, 100, 260, 80, 130, 380), alto=10)
        marco.pack(fill=tk.BOTH, expand=True)

    def _importar(self) -> None:
        if self._corriendo:
            return
        from app.services.bulk_url_importer import parsear_lineas

        items = parsear_lineas(self._texto.get("1.0", tk.END))
        if not items:
            self.aviso("Pega al menos una línea con una URL de producto.", "aviso")
            return
        moneda, lote = (self._moneda.get().strip().upper() or "USD"), self._lote.get().strip()
        self._corriendo = True
        self._boton.config(state=tk.DISABLED)
        self.aviso(f"Importando {len(items)} producto(s)…", "info")
        self.en_hilo(lambda: self._trabajo(items, moneda, lote), self._terminado, self._fallo)

    def _trabajo(self, items: List[Dict[str, Any]], moneda: str, lote: str) -> List[Dict]:
        from app.services.bulk_url_importer import BulkUrlImporter
        return BulkUrlImporter(self.db_manager).importar_lote(items, moneda_costo=moneda, etiqueta_lote=lote)

    def _terminado(self, resultados: List[Dict]) -> None:
        self._corriendo = False
        self._boton.config(state=tk.NORMAL)
        filas = [(_NOMBRE_ESTADO.get(r["status"], r["status"]), r["plataforma"].capitalize(), r["url"],
                  (r.get("validacion") or {}).get("pvp_calculado", "—"), r.get("shopify_draft_id") or "—",
                  r.get("error") or "OK") for r in resultados]
        llenar_tabla(self._tree, filas, [_COLOR_ESTADO.get(r["status"], "") for r in resultados])
        creados = sum(1 for r in resultados if r["status"] == "success")
        self.aviso(f"{creados} de {len(resultados)} borradores creados.", "ok" if creados else "aviso")

    def _fallo(self, exc: Exception) -> None:
        self._corriendo = False
        self._boton.config(state=tk.NORMAL)
        self.aviso(f"Error: {exc}", "error")
