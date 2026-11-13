"""Matriz de precios 2x/3x: todo sobre coste landed, sin envíos inventados. Sin red; BD temporal."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import DatabaseConnection
from app.services.pricing_matrix import PricingMatrix


class PricingMatrixTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.pm = PricingMatrix(db_manager=DatabaseConnection(os.path.join(self.tmp.name, "t.db")))

    def tearDown(self):
        self.tmp.cleanup()

    def calcular(self, **producto):
        base = {"name": "Pelota gatos", "cost_usd": 5, "shipping_usd": 2}
        base.update(producto)
        return self.pm.calculate([base])[0]

    def test_multiplos_sobre_coste_landed(self):
        r = self.calcular()
        self.assertEqual(r["landed_usd"], 7.0)
        self.assertEqual((r["pvp_2x"], r["pvp_3x"]), (14.99, 21.99))
        # El caso de CLAUDE.md: sobre el producto solo, $15 aparentaría 3,0x
        self.assertAlmostEqual(r["ratio_2x"], 14.99 / 7, places=2)
        self.assertAlmostEqual(r["ratio_3x"], 21.99 / 7, places=2)

    def test_pvp_99_nunca_queda_por_debajo_del_multiplo(self):
        for coste, envio in ((5, 2), (9.5, 0), (4.33, 1.67), (12.495, 2.5), (0.5, 0.25)):
            r = self.calcular(cost_usd=coste, shipping_usd=envio)
            landed = coste + envio
            self.assertGreaterEqual(r["pvp_2x"], landed * 2 - 1e-9, (coste, envio))
            self.assertGreaterEqual(r["pvp_3x"], landed * 3 - 1e-9, (coste, envio))
            self.assertEqual(round(r["pvp_2x"] % 1, 2), 0.99)
            self.assertEqual(round(r["pvp_3x"] % 1, 2), 0.99)

    def test_to_99_conserva_un_precio_que_ya_termina_en_99(self):
        self.assertEqual(PricingMatrix._to_99(20.99), 20.99)
        self.assertEqual(PricingMatrix._to_99(14.0), 14.99)
        self.assertEqual(PricingMatrix._to_99(28.5), 28.99)
        self.assertEqual(PricingMatrix._to_99(28.995), 29.99)

    def test_clasificacion_y_validacion_sobre_landed(self):
        r = self.calcular()
        self.assertEqual(r["classification_2x"], "COLD")   # 2,14x: cumple el mínimo
        self.assertEqual(r["classification_3x"], "WARM")   # 3,14x: cumple el objetivo
        self.assertTrue(r["fv_compliant"])

    def test_sin_envio_es_data_gap_no_una_estimacion(self):
        with self.assertRaises(ValueError) as ctx:
            self.pm.calculate([{"name": "Sin envío", "cost_usd": 9.5, "vertical": "Home"}])
        self.assertIn("DATA_GAP_REQUEST", str(ctx.exception))
        self.assertIn("shipping_usd", str(ctx.exception))

    def test_sin_coste_es_data_gap(self):
        with self.assertRaises(ValueError) as ctx:
            self.pm.calculate([{"name": "Sin coste", "shipping_usd": 2}])
        self.assertIn("DATA_GAP_REQUEST", str(ctx.exception))

    def test_envio_cero_explicito_se_acepta(self):
        r = self.calcular(cost_usd=9.5, shipping_usd=0)
        self.assertEqual(r["landed_usd"], 9.5)
        self.assertEqual(r["pvp_2x"], 19.99)

    def test_alias_shipping_override_sigue_funcionando(self):
        r = self.pm.calculate([{"name": "Legado", "cost_usd": 5, "shipping_override": 2}])[0]
        self.assertEqual(r["landed_usd"], 7.0)

    def test_tabla_y_guardado(self):
        out = self.pm.run([{"name": "Pelota gatos", "cost_usd": 5, "shipping_usd": 2}],
                          budget_month="2026-11", save=True)
        self.assertIn("Landed", out["table"])
        self.assertEqual(len(out["saved_ids"]), 1)
        self.assertTrue(out["correlation_id"])


if __name__ == "__main__":
    unittest.main()
