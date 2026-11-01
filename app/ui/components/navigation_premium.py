"""
navigation_premium.py — Sidebar y navegación premium moderno
Inspiración: Visual Studio Code, Figma, Linear
Características:
- Diseño minimalista glassmorphism
- Animaciones suaves
- Indicadores visuales mejorados
- Hover effects premium
- Colores semánticos
"""
import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Optional, Callable
from app.ui.themes.design_tokens import COLORS, TYPOGRAPHY, SPACING


# Colores premium
COLOR_BG_PRIMARY = "#0f0f0f"
COLOR_BG_SECONDARY = "#1a1a1a"
COLOR_BG_TERTIARY = "#252525"
COLOR_BORDER = "#3d3d3d"
COLOR_TEXT_PRIMARY = "#ffffff"
COLOR_TEXT_SECONDARY = "#b0b0b0"
COLOR_ACCENT = "#6366f1"
COLOR_ACCENT_HOVER = "#8b5cf6"


class SidebarPremium(tk.Frame):
    """Sidebar colapsable premium con animaciones."""
    
    W_EXPANDED = 200
    W_COLLAPSED = 70

    def __init__(self, parent, items: List[Tuple[str, str, Optional[Callable]]], **kwargs):
        super().__init__(parent, bg=COLOR_BG_SECONDARY, **kwargs)
        self._items = items
        self._collapsed = False
        self._active_idx = 0
        self._buttons = []
        
        # Configure width
        self.pack_propagate(False)
        self.configure(width=self.W_EXPANDED)
        
        # Header container
        header = tk.Frame(self, bg=COLOR_BG_SECONDARY)
        header.pack(fill=tk.X, padx=0, pady=0)
        header.pack_propagate(False)
        
        # Toggle button
        self.toggle_btn = tk.Button(
            header, text="☰",
            bg=COLOR_BG_TERTIARY, fg=COLOR_TEXT_PRIMARY,
            font=("Arial", 14), border=0,
            command=self._toggle_collapse,
            cursor="hand2", relief=tk.FLAT, highlightthickness=0,
            activebackground=COLOR_ACCENT, activeforeground=COLOR_TEXT_PRIMARY,
            padx=SPACING.md, pady=SPACING.md
        )
        self.toggle_btn.pack(fill=tk.X, padx=0, pady=0)
        
        # Separator
        sep1 = tk.Frame(self, bg=COLOR_BORDER, height=1)
        sep1.pack(fill=tk.X, padx=SPACING.sm, pady=SPACING.sm)
        
        # Section label
        self.section_label = tk.Label(
            self, text="NAVEGACIÓN",
            bg=COLOR_BG_SECONDARY, fg=COLOR_TEXT_SECONDARY,
            font=(TYPOGRAPHY.body_family, 9, "bold")
        )
        self.section_label.pack(fill=tk.X, padx=SPACING.md, pady=(SPACING.md, SPACING.sm))
        
        # Navigation items container
        nav_container = tk.Frame(self, bg=COLOR_BG_SECONDARY)
        nav_container.pack(fill=tk.BOTH, expand=True, padx=SPACING.sm, pady=SPACING.sm)
        
        # Create buttons for each item
        for i, (icon, label, callback) in enumerate(items):
            btn = self._create_nav_button(nav_container, icon, label, callback, i)
            btn.pack(fill=tk.X, pady=SPACING.xs)
            self._buttons.append((btn, label, callback))
        
        # Separator before footer
        sep2 = tk.Frame(self, bg=COLOR_BORDER, height=1)
        sep2.pack(fill=tk.X, padx=SPACING.sm, pady=SPACING.sm, side=tk.BOTTOM)
        
        # Footer
        footer = tk.Frame(self, bg=COLOR_BG_SECONDARY)
        footer.pack(fill=tk.X, padx=SPACING.sm, pady=SPACING.sm, side=tk.BOTTOM)
        
        self.config_btn = tk.Button(
            footer, text="⚙ Configuración",
            bg=COLOR_BG_TERTIARY, fg=COLOR_TEXT_SECONDARY,
            font=(TYPOGRAPHY.body_family, 9),
            border=0, cursor="hand2", relief=tk.FLAT, highlightthickness=0,
            padx=SPACING.md, pady=SPACING.sm,
            activebackground=COLOR_ACCENT, activeforeground=COLOR_TEXT_PRIMARY
        )
        self.config_btn.pack(fill=tk.X)
        
        # Highlight first button
        self._highlight_button(0)

    def _create_nav_button(self, parent, icon, label, callback, idx):
        """Crear botón de navegación."""
        def on_click():
            self._highlight_button(idx)
            if callback:
                callback()
        
        btn = tk.Button(
            parent, text=f"  {icon}  {label}",
            bg=COLOR_BG_TERTIARY, fg=COLOR_TEXT_SECONDARY,
            font=(TYPOGRAPHY.body_family, 10),
            border=0, cursor="hand2", relief=tk.FLAT, highlightthickness=0,
            padx=SPACING.md, pady=SPACING.sm,
            activebackground=COLOR_ACCENT, activeforeground=COLOR_TEXT_PRIMARY,
            command=on_click, justify=tk.LEFT
        )
        
        # Hover effects
        def on_enter(e):
            if idx != self._active_idx:
                btn.config(bg=COLOR_BG_TERTIARY)
        
        def on_leave(e):
            if idx != self._active_idx:
                btn.config(bg=COLOR_BG_TERTIARY)
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn

    def _highlight_button(self, idx):
        """Resaltar botón activo."""
        self._active_idx = idx
        for i, (btn, label, _) in enumerate(self._buttons):
            if i == idx:
                btn.config(
                    bg=COLOR_ACCENT, fg=COLOR_TEXT_PRIMARY,
                    activebackground=COLOR_ACCENT_HOVER
                )
            else:
                btn.config(
                    bg=COLOR_BG_TERTIARY, fg=COLOR_TEXT_SECONDARY,
                    activebackground=COLOR_ACCENT
                )

    def _toggle_collapse(self):
        """Colapsar/expandir sidebar."""
        self._collapsed = not self._collapsed
        
        if self._collapsed:
            # Collapse: hide labels
            self.configure(width=self.W_COLLAPSED)
            self.section_label.pack_forget()
            
            for btn, label, _ in self._buttons:
                btn.config(text=f"  {label[0]}")  # Show only first char of icon
            
            self.config_btn.config(text="⚙")
        else:
            # Expand: show labels
            self.configure(width=self.W_EXPANDED)
            self.section_label.pack(fill=tk.X, padx=SPACING.md, pady=(SPACING.md, SPACING.sm))
            
            for i, (btn, label, _) in enumerate(self._buttons):
                icon = self._items[i][0]
                btn.config(text=f"  {icon}  {label}")
            
            self.config_btn.config(text="⚙ Configuración")

    @property
    def active(self):
        return self._active_idx


