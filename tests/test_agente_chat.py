"""Capa conversacional del Agente IA (app/services/agent_chat.py), compartida por web y escritorio.

Todo lo que no es la llamada al proveedor de IA es determinista: se prueba sin red y sin clave.
"""
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
from app.services import agent_chat


class CharlaTests(unittest.TestCase):
    def test_reconoce_saludo_ayuda_gracias_y_adios(self):
        self.assertEqual(agent_chat.charla("Hola"), "saludo")
        self.assertEqual(agent_chat.charla("  buenas tardes  "), "saludo")
        self.assertEqual(agent_chat.charla("¿Qué puedes hacer?"), "ayuda")
        self.assertEqual(agent_chat.charla("muchas gracias"), "gracias")
        self.assertEqual(agent_chat.charla("vale, gracias"), "gracias")
        self.assertEqual(agent_chat.charla("hasta luego"), "adios")

    def test_no_confunde_una_pregunta_real_con_charla(self):
        self.assertIsNone(agent_chat.charla("¿Qué productos HOT han aparecido en la KB?"))
        self.assertIsNone(agent_chat.charla("Hola, ¿cuál es el margen de este producto con coste 5 y PVP 12?"))
        self.assertIsNone(agent_chat.charla(""))
        self.assertIsNone(agent_chat.charla("x" * 80))

    def test_respuesta_rapida_de_ayuda_no_toca_la_bd(self):
        texto = agent_chat.respuesta_rapida("ayuda", "/ruta/que/no/existe.db")
        self.assertIn("GEM OS", texto)
        self.assertIn("mentores", texto)

    def test_respuesta_rapida_de_saludo_no_revienta_sin_bd(self):
        texto = agent_chat.respuesta_rapida("saludo", "/ruta/que/no/existe.db")
        self.assertIn("Hola", texto)
        self.assertIn("apuntes", texto)


class LimpiarMarcasTests(unittest.TestCase):
    def test_quita_tienda_y_data_gap_pero_conserva_las_citas(self):
        t, usa = agent_chat.limpiar_marcas("Vendes bien [TIENDA]. Según [3] el hook funciona [DATA_GAP: coste envío].")
        self.assertTrue(usa)
        self.assertNotIn("[TIENDA]", t)
        self.assertNotIn("DATA_GAP", t)
        self.assertIn("[3]", t)
        self.assertIn("(falta: coste envío)", t)

    def test_sin_marcas_no_cambia_nada_relevante(self):
        t, usa = agent_chat.limpiar_marcas("Texto normal sin marcas.")
        self.assertEqual(t, "Texto normal sin marcas.")
        self.assertFalse(usa)


class EtiquetaValorTests(unittest.TestCase):
    def test_etiqueta_convierte_snake_case(self):
        self.assertEqual(agent_chat.etiqueta("multiplicador_sobre_coste_producto"), "Multiplicador sobre coste producto")
        self.assertEqual(agent_chat.etiqueta("pvp_eur"), "PVP (EUR)")
        self.assertEqual(agent_chat.etiqueta("roas_real"), "ROAS real")
        self.assertEqual(agent_chat.etiqueta("coste_envio_usd"), "Coste envio (USD)")

    def test_valor_formatea_numeros_booleanos_y_vacios(self):
        self.assertEqual(agent_chat.valor(None), "—")
        self.assertEqual(agent_chat.valor(""), "—")
        self.assertEqual(agent_chat.valor(True), "Sí")
        self.assertEqual(agent_chat.valor(False), "No")
        self.assertEqual(agent_chat.valor(5), "5")
        self.assertEqual(agent_chat.valor(2.15), "2,15")
        self.assertEqual(agent_chat.valor(3.0), "3")

    def test_valor_limpia_marcas_dentro_de_un_texto(self):
        self.assertEqual(agent_chat.valor("Pedidos reales [TIENDA]"), "Pedidos reales")


class DatosLegiblesTests(unittest.TestCase):
    def test_lista_de_productos_se_convierte_en_bloques_con_titulo(self):
        data = {
            "respuesta": "...",
            "datos": [
                {"producto": "Peine láser", "pvp_eur": 42.99, "multiplicador_sobre_coste_producto": 2.15,
                 "clasificacion": "COLD"},
                {"producto": "Funda térmica", "pvp_eur": 19.0, "multiplicador_sobre_coste_producto": 3.2,
                 "clasificacion": "WARM"},
            ],
        }
        bloques = agent_chat.datos_legibles(data)
        self.assertEqual(len(bloques), 2)
        self.assertEqual(bloques[0]["titulo"], "Peine láser")
        self.assertIn(["Clasificacion", "COLD"], bloques[0]["filas"])
        self.assertNotIn(["Producto", "Peine láser"], bloques[0]["filas"])     # el título no se repite como fila

    def test_nunca_se_cuela_json_crudo_en_los_valores(self):
        data = {"respuesta": "ok", "detalle": {"a": 1, "b": [1, 2, 3]}}
        bloques = agent_chat.datos_legibles(data)
        texto = agent_chat.bloques_a_texto(bloques)
        self.assertNotIn("{", texto)
        self.assertNotIn("}", texto)


