"""
Suite de Tests Unitarios — GEM OS Suite (Cobertura 80%+)
==========================================================
Ejecucion: python -m pytest governance/tests/ -v
"""

import sys
import os
import unittest
import tempfile
import json
import shutil
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'app'))


class TestFinancialValidator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.tmpdir, "test.db")
        from app.database.connection import DatabaseConnection
        cls.db = DatabaseConnection(db_path=cls.db_path)
        from app.services.financial_validator import FinancialValidator
        cls.validator = FinancialValidator(db_manager=cls.db)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_sin_pvp_usa_objetivo_3x_sobre_coste_landed(self):
        r = self.validator.validar_producto("TEST-001", 10.0, 0.5, costo_envio=2.0)
        self.assertEqual(r['costo_landed'], 12.0)
        self.assertEqual(r['pvp_calculado'], 36.0)
        self.assertTrue(r['objetivo_x3_cumple'])

    def test_por_debajo_de_2x_se_rechaza(self):
        # $5 producto + $2 envío = $7 landed; PVP $13 = 1,86x  (sobre el producto solo sería 2,6x)
        r = self.validator.validar_producto("TEST-002", 5.0, 0.5, 13.0, costo_envio=2.0)
        self.assertFalse(r['validado'])
        self.assertEqual(r['status_validacion'], 'rechazado')

    def test_entre_2x_y_3x_valida_con_advertencia(self):
        r = self.validator.validar_producto("TEST-003", 5.0, 0.5, 15.0, costo_envio=2.0)   # 2,14x
        self.assertTrue(r['validado'])
        self.assertFalse(r['objetivo_x3_cumple'])
        self.assertTrue(any('x3' in a for a in r['advertencias']))

    def test_el_peso_no_rechaza(self):
        # El curso no fija límite de peso: un producto pesado no se rechaza por eso
        r = self.validator.validar_producto("TEST-004", 10.0, 5.0, 30.0)
        self.assertTrue(r['validado'])

    def test_margen_neto_descuenta_fees_y_cancelaciones(self):
        r = self.validator.validar_producto("TEST-005", 5.0, 0.5, 15.0, costo_envio=2.0)
        esperado = 15.0 - 7.0 - 15.0 * 0.04 - 15.0 * 0.101
        self.assertAlmostEqual(r['margen_neto_unidad'], round(esperado, 2), places=2)

    def test_producto_completo_valido(self):
            # PVP = costo*3 = 30 sin envío: cumple el objetivo x3
            r = self.validator.validar_producto("TEST-006", 10.0, 0.5, 30.0)
            self.assertTrue(r['regla_3x_cumple'])
            self.assertTrue(r['validado'])

    def test_guardar_y_recuperar(self):
        r = self.validator.validar_producto("TEST-007", 10.0, 0.5, 35.0)
        pid = self.validator.guardar_validacion(r)
        self.assertGreater(pid, 0)

    def test_validar_lote(self):
        prods = [
            {'sku': 'LOTE-1', 'costo_origen': 10.0, 'peso_kg': 0.5, 'pvp': 35.0},
            {'sku': 'LOTE-2', 'costo_origen': 10.0, 'peso_kg': 0.5, 'pvp': 15.0},   # 1,5x: rechazado
        ]
        resultados, validados, rechazados = self.validator.validar_lote(prods)
        self.assertEqual(len(resultados), 2)
        self.assertGreaterEqual(rechazados, 1)


class TestCopywrightingEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.tmpdir, "test.db")
        from app.database.connection import DatabaseConnection
        cls.db = DatabaseConnection(db_path=cls.db_path)
        from app.services.copywriting_engine import CopywrightingEngine
        cls.engine = CopywrightingEngine(db_manager=cls.db)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_generar_copy_template(self):
        copy = self.engine.generar_copy_template("Test", "tecnologia", 10.0, 35.0, 0.5)
        self.assertIn('titulo', copy)

    def test_validar_sin_superlativos_ok(self):
        valido, adjs = self.engine.validar_sin_superlativos("Producto de calidad")
        self.assertTrue(valido)

    def test_validar_sin_superlativos_fail(self):
            valido, adjs = self.engine.validar_sin_superlativos("Producto increíble y fantástico")
            self.assertFalse(valido)
            self.assertGreater(len(adjs), 0)

    def test_calcular_scores_aida(self):
        scores = self.engine.calcular_scores_aida("Titulo", "Descripcion con soluciona mejora compra")
        self.assertIn('promedio', scores)

    def test_obtener_contexto_kb(self):
        ctx = self.engine.obtener_contexto_kb(limite=2)
        self.assertIsInstance(ctx, str)

    def test_cargar_contexto_archivos(self):
        ctx = self.engine._cargar_contexto_archivos()
        self.assertIsInstance(ctx, str)

    def test_generar_con_openrouter_sin_api_key(self):
        """Debe caer en fallback template cuando no hay API key."""
        import os
        original_key = os.environ.get('OPENROUTER_API_KEY', '')
        if 'OPENROUTER_API_KEY' in os.environ:
            del os.environ['OPENROUTER_API_KEY']
            # Mock the hybrid pool to simulate failure (no API key)
            original_pool = self.engine._hybrid_pool
            self.engine._hybrid_pool = None
            try:
                copy = self.engine.generar_con_openrouter("Test", "tecnologia", 10.0, 35.0, 0.5)
                self.assertIn('titulo', copy)
                self.assertIn('contexto_fuente', copy)
            finally:
                self.engine._hybrid_pool = original_pool
                if original_key:
                    os.environ['OPENROUTER_API_KEY'] = original_key

        def test_generar_con_openrouter_con_api_key_mock(self):
            """Simula llamada con API key presente (usa fallback por falta de red)."""
            import os
            os.environ['OPENROUTER_API_KEY'] = 'sk-or-v1-test-key-12345'
            # Mock the hybrid pool to simulate failure (no network)
            original_pool = self.engine._hybrid_pool
            self.engine._hybrid_pool = None
            try:
                copy = self.engine.generar_con_openrouter("Test", "tecnologia", 10.0, 35.0, 0.5)
                self.assertIn('titulo', copy)
                self.assertIn('contexto_fuente', copy)
            finally:
                self.engine._hybrid_pool = original_pool
                del os.environ['OPENROUTER_API_KEY']


class TestTikTokScriptGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.tmpdir, "test.db")
        from app.database.connection import DatabaseConnection
        cls.db = DatabaseConnection(db_path=cls.db_path)
        from app.services.tiktok_script_generator import TikTokScriptGenerator
        cls.gen = TikTokScriptGenerator(db_manager=cls.db)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_generar_hook(self):
        hook = self.gen.generar_hook('story-telling')
        self.assertTrue(len(hook) > 0)

    def test_generar_cuerpo(self):
        cuerpo = self.gen.generar_cuerpo("Test", "tecnologia")
        self.assertTrue(len(cuerpo) > 0)

    def test_generar_cta(self):
        cta = self.gen.generar_cta()
        self.assertTrue(len(cta) > 0)

    def test_generar_guion_completo(self):
        guion = self.gen.generar_guion_completo("Test", "tecnologia", 'shock')
        self.assertIn('hook', guion)

    def test_generar_variantes_lote(self):
        variantes = self.gen.generar_variantes_lote("Test", "tecnologia", 3)
        self.assertEqual(len(variantes), 3)

    def test_generar_con_openrouter_sin_api_key(self):
        """Debe caer en fallback template cuando no hay API key."""
        import os
        original_key = os.environ.get('OPENROUTER_API_KEY', '')
        if 'OPENROUTER_API_KEY' in os.environ:
            del os.environ['OPENROUTER_API_KEY']
            # Mock the hybrid pool to simulate failure (no API key)
            original_pool = self.gen._hybrid_pool
            self.gen._hybrid_pool = None
            try:
                guion = self.gen.generar_con_openrouter("Test", "tecnologia")
                self.assertIn('titulo', guion)
                self.assertIn('guion_completo', guion)
            finally:
                self.gen._hybrid_pool = original_pool
                if original_key:
                    os.environ['OPENROUTER_API_KEY'] = original_key

        def test_generar_con_openrouter_con_api_key_mock(self):
            """Simula llamada con API key presente (usa fallback por falta de red)."""
            import os
            os.environ['OPENROUTER_API_KEY'] = 'sk-or-v1-test-key-12345'
            # Mock the hybrid pool to simulate failure (no network)
            original_pool = self.gen._hybrid_pool
            self.gen._hybrid_pool = None
            try:
                guion = self.gen.generar_con_openrouter("Test", "tecnologia")
                self.assertIn('titulo', guion)
                self.assertIn('guion_completo', guion)
            finally:
                self.gen._hybrid_pool = original_pool
                del os.environ['OPENROUTER_API_KEY']


