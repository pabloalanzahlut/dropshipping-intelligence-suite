"""
design_tokens.py — Design System Centralizado de GEM OS
Inspirado en el estilo de @Itssssss_Jack: glassmorphism, neon accents,
y animaciones fluidas. Sistema de diseño moderno y minimalista.
"""
from dataclasses import dataclass, field
from typing import Dict, Tuple

# ═══════════════════════════════════════════════════════════════════
# JACK-STYLE DESIGN SYSTEM — Neon, Glassmorphism & Premium Dark
# ═══════════════════════════════════════════════════════════════════

# Paleta de acentos — idéntica a la web (app/templates/base.html) para que
# escritorio y web se vean como una sola herramienta.
NEON_COLORS = {
    "cyan": "#22d3ee",      # acento principal
    "purple": "#a78bfa",    # violeta
    "pink": "#fb7185",      # rosa (errores / alertas)
    "blue": "#06b6d4",      # cian oscuro
    "green": "#34d399",     # verde (éxito)
    "yellow": "#fbbf24",    # ámbar (avisos)
}

# Fondos oscuros — mismos valores que la web (bg.base/deep/card/hover, border.dim/mid)
DARK_BASE = {
    "bg_primary": "#060810",      # bg.base: fondo de la aplicación
    "bg_secondary": "#08091a",    # bg.deep: barra lateral y barras
    "bg_tertiary": "#0d0f1f",     # bg.card: paneles
    "bg_card": "#0d0f1f",         # bg.card: tarjetas
    "bg_input": "#111328",        # bg.hover: campos y controles
    "bg_hover": "#1a1d35",        # border.dim: estado hover
}

# Sistema de Vidrio (Glassmorphism)
GLASS_EFFECTS = {
    "bg_glass": "rgba(30, 30, 46, 0.7)",
    "bg_glass_light": "rgba(42, 42, 62, 0.5)",
    "border_glass": "rgba(255, 255, 255, 0.1)",
    "shadow_glass": "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
}

# Texto con jerarquía — mismos valores que la web (text.bright → text.muted)
TEXT_COLORS = {
    "primary": "#e8ecff",
    "secondary": "#a8b0d8",
    "tertiary": "#7880b0",
    "disabled": "#4a5080",
    "neon_text": "#22d3ee",
}

# Estados — mismos acentos que las insignias de la web
STATUS_COLORS = {
    "success": "#34d399",
    "error": "#fb7185",
    "warning": "#fbbf24",
    "info": "#22d3ee",
    "neutral": "#a8b0d8",
}

# ═══════════════════════════════════════════════════════════════════
# PALETA DE TARJETAS KPI — Gradientes Neon
# ═══════════════════════════════════════════════════════════════════

