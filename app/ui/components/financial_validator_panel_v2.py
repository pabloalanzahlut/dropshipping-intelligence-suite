"""
FinancialValidatorPanel V2 - UI/UX Premium Style (Jack-inspired)
Panel de validación financiera con glassmorphism, neon accents y animaciones fluidas.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import csv
import json
from datetime import datetime
from typing import List, Dict, Any

from app.services.financial_validator import FinancialValidator
from app.ui.themes.design_tokens import (
    NEON_COLORS, 
    DARK_BASE, 
    TEXT_COLORS, 
    STATUS_COLORS,
    CARD_GRADIENTS
)


class ModernButton(tk.Canvas):
    """Botón personalizado con efectos neon y glassmorphism."""
    
    def __init__(self, parent, text="", command=None, style="primary", **kwargs):
        width = kwargs.pop('width', 140)
        height = kwargs.pop('height', 40)
        super().__init__(parent, width=width, height=height, 
                        bg=DARK_BASE['bg_secondary'], 
                        highlightthickness=0, **kwargs)
        
        self.command = command
        self.style = style
        self.text = text
        self.is_hovered = False
        self.is_pressed = False
        
        # Colores según estilo
        self.colors = {
            "primary": NEON_COLORS["cyan"],
            "success": STATUS_COLORS["success"],
            "warning": STATUS_COLORS["warning"],
            "error": STATUS_COLORS["error"],
            "secondary": TEXT_COLORS["secondary"]
        }
        
        self.accent_color = self.colors.get(style, NEON_COLORS["cyan"])
        
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        
        self._draw()
    
    def _draw(self):
        """Dibuja el botón con estado actual."""
        self.delete("all")
        
        w = int(self.cget("width"))
        h = int(self.cget("height"))
        
        # Sombra/glow si está hover
        if self.is_hovered:
            glow_color = self._hex_to_rgba(self.accent_color, 0.3)
            self.create_rectangle(2, 2, w-2, h-2, 
                                fill="", outline=self.accent_color,
                                width=2, tags="glow")
        
        # Background con glassmorphism
        bg_color = DARK_BASE['bg_input'] if not self.is_pressed else DARK_BASE['bg_hover']
        border_color = self.accent_color if self.is_hovered or self.is_pressed else TEXT_COLORS["tertiary"]
        
        self.create_rectangle(4, 4, w-4, h-4,
                            fill=bg_color, outline=border_color,
                            width=1, tags="bg")
        
        # Texto
        text_color = self.accent_color if self.is_hovered else TEXT_COLORS["primary"]
        self.create_text(w/2, h/2, text=self.text,
                        fill=text_color, font=("Segoe UI", 10, "bold"),
                        tags="text")
    
    def _hex_to_rgba(self, hex_color, alpha):
        """Convierte hex a rgba para efectos."""
        return hex_color  # Simplificado para tkinter
    
    def _on_enter(self, event):
        self.is_hovered = True
        self._draw()
    
    def _on_leave(self, event):
        self.is_hovered = False
        self.is_pressed = False
        self._draw()
    
    def _on_press(self, event):
        self.is_pressed = True
        self._draw()
    
    def _on_release(self, event):
        self.is_pressed = False
        self._draw()
        if self.is_hovered and self.command:
            self.command()


class GlassCard(tk.Canvas):
    """Card con efecto glassmorphism y borde neon."""
    
    def __init__(self, parent, title="", style="primary", **kwargs):
        width = kwargs.pop('width', 300)
        height = kwargs.pop('height', 120)
        super().__init__(parent, width=width, height=height,
                        bg=DARK_BASE['bg_primary'],
                        highlightthickness=0, **kwargs)
        
        self.title = title
        self.style = style
        self.gradient = CARD_GRADIENTS.get(style, CARD_GRADIENTS["primary"])
        
        self._draw()
    
    def _draw(self):
        """Dibuja el card con glassmorphism."""
        w = int(self.cget("width"))
        h = int(self.cget("height"))
        
        # Background con gradiente simulado
        self.create_rectangle(0, 0, w, h,
                            fill=self.gradient["start"],
                            outline="", tags="bg")
        
        # Borde neon
        self.create_rectangle(2, 2, w-2, h-2,
                            fill="", outline=self.gradient["border"],
                            width=1, tags="border")
        
        # Inner glow
        self.create_rectangle(4, 4, w-4, h-4,
                            fill="", outline=self.gradient["inner_glow"],
                            width=1, tags="glow")
        
        # Título
        if self.title:
            self.create_text(w/2, 20, text=self.title,
                           fill=self.gradient["text"],
                           font=("Segoe UI", 11, "bold"),
                           tags="title")
    
    def update_content(self, value, subtitle=""):
        """Actualiza el contenido del card."""
        w = int(self.cget("width"))
        h = int(self.cget("height"))
        
        # Eliminar contenido anterior
        self.delete("value")
        self.delete("subtitle")
        
        # Valor principal
        self.create_text(w/2, h/2 + 5, text=str(value),
                        fill=TEXT_COLORS["primary"],
                        font=("Segoe UI", 24, "bold"),
                        tags="value")
        
        # Subtítulo
        if subtitle:
            self.create_text(w/2, h - 15, text=subtitle,
                           fill=TEXT_COLORS["secondary"],
                           font=("Segoe UI", 9),
                           tags="subtitle")


class ModernEntry(tk.Frame):
    """Input field con estilo moderno y neon focus."""
    
    def __init__(self, parent, placeholder="", **kwargs):
        super().__init__(parent, bg=DARK_BASE['bg_secondary'])
        
        self.placeholder = placeholder
        self.has_focus = False
        
        # Canvas para el borde
        self.border_canvas = tk.Canvas(self, height=42, 
                                      bg=DARK_BASE['bg_secondary'],
                                      highlightthickness=0)
        self.border_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Entry interno
        self.entry = tk.Entry(self.border_canvas,
                            bg=DARK_BASE['bg_input'],
                            fg=TEXT_COLORS["primary"],
                            font=("Segoe UI", 10),
                            relief=tk.FLAT,
                            insertbackground=NEON_COLORS["cyan"],
                            **kwargs)
        
        self.border_canvas.create_window(21, 21, window=self.entry, 
                                        width=260, height=32)
        
        # Bindings para efectos de focus
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        
        self._draw_border()
        
        # Placeholder
        if placeholder:
            self._set_placeholder()
    
    def _draw_border(self):
        """Dibuja el borde del input."""
        self.border_canvas.delete("border")
        
        w = int(self.border_canvas.cget("width"))
        h = 42
        
        border_color = NEON_COLORS["cyan"] if self.has_focus else TEXT_COLORS["tertiary"]
        border_width = 2 if self.has_focus else 1
        
        self.border_canvas.create_rectangle(2, 2, w-2, h-2,
                                          fill="", outline=border_color,
                                          width=border_width, tags="border")
    
    def _on_focus_in(self, event):
        self.has_focus = True
        self._draw_border()
        if self.entry.get() == self.placeholder:
            self.entry.delete(0, tk.END)
            self.entry.config(fg=TEXT_COLORS["primary"])
    
    def _on_focus_out(self, event):
        self.has_focus = False
        self._draw_border()
        if not self.entry.get():
            self._set_placeholder()
    
    def _set_placeholder(self):
        self.entry.insert(0, self.placeholder)
        self.entry.config(fg=TEXT_COLORS["tertiary"])
    
    def get(self):
        value = self.entry.get()
        return "" if value == self.placeholder else value
    
    def set(self, value):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)
        self.entry.config(fg=TEXT_COLORS["primary"])


class FinancialValidatorPanel(ttk.Frame):
    """Panel de Validación Financiera con UI/UX Premium (Jack-style)."""
    
    def __init__(self, parent, db_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.db_manager = db_manager
        self.validator = FinancialValidator(db_manager=db_manager)
        self.validaciones_actuales = []
        
        # Configurar el frame principal
        self.configure(style='Dark.TFrame')
        
        self._build_ui()
    
    def _build_ui(self):
        """Construye la interfaz con diseño premium."""
        
        # Contenedor principal con scroll
        main_container = tk.Canvas(self, bg=DARK_BASE['bg_primary'], 
                                  highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", 
                                 command=main_container.yview)
        
        scrollable_frame = tk.Frame(main_container, bg=DARK_BASE['bg_primary'])
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_container.configure(scrollregion=main_container.bbox("all"))
        )
        
        main_container.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_container.configure(yscrollcommand=scrollbar.set)
        
        main_container.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # ===== HEADER SECTION =====
        self._build_header(scrollable_frame)
        
        # ===== KPI CARDS SECTION =====
        self._build_kpi_cards(scrollable_frame)
        
        # ===== IMPORT SECTION =====
        self._build_import_section(scrollable_frame)
        
        # ===== VALIDATION TABLE =====
        self._build_validation_table(scrollable_frame)
        
        # ===== EXPORT SECTION =====
        self._build_export_section(scrollable_frame)
    
    def _build_header(self, parent):
        """Construye el header con título y estado."""
        header_frame = tk.Frame(parent, bg=DARK_BASE['bg_primary'])
        header_frame.pack(fill=tk.X, padx=20, pady=(20, 10))
        
        # Título principal
        title_label = tk.Label(header_frame,
                              text="💎 Validador Financiero",
                              font=("Segoe UI", 22, "bold"),
                              fg=NEON_COLORS["cyan"],
                              bg=DARK_BASE['bg_primary'])
        title_label.pack(anchor="w")
        
        # Subtítulo
        subtitle_label = tk.Label(header_frame,
                                 text="Validación de productos según reglas de Adrián Sáenz e Iván Caicedo",
                                 font=("Segoe UI", 10),
                                 fg=TEXT_COLORS["secondary"],
                                 bg=DARK_BASE['bg_primary'])
        subtitle_label.pack(anchor="w", pady=(2, 0))
        
        # Status indicator
        self.status_frame = tk.Frame(header_frame, bg=DARK_BASE['bg_secondary'],
                                    height=40)
        self.status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_label = tk.Label(self.status_frame,
                                    text="⚡ Listo para importar productos",
                                    font=("Segoe UI", 10),
                                    fg=STATUS_COLORS["info"],
                                    bg=DARK_BASE['bg_secondary'])
        self.status_label.pack(side=tk.LEFT, padx=15, pady=8)
    
    def _build_kpi_cards(self, parent):
        """Construye las tarjetas KPI con glassmorphism."""
        kpi_container = tk.Frame(parent, bg=DARK_BASE['bg_primary'])
        kpi_container.pack(fill=tk.X, padx=20, pady=15)
        
        # Grid de KPI cards
        cards_data = [
            ("📦 Total Productos", "0", "primary"),
            ("✅ Validados", "0", "success"),
            ("❌ Rechazados", "0", "error"),
            ("📊 Margen Promedio", "0%", "info"),
        ]
        
        self.kpi_cards = []
        
        for i, (title, value, style) in enumerate(cards_data):
            card = GlassCard(kpi_container, title=title, style=style,
                           width=280, height=110)
            card.grid(row=0, column=i, padx=8, pady=5, sticky="ew")
            card.update_content(value)
            self.kpi_cards.append(card)
            
            kpi_container.grid_columnconfigure(i, weight=1)
    
    def _build_import_section(self, parent):
        """Construye la sección de importación con botones modernos."""
        import_frame = tk.Frame(parent, bg=DARK_BASE['bg_secondary'],
                               height=100)
        import_frame.pack(fill=tk.X, padx=20, pady=15)
        
        # Título de sección
        section_title = tk.Label(import_frame,
                                text="📥 Importar Productos",
                                font=("Segoe UI", 14, "bold"),
                                fg=TEXT_COLORS["primary"],
                                bg=DARK_BASE['bg_secondary'])
        section_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        # Botones de importación
        buttons_frame = tk.Frame(import_frame, bg=DARK_BASE['bg_secondary'])
        buttons_frame.pack(anchor="w", padx=20, pady=(0, 15))
        
        csv_btn = ModernButton(buttons_frame, text="📄 Importar CSV",
                              command=self._importar_csv, style="primary",
                              width=160)
        csv_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        json_btn = ModernButton(buttons_frame, text="📋 Importar JSON",
                               command=self._importar_json, style="secondary",
                               width=160)
        json_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        manual_btn = ModernButton(buttons_frame, text="➕ Añadir Manual",
                                 command=self._add_manual_product, style="success",
                                 width=160)
        manual_btn.pack(side=tk.LEFT)
    
    def _build_validation_table(self, parent):
        """Construye la tabla de validaciones con estilo moderno."""
        table_frame = tk.Frame(parent, bg=DARK_BASE['bg_secondary'])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        # Título de sección
        section_title = tk.Label(table_frame,
                                text="📋 Resultados de Validación",
                                font=("Segoe UI", 14, "bold"),
                                fg=TEXT_COLORS["primary"],
                                bg=DARK_BASE['bg_secondary'])
        section_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        # Contenedor de tabla con scroll
        tree_container = tk.Frame(table_frame, bg=DARK_BASE['bg_input'])
        tree_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
        
        # Configurar estilo del Treeview
        style = ttk.Style()
        style.theme_use("clam")
        
        style.configure("Modern.Treeview",
                       background=DARK_BASE['bg_input'],
                       foreground=TEXT_COLORS["primary"],
                       fieldbackground=DARK_BASE['bg_input'],
                       borderwidth=0,
                       font=("Segoe UI", 9))
        
        style.configure("Modern.Treeview.Heading",
                       background=DARK_BASE['bg_hover'],
                       foreground=NEON_COLORS["cyan"],
                       borderwidth=1,
                       font=("Segoe UI", 10, "bold"))
        
        style.map("Modern.Treeview",
                 background=[("selected", DARK_BASE['bg_hover'])],
                 foreground=[("selected", NEON_COLORS["cyan"])])
        
        # Treeview
        columns = ("SKU", "Costo ($)", "PVP ($)", "Margen %", 
                  "Regla 3x", "Peso (kg)", "Estado")
        
        self.validaciones_tree = ttk.Treeview(tree_container, 
                                             columns=columns,
                                             show="tree headings",
                                             style="Modern.Treeview",
                                             height=15)
        
        self.validaciones_tree.heading("#0", text="")
        self.validaciones_tree.column("#0", width=30, stretch=False)
        
        col_widths = [120, 80, 80, 80, 80, 80, 100]
        for col, width in zip(columns, col_widths):
            self.validaciones_tree.heading(col, text=col)
            self.validaciones_tree.column(col, width=width, anchor="center")
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL,
                                 command=self.validaciones_tree.yview)
        self.validaciones_tree.configure(yscroll=scrollbar.set)
        
        self.validaciones_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _build_export_section(self, parent):
        """Construye la sección de exportación."""
        export_frame = tk.Frame(parent, bg=DARK_BASE['bg_secondary'],
                               height=100)
        export_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Título de sección
        section_title = tk.Label(export_frame,
                                text="📤 Exportar Resultados",
                                font=("Segoe UI", 14, "bold"),
                                fg=TEXT_COLORS["primary"],
                                bg=DARK_BASE['bg_secondary'])
        section_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        # Botones de exportación
        buttons_frame = tk.Frame(export_frame, bg=DARK_BASE['bg_secondary'])
        buttons_frame.pack(anchor="w", padx=20, pady=(0, 15))
        
        export_csv_btn = ModernButton(buttons_frame, text="💾 Exportar CSV",
                                     command=self._exportar_csv, style="success",
                                     width=160)
        export_csv_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        export_json_btn = ModernButton(buttons_frame, text="📦 Exportar JSON",
                                      command=self._exportar_json, style="primary",
                                      width=160)
        export_json_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        clear_btn = ModernButton(buttons_frame, text="🗑️ Limpiar Todo",
                                command=self._clear_all, style="error",
                                width=160)
        clear_btn.pack(side=tk.LEFT)
    
    # ===== MÉTODOS DE FUNCIONALIDAD =====
    
    def _importar_csv(self):
        """Importa productos desde CSV."""
        filepath = filedialog.askopenfilename(
            title="Seleccionar archivo CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            self._update_status("⏳ Cargando CSV...", STATUS_COLORS["warning"])
            
            productos = []
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    productos.append({
                        'sku': row.get('sku', row.get('SKU', '')),
                        'costo_origen': float(row.get('costo_origen', row.get('costo', 0))),
                        'peso_kg': float(row.get('peso_kg', row.get('peso', 0))),
                        'pvp': float(row.get('pvp', 0)) if row.get('pvp') else None
                    })
            
            self._procesar_productos(productos)
            
        except Exception as e:
            messagebox.showerror("Error al importar CSV", str(e))
            self._update_status("❌ Error al cargar CSV", STATUS_COLORS["error"])
    
    def _importar_json(self):
        """Importa productos desde JSON."""
        filepath = filedialog.askopenfilename(
            title="Seleccionar archivo JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            self._update_status("⏳ Cargando JSON...", STATUS_COLORS["warning"])
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            productos = data if isinstance(data, list) else [data]
            self._procesar_productos(productos)
            
        except Exception as e:
            messagebox.showerror("Error al importar JSON", str(e))
            self._update_status("❌ Error al cargar JSON", STATUS_COLORS["error"])
    
    def _add_manual_product(self):
        """Abre diálogo para añadir producto manualmente."""
        messagebox.showinfo("Próximamente", 
                          "Función de añadir manual en desarrollo")
    
    def _procesar_productos(self, productos: List[Dict[str, Any]]):
        """Procesa y valida productos en thread separado."""
        self._update_status("⚙️ Validando productos...", STATUS_COLORS["info"])
        
        def worker():
            validaciones, validados, rechazados = self.validator.validar_lote(productos)
            self.validaciones_actuales = validaciones
            
            # Actualizar UI en main thread
            self.after(0, lambda: self._actualizar_tabla(validaciones, validados, rechazados))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _actualizar_tabla(self, validaciones, validados, rechazados):
        """Actualiza la tabla y las KPI cards."""
        # Limpiar tabla
        for item in self.validaciones_tree.get_children():
            self.validaciones_tree.delete(item)
        
        # Insertar filas con colores
        for i, val in enumerate(validaciones, 1):
            estado_icon = "✅" if val['validado'] else "❌"
            estado_text = "APROBADO" if val['validado'] else "RECHAZADO"
            
            regla_3x = "✅" if val.get('cumple_regla_3x', False) else "❌"
            
            valores = (
                val['sku'],
                f"${val['costo_origen']:.2f}",
                f"${val['pvp']:.2f}",
                f"{val['margen_bruto']:.1f}%",
                regla_3x,
                f"{val['peso_kg']:.2f}",
                f"{estado_icon} {estado_text}"
            )
            
            # Tag para colorear filas
            tag = "aprobado" if val['validado'] else "rechazado"
            self.validaciones_tree.insert("", tk.END, text=str(i), values=valores, tags=(tag,))
        
        # Configurar colores de tags
        self.validaciones_tree.tag_configure("aprobado", 
                                            background=CARD_GRADIENTS["success"]["start"])
        self.validaciones_tree.tag_configure("rechazado", 
                                            background=CARD_GRADIENTS["error"]["start"])
        
        # Actualizar KPI cards
        total = len(validaciones)
        margen_promedio = sum(v['margen_bruto'] for v in validaciones) / total if total > 0 else 0
        
        self.kpi_cards[0].update_content(total, f"productos analizados")
        self.kpi_cards[1].update_content(validados, f"{validados/total*100:.1f}% del total" if total > 0 else "")
        self.kpi_cards[2].update_content(rechazados, f"{rechazados/total*100:.1f}% del total" if total > 0 else "")
        self.kpi_cards[3].update_content(f"{margen_promedio:.1f}%", "margen bruto medio")
        
        self._update_status(f"✅ Procesados {total} productos: {validados} aprobados, {rechazados} rechazados",
                          STATUS_COLORS["success"])
    
    def _exportar_csv(self):
        """Exporta validaciones a CSV."""
        if not self.validaciones_actuales:
            messagebox.showwarning("Sin datos", "No hay validaciones para exportar")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['sku', 'costo_origen', 'pvp', 'margen_bruto', 
                            'cumple_regla_3x', 'peso_kg', 'validado', 'alertas']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for val in self.validaciones_actuales:
                    row = {k: val.get(k, '') for k in fieldnames if k != 'alertas'}
                    row['alertas'] = '; '.join(val.get('alertas', []))
                    writer.writerow(row)
            
            messagebox.showinfo("Exportado", f"CSV guardado en:\n{filepath}")
            
        except Exception as e:
            messagebox.showerror("Error al exportar", str(e))
    
    def _exportar_json(self):
        """Exporta validaciones a JSON."""
        if not self.validaciones_actuales:
            messagebox.showwarning("Sin datos", "No hay validaciones para exportar")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.validaciones_actuales, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Exportado", f"JSON guardado en:\n{filepath}")
            
        except Exception as e:
            messagebox.showerror("Error al exportar", str(e))
    
    def _clear_all(self):
        """Limpia todas las validaciones."""
        if not self.validaciones_actuales:
            return
        
        if messagebox.askyesno("Confirmar", "¿Limpiar todas las validaciones?"):
            self.validaciones_actuales = []
            
            for item in self.validaciones_tree.get_children():
                self.validaciones_tree.delete(item)
            
            for card in self.kpi_cards:
                card.update_content("0")
            
            self._update_status("⚡ Listo para importar productos", STATUS_COLORS["info"])
    
    def _update_status(self, message: str, color: str):
        """Actualiza el mensaje de estado."""
        self.status_label.config(text=message, fg=color)
