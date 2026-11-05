"""
BulkImportPanel — Panel de Importación Masiva por URL
======================================================
UI para pegar URLs de AliExpress/CJ/Temu e importar como borradores Shopify.
"""

import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from app.ui.components.data_table import DataTable
from app.ui.components.progress_bar import ProgressBar
from app.ui.themes.design_tokens import TYPOGRAPHY


class BulkImportPanel(ttk.Frame):
    """Panel de importación masiva: pegar URLs → validar → borrador Shopify."""

    COL_NAMES = ["URL", "Plataforma", "Estado", "Shopify Draft ID", "Detalle"]
    COL_WIDTHS = [260, 100, 90, 130, 220]

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._running = False
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)

        # Título
        ttk.Label(
            self, text="Importación Masiva de Productos",
            font=(TYPOGRAPHY.heading_family, 14, "bold")
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 4))

        ttk.Label(
            self,
            text="Pega una URL por línea (AliExpress, CJ Dropshipping, Temu)",
            font=(TYPOGRAPHY.body_family, 9),
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 8))

        # Área de URLs
        url_frame = ttk.LabelFrame(self, text="URLs de productos")
        url_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=4)
        url_frame.columnconfigure(0, weight=1)

        self._url_text = tk.Text(url_frame, height=8, font=(TYPOGRAPHY.body_family, 10), wrap="word")
        self._url_text.grid(row=0, column=0, sticky="ew", padx=8, pady=8)

        # Parámetros financieros
        params_frame = ttk.Frame(self)
        params_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=4)

        ttk.Label(params_frame, text="Costo origen (USD):").pack(side=tk.LEFT, padx=(0, 4))
        self._costo_var = tk.StringVar()
        ttk.Entry(params_frame, textvariable=self._costo_var, width=10).pack(side=tk.LEFT, padx=(0, 16))

        ttk.Label(params_frame, text="Peso kg:").pack(side=tk.LEFT, padx=(0, 4))
        self._peso_var = tk.StringVar(value="0.3")
        ttk.Entry(params_frame, textvariable=self._peso_var, width=8).pack(side=tk.LEFT)

        # Botón importar
        self._btn_importar = ttk.Button(
            self, text="▶  Importar Todo", command=self._on_importar
        )
        self._btn_importar.grid(row=4, column=0, sticky="w", padx=16, pady=8)

        # Barra de progreso
        self._progress = ProgressBar(self)
        self._progress.grid(row=5, column=0, sticky="ew", padx=16, pady=4)

        # Tabla de resultados
        self._table = DataTable(
            self,
            columns=self.COL_NAMES,
            col_widths=self.COL_WIDTHS,
            enable_search=False,
            enable_export=True,
            rows_per_page=25,
        )
        self._table.grid(row=6, column=0, sticky="nsew", padx=16, pady=(4, 16))
        self.rowconfigure(6, weight=1)

    def _on_importar(self):
        if self._running:
            return

        raw = self._url_text.get("1.0", tk.END).strip()
        urls = [u.strip() for u in raw.splitlines() if u.strip()]
        if not urls:
            messagebox.showwarning("Sin URLs", "Pega al menos una URL antes de importar.")
            return

        costo_str = self._costo_var.get().strip()
        if not costo_str:
            messagebox.showwarning(
                "Costo requerido",
                "Ingresa el costo de origen en USD para aplicar la regla 3x."
            )
            return

        try:
            costo = float(costo_str)
            peso = float(self._peso_var.get() or "0.3")
        except ValueError:
            messagebox.showerror("Valor inválido", "Costo y peso deben ser números.")
            return

        self._running = True
        self._btn_importar.config(state="disabled")
        self._table.load_data([])
        self._progress.set(0)

        threading.Thread(
            target=self._run_importacion,
            args=(urls, costo, peso),
            daemon=True,
        ).start()

    def _run_importacion(self, urls: list, costo: float, peso: float):
        from app.services.bulk_url_importer import BulkUrlImporter

        total = len(urls)
        importer = BulkUrlImporter()
        resultados = []

        for i, url in enumerate(urls, 1):
            parcial = importer.importar_lote([url], costo_origen=costo, peso_kg=peso)
            resultados.extend(parcial)
            self.after(0, self._progress.set, int(i / total * 100))

        rows = [
            {
                "URL": r["url"][:60] + ("…" if len(r["url"]) > 60 else ""),
                "Plataforma": r["plataforma"].capitalize(),
                "Estado": r["status"].upper(),
                "Shopify Draft ID": r.get("shopify_draft_id") or "—",
                "Detalle": r.get("error") or "OK",
            }
            for r in resultados
        ]

        self.after(0, self._tabla_actualizar, rows)
        self.after(0, self._finalizar)

    def _tabla_actualizar(self, rows):
        self._table.load_data(rows)

    def _finalizar(self):
        self._running = False
        self._btn_importar.config(state="normal")
        self._progress.set(100)