CARD_GRADIENTS: Dict[str, Dict[str, str]] = {
    "success": {
        "start": "#0d1a15",
        "end": "#0a0a0f",
        "border": "#00ff88",
        "accent": "#00ff88",
        "text": "#00ff88",
        "glow": "0 0 20px rgba(0, 255, 136, 0.3)",
        "inner_glow": "rgba(0, 255, 136, 0.1)"
    },
    "info": {
        "start": "#0d1520",
        "end": "#0a0a0f",
        "border": "#00d9ff",
        "accent": "#00d9ff",
        "text": "#00d9ff",
        "glow": "0 0 20px rgba(0, 217, 255, 0.3)",
        "inner_glow": "rgba(0, 217, 255, 0.1)"
    },
    "warning": {
        "start": "#1a1a0d",
        "end": "#0a0a0f",
        "border": "#ffea00",
        "accent": "#ffea00",
        "text": "#ffea00",
        "glow": "0 0 20px rgba(255, 234, 0, 0.3)",
        "inner_glow": "rgba(255, 234, 0, 0.1)"
    },
    "error": {
        "start": "#1a0d15",
        "end": "#0a0a0f",
        "border": "#ff006e",
        "accent": "#ff006e",
        "text": "#ff006e",
        "glow": "0 0 20px rgba(255, 0, 110, 0.3)",
        "inner_glow": "rgba(255, 0, 110, 0.1)"
    },
    "primary": {
        "start": "#13131a",
        "end": "#0a0a0f",
        "border": "#00f5ff",
        "accent": "#00f5ff",
        "text": "#00f5ff",
        "glow": "0 0 20px rgba(0, 245, 255, 0.3)",
        "inner_glow": "rgba(0, 245, 255, 0.1)"
    },
    "purple": {
        "start": "#15091a",
        "end": "#0a0a0f",
        "border": "#b462ff",
        "accent": "#b462ff",
        "text": "#b462ff",
        "glow": "0 0 20px rgba(180, 98, 255, 0.3)",
        "inner_glow": "rgba(180, 98, 255, 0.1)"
    },
    "pink": {
        "start": "#1a0d15",
        "end": "#0a0a0f",
        "border": "#ff006e",
        "accent": "#ff006e",
        "text": "#ff006e",
        "glow": "0 0 20px rgba(255, 0, 110, 0.3)",
        "inner_glow": "rgba(255, 0, 110, 0.1)"
    },
    "neutral": {
        "start": "#1a1a24",
        "end": "#0a0a0f",
        "border": "#b4b4c8",
        "accent": "#b4b4c8",
        "text": "#b4b4c8",
        "glow": "0 0 15px rgba(180, 180, 200, 0.2)",
        "inner_glow": "rgba(180, 180, 200, 0.05)"
    },
}

# Mapa de iconos por tipo de métrica
KPI_ICONS: Dict[str, str] = {
    "productos": "📦",
    "validaciones": "✅",
    "transcripciones": "🎬",
    "copys": "✍️",
    "guiones": "🎵",
    "tiktok": "🎵",
    "trafico": "📊",
    "nichos": "🎯",
    "score": "📈",
    "tokens": "🔤",
    "ahorro": "💰",
    "duracion": "⏱",
}


# ═══════════════════════════════════════════════════════════════════
# COLORES SEMÁNTICOS — Paleta Gemini-inspired
# ═══════════════════════════════════════════════════════════════════
@dataclass
class GeminiColors:
    """Paleta de colores semánticos. Basado en Material + Gemini Design."""
    # Dark theme
    dark_bg_primary: str = "#1a1a1a"
    dark_bg_secondary: str = "#2d2d2d"
    dark_bg_tertiary: str = "#3d3d3d"
    dark_surface: str = "#404040"
    # Light theme
    light_bg_primary: str = "#ffffff"
    light_bg_secondary: str = "#f9fafb"
    light_bg_tertiary: str = "#f3f4f6"
    light_surface: str = "#e5e7eb"
    # Texto dark
    dark_fg_primary: str = "#ffffff"
    dark_fg_secondary: str = "#b0b0b0"
    dark_fg_disabled: str = "#666666"
    dark_fg_on_primary: str = "#000000"
    # Texto light
    light_fg_primary: str = "#1f2937"
    light_fg_secondary: str = "#4b5563"
    light_fg_disabled: str = "#9ca3af"
    light_fg_on_primary: str = "#ffffff"
    # Semántica (Acción/Estado)
    primary_action: str = "#6366f1"       # Índigo
    primary_action_hover: str = "#4f46e5"
    success: str = "#10b981"              # Verde esmeralda
    success_dim: str = "#059669"
    warning: str = "#f59e0b"              # Ámbar
    warning_dim: str = "#d97706"
    error: str = "#ef4444"                # Rojo
    error_dim: str = "#dc2626"
    info: str = "#3b82f6"                 # Azul
    info_dim: str = "#1d4ed8"
    # Secundarios
    pink: str = "#ec4899"
    amber: str = "#f97316"
    cyan: str = "#06b6d4"
    purple: str = "#a855f7"
    # Terminal
    console_bg: str = "#0f0f0f"
    console_fg: str = "#4af626"
    console_error: str = "#ff1744"
    console_warning: str = "#ffd54f"
    console_debug: str = "#6a1b9a"
    console_system: str = "#8a8a8a"

    @property
    def log_colors_dark(self) -> Dict[str, str]:
        return {"SYSTEM": self.console_system, "INFO": self.console_fg,
                "OK": "#00c853", "WARNING": self.console_warning,
                "ERROR": self.console_error, "CRITICAL": "#d50000",
                "DEBUG": self.console_debug}

    @property
    def log_colors_light(self) -> Dict[str, str]:
        return {"SYSTEM": self.light_fg_disabled, "INFO": self.light_fg_primary,
                "OK": "#2e7d32", "WARNING": "#f9a825",
                "ERROR": "#c62828", "CRITICAL": "#b71c1c",
                "DEBUG": "#6a1b9a"}

