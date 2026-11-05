"""
kb_router.py — Enrutador de Conocimiento GEM OS con Segmentación Mejorada
=========================================================================
Analiza el Markdown estructurado generado por transcript cleaners,
extrae variables clave, parsea tablas Markdown e inserta en las tablas
del esquema relacional (product_trends, conversion_formulas,
operations_traffic).

Complejidad:
  Temporal (ruteo): O(s * t) donde s = secciones, t = tablas en cada sección
  Temporal (parseo tabla): O(c * r) donde c = celdas, r = filas
  Espacial: O(n) para tablas parseadas en memoria

Referencias:
  [PEP 8]     snake_case, imports en 3 bloques
  [PEP 391]   logging.getLogger(__name__) para errores
  [PEP 484]   Type hints en todas las funciones
  [PEP 557]   Dict tipados para estructuras de tablas
  [SQLite Docs] INSERT OR IGNORE, queries parametrizadas
  [CWE-89]   Queries parametrizadas con ? — prohibido f-strings
  [Big-O]    Análisis de complejidad en métodos públicos
  [SOLID-SRP] Cada _route_* maneja una tabla específica

Mejoras v2 (FASE 2):
  - Parseo de tablas Markdown → dict/JSON
  - Detección de tablas de precios, especificaciones, competencia
  - Enrutador específico para sección de competencia
  - Patrones regex mejorados con MULTILINE
  - Extracción de peso desde texto/tablas
  - Manejo de errores con logging y retorno bool
"""

import json
import re
import sqlite3
from typing import Dict, List, Optional, Tuple


