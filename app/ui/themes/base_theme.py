"""
BaseTheme v2.0 — Clase base con paleta extendida Gemini + Design System.
Define el contrato de colores, estilos ttk y fuentes que cada tema
debe implementar. Los temas se aplican globalmente via ttk.Style().
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional
from app.ui.themes.design_tokens import COLORS, TYPOGRAPHY, SPACING, SHADOWS


@dataclass
class BaseTheme:
    """Especificación completa de un tema visual v2.0.

    Atributos extendidos:
        bg_tertiary: Fondo terciario (cards, raised surfaces).
        fg_disabled: Color para texto deshabilitado.
        accent_hover: Color de acento en hover.
        success/warning/error/info + variantes _dim (hover/states).
        surface_elevation: Relieve para componentes elevados.
    """
    name: str = "base"

    # Paleta general (v2.0)
    bg_primary: str = COLORS.dark_bg_primary
    bg_secondary: str = COLORS.dark_bg_secondary
    bg_tertiary: str = COLORS.dark_bg_tertiary
    fg_primary: str = COLORS.dark_fg_primary
    fg_secondary: str = COLORS.dark_fg_secondary
    fg_disabled: str = COLORS.dark_fg_disabled

    # Terminal
    console_bg: str = COLORS.console_bg
    console_fg: str = COLORS.console_fg

    # Acentos
    accent: str = COLORS.primary_action
    accent_hover: str = COLORS.primary_action_hover

    # Semántica
    success: str = COLORS.success
    success_dim: str = COLORS.success_dim
    warning: str = COLORS.warning
    warning_dim: str = COLORS.warning_dim
    error: str = COLORS.error
    error_dim: str = COLORS.error_dim
    info: str = COLORS.info
    info_dim: str = COLORS.info_dim

    # Logs coloreados
    log_colors: Dict[str, str] = field(default_factory=lambda: dict(COLORS.log_colors_dark))

    # Progreso
    progress_bar_bg: str = COLORS.dark_bg_secondary
    progress_bar_fg: str = COLORS.primary_action
    progress_label_color: str = COLORS.dark_fg_secondary

    # Fuentes
    font_family: str = TYPOGRAPHY.body_family
    font_family_mono: str = TYPOGRAPHY.mono_family
    font_size_base: int = TYPOGRAPHY.body_size

    # Botones
    button_font_size: int = TYPOGRAPHY.body_size

    # Elevación
    surface_elevation: str = SHADOWS.low

    # ──────────────────────────────────────────────────────────────────────
    # Apply — Aplica estilos ttk globalmente
    # ──────────────────────────────────────────────────────────────────────
    def apply(self) -> None:
        """Aplica el tema globalmente via ttk.Style()."""
        import tkinter.ttk as ttk
        style = ttk.Style()
        style.theme_use("default")
        # Base
        style.configure(".", font=(self.font_family, self.font_size_base))
        style.configure("TFrame", background=self.bg_primary)
        style.configure("TLabelframe", background=self.bg_secondary)
        style.configure("TLabelframe.Label", background=self.bg_secondary,
                        foreground=self.fg_primary, font=(self.font_family, 10, "bold"))
        # Botón
        style.configure("ConsoleButton.TButton",
                        font=(self.font_family, self.button_font_size, "bold"), padding=6)
        style.map("ConsoleButton.TButton",
                  background=[("active", self.accent), ("!disabled", self.accent_hover)],
                  foreground=[("disabled", self.fg_disabled)])
        # Progress
        style.configure("ConsoleProgress.Horizontal.TProgressbar",
                        thickness=18, troughcolor=self.progress_bar_bg,
                        barcolor=self.progress_bar_fg, background=self.progress_bar_fg)
        # Treeview
        style.configure("Treeview", background=self.bg_secondary,
                        foreground=self.fg_primary, fieldbackground=self.bg_secondary)
        style.configure("Treeview.Heading", background=self.bg_tertiary,
                        foreground=self.fg_primary, font=(self.font_family, 9, "bold"))
        style.map("Treeview", background=[("selected", self.accent)])

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────
    def as_ttk_style_kwargs(self, widget_type: str = "TFrame") -> dict:
        """Devuelve kwargs de color compatibles con ttk widgets."""
        mapping = {
            "TFrame": {"background": self.bg_primary, "relief": self.surface_elevation},
            "TLabel": {"background": self.bg_primary, "foreground": self.fg_primary},
            "TButton": {"background": self.bg_secondary, "foreground": self.fg_primary},
            "TScrolledText": {"background": self.console_bg, "foreground": self.console_fg},
        }
        return mapping.get(widget_type, {})

    def get_log_color(self, level: str) -> str:
        return self.log_colors.get(level.upper(), self.console_fg)

    def get_status_color(self, status: str) -> str:
        mapping = {"ok": self.success, "success": self.success,
                   "warning": self.warning, "warn": self.warning,
                   "error": self.error, "fail": self.error,
                   "info": self.info, "neutral": self.fg_secondary,
                   "disabled": self.fg_disabled}
        return mapping.get(status.lower(), self.fg_secondary)

    def darken(self, hex_color: str, amount: int = 15) -> str:
        """Oscurece un color hex en `amount` porciento."""
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        factor = 1 - amount / 100
        return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"

    def __repr__(self) -> str:
        return f"<Theme '{self.name}'>"