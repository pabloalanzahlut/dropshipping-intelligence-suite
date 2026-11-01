"""
CopywritingPanel - UI para Generación de Copys AIDA
Permite generar copys, validar superlativos y exportar resultados.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
import threading
import json
from datetime import datetime

from app.services.copywriting_engine import CopywrightingEngine


class CopywritingPanel(ttk.Frame):
    """Panel UI para generación y validación de copys AIDA."""

    def __init__(self, parent, db_manager=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.db_manager = db_manager
        self.engine = CopywrightingEngine(db_manager=db_manager)
        self.copy_actual = None
        self.variantes_actuales = []
        self.productos_db = []

        self._build_ui()

    def _build_ui(self):
        """Construye la interfaz gráfica completa."""

        # ====== Sección Superior: Generar Copy AIDA ======
        gen_frame = ttk.LabelFrame(self, text="Generar Copy AIDA", padding=10)
        gen_frame.pack(fill=tk.X, padx=10, pady=5)

        # Fila 1: Nombre y Categoría
        row1 = ttk.Frame(gen_frame)
        row1.pack(fill=tk.X, pady=2)

        ttk.Label(row1, text="Producto:", width=12).pack(side=tk.LEFT, padx=2)
        self.entry_nombre = ttk.Entry(row1, width=30)
        self.entry_nombre.pack(side=tk.LEFT, padx=2)

        ttk.Label(row1, text="Categoría:", width=10).pack(side=tk.LEFT, padx=2)
        self.entry_categoria = ttk.Entry(row1, width=25)
        self.entry_categoria.pack(side=tk.LEFT, padx=2)

        # Fila 2: Costo, PVP, Peso
        row2 = ttk.Frame(gen_frame)
        row2.pack(fill=tk.X, pady=2)

        ttk.Label(row2, text="Costo Origen ($):", width=14).pack(side=tk.LEFT, padx=2)
        self.entry_costo = ttk.Entry(row2, width=12)
        self.entry_costo.pack(side=tk.LEFT, padx=2)

        ttk.Label(row2, text="PVP ($):", width=8).pack(side=tk.LEFT, padx=2)
        self.entry_pvp = ttk.Entry(row2, width=12)
        self.entry_pvp.pack(side=tk.LEFT, padx=2)

        ttk.Label(row2, text="Peso (kg):", width=10).pack(side=tk.LEFT, padx=2)
        self.entry_peso = ttk.Entry(row2, width=10)
        self.entry_peso.pack(side=tk.LEFT, padx=2)

        # Fila 3: Botones de generación
        row3 = ttk.Frame(gen_frame)
        row3.pack(fill=tk.X, pady=4)

        self.btn_generar = ttk.Button(row3, text="Generar Copy", command=self._generar_copy)
        self.btn_generar.pack(side=tk.LEFT, padx=5)

        self.btn_variantes = ttk.Button(row3, text="Generar 5 Variantes", command=self._generar_variantes)
        self.btn_variantes.pack(side=tk.LEFT, padx=5)

        self.gen_status = ttk.Label(row3, text="Listo", foreground="blue")
        self.gen_status.pack(side=tk.LEFT, padx=10, expand=True, fill=tk.X)

        # ====== Sección Media: Preview AIDA ======
        preview_frame = ttk.LabelFrame(self, text="Preview AIDA", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Título
        titulo_frame = ttk.Frame(preview_frame)
        titulo_frame.pack(fill=tk.X, pady=2)

        ttk.Label(titulo_frame, text="Título:", font=("Consolas", 9, "bold")).pack(side=tk.LEFT, padx=2)
        self.text_titulo = tk.Text(titulo_frame, height=2, width=80, font=("Consolas", 10),
                                   bg="#1e1e1e", fg="#d4d4d4", insertbackground="#d4d4d4",
                                   relief=tk.SUNKEN, bd=1)
        self.text_titulo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # Descripción (ScrolledText)
        desc_frame = ttk.Frame(preview_frame)
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=2)

        ttk.Label(desc_frame, text="Descripción:", font=("Consolas", 9, "bold")).pack(anchor=tk.NW, padx=2)
        self.text_desc = ScrolledText(desc_frame, height=12, width=80, font=("Consolas", 10),
                                      bg="#1e1e1e", fg="#d4d4d4", insertbackground="#d4d4d4",
                                      relief=tk.SUNKEN, bd=1)
        self.text_desc.pack(fill=tk.BOTH, expand=True, padx=2)

        # AIDA Score Bars + Radar Chart + Superlative Indicator
        scores_frame = ttk.Frame(preview_frame)
        scores_frame.pack(fill=tk.X, pady=4)

        # Columna izquierda: barras AIDA
        bars_col = ttk.Frame(scores_frame)
        bars_col.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self._crear_barra_aida(bars_col, "Attention", 0)
        self._crear_barra_aida(bars_col, "Interest", 1)
        self._crear_barra_aida(bars_col, "Decision", 2)
        self._crear_barra_aida(bars_col, "Action", 3)

        # Columna centro: Radar Chart AIDA
        radar_col = ttk.Frame(scores_frame)
        radar_col.pack(side=tk.LEFT, padx=10, pady=5)

        ttk.Label(radar_col, text="Radar AIDA", font=("Consolas", 9, "bold")).pack(pady=2)
        self.aida_canvas = tk.Canvas(radar_col, width=220, height=220,
                                     bg="#1e1e1e", highlightthickness=0)
        self.aida_canvas.pack()

        # Columna derecha: indicador de superlativos
        super_col = ttk.Frame(scores_frame)
        super_col.pack(side=tk.RIGHT, padx=10, pady=5)

        ttk.Label(super_col, text="Validación Superlativos", font=("Consolas", 9, "bold")).pack(pady=2)
        self.super_label = ttk.Label(super_col, text="✓ Sin superlativos", foreground="green",
                                     font=("Consolas", 10, "bold"))
        self.super_label.pack(pady=2)
        self.super_detail = ttk.Label(super_col, text="", foreground="gray")
        self.super_detail.pack(pady=2)

        # ====== Sección Inferior: Guardar + Exportar ======
        bottom_frame = ttk.LabelFrame(self, text="Guardar y Exportar", padding=10)
        bottom_frame.pack(fill=tk.X, padx=10, pady=5)

        # Fila 1: Botones de acción
        action_row = ttk.Frame(bottom_frame)
        action_row.pack(fill=tk.X, pady=2)

        self.btn_guardar = ttk.Button(action_row, text="Guardar en BD", command=self._guardar_bd)
        self.btn_guardar.pack(side=tk.LEFT, padx=5)

        self.btn_export_txt = ttk.Button(action_row, text="Exportar a TXT", command=self._exportar_txt)
        self.btn_export_txt.pack(side=tk.LEFT, padx=5)

        self.btn_export_html = ttk.Button(action_row, text="Exportar a HTML", command=self._exportar_html)
        self.btn_export_html.pack(side=tk.LEFT, padx=5)

        # Fila 2: Selector de producto + Rating
        sel_row = ttk.Frame(bottom_frame)
        sel_row.pack(fill=tk.X, pady=2)

        ttk.Label(sel_row, text="Producto guardado:").pack(side=tk.LEFT, padx=2)
        self.producto_combo = ttk.Combobox(sel_row, width=50, state="readonly")
        self.producto_combo.pack(side=tk.LEFT, padx=2)
        ttk.Button(sel_row, text="Cargar", command=self._cargar_producto).pack(side=tk.LEFT, padx=2)

        ttk.Label(sel_row, text="Rating:").pack(side=tk.LEFT, padx=10)
        self.rating_var = tk.IntVar(value=0)
        self.rating_combo = ttk.Combobox(sel_row, width=8, state="readonly",
                                         values=[str(i) for i in range(1, 6)])
        self.rating_combo.set("3")
        self.rating_combo.pack(side=tk.LEFT, padx=2)
        ttk.Button(sel_row, text="Actualizar Rating", command=self._actualizar_rating).pack(side=tk.LEFT, padx=2)

        # Cargar productos al iniciar
        self.after(200, self._refrescar_lista_productos)

    # ------------------------------------------------------------------
    #   Helper: barra AIDA
    # ------------------------------------------------------------------
    def _crear_barra_aida(self, parent, label, idx):
        """Crea una fila con label + Progressbar para un score AIDA."""
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=1)

        lbl = ttk.Label(row, text=f"{label}:", width=10, anchor=tk.W)
        lbl.pack(side=tk.LEFT, padx=2)

        bar = ttk.Progressbar(row, length=200, mode="determinate")
        bar.pack(side=tk.LEFT, padx=2)

        val_lbl = ttk.Label(row, text="0%", width=6, anchor=tk.E)
        val_lbl.pack(side=tk.LEFT, padx=2)

        setattr(self, f"_bar_aida_{idx}", bar)
        setattr(self, f"_bar_aida_label_{idx}", val_lbl)

    def _set_aida_scores(self, scores):
        """Actualiza las barras de progreso AIDA y el radar chart."""
        labels = ["attention", "interest", "decision", "action"]
        for idx, key in enumerate(labels):
            val = scores.get(key, 0)
            bar = getattr(self, f"_bar_aida_{idx}")
            lbl = getattr(self, f"_bar_aida_label_{idx}")
            bar["value"] = val
            lbl.config(text=f"{val}%")
            # Dibujar radar chart
            try:
                from app.ui.components.aida_radar import draw_aida_radar
                draw_aida_radar(self.aida_canvas, scores)
            except Exception as e:
                print(f"[RADAR] Error dibujando radar: {e}")

    # ------------------------------------------------------------------
    #   Generación de Copy (threaded)
    # ------------------------------------------------------------------
    def _obtener_datos_formulario(self):
        """Lee y valida los campos del formulario."""
        try:
            nombre = self.entry_nombre.get().strip()
            categoria = self.entry_categoria.get().strip()
            costo = float(self.entry_costo.get().strip())
            pvp = float(self.entry_pvp.get().strip())
            peso = float(self.entry_peso.get().strip())
            if not nombre or not categoria:
                raise ValueError("Nombre y categoría son obligatorios")
            return nombre, categoria, costo, pvp, peso
        except ValueError as e:
            messagebox.showwarning("Datos inválidos", str(e))
            return None

    def _generar_copy(self):
        """Genera un copy en thread separado."""
        datos = self._obtener_datos_formulario()
        if datos is None:
            return

        nombre, categoria, costo, pvp, peso = datos
        self.gen_status.config(text="Generando copy...", foreground="orange")
        self.btn_generar.config(state=tk.DISABLED)
        self.btn_variantes.config(state=tk.DISABLED)

        def worker():
            contexto = self.engine.obtener_contexto_kb(limite=3)
            copy = self.engine.generar_copy_template(nombre, categoria, costo, pvp, peso, contexto)
            self.after(0, lambda: self._mostrar_copy(copy))

        threading.Thread(target=worker, daemon=True).start()

    
    def _generar_variantes(self):
        """Genera 5 variantes de copy usando el pool hibrido (con fallback a template)."""
        datos = self._obtener_datos_formulario()
        if datos is None:
            return

        nombre, categoria, costo, pvp, peso = datos
        self.gen_status.config(text="Generando 5 variantes con IA...", foreground="orange")
        self.btn_generar.config(state=tk.DISABLED)
        self.btn_variantes.config(state=tk.DISABLED)

        def worker():
            contexto = self.engine.obtener_contexto_kb(limite=3)
            variantes = []
            angulos = [
                "beneficio principal", "ahorro de tiempo", "calidad premium",
                "facilidad de uso", "resultados garantizados"
            ]
            for i, angulo in enumerate(angulos):
                try:
                    copy = self.engine.generar_con_openrouter(
                        f"{nombre} - {angulo}", categoria, costo, pvp, peso, contexto
                    )
                except Exception:
                    copy = self.engine.generar_copy_template(
                        f"{nombre} v{i+1}", categoria, costo, pvp, peso, contexto
                    )
                variantes.append(copy)
            self.variantes_actuales = variantes
            self.after(0, lambda: self._mostrar_variantes(variantes))

        threading.Thread(target=worker, daemon=True).start()
