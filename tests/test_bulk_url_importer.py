"""Importación masiva por URL. Sin red: Shopify falso, tipo de cambio fijo, BD temporal."""
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import DatabaseConnection
from app.services.bulk_url_importer import (BulkUrlImporter, DESCRIPCION_BORRADOR, detectar_plataforma,
                                            extraer_datos_pagina, extraer_product_id, imagenes_validas,
                                            parsear_lineas, precio_psicologico)
from app.services.shopify_client import ShopifyClient

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


def pagina(titulo="Producto de prueba", imagenes=()):
    return lambda url: {"titulo": titulo, "imagenes": list(imagenes)}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        (Path(self.tmp.name) / "data").mkdir()
        self.db_path = str(Path(self.tmp.name) / "data" / "t.db")
        self.db = DatabaseConnection(self.db_path)
        self.shopify = ShopifyFalso()
        self.imp = self.nuevo()
        p1 = mock.patch("app.services.fx_rates.get_rate", return_value=0.9)
        p2 = mock.patch("app.services.fx_rates.is_rate_live", return_value=True)
        p1.start(), p2.start()
        self.addCleanup(mock.patch.stopall)

    def nuevo(self, **kw):
        kw.setdefault("pagina_fn", pagina())
        return BulkUrlImporter(self.db, shopify=self.shopify, pausa=0, **kw)

    def tearDown(self):
        self.tmp.cleanup()

    def item(self, url=URL, costo=10.0, envio=2.0, **extra):
        return {"url": url, "costo_origen": costo, "costo_envio": envio, **extra}

    def filas(self):
        with sqlite3.connect(self.db_path) as c:
            return c.execute("SELECT url_origen, status FROM importaciones_masivas").fetchall()


class TestParseo(unittest.TestCase):
    def test_plataforma_e_id(self):
        self.assertEqual(detectar_plataforma(URL), "aliexpress")
        self.assertEqual(extraer_product_id(URL, "aliexpress"), "1005006789123456")
        self.assertEqual(extraer_product_id("https://www.temu.com/es/producto-7891234.html", "temu"), "7891234")

    def test_plataforma_por_host_real_no_por_texto(self):
        for falsa in ("https://evil.net/aliexpress.com/item/1.html", "https://aliexpress.com.evil.net/item/1.html",
                      "ftp://aliexpress.com/item/1", "file:///etc/passwd", "javascript:alert(1)"):
            self.assertEqual(detectar_plataforma(falsa), "desconocida", falsa)
        self.assertEqual(detectar_plataforma("https://aliexpress.com/item/1.html"), "aliexpress")

    def test_lineas_con_coma_decimal_y_huecos(self):
        items = parsear_lineas(f"{URL} 10,5 2\n\n{URL2} 8\n")
        self.assertEqual(items[0], {"url": URL, "costo_origen": 10.5, "costo_envio": 2.0})
        self.assertEqual(items[1]["costo_origen"], 8.0)
        self.assertIsNone(items[1]["costo_envio"])

    def test_lineas_con_imagenes_y_variantes(self):
        it = parsear_lineas(f"{URL} 10 2 img=https://cdn.x/a.jpg var=Color:Rojo/Azul_marino img=https://cdn.x/b.jpg "
                            f"var=Talla:S/M")[0]
        self.assertEqual(it["costo_envio"], 2.0)
        self.assertEqual(it["imagenes"], ["https://cdn.x/a.jpg", "https://cdn.x/b.jpg"])
        self.assertEqual(it["opciones"], {"Color": ["Rojo", "Azul marino"], "Talla": ["S", "M"]})

    def test_extras_no_se_confunden_con_coste_y_envio(self):
        it = parsear_lineas(f"{URL} img=https://cdn.x/a.jpg 10 2")[0]
        self.assertEqual((it["costo_origen"], it["costo_envio"]), (10.0, 2.0))

    def test_var_mal_formada_se_senala(self):
        self.assertIn("var=Color", parsear_lineas(f"{URL} 10 2 var=Color")[0]["error_formato"])