class TestBudgetController(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['AI_MONTHLY_BUDGET_USD'] = '10.0'
        from app.services.budget_controller import BudgetController
        cls.bc = BudgetController()
        cls.bc.reset_monthly()

    def test_allow_request_under_budget(self):
        self.assertTrue(self.bc.allow_request('test'))

    def test_log_operation_free(self):
        cost = self.bc.log_operation('test', 100, 50, 'freellm', 'free')
        self.assertEqual(cost, 0.0)

    def test_log_operation_paid(self):
        cost = self.bc.log_operation('test', 1000, 500, 'openrouter', 'claude-sonnet-4.6')
        self.assertGreater(cost, 0.0)

    def test_remaining_budget(self):
        self.assertGreater(self.bc.get_remaining_budget(), 0)

    def test_usage_ratio(self):
        self.assertGreaterEqual(self.bc.get_usage_ratio(), 0)

    def test_is_blocked_false_initially(self):
        self.assertFalse(self.bc.is_blocked())


class TestExportPack(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_export_csv(self):
        from app.services.export_pack import export_to_csv
        data = [{'sku': 'T1', 'pvp': 29.99}]
        path = export_to_csv(data, os.path.join(self.tmpdir, 'test.csv'))
        self.assertTrue(os.path.exists(path))

    def test_export_html(self):
        from app.services.export_pack import export_to_html
        data = [{'sku': 'T1', 'pvp': 29.99}]
        path = export_to_html(data, os.path.join(self.tmpdir, 'test.html'))
        self.assertTrue(os.path.exists(path))

    def test_export_copy_txt(self):
        from app.services.export_pack import export_copy_to_txt
        copy = {'titulo': 'Test', 'descripcion': 'Desc', 'scores_aida': {'attention': 80, 'interest': 70, 'decision': 60, 'action': 90, 'promedio': 75}, 'sin_superlativos': True, 'contexto_fuente': 'test'}
        path = export_copy_to_txt(copy, os.path.join(self.tmpdir, 'copy.txt'))
        self.assertTrue(os.path.exists(path))

    def test_export_guion_txt(self):
        from app.services.export_pack import export_guion_to_txt
        guion = {'titulo': 'Test', 'hook': 'Hook', 'cuerpo': 'Body', 'cta': 'Buy', 'patron_hook': 'shock', 'duracion_segundos': 30}
        path = export_guion_to_txt(guion, os.path.join(self.tmpdir, 'guion.txt'))
        self.assertTrue(os.path.exists(path))


class TestMultiLang(unittest.TestCase):
    def test_idiomas_disponibles(self):
        from app.services.multi_lang import obtener_idiomas_disponibles
        idiomas = obtener_idiomas_disponibles()
        self.assertIn('en', idiomas)
        self.assertIn('pt', idiomas)
        self.assertIn('es', idiomas)

    def test_traducir_copy_sin_pool(self):
        from app.services.multi_lang import traducir_copy
        # Sin red: un pool que no responde debe dar None (antes se creaba un pool real y se
        # llamaba a la API de verdad en cada ejecución de las pruebas)
        class PoolSinRespuesta:
            def execute_hybrid_query(self, **kwargs):
                return None
        copy = {'titulo': 'Test', 'descripcion': 'Description'}
        self.assertIsNone(traducir_copy(copy, 'en', pool=PoolSinRespuesta()))


class TestTikTokCaptions(unittest.TestCase):
    def test_generar_hashtags(self):
        from app.services.tiktok_captions import generar_hashtags
        tags = generar_hashtags('tecnologia', 'SmartWatch')
        self.assertGreater(len(tags), 0)
        self.assertTrue(all(t.startswith('#') for t in tags))

    def test_generar_hashtags_max(self):
        from app.services.tiktok_captions import generar_hashtags
        tags = generar_hashtags('moda', '', max_tags=3)
        self.assertLessEqual(len(tags), 3)


class TestTrafficAnalyzer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.tmpdir, "test.db")
        from app.database.connection import DatabaseConnection
        cls.db = DatabaseConnection(db_path=cls.db_path)
        from app.services.traffic_analyzer import TrafficAnalyzer
        cls.analyzer = TrafficAnalyzer(db_manager=cls.db)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_clasificar_producto(self):
        r = self.analyzer.clasificar_producto("SmartWatch Pro", "tecnologia")
        self.assertIn('nicho', r)

    def test_calcular_trend_score_ai_weighted(self):
        from app.services.traffic_analyzer import calcular_trend_score_ai_weighted
        r = calcular_trend_score_ai_weighted("SmartWatch", "tecnologia", 5, 0.3, 0.78)
        self.assertIn('score_total', r)
        self.assertGreater(r['score_total'], 50)

    def test_obtener_datos_para_grafico(self):
        from app.services.traffic_analyzer import obtener_datos_para_grafico
        r = obtener_datos_para_grafico(self.analyzer)
        self.assertIn('nichos', r)


class TestSanitizeAPIKey(unittest.TestCase):
    def test_sanitize_normal(self):
        from app.services.openrouter_client import sanitize_api_key
        self.assertEqual(sanitize_api_key('sk-or-v1-test12345678'), 'sk-...5678')

    def test_sanitize_empty(self):
        from app.services.openrouter_client import sanitize_api_key
        self.assertEqual(sanitize_api_key(''), '<vacia>')

    def test_sanitize_short(self):
        from app.services.openrouter_client import sanitize_api_key
        result = sanitize_api_key('abc123')
        # Para keys cortas, muestra *** + ultimos 4
        self.assertIn('123', result)


class TestAIDARadar(unittest.TestCase):
    def test_draw_radar(self):
        import tkinter as tk
        from app.ui.components.aida_radar import draw_aida_radar
        root = tk.Tk()
        canvas = tk.Canvas(root, width=220, height=220)
        try:
            draw_aida_radar(canvas, {'attention': 80, 'interest': 65, 'decision': 70, 'action': 90})
            success = True
        except Exception:
            success = False
        root.destroy()
        self.assertTrue(success)


class TestProfileManager(unittest.TestCase):
    def test_create_profile(self):
        from app.services.profile_manager import ProfileManager
        pm = ProfileManager()
        profile = pm.create_profile("Test User")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.name, "Test User")

    def test_list_profiles(self):
        from app.services.profile_manager import ProfileManager
        pm = ProfileManager()
        profiles = pm.list_profiles()
        self.assertIsInstance(profiles, list)


