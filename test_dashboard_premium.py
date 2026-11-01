#!/usr/bin/env python3
"""
test_dashboard_premium.py — Script de demostración del Dashboard v3
Prueba visual del nuevo diseño premium
"""
import tkinter as tk
from tkinter import ttk
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ui.components.dashboard_panel import DashboardPanel
from app.database.connection import DatabaseConnection


def main():
    """Crear ventana de demostración."""
    root = tk.Tk()
    root.title("GEM OS Dashboard v3.0 — Preview")
    root.geometry("1400x900")
    root.minsize(1000, 700)
    
    # Set dark background
    root.config(bg="#0f0f0f")
    
    try:
        # Crear dashboard
        db_manager = DatabaseConnection()
        dashboard = DashboardPanel(root, db_manager=db_manager)
        dashboard.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Info label
        info_frame = tk.Frame(root, bg="#1a1a1a", height=40)
        info_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=0, pady=0)
        info_frame.pack_propagate(False)
        
        info_label = tk.Label(
            info_frame,
            text="✨ Dashboard Premium v3.0 — Diseño Moderno Inspirado en Figma, Linear & Stripe",
            bg="#1a1a1a", fg="#888888",
            font=("Segoe UI", 9)
        )
        info_label.pack(anchor="w", padx=16, pady=8)
        
        print("✅ Dashboard Premium v3.0 cargado exitosamente")
        print("📊 Características disponibles:")
        print("   • KPI Cards con diseño glassmorphism")
        print("   • Tablas minimalistas mejoradas")
        print("   • Gráficos con colores dinámicos")
        print("   • Animaciones suaves")
        print("   • Paleta de colores profesional")
        print("   • Tipografía jerárquica")
        print("\nCierra la ventana para salir.")
        
        root.mainloop()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        root.destroy()


if __name__ == "__main__":
    main()