class TestPrecio(unittest.TestCase):
    def test_sube_a_99_sin_bajar_nunca(self):
        for entrada, esperado in ((32.40, 32.99), (32.99, 32.99), (33.00, 33.99), (10.01, 10.99), (0.5, 0.99)):
            self.assertEqual(precio_psicologico(entrada), esperado, entrada)
            self.assertGreaterEqual(precio_psicologico(entrada), entrada)


class TestPagina(unittest.TestCase):
    def test_json_ld_producto_con_imagenes(self):
        html = ('<html><head><title>X | AliExpress</title><script type="application/ld+json">'
                '{"@type":"Product","name":"Peine eléctrico","image":["https://cdn.x/1.jpg","//cdn.x/2.jpg"]}'
                '</script></head></html>')
        d = extraer_datos_pagina(html, "https://es.aliexpress.com/item/1.html")
        self.assertEqual(d["titulo"], "Peine eléctrico")
        self.assertEqual(d["imagenes"], ["https://cdn.x/1.jpg", "https://cdn.x/2.jpg"])

    def test_open_graph_y_limpieza_de_sufijo(self):
        html = ('<meta property="og:title" content="Lámpara LED - AliExpress"><meta property="og:image" '
                'content="https://cdn.x/l.jpg"><meta property="og:image" content="https://cdn.x/l.jpg">')
        d = extraer_datos_pagina(html)
        self.assertEqual((d["titulo"], d["imagenes"]), ("Lámpara LED", ["https://cdn.x/l.jpg"]))

    def test_captcha_no_aporta_ni_titulo_ni_imagenes(self):
        d = extraer_datos_pagina('<title>Captcha Interception</title><meta property="og:image" content="https://x/y.jpg">')
        self.assertEqual(d, {"titulo": "", "imagenes": []})

    def test_imagenes_solo_http_sin_duplicados_y_maximo_10(self):
        lista = ["data:image/png;base64,AAA", "javascript:x", "https://a/1.jpg", "https://a/1.jpg"] + [f"https://a/{i}.jpg" for i in range(20)]
        r = imagenes_validas(lista)
        self.assertEqual(len(r), 10)
        self.assertTrue(all(u.startswith("https://") for u in r))


class TestVariantesShopify(unittest.TestCase):
    def test_producto_cartesiano_y_payload(self):
        peticiones = []

        def tx(metodo, url, cab, cuerpo, timeout):
            peticiones.append((metodo, url, json.loads(cuerpo) if cuerpo else None))
            return 201, {}, json.dumps({"product": {"id": 555}})

        c = ShopifyClient(env={"SHOPIFY_STORE_URL": "t.myshopify.com", "SHOPIFY_ACCESS_TOKEN": "shpat_x"}, transporte=tx)
        pid = c.create_draft_product("T", "<p>d</p>", 32.99, imagenes=["https://a/1.jpg"],
                                     opciones={"Color": ["Rojo", "Azul"], "Talla": ["S", "M", "L"]})
        self.assertEqual(pid, "555")
        prod = peticiones[0][2]["product"]
        self.assertEqual(prod["status"], "draft")
        self.assertEqual([o["name"] for o in prod["options"]], ["Color", "Talla"])
        self.assertEqual(len(prod["variants"]), 6)
        self.assertEqual(prod["variants"][0], {"price": "32.99", "inventory_management": None,
                                               "option1": "Rojo", "option2": "S"})
        self.assertEqual(prod["images"], [{"src": "https://a/1.jpg"}])

    def test_sin_opciones_una_variante_y_limites(self):
        self.assertEqual(len(ShopifyClient.construir_variantes(1.0, None)[1]), 1)
        with self.assertRaises(ValueError):
            ShopifyClient.construir_variantes(1.0, {"a": ["1"], "b": ["1"], "c": ["1"], "d": ["1"]})
        with self.assertRaises(ValueError):
            ShopifyClient.construir_variantes(1.0, {"a": [str(i) for i in range(11)], "b": [str(i) for i in range(11)]})


