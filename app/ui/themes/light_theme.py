"""
LightTheme v2.0 — Tema claro profesional con paleta Gemini Design System.
Paleta corporativa:
  - Fondo: #ffffff (blanco), #f9fafb (paneles)
  - Acento: #6366f1 (índigo Gemini)
  - Éxito: #10b981 (verde esmeralda)
  - Terminal: #fafafa + texto oscuro legible
"""
from app.ui.themes.base_theme import BaseTheme
from app.ui.themes.design_tokens import COLORS, TYPOGRAPHY


class LightTheme(BaseTheme):
    """Tema claro profesional — Gemini-inspired."""
    name: str = "light"
    # Paleta
    bg_primary: str = COLORS.light_bg_primary
    bg_secondary: str = COLORS.light_bg_secondary
    bg_tertiary: str = COLORS.light_bg_tertiary
    fg_primary: str = COLORS.light_fg_primary
    fg_secondary: str = COLORS.light_fg_secondary
    fg_disabled: str = COLORS.light_fg_disabled
    # Terminal
    console_bg: str = COLORS.light_bg_secondary
    console_fg: str = COLORS.light_fg_primary
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
    # Logs
    log_colors = dict(COLORS.log_colors_light)
    # Progreso
    progress_bar_bg: str = COLORS.light_bg_tertiary
    progress_bar_fg: str = COLORS.primary_action
    progress_label_color: str = COLORS.light_fg_secondary
    # Fuentes
    font_family: str = TYPOGRAPHY.body_family
    font_family_mono: str = TYPOGRAPHY.mono_family
    font_size_base: int = TYPOGRAPHY.body_size