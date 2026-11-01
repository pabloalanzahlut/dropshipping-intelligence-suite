"""
jack_styles.py - Sistema de estilos completo inspirado en @Itssssss_Jack
Provee configuraciones de ttk.Style para aplicar el tema premium globalmente.
"""

import tkinter as tk
from tkinter import ttk
from app.ui.themes.design_tokens import (
    NEON_COLORS,
    DARK_BASE,
    TEXT_COLORS,
    STATUS_COLORS
)


def apply_jack_styles(root: tk.Tk):
    """
    Aplica estilos premium Jack-inspired a todos los widgets ttk.
    Debe llamarse después de crear la ventana principal.
    """
    style = ttk.Style(root)
    
    # Usar tema base clam (más personalizable)
    style.theme_use('clam')
    
    # ===== CONFIGURACIÓN GLOBAL =====
    style.configure('.',
                   background=DARK_BASE['bg_primary'],
                   foreground=TEXT_COLORS['primary'],
                   bordercolor=TEXT_COLORS['tertiary'],
                   darkcolor=DARK_BASE['bg_secondary'],
                   lightcolor=DARK_BASE['bg_tertiary'],
                   troughcolor=DARK_BASE['bg_input'],
                   focuscolor=NEON_COLORS['cyan'],
                   selectbackground=NEON_COLORS['cyan'],
                   selectforeground=DARK_BASE['bg_primary'],
                   font=('Segoe UI', 10))
    
    # ===== FRAMES =====
    style.configure('TFrame',
                   background=DARK_BASE['bg_primary'])
    
    style.configure('Dark.TFrame',
                   background=DARK_BASE['bg_primary'])
    
    style.configure('Card.TFrame',
                   background=DARK_BASE['bg_card'],
                   relief='flat',
                   borderwidth=1)
    
    # ===== LABELS =====
    style.configure('TLabel',
                   background=DARK_BASE['bg_primary'],
                   foreground=TEXT_COLORS['primary'],
                   font=('Segoe UI', 10))
    
    style.configure('Title.TLabel',
                   foreground=NEON_COLORS['cyan'],
                   font=('Segoe UI', 16, 'bold'))
    
    style.configure('Subtitle.TLabel',
                   foreground=TEXT_COLORS['secondary'],
                   font=('Segoe UI', 11))
    
    style.configure('Caption.TLabel',
                   foreground=TEXT_COLORS['tertiary'],
                   font=('Segoe UI', 9))
    
    # ===== BUTTONS =====
    style.configure('TButton',
                   background=DARK_BASE['bg_input'],
                   foreground=TEXT_COLORS['primary'],
                   bordercolor=TEXT_COLORS['tertiary'],
                   focuscolor='none',
                   font=('Segoe UI', 10, 'bold'),
                   padding=(15, 8))
    
    style.map('TButton',
             background=[('active', DARK_BASE['bg_hover']),
                        ('pressed', DARK_BASE['bg_tertiary'])],
             foreground=[('active', NEON_COLORS['cyan']),
                        ('pressed', NEON_COLORS['cyan'])],
             bordercolor=[('active', NEON_COLORS['cyan']),
                         ('pressed', NEON_COLORS['blue'])])
    
    # Botón primario con acento neon
    style.configure('Primary.TButton',
                   background=DARK_BASE['bg_tertiary'],
                   foreground=NEON_COLORS['cyan'],
                   bordercolor=NEON_COLORS['cyan'])
    
    style.map('Primary.TButton',
             background=[('active', NEON_COLORS['cyan']),
                        ('pressed', NEON_COLORS['blue'])],
             foreground=[('active', DARK_BASE['bg_primary']),
                        ('pressed', DARK_BASE['bg_primary'])])
    
    # Botón de éxito
    style.configure('Success.TButton',
                   foreground=STATUS_COLORS['success'],
                   bordercolor=STATUS_COLORS['success'])
    
    # Botón de error
    style.configure('Error.TButton',
                   foreground=STATUS_COLORS['error'],
                   bordercolor=STATUS_COLORS['error'])
    
    # ===== ENTRY =====
    style.configure('TEntry',
                   fieldbackground=DARK_BASE['bg_input'],
                   foreground=TEXT_COLORS['primary'],
                   bordercolor=TEXT_COLORS['tertiary'],
                   insertcolor=NEON_COLORS['cyan'],
                   font=('Segoe UI', 10))
    
    style.map('TEntry',
             fieldbackground=[('focus', DARK_BASE['bg_input'])],
             bordercolor=[('focus', NEON_COLORS['cyan'])])
    
    # ===== COMBOBOX =====
    style.configure('TCombobox',
                   fieldbackground=DARK_BASE['bg_input'],
                   background=DARK_BASE['bg_hover'],
                   foreground=TEXT_COLORS['primary'],
                   bordercolor=TEXT_COLORS['tertiary'],
                   arrowcolor=TEXT_COLORS['secondary'],
                   font=('Segoe UI', 10))
    
    style.map('TCombobox',
             fieldbackground=[('focus', DARK_BASE['bg_input'])],
             bordercolor=[('focus', NEON_COLORS['cyan'])],
             arrowcolor=[('focus', NEON_COLORS['cyan'])])
    
    # ===== TREEVIEW =====
    style.configure('Treeview',
                   background=DARK_BASE['bg_input'],
                   foreground=TEXT_COLORS['primary'],
                   fieldbackground=DARK_BASE['bg_input'],
                   borderwidth=0,
                   font=('Segoe UI', 9))
    
    style.configure('Treeview.Heading',
                   background=DARK_BASE['bg_hover'],
                   foreground=NEON_COLORS['cyan'],
                   borderwidth=1,
                   relief='flat',
                   font=('Segoe UI', 10, 'bold'))
    
    style.map('Treeview',
             background=[('selected', DARK_BASE['bg_hover'])],
             foreground=[('selected', NEON_COLORS['cyan'])])
    
    style.map('Treeview.Heading',
             background=[('active', DARK_BASE['bg_tertiary'])],
             foreground=[('active', NEON_COLORS['blue'])])
    
    # ===== NOTEBOOK (TABS) =====
    style.configure('TNotebook',
                   background=DARK_BASE['bg_secondary'],
                   bordercolor=TEXT_COLORS['tertiary'],
                   tabmargins=[2, 5, 2, 0])
    
    style.configure('TNotebook.Tab',
                   background=DARK_BASE['bg_secondary'],
                   foreground=TEXT_COLORS['secondary'],
                   bordercolor=TEXT_COLORS['tertiary'],
                   padding=[20, 8],
                   font=('Segoe UI', 10, 'bold'))
    
    style.map('TNotebook.Tab',
             background=[('selected', DARK_BASE['bg_tertiary']),
                        ('active', DARK_BASE['bg_hover'])],
             foreground=[('selected', NEON_COLORS['cyan']),
                        ('active', TEXT_COLORS['primary'])],
             expand=[('selected', [1, 1, 1, 0])])
    
    # ===== SCROLLBAR =====
    style.configure('Vertical.TScrollbar',
                   background=DARK_BASE['bg_input'],
                   troughcolor=DARK_BASE['bg_secondary'],
                   bordercolor=DARK_BASE['bg_secondary'],
                   arrowcolor=TEXT_COLORS['secondary'],
                   width=12)
    
    style.map('Vertical.TScrollbar',
             background=[('active', NEON_COLORS['cyan']),
                        ('pressed', NEON_COLORS['blue'])])
    
    style.configure('Horizontal.TScrollbar',
                   background=DARK_BASE['bg_input'],
                   troughcolor=DARK_BASE['bg_secondary'],
                   bordercolor=DARK_BASE['bg_secondary'],
                   arrowcolor=TEXT_COLORS['secondary'],
                   height=12)
    
    style.map('Horizontal.TScrollbar',
             background=[('active', NEON_COLORS['cyan']),
                        ('pressed', NEON_COLORS['blue'])])
    
    # ===== PROGRESSBAR =====
    style.configure('TProgressbar',
                   background=NEON_COLORS['cyan'],
                   troughcolor=DARK_BASE['bg_input'],
                   bordercolor=DARK_BASE['bg_secondary'],
                   lightcolor=NEON_COLORS['cyan'],
                   darkcolor=NEON_COLORS['blue'],
                   thickness=8)
    
    # ===== SEPARATOR =====
    style.configure('TSeparator',
                   background=TEXT_COLORS['tertiary'])
    
    # ===== LABELFRAME =====
    style.configure('TLabelframe',
                   background=DARK_BASE['bg_secondary'],
                   bordercolor=TEXT_COLORS['tertiary'],
                   relief='flat')
    
    style.configure('TLabelframe.Label',
                   background=DARK_BASE['bg_secondary'],
                   foreground=NEON_COLORS['cyan'],
                   font=('Segoe UI', 11, 'bold'))
    
    # ===== CHECKBUTTON =====
    style.configure('TCheckbutton',
                   background=DARK_BASE['bg_primary'],
                   foreground=TEXT_COLORS['primary'],
                   font=('Segoe UI', 10))
    
    style.map('TCheckbutton',
             background=[('active', DARK_BASE['bg_primary'])],
             foreground=[('active', NEON_COLORS['cyan'])])
    
    # ===== RADIOBUTTON =====
    style.configure('TRadiobutton',
                   background=DARK_BASE['bg_primary'],
                   foreground=TEXT_COLORS['primary'],
                   font=('Segoe UI', 10))
    
    style.map('TRadiobutton',
             background=[('active', DARK_BASE['bg_primary'])],
             foreground=[('active', NEON_COLORS['cyan'])])
    
    # ===== SCALE =====
    style.configure('TScale',
                   background=NEON_COLORS['cyan'],
                   troughcolor=DARK_BASE['bg_input'],
                   bordercolor=DARK_BASE['bg_secondary'],
                   sliderlength=30,
                   sliderrelief='flat')
    
    # ===== SPINBOX =====
    style.configure('TSpinbox',
                   fieldbackground=DARK_BASE['bg_input'],
                   background=DARK_BASE['bg_hover'],
                   foreground=TEXT_COLORS['primary'],
                   bordercolor=TEXT_COLORS['tertiary'],
                   arrowcolor=TEXT_COLORS['secondary'],
                   font=('Segoe UI', 10))
    
    style.map('TSpinbox',
             fieldbackground=[('focus', DARK_BASE['bg_input'])],
             bordercolor=[('focus', NEON_COLORS['cyan'])],
             arrowcolor=[('focus', NEON_COLORS['cyan'])])
    
    # ===== PANEDWINDOW =====
    style.configure('TPanedwindow',
                   background=DARK_BASE['bg_primary'])
    
    style.configure('Sash',
                   sashthickness=8,
                   background=TEXT_COLORS['tertiary'])
    
    return style


