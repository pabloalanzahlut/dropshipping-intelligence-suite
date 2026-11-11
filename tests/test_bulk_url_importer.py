"""Importación masiva por URL. Sin red: Shopify falso, tipo de cambio fijo, BD temporal."""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import DatabaseConnection
from app.services.bulk_url_importer import (BulkUrlImporter, DESCRIPCION_BORRADOR, detectar_plataforma,
                                            extraer_product_id, parsear_lineas)

URL = "https://es.aliexpress.com/item/1005006789123456.html"
URL2 = "https://es.aliexpress.com/item/1005000000000002.html"


class ShopifyFalso:
    def __init__(self, moneda="EUR"):
        self.moneda = moneda
        self.llamadas = []

    def shop_info(self):
        return {"moneda": self.moneda}

    def create_draft_product(self, **kw):
        self.llamadas.append(kw)
        return str(1000 + len(self.llamadas))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        (Path(self.tmp.name) / "data").mkdir()
        self.db_path = str(Path(self.tmp.name) / "data" / "t.db")
        self.db = DatabaseConnection(self.db_path)
        self.shopify = ShopifyFalso()
        self.imp = BulkUrlImporter(self.db, shopify=self.shopify, titulo_fn=lambda u: "Producto de prueba", pausa=0)
        p1 = mock.patch("app.services.fx_rates.get_rate", return_value=0.9)
        p2 = mock.patch("app.services.fx_rates.is_rate_live", return_value=True)
        p1.start(), p2.start()
        self.addCleanup(mock.patch.stopall)

    def tearDown(self):
        self.tmp.cleanup()

    def item(self, url=URL, costo=10.0, envio=2.0):
        return {"url": url, "costo_origen": costo, "costo_envio": envio}

    def filas(self):
        with sqlite3.connect(self.db_path) as c:
            return c.execute("SELECT url_origen, status FROM importaciones_masivas").fetchall()


class TestParseo(unittest.TestCase):
    def test_plataforma_e_id(self):
        self.assertEqual(detectar_plataforma(URL), "aliexpress")
        self.assertEqual(extraer_product_id(URL, "aliexpress"), "1005006789123456")
        self.assertEqual(extraer_product_id("https://www.temu.com/es/producto-7891234.html", "temu"), "7891234")

    def test_lineas_con_coma_decimal_y_huecos(self):
        items = parsear_lineas(f"{URL} 10,5 2\n\n{URL2} 8\n")
        self.assertEqual(items[0], {"url": URL, "costo_origen": 10.5, "costo_envio": 2.0})
        self.assertEqual(items[1]["costo_origen"], 8.0)
        self.assertIsNone(items[1]["costo_envio"])


class TestImportador(Base):
    def test_falta_envio_es_data_gap_y_no_toca_shopify(self):
        r = self.imp.importar_lote([self.item(envio=None)])[0]
        self.assertEqual(r["status"], "skipped")
        self.assertIn("DATA_GAP_REQUEST", r["error"])
        self.assertEqual(self.shopify.llamadas, [])

    def test_precio_sobre_landed_convertido_a_la_divisa_de_la_tienda(self):
        r = self.imp.importar_lote([self.item()], moneda_costo="USD")[0]
        self.assertEqual(r["status"], "success")
        # (10 + 2) USD × 0,9 = 10,80 EUR landed → ×3 = 32,40 EUR (no 30,00 ni 36,00)
        self.assertEqual(self.shopify.llamadas[0]["precio"], 32.40)
        self.assertEqual(r["validacion"]["costo_landed"], 10.80)

    def test_misma_divisa_no_convierte(self):
        self.shopify.moneda = "USD"
        self.imp._moneda = None
        self.imp.importar_lote([self.item()], moneda_costo="USD")
        self.assertEqual(self.shopify.llamadas[0]["precio"], 36.00)

    def test_descripcion_no_filtra_proveedor_ni_calculos(self):
        self.imp.importar_lote([self.item()])
        desc = self.shopify.llamadas[0]["descripcion"]
        self.assertEqual(desc, DESCRIPCION_BORRADOR)
        for dato in ("aliexpress", "http", "3x", "PVP"):
            self.assertNotIn(dato.lower(), desc.lower())

    def test_duplicado_no_crea_segundo_borrador(self):
        self.imp.importar_lote([self.item()])
        r = self.imp.importar_lote([self.item()])[0]
        self.assertEqual(r["status"], "skipped")
        self.assertIn("Duplicado", r["error"])
        self.assertEqual(len(self.shopify.llamadas), 1)

    def test_cada_producto_usa_su_propio_coste(self):
        self.imp.importar_lote([self.item(costo=10.0), self.item(url=URL2, costo=5.0, envio=1.0)])
        precios = [c["precio"] for c in self.shopify.llamadas]
        self.assertEqual(precios, [32.40, 16.20])

    def test_etiqueta_de_lote_en_tags(self):
        self.imp.importar_lote([self.item()], etiqueta_lote="test-2026-11")
        self.assertIn("test-2026-11", self.shopify.llamadas[0]["tags"])

    def test_gate_bloquea_si_el_multiplicador_no_cuadra(self):
        incoherente = {"passed": False, "violations": ["no cuadra"]}
        with mock.patch("app.services.bulk_url_importer.verificar_validacion_financiera", return_value=incoherente):
            r = self.imp.importar_lote([self.item()])[0]
        self.assertEqual(r["status"], "error")
        self.assertIn("Gate determinista", r["error"])
        self.assertEqual(self.shopify.llamadas, [])

    def test_titulo_vacio_usa_marcador_en_vez_de_basura(self):
        imp = BulkUrlImporter(self.db, shopify=self.shopify, titulo_fn=lambda u: "", pausa=0)
        imp.importar_lote([self.item()])
        self.assertIn("revisar título", self.shopify.llamadas[0]["titulo"])

    def test_se_registra_en_bd(self):
        self.imp.importar_lote([self.item()])
        self.assertEqual(self.filas(), [(URL, "success")])


if __name__ == "__main__":
    unittest.main()
