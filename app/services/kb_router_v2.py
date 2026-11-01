"""
kb_router_v2.py — Enrutador de Conocimiento GEM OS v2.0 con Ruteo por Agentes
================================================================================
Extiende KBRouter v1 con integracion FASE 4: ruteo consciente del agente que
procesa, seleccion de modelo OpenRouter segun AGENT_MODEL_MAP, y validacion
de cumplimiento post-insercion.
"""
import json
import re
import sqlite3
import logging
from typing import Dict, List, Optional, Any

from app.services.validator_rules import RulesValidator
from app.services.memory_logger import MemoryLogger

logger = logging.getLogger(__name__)


class KBRouterV2:
    """Enrutador de Conocimiento GEM OS v2 con ruteo por agente."""

    SECTION_TABLE_MAP: Dict[str, str] = {
        "producto":    "product_trends",
        "conversion":  "conversion_formulas",
        "operaciones": "operations_traffic",
        "competencia": "product_trends",
    }

    def __init__(self, db_path: Optional[str] = None,
                 agent_name: str = "gem-backend-core"):
        if db_path is None:
            from app.config.path_manager import PathManager
            db_path = str(PathManager.get_paths()['db'])
        self.db_path = db_path
        from app.database.connection import DatabaseConnection
        self.db_manager = DatabaseConnection(db_path)
        self.agent_name = agent_name
        from app.agents_engine.executor import AGENT_MODEL_MAP
        self.agent_model = AGENT_MODEL_MAP.get(agent_name,
                                                "deepseek/deepseek-chat")
        self.validator = RulesValidator(agent_md_path="agent.md",
                                        db_manager=self.db_manager)
        self.memory = MemoryLogger(db_manager=self.db_manager)
        self.stats: Dict[str, int] = {"inserted": 0, "updated": 0,
                                       "skipped": 0, "errors": 0}
        self.correlation_id: Optional[str] = None

    def _extract_field(self, pattern: str, text: str,
                       default: str = "No especificado") -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else default

    def _extract_all_fields(self, pattern: str, text: str) -> List[str]:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        return [m.strip() if isinstance(m, str) else m[0].strip()
                for m in matches]

    def _extract_int(self, pattern: str, text: str,
                     default: int = 0) -> int:
        val = self._extract_field(pattern, text, str(default))
        try:
            return int(float(val))
        except ValueError:
            return default

    def _extract_float(self, pattern: str, text: str,
                       default: float = 0.0) -> float:
        val = self._extract_field(pattern, text, str(default))
        try:
            return float(val)
        except ValueError:
            return default

    @staticmethod
    def parse_markdown_table(
            table_str: str) -> Optional[List[Dict[str, str]]]:
        lines = [l.strip() for l in table_str.strip().split('\n')
                 if l.strip()]
        if len(lines) < 3:
            return None
        header_line = lines[0]
        sep_line = lines[1]
        if not all(c in '|-: ' for c in sep_line):
            return None
        headers = [h.strip() for h in header_line.split('|') if h.strip()]
        if not headers or len(headers) < 2:
            return None
        result = []
        for data_line in lines[2:]:
            cells = [c.strip() for c in data_line.split('|') if c.strip()]
            if len(cells) >= len(headers):
                result.append(dict(zip(headers, cells[:len(headers)])))
        return result if result else None

    def _analyze_tables_in_section(
            self, section: str) -> Dict[str, Any]:
        tp = re.compile(
            r'^\|.+?\|.+$\n^\|[-: |]+\|$(?:\n^\|.+?\|.+$)*', re.MULTILINE)
        tables = []
        for m in tp.finditer(section):
            p = self.parse_markdown_table(m.group(0))
            if p:
                tables.append({"raw": m.group(0), "data": p})
        metrics: Dict[str, Any] = {}
        cl = [l for l in section.split('\n')
              if any(w in l.lower()
                     for w in ["debilidad", "weakness",
                               "desventaja", "competidor"])]
        if cl:
            metrics["competitor_weaknesses"] = " ".join(cl)
        return {"tables_data": tables, "metrics": metrics}

    def _route_products(self, cursor: sqlite3.Cursor,
                        video_id: str, section: str,
                        table_metrics: Dict) -> None:
        product_name = self._extract_field(
            r"(?:Nombre del producto|Producto|Product Name)[:\s]*([^\n]*)",
            section, "Producto sin nombre")
        niche = self._extract_field(
            r"(?:Categoria|Nicho|Niche|Vertical)[:\s]*([^\n]*)",
            section, "General")
        wow = self._extract_field(
            r"(?:Wow Factor|Factor WOW|Unique|Factor)[:\s]*([^\n]*)",
            section, "No especificado")
        price = self._extract_float(
            r"(?:Precio|Price|Costo|Cost)[:\s]*\$?([0-9.]+)", section, 0.0)
        margin = self._extract_float(
            r"(?:Margen|Margin)[:\s]*([0-9.]+)", section, 0.0)
        cursor.execute("""
            INSERT INTO product_trends
                (video_id, product_name, niche, wow_factor,
                 estimated_price, estimated_margin, agent_name, model_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (video_id, product_name, niche, wow,
              price, margin, self.agent_name, self.agent_model))

    def _route_conversion(self, cursor: sqlite3.Cursor,
                          video_id: str, section: str,
                          table_metrics: Dict) -> None:
        framework = self._extract_field(
            r"(?:Framework|Estructura|Formato)[:\s]*([^\n]*)",
            section, "AIDA")
        apps = self._extract_field(
            r"(?:Apps|Herramientas|Tools|Recommended)[:\s]*([^\n]*)",
            section, "Shopify Native")
        raw_structure = section
        td = table_metrics.get("tables_data")
        if td:
            raw_structure += ("\n\n<!-- TABLAS -->\n" +
                              json.dumps(td, ensure_ascii=False, indent=2))
        persuasion = table_metrics.get("metrics", {}).get(
            "competitor_weaknesses", "Gatillos detectados en pauta")
        cursor.execute("""
            INSERT INTO conversion_formulas
                (video_id, category, framework_name, raw_structure,
                 persuasion_triggers, recommended_apps)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (video_id, "conversion", framework,
              raw_structure, persuasion, apps))

    def _route_traffic(self, cursor: sqlite3.Cursor,
                       video_id: str, section: str,
                       table_metrics: Dict) -> None:
        traffic = self._extract_field(
            r"(?:Fuente de Trafico|Trafico|Traffic|Source)[:\s]*([^\n]*)",
            section, "TikTok/Meta Ads")
        scaling = self._extract_field(
            r"(?:Escalamiento|Estrategia|Scaling|Strategy)[:\s]*([^\n]*)",
            section, "CBO/ABO Testing")
        logistics = self._extract_field(
            r"(?:Logistica|Logistics|Envio|Shipping|Notas)[:\s]*([^\n]*)",
            section, "No especificado")
        weight = self._extract_float(
            r"(?:Peso|Weight)[:\s]*([0-9.]+)", section, 0.0)
        gateways = self._extract_field(
            r"(?:Pasarela|Gateway|Pago|Payment)[:\s]*([^\n]*)",
            section, "Shopify Payments / PayPal")
        notes = logistics
        td = table_metrics.get("tables_data")
        if td:
            notes += ("\n<!-- PRICING -->\n" +
                      json.dumps(td, ensure_ascii=False, indent=2))
        cursor.execute("""
            INSERT INTO operations_traffic
                (video_id, traffic_source, scaling_strategy,
                 logistics_notes, weight_kg, gateways_legal)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (video_id, traffic, scaling, notes, weight, gateways))

    def _route_competition(self, cursor: sqlite3.Cursor,
                           video_id: str, section: str,
                           table_metrics: Dict) -> None:
        weaknesses = self._extract_field(
            r"(?:Debilidad|Weakness|Desventaja)[:\s]*([^\n]*)", section, "")
        if not weaknesses:
            weaknesses = table_metrics.get("metrics", {}).get(
                "competitor_weaknesses", "")
        if weaknesses:
            cursor.execute("""
                UPDATE product_trends
                SET competitor_weaknesses = ?
                WHERE video_id = ?
                  AND (competitor_weaknesses IS NULL
                       OR competitor_weaknesses = 'No especificado')
            """, (weaknesses, video_id))

    def route_and_insert(
            self, video_id: str, sections: Dict[str, str],
            correlation_id: Optional[str] = None) -> bool:
        self.correlation_id = correlation_id or video_id
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                for sname, stext in sections.items():
                    if not stext or len(stext.strip()) < 10:
                        self.stats["skipped"] += 1
                        continue
                    tm = self._analyze_tables_in_section(stext)
                    if sname == "producto":
                        self._route_products(cursor, video_id, stext, tm)
                        self.stats["inserted"] += 1
                    elif sname == "conversion":
                        self._route_conversion(cursor, video_id, stext, tm)
                        self.stats["inserted"] += 1
                    elif sname == "operaciones":
                        self._route_traffic(cursor, video_id, stext, tm)
                        self.stats["inserted"] += 1
                    elif sname == "competencia":
                        self._route_competition(cursor, video_id, stext, tm)
                        self.stats["updated"] += 1
                conn.commit()

            val_output = {
                "agent_id": self.agent_name,
                "status": "success",
                "data": {"video_id": video_id,
                         "sections": list(sections.keys()),
                         "inserted": self.stats["inserted"],
                         "updated": self.stats["updated"]},
                "rules_compliance": {"ok": True},
            }
            validation = self.validator.post_execution_validation(
                self.agent_name, val_output)

            self.memory.log(
                self.agent_name, "kb_route",
                f"KB route para {video_id}: "
                f"{self.stats['inserted']} ins, "
                f"{self.stats['updated']} upd | "
                f"Val: {validation['status']}",
                category="business",
                details={"video_id": video_id,
                         "correlation_id": self.correlation_id,
                         "model_used": self.agent_model,
                         "stats": dict(self.stats),
                         "validation": validation["status"]})
            return True

        except sqlite3.Error as exc:
            logger.error("[KB_ROUTER_V2] Error BD %s: %s", video_id, exc)
            self.stats["errors"] += 1
            self.memory.log_error(
                self.agent_name, f"Error BD ruteando {video_id}: {exc}")
            return False
        except Exception as exc:
            logger.error("[KB_ROUTER_V2] Error %s: %s", video_id, exc)
            self.stats["errors"] += 1
            self.memory.log_error(
                self.agent_name, f"Error ruteando {video_id}: {exc}")
            return False

    def get_stats(self) -> Dict[str, int]:
        return dict(self.stats)

    def get_route_info(self) -> Dict[str, Any]:
        return {"agent_name": self.agent_name,
                "agent_model": self.agent_model,
                "stats": dict(self.stats),
                "correlation_id": self.correlation_id}