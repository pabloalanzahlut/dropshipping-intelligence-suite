"""Fix main.py - ensure proper indentation"""
with open('app/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The issue: _load_panel body is at 8 spaces, _log at 4 spaces
# Need to ensure _log is properly at class level
# Let me check what happened

# Find _log
log_line = None
for i, line in enumerate(lines):
    if line.strip().startswith('def _log('):
        log_line = i
        break

if log_line:
    print(f'_log at line {log_line+1}: {repr(lines[log_line])}')
    print(f'Previous line: {repr(lines[log_line-1])}')
    print(f'Previous 2: {repr(lines[log_line-2])}')

# The issue might be that _load_panel's body was indented but _log wasn't
# Let me check the indentation of all methods
for i, line in enumerate(lines):
    stripped = line.lstrip()
    if stripped.startswith('def ') and not stripped.startswith('def _load_panel'):
        indent = len(line) - len(stripped)
        print(f'Line {i+1}: indent={indent} | {stripped[:50]}')