"""
cards.py — Componentes de tarjeta modernos para GEM OS v2.0
Incluye: InfoCard, MetricCard, EnhancedKPICard, StatCard.
Con soporte para hover effects, gradientes simulados y animaciones.
"""
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable

from app.ui.themes.design_tokens import (
    COLORS, TYPOGRAPHY, SPACING, SHADOWS, CARD_GRADIENTS
)
from app.ui.themes.base_theme import BaseTheme
from app.ui.components.animations import HoverTracker


class InfoCard(ttk.LabelFrame):
    """Tarjeta contenedora con borde semántico y título.
    Variants: primary, success, info, warning, error, neutral.
    """
    def __init__(self, parent, text: str = "", icon: str = "",
                 variant: str = "primary", padding: int = SPACING.md, **kwargs):
        display = f" {icon} {text}" if icon else text
        colors = CARD_GRADIENTS.get(variant, CARD_GRADIENTS["neutral"])
        super().__init__(parent, text=display,
                        font=(TYPOGRAPHY.body_family, 9, "bold"),
                        foreground=colors["border"], padding=padding,
                        background=colors["start"], **kwargs)


class MetricCard(tk.Frame):
    """Tarjeta compacta con label + valor alineado.
    Versión mejorada con hover highlight y color semántico.
    """
    def __init__(self, parent, label: str, value: str,
                 color: Optional[str] = None,
                 variant: str = "neutral",
                 on_click: Optional[Callable] = None, **kwargs):
        super().__init__(parent, relief=SHADOWS.low, bd=1,
                        bg=COLORS.dark_bg_tertiary, **kwargs)
        colors = CARD_GRADIENTS.get(variant, CARD_GRADIENTS["neutral"])
        c = color or colors["text"]

        ttk.Label(self, text=label, font=(TYPOGRAPHY.body_family, 9),
                 foreground=COLORS.dark_fg_secondary).pack(
                     padx=SPACING.sm, pady=(SPACING.xs, SPACING.xs), anchor="center")

        self._val_label = ttk.Label(self, text=value,
            font=(TYPOGRAPHY.heading_family, 14, "bold"),
            foreground=c)
        self._val_label.pack(padx=SPACING.sm, pady=(SPACING.xs, SPACING.xs), anchor="center")

        if on_click:
            HoverTracker.bind_recursive(self,
                lambda w: w.configure(background="#3d3d3d"),
                lambda w: w.configure(background=COLORS.dark_bg_tertiary))
            for w in [self, self._val_label]:
                w.bind("<Button-1>", lambda e: on_click())

    def set_value(self, value: str, color: Optional[str] = None):
        self._val_label.config(text=value)
        if color:
            self._val_label.config(foreground=color)


