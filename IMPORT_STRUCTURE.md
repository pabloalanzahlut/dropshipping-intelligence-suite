# GEM OS Import Structure Reference

## Project Architecture
```
app/
├── main.py                 # Entry point (GEMOSApplication class)
├── core/                   # Business logic cores
│   ├── ollama_startup_engine.py
│   └── ...
├── ui/                     # Desktop UI layer (Tkinter)
│   ├── components/         # Reusable UI components
│   │   ├── console_view.py
│   │   ├── dashboard_panel.py
│   │   ├── financial_validator_panel.py
│   │   ├── youtube_monitor_panel.py
│   │   ├── copywriting_panel.py
│   │   ├── tiktok_panel.py
│   │   ├── governance_panel.py
│   │   ├── ollama_panel.py
│   │   ├── navigation.py
│   │   └── indicators.py
│   ├── layouts/            # Layout managers
│   │   └── dashboard_layout.py
│   └── themes/             # Theme engines
│       ├── dark_theme.py
│       ├── light_theme.py
│       └── design_tokens.py
├── database/               # Data persistence layer
│   ├── connection.py       # DatabaseConnection class
│   └── migrations.py
├── services/               # Business services
│   ├── provider_monitor_engine.py  # ProviderMonitorEngine class
│   ├── openrouter_client.py
│   └── ...
└── agents_engine/          # Agent orchestration
    └── ...
```

## Standard Imports for main.py

### Standard Library
```python
import os                              # Environment variables
import threading                       # Background threads
import tkinter as tk                   # GUI framework
from tkinter import ttk, messagebox    # Widgets & dialogs
from dotenv import load_dotenv         # .env file loading
```

### Internal Layers (Ordered by Dependency)

**1. Themes (Foundation)**
```python
from app.ui.themes import DarkTheme, LightTheme
from app.ui.themes.design_tokens import COLORS
```

**2. Components (Widgets built on themes)**
```python
from app.ui.components import Sidebar, StatusIndicator, ConsoleView
from app.ui.components.dashboard_panel import DashboardPanel
from app.ui.components.financial_validator_panel import FinancialValidatorPanel
from app.ui.components.youtube_monitor_panel import YouTubeMonitorPanel
from app.ui.components.copywriting_panel import CopywritingPanel
from app.ui.components.tiktok_panel import TikTokPanel
from app.ui.components.governance_panel import GovernancePanel
from app.ui.components.ollama_panel import OllamaPanel
```

**3. Data Layer**
```python
from app.database.connection import DatabaseConnection
```

**4. Services (Uses data layer)**
```python
from app.services.provider_monitor_engine import ProviderMonitorEngine
```

## Key Import Rules

### ❌ Wrong
```python
from app.database import DatabaseConnection      # No __init__.py in database/
from app.ui.layouts import DashboardPanel       # Panels are in components/
```

### ✅ Right
```python
from app.database.connection import DatabaseConnection
from app.ui.components.dashboard_panel import DashboardPanel
```

## Module Location Quick Reference

| Class | Import Path |
|-------|-------------|
| `GEMOSApplication` | `app.main` |
| `DarkTheme`, `LightTheme` | `app.ui.themes` |
| `COLORS` | `app.ui.themes.design_tokens` |
| `Sidebar`, `StatusIndicator` | `app.ui.components` |
| `ConsoleView` | `app.ui.components.console_view` |
| `DashboardPanel` | `app.ui.components.dashboard_panel` |
| `FinancialValidatorPanel` | `app.ui.components.financial_validator_panel` |
| `YouTubeMonitorPanel` | `app.ui.components.youtube_monitor_panel` |
| `CopywritingPanel` | `app.ui.components.copywriting_panel` |
| `TikTokPanel` | `app.ui.components.tiktok_panel` |
| `GovernancePanel` | `app.ui.components.governance_panel` |
| `OllamaPanel` | `app.ui.components.ollama_panel` |
| `DatabaseConnection` | `app.database.connection` |
| `ProviderMonitorEngine` | `app.services.provider_monitor_engine` |

## Debugging Import Errors

### Test import resolution
```bash
python -c "from app.main import GEMOSApplication; print('OK')"
```

### Check syntax
```bash
python -m py_compile app/main.py
```

### List module contents
```bash
python -c "import app.ui.components; print(dir(app.ui.components))"
```

### Find a class
```bash
grep -r "class YourClassName" app/
```

---
**Last Updated**: 2026-10-31  
**Maintainer**: GEM OS Team