class ANaturalTests(unittest.TestCase):
    def test_json_normal_devuelve_solo_la_respuesta_como_texto(self):
        bruto = json.dumps({"respuesta": "Tu tienda va bien.", "tipo_consulta": "metrica",
                            "datos": [{"pedidos": 3}], "confianza": "Alta"}, ensure_ascii=False)
        r = agent_chat.a_natural(bruto)
        self.assertEqual(r["texto"], "Tu tienda va bien.")
        self.assertEqual(r["confianza"], "Alta")
        self.assertEqual(len(r["datos"]), 1)
        self.assertNotIn("tipo_consulta", r["texto"])

    def test_json_envuelto_en_fences_markdown(self):
        bruto = '```json\n{"respuesta": "Hola"}\n```'
        self.assertEqual(agent_chat.a_natural(bruto)["texto"], "Hola")

    def test_json_sin_campo_respuesta_cae_a_los_datos_legibles(self):
        bruto = json.dumps({"producto": "X", "margen": 3.2})
        r = agent_chat.a_natural(bruto)
        self.assertIn("Producto", r["texto"])
        self.assertIn("X", r["texto"])
        self.assertNotIn("{", r["texto"])

    def test_texto_plano_pasa_tal_cual(self):
        r = agent_chat.a_natural("Esto ya es una respuesta en texto normal.")
        self.assertEqual(r["texto"], "Esto ya es una respuesta en texto normal.")

    def test_json_cortado_a_media_cadena_rescata_la_respuesta(self):
        bruto = '{"respuesta": "Esto se corta a la mi'
        r = agent_chat.a_natural(bruto)
        self.assertIn("Esto se corta a la mi", r["texto"])

    def test_json_vacio_no_rompe(self):
        r = agent_chat.a_natural("{}")
        self.assertTrue(r["texto"])
        self.assertNotIn("{", r["texto"])

    def test_marca_tienda_se_detecta_y_se_limpia_del_texto(self):
        bruto = json.dumps({"respuesta": "Tienes 3 pedidos [TIENDA]."})
        r = agent_chat.a_natural(bruto)
        self.assertTrue(r["usa_tienda"])
        self.assertNotIn("[TIENDA]", r["texto"])


class HistorialYRutaTests(unittest.TestCase):
    HIST = [{"rol": "user", "texto": "¿Qué productos HOT hay?"},
            {"rol": "agente", "texto": "Tienes dos: X e Y [1]."}]

    def test_turnos_filtra_y_recorta(self):
        largo = [{"rol": "user", "texto": "a" * 2000}]
        t = agent_chat._turnos(largo)
        self.assertEqual(len(t[0][1]), agent_chat.MAX_CHARS_TURNO)
        self.assertEqual(agent_chat._turnos([{"rol": "sistema", "texto": "x"}]), [])
        self.assertEqual(agent_chat._turnos([{"rol": "user", "texto": "  "}]), [])

    def test_historial_a_texto_tiene_los_dos_roles(self):
        t = agent_chat.historial_a_texto(self.HIST)
        self.assertIn("Operador:", t)
        self.assertIn("Agente:", t)

    def test_consulta_para_buscar_hereda_el_tema_en_una_repregunta_corta(self):
        self.assertEqual(agent_chat.consulta_para_buscar("¿y con envío?", self.HIST),
                         "¿y con envío? ¿Qué productos HOT hay?")
        # una pregunta con sus propias señales no necesita heredar nada
        self.assertEqual(agent_chat.consulta_para_buscar("¿Qué estrategias de tráfico recomienda la KB?", self.HIST),
                         "¿Qué estrategias de tráfico recomienda la KB?")

    def test_elegir_ruta_sigue_el_tema_de_la_pregunta_anterior(self):
        ruta = agent_chat.elegir_ruta("¿y el segundo?", "auto", self.HIST)
        self.assertEqual(ruta["tipo"], "producto")
        self.assertIn("continúa la conversación", ruta["motivo"])
        self.assertEqual(ruta["rol"], "Orquestador")

    def test_elegir_ruta_sin_historial_se_queda_en_general(self):
        ruta = agent_chat.elegir_ruta("¿y el segundo?", "auto", None)
        self.assertEqual(ruta["tipo"], "general")

    def test_charla_no_hereda_tema_del_historial(self):
        ruta = agent_chat.elegir_ruta("gracias", "auto", self.HIST)
        self.assertEqual(ruta["tipo"], "general")


