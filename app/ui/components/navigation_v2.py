"""
navigation_v2.py — Sidebar glassmorphism con neon accents (Jack-style)
Basado en el diseño de @Itssssss_Jack: minimalista, moderno, con efectos de glow.
"""
import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Optional, Callable

from app.ui.themes.design_tokens import (
    NEON_COLORS,
    DARK_BASE,
    TEXT_COLORS,
    STATUS_COLORS
)


class ModernSidebarButton(tk.Canvas):
    """Botón de sidebar con efecto glassmorphism y neon hover."""
    
    def __init__(self, parent, icon="", label="", command=None, **kwargs):
        width = kwargs.pop('width', 180)
        height = kwargs.pop('height', 48)
        
        super().__init__(parent, width=width, height=height,
                        bg=DARK_BASE['bg_primary'],
                        highlightthickness=0, **kwargs)
        
        self.icon = icon
        self.label = label
        self.command = command
        self.is_active = False
        self.is_hovered = False
        
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        
        self._draw()
    
    def _draw(self):
        """Dibuja el botón con estado actual."""
        self.delete("all")
        
        w = int(self.cget("width"))
        h = int(self.cget("height"))
        
        # Background
        if self.is_active:
            bg_color = DARK_BASE['bg_tertiary']
            border_color = NEON_COLORS['cyan']
            text_color = NEON_COLORS['cyan']
            border_width = 2
        elif self.is_hovered:
            bg_color = DARK_BASE['bg_secondary']
            border_color = TEXT_COLORS['secondary']
            text_color = TEXT_COLORS['primary']
            border_width = 1
        else:
            bg_color = DARK_BASE['bg_primary']
            border_color = ""
            text_color = TEXT_COLORS['secondary']
            border_width = 0
        
        # Rectángulo principal
        if border_width > 0:
            self.create_rectangle(2, 2, w-2, h-2,
                                fill=bg_color, outline=border_color,
                                width=border_width, tags="bg")
        else:
            self.create_rectangle(0, 0, w, h,
                                fill=bg_color, outline="",
                                tags="bg")
        
        # Línea vertical neon si está activo
        if self.is_active:
            self.create_rectangle(0, h//4, 3, 3*h//4,
                                fill=NEON_COLORS['cyan'], outline="",
                                tags="accent_line")
        
        # Icono
        icon_x = 20 if self.label else w/2
        self.create_text(icon_x, h/2, text=self.icon,
                        fill=text_color, font=("Segoe UI", 16),
                        tags="icon")
        
        # Label (si existe)
        if self.label:
            self.create_text(45, h/2, text=self.label, anchor="w",
                           fill=text_color, font=("Segoe UI", 10, "bold"),
                           tags="label")
    
    def _on_enter(self, event):
        if not self.is_active:
            self.is_hovered = True
            self._draw()
    
    def _on_leave(self, event):
        self.is_hovered = False
        self._draw()
    
    def _on_click(self, event):
        if self.command:
            self.command()
    
    def set_active(self, active: bool):
        """Marca el botón como activo."""
        self.is_active = active
        self._draw()