class TestImportador(Base):
    def test_falta_envio_es_data_gap_y_no_toca_shopify(self):
        r = self.imp.importar_lote([self.item(envio=None)])[0]
        self.assertEqual(r["status"], "skipped")
        self.assertIn("DATA_GAP_REQUEST", r["error"])
        self.assertEqual(self.shopify.llamadas, [])

    def test_precio_sobre_landed_convertido_y_psicologico(self):
        r = self.imp.importar_lote([self.item()], moneda_costo="USD")[0]
        self.assertEqual(r["status"], "success")
        # (10 + 2) USD × 0,9 = 10,80 EUR landed → ×3 = 32,40 → ,99 = 32,99 (multiplicador 3,05, no baja de x3)
        self.assertEqual(self.shopify.llamadas[0]["precio"], 32.99)
        self.assertEqual(r["validacion"]["costo_landed"], 10.80)
        self.assertGreaterEqual(r["validacion"]["multiplicador"], 3.0)

    def test_sin_precio_psicologico_deja_el_x3_exacto(self):
        self.imp.importar_lote([self.item()], precio_psico=False)
        self.assertEqual(self.shopify.llamadas[0]["precio"], 32.40)

    def test_misma_divisa_no_convierte(self):
        self.shopify.moneda = "USD"
        self.imp._moneda = None
        self.imp.importar_lote([self.item()], moneda_costo="USD", precio_psico=False)
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
        self.imp.importar_lote([self.item(costo=10.0), self.item(url=URL2, costo=5.0, envio=1.0)], precio_psico=False)
        self.assertEqual([c["precio"] for c in self.shopify.llamadas], [32.40, 16.20])

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
        self.nuevo(pagina_fn=pagina("")).importar_lote([self.item()])
        self.assertIn("revisar título", self.shopify.llamadas[0]["titulo"])

    def test_se_registra_en_bd(self):
        self.imp.importar_lote([self.item()])
        self.assertEqual(self.filas(), [(URL, "success")])

    # ── imágenes y variantes ─────────────────────────────────────────────────

    def test_imagenes_de_la_pagina_y_variantes_del_usuario(self):
        imp = self.nuevo(pagina_fn=pagina(imagenes=["https://cdn.x/p1.jpg", "https://cdn.x/p2.jpg"]))
        r = imp.importar_lote([self.item(opciones={"Color": ["Rojo", "Azul"]})])[0]
        c = self.shopify.llamadas[0]
        self.assertEqual(c["imagenes"], ["https://cdn.x/p1.jpg", "https://cdn.x/p2.jpg"])
        self.assertEqual(c["opciones"], {"Color": ["Rojo", "Azul"]})
        self.assertEqual((r["imagenes"], r["variantes"]), (2, 2))

    def test_las_imagenes_del_usuario_mandan_sobre_las_de_la_pagina(self):
        imp = self.nuevo(pagina_fn=pagina(imagenes=["https://cdn.x/pagina.jpg"]))
        imp.importar_lote([self.item(imagenes=["https://mis.fotos/a.jpg", "data:image/png;base64,AA"])])
        self.assertEqual(self.shopify.llamadas[0]["imagenes"], ["https://mis.fotos/a.jpg"])

    def test_demasiadas_variantes_se_omiten_sin_tocar_shopify(self):
        grande = {"A": [str(i) for i in range(11)], "B": [str(i) for i in range(11)]}
        r = self.imp.importar_lote([self.item(opciones=grande)])[0]
        self.assertEqual(r["status"], "skipped")
        self.assertEqual(self.shopify.llamadas, [])

    def test_plataforma_desconocida_no_se_descarga(self):
        visitadas = []
        imp = self.nuevo(pagina_fn=lambda u: visitadas.append(u) or {})
        imp.importar_lote([self.item(url="http://192.168.1.10/admin")])
        self.assertEqual(visitadas, [])

    # ── previsualizar ────────────────────────────────────────────────────────

    def test_previsualizar_no_crea_nada(self):
        r = self.imp.previsualizar([self.item(opciones={"Color": ["Rojo", "Azul"]})])[0]
        self.assertEqual((r["status"], r["pvp"], r["variantes"]), ("preview", 32.99, 2))
        self.assertEqual(self.shopify.llamadas, [])
        self.assertEqual(self.filas(), [])

    def test_previsualizar_avisa_de_duplicados(self):
        self.imp.importar_lote([self.item()])
        self.assertEqual(self.imp.previsualizar([self.item()])[0]["status"], "skipped")

    # ── Google Sheets ────────────────────────────────────────────────────────

    def test_escribe_en_la_hoja_con_el_coste_landed(self):
        filas = []
        imp = self.nuevo(hoja_fn=filas.append)
        r = imp.importar_lote([self.item()], sincronizar_hoja=True)[0]
        self.assertEqual(r["hoja"], "ok")
        p = filas[0]
        self.assertEqual((p["sku"], p["costo_origen"], p["pvp"]), ("1005006789123456", 10.80, 32.99))
        self.assertIn("borrador 1001", p["categoria"])
        # la hoja calcula pvp/costo: con el landed convertido coincide con el multiplicador validado
        self.assertEqual(round(p["pvp"] / p["costo_origen"], 2), r["validacion"]["multiplicador"])

    def test_sin_sincronizar_no_toca_la_hoja(self):
        filas = []
        r = self.nuevo(hoja_fn=filas.append).importar_lote([self.item()])[0]
        self.assertEqual((filas, r["hoja"]), ([], "omitida"))

    def test_fallo_de_sheets_no_deshace_el_borrador(self):
        def roto(_):
            raise RuntimeError("invalid_grant")
        r = self.nuevo(hoja_fn=roto).importar_lote([self.item()], sincronizar_hoja=True)[0]
        self.assertEqual(r["status"], "success")
        self.assertIn("invalid_grant", r["hoja"])

    def test_solo_los_creados_van_a_la_hoja(self):
        filas = []
        self.nuevo(hoja_fn=filas.append).importar_lote([self.item(envio=None)], sincronizar_hoja=True)
        self.assertEqual(filas, [])


