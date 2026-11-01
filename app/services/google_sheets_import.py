"""
Google Sheets Import — Importación de Datos desde Google Sheets
=================================================================
GEM OS Suite — Permite importar productos desde Google Sheets vía CSV export.
"""

import csv
import os
import logging
import tempfile
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


def import_from_csv(filepath: str, delimiter: str = ",") -> List[Dict]:
    """
    Importa datos desde un archivo CSV (exportado de Google Sheets).

    Args:
        filepath: Ruta al archivo CSV
        delimiter: Delimitador (default: coma)

    Returns:
        Lista de diccionarios con los datos importados

    Columnas esperadas:
        sku, costo_origen, peso_kg, pvp (opcional), categoria (opcional)
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

    if path.suffix.lower() not in (".csv", ".tsv"):
        logger.warning(f"[IMPORT] Extensión no estándar: {path.suffix}")

    results = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError("El CSV no tiene encabezados")

        # Normalizar nombres de columnas
        col_map = {}
        for col in reader.fieldnames:
            col_lower = col.strip().lower().replace(" ", "_")
            col_map[col] = col_lower

        for row_num, row in enumerate(reader, 2):  # 2 = skip header
            try:
                # Mapear columnas
                item = {}
                for orig_col, val in row.items():
                    norm_col = col_map.get(orig_col, orig_col)
                    item[norm_col] = val.strip() if val else ""

                # Validar campos mínimos
                sku = item.get("sku") or item.get("codigo") or item.get("id", "")
                costo = float(item.get("costo_origen") or item.get("costo") or item.get("price", 0))
                peso = float(item.get("peso_kg") or item.get("peso") or item.get("weight", 0))
                pvp = float(item.get("pvp") or item.get("precio") or item.get("price_sale", 0)) or None
                categoria = item.get("categoria") or item.get("category") or ""

                if not sku:
                    logger.warning(f"[IMPORT] Fila {row_num}: SKU vacío, saltando")
                    continue

                results.append({
                    "sku": sku,
                    "costo_origen": costo,
                    "peso_kg": peso,
                    "pvp": pvp if pvp and pvp > 0 else None,
                    "categoria": categoria,
                    "_source_row": row_num,
                    "_raw": item,
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"[IMPORT] Fila {row_num}: error parseando: {e}")
                continue

    logger.info(f"[IMPORT] CSV importado: {len(results)} productos de {path.name}")
    return results


def import_from_tsv(filepath: str) -> List[Dict]:
    """Importa desde TSV (tab-separated)."""
    return import_from_csv(filepath, delimiter="\t")


def validate_imported_data(data: List[Dict]) -> Dict:
    """
    Valida los datos importados antes de insertarlos en BD.

    Returns:
        Dict con 'validos', 'invalidos', 'errores'
    """
    validos = []
    invalidos = []

    for item in data:
        errores = []
        if item["costo_origen"] <= 0:
            errores.append("Costo de origen debe ser > 0")
        if item["peso_kg"] < 0:
            errores.append("Peso no puede ser negativo")
        if item["pvp"] is not None and item["pvp"] <= 0:
            errores.append("PVP debe ser > 0")

        if errores:
            invalidos.append({"item": item, "errores": errores})
        else:
            validos.append(item)

    return {
        "total": len(data),
        "validos": len(validos),
        "invalidos": len(invalidos),
        "items_validos": validos,
        "items_invalidos": invalidos,
    }