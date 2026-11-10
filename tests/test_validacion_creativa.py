"""Fase 2: investigar-nicho, refutar-producto (borrador por IA) y hook-matrix.
Sin red: el LLM se mockea siempre. BD temporal, nunca toca data/dropshipping_suite.db."""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import DatabaseConnection
from app.services import deterministic_gate as gate
from app.services import hook_matrix_service, nicho_research, product_catalog as pc, refutacion_debate


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        raiz = Path(self.tmp.name)
        (raiz / "data").mkdir()
        self.db = str(raiz / "data" / "t.db")
        DatabaseConnection(self.db)

    def tearDown(self):
        self.tmp.cleanup()


def _hook(id_, formula, texto="Mira esto"):
    return {"id": id_, "formula": formula, "texto": texto, "angulo": "", "formato": "tiktok_caption",
            "primera_linea_chars": len(texto), "apto_tiktok_caption": True, "apto_meta_ad": True,
            "notas_produccion": ""}


_FORMULAS = gate.FORMULAS_HOOK


def _doce_hooks_validos():
    return [_hook(i * 2 + j, f, f"Hook {f} #{j}") for i, f in enumerate(_FORMULAS) for j in range(2)]


class CheckHookCountTests(unittest.TestCase):
    def test_doce_hooks_dos_por_formula_pasa(self):
        r = gate.check_hook_count(_doce_hooks_validos())
        self.assertTrue(r.passed)

    def test_menos_de_doce_falla(self):
        r = gate.check_hook_count(_doce_hooks_validos()[:10])
        self.assertFalse(r.passed)

    def test_formula_con_un_solo_hook_falla_aunque_el_total_llegue_a_doce(self):
        hooks = _doce_hooks_validos()[:-1] + [_hook(99, "Story")]   # Urgencia se queda con 1
        r = gate.check_hook_count(hooks)
        self.assertFalse(r.passed)
        self.assertTrue(any("Urgencia" in v for v in r.violations))

    def test_formula_desconocida_cuenta_como_violacion(self):
        hooks = _doce_hooks_validos()
        hooks[0] = _hook(1, "FormulaInventada")
        r = gate.check_hook_count(hooks)
        self.assertFalse(r.passed)

    def test_verificar_hook_matrix_detecta_superlativo(self):
        hooks = _doce_hooks_validos()
        hooks[0]["texto"] = "Esto es increíble y revolucionario"
        r = gate.verificar_hook_matrix({"hook_matrix": hooks})
        self.assertFalse(r["passed"])
        self.assertTrue(any("Superlativo" in v or "superlativo" in v for v in r["violations"]))

    def test_verificar_hook_matrix_ok_con_matriz_limpia(self):
        r = gate.verificar_hook_matrix({"hook_matrix": _doce_hooks_validos()})
        self.assertTrue(r["passed"])


class CheckRefutacionTallyTests(unittest.TestCase):
    def _respuestas(self, refutadas=()):
        return {n: {"resultado": "refutada" if n in refutadas else "pasa"} for n in range(1, 9)}

    def test_faltan_respuestas_no_decide(self):
        r = gate.check_refutacion_tally({1: {"resultado": "pasa"}})
        self.assertFalse(r.passed)
        self.assertIn("faltan", r.violations[0].lower())

    def test_ninguna_refutada_es_invertir(self):
        r = gate.check_refutacion_tally(self._respuestas())
        self.assertTrue(r.passed)
        self.assertEqual(r.evidence["accion"], "invertir")

    def test_dos_refutadas_no_eliminatorias_es_invertir_test(self):
        r = gate.check_refutacion_tally(self._respuestas({3, 4}))
        self.assertEqual(r.evidence["accion"], "invertir_test")

    def test_tres_refutadas_descarta(self):
        r = gate.check_refutacion_tally(self._respuestas({2, 3, 4}))
        self.assertEqual(r.evidence["accion"], "descartar")

    def test_eliminatoria_margen_descarta_aunque_sea_la_unica(self):
        r = gate.check_refutacion_tally(self._respuestas({1}))
        self.assertEqual(r.evidence["accion"], "descartar")
        self.assertIn(1, r.evidence["eliminatorias"])

    def test_eliminatoria_legal_descarta(self):
        r = gate.check_refutacion_tally(self._respuestas({6}))
        self.assertEqual(r.evidence["accion"], "descartar")

    def test_acepta_forma_corta_sin_dict(self):
        respuestas = {n: "pasa" for n in range(1, 9)}
        r = gate.check_refutacion_tally(respuestas)
        self.assertTrue(r.passed)


