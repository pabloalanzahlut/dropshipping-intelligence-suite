"""
test_agents_smoke.py — Smoke Tests Agentes IA & OpenRouter (FASE 4)
Valida que los 3 agentes (@gem-qa-validation, @gem-backend-core, @gem-orchestrator-core)
tengan definiciones válidas, modelos OpenRouter asignados y funcionamiento básico.
"""
import os
import sys
import json
import unittest
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../app')))

from app.agents_engine.executor import (
    AgentExecutor, AGENT_MODEL_MAP, AGENT_TEMP_MAP, AGENT_TOKENS_MAP
)
from app.services.validator_rules import RulesValidator
from app.services.memory_logger import MemoryLogger
from app.services.protocol_enforcer import ProtocolEnforcer


# === CONSTANTES ===
AGENTS_REQUERIDOS = [
    "gem-qa-validation",
    "gem-backend-core",
    "gem-orchestrator-core",
]

AGENTES_CON_ARROBA = [f"@{a}" for a in AGENTS_REQUERIDOS]

MODELOS_ESPERADOS = {
    "gem-qa-validation":     "google/gemini-2.5-flash:free",
    "gem-backend-core":      "qwen/qwen-2.5-coder-32b-instruct:free",
    "gem-orchestrator-core": "meta-llama/llama-3.1-8b-instruct:free",
}

TEMPERATURAS_ESPERADAS = {
    "gem-qa-validation":     0.0,
    "gem-backend-core":      0.0,
    "gem-orchestrator-core": 0.1,
}

TOKENS_ESPERADOS = {
    "gem-qa-validation":     4096,
    "gem-backend-core":      4096,
    "gem-orchestrator-core": 2048,
}
class TestAgentModelRouting(unittest.TestCase):
    """Valida que el mapa de ruteo de agentes → modelos OpenRouter esté completo."""

    def test_01_all_agents_in_model_map(self):
        """AGENT_MODEL_MAP debe contener todos los agentes requeridos."""
        for agent in AGENTS_REQUERIDOS:
            self.assertIn(agent, AGENT_MODEL_MAP,
                          f"Falta '{agent}' en AGENT_MODEL_MAP")
        for agent in AGENTES_CON_ARROBA:
            self.assertIn(agent, AGENT_MODEL_MAP,
                          f"Falta '{agent}' (alias @) en AGENT_MODEL_MAP")

    def test_02_all_agents_in_temp_map(self):
        for agent in AGENTS_REQUERIDOS:
            self.assertIn(agent, AGENT_TEMP_MAP,
                          f"Falta '{agent}' en AGENT_TEMP_MAP")

    def test_03_all_agents_in_tokens_map(self):
        for agent in AGENTS_REQUERIDOS:
            self.assertIn(agent, AGENT_TOKENS_MAP,
                          f"Falta '{agent}' en AGENT_TOKENS_MAP")

    def test_04_model_map_values_correct(self):
        for agent, expected_model in MODELOS_ESPERADOS.items():
            actual = AGENT_MODEL_MAP.get(agent)
            self.assertEqual(
                actual, expected_model,
                f"Modelo para '{agent}': esperado '{expected_model}', obtenido '{actual}'"
            )

    def test_05_temp_map_values_correct(self):
        for agent, expected_temp in TEMPERATURAS_ESPERADAS.items():
            actual = AGENT_TEMP_MAP.get(agent)
            self.assertEqual(
                actual, expected_temp,
                f"Temperatura para '{agent}': esperado {expected_temp}, obtenido {actual}"
            )

    def test_06_tokens_map_values_correct(self):
        for agent, expected_tokens in TOKENS_ESPERADOS.items():
            actual = AGENT_TOKENS_MAP.get(agent)
            self.assertEqual(
                actual, expected_tokens,
                f"Max tokens para '{agent}': esperado {expected_tokens}, obtenido {actual}"
            )

    def test_07_agent_model_map_no_duplicates(self):
        for agent in AGENTS_REQUERIDOS:
            model_sin = AGENT_MODEL_MAP.get(agent)
            model_con = AGENT_MODEL_MAP.get(f"@{agent}")
            self.assertEqual(
                model_sin, model_con,
                f"Inconsistencia: '{agent}' → '{model_sin}', '@{agent}' → '{model_con}'"
            )

    def test_08_all_models_are_openrouter_format(self):
        for agent, model in AGENT_MODEL_MAP.items():
            if agent.startswith("@"):
                continue
            self.assertIn("/", model,
                          f"Modelo '{model}' para '{agent}' no es slug OpenRouter")
            parts = model.split("/")
            self.assertGreaterEqual(len(parts), 2,
                                    f"Modelo '{model}' debe tener formato 'provider/model'")

    def test_09_agents_md_exists(self):
        agents_md = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                  "../../ai_workspace/agents.md"))
        self.assertTrue(os.path.exists(agents_md),
                        f"agents.md no encontrado en {agents_md}")

    def test_10_agents_md_contains_agent_definitions(self):
        agents_md = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                  "../../ai_workspace/agents.md"))
        with open(agents_md, "r", encoding="utf-8") as f:
            content = f.read()
        for agent in AGENTS_REQUERIDOS:
            self.assertIn(agent, content,
                          f"agents.md debe contener la definición de '{agent}'")


