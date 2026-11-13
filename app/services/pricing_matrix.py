"""
PricingMatrix — Generador de Matriz de Precios 2x/3x
Aplica las reglas de negocio de GEM OS (.claude/memory/reglas-financieras.md):
  - Todo múltiplo se calcula sobre el coste LANDED (producto + envío)
  - Precios terminados en .99, nunca por debajo del múltiplo
  - Clasificación HOT/WARM/COLD/DISCARD por ratio PVP/landed (product_catalog.clasificar)
  - Margen = (PVP - landed) / PVP × 100 (informativo: el curso no fija umbral)
  - El envío es un dato del proveedor: sin él no se calcula (DATA_GAP_REQUEST)
  - Delega la validación a FinancialValidator (no duplica lógica)
"""

import math
import uuid
import re
import hashlib
from typing import Dict, List, Optional
from datetime import datetime

from app.services.financial_validator import FinancialValidator
from app.services.product_catalog import clasificar
from app.database.connection import DatabaseConnection


class PricingMatrix:
    """
    Genera la matriz de precios 2x/3x con auditoría financiera completa.
    Importa FinancialValidator para compliance — no duplica reglas de negocio.
    """

    def __init__(self, db_manager: Optional[DatabaseConnection] = None):
        self.db = db_manager or DatabaseConnection()
        self.validator = FinancialValidator(db_manager=self.db)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_99(price: float) -> float:
        """
        Primer precio terminado en .99 que sea >= price: $14.00 → $14.99, $28.50 → $28.99.

        Nunca redondea hacia abajo: $13.99 sobre un landed de $7.00 es 1,998x y no
        cumple el mínimo 2x.
        """
        cents = math.ceil(round(price * 100, 6))
        return round(cents // 100 + 0.99, 2)

    @staticmethod
    def _dato_requerido(p: Dict, *claves: str) -> float:
        """Devuelve el primer campo presente. Sin dato no hay cálculo: nunca se estima."""
        for clave in claves:
            if p.get(clave) is not None:
                return float(p[clave])
        raise ValueError(
            f"DATA_GAP_REQUEST: falta '{claves[0]}' del producto "
            f"'{p.get('name', '?')}'. Pídeselo al usuario; no se asume ningún valor."
        )

    @staticmethod
    def _make_sku(name: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]", "", name.upper())[:12]
        suffix = hashlib.md5(name.encode()).hexdigest()[:6].upper()
        return f"{slug}_{suffix}"

    # ------------------------------------------------------------------
    # Core calculation
    # ------------------------------------------------------------------

    def calculate(self, products: List[Dict], budget_month: str = "") -> List[Dict]:
        """
        Calcula la matriz para cada producto.

        Args:
            products: lista de dicts con claves:
                - name (str, requerido)
                - cost_usd (float, requerido)
                - shipping_usd (float, requerido; se acepta el alias shipping_override)
                - weight_kg (float, opcional, informativo)
                - vertical (str, opcional, solo etiqueta)
            budget_month: "YYYY-MM" para auditoría

        Returns:
            Lista de dicts con resultados por producto.

        Raises:
            ValueError: DATA_GAP_REQUEST si falta el coste o el envío de un producto.
        """
        results = []
        for p in products:
            name = p["name"]
            cost = self._dato_requerido(p, "cost_usd")
            shipping = self._dato_requerido(p, "shipping_usd", "shipping_override")
            weight = float(p.get("weight_kg", 0.0))
            vertical = p.get("vertical", "default")
            sku = self._make_sku(name)

            landed = round(cost + shipping, 2)
            if landed <= 0:
                raise ValueError(
                    f"DATA_GAP_REQUEST: el coste landed de '{name}' es {landed}; "
                    "revisa coste y envío con el usuario."
                )

            pvp_2x = self._to_99(landed * 2)
            pvp_3x = self._to_99(landed * 3)

            ratio_2x = pvp_2x / landed
            ratio_3x = pvp_3x / landed

            margin_2x = round((pvp_2x - landed) / pvp_2x * 100, 1)
            margin_3x = round((pvp_3x - landed) / pvp_3x * 100, 1)

            # La validación (mínimo 2x sobre landed, fees, cancelaciones) es de FinancialValidator
            fv = self.validator.validar_producto(
                sku=sku,
                costo_origen=cost,
                peso_kg=weight,
                pvp_sugerido=pvp_3x,
                costo_envio=shipping,
            )

            results.append({
                "name": name,
                "sku": sku,
                "cost_usd": cost,
                "weight_kg": weight,
                "vertical": vertical,
                "shipping_usd": shipping,
                "landed_usd": landed,
                "pvp_2x": pvp_2x,
                "pvp_3x": pvp_3x,
                "ratio_2x": round(ratio_2x, 2),
                "ratio_3x": round(ratio_3x, 2),
                "margin_net_2x": margin_2x,
                "margin_net_3x": margin_3x,
                "classification_2x": clasificar(ratio_2x),
                "classification_3x": clasificar(ratio_3x),
                "fv_compliant": fv["validado"],
                "fv_note": fv.get("nota_auditoria", ""),
                "budget_month": budget_month,
            })
        return results

    # ------------------------------------------------------------------
    # Output formatting
    # ------------------------------------------------------------------

    @staticmethod
    def format_ascii_table(results: List[Dict]) -> str:
        col_name = 24
        header = (
            f"{'Producto':<{col_name}} {'CO':>6} {'Ship':>5} {'Landed':>7} "
            f"{'PVP 2x':>8} {'Mg2x':>6} {'Cls2x':>7} "
            f"{'PVP 3x':>8} {'Mg3x':>6} {'Cls3x':>7} {'FV':>5}"
        )
        sep = "─" * len(header)
        rows = [sep, header, sep]
        for r in results:
            fv_flag = "✓ OK" if r["fv_compliant"] else "✗ KO"
            row = (
                f"{r['name'][:col_name]:<{col_name}} "
                f"${r['cost_usd']:>5.2f} "
                f"${r['shipping_usd']:>4.2f} "
                f"${r['landed_usd']:>6.2f} "
                f"${r['pvp_2x']:>7.2f} "
                f"{r['margin_net_2x']:>5.1f}% "
                f"{r['classification_2x']:>7} "
                f"${r['pvp_3x']:>7.2f} "
                f"{r['margin_net_3x']:>5.1f}% "
                f"{r['classification_3x']:>7} "
                f"{fv_flag:>5}"
            )
            rows.append(row)
        rows.append(sep)

        # Summary
        cls_counts = {}
        for r in results:
            c = r["classification_3x"]
            cls_counts[c] = cls_counts.get(c, 0) + 1
        summary_parts = [f"{k}: {v}" for k, v in sorted(cls_counts.items())]
        rows.append(f"\nResumen (3x): {' | '.join(summary_parts)}")

        return "\n".join(rows)

    # ------------------------------------------------------------------
    # DB persistence
    # ------------------------------------------------------------------

    def save_to_db(self, results: List[Dict], correlation_id: Optional[str] = None) -> List[int]:
        """
        Escribe resultados en productos_validados.
        INSERT OR REPLACE por SKU — re-validar el mismo producto actualiza la fila.
        """
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())

        ids = []
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            for r in results:
                status = "validado" if r["fv_compliant"] else "rechazado"
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO productos_validados
                        (sku, costo_origen, pvp, margen_bruto, status_validacion,
                         validado_regla_3x, peso_kg, nota_auditoria,
                         correlation_id, budget_month, vertical, actualizada_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r["sku"],
                        r["cost_usd"],
                        r["pvp_3x"],
                        r["margin_net_3x"],
                        status,
                        1 if r["fv_compliant"] else 0,
                        r["weight_kg"],
                        r["fv_note"],
                        correlation_id,
                        r["budget_month"],
                        r["vertical"],
                        datetime.now().isoformat(),
                    ),
                )
                ids.append(cursor.lastrowid)
            conn.commit()
        return ids

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(
        self,
        products: List[Dict],
        budget_month: str = "",
        save: bool = True,
    ) -> Dict:
        """
        Calcula, formatea y opcionalmente guarda la matriz de precios.

        Returns:
            {
              "correlation_id": str,
              "results": List[Dict],
              "table": str,
              "saved_ids": List[int],
            }
        """
        if not budget_month:
            budget_month = datetime.now().strftime("%Y-%m")

        correlation_id = str(uuid.uuid4())
        results = self.calculate(products, budget_month=budget_month)
        table = self.format_ascii_table(results)
        saved_ids = self.save_to_db(results, correlation_id=correlation_id) if save else []

        return {
            "correlation_id": correlation_id,
            "results": results,
            "table": table,
            "saved_ids": saved_ids,
        }
