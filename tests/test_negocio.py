"""Catálogo de productos y números del negocio (ROAS, caja, escalado). Sin red; BD temporal."""
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import DatabaseConnection
from app.services import business_metrics as bm
from app.services import product_catalog as pc

TODAS_PASAN = {str(n): {"resultado": "pasa", "dato": "ok"} for n in pc.REFUTACIONES}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = os.path.join(self.tmp.name, "t.db")
        DatabaseConnection(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def producto(self, **extra):
        datos = {"nombre": "Pelota gatos", "costo_origen": 5, "costo_envio": 2, "pvp": 15}
        datos.update(extra)
        return pc.crear(self.db, datos)

    def hasta_tienda(self):
        p = self.producto()
        pc.mover(self.db, p["id"], "clasificado")
        pc.guardar_refutaciones(self.db, p["id"], TODAS_PASAN)
        pc.mover(self.db, p["id"], "refutado")
        pc.mover(self.db, p["id"], "validado")
        pc.guardar_demanda(self.db, p["id"], {"visitantes": 400, "clics_comprar": 40, "emails": 12}, True)
        pc.mover(self.db, p["id"], "creativo")
        return pc.mover(self.db, p["id"], "tienda")


class CatalogoTests(Base):
    def test_clasificacion_por_multiplicador(self):
        self.assertEqual([pc.clasificar(x) for x in (1.99, 2.0, 2.99, 3.0, 4.99, 5.0)],
                         ["DISCARD", "COLD", "COLD", "WARM", "WARM", "HOT"])

    def test_no_se_puede_saltar_pasos(self):
        p = self.producto()
        with self.assertRaisesRegex(ValueError, "saltar pasos"):
            pc.mover(self.db, p["id"], "validado")

    def test_clasificar_exige_datos_y_usa_coste_landed(self):
        vacio = pc.crear(self.db, {"nombre": "Sin datos"})
        with self.assertRaisesRegex(ValueError, "Faltan datos"):
            pc.mover(self.db, vacio["id"], "clasificado")
        p = pc.mover(self.db, self.producto()["id"], "clasificado")
        self.assertEqual(p["calculo"]["costo_landed"], 7.0)        # 5 + 2 de envío
        self.assertEqual(p["calculo"]["multiplicador"], 2.14)      # no 3,0 (sobre el producto solo)
        self.assertEqual(p["clasificacion"], "COLD")

    def test_por_debajo_de_2x_se_descarta_solo(self):
        p = pc.mover(self.db, self.producto(pvp=12)["id"], "clasificado")   # 12/7 = 1,71x
        self.assertEqual(p["estado"], "descartado")
        self.assertTrue(p["auto_descartado"])

    def test_refutaciones_veredicto(self):
        self.assertIsNone(pc.veredicto_refutacion({"1": {"resultado": "pasa"}}))
        self.assertEqual(pc.veredicto_refutacion(TODAS_PASAN)["accion"], "invertir")
        una = {**TODAS_PASAN, "3": {"resultado": "refutada"}}
        self.assertEqual(pc.veredicto_refutacion(una)["accion"], "invertir_test")
        tres = {**TODAS_PASAN, **{str(n): {"resultado": "refutada"} for n in (2, 3, 4)}}
        self.assertEqual(pc.veredicto_refutacion(tres)["accion"], "descartar")
        eliminatoria = {**TODAS_PASAN, "6": {"resultado": "refutada"}}
        self.assertEqual(pc.veredicto_refutacion(eliminatoria)["accion"], "descartar")

    def test_refutar_exige_las_8_respuestas(self):
        p = self.producto()
        pc.mover(self.db, p["id"], "clasificado")
        with self.assertRaisesRegex(ValueError, "8 refutaciones"):
            pc.mover(self.db, p["id"], "refutado")

    def test_refutacion_eliminatoria_descarta(self):
        p = self.producto()
        pc.mover(self.db, p["id"], "clasificado")
        pc.guardar_refutaciones(self.db, p["id"], {**TODAS_PASAN, "1": {"resultado": "refutada"}})
        self.assertEqual(pc.mover(self.db, p["id"], "refutado")["estado"], "descartado")

    def test_creativo_exige_demanda_y_confirmacion(self):
        p = self.producto()
        for paso in ("clasificado",):
            pc.mover(self.db, p["id"], paso)
        pc.guardar_refutaciones(self.db, p["id"], TODAS_PASAN)
        pc.mover(self.db, p["id"], "refutado")
        pc.mover(self.db, p["id"], "validado")
        with self.assertRaisesRegex(ValueError, "test de demanda"):
            pc.mover(self.db, p["id"], "creativo")
        pc.guardar_demanda(self.db, p["id"], {"visitantes": 300, "emails": 9}, False)
        with self.assertRaisesRegex(ValueError, "creativo funciona"):
            pc.mover(self.db, p["id"], "creativo")

    def test_escalar_exige_metricas_reales(self):
        p = self.hasta_tienda()
        with self.assertRaisesRegex(ValueError, "SIN_DATOS|ESCALAR"):
            pc.mover(self.db, p["id"], "escalado")

    def test_recorrido_completo_con_trazabilidad(self):
        p = self.hasta_tienda()
        hoy = date.today()
        for i in range(3):   # 3 días de campaña ganadora
            bm.registrar_dia(self.db, {"fecha": (hoy - timedelta(days=2 - i)).isoformat(), "producto_id": p["id"],
                                       "gasto_ads": 20, "ingresos": 70, "pedidos": 5, "cogs_pagado": 35,
                                       "visitantes": 200, "presupuesto_diario": 20})
        bm.registrar_caja(self.db, {"saldo_cuenta": 2000, "liberaciones_pasarela": 0, "pagos_proveedor_pendientes": 0})
        final = pc.mover(self.db, p["id"], "escalado")
        self.assertEqual(final["estado"], "escalado")
        self.assertGreaterEqual(len(final["eventos"]), 7)
        self.assertTrue(all(e["correlation_id"] for e in final["eventos"]))

    def test_un_descartado_solo_se_reabre_como_candidato(self):
        p = pc.mover(self.db, self.producto()["id"], "descartado", "no me convence")
        with self.assertRaisesRegex(ValueError, "reabrir"):
            pc.mover(self.db, p["id"], "clasificado")
        self.assertEqual(pc.mover(self.db, p["id"], "candidato")["estado"], "candidato")


class NegocioTests(Base):
    def test_estados_de_caja_y_roas_segun_las_tablas(self):
        self.assertEqual([bm.estado_caja(d)["estado"] for d in (8, 7, 5, 3, 1.9, None)],
                         ["SALUDABLE", "SALUDABLE", "PRECAUCION", "ALERTA", "CRITICO", "SIN_DATOS"])
        self.assertEqual([bm.estado_roas(r)["estado"] for r in (3.2, 2.0, 1.5, 0.8, None)],
                         ["RENTABLE", "AJUSTADO", "PERDIDA", "SANGRADO", "SIN_DATOS"])

    def test_cpa_maximo_es_el_margen_neto_por_unidad(self):
        c = bm.cpa_producto(5, 2, 15)
        self.assertAlmostEqual(c["cpa_max"], 15 - 7 - 15 * 0.04 - 15 * 0.101, places=2)
        self.assertAlmostEqual(c["cpa_objetivo"], round(c["cpa_max"] * 0.7, 2), places=2)

    def test_resumen_calcula_roas_cpa_y_dias_de_caja(self):
        hoy = date.today().isoformat()
        bm.registrar_dia(self.db, {"fecha": hoy, "gasto_ads": 100, "ingresos": 300, "pedidos": 10, "cogs_pagado": 100})
        bm.registrar_caja(self.db, {"saldo_cuenta": 600, "liberaciones_pasarela": 200, "pagos_proveedor_pendientes": 100})
        r = bm.resumen(self.db, 7)
        self.assertEqual(r["roas"], 3.0)
        self.assertEqual(r["cpa_real"], 10.0)
        self.assertEqual(r["caja_disponible"], 700.0)
        self.assertEqual(r["dias_de_caja"], 3.5)                 # 700 / (100 + 100)
        self.assertEqual(r["caja_estado"]["estado"], "ALERTA")
        self.assertEqual(r["resultado_periodo"], 100.0)           # 300 - 100 - 100
        self.assertTrue(r["devoluciones_estimadas"])              # sin dato real: 10,1 % marcado como estimado

    def test_sin_caja_no_se_inventa(self):
        bm.registrar_dia(self.db, {"gasto_ads": 50, "ingresos": 150, "pedidos": 4})
        r = bm.resumen(self.db, 7)
        self.assertIsNone(r["dias_de_caja"])
        self.assertTrue(any("caja" in h.lower() for h in r["datos_que_faltan"]))

    def test_registrar_valida_los_datos(self):
        with self.assertRaises(ValueError):
            bm.registrar_dia(self.db, {"fecha": "ayer", "gasto_ads": 1})
        with self.assertRaises(ValueError):
            bm.registrar_dia(self.db, {"gasto_ads": -5})
        with self.assertRaises(ValueError):
            bm.registrar_caja(self.db, {"saldo_cuenta": None})

    def test_mismo_dia_se_sustituye_no_se_duplica(self):
        bm.registrar_dia(self.db, {"fecha": "2026-11-01", "gasto_ads": 10, "ingresos": 20, "pedidos": 1})
        bm.registrar_dia(self.db, {"fecha": "2026-11-01", "gasto_ads": 30, "ingresos": 90, "pedidos": 3})
        filas = bm.listar_metricas(self.db, 3650)
        self.assertEqual(len([f for f in filas if f["fecha"] == "2026-11-01"]), 1)
        self.assertEqual([f for f in filas if f["fecha"] == "2026-11-01"][0]["gasto_ads"], 30)

    def _campana(self, dias, gasto, ingresos, pedidos, visitantes=None):
        p = self.producto()
        hoy = date.today()
        for i in range(dias):
            bm.registrar_dia(self.db, {"fecha": (hoy - timedelta(days=dias - 1 - i)).isoformat(), "producto_id": p["id"],
                                       "gasto_ads": gasto, "ingresos": ingresos, "pedidos": pedidos,
                                       "cogs_pagado": pedidos * 7, "visitantes": visitantes, "presupuesto_diario": 20})
        return pc.obtener(self.db, p["id"])

    def test_escalado_dia_1_2_es_aprendizaje(self):
        r = bm.evaluar_escalado(self.db, self._campana(2, 20, 70, 5))
        self.assertEqual(r["escenario"], "APRENDIZAJE")
        self.assertEqual(r["decision"], "MANTENER")

    def test_escalado_negativo_corta(self):
        r = bm.evaluar_escalado(self.db, self._campana(3, 20, 10, 1))   # ROAS 0,5
        self.assertEqual((r["escenario"], r["decision"]), ("NEGATIVO", "CORTAR"))

    def test_escalado_winner_necesita_caja(self):
        p = self._campana(3, 20, 70, 5, visitantes=200)                 # ROAS 3,5 · CPA 4
        sin_caja = bm.evaluar_escalado(self.db, p)
        self.assertEqual(sin_caja["decision"], "MANTENER")              # nunca se escala sin verificar la caja
        bm.registrar_caja(self.db, {"saldo_cuenta": 5000})
        con_caja = bm.evaluar_escalado(self.db, p)
        self.assertEqual((con_caja["escenario"], con_caja["decision"]), ("WINNER", "ESCALAR"))
        self.assertIn("24.00", con_caja["accion"])                      # 20 + 20 %

    def test_escalado_con_poca_caja_espera(self):
        p = self._campana(3, 20, 70, 5, visitantes=200)
        bm.registrar_caja(self.db, {"saldo_cuenta": 100})
        self.assertEqual(bm.evaluar_escalado(self.db, p)["decision"], "MANTENER")

    def test_integraciones_no_muestran_valores(self):
        for i in bm.estado_integraciones():
            self.assertNotIn("valor", i)
            self.assertIn("configurada", i)


if __name__ == "__main__":
    unittest.main()
