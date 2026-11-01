"""
Test visual del rediseño Jack-Style UI/UX
Ejecuta la aplicación con el nuevo panel Validador premium.
"""

import tkinter as tk
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(__file__))

from app.main import GEMOSApplication


def main():
    """Inicia la aplicación con el nuevo diseño."""
    print("=" * 60)
    print("  💎 GEM OS v3.0 - Jack-Style UI/UX Redesign")
    print("=" * 60)
    print("\nCaracterísticas del nuevo diseño:")
    print("  ✓ Glassmorphism con neon accents")
    print("  ✓ Sidebar premium colapsable")
    print("  ✓ Panel Validador rediseñado")
    print("  ✓ KPI Cards con glow effects")
    print("  ✓ Botones modernos con hover neon")
    print("  ✓ Tabla con visual premium")
    print("\n" + "=" * 60)
    print("\n🚀 Iniciando aplicación...\n")
    
    try:
        root = tk.Tk()
        app = GEMOSApplication(root, initial_theme="dark")
        
        print("✅ Aplicación iniciada correctamente")
        print("\n📋 Instrucciones:")
        print("  1. Haz clic en '💎 Validador' en el sidebar")
        print("  2. Explora los nuevos componentes premium")
        print("  3. Prueba los botones con hover effects")
        print("  4. Observa las KPI cards con glassmorphism")
        print("\n💡 Tip: El sidebar es colapsable (botón ⚙️)")
        print("\n" + "=" * 60 + "\n")
        
        root.mainloop()
        
    except Exception as e:
        print(f"\n❌ Error al iniciar: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
