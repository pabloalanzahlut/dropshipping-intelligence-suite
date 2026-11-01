"""Sistema de temas Dark/Light para la interfaz GEM OS v2.0."""
from app.ui.themes.base_theme import BaseTheme
from app.ui.themes.dark_theme import DarkTheme
from app.ui.themes.light_theme import LightTheme
from app.ui.themes.design_tokens import (
    COLORS, TYPOGRAPHY, SPACING, SHADOWS, ANIMATIONS, BREAKPOINTS
)

__all__ = ["BaseTheme", "DarkTheme", "LightTheme",
           "COLORS", "TYPOGRAPHY", "SPACING", "SHADOWS", "ANIMATIONS", "BREAKPOINTS"]