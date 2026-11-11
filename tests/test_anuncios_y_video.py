"""Fase 4: redactar-anuncios-meta y generar-video-ia. Sin red: todo mockeado
(llm_router.chat, gemini_vision, higgsfield_client). BD temporal."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import DatabaseConnection
from app.services import anuncios_meta_service, video_generator_service


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        raiz = Path(self.tmp.name)
        (raiz / "data").mkdir()
        self.db = str(raiz / "data" / "t.db")
        DatabaseConnection(self.db)

    def tearDown(self):
        self.tmp.cleanup()


_RESPUESTA_LIMPIA = """{"formato_a": {"primary_text": "Organiza tu cocina en minutos", "headline": "Organiza tu cocina hoy", "descripcion": "Garantia 30 dias"},
"formato_b": {"problema": {"headline": "El cajon es un caos", "descripcion": "Pierdes tiempo cada dia"},
"solucion": {"headline": "Organizador modular", "descripcion": "Todo en su sitio en 5 minutos"},
"oferta": {"headline": "19,99 euros - Garantia 30 dias", "descripcion": "Envio en 2-5 dias habiles"}},
"formato_c": {"dolor": "Cansado de no encontrar nada en el cajon?", "resultado": "Asi quedo mi cocina en 5 minutos"}}"""


class AnunciosMetaServiceTests(Base):
    def test_generar_parsea_los_tres_formatos_y_pasa_el_gate(self):
        with mock.patch.object(anuncios_meta_service, "chat", return_value=_RESPUESTA_LIMPIA):
            r = anuncios_meta_service.generar("Organizador de cocina")
        self.assertTrue(r["generado"])
        self.assertTrue(r["gate_pass"])
        self.assertEqual(r["formato_a"]["headline"], "Organiza tu cocina hoy")
        self.assertIn("dolor", r["formato_c"])
        self.assertIn("resultado", r["formato_c"])

    def test_superlativo_en_cualquier_formato_falla_el_gate(self):
        sucio = _RESPUESTA_LIMPIA.replace("Organiza tu cocina hoy", "El mejor organizador del mundo")
        with mock.patch.object(anuncios_meta_service, "chat", return_value=sucio):
            r = anuncios_meta_service.generar("Organizador de cocina")
        self.assertFalse(r["gate_pass"])
        self.assertTrue(r["gate_violations"])

    def test_promesa_de_envio_irreal_falla_el_gate(self):
        sucio = _RESPUESTA_LIMPIA.replace("Envio en 2-5 dias habiles", "Envio en 24-48h")
        with mock.patch.object(anuncios_meta_service, "chat", return_value=sucio):
            r = anuncios_meta_service.generar("Organizador de cocina")
        self.assertFalse(r["gate_pass"])

    def test_sin_respuesta_del_modelo_no_rompe(self):
        with mock.patch.object(anuncios_meta_service, "chat", return_value=None):
            r = anuncios_meta_service.generar("x")
        self.assertFalse(r["generado"])
        self.assertEqual(r["formato_a"], {})

    def test_guardar_y_listar_roundtrip_y_filtra_por_producto(self):
        with mock.patch.object(anuncios_meta_service, "chat", return_value=_RESPUESTA_LIMPIA):
            r = anuncios_meta_service.generar("x")
        mid = anuncios_meta_service.guardar(self.db, 7, r)
        anuncios_meta_service.guardar(self.db, 9, r)
        filas = anuncios_meta_service.listar(self.db, producto_id=7)
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["id"], mid)
        self.assertTrue(filas[0]["gate_pass"])
        self.assertEqual(len(anuncios_meta_service.listar(self.db)), 2)


class VideoGeneratorServiceTests(Base):
    def test_sin_clave_higgsfield_usa_fallback_manual(self):
        with mock.patch.dict("os.environ", {"HIGGSFIELD_API_KEY": ""}), \
             mock.patch.object(video_generator_service.gemini_vision, "analyze_product_image",
                               return_value={"material": "plastico", "category": "hogar"}), \
             mock.patch.object(video_generator_service.higgsfield_client, "generate_product_video") as gen_video:
            r = video_generator_service.generar(self.db, 1, "https://ej.com/foto.jpg", "Lámpara", "gira mostrando el detalle")
        gen_video.assert_not_called()
        self.assertEqual(r["estado"], "fallback_manual")
        self.assertIsNone(r["video_url"])
        self.assertIn("prompt_movimiento", r)
        self.assertTrue(r["prompt_movimiento"])

    def test_con_clave_y_video_generado(self):
        with mock.patch.dict("os.environ", {"HIGGSFIELD_API_KEY": "clave-de-prueba"}), \
             mock.patch.object(video_generator_service.gemini_vision, "analyze_product_image",
                               return_value={"material": "plastico"}), \
             mock.patch.object(video_generator_service.higgsfield_client, "generate_product_video",
                               return_value="https://cdn.ej.com/video.mp4"):
            r = video_generator_service.generar(self.db, 1, "https://ej.com/foto.jpg", "Lámpara", "hook")
        self.assertEqual(r["estado"], "generado")
        self.assertEqual(r["video_url"], "https://cdn.ej.com/video.mp4")

    def test_con_clave_pero_higgsfield_falla_queda_en_error(self):
        with mock.patch.dict("os.environ", {"HIGGSFIELD_API_KEY": "clave-de-prueba"}), \
             mock.patch.object(video_generator_service.gemini_vision, "analyze_product_image", return_value=None), \
             mock.patch.object(video_generator_service.higgsfield_client, "generate_product_video", return_value=None):
            r = video_generator_service.generar(self.db, 1, "https://ej.com/foto.jpg", "Lámpara", "hook")
        self.assertEqual(r["estado"], "error")
        self.assertIsNone(r["video_url"])

    def test_listar_filtra_por_producto_y_persiste_specs(self):
        with mock.patch.dict("os.environ", {"HIGGSFIELD_API_KEY": ""}), \
             mock.patch.object(video_generator_service.gemini_vision, "analyze_product_image",
                               return_value={"material": "metal"}):
            video_generator_service.generar(self.db, 3, "https://ej.com/a.jpg", "A", "hook a")
            video_generator_service.generar(self.db, 5, "https://ej.com/b.jpg", "B", "hook b")
        self.assertEqual(len(video_generator_service.listar(self.db, producto_id=3)), 1)
        self.assertEqual(video_generator_service.listar(self.db, producto_id=3)[0]["specs"]["material"], "metal")
        self.assertEqual(len(video_generator_service.listar(self.db)), 2)


if __name__ == "__main__":
    unittest.main()
