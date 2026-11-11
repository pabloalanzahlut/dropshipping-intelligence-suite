"""
oferta_multiunidad_service — escalones 1+1 / 2+2 validados sobre coste landed total
(skill oferta-multiunidad).

Sin matemática de coste nueva: cada escalón se valida llamando a
`FinancialValidator.validar_producto(costo_origen=coste_landed_unidad*unidades, costo_envio=0, ...)`
— exactamente la llamada que el propio markdown del skill ya muestra para el caso 1+1.
Nunca recalcula el multiplicador por su cuenta.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services.financial_validator import FinancialValidator

# Los 3 escalones del skill: unidades realmente entregadas por cada uno.
_ESCALONES = (("entrada", 1), ("principal", 2), ("upsell", 4))


def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def calcular(sku: str, costo_landed_unidad: float, pvp_entrada: float, pvp_principal: float,
            pvp_upsell: Optional[float] = None, moneda_costo: str = "USD", moneda_pvp: str = "USD") -> Dict[str, Any]:
    """Valida los 3 escalones (o 2, si no se da upsell) delegando en FinancialValidator."""
    if costo_landed_unidad <= 0:
        raise ValueError("El coste landed por unidad debe ser mayor que 0.")
    validator = FinancialValidator()
    pvps = {"entrada": pvp_entrada, "principal": pvp_principal, "upsell": pvp_upsell}

    escalones: Dict[str, Any] = {}
    ticket_ponderado = 0.0
    pvps_validos = 0
    for nombre, unidades in _ESCALONES:
        pvp = pvps[nombre]
        if pvp is None:
            continue
        v = validator.validar_producto(
            sku=f"{sku}-{nombre}", costo_origen=costo_landed_unidad * unidades, costo_envio=0.0,
            pvp_sugerido=pvp, moneda_costo=moneda_costo, moneda_pvp=moneda_pvp)
        escalones[nombre] = {
            "unidades_entregadas": unidades, "pvp": pvp, "multiplicador": v["multiplicador"],
            "margen_neto_unidad": v["margen_neto_unidad"], "validado": v["validado"],
            "status_validacion": v["status_validacion"], "nota_auditoria": v["nota_auditoria"],
        }
        ticket_ponderado += pvp
        pvps_validos += 1

    if not escalones:
        raise ValueError("Da al menos el PVP de entrada y principal.")

    return {
        "sku": sku, "costo_landed_unidad": costo_landed_unidad, "escalones": escalones,
        "ticket_medio_estimado": round(ticket_ponderado / pvps_validos, 2) if pvps_validos else 0.0,
        "veredicto_general": "validado" if all(e["validado"] for e in escalones.values()) else "revisar",
    }


def guardar(db_path: str, producto_id: Optional[int], resultado: Dict[str, Any]) -> int:
    with _db(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO ofertas_multiunidad (producto_id, escalones_json, veredicto, creado_at) VALUES (?, ?, ?, ?)",
            (producto_id, json.dumps(resultado, ensure_ascii=False), resultado.get("veredicto_general", ""),
             datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        return cur.lastrowid


def listar(db_path: str, producto_id: Optional[int] = None) -> List[Dict[str, Any]]:
    sql, params = "SELECT * FROM ofertas_multiunidad WHERE 1=1", []
    if producto_id is not None:
        sql += " AND producto_id = ?"
        params.append(producto_id)
    sql += " ORDER BY creado_at DESC, id DESC"
    with _db(db_path) as conn:
        try:
            filas = [dict(r) for r in conn.execute(sql, params)]
        except sqlite3.OperationalError:
            return []
    for f in filas:
        f["resultado"] = json.loads(f.pop("escalones_json") or "{}")
    return filas
