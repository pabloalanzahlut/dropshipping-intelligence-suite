"""
Metrics Aggregator — Vista única producto → decisión → resultado real.

POR QUÉ
-------
Los datos de GEM OS viven repartidos: la clasificación en SQLite, el gasto de
ads en Meta, las ventas en Shopify, el histórico en Google Sheets. Mientras
sigan separados es imposible responder la única pregunta que importa:
**¿los productos que el sistema clasificó como HOT realmente vendieron?**

Adrián Sáenz lo plantea así (Ra3GIwwT4Yc): construye un panel propio no por
comodidad, sino porque solo con todos los datos en un sitio puede pasárselos a
Claude para que decida. La fragmentación impide la automejora.

Este módulo es el prerequisito de `self_improve.py`: sin la vista unificada,
el loop de aprendizaje no tiene con qué comparar.
"""

import os
import json
import sqlite3
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ProductMetrics:
    """Una fila de la vista unificada: qué decidimos y qué pasó realmente."""
    sku: str
    nombre: str
    # Lo que el sistema decidió
    clasificacion: Optional[str] = None       # HOT / WARM / COLD / DISCARD
    score: Optional[int] = None               # 0-100
    clasificado_at: Optional[str] = None
    multiplicador_previsto: Optional[float] = None
    margen_neto_previsto: Optional[float] = None
    # Lo que ocurrió
    unidades_vendidas: int = 0
    ingresos: float = 0.0
    gasto_ads: float = 0.0
    cancelaciones: int = 0
    # Derivados
    roas_real: Optional[float] = None
    margen_real: Optional[float] = None
    tasa_cancelacion: Optional[float] = None
    # Veredicto
    acierto: Optional[bool] = None            # ¿la clasificación se confirmó?

    def calcular_derivados(self) -> None:
        """Calcula ROAS, margen y tasa de cancelación a partir de los datos crudos."""
        if self.gasto_ads > 0:
            self.roas_real = round(self.ingresos / self.gasto_ads, 2)
        if self.ingresos > 0:
            self.margen_real = round((self.ingresos - self.gasto_ads) / self.ingresos, 4)
            total_pedidos = self.unidades_vendidas + self.cancelaciones
            if total_pedidos > 0:
                self.tasa_cancelacion = round(self.cancelaciones / total_pedidos, 4)

    def evaluar_acierto(self, roas_minimo: float = 2.0) -> None:
        """
        Compara la predicción con el resultado.

        HOT que no alcanzó el ROAS mínimo = fallo del clasificador.
        COLD o DISCARD que habría vendido bien no se puede medir (nunca se probó),
        así que queda como None en lugar de contarse como acierto.
        """
        if self.clasificacion in ("HOT", "WARM"):
            if self.gasto_ads <= 0:
                self.acierto = None  # nunca se probó
            else:
                self.acierto = (self.roas_real or 0) >= roas_minimo
        else:
            self.acierto = None


