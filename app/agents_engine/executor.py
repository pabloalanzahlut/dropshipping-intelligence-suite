"""
executor.py — Orquestador Maestro GEM OS v2.0
Integra las 4 metodologías del agent.md:
1. REGLA PRINCIPAL: agent.md, no inventar, memoria
2. MÉTODO 1: Herramientas externas, formato técnico
3. MÉTODO 2: Agentes encadenados, memoria secuencial
4. MÉTODO 3: Manejo de errores, formato JSON
"""

import os, json, requests
from typing import Dict, Any, Optional, Tuple
from app.database.connection import DatabaseConnection
from app.services.validator_rules import RulesValidator
from app.services.memory_logger import MemoryLogger
from app.services.protocol_enforcer import ProtocolEnforcer


# Mapa de ruteo de agentes → modelos OpenRouter (FASE 4)
# Cada agente usa un modelo específico según su rol y criticidad.
AGENT_MODEL_MAP = {
    "gem-qa-validation":     "google/gemini-2.5-flash:free",
    "gem-backend-core":      "qwen/qwen-2.5-coder-32b-instruct:free",
    "gem-orchestrator-core": "meta-llama/llama-3.1-8b-instruct:free",
    # Aliases con @
    "@gem-qa-validation":     "google/gemini-2.5-flash:free",
    "@gem-backend-core":      "qwen/qwen-2.5-coder-32b-instruct:free",
    "@gem-orchestrator-core": "meta-llama/llama-3.1-8b-instruct:free",
}

# Temperatura por agente
AGENT_TEMP_MAP = {
    "gem-qa-validation":     0.0,
    "gem-backend-core":      0.0,
    "gem-orchestrator-core": 0.1,
    "@gem-qa-validation":     0.0,
    "@gem-backend-core":      0.0,
    "@gem-orchestrator-core": 0.1,
}

# Max tokens por agente
AGENT_TOKENS_MAP = {
    "gem-qa-validation":     4096,
    "gem-backend-core":      4096,
    "gem-orchestrator-core": 2048,
    "@gem-qa-validation":     4096,
    "@gem-backend-core":      4096,
    "@gem-orchestrator-core": 2048,
}


