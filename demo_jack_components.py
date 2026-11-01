"""
Demo interactivo de los componentes Jack-Style
Muestra todos los componentes premium en una ventana de prueba.
"""

import tkinter as tk
from app.ui.themes.design_tokens import NEON_COLORS, DARK_BASE, TEXT_COLORS
from app.ui.themes.jack_styles import apply_jack_styles
from app.ui.components.financial_validator_panel_v2 import ModernButton, GlassCard, ModernEntry


def main():
    """Crea una ventana de demo con todos los componentes."""
    root = tk.Tk()
    root.title("💎 Demo Jack-Style Components")
    root.geometry("900x700")
    root.configure(bg=DARK_BASE['bg_primary'])
    
    # Aplicar estilos
    apply_jack_styles(root)
    
    # Container principal con scroll
    canvas = tk.Canvas(root, bg=DARK_BASE['bg_primary'], highlightthickness=0)
    scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=DARK_BASE['bg_primary'])
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # ===== TÍTULO =====
    title = tk.Label(
        scrollable_frame,
        text="💎 Jack-Style Components Demo",
        font=("Segoe UI", 24, "bold"),
        fg=NEON_COLORS['cyan'],
        bg=DARK_BASE['bg_primary']
    )
    title.pack(pady=(20, 10))
    
    subtitle = tk.Label(
        scrollable_frame,
        text="Inspirado en @Itssssss_Jack • Glassmorphism & Neon Accents",
        font=("Segoe UI", 11),
        fg=TEXT_COLORS['secondary'],
        bg=DARK_BASE['bg_primary']
    )
    subtitle.pack(pady=(0, 30))
    
    # ===== SECCIÓN: BOTONES =====
    section_title(scrollable_frame, "🔘 Modern Buttons")
    
    buttons_frame = tk.Frame(scrollable_frame, bg=DARK_BASE['bg_primary'])
    buttons_frame.pack(pady=10)
    
    def on_click(style):
        print(f"✅ Botón {style} clickeado!")
    
    btn_primary = ModernButton(buttons_frame, text="Primary", 
                               command=lambda: on_click("primary"), 
                               style="primary")
    btn_primary.pack(side=tk.LEFT, padx=8)
    
    btn_success = ModernButton(buttons_frame, text="Success", 
                               command=lambda: on_click("success"), 
                               style="success")
    btn_success.pack(side=tk.LEFT, padx=8)
    
    btn_warning = ModernButton(buttons_frame, text="Warning", 
                               command=lambda: on_click("warning"), 
                               style="warning")
    btn_warning.pack(side=tk.LEFT, padx=8)
    
    btn_error = ModernButton(buttons_frame, text="Error", 
                             command=lambda: on_click("error"), 
                             style="error")
    btn_error.pack(side=tk.LEFT, padx=8)
    
    btn_secondary = ModernButton(buttons_frame, text="Secondary", 
                                 command=lambda: on_click("secondary"), 
                                 style="secondary")
    btn_secondary.pack(side=tk.LEFT, padx=8)
    
    # ===== SECCIÓN: GLASS CARDS =====
    section_title(scrollable_frame, "💎 Glass Cards")
    
    cards_frame = tk.Frame(scrollable_frame, bg=DARK_BASE['bg_primary'])
    cards_frame.pack(pady=10)
    
    card1 = GlassCard(cards_frame, title="📦 Total", style="primary", width=200, height=100)
    card1.update_content("142", "items")
    card1.pack(side=tk.LEFT, padx=8)
    
    card2 = GlassCard(cards_frame, title="✅ Success", style="success", width=200, height=100)
    card2.update_content("98", "validated")
    card2.pack(side=tk.LEFT, padx=8)
    
    card3 = GlassCard(cards_frame, title="❌ Errors", style="error", width=200, height=100)
    card3.update_content("5", "rejected")
    card3.pack(side=tk.LEFT, padx=8)
    
    card4 = GlassCard(cards_frame, title="📊 Average", style="info", width=200, height=100)
    card4.update_content("73.2%", "margin")
    card4.pack(side=tk.LEFT, padx=8)
    
    # Segunda fila de cards
    cards_frame2 = tk.Frame(scrollable_frame, bg=DARK_BASE['bg_primary'])
    cards_frame2.pack(pady=10)
    
    card5 = GlassCard(cards_frame2, title="🟣 Purple", style="purple", width=200, height=100)
    card5.update_content("24", "special")
    card5.pack(side=tk.LEFT, padx=8)
    
    card6 = GlassCard(cards_frame2, title="🌸 Pink", style="pink", width=200, height=100)
    card6.update_content("12", "critical")
    card6.pack(side=tk.LEFT, padx=8)
    
    card7 = GlassCard(cards_frame2, title="⚪ Neutral", style="neutral", width=200, height=100)
    card7.update_content("88", "pending")
    card7.pack(side=tk.LEFT, padx=8)
    
    # ===== SECCIÓN: INPUTS =====
    section_title(scrollable_frame, "📝 Modern Entries")
    
    entries_frame = tk.Frame(scrollable_frame, bg=DARK_BASE['bg_primary'])
    entries_frame.pack(pady=10)
    
    entry1 = ModernEntry(entries_frame, placeholder="Ingresa tu nombre...")
    entry1.pack(pady=5)
    
    entry2 = ModernEntry(entries_frame, placeholder="Correo electrónico...")
    entry2.pack(pady=5)
    
    entry3 = ModernEntry(entries_frame, placeholder="Buscar productos...")
    entry3.pack(pady=5)
    
    def get_values():
        val1 = entry1.get()
        val2 = entry2.get()
        val3 = entry3.get()
        print(f"\n📋 Valores ingresados:")
        print(f"  Nombre: {val1}")
        print(f"  Email: {val2}")
        print(f"  Búsqueda: {val3}")
    
    btn_get = ModernButton(entries_frame, text="Obtener Valores", 
                          command=get_values, style="primary")
    btn_get.pack(pady=10)
    
    # ===== SECCIÓN: PALETA DE COLORES =====
    section_title(scrollable_frame, "🎨 Color Palette")
    
    colors_frame = tk.Frame(scrollable_frame, bg=DARK_BASE['bg_primary'])
    colors_frame.pack(pady=10)
    
    def create_color_swatch(parent, label, color):
        frame = tk.Frame(parent, bg=DARK_BASE['bg_secondary'], padx=10, pady=8)
        frame.pack(side=tk.LEFT, padx=5)
        
        swatch = tk.Canvas(frame, width=60, height=60, 
                          bg=color, highlightthickness=2,
                          highlightbackground=color)
        swatch.pack()
        
        name_label = tk.Label(frame, text=label, 
                             font=("Segoe UI", 9, "bold"),
                             fg=TEXT_COLORS['primary'],
                             bg=DARK_BASE['bg_secondary'])
        name_label.pack(pady=(4, 0))
        
        hex_label = tk.Label(frame, text=color, 
                            font=("Consolas", 8),
                            fg=TEXT_COLORS['tertiary'],
                            bg=DARK_BASE['bg_secondary'])
        hex_label.pack()
    
    create_color_swatch(colors_frame, "Cyan", NEON_COLORS['cyan'])
    create_color_swatch(colors_frame, "Purple", NEON_COLORS['purple'])
    create_color_swatch(colors_frame, "Pink", NEON_COLORS['pink'])
    create_color_swatch(colors_frame, "Green", NEON_COLORS['green'])
    create_color_swatch(colors_frame, "Yellow", NEON_COLORS['yellow'])
    create_color_swatch(colors_frame, "Blue", NEON_COLORS['blue'])
    
    # ===== FOOTER =====
    footer = tk.Label(
        scrollable_frame,
        text="💎 GEM OS v3.0 • Premium Components Library",
        font=("Segoe UI", 10),
        fg=TEXT_COLORS['tertiary'],
        bg=DARK_BASE['bg_primary']
    )
    footer.pack(pady=(30, 20))
    
    # Bind mouse wheel para scroll
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    canvas.bind_all("<MouseWheel>", on_mousewheel)
    
    print("\n" + "="*60)
    print("  💎 Demo Jack-Style Components")
    print("="*60)
    print("\n✅ Ventana de demo iniciada correctamente")
    print("\n📋 Interactúa con los componentes:")
    print("  • Hover sobre los botones para ver efectos neon")
    print("  • Click en los botones para ver feedback en consola")
    print("  • Escribe en los inputs y obtén los valores")
    print("  • Observa las glass cards con gradientes")
    print("\n" + "="*60 + "\n")
    
    root.mainloop()


def section_title(parent, text):
    """Crea un título de sección."""
    frame = tk.Frame(parent, bg=DARK_BASE['bg_primary'])
    frame.pack(fill=tk.X, padx=20, pady=(20, 5))
    
    title = tk.Label(
        frame,
        text=text,
        font=("Segoe UI", 14, "bold"),
        fg=NEON_COLORS['cyan'],
        bg=DARK_BASE['bg_primary']
    )
    title.pack(anchor="w")
    
    separator = tk.Frame(frame, bg=TEXT_COLORS['tertiary'], height=1)
    separator.pack(fill=tk.X, pady=5)


if __name__ == "__main__":
    main()
