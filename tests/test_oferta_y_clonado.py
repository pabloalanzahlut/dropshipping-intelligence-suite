"""Fase 5: oferta-multiunidad (sin IA, delega en FinancialValidator) y clonar-seccion
(con IA mockeada). BD temporal, sin red."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import DatabaseConnection
from app.services import clonar_seccion_service, oferta_multiunidad_service


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        raiz = Path(self.tmp.name)
        (raiz / "data").mkdir()
        self.db = str(raiz / "data" / "t.db")
        DatabaseConnection(self.db)

    def tearDown(self):
        self.tmp.cleanup()


class OfertaMultiunidadServiceTests(Base):
    def test_coste_invalido_lanza_valueerror(self):
        with self.assertRaises(ValueError):
            oferta_multiunidad_service.calcular("sku", 0, 20, 79, 119)

    def test_sin_pvps_lanza_valueerror(self):
        with self.assertRaises(ValueError):
            oferta_multiunidad_service.calcular("sku", 7, None, None, None)

    def test_caso_del_skill_1_mas_1_a_79_es_buen_multiplicador(self):
        # landed 7 €/ud, 1+1 = 2 uds → coste 14 €; PVP 79 → ~5,6x (ejemplo del propio skill)
        r = oferta_multiunidad_service.calcular("sku", 7.0, pvp_entrada=45.0, pvp_principal=79.0, pvp_upsell=119.0)
        self.assertTrue(r["escalones"]["principal"]["validado"])
        self.assertAlmostEqual(r["escalones"]["principal"]["multiplicador"], 79 / 14, places=1)
        self.assertEqual(r["escalones"]["principal"]["unidades_entregadas"], 2)
        self.assertEqual(r["escalones"]["upsell"]["unidades_entregadas"], 4)

    def test_oferta_barata_no_llega_al_minimo_y_queda_sin_validar(self):
        # La misma oferta 1+1 a 25 € con landed 7 €/ud es ~1,78x — por debajo del mínimo 2x.
        r = oferta_multiunidad_service.calcular("sku", 7.0, pvp_entrada=15.0, pvp_principal=25.0)
        self.assertFalse(r["escalones"]["principal"]["validado"])
        self.assertEqual(r["veredicto_general"], "revisar")
        self.assertNotIn("upsell", r["escalones"])   # no se pidió upsell: no aparece

    def test_nunca_calcula_su_propio_multiplicador_delega_siempre(self):
        """Defensa en profundidad: el multiplicador que devuelve siempre coincide con
        pvp / (landed_unidad * unidades) — la única fuente de verdad es FinancialValidator."""
        r = oferta_multiunidad_service.calcular("sku", 6.5, pvp_entrada=30.0, pvp_principal=60.0, pvp_upsell=100.0)
        for nombre, unidades in (("entrada", 1), ("principal", 2), ("upsell", 4)):
            esc = r["escalones"][nombre]
            esperado = round(esc["pvp"] / (6.5 * unidades), 2)
            self.assertEqual(esc["multiplicador"], esperado)

    def test_guardar_y_listar_roundtrip_filtra_por_producto(self):
        r = oferta_multiunidad_service.calcular("sku", 7.0, 45.0, 79.0, 119.0)
        oferta_multiunidad_service.guardar(self.db, 4, r)
        oferta_multiunidad_service.guardar(self.db, 8, r)
        self.assertEqual(len(oferta_multiunidad_service.listar(self.db, producto_id=4)), 1)
        self.assertEqual(len(oferta_multiunidad_service.listar(self.db)), 2)


_RESPUESTA_LIMPIA = """{"que_resuelve": "Urgencia de stock bajo", "patron": "urgencia",
"liquid_code": "{%- if product.selected_or_first_available_variant.inventory_quantity < 20 -%}<div class=\\"gem-stock-badge\\">Quedan {{ product.selected_or_first_available_variant.inventory_quantity }} unidades</div>{%- endif -%}",
"css_code": ".gem-stock-badge { color: red; }", "variables": ["product.selected_or_first_available_variant.inventory_quantity"],
"notas": "Usa el inventario real de Shopify, no un numero inventado."}"""


class ClonarSeccionServiceTests(Base):
    def test_html_vacio_lanza_valueerror(self):
        with self.assertRaises(ValueError):
            clonar_seccion_service.clonar("   ")

    def test_clonar_parsea_y_pasa_el_gate(self):
        with mock.patch.object(clonar_seccion_service, "chat", return_value=_RESPUESTA_LIMPIA):
            r = clonar_seccion_service.clonar("<div class='stock'>Quedan 3</div>")
        self.assertTrue(r["generado"])
        self.assertTrue(r["gate_pass"])
        self.assertEqual(r["patron"], "urgencia")
        self.assertIn("gem-stock-badge", r["liquid_code"])
        self.assertIn("product.selected_or_first_available_variant.inventory_quantity", r["variables"])

    def test_superlativo_en_que_resuelve_falla_el_gate(self):
        sucio = _RESPUESTA_LIMPIA.replace("Urgencia de stock bajo", "La seccion mas increible")
        with mock.patch.object(clonar_seccion_service, "chat", return_value=sucio):
            r = clonar_seccion_service.clonar("<div>x</div>")
        self.assertFalse(r["gate_pass"])

    def test_sin_respuesta_no_rompe(self):
        with mock.patch.object(clonar_seccion_service, "chat", return_value=None):
            r = clonar_seccion_service.clonar("<div>x</div>")
        self.assertFalse(r["generado"])
        self.assertEqual(r["liquid_code"], "")

    def test_guardar_y_listar_roundtrip(self):
        with mock.patch.object(clonar_seccion_service, "chat", return_value=_RESPUESTA_LIMPIA):
            r = clonar_seccion_service.clonar("<div>x</div>")
        cid = clonar_seccion_service.guardar(self.db, 2, r)
        filas = clonar_seccion_service.listar(self.db, producto_id=2)
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["id"], cid)
        self.assertTrue(filas[0]["gate_pass"])


if __name__ == "__main__":
    unittest.main()