# ═══════════════════════════════════════════════════════════════════
# TIPOGRAFÍA
# ═══════════════════════════════════════════════════════════════════
@dataclass
class Typography:
    heading_family: str = "Segoe UI"
    body_family: str = "Segoe UI"
    mono_family: str = "Consolas"
    h1_size: int = 14; h2_size: int = 12; h3_size: int = 11
    body_size: int = 10; body_small: int = 9; mono_size: int = 9

    @property
    def h1(self) -> Tuple[str, int, str]:
        return (self.heading_family, self.h1_size, "bold")
    @property
    def h2(self) -> Tuple[str, int, str]:
        return (self.heading_family, self.h2_size, "bold")
    @property
    def h3(self) -> Tuple[str, int, str]:
        return (self.heading_family, self.h3_size, "bold")
    @property
    def body(self) -> Tuple[str, int, str]:
        return (self.body_family, self.body_size, "normal")
    @property
    def body_emph(self) -> Tuple[str, int, str]:
        return (self.body_family, self.body_size, "bold")
    @property
    def body_sm(self) -> Tuple[str, int, str]:
        return (self.body_family, self.body_small, "normal")
    @property
    def mono(self) -> Tuple[str, int, str]:
        return (self.mono_family, self.mono_size, "normal")


@dataclass
class Spacing:
    """Sistema de espaciado basado en múltiplos de 8px."""
    xs: int = 4; sm: int = 8; md: int = 16
    lg: int = 24; xl: int = 32; xxl: int = 48
    card_padding: Tuple[int, ...] = (12, 16, 12, 16)
    panel_padding: Tuple[int, ...] = (10, 10, 10, 10)
    table_padding: Tuple[int, ...] = (4, 8, 4, 8)


@dataclass
class Shadows:
    """Elevación simulada con relief+bd de Tkinter."""
    low: str = "raised"; medium: str = "raised"
    high: str = "ridge"; flat: str = "flat"; sunken: str = "sunken"


@dataclass
class Animations:
    """Tiempos estándar para microinteracciones (ms)."""
    quick: int = 100; normal: int = 200
    slow: int = 300; progress_update: int = 80


@dataclass
class Breakpoints:
    """Breakpoints responsive para Tkinter."""
    min_width: int = 800; small_width: int = 1000
    standard_width: int = 1200; large_width: int = 1600
    min_height: int = 600


# ═══════════════════════════════════════════════════════════════════
# SINGLETONS DE ACCESO RÁPIDO
# ═══════════════════════════════════════════════════════════════════
COLORS = GeminiColors()
TYPOGRAPHY = Typography()
SPACING = Spacing()
SHADOWS = Shadows()
ANIMATIONS = Animations()
BREAKPOINTS = Breakpoints()

__all__ = [
    "COLORS", "TYPOGRAPHY", "SPACING", "SHADOWS", "ANIMATIONS", "BREAKPOINTS",
    "CARD_GRADIENTS", "KPI_ICONS",
    "GeminiColors", "Typography", "Spacing", "Shadows", "Animations", "Breakpoints",
]