class ExplicarErrorTests(unittest.TestCase):
    def test_traduce_los_codigos_de_error_mas_comunes(self):
        self.assertIn("saldo", agent_chat.explicar_error(Exception("402 Payment Required")))
        self.assertIn("clave", agent_chat.explicar_error(Exception("401 Unauthorized")))
        self.assertIn("espera", agent_chat.explicar_error(Exception("429 Too Many Requests")).lower())
        self.assertIn("conectar", agent_chat.explicar_error(Exception("Connection refused")))
        self.assertIn("tardado", agent_chat.explicar_error(Exception("Read timed out")))

    def test_agente_no_disponible_devuelve_su_propio_mensaje(self):
        self.assertEqual(agent_chat.explicar_error(agent_chat.AgenteNoDisponible("mensaje concreto")),
                         "mensaje concreto")

    def test_error_desconocido_no_se_queda_mudo(self):
        texto = agent_chat.explicar_error(Exception("algo_muy_raro_12345"))
        self.assertIn("algo_muy_raro_12345", texto)


class TrocearTests(unittest.TestCase):
    def test_trocear_reconstruye_el_texto_completo(self):
        original = "Hola mundo, esto es una prueba con varias palabras seguidas."
        self.assertEqual("".join(agent_chat.trocear(original, 2)), original)

    def test_trocear_vacio_no_rompe(self):
        self.assertEqual(list(agent_chat.trocear("")), [])


class ResponderTests(unittest.TestCase):
    """responder() con un AgentExecutor simulado: sin red, sin clave de verdad."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = str(Path(self.tmp.name) / "t.db")
        DatabaseConnection(self.db_path)   # crea el esquema

    def tearDown(self):
        self.tmp.cleanup()

    def test_pregunta_vacia_lanza_value_error(self):
        with self.assertRaises(ValueError):
            agent_chat.responder(self.db_path, "   ")

    def test_la_charla_no_llama_al_motor(self):
        executor = mock.Mock()
        r = agent_chat.responder(self.db_path, "hola", executor=executor)
        self.assertTrue(r["rapida"])
        self.assertFalse(executor.execute_agent_task.called)
        self.assertIn("Hola", r["texto"])

    def test_sin_clave_y_sin_executor_avisa_en_vez_de_fallar_feo(self):
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            with self.assertRaises(agent_chat.AgenteNoDisponible):
                agent_chat.responder(self.db_path, "¿qué productos hay?")

    def test_pregunta_normal_usa_el_executor_y_devuelve_texto_natural(self):
        executor = mock.Mock()
        executor.execute_agent_task.return_value = json.dumps(
            {"respuesta": "Aquí tienes la respuesta [1].", "confianza": "Media"})
        r = agent_chat.responder(self.db_path, "¿Qué productos HOT hay?", executor=executor)
        self.assertFalse(r["rapida"])
        self.assertEqual(r["texto"], "Aquí tienes la respuesta [1].")
        self.assertEqual(r["ruta"]["agente"], "gem-orchestrator-core")
        executor.execute_agent_task.assert_called_once()
        self.assertEqual(executor.execute_agent_task.call_args.kwargs["skill_name"], "consultar_kb_agente")

    def test_fallo_del_motor_se_traduce_para_el_operador(self):
        executor = mock.Mock()
        executor.execute_agent_task.side_effect = RuntimeError("401 Unauthorized")
        with self.assertRaises(agent_chat.AgenteNoDisponible) as ctx:
            agent_chat.responder(self.db_path, "¿Qué productos hay?", executor=executor)
        self.assertIn("clave", str(ctx.exception))

    def test_construir_peticion_lleva_el_estilo_y_la_conversacion_previa(self):
        ruta = agent_chat.elegir_ruta("¿y con envío?", "auto")
        peticion, fuentes, con_tienda = agent_chat.construir_peticion(
            self.db_path, "¿y con envío?", ruta,
            [{"rol": "user", "texto": "coste 5, PVP 12"}, {"rol": "agente", "texto": "Cumple el 2x."}])
        self.assertIn("ESTILO DE LA RESPUESTA", peticion)
        self.assertIn("CONVERSACIÓN HASTA AHORA", peticion)
        self.assertIn("coste 5, PVP 12", peticion)
        self.assertIn("PREGUNTA DEL OPERADOR:\n¿y con envío?", peticion)


if __name__ == "__main__":
    unittest.main()
