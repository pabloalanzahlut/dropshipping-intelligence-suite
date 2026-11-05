"""
kb_index_sync.py — Sincronizador SQLite → kb_index.json
=========================================================
Genera y mantiene actualizado ai_workspace/memory/kb_index.json
como snapshot exportado del estado real de la KB en SQLite.

Decisión arquitectural (GEM OS v3.7):
  - SQLite es la ÚNICA fuente de verdad de la KB.
  - kb_index.json es un artefacto de exportación/caché generado bajo demanda.
  - Los archivos kb_{video_id}.md NO son la fuente de verdad; este módulo
    los genera opcionalmente como copia legible para inspección humana.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class KBIndexSync:
    """Genera kb_index.json desde SQLite y opcionalmente archivos kb_*.md."""

    KB_INDEX_VERSION = "2.0.0"

    def __init__(self,
                 db_path: Optional[str] = None,
                 workspace_path: str = "ai_workspace"):
        if db_path is None:
            from app.config.path_manager import PathManager
            db_path = str(PathManager.get_paths()["db"])
        self.db_path = db_path
        self.workspace_path = Path(workspace_path)
        self.kb_dir = self.workspace_path / "knowledge_base"
        self.memory_dir = self.workspace_path / "memory"
        self.index_path = self.memory_dir / "kb_index.json"
        self.kb_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    # ─── Consulta SQLite ────────────────────────────────────────────────────

    def _query_kb_entries(self) -> List[Dict[str, Any]]:
        """Agrega entradas de product_trends, conversion_formulas y operations_traffic."""
        entries: List[Dict[str, Any]] = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # product_trends
                rows = conn.execute("""
                    SELECT pt.id, pt.video_id, pt.product_name, pt.niche,
                           pt.wow_factor, pt.estimated_margin, pt.validated_at,
                           vs.title AS video_title, vs.channel_name, vs.processed_at
                    FROM product_trends pt
                    LEFT JOIN video_sources vs ON pt.video_id = vs.video_id
                    ORDER BY pt.id DESC
                """).fetchall()
                for r in rows:
                    entries.append({
                        "tipo": "producto",
                        "tabla": "product_trends",
                        "id": r["id"],
                        "video_id": r["video_id"] or "",
                        "video_title": r["video_title"] or "",
                        "canal": r["channel_name"] or "",
                        "fecha_indexacion": (r["validated_at"] or r["processed_at"] or "")[:10],
                        "nombre": r["product_name"],
                        "nicho": r["niche"],
                        "wow_factor": r["wow_factor"] or "",
                        "margen_estimado": r["estimated_margin"],
                    })

                # conversion_formulas
                rows = conn.execute("""
                    SELECT cf.id, cf.video_id, cf.category, cf.framework_name,
                           cf.raw_structure, cf.persuasion_triggers,
                           vs.title AS video_title, vs.channel_name
                    FROM conversion_formulas cf
                    LEFT JOIN video_sources vs ON cf.video_id = vs.video_id
                    ORDER BY cf.id DESC
                """).fetchall()
                for r in rows:
                    entries.append({
                        "tipo": "conversion",
                        "tabla": "conversion_formulas",
                        "id": r["id"],
                        "video_id": r["video_id"] or "",
                        "video_title": r["video_title"] or "",
                        "canal": r["channel_name"] or "",
                        "fecha_indexacion": "",
                        "categoria": r["category"],
                        "framework": r["framework_name"] or "AIDA",
                        "estructura": (r["raw_structure"] or "")[:300],
                        "triggers": r["persuasion_triggers"] or "",
                    })

                # operations_traffic
                rows = conn.execute("""
                    SELECT ot.id, ot.video_id, ot.traffic_source, ot.scaling_strategy,
                           ot.logistics_notes, ot.weight_kg,
                           vs.title AS video_title, vs.channel_name
                    FROM operations_traffic ot
                    LEFT JOIN video_sources vs ON ot.video_id = vs.video_id
                    ORDER BY ot.id DESC
                """).fetchall()
                for r in rows:
                    entries.append({
                        "tipo": "operaciones",
                        "tabla": "operations_traffic",
                        "id": r["id"],
                        "video_id": r["video_id"] or "",
                        "video_title": r["video_title"] or "",
                        "canal": r["channel_name"] or "",
                        "fecha_indexacion": "",
                        "fuente_trafico": r["traffic_source"],
                        "estrategia_escalado": r["scaling_strategy"] or "",
                        "logistica": r["logistics_notes"] or "",
                        "peso_kg": r["weight_kg"],
                    })

        except sqlite3.Error as exc:
            logger.error(f"[KBIndexSync] Error consultando SQLite: {exc}")

        return entries

    # ─── Generar índice ─────────────────────────────────────────────────────

    def sync(self) -> Dict[str, Any]:
        """
        Regenera kb_index.json desde SQLite.
        Retorna el índice generado como dict.
        """
        entries = self._query_kb_entries()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        index: Dict[str, Any] = {
            "kb_version": self.KB_INDEX_VERSION,
            "fuente": "sqlite",
            "nota": "Generado automáticamente desde SQLite. No editar manualmente.",
            "ultima_actualizacion": now,
            "total_entradas": len(entries),
            "por_tipo": {
                "productos": sum(1 for e in entries if e["tipo"] == "producto"),
                "conversion": sum(1 for e in entries if e["tipo"] == "conversion"),
                "operaciones": sum(1 for e in entries if e["tipo"] == "operaciones"),
            },
            "entradas": entries,
        }

        try:
            self.index_path.write_text(
                json.dumps(index, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(
                f"[KBIndexSync] kb_index.json actualizado — {len(entries)} entradas."
            )
        except OSError as exc:
            logger.error(f"[KBIndexSync] Error escribiendo kb_index.json: {exc}")

        return index

    # ─── Generar archivos .md por video (opcional, solo para inspección) ────

    def export_md_for_video(self, video_id: str) -> Optional[Path]:
        """
        Genera un archivo kb_{video_id}.md con todas las entradas de ese video.
        Es una copia legible de lo que ya está en SQLite — no es la fuente de verdad.
        Retorna la ruta del archivo generado, o None si no hay datos.
        """
        entries = [e for e in self._query_kb_entries() if e.get("video_id") == video_id]
        if not entries:
            return None

        canal = entries[0].get("canal", "desconocido")
        titulo = entries[0].get("video_title", video_id)
        fecha = entries[0].get("fecha_indexacion", datetime.now().strftime("%Y-%m-%d"))

        lines = [
            f"# KB: {titulo}",
            "",
            f"**video_id:** {video_id}",
            f"**canal:** {canal}",
            f"**fecha_indexacion:** {fecha}",
            f"**fuente:** sqlite (GEM OS v{self.KB_INDEX_VERSION})",
            f"**nota:** Exportado desde SQLite — no editar manualmente.",
            "",
            "---",
            "",
        ]

        productos = [e for e in entries if e["tipo"] == "producto"]
        if productos:
            lines.append("## Productos")
            for p in productos:
                lines.append(
                    f"- **{p['nombre']}** | Nicho: {p['nicho']} "
                    f"| Margen: {p['margen_estimado']}x | {p['wow_factor']}"
                )
            lines.append("")

        conversiones = [e for e in entries if e["tipo"] == "conversion"]
        if conversiones:
            lines.append("## Fórmulas de Conversión")
            for c in conversiones:
                lines.append(f"- **{c['framework']}** ({c['categoria']}): {c['estructura'][:200]}")
            lines.append("")

        operaciones = [e for e in entries if e["tipo"] == "operaciones"]
        if operaciones:
            lines.append("## Operaciones & Tráfico")
            for o in operaciones:
                lines.append(
                    f"- Tráfico: {o['fuente_trafico']} | Escalado: {o['estrategia_escalado'][:100]}"
                )
            lines.append("")

        lines.append("---")
        lines.append(f"*Exportado por KBIndexSync v{self.KB_INDEX_VERSION} · GEM OS*")

        md_path = self.kb_dir / f"kb_{video_id}.md"
        try:
            md_path.write_text("\n".join(lines), encoding="utf-8")
            logger.info(f"[KBIndexSync] Generado {md_path.name}")
            return md_path
        except OSError as exc:
            logger.error(f"[KBIndexSync] Error escribiendo {md_path}: {exc}")
            return None
