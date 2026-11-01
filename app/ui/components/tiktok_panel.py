"""
TikTokPanel - Panel UI para Generación de Guiones TikTok
Genera guiones virales con patrones hook + vista previa.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
import threading
import json
from datetime import datetime

from app.services.tiktok_script_generator import TikTokScriptGenerator


class TikTokPanel(ttk.Frame):
    """Panel UI para generación de guiones TikTok."""

    def __init__(self, parent, db_manager=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.db_manager = db_manager
        self.generator = TikTokScriptGenerator(db_manager=db_manager)
        self.guion_actual = None
        self.variantes_actuales = []

        self._build_ui()

    # ─────────────────────────────── UI ───────────────────────────────

    def _build_ui(self):
        # ====== Top: Formulario de Generación ======
        form_frame = ttk.LabelFrame(self, text="Generar Guiones TikTok", padding=10)
        form_frame.pack(fill=tk.X, padx=10, pady=5)

        grid = ttk.Frame(form_frame)
        grid.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(grid, text="Producto:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.producto_entry = ttk.Entry(grid, width=40)
        self.producto_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(grid, text="Categoría:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.categoria_entry = ttk.Entry(grid, width=40)
        self.categoria_entry.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(grid, text="Patrón Hook:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5))
        self.hook_combo = ttk.Combobox(
            grid, values=['story-telling', 'curiosity-gap', 'shock', 'humor'],
            state='readonly', width=37
        )
        self.hook_combo.grid(row=2, column=1, padx=5, pady=2)
        self.hook_combo.current(0)

        btn_row = ttk.Frame(form_frame)
        btn_row.pack(fill=tk.X, pady=(4, 0))

        self.gen_btn = ttk.Button(btn_row, text="Generar Guión", command=self._generar_guion)
        self.gen_btn.pack(side=tk.LEFT, padx=5)

        self.batch_btn = ttk.Button(btn_row, text="Generar 5 Variantes", command=self._generar_variantes)
        self.batch_btn.pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(btn_row, text="Listo", foreground="blue")
        self.status_label.pack(side=tk.LEFT, padx=10, expand=True, fill=tk.X)

        # ====== Middle: Preview ======
        preview_frame = ttk.LabelFrame(self, text="Vista Previa del Guión", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # ── Hook ──
        hook_frame = ttk.Frame(preview_frame)
        hook_frame.pack(fill=tk.X, pady=2)
        hook_label = ttk.Label(hook_frame, text="📢 HOOK", font=("Segoe UI", 9, "bold"),
                               background="#FFF3CD", anchor=tk.CENTER)
        hook_label.pack(fill=tk.X, ipady=2)
        self.hook_text = ScrolledText(hook_frame, height=3, wrap=tk.WORD, font=("Segoe UI", 10))
        self.hook_text.pack(fill=tk.X, pady=(0, 6))
        self.hook_text.config(state=tk.DISABLED)

        # ── Cuerpo ──
        cuerpo_frame = ttk.Frame(preview_frame)
        cuerpo_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        cuerpo_label = ttk.Label(cuerpo_frame, text="📝 CUERPO", font=("Segoe UI", 9, "bold"),
                                 background="#FFFFFF", anchor=tk.CENTER)
        cuerpo_label.pack(fill=tk.X, ipady=2)
        self.cuerpo_text = ScrolledText(cuerpo_frame, height=5, wrap=tk.WORD, font=("Segoe UI", 10))
        self.cuerpo_text.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        self.cuerpo_text.config(state=tk.DISABLED)

        # ── CTA ──
        cta_frame = ttk.Frame(preview_frame)
        cta_frame.pack(fill=tk.X, pady=2)
        cta_label = ttk.Label(cta_frame, text="🎯 CTA", font=("Segoe UI", 9, "bold"),
                              background="#D4EDDA", anchor=tk.CENTER)
        cta_label.pack(fill=tk.X, ipady=2)
        self.cta_text = ScrolledText(cta_frame, height=3, wrap=tk.WORD, font=("Segoe UI", 10))
        self.cta_text.pack(fill=tk.X, pady=(0, 6))
        self.cta_text.config(state=tk.DISABLED)

        # ── Duración ──
        self.duracion_label = ttk.Label(preview_frame, text="⏱ Duración estimada: — s",
                                        font=("Segoe UI", 9, "italic"), foreground="#555")
        self.duracion_label.pack(anchor=tk.E, pady=(0, 2))

        # ====== Bottom: Guardar + Exportar + Stats ======
        bottom_frame = ttk.LabelFrame(self, text="Guardar y Administrar", padding=10)
        bottom_frame.pack(fill=tk.X, padx=10, pady=5)

        action_row = ttk.Frame(bottom_frame)
        action_row.pack(fill=tk.X, pady=(0, 6))

        self.save_btn = ttk.Button(action_row, text="Guardar en BD", command=self._guardar_en_bd,
                                   state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT, padx=5)

        self.export_btn = ttk.Button(action_row, text="Exportar a TXT", command=self._exportar_txt,
                                     state=tk.DISABLED)
        self.export_btn.pack(side=tk.LEFT, padx=5)

        # Product selector
        ttk.Label(action_row, text="Producto:").pack(side=tk.LEFT, padx=(15, 5))
        self.producto_combo = ttk.Combobox(action_row, state='readonly', width=35)
        self.producto_combo.pack(side=tk.LEFT, padx=5)

        ttk.Button(action_row, text="↻", width=3,
                   command=self._cargar_productos).pack(side=tk.LEFT, padx=2)

        # ── Rating ──
        rating_frame = ttk.Frame(bottom_frame)
        rating_frame.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(rating_frame, text="Valorar guión guardado:").pack(side=tk.LEFT, padx=(0, 8))
        self.rating_var = tk.IntVar(value=0)
        self.rating_buttons = []
        for i in range(1, 6):
            rb = ttk.Radiobutton(rating_frame, text="★", variable=self.rating_var, value=i,
                                 command=self._aplicar_rating)
            rb.pack(side=tk.LEFT, padx=1)
            self.rating_buttons.append(rb)
        self.rating_info = ttk.Label(rating_frame, text="(selecciona un guión guardado)",
                                     foreground="#888")
        self.rating_info.pack(side=tk.LEFT, padx=10)

        # ── Stats ──
        self.stats_label = ttk.Label(bottom_frame, text="Stats: 0 guiones · 0 patrones",
                                     foreground="#555")
        self.stats_label.pack(anchor=tk.W, pady=(2, 0))

        self.guardado_id = None
        self.after(200, self._cargar_productos)

    # ─────────────────────────── Generación ───────────────────────────

    def _generar_guion(self):
        producto = self.producto_entry.get().strip()
        categoria = self.categoria_entry.get().strip()
        patron = self.hook_combo.get()

        if not producto or not categoria:
            messagebox.showwarning("Campos incompletos",
                                   "Completa producto y categoría antes de generar.")
            return

        self._set_estado("Generando guión...", "orange", disabled=True)

        def worker():
            try:
                guion = self.generator.generar_guion_completo(
                    nombre_producto=producto,
                    categoria=categoria,
                    patron_hook=patron
                )
                self.after(0, lambda: self._mostrar_guion(guion))
            except Exception as e:
                self.after(0, lambda: self._error_msg(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _generar_variantes(self):
        producto = self.producto_entry.get().strip()
        categoria = self.categoria_entry.get().strip()

        if not producto or not categoria:
            messagebox.showwarning("Campos incompletos",
                                   "Completa producto y categoría antes de generar.")
            return

        self._set_estado("Generando 5 variantes...", "orange", disabled=True)

        def worker():
            try:
                variantes = self.generator.generar_variantes_lote(
                    nombre_producto=producto,
                    categoria=categoria,
                    cantidad=5
                )
                self.after(0, lambda: self._mostrar_variantes(variantes))
            except Exception as e:
                self.after(0, lambda: self._error_msg(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _mostrar_guion(self, guion):
        self.guion_actual = guion
        self.guardado_id = None
        self._set_text(self.hook_text, guion.get('hook', ''))
        self._set_text(self.cuerpo_text, guion.get('cuerpo', ''))
        self._set_text(self.cta_text, guion.get('cta', ''))
        self.duracion_label.config(
            text=f"⏱ Duración estimada: {guion.get('duracion_segundos', 0)} s"
        )
        self.save_btn.config(state=tk.NORMAL)
        self.export_btn.config(state=tk.NORMAL)
        self._set_estado("Guión generado", "green")

    def _mostrar_variantes(self, variantes):
        self.variantes_actuales = variantes
        self.guardado_id = None
        if variantes:
            self._mostrar_guion(variantes[0])
            self._set_estado(f"5 variantes generadas · mostrando #1", "green")
        else:
            self._set_estado("No se generaron variantes", "red")

    # ─────────────────────────── Persistencia ─────────────────────────

    def _guardar_en_bd(self):
        if not self.guion_actual:
            messagebox.showwarning("Sin guión", "Genera un guión primero.")
            return

        prod_id = self._producto_id_seleccionado()
        if prod_id is None:
            messagebox.showwarning("Sin producto",
                                   "Selecciona un producto del listado o agrega uno nuevo.")
            return

        self._set_estado("Guardando en BD...", "orange")

        def worker():
            try:
                guion = self.guion_actual
                if self.guardado_id is not None:
                    # Ya guardado: actualizar rating si cambió
                    val = self.rating_var.get()
                    if val > 0:
                        with self.generator.db_manager.get_connection() as conn:
                            conn.execute(
                                "UPDATE guiones_tiktok SET rating_usuario = ? WHERE id = ?",
                                (val, self.guardado_id)
                            )
                            conn.commit()
                        self.after(0, lambda: self._set_estado(
                            f"Rating {val}★ actualizado", "green"))
                    else:
                        self.after(0, lambda: self._set_estado(
                            "Ya guardado (selecciona rating para actualizar)", "blue"))
                    return

                guion_id = self.generator.guardar_guion(prod_id, guion)
                if guion_id > 0:
                    self.guardado_id = guion_id
                    self.after(0, lambda: self._set_estado(
                        f"Guardado en BD (ID {guion_id})", "green"))
                    self.after(0, self._cargar_productos)
                    self.after(0, self._actualizar_stats)
                else:
                    self.after(0, lambda: self._set_estado("Error al guardar", "red"))
            except Exception as e:
                self.after(0, lambda: self._error_msg(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _exportar_txt(self):
        if not self.guion_actual:
            messagebox.showwarning("Sin guión", "Genera un guión primero.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not filepath:
            return

        try:
            guion = self.guion_actual
            contenido = (
                f"=== GUIÓN TIKTOK ===\n"
                f"Producto: {self.producto_entry.get()}\n"
                f"Categoría: {self.categoria_entry.get()}\n"
                f"Patrón Hook: {guion.get('patron_hook', '')}\n"
                f"Duración: {guion.get('duracion_segundos', 0)} s\n"
                f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"\n── HOOK ──\n{guion.get('hook', '')}\n"
                f"\n── CUERPO ──\n{guion.get('cuerpo', '')}\n"
                f"\n── CTA ──\n{guion.get('cta', '')}\n"
            )
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(contenido)
            messagebox.showinfo("Éxito", f"Exportado a {filepath}")
        except Exception as e:
            messagebox.showerror("Error al Exportar", str(e))

    # ─────────────────────────── Rating ───────────────────────────────

    def _aplicar_rating(self):
        val = self.rating_var.get()
        if self.guardado_id is not None and val > 0:
            self._set_estado(f"Asignando {val}★ al guión ID {self.guardado_id}...", "orange")

            def worker():
                try:
                    with self.generator.db_manager.get_connection() as conn:
                        conn.execute(
                            "UPDATE guiones_tiktok SET rating_usuario = ? WHERE id = ?",
                            (val, self.guardado_id)
                        )
                        conn.commit()
                    self.after(0, lambda: self._set_estado(
                        f"Rating {val}★ guardado", "green"))
                    self.after(0, self._actualizar_stats)
                except Exception as e:
                    self.after(0, lambda: self._error_msg(str(e)))

            threading.Thread(target=worker, daemon=True).start()
        elif self.guardado_id is None:
            self.rating_info.config(text="(guarda primero el guión)")
            self.rating_var.set(0)
        else:
            self.rating_info.config(text="")

    # ─────────────────────────── DB helpers ───────────────────────────

    def _cargar_productos(self):
        if not self.db_manager:
            return
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, sku FROM productos_validados ORDER BY id DESC LIMIT 50"
                )
                rows = cursor.fetchall()
            opciones = [f"{r[0]} - {r[1]}" for r in rows]
            self.producto_combo['values'] = opciones
            if opciones:
                self.producto_combo.current(0)
        except Exception:
            self.producto_combo['values'] = []
        self._actualizar_stats()

    def _producto_id_seleccionado(self) -> int | None:
        val = self.producto_combo.get()
        if not val:
            return None
        try:
            return int(val.split(" - ")[0])
        except (ValueError, IndexError):
            return None

    def _actualizar_stats(self):
        if not self.db_manager:
            return
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM guiones_tiktok")
                total = cursor.fetchone()[0]
                cursor.execute("""
                    SELECT patron_hook, COUNT(*) FROM guiones_tiktok
                    GROUP BY patron_hook ORDER BY COUNT(*) DESC
                """)
                rows = cursor.fetchall()
            partes = ", ".join(f"{r[0]}: {r[1]}" for r in rows)
            self.stats_label.config(
                text=f"Stats: {total} guiones · {partes}" if partes
                     else f"Stats: {total} guiones · 0 patrones"
            )
        except Exception:
            self.stats_label.config(text="Stats: —")

    # ─────────────────────────── Utilitarios ──────────────────────────

    def _set_text(self, widget, text):
        widget.config(state=tk.NORMAL)
        widget.delete(1.0, tk.END)
        widget.insert(tk.END, text)
        widget.config(state=tk.DISABLED)

    def _set_estado(self, msg, color="blue", disabled=False):
        self.status_label.config(text=msg, foreground=color)
        state = tk.DISABLED if disabled else tk.NORMAL
        self.gen_btn.config(state=state)
        self.batch_btn.config(state=state)

    def _error_msg(self, msg):
        self._set_estado("Error", "red", disabled=False)
        messagebox.showerror("Error", msg)