class AgentExecutor:
    """Orquestador determinista con validación de cumplimiento."""

    def __init__(self, workspace_path: str = "ai_workspace",
                 db_manager: Optional[DatabaseConnection] = None,
                 agent_md_path: str = "agent.md"):
        self.workspace_path = workspace_path
        self.db_manager = db_manager if db_manager else DatabaseConnection()
        # NUEVO: Gobernanza centralizada
        self.validator = RulesValidator(agent_md_path=agent_md_path, db_manager=self.db_manager)
        self.memory = MemoryLogger(db_manager=self.db_manager)
        self.enforcer = ProtocolEnforcer(validator=self.validator)
        # Existente
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.governance_file = os.path.join(self.workspace_path, "agents.md")
        self.memory_dir = os.path.join(self.workspace_path, "memory")
        self.skills_dir = os.path.join(self.workspace_path, "skills")
        self.projects_dir = os.path.join(self.workspace_path, "projects")
        # FASE 4: Mapa de modelos OpenRouter por agente
        self.agent_model_map = AGENT_MODEL_MAP
        self.agent_temp_map = AGENT_TEMP_MAP
        self.agent_tokens_map = AGENT_TOKENS_MAP

    def _read_file(self, fp: str) -> str:
        if os.path.exists(fp):
            with open(fp, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def _write_file(self, fp: str, content: str):
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)

    def log_to_memory(self, agent_name: str, event_type: str, log_message: str):
        """Compatibilidad con sistema legacy de memoria."""
        mf = os.path.join(self.memory_dir, f"{agent_name}_memory.txt")
        with open(mf, "a", encoding="utf-8") as f:
            f.write(f"[{event_type.upper()}] {log_message}\n")

    # ===================== PRE-FLIGHT (FASE PRE) =====================

    def pre_flight_check(self) -> Dict:
        """Verificacion PRE-VUELO (punto 2.4 del agent.md)."""
        result = self.validator.pre_execution_check()
        self.memory.log('system_orchestrator', 'pre_flight',
                        f"Pre-flight: {result['status']}",
                        category='technical',
                        details={'checks': result.get('resultados', {})})
        return result

    def check_data_gaps_before_run(self, required_fields: Dict[str, type],
                                   available_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Verifica data gaps (punto 2.2 agent.md: preguntar antes de inventar)."""
        gaps = self.enforcer.check_data_gaps(required_fields, available_data)
        if gaps:
            qs = self.enforcer.generate_questions_batch(gaps)
            self.memory.log('system_orchestrator', 'data_gap',
                            f"Faltan {len(gaps)} datos", category='warning',
                            details={'gaps': gaps})
            return False, qs
        return True, "Datos completos"

    # ===================== MANEJO DE ERRORES (Metodo 3) =====================

    def handle_agent_error(self, agent_name: str, error_description: str, current_skill_path: str) -> str:
        """Implementa Mitjana: corrige skill en lugar de parchar."""
        csc = self._read_file(current_skill_path)
        cp = (f"El resultado de {agent_name} no es correcto.\nError: {error_description}\n"
              f"Analiza: 1) ignoraste skills? 2) inconsistente?\n"
              f"Original:\n```md\n{csc}\n```\nReescribe en {current_skill_path}.")
        hdrs = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        pl = {"model": "google/gemini-flash",
              "messages": [{"role": "system", "content": "QA de GEM OS."},
                           {"role": "user", "content": cp}]}
        try:
            r = requests.post(self.url + "/api/v1/chat/completions", headers=hdrs, json=pl, timeout=60)
            r.raise_for_status()
            up = r.json()['choices'][0]['message']['content'].strip()
            self._write_file(current_skill_path, up)
            self.log_to_memory(agent_name, "permanent_patch", f"Skill corregida: {current_skill_path}")
            return "Skill corregida permanentemente."
        except Exception as e:
            em = f"Error auto-correccion: {str(e)}"
            self.log_to_memory(agent_name, "critical_fault", em)
            return em

    def execute_agent_task(self, agent_name: str, skill_name: str,
                           project_name: str, user_request: str,
                           required_fields: Optional[Dict[str, type]] = None,
                           available_data: Optional[Dict[str, Any]] = None) -> str:
        """Orquestador: PRE-flight -> DATA GAP -> Ejecuta -> POST-valida."""
        # PASO 1: Pre-flight check
        fc = self.pre_flight_check()
        if fc['status'] == 'FAIL':
            err = "[GOVERNANCE BLOCK] Pre-flight fallo"
            self.memory.log_error(agent_name, err, critical=True)
            raise RuntimeError(err)

        # PASO 2: Data gap check (no inventar)
        if required_fields and available_data is not None:
            ok, msg = self.check_data_gaps_before_run(required_fields, available_data)
            if not ok:
                self.memory.log(agent_name, 'data_gap_blocked',
                                "Bloqueado por datos faltantes", category='warning')
                return f"[BLOQUEO POR DATOS FALTANTES]\n\n{msg}"

        # PASO 3: Construir contextos
        governance = self._read_file(self.governance_file)
        skill_path = os.path.join(self.skills_dir, skill_name, "procedimiento.md")
        skill_procedure = self._read_file(skill_path)

        # PASO 4: Memoria activa (Metodo 2)
        memory_context = self.memory.get_context(agent_name, max_entries=15)

        # PASO 5: System prompt con todas las metodologias
        sp = (
            "=== AGENT.md (CONSTITUCION SUPREMA) ===\n"
            f"Hash: {self.validator.agent_md_hash[:16] if self.validator.agent_md_hash else 'N/A'}...\n\n"
            f"=== GOBERNANZA GLOBAL ===\n{governance}\n\n"
            f"=== SKILL ===\n{skill_procedure}\n\n"
            f"=== MEMORIA ACTIVA ===\n{memory_context}\n\n"
            f"Operas como '{agent_name}'. REGLAS:\n"
            "1. NUNCA inventes datos. Si falta algo -> [DATA_GAP: campo]\n"
            "2. No uses superlativos: increible, fantastico, alucinante, etc.\n"
            "3. Responde en JSON estructurado.\n"
            "4. Registra decisiones en tu bitacora.\n"
            "5. Prohibido alterar dimensiones fisicas o simular fletes."
        )

        # FASE 4: Resolver modelo OpenRouter según el agente
        model = self.agent_model_map.get(agent_name, "deepseek/deepseek-chat")
        temperature = self.agent_temp_map.get(agent_name, 0.2)
        max_tokens = self.agent_tokens_map.get(agent_name, 4096)

        self.memory.log(agent_name, 'model_routing',
                        f"Ruteado a modelo: {model} (temp={temperature}, max_tokens={max_tokens})",
                        category='technical')

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": model,
                   "messages": [{"role": "system", "content": sp},
                                {"role": "user", "content": f"Tarea '{project_name}': {user_request}"}],
                   "temperature": temperature,
                   "max_tokens": max_tokens,
                   "response_format": {"type": "json_object"}}

        try:
            r = requests.post(self.url + "/api/v1/chat/completions", headers=headers, json=payload, timeout=60)
            r.raise_for_status()
            output = r.json()['choices'][0]['message']['content'].strip()

            # Guardar
            pf = os.path.join(self.projects_dir, project_name, f"{agent_name}_output.txt")
            self._write_file(pf, output)

            # PASO 6: POST-validacion (FASE POST)
            try:
                data = json.loads(output)
                val = self.validator.post_execution_validation(agent_name, data)
                status = val['status']
            except json.JSONDecodeError:
                self.memory.log(agent_name, 'warning', 'Output no-JSON', category='technical')
                status = 'WARNING'

            self.memory.log(agent_name, 'execution_complete',
                            f"Task '{project_name}': {status}", category='business')
            return output

        except Exception as e:
            raw = str(e)
            self.memory.log_error(agent_name, raw)
            # Fallo doble Mitjana
            mf = os.path.join(self.memory_dir, f"{agent_name}_memory.txt")
            logs = self._read_file(mf).splitlines()[-3:]
            errs = sum(1 for l in logs if "[ERROR]" in l)
            if errs >= 2 or "margen" in user_request.lower():
                print("ACTIVANDO PROTOCOLO MITJANA")
                self.handle_agent_error(agent_name, raw, skill_path)
            raise RuntimeError(raw)