class TestWeb(Base):
    def setUp(self):
        super().setUp()
        from fastapi.testclient import TestClient
        import app.routes.importacion as ruta
        import app.services.dashboard_server as ds
        self.ruta = ruta
        self.c = TestClient(ds.app)
        patches = [
            mock.patch.object(ruta, "DB_PATH", self.db_path),
            mock.patch.object(ruta, "_crear_importador", lambda: self.imp),
            mock.patch.object(ruta, "estado_credenciales",
                              lambda: {"configurada": True, "faltan": [], "aviso": "", "tienda": "t", "modo": "token"}),
        ]
        for p in patches:
            p.start()

    def post(self, ruta, **cuerpo):
        return self.c.post(f"/api/importacion/{ruta}", json={"texto": f"{URL} 10 2", **cuerpo})

    def test_pagina_y_estado(self):
        r = self.c.get("/importacion")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Importación", r.text)
        est = self.c.get("/api/importacion/estado").json()
        self.assertTrue(est["shopify"]["configurada"])
        self.assertEqual(est["max_productos"], 50)

    def test_previsualizar_e_importar_e_historial(self):
        pv = self.post("previsualizar").json()["resultados"][0]
        self.assertEqual((pv["status"], pv["pvp"]), ("preview", 32.99))
        self.assertEqual(self.shopify.llamadas, [])
        r = self.post("importar", etiqueta_lote="lote-1")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["creados"], 1)
        self.assertNotIn("guardar", r.json()["resultados"][0])
        h = self.c.get("/api/importacion/historial").json()["historial"]
        self.assertEqual((h[0]["url_origen"], h[0]["status"]), (URL, "success"))

    def test_validaciones_de_entrada(self):
        self.assertEqual(self.c.post("/api/importacion/importar", json={"texto": "  \n "}).status_code, 422)
        self.assertEqual(self.post("importar", moneda_costo="DOLARES").status_code, 422)
        self.assertEqual(self.post("importar", etiqueta_lote="con espacios y ñ!").status_code, 422)
        masivo = "\n".join(f"https://es.aliexpress.com/item/{i}.html 5 1" for i in range(51))
        self.assertEqual(self.c.post("/api/importacion/importar", json={"texto": masivo}).status_code, 422)

    def test_shopify_sin_configurar_da_422_claro(self):
        with mock.patch.object(self.ruta, "estado_credenciales",
                               lambda: {"configurada": False, "faltan": ["SHOPIFY_CLIENT_ID"], "aviso": ""}):
            r = self.post("importar")
        self.assertEqual(r.status_code, 422)
        self.assertIn("SHOPIFY_CLIENT_ID", r.json()["detail"])


if __name__ == "__main__":
    unittest.main()
