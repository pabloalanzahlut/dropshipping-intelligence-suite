"""
BulkImportPanel — importación masiva por URL: borradores en Shopify con validación sobre coste landed.

Una línea por producto: `URL  coste  envío  [img=URL …]  [var=Color:Rojo/Azul …]`. Cada producto lleva SU coste
y SU envío (el multiplicador se mide sobre coste landed). Lo que falte se marca como DATA_GAP y no se crea nada.
"""
from __future__ import annotations

import tkinter as tk
from typing import Any, Dict, List

from app.ui.components.panel_kit import (
    BG_CARD, BG_TERTIARY, COLOR_SUCCESS, FONT_BODY, PanelBase, TXT, TXT_2, boton, etiqueta, llenar_tabla, tabla,
    tarjeta,
)

COLUMNAS = ("Estado", "Plataforma", "Producto", "PVP", "Mult.", "Img", "Var.", "Borrador", "Sheets", "Detalle")
_COLOR_ESTADO = {"success": "verde", "skipped": "ambar", "error": "rojo", "preview": ""}
_NOMBRE_ESTADO = {"success": "CREADO", "skipped": "OMITIDO", "error": "ERROR", "preview": "LISTO"}


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
        etiqueta(entrada, "Por línea:  URL  coste  envío   (envío 0 si es gratis · coma decimal admitida)\n"
                          "Opcional:  img=URL (repetible)   var=Color:Rojo/Azul (usa _ para espacios)", "suave").pack(fill=tk.X)
        self._texto = tk.Text(entrada, height=7, font=FONT_BODY, bg=BG_TERTIARY, fg=TXT, insertbackground=TXT,
                              relief=tk.FLAT, wrap="none")
        self._texto.pack(fill=tk.X, pady=(4, 8))

        fila = tk.Frame(entrada, bg=BG_CARD)
        fila.pack(fill=tk.X)
        m1, self._moneda, _ = self.campo(fila, "Divisa del proveedor", 10, "USD")
        m1.pack(side=tk.LEFT, padx=(0, 12))
        m2, self._lote, _ = self.campo(fila, "Etiqueta del lote (opcional)", 22)
        m2.pack(side=tk.LEFT, padx=(0, 12))
        self._psico = tk.BooleanVar(value=True)
        self._hoja = tk.BooleanVar(value=True)
        for texto, var in (("Precio ,99", self._psico), ("Anotar en Sheets", self._hoja)):
            tk.Checkbutton(fila, text=texto, variable=var, bg=BG_CARD, fg=TXT_2, selectcolor=BG_TERTIARY,
                           activebackground=BG_CARD, activeforeground=TXT).pack(side=tk.LEFT, padx=(0, 10), pady=(14, 0))
        self._b_prev = boton(fila, "👁 Previsualizar", lambda: self._lanzar(False), BG_TERTIARY, TXT_2)
        self._b_prev.pack(side=tk.LEFT, padx=(0, 6), pady=(14, 0))
        self._b_imp = boton(fila, "▶ Crear borradores", lambda: self._lanzar(True), COLOR_SUCCESS)
        self._b_imp.pack(side=tk.LEFT, pady=(14, 0))

        resultados = tarjeta(self.cuerpo, "Resultado", expand=True)
        marco, self._tree = tabla(resultados, COLUMNAS, (70, 90, 200, 70, 50, 40, 40, 110, 70, 300), alto=10)
        marco.pack(fill=tk.BOTH, expand=True)

    def _botones(self, activos: bool) -> None:
        estado = tk.NORMAL if activos else tk.DISABLED
        self._b_prev.config(state=estado)
        self._b_imp.config(state=estado)

    def _lanzar(self, crear: bool) -> None:
        if self._corriendo:
            return
        from app.services.bulk_url_importer import parsear_lineas

        items = parsear_lineas(self._texto.get("1.0", tk.END))
        if not items:
            self.aviso("Pega al menos una línea con una URL de producto.", "aviso")
            return
        ajustes = (self._moneda.get().strip().upper() or "USD", self._lote.get().strip(),
                   self._psico.get(), self._hoja.get())
        self._corriendo = True
        self._botones(False)
        self.aviso(f"{'Importando' if crear else 'Calculando'} {len(items)} producto(s)…", "info")
        self.en_hilo(lambda: self._trabajo(items, crear, *ajustes), lambda r: self._terminado(r, crear), self._fallo)

    def _trabajo(self, items: List[Dict[str, Any]], crear: bool, moneda: str, lote: str, psico: bool,
                 hoja: bool) -> List[Dict]:
        from app.services.bulk_url_importer import BulkUrlImporter
        imp = BulkUrlImporter(self.db_manager)
        if crear:
            return imp.importar_lote(items, moneda_costo=moneda, etiqueta_lote=lote, precio_psico=psico,
                                     sincronizar_hoja=hoja)
        return imp.previsualizar(items, moneda_costo=moneda, precio_psico=psico)

    def _terminado(self, resultados: List[Dict], crear: bool) -> None:
        self._corriendo = False
        self._botones(True)
        filas = []
        for r in resultados:
            v = r.get("validacion") or {}
            filas.append((_NOMBRE_ESTADO.get(r["status"], r["status"]), r["plataforma"].capitalize(),
                          r.get("titulo") or r["url"], r.get("pvp") if r.get("pvp") is not None else "—",
                          v.get("multiplicador", "—"), r.get("imagenes", 0), r.get("variantes", 1),
                          r.get("shopify_draft_id") or "—", r.get("hoja") or "—",
                          r.get("error") or " · ".join(([r["aviso"]] if r.get("aviso") else [])
                                                      + v.get("advertencias", [])) or "OK"))
        llenar_tabla(self._tree, filas, [_COLOR_ESTADO.get(r["status"], "") for r in resultados])
        if crear:
            creados = sum(1 for r in resultados if r["status"] == "success")
            self.aviso(f"{creados} de {len(resultados)} borradores creados.", "ok" if creados else "aviso")
        else:
            listos = sum(1 for r in resultados if r["status"] == "preview")
            self.aviso(f"{listos} de {len(resultados)} listos para importar (no se ha creado nada).", "info")

    def _fallo(self, exc: Exception) -> None:
        self._corriendo = False
        self._botones(True)
        self.aviso(f"Error: {exc}", "error")