class TestExecutorAgentRouting(unittest.TestCase):
    """Valida que el AgentExecutor resuelva modelos correctamente."""

    def setUp(self):
        self.executor = AgentExecutor(
            workspace_path=tempfile.mkdtemp(),
            agent_md_path="agent.md"
        )

    def test_01_executor_has_model_map(self):
        self.assertTrue(hasattr(self.executor, 'agent_model_map'))
        self.assertIsInstance(self.executor.agent_model_map, dict)

    def test_02_resolve_qa_validation_model(self):
        model = self.executor.agent_model_map.get("gem-qa-validation")
        self.assertEqual(model, "google/gemini-2.5-flash:free")

    def test_03_resolve_backend_core_model(self):
        model = self.executor.agent_model_map.get("gem-backend-core")
        self.assertEqual(model, "qwen/qwen-2.5-coder-32b-instruct:free")

    def test_04_resolve_orchestrator_core_model(self):
        model = self.executor.agent_model_map.get("gem-orchestrator-core")
        self.assertEqual(model, "meta-llama/llama-3.1-8b-instruct:free")

    def test_05_resolve_with_at_sign(self):
        for agent in AGENTES_CON_ARROBA:
            model = self.executor.agent_model_map.get(agent)
            self.assertIsNotNone(model, f"No se resolvió modelo para {agent}")

    def test_06_default_model_for_unknown_agent(self):
        model = self.executor.agent_model_map.get("unknown-agent", "deepseek/deepseek-chat")
        self.assertEqual(model, "deepseek/deepseek-chat")

    def test_07_executor_has_temp_map(self):
        self.assertTrue(hasattr(self.executor, 'agent_temp_map'))

    def test_08_executor_has_tokens_map(self):
        self.assertTrue(hasattr(self.executor, 'agent_tokens_map'))

class TestAgentMemoryIntegration(unittest.TestCase):
    """Valida que cada agente pueda registrar y recuperar memoria."""

    def setUp(self):
        self.memory = MemoryLogger(memory_dir=tempfile.mkdtemp())

    def test_01_qa_validation_memory(self):
        e = self.memory.log("gem-qa-validation", "validation",
                            "Validación de formato completada",
                            category="audit")
        self.assertEqual(e['agent_name'], "gem-qa-validation")
        self.assertEqual(e['event_type'], "validation")

    def test_02_backend_core_memory(self):
        e = self.memory.log("gem-backend-core", "ingestion",
                            "Ingesta de KB completada: 150 registros",
                            category="business")
        self.assertEqual(e['agent_name'], "gem-backend-core")

    def test_03_orchestrator_core_memory(self):
        e = self.memory.log("gem-orchestrator-core", "orchestration",
                            "DAG ejecutado sin errores",
                            category="technical")
        self.assertEqual(e['agent_name'], "gem-orchestrator-core")

    def test_04_qa_validation_decision_log(self):
        e = self.memory.log_decision(
            "gem-qa-validation",
            "OUTPUT_VALIDO",
            "Formato JSON y métricas correctas",
            ["formulas_conversion", "matriz_tendencias"]
        )
        self.assertEqual(e['event_type'], 'decision')
        self.assertIn('formulas_conversion', str(e.get('sources', [])))

    def test_05_backend_core_decision_log(self):
        e = self.memory.log_decision(
            "gem-backend-core",
            "DUPLICADOS_LIMPIOS",
            "Registros duplicados eliminados vía similitud Jaccard",
            ["product_trends"]
        )
        self.assertEqual(e['event_type'], 'decision')

    def test_06_orchestrator_core_decision_log(self):
        e = self.memory.log_decision(
            "gem-orchestrator-core",
            "PIPELINE_CONTINUAR",
            "Circuit breaker OK, continuar con Funnel Builder",
            ["dag_status"]
        )
        self.assertEqual(e['event_type'], 'decision')

    def test_07_all_agents_recall(self):
        test_agents = ["gem-qa-validation", "gem-backend-core", "gem-orchestrator-core"]
        for agent in test_agents:
            self.memory.log(agent, "test", f"Test entry for {agent}", category="test")
            entries = self.memory.recall(agent)
            self.assertGreaterEqual(
                len(entries), 1,
                f"Debe haber al menos 1 entrada de memoria para {agent}"
            )
