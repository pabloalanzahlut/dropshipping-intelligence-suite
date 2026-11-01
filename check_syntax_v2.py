"""Syntax checker for all new UI files."""
import ast
import os

os.chdir("h:\\dropshipping_intelligence_suite")

files = [
    "app/ui/themes/design_tokens.py",
    "app/ui/themes/base_theme.py", 
    "app/ui/themes/dark_theme.py",
    "app/ui/themes/light_theme.py",
    "app/ui/themes/__init__.py",
    "app/ui/components/base_components.py",
    "app/ui/components/data_table.py",
    "app/ui/components/navigation.py",
    "app/ui/components/buttons.py",
    "app/ui/components/inputs.py",
    "app/ui/components/cards.py",
    "app/ui/components/indicators.py",
    "app/ui/components/__init__.py",
    "app/ui/layouts/dashboard_layout.py",
    "app/ui/layouts/__init__.py",
    "app/ui/layouts/panel_layout.py",
]

for f in files:
    if not os.path.exists(f):
        print(f"❌ NOT FOUND: {f}")
        continue
    try:
        with open(f, "r", encoding="utf-8") as fh:
            ast.parse(fh.read())
        print(f"✅ OK: {f}")
    except SyntaxError as e:
        print(f"❌ SYNTAX ERROR: {f}: {e}")
    except Exception as e:
        print(f"❌ ERROR: {f}: {e}")