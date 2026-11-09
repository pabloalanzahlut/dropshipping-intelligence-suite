"""
N4 - EXPORT KB (Nivel 4: Exportación de Conocimiento)
══════════════════════════════════════════════════════════
Exportador estructurado de la Base de Conocimiento GEM OS.
Consolida datos de producto, conversión y tráfico en un
manual táctico Markdown + HTML interactivo.
Cumple con: FASE 3 — Capa de Visualización e Infraestructura de Acceso
══════════════════════════════════════════════════════════
"""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from app.database.connection import DatabaseConnection
from app.config.path_manager import PathManager

# ── Constantes usando PathManager ──────────────────────────────────
_GEM_PATHS = PathManager.get_paths()
DB_PATH = str(_GEM_PATHS['db'])
OUTPUT_PATH = str(_GEM_PATHS['context'] / "manual_tactico_consolidado.md")
HTML_OUTPUT_PATH = str(_GEM_PATHS['context'] / "manual_tactico_consolidado.html")

SECTION_HEADINGS = {
    "productos": "1. Datos de Producto y Tendencias",
    "conversion": "2. Estructuras de Conversión y Copy",
    "trafico": "3. Logística, Tráfico y Legal",
}


# ── Helpers de extracción ───────────────────────────────────────────────────

def _get_db_manager() -> DatabaseConnection:
    return DatabaseConnection(DB_PATH)


def _fetch_product_trends() -> List[Dict[str, Any]]:
    """Extrae todos los registros de product_trends con metadatos del video fuente."""
    db = _get_db_manager()
    with db.get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.*, v.title AS video_title, v.channel_name, v.platform
            FROM product_trends t
            LEFT JOIN video_sources v ON t.video_id = v.video_id
            ORDER BY t.validated_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]


def _fetch_conversion_formulas() -> List[Dict[str, Any]]:
    """Extrae todas las fórmulas de conversión con metadatos."""
    db = _get_db_manager()
    with db.get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT f.*, v.title AS video_title, v.channel_name
            FROM conversion_formulas f
            LEFT JOIN video_sources v ON f.video_id = v.video_id
            ORDER BY f.id DESC
        """)
        return [dict(row) for row in cursor.fetchall()]


def _fetch_operations_traffic() -> List[Dict[str, Any]]:
    """Extrae todos los registros de operaciones y tráfico."""
    db = _get_db_manager()
    with db.get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.*, v.title AS video_title, v.channel_name
            FROM operations_traffic o
            LEFT JOIN video_sources v ON o.video_id = v.video_id
            ORDER BY o.id DESC
        """)
        return [dict(row) for row in cursor.fetchall()]


# ── Generación Markdown ─────────────────────────────────────────────────────