class MetricsAggregator:
    """Unifica las fuentes de datos en una sola vista consultable."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv(
            "DATABASE_PATH", "app/database/dropshipping_suite.db"
        )

    # ── Lectura por fuente ────────────────────────────────────────────────────

    # Columnas que el clasificador v2 añade a product_trends. Pueden no existir
    # todavía: la query se adapta a lo que haya en el esquema.
    COLUMNAS_OPCIONALES = ("clasificacion", "score", "clasificado_at", "margen_neto_unidad")

    def _columnas_disponibles(self, conn: sqlite3.Connection) -> set:
        return {r[1] for r in conn.execute("PRAGMA table_info(product_trends)")}

    def _leer_clasificaciones(self, dias: int) -> Dict[str, ProductMetrics]:
        """
        Lee las decisiones que tomó el sistema desde SQLite.

        El esquema base de product_trends no tiene columnas de clasificación;
        las añade el clasificador v2. Se leen solo las que existan.
        """
        desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
        filas: Dict[str, ProductMetrics] = {}

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            disponibles = self._columnas_disponibles(conn)

            base = ["product_name", "estimated_margin", "validated_at"]
            extra = [c for c in self.COLUMNAS_OPCIONALES if c in disponibles]
            campo_fecha = "clasificado_at" if "clasificado_at" in disponibles else "validated_at"

            cur = conn.execute(
                f"SELECT {', '.join(base + extra)} FROM product_trends "
                f"WHERE {campo_fecha} >= ? OR {campo_fecha} IS NULL",
                (desde,),
            )
            for row in cur.fetchall():
                nombre = row["product_name"] or ""
                if not nombre:
                    continue
                claves = row.keys()
                filas[nombre] = ProductMetrics(
                    sku=nombre,
                    nombre=nombre,
                    clasificacion=row["clasificacion"] if "clasificacion" in claves else None,
                    score=row["score"] if "score" in claves else None,
                    clasificado_at=row[campo_fecha],
                    multiplicador_previsto=row["estimated_margin"],
                    margen_neto_previsto=(
                        row["margen_neto_unidad"] if "margen_neto_unidad" in claves else None
                    ),
                )
            conn.close()
        except sqlite3.OperationalError as e:
            logger.warning(f"[METRICS] No se pudieron leer clasificaciones: {e}")

        return filas

    def _aplicar_ventas_shopify(self, filas: Dict[str, ProductMetrics], dias: int) -> None:
        """Cruza con las ventas reales de Shopify."""
        token = os.getenv("SHOPIFY_ACCESS_TOKEN")
        store = os.getenv("SHOPIFY_STORE_URL")
        if not token or not store or token.startswith("PENDIENTE"):
            logger.info("[METRICS] Shopify no configurado — sin datos de ventas")
            return

        try:
            import requests
            desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
            resp = requests.get(
                f"https://{store}/admin/api/2026-01/orders.json",
                headers={"X-Shopify-Access-Token": token},
                params={"status": "any", "created_at_min": desde, "limit": 250},
                timeout=30,
            )
            resp.raise_for_status()

            for order in resp.json().get("orders", []):
                cancelado = order.get("cancelled_at") is not None
                for item in order.get("line_items", []):
                    sku = item.get("sku") or item.get("title", "")
                    fila = filas.get(sku)
                    if fila is None:
                        fila = ProductMetrics(sku=sku, nombre=item.get("title", ""))
                        filas[sku] = fila
                    if cancelado:
                        fila.cancelaciones += item.get("quantity", 0)
                    else:
                        fila.unidades_vendidas += item.get("quantity", 0)
                        fila.ingresos += float(item.get("price", 0)) * item.get("quantity", 0)

        except Exception as e:
            logger.warning(f"[METRICS] Shopify no respondió: {e}")

    def _aplicar_gasto_ads(self, filas: Dict[str, ProductMetrics]) -> None:
        """
        Cruza con el gasto de Meta Ads.

        Sin API de Meta configurada, lee el fichero manual que el operador
        mantiene. Es la fuente menos automatizable del conjunto.
        """
        ruta = "ai_workspace/knowledge_base/gasto_ads.json"
        if not os.path.exists(ruta):
            logger.info(f"[METRICS] Sin datos de ads ({ruta} no existe)")
            return
        try:
            with open(ruta, encoding="utf-8") as f:
                gastos = json.load(f)
            for sku, gasto in gastos.items():
                if sku in filas:
                    filas[sku].gasto_ads = float(gasto)
        except Exception as e:
            logger.warning(f"[METRICS] No se pudo leer gasto de ads: {e}")

    # ── Vista unificada ───────────────────────────────────────────────────────

    def construir_vista(self, dias: int = 21) -> List[ProductMetrics]:
        """
        Devuelve la vista unificada de los últimos N días.

        21 días es el ciclo que Adrián usa para evaluar: suficiente para que una
        campaña dé señal, corto para corregir antes de quemar presupuesto.
        """
        filas = self._leer_clasificaciones(dias)
        self._aplicar_ventas_shopify(filas, dias)
        self._aplicar_gasto_ads(filas)

        for fila in filas.values():
            fila.calcular_derivados()
            fila.evaluar_acierto()

        return sorted(
            filas.values(),
            key=lambda f: (f.ingresos, f.score or 0),
            reverse=True,
        )

    def resumen(self, dias: int = 21) -> Dict:
        """
        Resumen agregado — es lo que se le pasa a Claude para que evalúe
        si los criterios de clasificación están funcionando.
        """
        vista = self.construir_vista(dias)
        medibles = [f for f in vista if f.acierto is not None]
        aciertos = [f for f in medibles if f.acierto]
        hot = [f for f in vista if f.clasificacion == "HOT"]

        ingresos = sum(f.ingresos for f in vista)
        gasto = sum(f.gasto_ads for f in vista)
        canceladas = sum(f.cancelaciones for f in vista)
        vendidas = sum(f.unidades_vendidas for f in vista)

        return {
            "periodo_dias": dias,
            "productos_evaluados": len(vista),
            "productos_medibles": len(medibles),
            "precision_clasificador": (
                round(len(aciertos) / len(medibles), 4) if medibles else None
            ),
            "hot_total": len(hot),
            "hot_que_vendieron": len([f for f in hot if f.unidades_vendidas > 0]),
            "ingresos_totales": round(ingresos, 2),
            "gasto_ads_total": round(gasto, 2),
            "roas_global": round(ingresos / gasto, 2) if gasto > 0 else None,
            "tasa_cancelacion_global": (
                round(canceladas / (vendidas + canceladas), 4)
                if (vendidas + canceladas) > 0 else None
            ),
            "generado_at": datetime.now(timezone.utc).isoformat(),
        }

    def exportar_json(self, ruta: str = "ai_workspace/knowledge_base/metrics_view.json",
                      dias: int = 21) -> str:
        """Guarda la vista completa para que el loop de auto-mejora la lea."""
        payload = {
            "resumen": self.resumen(dias),
            "productos": [asdict(f) for f in self.construir_vista(dias)],
        }
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        logger.info(f"[METRICS] Vista exportada a {ruta}")
        return ruta