class Sidebar(tk.Frame):
    """Sidebar glassmorphism con navegación premium (Jack-style)."""
    
    EXPANDED_WIDTH = 220
    COLLAPSED_WIDTH = 70
    
    def __init__(self, parent, items: List[Tuple[str, str, Optional[Callable]]], **kwargs):
        super().__init__(parent, bg=DARK_BASE['bg_secondary'], **kwargs)
        
        self.items = items
        self.is_collapsed = False
        self.active_index = 0
        self.buttons = []
        
        self.configure(width=self.EXPANDED_WIDTH)
        self.pack_propagate(False)
        
        self._build_ui()
    
    def _build_ui(self):
        """Construye la interfaz del sidebar."""
        
        # ===== HEADER CON LOGO =====
        header_frame = tk.Frame(self, bg=DARK_BASE['bg_secondary'], height=80)
        header_frame.pack(fill=tk.X, pady=(15, 10))
        header_frame.pack_propagate(False)
        
        # Logo con glassmorphism mejorado
        logo_canvas = tk.Canvas(header_frame, width=50, height=50,
                               bg=DARK_BASE['bg_secondary'],
                               highlightthickness=0)
        logo_canvas.place(relx=0.5, rely=0.5, anchor="center")
        
        # Círculo de fondo más claro para mejor contraste
        logo_canvas.create_oval(2, 2, 48, 48,
                               fill="#252535",  # Fondo más claro
                               outline=NEON_COLORS['cyan'],
                               width=3)  # Borde más grueso
        
        # Círculo interior con gradiente (simulado)
        logo_canvas.create_oval(6, 6, 44, 44,
                               fill="#1e1e2e",
                               outline="")
        
        # Icono central con mejor contraste
        logo_canvas.create_text(25, 25, text="💎",
                               font=("Segoe UI", 22),  # Más grande
                               fill=NEON_COLORS['cyan'])  # Color cyan brillante
        
        # Título (se oculta al colapsar) con mejor contraste
        self.title_label = tk.Label(header_frame, text="GEM OS",
                                   font=("Segoe UI", 13, "bold"),
                                   fg="#00f5ff",  # Cyan más brillante
                                   bg=DARK_BASE['bg_secondary'])
        self.title_label.place(relx=0.5, rely=0.85, anchor="center")
        
        # Separator
        separator = tk.Frame(self, bg=TEXT_COLORS['tertiary'], height=1)
        separator.pack(fill=tk.X, padx=15, pady=8)
        
        # ===== NAVIGATION ITEMS =====
        nav_frame = tk.Frame(self, bg=DARK_BASE['bg_secondary'])
        nav_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)
        
        for i, (icon, label, callback) in enumerate(self.items):
            btn = ModernSidebarButton(
                nav_frame,
                icon=icon,
                label=label,
                command=lambda idx=i: self._on_item_click(idx),
                width=self.EXPANDED_WIDTH - 16
            )
            btn.pack(fill=tk.X, pady=3)
            self.buttons.append(btn)
        
        # Marcar primero como activo
        if self.buttons:
            self.buttons[0].set_active(True)
        
        # ===== FOOTER CON TOGGLE =====
        footer_frame = tk.Frame(self, bg=DARK_BASE['bg_secondary'], height=60)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=10)
        footer_frame.pack_propagate(False)
        
        # Separator superior
        separator2 = tk.Frame(self, bg=TEXT_COLORS['tertiary'], height=1)
        separator2.pack(fill=tk.X, side=tk.BOTTOM, padx=15, pady=(0, 8))
        
        # Botón de colapsar/expandir
        self.toggle_btn = ModernSidebarButton(
            footer_frame,
            icon="⚙️",
            label="Configuración",
            command=self._toggle_collapse,
            width=self.EXPANDED_WIDTH - 16
        )
        self.toggle_btn.pack(fill=tk.X, padx=8)
    
    def _on_item_click(self, index: int):
        """Maneja el click en un item del sidebar."""
        # Actualizar botón activo
        for i, btn in enumerate(self.buttons):
            btn.set_active(i == index)
        
        self.active_index = index
        
        # Ejecutar callback
        icon, label, callback = self.items[index]
        if callback:
            callback()
    
    def _toggle_collapse(self):
        """Colapsa/expande el sidebar."""
        self.is_collapsed = not self.is_collapsed
        
        new_width = self.COLLAPSED_WIDTH if self.is_collapsed else self.EXPANDED_WIDTH
        self.configure(width=new_width)
        
        # Actualizar visibilidad del título
        if self.is_collapsed:
            self.title_label.place_forget()
        else:
            self.title_label.place(relx=0.5, rely=0.85, anchor="center")
        
        # Actualizar botones
        for btn in self.buttons + [self.toggle_btn]:
            btn.configure(width=new_width - 16)
            if self.is_collapsed:
                btn.label = ""
            else:
                # Restaurar labels originales
                idx = self.buttons.index(btn) if btn in self.buttons else -1
                if idx >= 0:
                    btn.label = self.items[idx][1]
                else:
                    btn.label = "Configuración"
            btn._draw()
    
    @property
    def active(self):
        """Retorna el índice activo."""
        return self.active_index


class TabNavigator(tk.Frame):
    """Navegador horizontal con indicador neon (Jack-style)."""
    
    def __init__(self, parent, tabs: List[str], **kwargs):
        super().__init__(parent, bg=DARK_BASE['bg_secondary'], **kwargs)
        
        self.tabs = tabs
        self.active_index = 0
        self.callbacks = {}
        self.tab_labels = []
        
        self._build_ui()
    
    def _build_ui(self):
        """Construye el navegador de tabs."""
        
        tabs_container = tk.Frame(self, bg=DARK_BASE['bg_secondary'])
        tabs_container.pack(fill=tk.X, padx=10, pady=8)
        
        for i, tab_name in enumerate(self.tabs):
            tab_label = tk.Label(
                tabs_container,
                text=tab_name,
                font=("Segoe UI", 10, "bold"),
                bg=DARK_BASE['bg_secondary'],
                fg=TEXT_COLORS['secondary'],
                padx=20,
                pady=8,
                cursor="hand2"
            )
            tab_label.pack(side=tk.LEFT, padx=5)
            tab_label.bind("<Button-1>", lambda e, idx=i: self._on_tab_click(idx))
            tab_label.bind("<Enter>", lambda e, lbl=tab_label: self._on_hover(lbl))
            tab_label.bind("<Leave>", lambda e, lbl=tab_label: self._on_leave(lbl))
            
            self.tab_labels.append(tab_label)
        
        # Indicador neon
        self.indicator = tk.Frame(self, bg=NEON_COLORS['cyan'], height=3)
        self.indicator.pack(fill=tk.X, padx=10)
        
        # Activar primera tab
        self._set_active(0)
    
    def _on_tab_click(self, index: int):
        """Maneja el click en una tab."""
        self._set_active(index)
        
        if index in self.callbacks:
            self.callbacks[index]()
    
    def _set_active(self, index: int):
        """Marca una tab como activa."""
        self.active_index = index
        
        for i, label in enumerate(self.tab_labels):
            if i == index:
                label.config(fg=NEON_COLORS['cyan'])
            else:
                label.config(fg=TEXT_COLORS['secondary'])
        
        # Animar indicador (simplificado para tkinter)
        self.indicator.pack_forget()
        self.indicator.pack(fill=tk.X, padx=(10 + index * 100, 10))
    
    def _on_hover(self, label):
        """Efecto hover."""
        current_color = label.cget("fg")
        if current_color != NEON_COLORS['cyan']:
            label.config(fg=TEXT_COLORS['primary'])
    
    def _on_leave(self, label):
        """Efecto leave."""
        idx = self.tab_labels.index(label)
        if idx != self.active_index:
            label.config(fg=TEXT_COLORS['secondary'])
    
    def bind(self, index: int, callback: Callable):
        """Vincula un callback a una tab."""
        self.callbacks[index] = callback
    
    @property
    def active(self):
        """Retorna el índice activo."""
        return self.active_index
