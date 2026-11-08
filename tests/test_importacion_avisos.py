"""Importación de CSV (Meta/Shopify) y avisos fuera de la app. Sin red, sin PowerShell real; BD temporal."""
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import DatabaseConnection
from app.services import alerts, metrics_import as mi, notifier
from app.services import business_metrics as bm
from app.services import product_catalog as pc


def dia(n):
    return (date.today() - timedelta(days=n)).isoformat()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        (Path(self.tmp.name) / "data").mkdir()
        self.db = str(Path(self.tmp.name) / "data" / "t.db")
        self.cfg = str(Path(self.tmp.name) / "data" / "youtube_channels.json")
        Path(self.cfg).write_text("[]", encoding="utf-8")
        DatabaseConnection(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def filas(self, plataforma=None):
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            sql = "SELECT * FROM metricas_diarias" + (" WHERE plataforma = ?" if plataforma else "") + " ORDER BY fecha"
            return [dict(r) for r in conn.execute(sql, (plataforma,) if plataforma else ())]


META_ES = (f"Día;Nombre de la campaña;Importe gastado (EUR);Compras;Valor de conversión de compras;"
           f"Visitas a la página de destino\n"
           f"{dia(2)};Camp A;\"12,50\";1;\"29,90\";40\n"
           f"{dia(2)};Camp B;\"7,50\";0;;22\n"
           f"{dia(1)};Camp A;\"30,00\";2;\"59,80\";55\n"
           f";Total;\"50,00\";3;\"89,70\";117\n").encode("utf-8")

META_EN = (f"Day,Campaign name,Amount spent (USD),Purchases,Purchases conversion value,Landing page views\n"
           f"{dia(1)},Camp A,\"1,234.50\",10,\"2,500.00\",400\n").encode("utf-8")

SHOPIFY_ES = (f"Día,Pedidos,Ventas brutas,Ventas netas,Ventas totales,Sesiones\n"
              f"{dia(2)},2,\"70,00\",\"65,00\",\"75,00\",120\n"
              f"{dia(1)},3,\"100,00\",\"95,00\",\"110,00\",150\n").encode("utf-8")


class ParseoTests(unittest.TestCase):
    def test_meta_espanol_con_punto_y_coma_y_coma_decimal(self):
        r = mi.parsear(META_ES)
        self.assertEqual((r["plataforma"], r["moneda"], r["delimitador"]), ("meta", "EUR", ";"))
        d = {x["fecha"]: x for x in r["dias"]}
        self.assertEqual(d[dia(2)]["gasto_ads"], 20.0)                  # 12,50 + 7,50 de dos campañas
        self.assertEqual(d[dia(2)]["visitantes"], 62)
        self.assertEqual(d[dia(2)]["compras_meta"], 1)
        self.assertEqual(d[dia(1)]["valor_meta"], 59.8)
        self.assertEqual(r["totales"]["gasto_ads"], 50.0)
        self.assertEqual({c["nombre"] for c in r["campanas"]}, {"Camp A", "Camp B"})
        self.assertTrue(any("sin fecha válida" in a for a in r["avisos"]))   # la fila «Total» se ignora

    def test_meta_ingles_con_miles(self):
        r = mi.parsear(META_EN)
        self.assertEqual(r["moneda"], "USD")
        self.assertEqual(r["dias"][0]["gasto_ads"], 1234.5)
        self.assertEqual(r["dias"][0]["valor_meta"], 2500.0)

    def test_filtro_de_campanas(self):
        r = mi.parsear(META_ES, campanas=["Camp A"])
        self.assertEqual(r["totales"]["gasto_ads"], 42.5)
        self.assertEqual(len(r["campanas"]), 2)                            # el listado muestra todas
        with self.assertRaisesRegex(ValueError, "campañas elegidas"):
            mi.parsear(META_ES, campanas=["No existe"])

    def test_shopify_elige_ventas_totales_y_avisa(self):
        r = mi.parsear(SHOPIFY_ES)
        self.assertEqual(r["plataforma"], "shopify")
        self.assertEqual(r["ingresos_columna"], "Ventas totales")
        self.assertEqual(r["dias"][1]["ingresos"], 110.0)
        self.assertEqual(r["dias"][1]["pedidos"], 3)
        self.assertTrue(any("envío e impuestos" in a for a in r["avisos"]))

    def test_sin_desglose_diario_se_explica(self):
        csv = (f"Inicio del informe,Fin del informe,Nombre de la campaña,Importe gastado (EUR)\n"
               f"{dia(5)},{dia(1)},Camp A,100\n").encode()
        with self.assertRaisesRegex(ValueError, "desglose por día"):
            mi.parsear(csv)
        ok = (f"Inicio del informe,Fin del informe,Nombre de la campaña,Importe gastado (EUR)\n"
              f"{dia(1)},{dia(1)},Camp A,100\n").encode()
        self.assertEqual(mi.parsear(ok)["dias"][0]["gasto_ads"], 100.0)

    def test_archivo_no_reconocido_y_vacio(self):
        with self.assertRaisesRegex(ValueError, "No reconozco"):
            mi.parsear(b"a,b,c\n1,2,3\n")
        with self.assertRaisesRegex(ValueError, "vac"):
            mi.parsear(b"\n\n")
        with self.assertRaisesRegex(ValueError, "5 MB"):
            mi.parsear(b"x" * (mi.MAX_BYTES + 1))

    def test_codificaciones_y_fechas(self):
        utf16 = META_ES.decode("utf-8").encode("utf-16")
        self.assertEqual(mi.parsear(utf16)["totales"]["gasto_ads"], 50.0)
        cp1252 = META_ES.decode("utf-8").encode("cp1252")
        self.assertEqual(mi.parsear(cp1252)["plataforma"], "meta")
        barras = (f"Día;Importe gastado (EUR)\n{(date.today() - timedelta(days=1)).strftime('%d/%m/%Y')};10,00\n").encode()
        r = mi.parsear(barras)
        self.assertEqual(r["dias"][0]["fecha"], dia(1))
        futuro = (f"Día;Importe gastado (EUR)\n{(date.today() + timedelta(days=3)).isoformat()};10,00\n"
                  f"{dia(1)};5,00\n").encode()
        self.assertTrue(any("futura" in a for a in mi.parsear(futuro)["avisos"]))

    def test_numeros(self):
        for texto, coma, esperado in [("1.234,56", False, 1234.56), ("1,234.56", False, 1234.56), ("12,50", True, 12.5),
                                      ("1,234", False, 1234.0), ("1,234", True, 1.234), ("€ 12,5", True, 12.5),
                                      ("1.234", True, 1234.0), ("12.5", False, 12.5), ("-", False, None), ("", False, None)]:
            self.assertEqual(mi._numero(texto, coma), esperado, texto)


class ImportacionBDTests(Base):
    def test_previsualizar_no_escribe(self):
        r = mi.previsualizar(self.db, mi.parsear(META_ES))
        self.assertEqual((r["nuevos"], r["actualizados"]), (2, 0))
        self.assertEqual(self.filas(), [])

    def test_meta_importa_solo_gasto_y_visitas_por_defecto(self):
        res = mi.aplicar(self.db, mi.parsear(META_ES))
        self.assertEqual((res["nuevos"], res["actualizados"]), (2, 0))
        f = self.filas("meta")
        self.assertEqual(f[0]["gasto_ads"], 20.0)
        self.assertEqual(f[0]["ingresos"], 0)                      # lo que declara Meta NO entra por defecto
        self.assertEqual(f[0]["pedidos"], 0)
        self.assertEqual(f[0]["visitantes"], 62)
        self.assertTrue(f[0]["correlation_id"])

    def test_meta_con_ingresos_declarados_avisa(self):
        r = mi.previsualizar(self.db, mi.parsear(META_ES), usar_ingresos_meta=True)
        self.assertTrue(any("DECLARA Meta" in a for a in r["avisos"]))
        mi.aplicar(self.db, mi.parsear(META_ES), usar_ingresos_meta=True)
        self.assertEqual(self.filas("meta")[1]["ingresos"], 59.8)

    def test_reimportar_es_idempotente_y_no_pisa_lo_tecleado(self):
        mi.aplicar(self.db, mi.parsear(META_ES))
        with sqlite3.connect(self.db) as conn:                      # el usuario completa a mano coste y devoluciones
            conn.execute("UPDATE metricas_diarias SET cogs_pagado = 33, devoluciones = 4, presupuesto_diario = 50, "
                         "notas = 'mi nota'")
        res = mi.aplicar(self.db, mi.parsear(META_ES))
        self.assertEqual((res["nuevos"], res["actualizados"]), (0, 2))
        f = self.filas("meta")
        self.assertEqual(len(f), 2)
        self.assertEqual((f[0]["cogs_pagado"], f[0]["devoluciones"], f[0]["presupuesto_diario"], f[0]["notas"]),
                         (33, 4, 50, "mi nota"))

    def test_meta_mas_shopify_dan_roas_real(self):
        mi.aplicar(self.db, mi.parsear(META_ES))
        mi.aplicar(self.db, mi.parsear(SHOPIFY_ES))
        r = bm.resumen(self.db, 7)
        self.assertEqual(r["gasto_ads"], 50.0)
        self.assertEqual(r["ingresos"], 185.0)                       # 75 + 110: reales de Shopify, no los de Meta
        self.assertEqual(r["roas"], 3.7)
        self.assertEqual(r["pedidos"], 5)

    def test_avisa_si_los_ingresos_se_sumarian_dos_veces(self):
        bm.registrar_dia(self.db, {"fecha": dia(1), "plataforma": "otros", "gasto_ads": 0, "ingresos": 110, "pedidos": 3})
        r = mi.previsualizar(self.db, mi.parsear(SHOPIFY_ES))
        self.assertTrue(any("SUMARÍAN" in a for a in r["avisos"]))
        bm.registrar_dia(self.db, {"fecha": dia(1), "plataforma": "otros", "gasto_ads": 9, "ingresos": 0})
        self.assertTrue(any("gasto registrado en otra plataforma" in a
                            for a in mi.previsualizar(self.db, mi.parsear(META_ES))["avisos"]))

    def test_estimar_cogs_solo_si_hay_coste_y_no_pisa_lo_manual(self):
        p = pc.crear(self.db, {"nombre": "Pelota", "costo_origen": 5, "costo_envio": 2, "pvp": 15})
        sin = mi.previsualizar(self.db, mi.parsear(SHOPIFY_ES), estimar_cogs=True)    # sin producto
        self.assertFalse(sin["cogs_estimado"])
        self.assertTrue(any("no se estima" in a.lower() for a in sin["avisos"]))
        mi.aplicar(self.db, mi.parsear(SHOPIFY_ES), producto_id=p["id"], estimar_cogs=True)
        f = self.filas("shopify")
        self.assertEqual([x["cogs_pagado"] for x in f], [14.0, 21.0])               # pedidos × (5 + 2)
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE metricas_diarias SET cogs_pagado = 99 WHERE fecha = ?", (dia(2),))
        mi.aplicar(self.db, mi.parsear(SHOPIFY_ES), producto_id=p["id"], estimar_cogs=True)
        self.assertEqual([x["cogs_pagado"] for x in self.filas("shopify")], [99.0, 21.0])

    def test_sin_estimar_avisa_del_coste(self):
        r = mi.previsualizar(self.db, mi.parsear(SHOPIFY_ES))
        self.assertTrue(any("coste pagado al proveedor" in a for a in r["avisos"]))

    def test_producto_inexistente_y_atomicidad(self):
        with self.assertRaisesRegex(ValueError, "no existe"):
            mi.aplicar(self.db, mi.parsear(META_ES), producto_id=999)
        self.assertEqual(self.filas(), [])

    def test_importar_resuelve_alertas_de_datos_faltantes(self):
        mi.aplicar(self.db, mi.parsear(META_ES))
        bm.registrar_caja(self.db, {"fecha": dia(0), "saldo_cuenta": 1000})
        alerts.evaluar(self.db, self.cfg)
        self.assertIn("roas_sangrado", {a["clave"] for a in alerts.listar(self.db)["items"]})   # gasto sin ingresos
        mi.aplicar(self.db, mi.parsear(SHOPIFY_ES))
        alerts.evaluar(self.db, self.cfg)
        self.assertNotIn("roas_sangrado", {a["clave"] for a in alerts.listar(self.db)["items"]})


class AvisosTests(Base):
    ENTORNO = {"GEM_OS_AVISOS": "1", "MAKE_WEBHOOK_ALERTAS": "https://hook.eu1.make.com/secreto123",
               "GEM_OS_AVISOS_NIVEL": "aviso", "GEM_OS_AVISOS_SILENCIO": "23-7"}

    def setUp(self):
        super().setUp()
        self.env = mock.patch.dict(os.environ, self.ENTORNO)
        self.env.start()
        self.toasts, self.hooks = [], []
        self.toast_ok = self.hook_ok = True
        self.p1 = mock.patch.object(notifier, "enviar_toast", side_effect=self._toast)
        self.p2 = mock.patch.object(notifier, "enviar_webhook", side_effect=self._hook)
        self.p3 = mock.patch.object(notifier.sys, "platform", "win32")
        for p in (self.p1, self.p2, self.p3):
            p.start()

    def tearDown(self):
        for p in (self.p1, self.p2, self.p3):
            p.stop()
        self.env.stop()
        super().tearDown()

    def _toast(self, titulo, texto, enlace=""):
        self.toasts.append(titulo)
        return {"ok": self.toast_ok, "motivo": None if self.toast_ok else "falló"}

    def _hook(self, payload):
        self.hooks.append(payload)
        return {"ok": self.hook_ok, "motivo": None if self.hook_ok else "HTTP 500"}

    def alerta(self, clave, nivel, titulo="T"):
        with sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO alertas (clave, nivel, titulo, detalle, enlace) VALUES (?,?,?,?,?)",
                         (clave, nivel, titulo, "detalle", "/negocio"))

    def mediodia(self):
        return datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)

    def test_avisa_una_sola_vez_y_solo_nivel_aviso_o_mas(self):
        self.alerta("a", "aviso", "Aviso A")
        self.alerta("b", "info", "Info B")
        r = notifier.enviar_pendientes(self.db, self.mediodia())
        self.assertEqual(r["enviadas"], 1)
        self.assertEqual(len(self.hooks), 1)
        self.assertEqual(self.hooks[0]["alertas"][0]["titulo"], "Aviso A")
        self.assertEqual(notifier.enviar_pendientes(self.db, self.mediodia())["enviadas"], 0)   # ya avisada
        self.assertEqual(len(self.hooks), 1)

    def test_el_payload_sirve_para_email(self):
        self.alerta("c", "critico", "Caja crítica")
        notifier.enviar_pendientes(self.db, self.mediodia())
        p = self.hooks[0]
        self.assertIn("CRÍTICA", p["asunto"])
        self.assertIn("[CRÍTICA] Caja crítica — detalle", p["mensaje"])
        self.assertTrue(p["alertas"][0]["enlace"].endswith("/negocio"))

    def test_silencio_nocturno_solo_deja_pasar_criticas(self):
        self.alerta("a", "aviso")
        self.alerta("b", "critico")
        noche = self.mediodia().replace(hour=2)
        self.assertEqual(notifier.enviar_pendientes(self.db, noche)["enviadas"], 1)
        self.assertEqual(self.hooks[0]["alertas"][0]["nivel"], "critico")
        self.assertEqual(notifier.enviar_pendientes(self.db, self.mediodia())["enviadas"], 1)  # la del aviso, de día

    def test_recordatorio_de_criticas_sin_ver(self):
        self.alerta("b", "critico")
        notifier.enviar_pendientes(self.db, self.mediodia())
        self.assertEqual(notifier.enviar_pendientes(self.db, self.mediodia() + timedelta(hours=5))["enviadas"], 0)
        self.assertEqual(notifier.enviar_pendientes(self.db, self.mediodia() + timedelta(hours=13))["enviadas"], 1)
        alerts.marcar_vista(self.db)                                           # vista → deja de recordar
        self.assertEqual(notifier.enviar_pendientes(self.db, self.mediodia() + timedelta(hours=30))["enviadas"], 0)

    def test_si_falla_un_canal_pero_otro_entrega_se_da_por_avisada(self):
        self.toast_ok = False
        self.alerta("a", "aviso")
        self.assertEqual(notifier.enviar_pendientes(self.db, self.mediodia())["enviadas"], 1)

    def test_si_fallan_todos_se_reintenta_despues(self):
        self.toast_ok = self.hook_ok = False
        self.alerta("a", "aviso")
        self.assertEqual(notifier.enviar_pendientes(self.db, self.mediodia())["enviadas"], 0)
        self.toast_ok = self.hook_ok = True
        self.assertEqual(notifier.enviar_pendientes(self.db, self.mediodia())["enviadas"], 1)

    def test_reaparecer_vuelve_a_avisar(self):
        self.alerta("a", "aviso")
        notifier.enviar_pendientes(self.db, self.mediodia())
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE alertas SET resuelta_at = '2026-01-01T00:00:00'")
        alerts._LOCK  # el motor real reabre con evaluar(); aquí se simula su UPDATE
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE alertas SET resuelta_at = NULL, vista_at = NULL, notificada_at = NULL")
        self.assertEqual(notifier.enviar_pendientes(self.db, self.mediodia())["enviadas"], 1)

    def test_evaluar_real_reabre_y_borra_notificada(self):
        bm.registrar_dia(self.db, {"fecha": dia(0), "gasto_ads": 100, "ingresos": 10, "pedidos": 1})
        bm.registrar_caja(self.db, {"fecha": dia(0), "saldo_cuenta": 10})
        alerts.evaluar(self.db, self.cfg)
        notifier.enviar_pendientes(self.db, self.mediodia())
        antes = len(self.hooks)
        bm.registrar_caja(self.db, {"fecha": dia(0), "saldo_cuenta": 90000})
        bm.registrar_dia(self.db, {"fecha": dia(0), "gasto_ads": 100, "ingresos": 500, "pedidos": 5})
        alerts.evaluar(self.db, self.cfg)                                       # se resuelven
        bm.registrar_caja(self.db, {"fecha": dia(0), "saldo_cuenta": 10})
        bm.registrar_dia(self.db, {"fecha": dia(0), "gasto_ads": 100, "ingresos": 10, "pedidos": 1})
        alerts.evaluar(self.db, self.cfg)                                       # reaparecen
        notifier.enviar_pendientes(self.db, self.mediodia())
        self.assertGreater(len(self.hooks), antes)

    def test_muchas_alertas_un_solo_toast_resumen(self):
        for i in range(5):
            self.alerta(f"k{i}", "aviso", f"Aviso {i}")
        notifier.enviar_pendientes(self.db, self.mediodia())
        self.assertEqual(len(self.hooks), 1)                                    # una sola llamada a Make

    def test_desactivado_o_sin_canal_no_hace_nada(self):
        self.alerta("a", "aviso")
        with mock.patch.dict(os.environ, {"GEM_OS_AVISOS": "0"}):
            self.assertEqual(notifier.enviar_pendientes(self.db, self.mediodia())["enviadas"], 0)
        with mock.patch.dict(os.environ, {"MAKE_WEBHOOK_ALERTAS": ""}), mock.patch.object(notifier.sys, "platform", "linux"):
            self.assertEqual(notifier.enviar_pendientes(self.db, self.mediodia())["enviadas"], 0)
        self.assertEqual(self.toasts + self.hooks, [])

    def test_configuracion_nunca_filtra_la_url(self):
        cfg = notifier.configuracion()
        self.assertTrue(cfg["make"]["configurado"])
        self.assertNotIn("secreto123", json.dumps(cfg))
        with mock.patch.dict(os.environ, {"MAKE_WEBHOOK_ALERTAS": "http://inseguro.example/x"}):
            self.assertFalse(notifier.configuracion()["make"]["configurado"])    # solo https

    def test_horas_de_silencio(self):
        h = lambda x: datetime(2026, 11, 8, x, 0)
        self.assertTrue(notifier.en_silencio(h(23)) and notifier.en_silencio(h(3)))
        self.assertFalse(notifier.en_silencio(h(7)) or notifier.en_silencio(h(12)))
        with mock.patch.dict(os.environ, {"GEM_OS_AVISOS_SILENCIO": "0-0"}):
            self.assertFalse(notifier.en_silencio(h(3)))
        with mock.patch.dict(os.environ, {"GEM_OS_AVISOS_SILENCIO": "basura"}):
            self.assertTrue(notifier.en_silencio(h(3)))                           # valor inválido → 23-7

    def test_prueba_usa_los_canales_activos(self):
        r = notifier.enviar_prueba()
        self.assertTrue(r["ok"])
        self.assertEqual(set(r["canales"]), {"windows", "make"})
        with mock.patch.dict(os.environ, {"GEM_OS_AVISOS": "0"}):
            self.assertFalse(notifier.enviar_prueba()["ok"])


class WebhookRealTests(unittest.TestCase):
    def test_solo_https_y_exito_2xx_sin_registrar_la_url(self):
        with mock.patch.dict(os.environ, {"MAKE_WEBHOOK_ALERTAS": "https://hook.eu1.make.com/abc"}):
            with mock.patch("requests.post", return_value=mock.Mock(status_code=200)) as post:
                self.assertTrue(notifier.enviar_webhook({"a": 1})["ok"])
                self.assertFalse(post.call_args.kwargs["allow_redirects"])
            with mock.patch("requests.post", return_value=mock.Mock(status_code=500)):
                self.assertEqual(notifier.enviar_webhook({})["motivo"], "HTTP 500")
            with mock.patch("requests.post", side_effect=ConnectionError("https://hook.eu1.make.com/abc")):
                r = notifier.enviar_webhook({})
                self.assertNotIn("make.com", json.dumps(r))                       # el error no arrastra la URL
        with mock.patch.dict(os.environ, {"MAKE_WEBHOOK_ALERTAS": ""}):
            self.assertFalse(notifier.enviar_webhook({})["ok"])


if __name__ == "__main__":
    unittest.main()
