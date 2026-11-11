"""Fase 6 (opcional): checklist + copy guiado para canales pagados. Sin red: llm_router.chat
mockeado. BD temporal."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import DatabaseConnection
from app.services import canal_checklist_service as svc


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        raiz = Path(self.tmp.name)
        (raiz / "data").mkdir()
        self.db = str(raiz / "data" / "t.db")
        DatabaseConnection(self.db)

    def tearDown(self):
        self.tmp.cleanup()


class ChecklistEstaticoTests(unittest.TestCase):
    def test_los_4_canales_tienen_checklist_no_vacio(self):
        for canal in svc.CANALES:
            items = svc.checklist(canal)
            self.assertTrue(items)
            self.assertTrue(all(isinstance(i, str) and i for i in items))

    def test_canal_desconocido_lanza_valueerror(self):
        with self.assertRaises(ValueError):
            svc.checklist("meta_ads")


class GenerarCopyTests(Base):
    def test_canal_desconocido_lanza_valueerror(self):
        with self.assertRaises(ValueError):
            svc.generar("meta_ads", "producto x")

    def test_genera_parsea_y_pasa_el_gate(self):
        respuesta = '{"copy": {"titulo_1": "Organiza tu cocina", "titulo_2": "Antes de que se agote", "descripcion": "Garantia 30 dias"}}'
        with mock.patch.object(svc, "chat", return_value=respuesta):
            r = svc.generar("google_ads", "Organizador de cocina, PVP 25")
        self.assertTrue(r["generado"])
        self.assertTrue(r["gate_pass"])
        self.assertEqual(r["copy"]["titulo_1"], "Organiza tu cocina")
        self.assertEqual(r["checklist"], svc.checklist("google_ads"))

    def test_superlativo_en_el_copy_falla_el_gate(self):
        respuesta = '{"copy": {"titulo": "El mejor producto del mundo"}}'
        with mock.patch.object(svc, "chat", return_value=respuesta):
            r = svc.generar("tiktok_ads", "x")
        self.assertFalse(r["gate_pass"])

    def test_copy_anidado_por_error_del_modelo_se_aplana_para_el_gate(self):
        """Bug real encontrado en vivo: el modelo a veces devuelve un objeto por canal en
        vez de los campos planos pedidos. El gate debe revisar ese texto igualmente, no
        saltárselo en silencio."""
        respuesta = ('{"copy": {"Google Ads": {"titulo_1": "El mejor organizador del mundo"}, '
                     '"TikTok Ads": {"hook_video": "normal"}}}')
        with mock.patch.object(svc, "chat", return_value=respuesta):
            r = svc.generar("google_ads", "x")
        self.assertFalse(r["gate_pass"])
        self.assertTrue(r["gate_violations"])

    def test_sin_respuesta_no_rompe(self):
        with mock.patch.object(svc, "chat", return_value=None):
            r = svc.generar("amazon", "x")
        self.assertFalse(r["generado"])
        self.assertEqual(r["copy"], {})

    def test_guardar_y_listar_filtra_por_canal_y_producto(self):
        respuesta = '{"copy": {"titulo": "Compra ahora tu organizador"}}'
        with mock.patch.object(svc, "chat", return_value=respuesta):
            r_google = svc.generar("google_ads", "x")
            r_tiktok = svc.generar("tiktok_shop", "x")
        svc.guardar(self.db, 3, r_google)
        svc.guardar(self.db, 3, r_tiktok)
        svc.guardar(self.db, 7, r_google)
        self.assertEqual(len(svc.listar(self.db, producto_id=3)), 2)
        self.assertEqual(len(svc.listar(self.db, producto_id=3, canal="google_ads")), 1)
        self.assertEqual(len(svc.listar(self.db)), 3)


if __name__ == "__main__":
    unittest.main()
