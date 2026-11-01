"""
DarkTheme v3.0 — Jack-Style Premium Dark Theme
Inspirado en @Itssssss_Jack: neon accents, glassmorphism, deep blacks
Paleta:
  - Fondo: #0a0a0f (deep black) → #13131a (elevated)
  - Acento: #00f5ff (cyan neon)
  - Secundario: #b462ff (purple), #ff006e (pink)
  - Terminal: #0a0a0f + cyan neón #00f5ff
"""
from app.ui.themes.base_theme import BaseTheme
from app.ui.themes.design_tokens import (
    NEON_COLORS, 
    DARK_BASE, 
    TEXT_COLORS, 
    STATUS_COLORS,
    TYPOGRAPHY
)


class DarkTheme(BaseTheme):
    """Tema oscuro premium — Jack-Style with neon accents."""
    name: str = "dark"
    
    # Paleta base oscura profunda
    bg_primary: str = DARK_BASE['bg_primary']        # #0a0a0f
    bg_secondary: str = DARK_BASE['bg_secondary']    # #13131a
    bg_tertiary: str = DARK_BASE['bg_tertiary']      # #1a1a24
    
    # Texto con jerarquía neon
    fg_primary: str = TEXT_COLORS['primary']         # #ffffff
    fg_secondary: str = TEXT_COLORS['secondary']     # #b4b4c8
    fg_disabled: str = TEXT_COLORS['disabled']       # #4a4a5e
    
    # Terminal premium
    console_bg: str = DARK_BASE['bg_primary']        # #0a0a0f
    console_fg: str = NEON_COLORS['cyan']            # #00f5ff
    
    # Acentos neon principales
    accent: str = NEON_COLORS['cyan']                # #00f5ff
    accent_hover: str = NEON_COLORS['blue']          # #00d9ff
    accent_secondary: str = NEON_COLORS['purple']    # #b462ff
    accent_tertiary: str = NEON_COLORS['pink']       # #ff006e
    
    # Semántica con neon
    success: str = STATUS_COLORS['success']          # #00ff88
    success_dim: str = "#00ff8833"
    warning: str = STATUS_COLORS['warning']          # #ffea00
    warning_dim: str = "#ffea0033"
    error: str = STATUS_COLORS['error']              # #ff006e
    error_dim: str = "#ff006e33"
    info: str = STATUS_COLORS['info']                # #00d9ff
    info_dim: str = "#00d9ff33"
    
    # Logs con neon accents
    log_colors = {
        'DEBUG': TEXT_COLORS['tertiary'],
        'INFO': NEON_COLORS['cyan'],
        'WARNING': STATUS_COLORS['warning'],
        'ERROR': STATUS_COLORS['error'],
        'CRITICAL': NEON_COLORS['pink']
    }
    
    # Progreso con glassmorphism
    progress_bar_bg: str = DARK_BASE['bg_input']
    progress_bar_fg: str = NEON_COLORS['cyan']
    progress_label_color: str = TEXT_COLORS['secondary']
    
    # Fuentes modernas
    font_family: str = TYPOGRAPHY.body_family
    font_family_mono: str = TYPOGRAPHY.mono_family
    font_size_base: int = TYPOGRAPHY.body_size