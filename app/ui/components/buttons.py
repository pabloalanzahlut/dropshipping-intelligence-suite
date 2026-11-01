"""
buttons.py — Variantes de botones estilizados para GEM OS.
Primary, Secondary, Danger, Success, Warning variants.
"""
import tkinter as tk
from tkinter import ttk
from typing import Optional
from app.ui.themes.design_tokens import COLORS, TYPOGRAPHY


def create_button(parent, text: str = "Button", variant: str = "primary",
                  command=None, width: Optional[int] = None, **kwargs):
    """Crea un botón con estilo semántico.

    Variants: primary, secondary, success, danger, warning, ghost.
    """
    styles = {
        "primary": {"bg": COLORS.primary_action, "fg": "#ffffff"},
        "secondary": {"bg": COLORS.dark_bg_tertiary, "fg": COLORS.dark_fg_primary},
        "success": {"bg": COLORS.success, "fg": "#ffffff"},
        "danger": {"bg": COLORS.error, "fg": "#ffffff"},
        "warning": {"bg": COLORS.warning, "fg": "#1f2937"},
        "ghost": {"bg": "transparent", "fg": COLORS.dark_fg_primary},
    }
    s = styles.get(variant, styles["primary"])
    btn = ttk.Button(parent, text=text, command=command, **kwargs)
    return btn


class ActionButton(ttk.Button):
    """Botón de acción con color semántico."""
    def __init__(self, parent, text: str = "", variant: str = "primary",
                 command=None, icon: str = "", **kwargs):
        display = f"{icon} {text}" if icon else text
        super().__init__(parent, text=display, command=command,
                        font=(TYPOGRAPHY.body_family, 9, "bold"), **kwargs)


class IconButton(ttk.Button):
    """Botón icono compacto (sin texto)."""
    def __init__(self, parent, icon: str = "⚙", command=None, **kwargs):
        super().__init__(parent, text=icon, command=command, width=3, **kwargs)