#!/usr/bin/env python
"""
verify_ui_fixes.py - Script de verificación de correcciones UI
Valida que los cambios se hayan aplicado correctamente sin ejecutar la GUI completa.
"""

import sys
import ast
from pathlib import Path

def check_file_syntax(filepath):
    """Verifica que un archivo Python tenga sintaxis válida."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        return True, "[OK] Sintaxis valida"
    except SyntaxError as e:
        return False, f"[FAIL] Error de sintaxis: {e}"

def check_method_exists(filepath, class_name, method_name):
    """Verifica que un método exista en una clase."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == method_name:
                        return True, f"[OK] Metodo '{method_name}' encontrado en clase '{class_name}'"
        
        return False, f"[FAIL] Metodo '{method_name}' no encontrado en clase '{class_name}'"
    except Exception as e:
        return False, f"[FAIL] Error al buscar metodo: {e}"

def check_string_in_file(filepath, search_string):
    """Verifica que una cadena específica exista en el archivo."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if search_string in content:
                return True, f"[OK] Cadena encontrada: '{search_string[:50]}...'"
            else:
                return False, f"[FAIL] Cadena no encontrada: '{search_string[:50]}...'"
    except Exception as e:
        return False, f"[FAIL] Error al buscar cadena: {e}"

def main():
    print("=" * 70)
    print("VERIFICACION DE CORRECCIONES UI - GEM OS v3.0")
    print("=" * 70)
    print()
    
    base_path = Path(__file__).parent
    all_passed = True
    
    # Test 1: Verificar sintaxis de archivos modificados
    print("TEST 1: Verificacion de sintaxis")
    print("-" * 70)
    
    files_to_check = [
        "app/main.py",
        "app/ui/components/dashboard_panel_v3.py",
        "app/ui/components/navigation_v2.py"
    ]
    
    for file in files_to_check:
        filepath = base_path / file
        passed, message = check_file_syntax(filepath)
        print(f"  {message} - {file}")
        all_passed = all_passed and passed
    
    print()
    
    # Test 2: Verificar que existan los métodos nuevos
    print()
    print("TEST 2: Verificacion de metodos implementados")
    print("-" * 70)
    
    checks = [
        ("app/main.py", "GEMOSApplication", "_apply_theme_recursive"),
        ("app/ui/components/dashboard_panel_v3.py", "DashboardPanelV3", "_create_button"),
    ]
    
    for filepath, class_name, method_name in checks:
        full_path = base_path / filepath
        passed, message = check_method_exists(full_path, class_name, method_name)
        print(f"  {message}")
        all_passed = all_passed and passed
    
    print()
    
    # Test 3: Verificar cambios específicos en el código
    print()
    print("TEST 3: Verificacion de cambios especificos")
    print("-" * 70)
    
    specific_checks = [
        ("app/main.py", "self.theme_radiobuttons"),
        ("app/ui/components/dashboard_panel_v3.py", "highlightthickness=2"),
        ("app/ui/components/navigation_v2.py", "#00f5ff"),
        ("app/ui/components/navigation_v2.py", "font=(\"Segoe UI\", 22)"),
    ]
    
    for filepath, search_string in specific_checks:
        full_path = base_path / filepath
        passed, message = check_string_in_file(full_path, search_string)
        print(f"  {message}")
        all_passed = all_passed and passed
    
    print()
    print("=" * 70)
    
    if all_passed:
        print("[OK] TODAS LAS VERIFICACIONES PASARON CORRECTAMENTE")
        print("=" * 70)
        return 0
    else:
        print("[FAIL] ALGUNAS VERIFICACIONES FALLARON")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