def _build_productos_section(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "*(No hay datos de productos indexados aún)*\n\n"

    lines = [
        f"## {SECTION_HEADINGS['productos']}\n",
        f"Total de productos analizados: **{len(rows)}**\n",
        "---\n",
    ]

    for i, row in enumerate(rows, 1):
        lines.append(f"### Producto #{i}: {row.get('product_name', 'Sin nombre')}")
        lines.append(f"- **Nicho:** {row.get('niche', 'No especificado')}")
        lines.append(f"- **Wow Factor:** {row.get('wow_factor', 'No disponible')}")
        lines.append(f"- **Multiplicador de Margen:** {row.get('estimated_margin', 3.0)}x")
        lines.append(f"- **Canal Fuente:** {row.get('channel_name', 'Desconocido')}")
        lines.append(f"- **Video:** {row.get('video_title', 'No disponible')}")
        lines.append(f"- **Validado el:** {row.get('validated_at', '—')}")
        weaknesses = row.get('competitor_weaknesses', '')
        if weaknesses and len(weaknesses) > 50:
            lines.append(f"- **Debilidades de Competidores:**\n  ```\n  {weaknesses[:500]}\n  ```")
        lines.append("")

    return "\n".join(lines)


def _build_conversion_section(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "*(No hay estructuras de conversión indexadas aún)*\n\n"

    lines = [
        f"## {SECTION_HEADINGS['conversion']}\n",
        f"Total de estructuras de conversión: **{len(rows)}**\n",
        "---\n",
    ]

    for i, row in enumerate(rows, 1):
        lines.append(f"### Framework #{i}: {row.get('framework_name', 'AIDA')} — {row.get('category', 'General')}")
        lines.append(f"- **Categoría:** {row.get('category', 'No especificada')}")
        lines.append(f"- **Framework:** {row.get('framework_name', 'AIDA')}")
        lines.append(f"- **Gatillos Persuasivos:** {row.get('persuasion_triggers', 'No especificados')}")
        lines.append(f"- **Apps Recomendadas:** {row.get('recommended_apps', 'No especificadas')}")
        lines.append(f"- **Canal Fuente:** {row.get('channel_name', 'Desconocido')}")
        lines.append(f"- **Video:** {row.get('video_title', 'No disponible')}")
        raw = row.get('raw_structure', '')
        if raw:
            lines.append(f"- **Estructura Raw:**\n  ```markdown\n  {raw[:800]}\n  ```")
        lines.append("")

    return "\n".join(lines)


def _build_trafico_section(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "*(No hay datos de operaciones y tráfico indexados aún)*\n\n"

    lines = [
        f"## {SECTION_HEADINGS['trafico']}\n",
        f"Total de registros de operaciones: **{len(rows)}**\n",
        "---\n",
    ]

    for i, row in enumerate(rows, 1):
        lines.append(f"### Operación #{i}: {row.get('traffic_source', 'Fuente no especificada')}")
        lines.append(f"- **Fuente de Tráfico:** {row.get('traffic_source', 'No especificada')}")
        lines.append(f"- **Estrategia de Escalamiento:** {row.get('scaling_strategy', 'No especificada')}")
        lines.append(f"- **Notas Logísticas:** {row.get('logistics_notes', 'No disponibles')}")
        lines.append(f"- **Peso (kg):** {row.get('weight_kg', 0.0)}")
        lines.append(f"- **Gateways / Legal:** {row.get('gateways_legal', 'No especificado')}")
        lines.append(f"- **Canal Fuente:** {row.get('channel_name', 'Desconocido')}")
        lines.append(f"- **Video:** {row.get('video_title', 'No disponible')}")
        lines.append("")

    return "\n".join(lines)


# ── Exportación principal ───────────────────────────────────────────────────

def export_to_markdown(
    db_path: str = DB_PATH,
    output_path: str = OUTPUT_PATH,
) -> str:
    """
    Extrae toda la KB y genera el manual táctico consolidado en Markdown.
    Retorna la ruta absoluta del archivo generado.
    """
    print(f"📦 Exportando Knowledge Base desde {db_path}...")

    trends = _fetch_product_trends()
    formulas = _fetch_conversion_formulas()
    traffic = _fetch_operations_traffic()

    total_records = len(trends) + len(formulas) + len(traffic)
    print(f"   → {len(trends)} productos, {len(formulas)} fórmulas, {len(traffic)} operaciones")

    sections = [
        "# Manual Táctico Consolidado — GEM OS\n",
        f"**Generado el:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"**Total de registros exportados:** {total_records}\n",
        f"**Fuente:** Base de Conocimiento local (SQLite)\n",
        "---\n",
        _build_productos_section(trends),
        "---\n",
        _build_conversion_section(formulas),
        "---\n",
        _build_trafico_section(traffic),
        "---\n",
        "*Documento generado automáticamente por GEM OS Export KB.*\n",
    ]

    content = "\n".join(sections)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")

    print(f"✅ Manual táctico generado: {output.resolve()}")
    return str(output.resolve())


def export_to_html(
    md_path: str = OUTPUT_PATH,
    html_path: str = HTML_OUTPUT_PATH,
) -> str:
    """
    Convierte el Markdown del manual táctico a HTML interactivo.
    Retorna la ruta absoluta del archivo HTML generado.
    """
    try:
        import markdown
    except ImportError:
        print("⚠️  La librería 'markdown' no está instalada. Ejecuta: pip install markdown")
        return ""

    md_file = Path(md_path)
    if not md_file.exists():
        print(f"⚠️  No se encontró {md_path}. Ejecuta primero export_to_markdown().")
        return ""

    md_content = md_file.read_text(encoding="utf-8")

    html_body = markdown.markdown(
        md_content,
        extensions=["fenced_code", "codehilite", "tables", "nl2br"],
    )

    html_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Manual Táctico Consolidado — GEM OS</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    colors: {{
                        gem: {{ 900: '#0a0e1a', 800: '#111827', 700: '#1f2937',
                               600: '#374151', 500: '#6b7280', 400: '#9ca3af',
                               300: '#d1d5db', 200: '#e5e7eb', 100: '#f3f4f6',
                               accent: '#22d3ee' }}
                    }}
                }}
            }}
        }}
    </script>
    <style>
        body {{ font-family: 'Inter', system-ui, -apple-system, sans-serif; }}
        pre {{ background: #1f2937; padding: 1rem; border-radius: 0.5rem; overflow-x: auto; }}
        code {{ font-size: 0.875rem; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #374151; padding: 0.5rem 0.75rem; text-align: left; }}
        th {{ background: #1f2937; color: #22d3ee; }}
        h2 {{ color: #22d3ee; border-bottom: 1px solid #374151; padding-bottom: 0.5rem; margin-top: 2rem; }}
        h3 {{ color: #e5e7eb; margin-top: 1.5rem; }}
        a {{ color: #22d3ee; }}
    </style>
</head>
<body class="bg-gem-900 text-gem-300 min-h-screen">
    <div class="max-w-4xl mx-auto px-4 py-8">
        <header class="mb-8">
            <h1 class="text-2xl font-bold text-white">📘 Manual Táctico Consolidado</h1>
            <p class="text-gem-400 text-sm">GEM OS · Dropshipping Intelligence Suite</p>
        </header>
        <div class="prose prose-invert max-w-none">
            {html_body}
        </div>
        <footer class="mt-12 pt-4 border-t border-gem-700 text-xs text-gem-500">
            Generado automáticamente por GEM OS Export KB · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </footer>
    </div>
</body>
</html>"""

    output = Path(html_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html_template, encoding="utf-8")

    print(f"✅ Manual HTML generado: {output.resolve()}")
    return str(output.resolve())


# ── CLI ─────────────────────────────────────────────────────────────────────

def run_export_all(db_path: str = DB_PATH) -> Dict[str, str]:
    """Ejecuta exportación completa: Markdown + HTML."""
    md = export_to_markdown(db_path=db_path)
    html = export_to_html()
    return {"markdown": md, "html": html}


if __name__ == "__main__":
    print("=" * 60)
    print("  GEM OS — Exportador de Base de Conocimiento")
    print("=" * 60)
    results = run_export_all()
    print("\n📁 Archivos generados:")
    for fmt, path in results.items():
        if path:
            print(f"   • {fmt.upper()}: {path}")
    print("\n✅ Exportación completada.")