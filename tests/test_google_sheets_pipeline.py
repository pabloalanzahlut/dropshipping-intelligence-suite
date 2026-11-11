"""upsert_producto_pipeline con gspread 6.x: find() devuelve None si no hay SKU (no lanza CellNotFound)."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import google_sheets_live as gs


class HojaFalsa:
    def __init__(self, existente=None):
        self.existente, self.actualizadas, self.anadidas = existente, [], []

    def row_values(self, n):
        return gs.PIPELINE_HEADERS

    def find(self, sku, in_column=None):
        return mock.Mock(row=self.existente) if self.existente else None

    def update(self, rango, filas):
        self.actualizadas.append((rango, filas))

    def append_row(self, fila):
        self.anadidas.append(fila)


@unittest.skipUnless(gs._GSPREAD_AVAILABLE, "gspread no instalado")
class TestUpsert(unittest.TestCase):
    PRODUCTO = {"sku": "123", "nombre": "Peine", "costo_origen": 10.8, "pvp": 32.99, "categoria": "x"}

    def test_sku_nuevo_se_anade_al_final(self):
        hoja = HojaFalsa()
        with mock.patch.object(gs, "_get_sheet", return_value=hoja):
            self.assertTrue(gs.upsert_producto_pipeline(self.PRODUCTO))
        self.assertEqual(len(hoja.anadidas), 1)
        self.assertEqual(hoja.anadidas[0][1:7], ["123", "Peine", 10.8, 32.99, 3.05, "WARM"])
        self.assertEqual(hoja.actualizadas, [])

    def test_sku_existente_se_actualiza_sin_duplicar(self):
        hoja = HojaFalsa(existente=5)
        with mock.patch.object(gs, "_get_sheet", return_value=hoja):
            gs.upsert_producto_pipeline(self.PRODUCTO)
        self.assertEqual(hoja.anadidas, [])
        self.assertEqual(hoja.actualizadas[0][0], "A5:J5")


if __name__ == "__main__":
    unittest.main()