class RefutacionDebateTests(Base):
    def _crear_producto(self):
        return pc.crear(self.db, {"nombre": "Lámpara", "costo_origen": 6, "costo_envio": 2, "pvp": 25})

    def test_producto_inexistente_lanza_keyerror(self):
        with self.assertRaises(KeyError):
            refutacion_debate.redactar_debate(self.db, 99999)

    def test_borrador_completo_con_respuesta_valida(self):
        p = self._crear_producto()
        respuesta = json.dumps({"refutaciones": [
            {"numero": n, "veredicto": "pasa", "evidencia": f"dato {n}"} for n in range(1, 9)
        ]})
        with mock.patch.object(refutacion_debate, "chat", return_value=respuesta):
            r = refutacion_debate.redactar_debate(self.db, p["id"])
        self.assertTrue(r["completo"])
        self.assertEqual(len(r["refutaciones"]), 8)
        self.assertEqual(r["sin_datos"], 0)
        # No se guardó nada en el producto: sigue sin refutaciones.
        self.assertEqual(pc.obtener(self.db, p["id"])["refutaciones"], {})

    def test_respuesta_parcial_completa_el_resto_como_sin_datos(self):
        p = self._crear_producto()
        respuesta = json.dumps({"refutaciones": [{"numero": 1, "veredicto": "refutada", "evidencia": "x"}]})
        with mock.patch.object(refutacion_debate, "chat", return_value=respuesta):
            r = refutacion_debate.redactar_debate(self.db, p["id"])
        self.assertFalse(r["completo"])
        self.assertEqual(r["sin_datos"], 7)
        self.assertEqual(r["refutaciones"][0]["veredicto"], "refutada")

    def test_sin_respuesta_del_modelo_todo_sin_datos(self):
        p = self._crear_producto()
        with mock.patch.object(refutacion_debate, "chat", return_value=None):
            r = refutacion_debate.redactar_debate(self.db, p["id"])
        self.assertFalse(r["generado"])
        self.assertEqual(r["sin_datos"], 8)

    def test_veredicto_invalido_se_normaliza_a_sin_datos(self):
        p = self._crear_producto()
        respuesta = json.dumps({"refutaciones": [{"numero": 1, "veredicto": "tal_vez", "evidencia": "x"}]})
        with mock.patch.object(refutacion_debate, "chat", return_value=respuesta):
            r = refutacion_debate.redactar_debate(self.db, p["id"])
        self.assertEqual(r["refutaciones"][0]["veredicto"], "sin_datos")


class NichoResearchTests(Base):
    def test_nicho_vacio_lanza_valueerror(self):
        with self.assertRaises(ValueError):
            nicho_research.investigar("   ")

    def test_investigar_parsea_y_guarda(self):
        respuesta = json.dumps({
            "resumen": "Nicho prometedor.",
            "angulos": [{"id": i, "problema": f"problema {i}", "hook": f"hook {i}"} for i in range(1, 11)],
            "ranking": [{"angulo_id": 1, "score": 90, "motivo": "mejor"}],
        })
        with mock.patch.object(nicho_research, "chat", return_value=respuesta):
            r = nicho_research.investigar("organización del hogar")
        self.assertTrue(r["generado"])
        self.assertEqual(len(r["angulos"]), 10)
        pid = nicho_research.guardar_investigacion(self.db, r["nicho"], r["resumen"], r["angulos"], r["ranking"])
        guardado = nicho_research.obtener(self.db, pid)
        self.assertEqual(guardado["nicho"], "organización del hogar")
        self.assertEqual(len(guardado["angulos"]), 10)
        self.assertEqual(len(nicho_research.listar(self.db)), 1)
        self.assertEqual(len(nicho_research.listar(self.db, "hogar")), 1)
        self.assertEqual(len(nicho_research.listar(self.db, "nada_que_ver")), 0)

    def test_respuesta_vacia_no_rompe(self):
        with mock.patch.object(nicho_research, "chat", return_value=None):
            r = nicho_research.investigar("mascotas")
        self.assertFalse(r["generado"])
        self.assertEqual(r["angulos"], [])


class HookMatrixServiceTests(Base):
    def test_generar_guarda_y_lista_con_gate_pass(self):
        respuesta = json.dumps({"hook_matrix": _doce_hooks_validos(), "recomendacion_test": "probar el #1"})
        with mock.patch.object(hook_matrix_service, "chat", return_value=respuesta):
            resultado = hook_matrix_service.generar("lámpara LED")
        self.assertTrue(resultado["gate_pass"])
        self.assertEqual(resultado["total_hooks"], 12)
        mid = hook_matrix_service.guardar(self.db, None, resultado)
        filas = hook_matrix_service.listar(self.db)
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["id"], mid)
        self.assertTrue(filas[0]["gate_pass"])
        self.assertEqual(len(filas[0]["hooks"]), 12)

    def test_matriz_insuficiente_no_pasa_el_gate_pero_se_puede_guardar_igual(self):
        respuesta = json.dumps({"hook_matrix": _doce_hooks_validos()[:5], "recomendacion_test": ""})
        with mock.patch.object(hook_matrix_service, "chat", return_value=respuesta):
            resultado = hook_matrix_service.generar("producto")
        self.assertFalse(resultado["gate_pass"])
        self.assertTrue(resultado["gate_violations"])
        hook_matrix_service.guardar(self.db, None, resultado)
        self.assertFalse(hook_matrix_service.listar(self.db)[0]["gate_pass"])

    def test_filtra_por_producto(self):
        respuesta = json.dumps({"hook_matrix": _doce_hooks_validos()})
        with mock.patch.object(hook_matrix_service, "chat", return_value=respuesta):
            r = hook_matrix_service.generar("x")
        hook_matrix_service.guardar(self.db, 5, r)
        hook_matrix_service.guardar(self.db, 9, r)
        self.assertEqual(len(hook_matrix_service.listar(self.db, producto_id=5)), 1)
        self.assertEqual(len(hook_matrix_service.listar(self.db)), 2)


if __name__ == "__main__":
    unittest.main()
