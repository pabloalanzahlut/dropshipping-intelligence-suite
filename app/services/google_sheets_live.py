"""
Google Sheets Live — Integración en tiempo real via Service Account
===================================================================
GEM OS Suite — Reemplaza el workaround CSV con la API oficial de Google Sheets.

Requiere:
  pip install gspread google-auth
  GOOGLE_CREDENTIALS_PATH y GOOGLE_SHEETS_SPREADSHEET_ID en .env

Hoja esperada "GEM OS Dashboard" con pestañas:
  - Pipeline       : tracker HOT/WARM/COLD por producto
  - ROAS_Diario    : métricas de campañas por día
  - Productos      : catálogo con costo/PVP/multiplicador
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import gspread
    from google.oauth2.service_account import Credentials
    _GSPREAD_AVAILABLE = True
except ImportError:
    _GSPREAD_AVAILABLE = False
    logger.warning("[SHEETS] gspread no instalado — ejecuta: pip install gspread google-auth")

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

_client: Optional[object] = None


def _get_client():
    global _client
    if _client:
        return _client

    if not _GSPREAD_AVAILABLE:
        raise RuntimeError("gspread no disponible — pip install gspread google-auth")

    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "ai_workspace/config/google_credentials.json")
    if not os.path.exists(creds_path):
        raise FileNotFoundError(
            f"Credenciales no encontradas: {creds_path}\n"
            "Sigue las instrucciones en .env para crear el Service Account."
        )

    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    _client = gspread.authorize(creds)
    return _client


def _get_sheet(tab_name: str):
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
    if not spreadsheet_id or spreadsheet_id == "PENDIENTE":
        raise ValueError(
            "GOOGLE_SHEETS_SPREADSHEET_ID no configurado en .env\n"
            "Copia el ID de tu hoja desde la URL de Google Sheets."
        )
    client = _get_client()
    spreadsheet = client.open_by_key(spreadsheet_id)
    try:
        return spreadsheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=20)


# ─── Pipeline HOT/WARM/COLD ───────────────────────────────────────────────────

PIPELINE_HEADERS = [
    "Fecha", "SKU", "Nombre", "Costo Origen", "PVP",
    "Multiplicador", "Clasificacion", "Peso KG", "Categoria", "ROAS",
]


def upsert_producto_pipeline(producto: Dict) -> bool:
    """
    Inserta o actualiza un producto en la pestaña Pipeline.
    Busca por SKU — actualiza si existe, inserta si no.
    """
    sheet = _get_sheet("Pipeline")

    # Crear headers si la hoja está vacía
    if not sheet.row_values(1):
        sheet.append_row(PIPELINE_HEADERS)

    sku = str(producto.get("sku", ""))
    costo = float(producto.get("costo_origen", 0))
    pvp = float(producto.get("pvp", 0))
    multiplicador = round(pvp / costo, 2) if costo > 0 else 0
    clasificacion = _clasificar(multiplicador)

    nueva_fila = [
        datetime.now().strftime("%Y-%m-%d"),
        sku,
        producto.get("nombre", ""),
        costo,
        pvp,
        multiplicador,
        clasificacion,
        producto.get("peso_kg", 0),
        producto.get("categoria", ""),
        producto.get("roas", ""),
    ]

    # Buscar SKU existente. gspread ≥ 6 devuelve None si no lo encuentra; las versiones antiguas lanzan CellNotFound.
    try:
        cell = sheet.find(sku, in_column=2)
    except getattr(gspread.exceptions, "CellNotFound", ()):
        cell = None
    if cell is not None:
        sheet.update(f"A{cell.row}:J{cell.row}", [nueva_fila])
        logger.info(f"[SHEETS] Actualizado: {sku} → {clasificacion}")
    else:
        sheet.append_row(nueva_fila)
        logger.info(f"[SHEETS] Insertado: {sku} → {clasificacion}")

    return True


def get_productos_por_clasificacion(clasificacion: str) -> List[Dict]:
    """Devuelve todos los productos HOT, WARM o COLD del Pipeline."""
    sheet = _get_sheet("Pipeline")
    rows = sheet.get_all_records(value_render_option=gspread.utils.ValueRenderOption.unformatted)
    return [r for r in rows if str(r.get("Clasificacion", "")).upper() == clasificacion.upper()]


# ─── ROAS Diario ──────────────────────────────────────────────────────────────

ROAS_HEADERS = [
    "Fecha", "Campaña", "Gasto €", "Ingresos €", "ROAS",
    "Pedidos", "CPA €", "Estado",
]


def registrar_roas(campana: str, gasto: float, ingresos: float, pedidos: int = 0) -> Dict:
    """Registra métricas diarias de una campaña."""
    sheet = _get_sheet("ROAS_Diario")

    if not sheet.row_values(1):
        sheet.append_row(ROAS_HEADERS)

    roas = round(ingresos / gasto, 2) if gasto > 0 else 0
    cpa = round(gasto / pedidos, 2) if pedidos > 0 else 0
    estado = "OK" if roas >= 2.0 else "ALERTA"

    fila = [
        datetime.now().strftime("%Y-%m-%d"),
        campana, gasto, ingresos, roas, pedidos, cpa, estado,
    ]
    sheet.append_row(fila)
    logger.info(f"[SHEETS] ROAS registrado: {campana} → {roas}× ({estado})")
    return {"campana": campana, "roas": roas, "estado": estado}


def get_roas_hoy() -> List[Dict]:
    """Devuelve todas las campañas registradas hoy."""
    sheet = _get_sheet("ROAS_Diario")
    hoy = datetime.now().strftime("%Y-%m-%d")
    rows = sheet.get_all_records(value_render_option=gspread.utils.ValueRenderOption.unformatted)
    return [r for r in rows if r.get("Fecha") == hoy]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _clasificar(multiplicador: float) -> str:
    if multiplicador >= 5:
        return "HOT"
    elif multiplicador >= 3:
        return "WARM"
    elif multiplicador >= 2:
        return "COLD"
    return "DISCARD"


def health_check() -> Dict:
    """Verifica que la conexión a Sheets funcione."""
    try:
        sheet = _get_sheet("Pipeline")
        return {"status": "OK", "sheet": sheet.title, "rows": sheet.row_count}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}
