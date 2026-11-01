---
name: kb-export-system
description: Sistema avanzado de exportación de Base de Conocimiento con filtros, plantillas, scheduler, historial e incremental.
---

# 📤 KB EXPORT SYSTEM

## Resumen de Funcionalidades

| # | Funcionalidad | Estado | Archivo |
|---|-------------|--------|---------|
| 1 | CLI `export_kb()` función | ✅ Completo | `app/services/kb_export_service.py` |
| 2 | Filtros pre-export (category, date, incremental) | ✅ Completo | `app/services/kb_export_service.py` |
| 3 | Plantillas de export (full/minimal/index_only) | ✅ Completo | `app/services/kb_export_service.py` |
| 4 | Compresión ZIP | ✅ Completo | `app/services/kb_export_service.py` |
| 5 | Historial de exportaciones | ✅ Completo | `app/services/kb_export_service.py` |
| 6 | Exportación incremental | ✅ Completo | `app/services/kb_export_service.py` |
| 7 | Preview antes de export | ✅ Completo | `app/services/kb_export_service.py` |
| 8 | Scheduler KB (daily/weekly/monthly) | ✅ Completo | `app/services/kb_export_scheduler.py` |
| 9 | Panel Export Settings UI | ✅ Completo | `app/ui/tabs/settings_tab.py` |
| 10 | Notificaciones de export | ✅ Completo | `app/services/kb_export_service.py` |

## Uso del CLI

```python
from app.services.kb_export_service import export_kb

# Export básico
result = export_kb(format="html", template="full")

# Export con filtros
result = export_kb(
    format="html",
    template="full",
    filters={"categories": ["AI", "Python"], "days_back": 7},
    compression=True
)

# Export incremental
result = export_kb(
    format="html",
    filters={"last_export_id": 123}
)
```

### CLI por línea de comandos

```bash
python -m app.services.kb_export_service --format html --template full --compress
python -m app.services.kb_export_service --incremental --categories AI Python
python -m app.services.kb_export_service --days 30
```

## Configuración en settings.json

```json
{
  "export": {
    "default_format": "html",
    "template": "full",
    "compression": false,
    "enable_incremental": true,
    "max_entries_per_file": 500,
    "schedule_enabled": false,
    "schedule_frequency": "daily",
    "schedule_hour": 2
  }
}
```

## APIs Principales

### KBExportService

```python
from app.services.kb_export_service import KBExportService, ExportFilters, ExportConfig

service = KBExportService()

# Preview
preview = service.preview_export(filters=ExportFilters(categories=["AI"]))

# Export
result = service.export(filters=ExportFilters(days_back=7), format="html", template="full")

# Historial
history = service.get_export_history(limit=10)
```

### KBExportScheduler

```python
from app.services.kb_export_scheduler import KBExportScheduler

scheduler = KBExportScheduler(export_service=service)
scheduler.configure(
    enabled=True,
    frequency="daily",
    hour=2,
    minute=0,
    template="full",
    compression=True,
    incremental=False
)
scheduler.start()
```

## Plantillas Disponibles

- **full**: Contenido completo con TOC y todos los detalles
- **minimal**: Solo índice sin contenido (solo títulos)
- **index_only**: Solo links/hipervínculos sin contenido

## Filtros Disponibles

- **categories**: Lista de categorías a incluir
- **date_from/date_to**: Rango de fechas
- **days_back**: Últimos N días
- **search_query**: Búsqueda en contenido
- **last_export_id**: Para exportación incremental

## Historial

Las exportaciones se registran en la tabla `export_history` con:
- export_date, format, template, entries_count
- file_size_bytes, file_path
- export_type (full/incremental/filtered)
- filters_applied, status