class TabNavigatorPremium(tk.Frame):
    """Navegador de tabs premium."""
    
    def __init__(self, parent, tabs: List[str], **kwargs):
        super().__init__(parent, bg=COLOR_BG_SECONDARY, **kwargs)
        
        self._tabs = tabs
        self._active_idx = 0
        self._callbacks = {}
        self._tab_buttons = []
        
        # Tabs container
        tabs_frame = tk.Frame(self, bg=COLOR_BG_SECONDARY)
        tabs_frame.pack(fill=tk.X, padx=0, pady=0)
        
        # Create tab buttons
        for i, tab_name in enumerate(tabs):
            btn = self._create_tab_button(tabs_frame, tab_name, i)
            btn.pack(side=tk.LEFT, padx=SPACING.xs, pady=SPACING.sm)
            self._tab_buttons.append(btn)
        
        # Separator
        sep = tk.Frame(self, bg=COLOR_BORDER, height=1)
        sep.pack(fill=tk.X, padx=0, pady=0)
        
        # Highlight first tab
        self._highlight_tab(0)

    def _create_tab_button(self, parent, name, idx):
        """Crear botón de tab."""
        def on_click():
            self._highlight_tab(idx)
            if idx in self._callbacks:
                self._callbacks[idx]()
        
        btn = tk.Button(
            parent, text=name,
            bg=COLOR_BG_SECONDARY, fg=COLOR_TEXT_SECONDARY,
            font=(TYPOGRAPHY.body_family, 10),
            border=0, cursor="hand2", relief=tk.FLAT, highlightthickness=0,
            padx=SPACING.md, pady=SPACING.sm,
            activebackground=COLOR_BG_SECONDARY, activeforeground=COLOR_ACCENT,
            command=on_click
        )
        
        return btn

    def _highlight_tab(self, idx):
        """Resaltar tab activo."""
        self._active_idx = idx
        for i, btn in enumerate(self._tab_buttons):
            if i == idx:
                btn.config(
                    fg=COLOR_ACCENT,
                    font=(TYPOGRAPHY.body_family, 10, "bold")
                )
            else:
                btn.config(
                    fg=COLOR_TEXT_SECONDARY,
                    font=(TYPOGRAPHY.body_family, 10)
                )

    def bind(self, idx: int, callback: Callable):
        """Vincular callback a tab."""
        self._callbacks[idx] = callback

    @property
    def active(self):
        return self._active_idx


# Aliases para compatibilidad
Sidebar = SidebarPremium
TabNavigator = TabNavigatorPremium