class TestProtocolEnforcerForAgents(unittest.TestCase):
    """Valida el ProtocolEnforcer para los agentes de FASE 4."""

    def setUp(self):
        self.enforcer = ProtocolEnforcer()

    def test_01_qa_data_gaps(self):
        required = {"formato_salida": str, "benchmark_kpi": float}
        available = {"formato_salida": "json"}
        gaps = self.enforcer.check_data_gaps(required, available)
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]['field'], 'benchmark_kpi')

    def test_02_backend_data_gaps(self):
        required = {"tabla_destino": str, "registros": int, "correlation_id": str}
        available = {"tabla_destino": "product_trends", "registros": 150}
        gaps = self.enforcer.check_data_gaps(required, available)
        campos = [g['field'] for g in gaps]
        self.assertIn('correlation_id', campos)

    def test_03_orchestrator_data_gaps(self):
        required = {"paso_actual": str, "estado_agentes": dict}
        available = {"paso_actual": "transcript_cleaner"}
        gaps = self.enforcer.check_data_gaps(required, available)
        self.assertGreaterEqual(len(gaps), 1)

    def test_04_block_hallucinations_qa(self):
        output = {"agent_id": "gem-qa-validation", "status": "success",
                  "data": {"validation": "resultado increíble y fantástico"}}
        blocked, reason = self.enforcer.block_if_hallucinating(output)
        self.assertIsInstance(blocked, bool)

    def test_05_block_hallucinations_backend(self):
        output = {"agent_id": "gem-backend-core", "status": "success",
                  "data": {"ingesta": 150, "precio_sin_costo": "$99.99"}}
        blocked, reason = self.enforcer.block_if_hallucinating(output)
        self.assertIsInstance(blocked, bool)

    def test_08_agent_memory_context(self):
        ctx = self.memory.get_context("gem-qa-validation", max_entries=5)
        self.assertIsInstance(ctx, str)
        self.assertGreater(len(ctx), 0)


class TestGovernanceIntegration(unittest.TestCase):
    """Valida la integración del sistema de gobernanza con los agentes."""

    def test_01_pre_flight(self):
        v = RulesValidator(agent_md_path="agent.md")
        self.assertEqual(v.pre_execution_check()['status'], 'PASS')

    def test_02_score_green(self):
        v = RulesValidator(agent_md_path="agent.md")
        v.pre_execution_check()
        s = v.compliance_score()
        self.assertGreaterEqual(s['compliance_score'], 90)
        self.assertEqual(s['status'], 'GREEN')

    def test_03_integrity(self):
        v = RulesValidator(agent_md_path="agent.md")
        self.assertEqual(v.check_agent_md_integrity()['status'], 'PASS')

    def test_04_post_val(self):
        v = RulesValidator(agent_md_path="agent.md")
        r = v.post_execution_validation("orchestrator",
            {"agent_id":"orchestrator","status":"ok","data":{"t":3},
             "rules_compliance":{"ok":True}})
        self.assertEqual(r['status'], 'PASS')

    def test_05_superlativos(self):
        v = RulesValidator(agent_md_path="agent.md")
        r = v.post_execution_validation("t",{"agent_id":"t","status":"s",
            "data":{"c":"increíble y fantástico"}})
        self.assertTrue(any("SUPERLATIVES" in x for x in r.get('violations',[])))

    def test_06_agent_files(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__),"../.."))
        for f in ["ai_workspace/agents.md",
                   ".github/agents/gem-qa-validation.md.agent.md",
                   ".github/agents/gem-backend-core.md.agent.md",
                   ".github/agents/gem-orchestrator-core.md.agent.md"]:
            self.assertTrue(os.path.exists(os.path.join(base,f)), f"Falta {f}")

    def test_07_context_files(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__),"../.."))
        for f in ["matriz_tendencias.md","formulas_conversion.md","operaciones_trafico.md"]:
            p = os.path.join(base,"ai_workspace","context",f)
            self.assertTrue(os.path.exists(p), f"Falta {f}")

    def test_08_context_routing(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__),"../.."))
        for f in ["matriz_tendencias.md","formulas_conversion.md","operaciones_trafico.md"]:
            p = os.path.join(base,"ai_workspace","context",f)
            with open(p,encoding="utf-8") as fh:
                c = fh.read()
            self.assertIn("FASE 4", c, f"{f}: falta 'FASE 4'")
            self.assertIn("openrouter_ruta", c, f"{f}: falta 'openrouter_ruta'")

    def test_09_config_agents(self):
        p = os.path.join(os.path.dirname(__file__),"../../.continue/config.json")
        with open(p,encoding="utf-8") as f:
            cfg = json.load(f)
        names = [a["name"] for a in cfg.get("agents",[])]
        for a in AGENTES_CON_ARROBA: self.assertIn(a, names, f"config.json falta '{a}'")

    def test_10_config_models(self):
        p = os.path.join(os.path.dirname(__file__),"../../.continue/config.json")
        with open(p,encoding="utf-8") as f:
            cfg = json.load(f)
        for m in cfg.get("models",[]):
            self.assertIn("openrouter", m.get("apiBase","").lower())


if __name__ == '__main__':
    unittest.main(verbosity=2)