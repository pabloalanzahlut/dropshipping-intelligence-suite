"""
DashboardPanel v3.0 PRO — Rediseño Premium Completo
Inspiración: Aplicaciones profesionales (Figma, Linear, Stripe)
- Diseño glassmorphism mejorado
- Animaciones fluidas
- Layout responsivo
- Colores premium con gradientes
- Componentes interactivos modernos
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import time
from typing import Dict, List, Optional

from app.database.connection import DatabaseConnection
from app.ui.themes.design_tokens import (
    COLORS, TYPOGRAPHY, SPACING, CARD_GRADIENTS, KPI_ICONS
)
from app.ui.components.animations import AnimatedValue, ThrottledUpdater


# Tipografía premium
FONT_TITLE = (TYPOGRAPHY.heading_family, 18, "bold")
FONT_SUBTITLE = (TYPOGRAPHY.heading_family, 12, "bold")
FONT_SECTION = (TYPOGRAPHY.heading_family, 10, "bold")
FONT_BODY = (TYPOGRAPHY.body_family, 10)
FONT_BODY_SM = (TYPOGRAPHY.body_family, 9)
FONT_MONO = (TYPOGRAPHY.mono_family, 8)

# Paleta de colores premium
COLOR_PRIMARY = "#6366f1"      # Indigo
COLOR_SECONDARY = "#8b5cf6"    # Purple
COLOR_SUCCESS = "#10b981"      # Emerald
COLOR_WARNING = "#f59e0b"      # Amber
COLOR_ERROR = "#ef4444"        # Red
COLOR_INFO = "#3b82f6"         # Blue
COLOR_BG_PRIMARY = "#0f0f0f"   # Near black
COLOR_BG_SECONDARY = "#1a1a1a" # Deep dark
COLOR_BG_TERTIARY = "#252525"  # Dark gray
COLOR_BG_CARD = "#2d2d2d"      # Card background
COLOR_BORDER = "#3d3d3d"       # Border color
COLOR_TEXT_PRIMARY = "#ffffff" # White
COLOR_TEXT_SECONDARY = "#b0b0b0"  # Gray
COLOR_TEXT_TERTIARY = "#888888"   # Dim gray

# Config de KPIs
KPI_CONFIG = [
    ("productos", "Productos Validados", "success", "📦", "up"),
    ("transcripciones", "Transcripciones", "info", "🎬", "up"),
    ("copys", "Copys Generados", "amber", "✍️", "up"),
    ("guiones", "Guiones TikTok", "tiktok", "🎵", "up"),
]


class DashboardPanelV3(tk.Frame):
    """Panel Dashboard Premium con diseño moderno."""

    def __init__(self, parent, db_manager=None, **kwargs):
        super().__init__(parent, bg=COLOR_BG_PRIMARY, **kwargs)
        self.db_manager = db_manager or DatabaseConnection()
        self._updater = ThrottledUpdater(min_interval_ms=150)
        self._kpi_cache = {}
        self._hover_tags = {}
        self._build_ui()
        self._load_data()
        self.after(2000, self._refrescar_periodicamente)

    def _build_ui(self):
        """Construir UI completo."""
        
        # Contenedor scrollable principal
        main_container = tk.Frame(self, bg=COLOR_BG_PRIMARY)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Header
        self._build_header(main_container)
        
        # Separador visual
        separator = tk.Frame(main_container, height=1, bg=COLOR_BORDER)
        separator.pack(fill=tk.X, padx=0, pady=(SPACING.sm, 0))

        # KPI Row
        self._build_kpi_row(main_container)
        
        # Content area con scroll
        content_frame = tk.Frame(main_container, bg=COLOR_BG_PRIMARY)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING.lg, pady=SPACING.md)
        
        # Dos columnas: Izquierda (tablas), Derecha (gráficos)
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        
        left_col = tk.Frame(content_frame, bg=COLOR_BG_PRIMARY)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING.md))
        
        right_col = tk.Frame(content_frame, bg=COLOR_BG_PRIMARY)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(SPACING.md, 0))
        
        # Tablas en columna izquierda
        self._build_tables(left_col)
        
        # Gráficos en columna derecha
        self._build_charts(right_col)

    def _build_header(self, parent):
        """Header moderno con título y controles."""
        header = tk.Frame(parent, bg=COLOR_BG_SECONDARY, height=80)
        header.pack(fill=tk.X, padx=0, pady=0)
        header.pack_propagate(False)
        
        header_inner = tk.Frame(header, bg=COLOR_BG_SECONDARY)
        header_inner.pack(fill=tk.BOTH, expand=True, padx=SPACING.lg, pady=SPACING.md)
        
        # Lado izquierdo: Título
        left = tk.Frame(header_inner, bg=COLOR_BG_SECONDARY)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        title = tk.Label(left, text="📊 Dashboard Analytics",
                        font=FONT_TITLE, fg=COLOR_TEXT_PRIMARY, bg=COLOR_BG_SECONDARY)
        title.pack(side=tk.LEFT, anchor="w")
        
        self.timestamp_label = tk.Label(left, text="",
                                       font=FONT_BODY_SM, fg=COLOR_TEXT_TERTIARY,
                                       bg=COLOR_BG_SECONDARY)
        self.timestamp_label.pack(side=tk.LEFT, padx=SPACING.lg)
        
        # Lado derecho: Botones
        right = tk.Frame(header_inner, bg=COLOR_BG_SECONDARY)
        right.pack(side=tk.RIGHT)
        
        btn_sync = self._create_button(right, "⚡ Sincronizar",
                                      command=self._on_sync, color=COLOR_PRIMARY)
        
        btn_refresh = self._create_button(right, "🔄 Actualizar",
                                         command=self._load_data, color=COLOR_INFO)

    def _create_button(self, parent, text, command=None, color=COLOR_PRIMARY):
        """Crear botón moderno con mejor diseño visual."""
        # Frame contenedor para darle borde y sombra
        btn_container = tk.Frame(parent, bg=COLOR_BG_SECONDARY, 
                                highlightbackground=color, 
                                highlightthickness=2,
                                highlightcolor=color)
        btn_container.pack(side=tk.LEFT, padx=SPACING.xs)
        
        btn = tk.Button(btn_container, text=text, command=command,
                       font=(TYPOGRAPHY.body_family, 10, "bold"), 
                       bg=color, fg=COLOR_TEXT_PRIMARY,
                       border=0, padx=SPACING.md + 4, pady=SPACING.sm,
                       activebackground=self._lighten_color(color), 
                       activeforeground=COLOR_TEXT_PRIMARY,
                       cursor="hand2", relief=tk.FLAT, highlightthickness=0)
        btn.pack(fill=tk.BOTH, expand=True)
        
        # Hover effect mejorado con sombra
        def on_enter(e):
            btn.config(bg=self._lighten_color(color))
            btn_container.configure(highlightthickness=3)
        
        def on_leave(e):
            btn.config(bg=color)
            btn_container.configure(highlightthickness=2)
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    def _lighten_color(self, color):
        """Aclarar color para hover."""
        # Función simple para aclarar hex color
        if color.startswith("#"):
            hex_color = color.lstrip("#")
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            rgb = tuple(min(255, int(c * 1.2)) for c in rgb)
            return "#{:02x}{:02x}{:02x}".format(*rgb)
        return color

    def _build_kpi_row(self, parent):
        """Fila de 4 KPI cards premium."""
        kpi_frame = tk.Frame(parent, bg=COLOR_BG_PRIMARY)
        kpi_frame.pack(fill=tk.X, padx=SPACING.lg, pady=SPACING.md)
        
        self._kpi_cards = {}
        
        for i, (key, title, variant, icon, _) in enumerate(KPI_CONFIG):
            kpi_frame.columnconfigure(i, weight=1)
            card = self._create_kpi_card(kpi_frame, title, icon, variant)
            card.grid(row=0, column=i, sticky="nsew", padx=SPACING.sm, pady=0)
            self._kpi_cards[key] = card

    def _create_kpi_card(self, parent, title, icon, variant):
        """Crear tarjeta KPI con diseño premium."""
        # Color según variante
        color_map = {
            "success": COLOR_SUCCESS,
            "info": COLOR_INFO,
            "amber": COLOR_WARNING,
            "tiktok": "#ec4899",
        }
        accent_color = color_map.get(variant, COLOR_PRIMARY)
        
        card = tk.Frame(parent, bg=COLOR_BG_CARD, highlightthickness=1,
                       highlightbackground=COLOR_BORDER)
        
        # Borde superior coloreado
        top_bar = tk.Frame(card, bg=accent_color, height=3)
        top_bar.pack(fill=tk.X, padx=0, pady=0)
        top_bar.pack_propagate(False)
        
        # Contenido
        content = tk.Frame(card, bg=COLOR_BG_CARD)
        content.pack(fill=tk.BOTH, expand=True, padx=SPACING.md, pady=SPACING.md)
        
        # Header: icon + title
        header = tk.Frame(content, bg=COLOR_BG_CARD)
        header.pack(fill=tk.X, pady=(0, SPACING.sm))
        
        icon_label = tk.Label(header, text=icon, font=("Arial", 14), bg=COLOR_BG_CARD)
        icon_label.pack(side=tk.LEFT, padx=(0, SPACING.xs))
        
        title_label = tk.Label(header, text=title, font=FONT_BODY_SM,
                              fg=COLOR_TEXT_SECONDARY, bg=COLOR_BG_CARD)
        title_label.pack(side=tk.LEFT, anchor="w")
        
        # Valor grande
        value_label = tk.Label(content, text="0", font=(TYPOGRAPHY.heading_family, 22, "bold"),
                              fg=accent_color, bg=COLOR_BG_CARD)
        value_label.pack(anchor="w", pady=(SPACING.sm, 0))
        
        # Indicador de tendencia
        trend_label = tk.Label(content, text="↑ Actualizado", font=FONT_BODY_SM,
                              fg=COLOR_SUCCESS, bg=COLOR_BG_CARD)
        trend_label.pack(anchor="w", pady=(SPACING.xs, 0))
        
        # Guardar referencias
        card._title = title
        card._value_label = value_label
        card._trend_label = trend_label
        card._accent_color = accent_color
        
        return card

    def _build_tables(self, parent):
        """Construir sección de tablas."""
        # Tabla de validaciones
        val_frame = self._create_section(parent, "✅ Últimas Validaciones", COLOR_SUCCESS)
        val_frame.pack(fill=tk.BOTH, expand=True, pady=(0, SPACING.md))
        
        self.val_tree = self._create_table(val_frame,
                                          columns=["SKU", "PVP ($)", "Margen %", "Status"],
                                          col_widths=[100, 80, 80, 90])
        self.val_tree.pack(fill=tk.BOTH, expand=True)
        
        # Tabla de copys
        copy_frame = self._create_section(parent, "✍️ Últimos Copys", COLOR_WARNING)
        copy_frame.pack(fill=tk.BOTH, expand=True)
        
        self.copy_tree = self._create_table(copy_frame,
                                           columns=["Producto", "Score AIDA", "Superlativos"],
                                           col_widths=[130, 90, 90])
        self.copy_tree.pack(fill=tk.BOTH, expand=True)

    def _create_section(self, parent, title, accent_color=COLOR_PRIMARY):
        """Crear sección con header coloreado."""
        section = tk.Frame(parent, bg=COLOR_BG_CARD, highlightthickness=1,
                          highlightbackground=COLOR_BORDER)
        
        # Header
        header = tk.Frame(section, bg=COLOR_BG_TERTIARY)
        header.pack(fill=tk.X, padx=0, pady=0)
        
        title_label = tk.Label(header, text=title, font=FONT_SECTION,
                              fg=accent_color, bg=COLOR_BG_TERTIARY)
        title_label.pack(fill=tk.X, padx=SPACING.md, pady=SPACING.sm)
        
        # Content
        content = tk.Frame(section, bg=COLOR_BG_CARD)
        content.pack(fill=tk.BOTH, expand=True, padx=SPACING.md, pady=SPACING.md)
        
        return content

    def _create_table(self, parent, columns, col_widths):
        """Crear tabla minimalista."""
        table = ttk.Treeview(parent, columns=columns, height=8, show="headings")
        
        for col, width in zip(columns, col_widths):
            table.heading(col, text=col, anchor="center")
            table.column(col, width=width, minwidth=60, anchor="center")
        
        # Estilos de tabla
        table.tag_configure("even", background=COLOR_BG_SECONDARY)
        table.tag_configure("odd", background=COLOR_BG_TERTIARY)
        table.tag_configure("hover", background=COLOR_BG_CARD)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=table.yview)
        table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        return table

    def _build_charts(self, parent):
        """Construir sección de gráficos."""
        # Contenedor de gráficos
        charts_section = self._create_section(parent, "📈 Tráfico y Tendencias", COLOR_INFO)
        charts_section.pack(fill=tk.BOTH, expand=True)
        
        # Dos gráficos uno debajo del otro
        chart1_frame = tk.Frame(charts_section, bg=COLOR_BG_CARD)
        chart1_frame.pack(fill=tk.BOTH, expand=True, pady=(0, SPACING.md))
        
        label1 = tk.Label(chart1_frame, text="Distribución de Tráfico",
                         font=FONT_BODY_SM, fg=COLOR_TEXT_PRIMARY, bg=COLOR_BG_CARD)
        label1.pack(anchor="w", pady=(0, SPACING.sm))
        
        self.traffic_canvas = tk.Canvas(chart1_frame, width=400, height=150,
                                       bg=COLOR_BG_SECONDARY, highlightthickness=0)
        self.traffic_canvas.pack(fill=tk.BOTH, expand=True)
        
        chart2_frame = tk.Frame(charts_section, bg=COLOR_BG_CARD)
        chart2_frame.pack(fill=tk.BOTH, expand=True)
        
        label2 = tk.Label(chart2_frame, text="Top Nichos por Score",
                         font=FONT_BODY_SM, fg=COLOR_TEXT_PRIMARY, bg=COLOR_BG_CARD)
        label2.pack(anchor="w", pady=(0, SPACING.sm))
        
        self.nichos_canvas = tk.Canvas(chart2_frame, width=400, height=150,
                                      bg=COLOR_BG_SECONDARY, highlightthickness=0)
        self.nichos_canvas.pack(fill=tk.BOTH, expand=True)

    def _load_data(self):
        """Cargar datos desde BD."""
        try:
            stats = self._fetch_statistics()
            self._update_kpis(stats)
            self._update_tables(stats)
            self._draw_charts()
            self.timestamp_label.config(
                text=f"Última actualización: {datetime.now().strftime('%H:%M:%S')}"
            )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar datos: {str(e)}")

    def _fetch_statistics(self) -> dict:
        """Obtener estadísticas de BD."""
        stats = {
            'productos': {'total': 0, 'validados': 0, 'rechazados': 0},
            'transcripciones': {'total': 0, 'procesadas': 0},
            'copys': {'total': 0, 'score_promedio': 0.0},
            'guiones': {'total': 0},
            'ultimas_validaciones': [],
            'ultimos_copys': []
        }
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Productos
                cursor.execute("""
                    SELECT COUNT(*), SUM(CASE WHEN status_validacion='validado' THEN 1 ELSE 0 END)
                    FROM productos_validados
                """)
                r = cursor.fetchone()
                if r:
                    stats['productos']['total'] = r[0] or 0
                    stats['productos']['validados'] = r[1] or 0
                    stats['productos']['rechazados'] = stats['productos']['total'] - stats['productos']['validados']
                
                # Últimas validaciones
                cursor.execute("""
                    SELECT sku, pvp, margen_bruto, status_validacion
                    FROM productos_validados ORDER BY creada_at DESC LIMIT 5
                """)
                stats['ultimas_validaciones'] = [
                    {
                        "sku": r[0],
                        "pvp": f"${r[1]:.2f}" if isinstance(r[1], (int, float)) else str(r[1]),
                        "margen": f"{r[2]:.1f}%" if isinstance(r[2], (int, float)) else "N/A",
                        "status": r[3] or "Pendiente"
                    }
                    for r in cursor.fetchall()
                ]
                
                # Transcripciones
                cursor.execute("SELECT COUNT(*) FROM transcripciones_youtube")
                stats['transcripciones']['total'] = cursor.fetchone()[0] or 0
                
                cursor.execute("SELECT COUNT(*) FROM transcripciones_youtube WHERE procesada=1")
                stats['transcripciones']['procesadas'] = cursor.fetchone()[0] or 0
                
                # Copys
                cursor.execute("SELECT COUNT(*), COALESCE(AVG(promedio_score),0) FROM copys_generados")
                r = cursor.fetchone()
                if r:
                    stats['copys']['total'] = r[0] or 0
                    stats['copys']['score_promedio'] = round(r[1], 1) if r[1] else 0.0
                
                cursor.execute("SELECT titulo_copy, promedio_score, sin_superlativos FROM copys_generados ORDER BY ROWID DESC LIMIT 5")
                stats['ultimos_copys'] = [
                    {
                        "producto": r[0],
                        "score": f"{r[1]}%",
                        "superlativos": "Si" if not r[2] else "No"
                    }
                    for r in cursor.fetchall()
                ]
                
                # Guiones
                cursor.execute("SELECT COUNT(*) FROM guiones_tiktok")
                stats['guiones']['total'] = cursor.fetchone()[0] or 0
                
        except Exception:
            pass
        
        return stats

    def _update_kpis(self, stats):
        """Actualizar valores de KPI cards."""
        p = stats['productos']
        t = stats['transcripciones']
        c = stats['copys']
        g = stats['guiones']
        
        val_pct = round(p['validados'] * 100 / max(p['total'], 1), 1)
        t_pct = round(t['procesadas'] * 100 / max(t['total'], 1), 1)
        
        updates = {
            "productos": (f"{p['validados']}/{p['total']}", f"{val_pct}% OK"),
            "transcripciones": (str(t['total']), f"{t_pct}% procesadas"),
            "copys": (str(c['total']), f"Score: {c['score_promedio']}%"),
            "guiones": (str(g['total']), "Generados"),
        }
        
        for key, (value, trend) in updates.items():
            if key in self._kpi_cards:
                card = self._kpi_cards[key]
                card._value_label.config(text=value)
                card._trend_label.config(text=f"↑ {trend}")

    def _update_tables(self, stats):
        """Actualizar datos de tablas."""
        # Tabla validaciones
        self.val_tree.delete(*self.val_tree.get_children())
        for i, row in enumerate(stats.get('ultimas_validaciones', [])):
            tag = "even" if i % 2 == 0 else "odd"
            self.val_tree.insert("", tk.END, values=[
                row.get('sku', ''),
                row.get('pvp', ''),
                row.get('margen', ''),
                row.get('status', '')
            ], tags=(tag,))
        
        # Tabla copys
        self.copy_tree.delete(*self.copy_tree.get_children())
        for i, row in enumerate(stats.get('ultimos_copys', [])):
            tag = "even" if i % 2 == 0 else "odd"
            self.copy_tree.insert("", tk.END, values=[
                row.get('producto', ''),
                row.get('score', ''),
                row.get('superlativos', '')
            ], tags=(tag,))

    def _draw_charts(self):
        """Dibujar gráficos de canvas."""
        for canvas in [self.traffic_canvas, self.nichos_canvas]:
            canvas.delete("all")
            # Placeholder simple
            canvas.create_text(canvas.winfo_width()/2, canvas.winfo_height()/2,
                             text="📊 Datos en procesamiento...",
                             fill=COLOR_TEXT_TERTIARY, font=FONT_BODY_SM)

    def _on_sync(self):
        """Sincronizar datos."""
        messagebox.showinfo("Sincronización", "Sincronizando con servidor...")
        self._load_data()

    def _refrescar_periodicamente(self):
        """Actualizar periódicamente."""
        if self.winfo_exists():
            self._load_data()
            self.after(30000, self._refrescar_periodicamente)


# Alias para compatibilidad
DashboardPanel = DashboardPanelV3
