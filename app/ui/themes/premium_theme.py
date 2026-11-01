"""
PremiumTheme — Tema ultra-moderno con paleta profesional inspirada en:
- Figma Design System
- Linear App UI
- Stripe Dashboard
- Modern SaaS applications

Características:
- Glassmorphism effects
- Smooth gradients
- Premium spacing
- Advanced animations
"""
from app.ui.themes.base_theme import BaseTheme
from app.ui.themes.design_tokens import COLORS, TYPOGRAPHY


class PremiumColors:
    """Colores premium con paleta extendida."""
    # Neutrals
    black_0 = "#000000"
    black_50 = "#0f0f0f"
    black_100 = "#1a1a1a"
    black_150 = "#252525"
    black_200 = "#2d2d2d"
    black_300 = "#3d3d3d"
    black_400 = "#525252"
    white_50 = "#f5f5f5"
    white_100 = "#ffffff"
    
    # Primary Accent - Indigo
    indigo_50 = "#6366f1"
    indigo_60 = "#4f46e5"
    indigo_70 = "#4338ca"
    
    # Secondary - Purple
    purple_50 = "#8b5cf6"
    purple_60 = "#7c3aed"
    
    # Semantic Colors
    green_success = "#10b981"
    red_error = "#ef4444"
    yellow_warning = "#f59e0b"
    blue_info = "#3b82f6"
    pink_accent = "#ec4899"
    cyan_accent = "#06b6d4"
    
    # Borders & Surfaces
    border_light = "#e5e7eb"
    border_dark = "#3d3d3d"
    surface_dark = "#2d2d2d"
    surface_darker = "#1a1a1a"
    
    # Text
    text_primary_dark = "#ffffff"
    text_secondary_dark = "#b0b0b0"
    text_tertiary_dark = "#888888"
    text_disabled_dark = "#666666"


class PremiumTheme(BaseTheme):
    """Tema Premium — Diseño ultra-moderno para aplicaciones profesionales."""
    
    name: str = "premium"
    
    # Background
    bg_primary: str = PremiumColors.black_50
    bg_secondary: str = PremiumColors.black_100
    bg_tertiary: str = PremiumColors.black_150
    bg_card: str = PremiumColors.black_200
    bg_hover: str = PremiumColors.black_300
    
    # Foreground
    fg_primary: str = PremiumColors.text_primary_dark
    fg_secondary: str = PremiumColors.text_secondary_dark
    fg_tertiary: str = PremiumColors.text_tertiary_dark
    fg_disabled: str = PremiumColors.text_disabled_dark
    
    # Accents
    accent_primary: str = PremiumColors.indigo_50
    accent_primary_hover: str = PremiumColors.indigo_60
    accent_secondary: str = PremiumColors.purple_50
    
    # Semantic
    success: str = PremiumColors.green_success
    error: str = PremiumColors.red_error
    warning: str = PremiumColors.yellow_warning
    info: str = PremiumColors.blue_info
    
    # Additional
    pink: str = PremiumColors.pink_accent
    cyan: str = PremiumColors.cyan_accent
    
    # Borders
    border: str = PremiumColors.border_dark
    border_subtle: str = "#1a1a1a"
    
    # Font
    font_family: str = TYPOGRAPHY.body_family
    font_family_mono: str = TYPOGRAPHY.mono_family
    font_size_base: int = TYPOGRAPHY.body_size
    
    # Console
    console_bg: str = COLORS.console_bg
    console_fg: str = COLORS.console_fg
    
    # Shadows
    shadow_sm: str = "0 1px 2px rgba(0,0,0,0.05)"
    shadow_md: str = "0 4px 6px rgba(0,0,0,0.1)"
    shadow_lg: str = "0 10px 15px rgba(0,0,0,0.1)"
    shadow_xl: str = "0 20px 25px rgba(0,0,0,0.1)"
    
    # Animations
    transition_fast: str = "150ms cubic-bezier(0.4, 0, 0.2, 1)"
    transition_base: str = "250ms cubic-bezier(0.4, 0, 0.2, 1)"
    transition_slow: str = "350ms cubic-bezier(0.4, 0, 0.2, 1)"


class PremiumSpacing:
    """Sistema de espaciado premium."""
    xs = 4
    sm = 8
    md = 12
    lg = 16
    xl = 24
    xxl = 32


class PremiumTypography:
    """Sistema tipográfico premium."""
    
    # Display
    display_lg = ("Inter", 32, "bold")
    display_md = ("Inter", 28, "bold")
    display_sm = ("Inter", 24, "bold")
    
    # Heading
    heading_lg = ("Inter", 20, "bold")
    heading_md = ("Inter", 16, "bold")
    heading_sm = ("Inter", 14, "bold")
    heading_xs = ("Inter", 12, "bold")
    
    # Body
    body_lg = ("Inter", 16, "normal")
    body_md = ("Inter", 14, "normal")
    body_sm = ("Inter", 12, "normal")
    body_xs = ("Inter", 11, "normal")
    
    # Mono
    mono_lg = ("Courier New", 12, "normal")
    mono_md = ("Courier New", 11, "normal")
    mono_sm = ("Courier New", 10, "normal")
    mono_xs = ("Courier New", 9, "normal")


class PremiumElevation:
    """Sistema de elevación (z-index)."""
    base = 0
    dropdown = 10
    sticky = 20
    floating = 30
    modal = 40
    popup = 50
