"""
test_governance.py — Tests de Validación del Sistema de Gobernanza GEM OS v2.0
Verifica el cumplimiento de las 4 metodologías del agent.md.
"""
import os, sys, json, unittest, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app'))
from app.services.validator_rules import RulesValidator
from app.services.memory_logger import MemoryLogger
from app.services.protocol_enforcer import ProtocolEnforcer


class TestRulesValidator(unittest.TestCase):
    """Tests para Validador de Cumplimiento (Metodologías 1-4)."""

    @classmethod
    def setUpClass(cls):
        cls.validator = RulesValidator(agent_md_path="agent.md")

    def test_01_agent_md_exists(self):
        ok, msg = self.validator._check_agent_md()
        self.assertTrue(ok, f"agent.md no válido: {msg}")

    def test_02_no_invent_policy(self):
        ok, msg = self.validator._check_no_invent_policy()
        self.assertTrue(ok, f"No inventar: {msg}")

    def test_03_memory_available(self):
        ok, msg = self.validator._check_memory_available()
        self.assertTrue(ok, f"Memoria: {msg}")

    def test_04_business_rules(self):
        ok, msg = self.validator._check_business_rules()
        self.assertTrue(ok, f"Reglas negocio: {msg}")

    def test_05_pre_execution_check_pass(self):
        result = self.validator.pre_execution_check()
        self.assertEqual(result['status'], 'PASS',
                         f"Pre-flight falló: {json.dumps(result.get('resultados', {}), indent=2)}")

    def test_06_compliance_score_green(self):
        score = self.validator.compliance_score()
        self.assertGreaterEqual(score['compliance_score'], 90,
                                f"Score bajo: {score['compliance_score']}%")
        self.assertEqual(score['status'], 'GREEN')

    def test_07_agent_md_integrity(self):
        integ = self.validator.check_agent_md_integrity()
        self.assertEqual(integ['status'], 'PASS', f"Integridad: {integ.get('detail')}")

    def test_08_post_validation_json(self):
        output = {"agent_id": "test", "status": "success", "data": {"p": "test"},
                   "rules_compliance": {"ok": True}}
        result = self.validator.post_execution_validation("test", output)
        self.assertEqual(result['status'], 'PASS', f"Violations: {result.get('violations')}")

    def test_09_superlativos_detected(self):
        output = {"agent_id": "t", "status": "s", "data": {"copy": "increíble y fantástico!"}}
        result = self.validator.post_execution_validation("t", output)
        v = result.get('violations', [])
        self.assertTrue(any('SUPERLATIVES_FOUND' in x for x in v), f"Debe detectar: {v}")

class TestProtocolEnforcer(unittest.TestCase):
    """Tests del Asegurador 'Preguntar antes de Inventar' (Regla Principal)."""

    @classmethod
    def setUpClass(cls):
        cls.enforcer = ProtocolEnforcer()

    def test_01_detect_data_gaps(self):
        required = {"costo_origen": float, "peso_kg": float, "sku": str, "material": str}
        available = {"sku": "PROD-001", "costo_origen": 15.50}
        gaps = self.enforcer.check_data_gaps(required, available)
        self.assertEqual(len(gaps), 2)
        campos = [g['field'] for g in gaps]
        self.assertIn('peso_kg', campos)
        self.assertIn('material', campos)

    def test_02_no_gaps_when_complete(self):
        required = {"sku": str, "costo_origen": float}
        available = {"sku": "PROD-002", "costo_origen": 20.0}
        gaps = self.enforcer.check_data_gaps(required, available)
        self.assertEqual(len(gaps), 0)

    def test_03_questions_batch(self):
        gaps = [{'field': 'peso_kg', 'expected_type': 'float', 'severity': 'CRITICAL', 'message': 'Req'},
                {'field': 'material', 'expected_type': 'str', 'severity': 'WARNING', 'message': 'Rec'}]
        q = self.enforcer.generate_questions_batch(gaps)
        self.assertIn('CRÍTICOS', q)
        self.assertIn('RECOMENDADOS', q)

    def test_04_block_hallucinations(self):
        output = {"agent_id": "t", "status": "s", "data": {"precio": "$99.99"}}
        blocked, reason = self.enforcer.block_if_hallucinating(output)
        self.assertIsInstance(blocked, bool)

    def test_05_validate_output_clean(self):
        r = self.enforcer.validate_output("Producto claro con datos verificados.")
        self.assertEqual(r['veredict'], 'CLEAN')


class TestMemoryLogger(unittest.TestCase):
    """Tests del Sistema de Memoria Activa (Método 2)."""

    @classmethod
    def setUpClass(cls):
        cls.memory = MemoryLogger(memory_dir=tempfile.mkdtemp())

    def test_01_log_entry(self):
        e = self.memory.log("test", "test", "Prueba", category="test")
        self.assertEqual(e['agent_name'], "test")
        self.assertEqual(e['event_type'], "test")

    def test_02_log_decision(self):
        e = self.memory.log_decision("test", "Ok", "Cumple", ["src"])
        self.assertEqual(e['event_type'], 'decision')

    def test_03_log_error(self):
        e = self.memory.log_error("test", "Error")
        self.assertEqual(e['event_type'], 'error')

    def test_04_log_success(self):
        e = self.memory.log_success("test", "OK")
        self.assertEqual(e['event_type'], 'success')

    def test_05_recall(self):
        es = self.memory.recall("test")
        self.assertGreaterEqual(len(es), 1)

    def test_06_get_context(self):
        c = self.memory.get_context("test", max_entries=5)
        self.assertIsInstance(c, str)
        self.assertGreater(len(c), 10)

    def test_07_stats(self):
        s = self.memory.memory_stats()
        self.assertIn('total_entries', s)
        self.assertIn('agents', s)

    def test_08_clear_memory(self):
        n = self.memory.clear_agent_memory("test")
        es = self.memory.recall("test")
        self.assertEqual(len(es), 0)


class TestIntegration(unittest.TestCase):
    """Tests de integración del sistema de gobernanza completo."""

    def test_01_full_workflow(self):
        v = RulesValidator(agent_md_path="agent.md")
        m = MemoryLogger()
        p = ProtocolEnforcer(validator=v)

        pre = v.pre_execution_check()
        self.assertEqual(pre['status'], 'PASS')

        gaps = p.check_data_gaps({"sku": str, "costo": float}, {"sku": "T-001"})
        self.assertEqual(len(gaps), 1)

        m.log("int_test", "test", "Workflow OK")
        score = v.compliance_score()
        self.assertGreaterEqual(score['compliance_score'], 0)

        print(f"\nWorkflow gobernanza PASS | Score: {score['compliance_score']}% | "
              f"Checks: {score['passed']}/{score['total_checks']}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
    def test_10_hallucinations_detected(self):
        output = {"agent_id": "t", "status": "s", "data": {"pvp": "$49.99"}}
        result = self.validator.post_execution_validation("t", output)
        self.assertIn(result['status'], ['FAIL', 'PASS'])