class TestErrorTelemetry(unittest.TestCase):
    def test_telemetry_disabled_by_default(self):
        from app.services.error_telemetry import ErrorTelemetry
        et = ErrorTelemetry()
        self.assertFalse(et.enabled)

    def test_telemetry_enable_disable(self):
        from app.services.error_telemetry import ErrorTelemetry
        et = ErrorTelemetry()
        et.enable()
        self.assertTrue(et.enabled)
        et.disable()
        self.assertFalse(et.enabled)

    def test_log_error_when_disabled(self):
        from app.services.error_telemetry import ErrorTelemetry
        et = ErrorTelemetry()
        et.disable()
        et.log_error("test", ValueError("test error"))
        stats = et.get_stats()
        self.assertEqual(stats['session_errors'], 0)


class TestGoogleSheetsImport(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_validate_imported_data(self):
        from app.services.google_sheets_import import validate_imported_data
        data = [{'sku': 'T1', 'costo_origen': 10.0, 'peso_kg': 0.5, 'pvp': 35.0, 'categoria': 'test'}]
        result = validate_imported_data(data)
        self.assertEqual(result['validos'], 1)

    def test_validate_imported_data_invalid(self):
        from app.services.google_sheets_import import validate_imported_data
        data = [{'sku': 'T1', 'costo_origen': -1, 'peso_kg': -1, 'pvp': -1, 'categoria': ''}]
        result = validate_imported_data(data)
        self.assertEqual(result['invalidos'], 1)


class TestContentScheduler(unittest.TestCase):
    def test_suggest_best_time(self):
        from app.services.content_scheduler import ContentScheduler
        cs = ContentScheduler()
        suggestion = cs.suggest_best_time('tecnologia')
        self.assertIn('hora_sugerida', suggestion)

    def test_get_weekly_plan(self):
        from app.services.content_scheduler import ContentScheduler
        cs = ContentScheduler()
        plan = cs.get_weekly_plan('general')
        self.assertEqual(len(plan), 5)


class TestSecurityAudit(unittest.TestCase):
    def test_audit_runs(self):
        from app.services.security_audit import SecurityAudit
        audit = SecurityAudit()
        report = audit.run_all()
        self.assertIn('total_checks', report)
        self.assertIn('score', report)
        self.assertGreaterEqual(report['total_checks'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)