class EnhancedKPICard(tk.Frame):
    """Tarjeta KPI moderna con gradiente, hover y animaciones.
    Features:
        - Borde superior con color de acento
        - Fondo degradado (start -> end)
        - Efecto hover: iluminación
        - Icono + título + valor + tendencia
        - Click handler opcional
    """
    def __init__(self, parent, title: str = "", value: str = "0",
                 subtitle: str = "", icon: str = "",
                 variant: str = "primary",
                 trend_direction: str = "stable",
                 trend_value: Optional[str] = None,
                 secondary_value: Optional[str] = None,
                 secondary_label: str = "",
                 on_click: Optional[Callable] = None, **kwargs):
        super().__init__(parent, **kwargs)
        colors = CARD_GRADIENTS.get(variant, CARD_GRADIENTS["neutral"])
        self.configure(relief=SHADOWS.low, bd=1, bg=colors["start"])
        self._colors = colors

        # Borde superior highlight
        tk.Frame(self, bg=colors["border"], bd=0, height=3).pack(fill=tk.X)

        # Header: icon + title
        hdr = ttk.Frame(self)
        hdr.pack(fill=tk.X, padx=SPACING.md, pady=(SPACING.sm, SPACING.xs))
        if icon:
            ttk.Label(hdr, text=icon,
                     font=(TYPOGRAPHY.body_family, 18)).pack(
                         side=tk.LEFT, padx=(0, SPACING.sm))
        ttk.Label(hdr, text=title,
                 font=(TYPOGRAPHY.heading_family, 11, "bold"),
                 foreground=colors["border"]).pack(
                     side=tk.LEFT, fill=tk.X, expand=True)

        # Value section
        val_frame = ttk.Frame(self)
        val_frame.pack(expand=True, fill=tk.BOTH, padx=SPACING.md)
        self._val_label = ttk.Label(val_frame, text=value,
            font=(TYPOGRAPHY.heading_family, 22, "bold"),
            foreground=colors["border"])
        self._val_label.pack(pady=(SPACING.sm, 0), anchor="center")

        if subtitle:
            ttk.Label(val_frame, text=subtitle,
                     font=(TYPOGRAPHY.body_family, 9),
                     foreground=COLORS.dark_fg_secondary).pack(
                         pady=(SPACING.xs, 0))

        # Trend indicator
        if trend_value:
            sym = {"up": "\u25b2", "down": "\u25bc",
                   "stable": "\u25c6"}.get(trend_direction, "\u25cf")
            tc = {"up": COLORS.success, "down": COLORS.error,
                  "stable": COLORS.info}.get(trend_direction, COLORS.info)
            self._trend_label = ttk.Label(val_frame,
                text=f"{sym} {trend_value}",
                font=(TYPOGRAPHY.body_family, 9), foreground=tc)
            self._trend_label.pack(pady=(SPACING.xs, 0))

        # Secondary value
        if secondary_value or secondary_label:
            sec = ttk.Frame(self)
            sec.pack(fill=tk.X, padx=SPACING.md, pady=(0, SPACING.xs))
            if secondary_label:
                ttk.Label(sec, text=secondary_label,
                         font=(TYPOGRAPHY.body_family, 9),
                         foreground=COLORS.dark_fg_disabled).pack(
                             side=tk.LEFT, padx=(0, SPACING.xs))
            if secondary_value:
                ttk.Label(sec, text=secondary_value,
                         font=(TYPOGRAPHY.body_family, 10, "bold"),
                         foreground=colors["accent"]).pack(side=tk.RIGHT)

        # Hover effect
        HoverTracker.bind_recursive(self,
            lambda w: (w.configure(background=colors["end"])
                      if hasattr(w, 'configure') else None),
            lambda w: (w.configure(background=colors["start"])
                      if hasattr(w, 'configure') else None))

        # Click handler
        if on_click:
            for w in [self, hdr, val_frame]:
                w.bind("<Button-1>", lambda e: on_click())

    def set_value(self, value: str):
        """Actualiza el valor mostrado en la tarjeta KPI."""
        self._val_label.config(text=value)

    def set_trend(self, direction: str, value=None):
        """Actualiza la tendencia (direccion y texto opcional)."""
        sym = {"up": "\u25b2", "down": "\u25bc",
               "stable": "\u25c6"}.get(direction, "\u25cf")
        tc = {"up": COLORS.success, "down": COLORS.error,
              "stable": COLORS.info}.get(direction, COLORS.info)
        if hasattr(self, '_trend_label'):
            if value:
                self._trend_label.config(text=f"{sym} {value}", foreground=tc)
            else:
                self._trend_label.config(text=sym, foreground=tc)

class StatCard(tk.Frame):
    """Tarjeta estadistica pequena para grid de stats."""
    def __init__(self, parent, label: str, value: str,
                 icon: str = "", variant: str = "neutral",
                 progress=None, progress_max: float = 100, **kwargs):
        super().__init__(parent, relief=SHADOWS.low, bd=1,
                        bg=COLORS.dark_bg_secondary, **kwargs)
        colors = CARD_GRADIENTS.get(variant, CARD_GRADIENTS["neutral"])
        row = ttk.Frame(self)
        row.pack(fill=tk.X, padx=SPACING.sm, pady=SPACING.xs)
        if icon:
            ttk.Label(row, text=icon,
                     font=(TYPOGRAPHY.body_family, 14)).pack(
                         side=tk.LEFT, padx=(0, SPACING.xs))
        ttk.Label(row, text=label,
                 font=(TYPOGRAPHY.body_family, 9),
                 foreground=COLORS.dark_fg_secondary).pack(
                     side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(self, text=value,
                 font=(TYPOGRAPHY.heading_family, 18, "bold"),
                 foreground=colors["text"]).pack(
                     padx=SPACING.sm, pady=(0, SPACING.xs))
        if progress is not None:
            pbar = tk.Frame(self, bg=COLORS.dark_bg_tertiary,
                            height=4, bd=0)
            pbar.pack(fill=tk.X, padx=SPACING.sm, pady=(SPACING.xs, 0))
            pct = min(1.0, progress / progress_max)
            tk.Frame(pbar, background=colors["border"], bd=0,
                    height=4).place(relx=0, rely=0, relwidth=pct, relheight=1)

__all__ = ["InfoCard", "MetricCard", "EnhancedKPICard", "StatCard"]