class KBRouter:
    """
    Enrutador de Conocimiento GEM OS — Segmentación Mejorada.
    Parsea Markdown estructurado con detección de tablas.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            from app.config.path_manager import PathManager
            db_path = str(PathManager.get_paths()['db'])
        self.db_path = db_path
        from app.database.connection import DatabaseConnection
        self.db_manager = DatabaseConnection(db_path)

    # ══════════════════════════════════════════════════════════════════════
    # Extracción de campos vía regex
    # ══════════════════════════════════════════════════════════════════════

    def _extract_field(self, pattern: str, text: str, default: str = "No especificado") -> str:
        """Extrae el primer valor capturado por regex dentro de un bloque."""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else default

    def _extract_labeled(self, labels: str, text: str,
                         default: str = "No especificado") -> str:
        """
        Extrae el valor de un campo "Etiqueta: valor".

        Exige inicio de línea y dos puntos: sin eso, una etiqueta como
        "Producto" matchea dentro del propio título de sección
        ("### 1. Datos de Producto y Tendencias") y guarda el fragmento
        sobrante en lugar del dato.
        """
        pattern = (
            rf"^[\s\-\*>]*(?:\*\*|__)?\s*(?:{labels})\s*(?:\*\*|__)?\s*:\s*(.+)$"
        )
        valor = self._extract_field(pattern, text, "")
        valor = re.sub(r"[*_`]", "", valor).strip()
        if not valor or valor.lower() in ("no especificado", "n/a", "-", "none"):
            return default
        return valor

    def _extract_all_fields(self, pattern: str, text: str) -> List[str]:
        """Extrae todas las ocurrencias de un patrón."""
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        return [m.strip() if isinstance(m, str) else m[0].strip() for m in matches]

    def _extract_int(self, pattern: str, text: str, default: int = 0) -> int:
        val = self._extract_field(pattern, text, str(default))
        try:
            return int(float(val))
        except ValueError:
            return default

    def _extract_float(self, pattern: str, text: str, default: float = 0.0) -> float:
        val = self._extract_field(pattern, text, str(default))
        try:
            return float(val)
        except ValueError:
            return default

    # ══════════════════════════════════════════════════════════════════════
    # Parseo de Tablas Markdown → Dict / JSON
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def parse_markdown_table(table_text: str) -> Optional[Dict]:
        """
        Convierte una tabla Markdown en un diccionario estructurado.

        Retorna:
            { "headers": [...], "rows": [{...}, ...], "row_count": N, "raw": "..." }
        """
        lines = [line.strip() for line in table_text.strip().split("\n") if line.strip()]
        if len(lines) < 2:
            return None

        data_start = 2 if len(lines) > 1 and re.match(r"^[\s\|:\-]+$", lines[1]) else 1

        headers = [
            re.sub(r"\*{1,2}(.*?)\*{1,2}", r"\1", h).strip()
            for h in lines[0].split("|")[1:-1]
        ]
        if not headers:
            return None

        rows = []
        for line in lines[data_start:]:
            if re.match(r"^[\s\|:\-]+$", line):
                continue
            cells = line.split("|")[1:-1]
            if len(cells) != len(headers):
                continue
            row = {}
            for i, cell in enumerate(cells):
                clean = re.sub(r"\*{1,2}(.*?)\*{1,2}", r"\1", cell).strip()
                clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean)
                row[headers[i]] = clean
            rows.append(row)

        if not rows:
            return None

        return {
            "headers": headers,
            "rows": rows,
            "row_count": len(rows),
            "raw": table_text.strip(),
        }

    @staticmethod
    def find_tables_in_markdown(markdown_text: str) -> List[Dict]:
        """
        Encuentra todas las tablas Markdown en un texto.

        Retorna lista con: {table, context, position}.
        """
        tables = []
        pattern = re.compile(
            r"(\|.*\|[\s]*\n\|[\s:.\-]+\|[\s]*\n(?:\|.*\|[\s]*\n?)+)",
            re.MULTILINE,
        )
        for match in pattern.finditer(markdown_text):
            raw = match.group(1)
            parsed = KBRouter.parse_markdown_table(raw)
            if parsed:
                start = max(0, match.start() - 200)
                context = markdown_text[start:match.start()].strip()
                tables.append({
                    "table": parsed,
                    "context": context,
                    "position": match.start(),
                })
        return tables

    def _extract_table_metrics(self, section: str) -> Dict:
        """
        Extrae datos tabulares de la sección y los convierte en métricas
        estructuradas para enriquecer los inserts en DB.
        """
        tables = self.find_tables_in_markdown(section)
        result = {"found_tables": len(tables), "tables_data": [], "metrics": {}}

        for t in tables:
            info = t["table"]
            context_lower = t["context"].lower()
            table_type = "generic"

            if any(w in context_lower for w in ["precio", "price", "costo", "cost"]):
                table_type = "pricing"
                for row in info["rows"]:
                    for header in info["headers"]:
                        h_lower = header.lower()
                        if "precio" in h_lower or "price" in h_lower or "$" in h_lower:
                            try:
                                val = float(re.sub(r"[^\d.]", "", row[header]))
                                result["metrics"]["precio_min"] = min(
                                    result["metrics"].get("precio_min", float("inf")), val
                                )
                                result["metrics"]["precio_max"] = max(
                                    result["metrics"].get("precio_max", float("-inf")), val
                                )
                            except (ValueError, KeyError):
                                pass

            elif any(w in context_lower for w in ["especificación", "spec", "característica"]):
                table_type = "specs"

            elif any(w in context_lower for w in ["competencia", "competitor", "comparación", "vs"]):
                table_type = "competition"
                weaknesses = []
                for row in info["rows"]:
                    for header in info["headers"]:
                        if any(w in header.lower() for w in ["debili", "weak", "contra"]):
                            weaknesses.append(row[header])
                if weaknesses:
                    result["metrics"]["competitor_weaknesses"] = "; ".join(weaknesses)

            info["type"] = table_type
            result["tables_data"].append(info)

        return result

# ══════════════════════════════════════════════════════════════════════
    # Pipeline Principal de Enrutamiento
    # ══════════════════════════════════════════════════════════════════════

    def route_and_insert(
        self,
        video_id: str,
        title: str,
        creator: str,
        content_hash: str,
        clean_markdown: str,
    ) -> bool:
        """
        Modo de replicación KDP+: Parsea Markdown estructurado e inserta
        en las tablas del esquema GEM OS.

        Mejoras v2:
          - Parsea tablas Markdown dentro de cada sección
          - Extrae métricas de tablas de precios/especificaciones
          - Inserta tablas como JSON en campos raw_structure
          - Manejo de errores con logging
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # 1. Registrar o ignorar la fuente maestra
                cursor.execute("""
                    INSERT OR IGNORE INTO video_sources
                        (video_id, platform, title, channel_name, content_hash)
                    VALUES (?, 'youtube', ?, ?, ?)
                """, (video_id, title, creator, content_hash))

                # 2. Segmentación semántica por bloques KDP Style
                sections = clean_markdown.split("### ")

                for section in sections:
                    table_metrics = self._extract_table_metrics(section)

                    if "1. Datos de Producto" in section:
                        self._route_product(cursor, video_id, section, table_metrics)

                    elif "2. Estructuras de Conversión" in section:
                        self._route_conversion(cursor, video_id, section, table_metrics)

                    elif "3. Logística, Tráfico y Legal" in section:
                        self._route_traffic(cursor, video_id, section, table_metrics)

                    elif any(kw in section for kw in ["4.", "Competencia", "Competition"]):
                        self._route_competition(cursor, video_id, section, table_metrics)

                conn.commit()
                return True

        except Exception as exc:
            import logging
            logger = logging.getLogger(__name__)
            logger.error("[KB_ROUTER] Error en route_and_insert para %s: %s", video_id, exc)
            return False

    # ══════════════════════════════════════════════════════════════════════
    # Enrutadores específicos por sección
    # ══════════════════════════════════════════════════════════════════════

    def _route_product(
        self,
        cursor: sqlite3.Cursor,
        video_id: str,
        section: str,
        table_metrics: Dict,
    ) -> None:
        """Inserta en product_trends extrayendo datos del bloque producto."""
        product_name = self._extract_labeled(
            r"Producto|Nombre|Product", section, "Producto Extraído por IA"
        )
        niche = self._extract_labeled(
            r"Nicho|Niche", section, "Dropshipping"
        )
        wow_factor = self._extract_labeled(
            r"Wow Factor|Factor WOW?|Unique", section, "Ver transcripción"
        )
        margin_str = self._extract_field(
            r"^[\s\-\*>]*(?:\*\*|__)?\s*(?:Margen|Multiplicador|Margin|Multiplier)"
            r"(?:\*\*|__)?\s*:\s*[^\d]*([0-9]+(?:[.,][0-9]+)?)",
            section, "3.0"
        ).replace(",", ".")
        try:
            estimated_margin = float(margin_str)
        except ValueError:
            estimated_margin = 3.0

        # Enriquecer con tablas detectadas como JSON
        competitor_weaknesses = section
        if table_metrics.get("tables_data"):
            competitor_weaknesses = (
                section
                + "\n\n<!-- TABLAS DETECTADAS -->\n"
                + json.dumps(table_metrics["tables_data"], ensure_ascii=False, indent=2)
            )

        cursor.execute("""
            INSERT INTO product_trends
                (video_id, product_name, niche, wow_factor,
                 estimated_margin, competitor_weaknesses)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (video_id, product_name, niche, wow_factor,
              estimated_margin, competitor_weaknesses))

    def _route_conversion(
        self,
        cursor: sqlite3.Cursor,
        video_id: str,
        section: str,
        table_metrics: Dict,
    ) -> None:
        """Inserta en conversion_formulas."""
        category = self._extract_field(
            r"(?:Categoría|Tipo|Category|Type)[:\s]*([^\n]*)",
            section, "landing_page"
        )
        framework = self._extract_field(
            r"(?:Framework|Estructura|Structure)[:\s]*([^\n]*)",
            section, "AIDA"
        )
        apps = self._extract_field(
            r"(?:Apps|Herramientas|Tools|Recommended)[:\s]*([^\n]*)",
            section, "Shopify Native"
        )

        raw_structure = section
        if table_metrics.get("tables_data"):
            raw_structure = (
                section
                + "\n\n<!-- ESTRUCTURAS TABULARES -->\n"
                + json.dumps(table_metrics["tables_data"], ensure_ascii=False, indent=2)
            )

        persuasion = table_metrics.get("metrics", {}).get(
            "competitor_weaknesses", "Gatillos detectados en pauta"
        )

        cursor.execute("""
            INSERT INTO conversion_formulas
                (video_id, category, framework_name, raw_structure,
                 persuasion_triggers, recommended_apps)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (video_id, category, framework, raw_structure, persuasion, apps))

    def _route_traffic(
        self,
        cursor: sqlite3.Cursor,
        video_id: str,
        section: str,
        table_metrics: Dict,
    ) -> None:
        """Inserta en operations_traffic."""
        traffic_source = self._extract_field(
            r"(?:Fuente de Tráfico|Tráfico|Traffic|Source)[:\s]*([^\n]*)",
            section, "TikTok/Meta Ads"
        )
        scaling = self._extract_field(
            r"(?:Escalamiento|Estrategia|Scaling|Strategy)[:\s]*([^\n]*)",
            section, "CBO/ABO Testing"
        )
        logistics = self._extract_field(
            r"(?:Logística|Logistics|Envío|Shipping|Notas)[:\s]*([^\n]*)",
            section, "No especificado"
        )
        weight = self._extract_float(
            r"(?:Peso|Weight)[:\s]*([0-9.]+)", section, 0.0
        )
        gateways = self._extract_field(
            r"(?:Pasarela|Gateway|Pago|Payment)[:\s]*([^\n]*)",
            section, "Shopify Payments / PayPal"
        )

        logistics_notes = logistics
        if table_metrics.get("tables_data"):
            pricing = [t for t in table_metrics["tables_data"] if t.get("type") == "pricing"]
            if pricing:
                logistics_notes += (
                    "\n<!-- PRICING -->\n" + json.dumps(pricing, ensure_ascii=False, indent=2)
                )

        cursor.execute("""
            INSERT INTO operations_traffic
                (video_id, traffic_source, scaling_strategy,
                 logistics_notes, weight_kg, gateways_legal)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (video_id, traffic_source, scaling, logistics_notes, weight, gateways))

    def _route_competition(
        self,
        cursor: sqlite3.Cursor,
        video_id: str,
        section: str,
        table_metrics: Dict,
    ) -> None:
        """Actualiza datos de competencia en product_trends."""
        weaknesses = self._extract_field(
            r"(?:Debilidad|Weakness|Desventaja)[:\s]*([^\n]*)",
            section, ""
        )
        if not weaknesses and table_metrics.get("metrics", {}).get("competitor_weaknesses"):
            weaknesses = table_metrics["metrics"]["competitor_weaknesses"]

        if weaknesses:
            cursor.execute("""
                UPDATE product_trends
                SET competitor_weaknesses = ?
                WHERE video_id = ?
                  AND (competitor_weaknesses IS NULL
                       OR competitor_weaknesses = 'No especificado')
            """, (weaknesses, video_id))