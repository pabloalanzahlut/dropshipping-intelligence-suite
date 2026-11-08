"""Conexión con Shopify y AutoDS: credenciales, cliente, sincronización, estadísticas y contexto del agente.
Sin red: Shopify se simula con un transporte falso; BD temporal."""
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import DatabaseConnection
from app.services import autods_import as ai
from app.services import shopify_client as sc
from app.services import store_context, tienda_store

ENV_CC = {"SHOPIFY_STORE_URL": "https://Mi-Tienda.myshopify.com/admin", "SHOPIFY_CLIENT_ID": "cid123",
          "SHOPIFY_CLIENT_SECRET": "shpss_secreto"}
CLAVES = ("SHOPIFY_STORE_URL", "SHOPIFY_CLIENT_ID", "SHOPIFY_CLIENT_SECRET", "SHOPIFY_ACCESS_TOKEN",
          "SHOPIFY_API_VERSION", "SHOPIFY_SYNC_METRICAS")


def entorno(**valores):
    """os.environ sin ninguna variable SHOPIFY_* salvo las indicadas."""
    base = {k: v for k, v in os.environ.items() if k not in CLAVES}
    base.update(valores)
    return mock.patch.dict(os.environ, base, clear=True)


AYER = (datetime.now(timezone.utc) - timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
FECHA_AYER = AYER.astimezone(sc._zona_dummy if hasattr(sc, "_zona_dummy") else timezone.utc).date().isoformat()


def money(x):
    return {"shopMoney": {"amount": f"{x:.2f}", "currencyCode": "EUR"}}


def pedido(num, total, lineas, cancelado=False, reembolsado=0.0, impuestos=0.0, pais="ES"):
    return {
        "id": f"gid://shopify/Order/{num}", "name": f"#{num}", "createdAt": AYER.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cancelledAt": "2026-01-01T00:00:00Z" if cancelado else None, "sourceName": "web",
        "displayFinancialStatus": "PAID", "displayFulfillmentStatus": "UNFULFILLED",
        "totalPriceSet": money(total), "subtotalPriceSet": money(total), "totalDiscountsSet": money(0),
        "totalShippingPriceSet": money(0), "totalTaxSet": money(impuestos), "totalRefundedSet": money(reembolsado),
        "shippingAddress": {"countryCodeV2": pais},
        "lineItems": {"pageInfo": {"hasNextPage": False}, "nodes": [
            {"id": f"gid://shopify/LineItem/{num}{i}", "title": t, "sku": s, "quantity": q,
             "originalUnitPriceSet": money(p), "variant": {"id": f"gid://shopify/ProductVariant/{v}"}}
            for i, (t, s, q, p, v) in enumerate(lineas)]},
    }


PEDIDOS = [
    pedido(1001, 30, [("Pelota gatos", "PEL-1", 2, 15, 1)]),
    pedido(1002, 15, [("Pelota gatos", "PEL-1", 1, 15, 1)], reembolsado=15),
    pedido(1003, 20, [("Lámpara luna", "LAM-1", 1, 20, 2)], cancelado=True),
    pedido(1004, 40, [("Lámpara luna", "LAM-1", 1, 40, 2)], impuestos=6),
]
VARIANTES = [
    {"id": "gid://shopify/ProductVariant/1", "sku": "PEL-1", "title": "Default", "price": "15.00",
     "inventoryQuantity": 10, "product": {"id": "gid://shopify/Product/10", "title": "Pelota gatos",
                                           "status": "ACTIVE", "vendor": "GEM"},
     "inventoryItem": {"unitCost": {"amount": "5.00", "currencyCode": "EUR"}}},
    {"id": "gid://shopify/ProductVariant/2", "sku": "LAM-1", "title": "Default", "price": "40.00",
     "inventoryQuantity": 3, "product": {"id": "gid://shopify/Product/20", "title": "Lámpara luna",
                                          "status": "ACTIVE", "vendor": "GEM"}, "inventoryItem": {"unitCost": None}},
    {"id": "gid://shopify/ProductVariant/3", "sku": "OLD-1", "title": "Default", "price": "9.00",
     "inventoryQuantity": 0, "product": {"id": "gid://shopify/Product/30", "title": "Sin ventas",
                                          "status": "ACTIVE", "vendor": "GEM"}, "inventoryItem": {"unitCost": None}},
]


class ShopifyFalso:
    """Transporte falso: responde a OAuth y a las consultas GraphQL por su contenido."""

    def __init__(self, pedidos=PEDIDOS, variantes=VARIANTES, scopes=("read_orders", "read_products", "read_inventory"),
                 estado_graphql=200, errores=None):
        self.pedidos, self.variantes, self.scopes = pedidos, variantes, list(scopes)
        self.estado_graphql, self.errores = estado_graphql, list(errores or [])
        self.llamadas = []
        self.tokens = 0

    def __call__(self, metodo, url, cab, cuerpo, timeout):
        self.llamadas.append((metodo, url, dict(cab), cuerpo))
        if url.endswith("/admin/oauth/access_token"):
            self.tokens += 1
            return 200, {}, json.dumps({"access_token": f"tok{self.tokens}", "scope": ",".join(self.scopes),
                                         "expires_in": 86399})
        if self.estado_graphql != 200:
            return self.estado_graphql, {}, "{}"
        cuerpo_json = json.loads(cuerpo)
        q, v = cuerpo_json["query"], cuerpo_json["variables"]
        if self.errores:
            return 200, {}, json.dumps({"errors": [self.errores.pop(0)]})
        if "currentAppInstallation" in q:
            return 200, {}, json.dumps({"data": {"currentAppInstallation": {
                "accessScopes": [{"handle": s} for s in self.scopes]}}})
        if "shop {" in q:
            return 200, {}, json.dumps({"data": {"shop": {
                "name": "Mi Tienda", "myshopifyDomain": "mi-tienda.myshopify.com", "currencyCode": "EUR",
                "ianaTimezone": "Europe/Madrid", "plan": {"displayName": "Basic"}}}})
        if "productVariants" in q:
            return 200, {}, json.dumps({"data": {"productVariants": {
                "pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": self.variantes}}})
        if "orders(" in q:
            return 200, {}, json.dumps({"data": {"orders": {
                "pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": self.pedidos}}})
        return 200, {}, json.dumps({"data": {}})

    def graphql(self):
        return [c for c in self.llamadas if c[1].endswith("/graphql.json")]


def cliente(**kw):
    tx = ShopifyFalso(**{k: kw.pop(k) for k in list(kw) if k in ("pedidos", "variantes", "scopes", "estado_graphql", "errores")})
    return sc.ShopifyClient(env=kw.pop("env", ENV_CC), transporte=tx, dormir=lambda s: None), tx


class CredencialesTests(unittest.TestCase):
    def test_normalizar_tienda(self):
        self.assertEqual(sc.normalizar_tienda("https://Mi-Tienda.myshopify.com/admin"), "mi-tienda.myshopify.com")
        self.assertEqual(sc.normalizar_tienda("mi-tienda"), "mi-tienda.myshopify.com")
        self.assertEqual(sc.normalizar_tienda(""), "")

    def test_secreto_shpss_sin_client_id_se_explica(self):
        c = sc.credenciales({"SHOPIFY_STORE_URL": "jiimqi-ms.myshopify.com", "SHOPIFY_ACCESS_TOKEN": "shpss_abc"})
        self.assertFalse(c["configurada"])
        self.assertEqual(c["modo"], "client_credentials")
        self.assertEqual(c["faltan"], ["SHOPIFY_CLIENT_ID"])
        self.assertIn("shpss_", c["problema"])
        self.assertEqual(c["token"], "")           # NO se usa como token de Admin API

    def test_shpss_mas_client_id_queda_configurada(self):
        c = sc.credenciales({"SHOPIFY_STORE_URL": "jiimqi-ms", "SHOPIFY_ACCESS_TOKEN": "shpss_abc",
                             "SHOPIFY_CLIENT_ID": "x"})
        self.assertTrue(c["configurada"])
        self.assertEqual(c["tienda"], "jiimqi-ms.myshopify.com")

    def test_token_shpat_se_usa_tal_cual(self):
        c = sc.credenciales({"SHOPIFY_STORE_URL": "t", "SHOPIFY_ACCESS_TOKEN": "shpat_zzz"})
        self.assertTrue(c["configurada"])
        self.assertEqual(c["modo"], "token")

    def test_dominio_propio_no_vale(self):
        c = sc.credenciales({"SHOPIFY_STORE_URL": "https://mitienda.com", "SHOPIFY_ACCESS_TOKEN": "shpat_zzz"})
        self.assertFalse(c["configurada"])
        self.assertIn("myshopify.com", c["problema"])

    def test_estado_publico_no_filtra_secretos(self):
        e = sc.estado_credenciales({**ENV_CC, "SHOPIFY_ACCESS_TOKEN": "shpat_zzz"})
        self.assertNotIn("shpss_secreto", json.dumps(e))
        self.assertNotIn("shpat_zzz", json.dumps(e))

    def test_cliente_sin_configurar_lanza_environmenterror(self):
        with self.assertRaises(EnvironmentError):
            sc.ShopifyClient(env={"SHOPIFY_STORE_URL": "t"})


class ClienteTests(unittest.TestCase):
    def test_canje_de_token_una_sola_vez_y_cabecera(self):
        c, tx = cliente()
        c.shop_info()
        c.scopes()
        self.assertEqual(tx.tokens, 1)
        for _, _, cab, _ in tx.graphql():
            self.assertEqual(cab["X-Shopify-Access-Token"], "tok1")
            self.assertNotIn("shpss_secreto", json.dumps(cab))

    def test_401_renueva_el_token_una_vez(self):
        c, tx = cliente()
        c.shop_info()
        llamadas = {"n": 0}
        original = tx.__call__

        def a_veces_401(metodo, url, cab, cuerpo, timeout):
            if url.endswith("/graphql.json"):
                llamadas["n"] += 1
                if llamadas["n"] == 1:
                    return 401, {}, "{}"
            return original(metodo, url, cab, cuerpo, timeout)
        c._tx = a_veces_401
        self.assertEqual(c.shop_info()["nombre"], "Mi Tienda")
        self.assertEqual(tx.tokens, 2)

    def test_errores_http_con_mensaje_claro(self):
        for st, codigo in ((402, "plan"), (403, "permiso"), (404, "tienda"), (401, "auth")):
            c, _ = cliente(env={**ENV_CC}, estado_graphql=st)
            with self.assertRaises(sc.ShopifyError) as cm:
                c.shop_info()
            self.assertEqual(cm.exception.codigo, codigo, st)

    def test_oauth_rechazado(self):
        def rechaza(metodo, url, cab, cuerpo, timeout):
            return 400, {}, json.dumps({"error": "shop_not_permitted"})
        c = sc.ShopifyClient(env=ENV_CC, transporte=rechaza, dormir=lambda s: None)
        with self.assertRaises(sc.ShopifyError) as cm:
            c.shop_info()
        self.assertEqual(cm.exception.codigo, "organizacion")

    def test_throttled_reintenta(self):
        c, tx = cliente(errores=[{"message": "Throttled", "extensions": {"code": "THROTTLED"}}])
        self.assertEqual(c.shop_info()["moneda"], "EUR")

    def test_coste_excesivo_reduce_la_pagina(self):
        c, tx = cliente(errores=[{"message": "too big", "extensions": {"code": "MAX_COST_EXCEEDED"}}])
        pedidos = list(c.iter_pedidos("2026-01-01T00:00:00Z"))
        tamanos = [json.loads(g[3])["variables"]["n"] for g in tx.graphql()]
        self.assertEqual(tamanos, [20, 10])
        self.assertEqual(len(pedidos), 4)

    def test_sin_scope_de_inventario_sigue_sin_coste(self):
        c, tx = cliente(errores=[{"message": "denied", "extensions": {"code": "ACCESS_DENIED"}}])
        vs = list(c.iter_variantes())
        self.assertEqual(len(vs), 3)
        self.assertTrue(any("read_inventory" in a for a in c.avisos))
        self.assertNotIn("unitCost", json.loads(tx.graphql()[-1][3])["query"])

    def test_pedido_normalizado(self):
        c, _ = cliente()
        p = next(iter(c.iter_pedidos("2026-01-01T00:00:00Z")))
        self.assertEqual((p["pedido_id"], p["nombre"], p["total"], p["unidades"]), ("1001", "#1001", 30.0, 2))
        self.assertEqual(p["lineas"][0]["variante_id"], "1")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = os.path.join(self.tmp.name, "t.db")
        DatabaseConnection(self.db)
        self.ayer = tienda_store._fecha_local(AYER.strftime("%Y-%m-%dT%H:%M:%SZ"), tienda_store._zona("Europe/Madrid"))

    def tearDown(self):
        self.tmp.cleanup()

    def sql(self, q, *a):
        with sqlite3.connect(self.db) as c:
            return c.execute(q, a).fetchall()

    def sync(self, **kw):
        c, tx = cliente(**kw)
        return tienda_store.sincronizar_shopify(self.db, c, dias=30), tx


class SincronizacionTests(Base):
    def test_guarda_pedidos_lineas_y_variantes(self):
        r, _ = self.sync()
        self.assertEqual((r["estado"], r["pedidos"], r["variantes"]), ("ok", 4, 3))
        self.assertEqual(self.sql("SELECT COUNT(*) FROM tienda_lineas")[0][0], 4)
        self.assertEqual(self.sql("SELECT coste FROM tienda_variantes WHERE variante_id='1'")[0][0], 5.0)
        self.assertEqual(self.sql("SELECT estado, terminado_at IS NOT NULL FROM tienda_sync")[0], ("ok", 1))

    def test_resincronizar_no_duplica(self):
        self.sync()
        self.sync()
        self.assertEqual(self.sql("SELECT COUNT(*) FROM tienda_pedidos")[0][0], 4)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM tienda_lineas")[0][0], 4)

    def test_escribe_ingresos_reales_en_metricas_diarias(self):
        self.sync()
        fila = self.sql("SELECT ingresos, pedidos, gasto_ads FROM metricas_diarias WHERE plataforma='shopify' "
                        "AND fecha=?", self.ayer)
        self.assertEqual(fila, [(70.0, 3, 0.0)])           # 30 + (15-15) + 40; el cancelado no cuenta

    def test_no_pisa_campos_manuales(self):
        self.sql  # noqa
        with sqlite3.connect(self.db) as c:
            c.execute("INSERT INTO metricas_diarias (fecha, plataforma, ingresos, pedidos, cogs_pagado, devoluciones) "
                      "VALUES (?, 'shopify', 1, 1, 7, 2)", (self.ayer,))
        self.sync()
        self.assertEqual(self.sql("SELECT ingresos, cogs_pagado, devoluciones FROM metricas_diarias "
                                  "WHERE plataforma='shopify' AND fecha=?", self.ayer), [(70.0, 7.0, 2.0)])

    def test_no_cuenta_dos_veces_si_otra_plataforma_declara_ingresos(self):
        with sqlite3.connect(self.db) as c:
            c.execute("INSERT INTO metricas_diarias (fecha, plataforma, ingresos, gasto_ads) VALUES (?, 'meta', 50, 20)",
                      (self.ayer,))
        r, _ = self.sync()
        self.assertEqual(self.sql("SELECT COUNT(*) FROM metricas_diarias WHERE plataforma='shopify'")[0][0], 0)
        self.assertEqual(r["metricas_diarias"]["omitidos"], [self.ayer])
        self.assertTrue(any("dos veces" in a for a in r["avisos"]))

    def test_se_puede_desactivar_la_escritura_en_metricas(self):
        c, _ = cliente()
        tienda_store.sincronizar_shopify(self.db, c, dias=30, escribir_metricas=False)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM metricas_diarias")[0][0], 0)

    def test_fallo_de_shopify_queda_registrado_y_no_deja_datos(self):
        c, _ = cliente(estado_graphql=402)
        with self.assertRaises(sc.ShopifyError):
            tienda_store.sincronizar_shopify(self.db, c, dias=30)
        self.assertEqual(self.sql("SELECT estado FROM tienda_sync")[0][0], "error")
        self.assertEqual(self.sql("SELECT COUNT(*) FROM tienda_pedidos")[0][0], 0)
        self.assertFalse(tienda_store.SYNC_LOCK.locked())

    def test_faltan_scopes_de_lectura(self):
        c, _ = cliente(scopes=("read_products",))
        with self.assertRaisesRegex(sc.ShopifyError, "read_orders"):
            tienda_store.sincronizar_shopify(self.db, c, dias=30)

    def test_una_sola_sincronizacion_a_la_vez(self):
        tienda_store.SYNC_LOCK.acquire()
        try:
            c, _ = cliente()
            with self.assertRaisesRegex(RuntimeError, "en curso"):
                tienda_store.sincronizar_shopify(self.db, c, dias=30)
        finally:
            tienda_store.SYNC_LOCK.release()

    def test_aviso_por_mas_de_60_dias_sin_read_all_orders(self):
        c, _ = cliente()
        r = tienda_store.sincronizar_shopify(self.db, c, dias=90)
        self.assertTrue(any("read_all_orders" in a for a in r["avisos"]))


class EstadisticasTests(Base):
    def resumen(self, **kw):
        return tienda_store.resumen(self.db, 30, hoy=date.fromisoformat(self.ayer) + timedelta(days=1), **kw)

    def test_antes_de_sincronizar_no_inventa(self):
        r = self.resumen()
        self.assertEqual((r["pedidos"], r["ingresos_netos"], r["roas_real"], r["margen_real"]), (0, 0, None, None))
        self.assertIn("Shopify todavía no se ha sincronizado.", r["datos_que_faltan"])

    def test_cifras_de_ventas(self):
        self.sync()
        r = self.resumen()
        self.assertEqual((r["pedidos"], r["cancelados"], r["unidades"]), (3, 1, 4))
        self.assertEqual((r["ingresos_brutos"], r["reembolsado"], r["ingresos_netos"]), (85.0, 15.0, 70.0))
        self.assertEqual(r["ticket_medio"], 23.33)
        cd = r["cancelaciones_y_devoluciones"]
        self.assertEqual(cd["pct_real"], round(35 / 105, 4))
        self.assertEqual(cd["estado"], "POR_ENCIMA")                    # 33 % > referencia 10,1 %
        self.assertEqual(r["fees_estimados"], round(85 * 0.04, 2))
        self.assertEqual(r["paises"], [{"pais": "ES", "pedidos": 3}])

    def test_margen_solo_con_coste_conocido_y_dice_la_cobertura(self):
        self.sync()
        r = self.resumen()
        m = r["margen_real"]
        # #1001 (2 uds × 5) y #1002 (1 × 5) tienen coste en Shopify; #1004 no
        self.assertEqual((m["pedidos_con_coste"], m["de_shopify"], m["de_autods"]), (2, 2, 0))
        self.assertEqual((m["ingresos_sin_impuestos"], m["coste_producto_y_envio"]), (30.0, 15.0))
        self.assertEqual(m["margen"], round(30 - 15 - 30 * 0.04, 2))
        self.assertEqual(r["cobertura_coste_pedidos"], round(2 / 3, 4))
        self.assertIsNone(r["beneficio_tras_ads"])                       # cobertura < 95 %: no se afirma
        self.assertTrue(any("67 %" in f for f in r["datos_que_faltan"]))

    def test_roas_real_usa_ingresos_de_shopify_y_gasto_registrado(self):
        self.sync()
        with sqlite3.connect(self.db) as c:
            c.execute("INSERT INTO metricas_diarias (fecha, plataforma, gasto_ads) VALUES (?, 'meta', 35)", (self.ayer,))
        r = self.resumen()
        self.assertEqual((r["gasto_ads"], r["roas_real"]), (35.0, 2.0))
        self.assertEqual(r["roas_estado"]["estado"], "AJUSTADO")

    def test_productos_activos_sin_ventas(self):
        self.sync()
        r = self.resumen()
        self.assertEqual((r["productos_activos"], r["activos_sin_ventas"]), (3, 1))
        self.assertEqual(r["top_productos"][0]["producto"], "Lámpara luna")

    def test_margen_con_coste_real_de_autods(self):
        self.sync()
        csv = (f"Número de pedido;Fecha del pedido;Producto;SKU;Cantidad;Precio de venta;Coste;Coste de envío;Estado;"
               f"Proveedor;Tracking\n#1004;{self.ayer};Lámpara luna;LAM-1;1;40,00;12,00;3,00;Enviado;AliExpress;TRK1\n"
               ).encode("utf-8")
        ai.aplicar(self.db, ai.parsear(csv, "pedidos.csv"))
        r = self.resumen()
        m = r["margen_real"]
        self.assertEqual((m["pedidos_con_coste"], m["de_autods"], m["de_shopify"]), (3, 1, 2))
        # base = 30 + 0 + (40 - 6 de impuestos); coste = 15 + 15
        self.assertEqual((m["ingresos_sin_impuestos"], m["coste_producto_y_envio"]), (64.0, 30.0))
        self.assertEqual(m["margen"], round(64 - 30 - 64 * 0.04, 2))
        self.assertEqual(r["cobertura_coste_pedidos"], 1.0)
        self.assertEqual(r["beneficio_tras_ads"], m["margen"])           # sin ads registrados
        self.assertFalse(any("AutoDS sin importar" in f for f in r["datos_que_faltan"]))


class AutodsTests(Base):
    CSV = ("Número de pedido;Fecha del pedido;Producto;SKU;Cantidad;Precio de venta;Coste;Coste de envío;Estado;Proveedor;"
           "Tracking;Columna rara\n"
           "#2001;07/11/2026;Pelota gatos;PEL-1;3;45,00;4,00;1,50;Entregado;AliExpress;TRK9;x\n"
           "#2002;08/11/2026;Lámpara luna;LAM-1;1;40,00;12,00;3,00;Enviado;CJ;;y\n").encode("utf-8")

    def test_csv_en_espanol_con_acentos_y_coma_decimal(self):
        p = ai.parsear(self.CSV, "pedidos.csv")
        self.assertEqual(p["tipo"], "pedidos")
        f = p["filas"][0]
        self.assertEqual((f["pedido_tienda"], f["fecha"], f["cantidad"], f["coste_proveedor"], f["coste_envio"]),
                         ("2001", "2026-11-07", 3, 4.0, 1.5))
        self.assertEqual(p["sin_mapear"], ["Columna rara"])              # lo que no se reconoce se dice, no se adivina
        self.assertTrue(any("DD/MM/AAAA" in a for a in p["avisos"]))

    def test_coste_por_unidad_multiplica_por_la_cantidad(self):
        total = ai.parsear(self.CSV, "p.csv")["filas"][0]["coste_proveedor"]
        unidad = ai.parsear(self.CSV, "p.csv", coste_por_unidad=True)["filas"][0]["coste_proveedor"]
        self.assertEqual((total, unidad), (4.0, 12.0))

    def test_formato_fecha_mdy(self):
        csv = (b"Order Number,Order Date,Product,Quantity,Cost\n#9,11/07/2026,Gadget,1,5.50\n")
        self.assertEqual(ai.parsear(csv, "o.csv", formato_fecha="mdy")["filas"][0]["fecha"], "2026-11-07")
        self.assertEqual(ai.parsear(csv, "o.csv")["filas"][0]["fecha"], "2026-07-11")

    def test_xlsx(self):
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append(["Order Number", "Order Date", "Product", "Quantity", "Cost", "Shipping Cost", "Status"])
        ws.append(["#3001", datetime(2026, 11, 7), "Gadget", 2, 6.5, 1.0, "Shipped"])
        buf = io.BytesIO()
        wb.save(buf)
        p = ai.parsear(buf.getvalue(), "pedidos.xlsx")
        self.assertEqual((p["formato"], p["filas"][0]["fecha"], p["filas"][0]["coste_proveedor"],
                          p["filas"][0]["coste_envio"]), ("xlsx", "2026-11-07", 6.5, 1.0))

    def test_columnas_minimas_o_se_rechaza_explicando(self):
        with self.assertRaisesRegex(ValueError, "No sé si es"):
            ai.parsear(b"Producto;SKU\nA;B\n", "x.csv")
        with self.assertRaisesRegex(ValueError, "DATA_GAP"):
            ai.parsear(b"Fecha;Producto\n2026-11-07;A\n", "x.csv", tipo="pedidos")
        with self.assertRaisesRegex(ValueError, "No reconozco"):
            ai.parsear(b"a,b,c\n1,2,3\n", "x.csv")

    def test_previsualizar_no_escribe_y_reimportar_no_duplica(self):
        p = ai.parsear(self.CSV, "pedidos.csv")
        vista = ai.previsualizar(self.db, p)
        self.assertEqual((vista["filas"], vista["nuevas"]), (2, 2))
        self.assertEqual(self.sql("SELECT COUNT(*) FROM autods_pedidos")[0][0], 0)
        self.assertEqual(ai.aplicar(self.db, p)["nuevas"], 2)
        again = ai.aplicar(self.db, ai.parsear(self.CSV, "pedidos.csv"))
        self.assertTrue(again["duplicado"])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM autods_pedidos")[0][0], 2)

    def test_archivo_solapado_actualiza_sin_duplicar(self):
        ai.aplicar(self.db, ai.parsear(self.CSV, "a.csv"))
        mas = self.CSV + "#2003;09/11/2026;Otro;OT-1;1;10,00;3,00;1,00;Pendiente;CJ;;z\n".encode("utf-8")
        r = ai.aplicar(self.db, ai.parsear(mas, "b.csv"))
        self.assertEqual((r["nuevas"], r["actualizadas"]), (1, 2))
        self.assertEqual(self.sql("SELECT COUNT(*) FROM autods_pedidos")[0][0], 3)

    def test_productos(self):
        csv = b"Title,SKU,Cost,Selling Price,Stock,Supplier\nGadget,G-1,4.5,15,20,CJ\n"
        p = ai.parsear(csv, "prod.csv")
        self.assertEqual((p["tipo"], p["filas"][0]["coste"], p["filas"][0]["stock"]), ("productos", 4.5, 20))
        self.assertEqual(ai.aplicar(self.db, p)["nuevas"], 1)

    def test_resumen_autods(self):
        ai.aplicar(self.db, ai.parsear(self.CSV, "a.csv"))
        r = ai.resumen(self.db, 90, hoy=date(2026, 11, 9))
        self.assertEqual((r["pedidos"], r["unidades"], r["coste_proveedor"], r["coste_envio"]), (2, 4, 16.0, 4.5))
        self.assertEqual(r["con_tracking_pct"], 0.5)


class ContextoAgenteTests(Base):
    def test_sin_conectar_dice_data_gap_y_prohibe_inventar(self):
        with entorno():
            c = store_context.construir(self.db)
        self.assertFalse(c["conectada"])
        self.assertIn("DATA_GAP", c["texto"])
        self.assertIn("no inventes", c["texto"])

    def test_con_datos_cita_cifras_reales_y_lo_que_falta(self):
        self.sync()
        with entorno(**ENV_CC):
            c = store_context.construir(self.db)
        t = c["texto"]
        self.assertTrue(c["conectada"])
        self.assertIn("Pedidos 3 (cancelados 1)", t)
        self.assertIn("70,00 EUR", t)
        self.assertIn("DATA_GAP: No hay gasto en ads", t)
        self.assertIn("DATA_GAP: AutoDS sin importar", t)
        self.assertLess(len(t), 2500)                                    # corto: barato en tokens

    def test_bloque_para_el_prompt(self):
        self.sync()
        with entorno(**ENV_CC):
            b = store_context.bloque_para_prompt(self.db)
        self.assertTrue(b.startswith("CONTEXTO TIENDA"))
        self.assertIn("[TIENDA]", b)
        self.assertIn("no estimes", b)

    def test_no_rompe_el_agente_si_la_bd_falla(self):
        self.assertEqual(store_context.bloque_para_prompt(os.path.join(self.tmp.name, "no_existe", "x.db")), "")


class ConexionTests(Base):
    def test_probar_conexion_ok(self):
        c, _ = cliente()
        with entorno(**ENV_CC):
            r = tienda_store.probar_conexion(c)
        self.assertTrue(r["ok"])
        self.assertEqual(r["tienda"]["nombre"], "Mi Tienda")

    def test_probar_conexion_sin_configurar_explica_que_falta(self):
        with entorno(SHOPIFY_STORE_URL="t.myshopify.com", SHOPIFY_ACCESS_TOKEN="shpss_abc"):
            r = tienda_store.probar_conexion()
        self.assertFalse(r["ok"])
        self.assertEqual(r["faltan"], ["SHOPIFY_CLIENT_ID"])
        self.assertIn("secreto", r["mensaje"])

    def test_probar_conexion_con_permisos_incompletos(self):
        c, _ = cliente(scopes=("read_products",))
        with entorno(**ENV_CC):
            r = tienda_store.probar_conexion(c)
        self.assertFalse(r["ok"])
        self.assertEqual(r["scopes_faltan"], ["read_orders"])

    def test_sync_programada_no_hace_nada_sin_configurar(self):
        with entorno():
            self.assertIsNone(tienda_store.sync_si_configurada(self.db))

    def test_estado_nunca_incluye_secretos(self):
        with entorno(**ENV_CC):
            e = tienda_store.estado(self.db)
        self.assertNotIn("shpss_secreto", json.dumps(e, default=str))
        self.assertEqual(e["autods"]["modo"], "importacion")


if __name__ == "__main__":
    unittest.main()
