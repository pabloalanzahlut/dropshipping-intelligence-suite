"""
Export Pack — Exportación de Datos a CSV y PDF
================================================
GEM OS Suite — Permite exportar productos validados, copys y guiones.
"""

import csv
import os
import logging
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def export_to_csv(data: List[Dict], filepath: str, fieldnames: Optional[List[str]] = None) -> str:
    """
    Exporta una lista de diccionarios a un archivo CSV.

    Args:
        data: Lista de diccionarios con los datos
        filepath: Ruta del archivo CSV a crear
        fieldnames: Lista de campos a incluir (si es None, usa las keys del primer dict)

    Returns:
        Ruta del archivo creado
    """
    if not data:
        raise ValueError("No hay datos para exportar")

    fieldnames = fieldnames or list(data[0].keys())

    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            # Filtrar solo los campos solicitados
            filtered = {k: row.get(k, "") for k in fieldnames}
            writer.writerow(filtered)

    logger.info(f"[EXPORT] CSV exportado: {path} ({len(data)} filas)")
    return str(path)


def export_to_html(data: List[Dict], filepath: str, title: str = "GEM OS Export") -> str:
    """
    Exporta datos a HTML formateado para visualización en navegador.

    Args:
        data: Lista de diccionarios
        filepath: Ruta del archivo HTML
        title: Título de la página

    Returns:
        Ruta del archivo creado
    """
    if not data:
        raise ValueError("No hay datos para exportar")

    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(data[0].keys())

    html_rows = []
    for row in data:
        html_rows.append("<tr>")
        for key in fieldnames:
            val = str(row.get(key, "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html_rows.append(f"<td>{val}</td>")
        html_rows.append("</tr>")

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; }}
h1 {{ color: #2E7D32; }}
table {{ border-collapse: collapse; width: 100%; }}
th {{ background: #4CAF50; color: white; padding: 8px; text-align: left; }}
td {{ padding: 6px; border-bottom: 1px solid #ddd; }}
tr:hover {{ background: #f5f5f5; }}
.footer {{ margin-top: 20px; color: #666; font-size: 12px; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p>Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<p>Registros: {len(data)}</p>
<table>
<thead><tr>{"".join(f'<th>{k}</th>' for k in fieldnames)}</tr></thead>
<tbody>{"".join(html_rows)}</tbody>
</table>
<div class="footer">GEM OS Dropshipping Intelligence Suite v2.0</div>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"[EXPORT] HTML exportado: {path} ({len(data)} filas)")
    return str(path)


def export_copy_to_txt(copy_data: Dict, filepath: str) -> str:
    """
    Exporta un copy a formato TXT legible.

    Args:
        copy_data: Dict con datos del copy
        filepath: Ruta del archivo

    Returns:
        Ruta del archivo creado
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    scores = copy_data.get("scores_aida", {})
    content = f"""========================================
  GEM OS - Copy AIDA
  Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
========================================

TITULO: {copy_data.get('titulo', '')}

DESCRIPCION:
{copy_data.get('descripcion', '')}

----------------------------------------
SCORES AIDA:
  Attention: {scores.get('attention', 0)}%
  Interest:  {scores.get('interest', 0)}%
  Decision:  {scores.get('decision', 0)}%
  Action:    {scores.get('action', 0)}%
  Promedio:  {scores.get('promedio', 0)}%
----------------------------------------
Superlativos: {'No' if copy_data.get('sin_superlativos', False) else 'Si'}
Fuente: {copy_data.get('contexto_fuente', 'template')}
========================================
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"[EXPORT] TXT exportado: {path}")
    return str(path)


def export_guion_to_txt(guion_data: Dict, filepath: str) -> str:
    """
    Exporta un guion TikTok a formato TXT.

    Args:
        guion_data: Dict con datos del guion
        filepath: Ruta del archivo

    Returns:
        Ruta del archivo creado
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    content = f"""========================================
  GEM OS - Guion TikTok
  Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
========================================

TITULO: {guion_data.get('titulo', '')}

HOOK:
{guion_data.get('hook', '')}

CUERPO:
{guion_data.get('cuerpo', '')}

CTA:
{guion_data.get('cta', '')}

----------------------------------------
Patron Hook: {guion_data.get('patron_hook', '')}
Duracion: {guion_data.get('duracion_segundos', 0)} segundos
========================================
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"[EXPORT] Guion TXT exportado: {path}")
    return str(path)