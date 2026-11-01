"""Quick syntax checker for FASE 3 files."""
import ast, sys, os

files = [
    "app/ui/themes/base_theme.py",
    "app/ui/themes/dark_theme.py",
    "app/ui/themes/light_theme.py",
    "app/ui/themes/__init__.py",
    "app/ui/__init__.py",
    "app/ui/components/__init__.py",
    "app/ui/components/progress_bar.py",
    "app/ui/components/console_view.py",
    "app/services/memory_logger.py",
    "app/main.py",
]

os.chdir(os.path.dirname(os.path.abspath(__file__)))
errors = 0
for f in files:
    try:
        with open(f, encoding="utf-8") as fh:
            ast.parse(fh.read())
        print(f"  ✅ {f}")
    except SyntaxError as e:
        print(f"  ❌ {f}: {e}")
        errors += 1

print(f"\n{'='*40}")
if errors:
    print(f"❌ {errors} archivo(s) con errores de sintaxis")
else:
    print(f"✅ Todos los archivos pasaron la verificación de sintaxis")
sys.exit(errors)