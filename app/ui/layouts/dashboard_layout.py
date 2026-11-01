"""
dashboard_layout.py — Sistema de layout responsive para el dashboard.
Proporciona grids adaptables para organizar componentes visuales.
"""
import tkinter as tk
from tkinter import ttk
from typing import List, Optional, Callable
from app.ui.themes.design_tokens import COLORS, TYPOGRAPHY, SPACING, BREAKPOINTS


class DashboardGrid(ttk.Frame):
    """Grid responsive de 4 columnas para organizar KPIs.

    Reglas de adaptación:
    - > 1000px:  4 columnas
    - 800-1000px: 2 columnas
    - < 800px:    1 columna
    """
    def __init__(self, parent, columns: int = 4, **kwargs):
        super().__init__(parent, **kwargs)
        self._max_cols = max(1, min(4, columns))
        self._children: List[ttk.Frame] = []
        self.columnconfigure(list(range(self._max_cols)), weight=1)

    def add_widget(self, widget: ttk.Frame, **pack_kw):
        """Añade un widget al grid en la siguiente posición disponible."""
        idx = len(self._children)
        row = idx // self._max_cols
        col = idx % self._max_cols
        widget.grid(row=row, column=col, sticky="nsew", padx=SPACING.sm, pady=SPACING.sm)
        self._children.append(widget)

    def clear(self):
        for w in self._children:
            w.grid_forget()
        self._children = []


class PanelSection(ttk.LabelFrame):
    """Sección de panel con título y padding consistente."""
    def __init__(self, parent, text: str = "", icon: str = "",
                 padding: int = SPACING.md, **kwargs):
        display = f" {icon} {text}" if icon else text
        super().__init__(parent, text=display, padding=padding,
                        font=(TYPOGRAPHY.body_family, 9, "bold"),
                        foreground=COLORS.primary_action, **kwargs)