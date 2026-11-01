"""
test_dashboard_files.py — Verifica sintaxis e imports del Dashboard rediseñado v2.0
"""
import sys
import os
import tkinter as tk

def test_syntax():
    """Verifica que todos los archivos tengan sintaxis Python válida."""
    import ast
    files = [
        "app/ui/themes/design_tokens.py",
        "app/ui/components/animations.py",
        "app/ui/components/cards.py",
        "app/ui/components/base_components.py",
        "app/ui/components/dashboard_panel.py",
    ]
    errors = []
    for path in files:
        fpath = os.path.join(os.path.dirname(__file__), "..", path)
        fpath = os.path.normpath(fpath)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                ast.parse(f.read())
            print(f"  ✅ {path} — Syntax OK")
        except SyntaxError as e:
            errors.append((path, str(e)))
            print(f"  ❌ {path} — {e}")
    return errors

def test_imports():
    """Verifica que los módulos se puedan importar (sin ejecutar UI)."""
    os.environ["DISPLAY"] = ":0"  # Para entornos headless
    modules = [
        "app.ui.themes.design_tokens",
        "app.ui.components.animations",
        "app.ui.components.cards",
        "app.ui.components.base_components",
    ]
    errors = []
    for mod_name in modules:
        try:
            __import__(mod_name, fromlist=[""])
            print(f"  ✅ {mod_name} — Import OK")
        except Exception as e:
            errors.append((mod_name, str(e)))
            print(f"  ❌ {mod_name} — {e}")
    return errors

if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, root)
    print("\n🔍 VERIFICACION DE ARCHIVOS DEL DASHBOARD v2.0")
    print("=" * 55)
    print("\n📄 1. Sintaxis Python:")
    errs = test_syntax()
    print(f"\n📦 2. Imports:")
    errs += test_imports()
    print("\n" + "=" * 55)
    if errs:
        print(f"\n❌ ERRORES ENCONTRADOS: {len(errs)}")
        for mod, err in errs:
            print(f"   - {mod}: {err}")
        sys.exit(1)
    else:
        print("\n✅ TODOS LOS ARCHIVOS VALIDADOS CORRECTAMENTE!")
        sys.exit(0)