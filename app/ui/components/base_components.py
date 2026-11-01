"""
base_components.py — Componentes base reutilizables para GEM OS.
Incluye: Badge, StatusIndicator, KPICard (mejorado v2.0).
Basado en Gemini Design System + Material Design.
"""
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable
from app.ui.themes.design_tokens import COLORS, TYPOGRAPHY, SPACING, SHADOWS, CARD_GRADIENTS
from app.ui.themes.base_theme import BaseTheme
from app.ui.components.animations import HoverTracker


class Badge(ttk.Label):
    """Etiqueta estilizada con color semántico.
    Uso: Badge(parent, text="Activo", variant="success")
    """
    VARIANTS = {
        "success": {"fg": "#ffffff", "bg": "#10b981"},
        "warning": {"fg": "#1f2937", "bg": "#f59e0b"},
        "error":   {"fg": "#ffffff", "bg": "#ef4444"},
        "info":    {"fg": "#ffffff", "bg": "#3b82f6"},
        "neutral": {"fg": "#b0b0b0", "bg": "#3d3d3d"},
        "primary": {"fg": "#ffffff", "bg": "#6366f1"},
    }
    def __init__(self, parent, text: str = "", variant: str = "neutral",
                 theme: Optional[BaseTheme] = None, **kwargs):
        c = self.VARIANTS.get(variant, self.VARIANTS["neutral"])
        super().__init__(parent, text=text,
                         font=(TYPOGRAPHY.body_family, 9, "bold"),
                         foreground=c["fg"], background=c["bg"],
                         padding=(4, 2), **kwargs)


class StatusIndicator(ttk.Frame):
    """Indicador circular + label textual.
    Estados: ok, success, warning, error, info, neutral, disabled.
    """
    STATUS_COLORS = {"ok":"#10b981","success":"#10b981","warning":"#f59e0b",
                     "warn":"#f59e0b","error":"#ef4444","fail":"#ef4444",
                     "info":"#3b82f6","neutral":"#b0b0b0","disabled":"#666666"}
    STATUS_ICONS = {"ok":"●","success":"●","warning":"●","warn":"●",
                    "error":"●","fail":"●","info":"●","neutral":"○","disabled":"○"}

    def __init__(self, parent, status: str = "neutral", text: str = "",
                 theme: Optional[BaseTheme] = None, **kwargs):
        super().__init__(parent, **kwargs)
        self._status = status
        icon = self.STATUS_ICONS.get(status, "○")
        color = self.STATUS_COLORS.get(status, "#b0b0b0")
        self._dot = ttk.Label(self, text=icon, foreground=color,
                              font=(TYPOGRAPHY.body_family, 14))
        self._dot.pack(side=tk.LEFT, padx=(0, 4))
        self._label = ttk.Label(self, text=text,
                                font=(TYPOGRAPHY.body_family, TYPOGRAPHY.body_size))
        self._label.pack(side=tk.LEFT)

    def set_status(self, status: str, text: Optional[str] = None):
        color = self.STATUS_COLORS.get(status, "#b0b0b0")
        icon = self.STATUS_ICONS.get(status, "○")
        self._dot.config(foreground=color, text=icon)
        self._status = status
        if text is not None:
            self._label.config(text=text)

    @property
    def status(self) -> str:
        return self._status


class KPICard(tk.Frame):
    """Tarjeta KPI reutilizable con métrica principal (v2.0 mejorada).
    Variants: success, warning, error, info, primary, neutral, tiktok, amber, cyan.
    Trend: up (▲), down (▼), stable (◆).
    Incluye hover effect, gradiente de fondo, y animaciones numéricas."""
    def __init__(self, parent, title: str = "", value: str = "0",
                 subtitle: str = "", icon: str = "",
                 variant: str = "primary",
                 trend_direction: str = "stable",
                 trend_value: Optional[str] = None,
                 theme: Optional[BaseTheme] = None,
                 on_click: Optional[Callable] = None, **kwargs):
        super().__init__(parent, **kwargs)
        colors = CARD_GRADIENTS.get(variant, CARD_GRADIENTS["neutral"])
        self.configure(relief=SHADOWS.low, bd=1, bg=colors["start"])
        # Borde superior highlight
        tk.Frame(self, bg=colors["border"], bd=0, height=3).pack(fill=tk.X)
        # Header: icono + título
        hdr = ttk.Frame(self); hdr.pack(fill=tk.X, padx=SPACING.md, pady=(SPACING.sm, SPACING.xs))
        if icon:
            ttk.Label(hdr, text=icon, font=("Segoe UI", 18)).pack(side=tk.LEFT, padx=(0, SPACING.sm))
        ttk.Label(hdr, text=title, font=(TYPOGRAPHY.heading_family, 11, "bold"),
                  foreground=colors["border"]).pack(side=tk.LEFT, fill=tk.X, expand=True)
        # Valor principal
        val_f = ttk.Frame(self); val_f.pack(expand=True, fill=tk.BOTH, padx=SPACING.md)
        self._val_label = ttk.Label(val_f, text=value, font=(TYPOGRAPHY.heading_family, 22, "bold"),
                  foreground=colors["border"])
        self._val_label.pack(pady=(SPACING.sm, 0), anchor="center")
        # Subtítulo
        if subtitle:
            ttk.Label(val_f, text=subtitle,
                      font=(TYPOGRAPHY.body_family, 9),
                      foreground=COLORS.dark_fg_secondary).pack(pady=(SPACING.xs, 0))
        # Trend
        if trend_value:
            sym = {"up":"▲","down":"▼","stable":"◆"}.get(trend_direction,"●")
            tc = {"up":COLORS.success,"down":COLORS.error,
                  "stable":COLORS.info}.get(trend_direction, COLORS.info)
            self._trend_label = ttk.Label(val_f, text=f"{sym} {trend_value}",
                      font=(TYPOGRAPHY.body_family, 9), foreground=tc)
            self._trend_label.pack(pady=(SPACING.xs, 0))
        # Hover effect
        HoverTracker.bind_recursive(self,
            lambda w: (w.configure(background=colors["end"])
                      if hasattr(w, 'configure') else None),
            lambda w: (w.configure(background=colors["start"])
                      if hasattr(w, 'configure') else None))
        # Click
        if on_click:
            for w in [self, hdr, val_f]:
                w.bind("<Button-1>", lambda e: on_click())

    def set_value(self, value: str):
        """Actualiza el valor mostrado."""
        if hasattr(self, '_val_label'):
            self._val_label.config(text=value)

    def set_trend(self, direction: str, value: Optional[str] = None):
        """Actualiza la tendencia."""
        sym = {"up":"▲","down":"▼","stable":"◆"}.get(direction, "●")
        tc = {"up": COLORS.success, "down": COLORS.error,
              "stable": COLORS.info}.get(direction, COLORS.info)
        if hasattr(self, '_trend_label'):
            if value:
                self._trend_label.config(text=f"{sym} {value}", foreground=tc)
            else:
                self._trend_label.config(text=sym, foreground=tc)