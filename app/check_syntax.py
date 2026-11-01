import ast, sys
try:
    with open(r'h:\dropshipping_intelligence_suite\app\ui\components\governance_panel.py', encoding='utf-8') as f:
        ast.parse(f.read())
    print('SYNTAX OK')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e}')
    sys.exit(1)