def apply_widget_animations(widget, hover_color=None, normal_color=None):
    """
    Aplica efectos de hover/press a un widget tk estándar.
    Para simular animaciones y efectos glassmorphism.
    """
    if hover_color is None:
        hover_color = NEON_COLORS['cyan']
    if normal_color is None:
        normal_color = TEXT_COLORS['primary']
    
    def on_enter(event):
        widget.configure(fg=hover_color)
    
    def on_leave(event):
        widget.configure(fg=normal_color)
    
    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)


def create_neon_border(parent, color=None, thickness=2):
    """
    Crea un borde neon alrededor de un frame.
    Retorna el frame border que debe contener el widget.
    """
    if color is None:
        color = NEON_COLORS['cyan']
    
    border_frame = tk.Frame(parent, bg=color, padx=thickness, pady=thickness)
    inner_frame = tk.Frame(border_frame, bg=DARK_BASE['bg_card'])
    inner_frame.pack(fill=tk.BOTH, expand=True)
    
    return border_frame, inner_frame


def create_glass_panel(parent, width=400, height=300, **kwargs):
    """
    Crea un panel con efecto glassmorphism usando Canvas.
    """
    canvas = tk.Canvas(parent, width=width, height=height,
                      bg=DARK_BASE['bg_primary'],
                      highlightthickness=0, **kwargs)
    
    # Background glassmorphism
    canvas.create_rectangle(0, 0, width, height,
                          fill=DARK_BASE['bg_card'],
                          outline="", tags="bg")
    
    # Borde sutil
    canvas.create_rectangle(1, 1, width-1, height-1,
                          fill="", outline=TEXT_COLORS['tertiary'],
                          width=1, tags="border")
    
    return canvas
