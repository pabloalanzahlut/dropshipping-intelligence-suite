"""
validator_rules.py - Validador de Cumplimiento de Reglas GEM OS v2.0
Verifica que cada agente cumpla con las 4 metodologias del agent.md
en 3 fases: PRE (antes), DURANTE, POST (despues).
"""

import os
import re
import json
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from app.database.connection import DatabaseConnection


class RulesValidator:
    """Validador de cumplimiento de reglas para agentes GEM OS."""

    VERSION_REQUERIDA = "2.0"
    CRITICAL_ADJETIVOS_PROHIBIDOS = [
        "increible", "alucinante", "fantastico", "asombroso",
        "espectacular", "maravilloso", "extraordinario", "unico",
        "revolucionario", "milagroso", "sorprendente", "impresionante"
    ]

    def __init__(self, agent_md_path: Optional[str] = None, db_manager: Optional[DatabaseConnection] = None):
        from app.config.path_manager import PathManager
        self.agent_md_path = agent_md_path or PathManager.resolve_resource("agent.md")
        self.db_manager = db_manager if db_manager else DatabaseConnection()
        self.agent_md_hash = None
        self.agent_md_content = None
        self.violaciones: List[Dict] = []
        self.checks_ejecutados = 0
        self.checks_fallidos = 0
        self.checks_ok = 0

    def pre_execution_check(self) -> Dict:
        self.violaciones = []
        resultados = {}
        md_ok, md_msg = self._check_agent_md()
        resultados['agent_md_loaded'] = {'status': md_ok, 'detail': md_msg}
        no_inv_ok, no_inv_msg = self._check_no_invent_policy()
        resultados['no_invent_policy'] = {'status': no_inv_ok, 'detail': no_inv_msg}
        mem_ok, mem_msg = self._check_memory_available()
        resultados['memory_available'] = {'status': mem_ok, 'detail': mem_msg}
        rules_ok, rules_msg = self._check_business_rules()
        resultados['business_rules'] = {'status': rules_ok, 'detail': rules_msg}
        all_ok = all(r['status'] for r in resultados.values())
        self.checks_ejecutados += 4
        if all_ok:
            self.checks_ok += 4
        else:
            self.checks_fallidos += sum(1 for r in resultados.values() if not r['status'])
        status = 'PASS' if all_ok else 'FAIL'
        return {'status': status, 'resultados': resultados, 'violaciones': self.violaciones}

    def post_execution_validation(self, agent_name: str, output_data: Dict) -> Dict:
        violations = []
        detalles = {}
        if isinstance(output_data, dict):
            formato_ok = all(k in output_data for k in ['agent_id', 'status', 'data'])
            detalles['json_structure'] = {
                'status': formato_ok,
                'detail': 'JSON valido' if formato_ok else 'Faltan campos requeridos'
            }
            if not formato_ok:
                violations.append('OUTPUT_FORMAT_VIOLATION')
        else:
            detalles['json_structure'] = {'status': False, 'detail': 'No es dict JSON'}
            violations.append('OUTPUT_FORMAT_VIOLATION')
        contenido = str(output_data.get('data', {})) if isinstance(output_data, dict) else str(output_data)
        adjetivos = self._detectar_superlativos(contenido)
        detalles['no_superlativos'] = {
            'status': len(adjetivos) == 0,
            'detail': f'Adjetivos: {adjetivos}' if adjetivos else 'Sin superlativos'
        }
        if adjetivos:
            violations.append("SUPERLATIVES_FOUND:" + (','.join(adjetivos)))
        inv_ok, inv_det = self._detect_hallucinations(output_data)
        detalles['no_hallucinations'] = {'status': inv_ok, 'detail': inv_det}
        if not inv_ok:
            violations.append('HALLUCINATION_DETECTED')
        resultado = {
            'agent_name': agent_name, 'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'PASS' if not violations else 'FAIL',
            'detalles': detalles, 'violations': violations
        }
        self._log_validation_result(agent_name, resultado)
        return resultado

    def check_agent_md_integrity(self) -> Dict:
        ok, msg = self._check_agent_md()
        return {
            'status': 'PASS' if ok else 'CRITICAL', 'detail': msg,
            'hash_actual': self.agent_md_hash,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    # ===================== INTERNAL CHECKS =====================

    def _check_agent_md(self) -> Tuple[bool, str]:
        if not os.path.exists(self.agent_md_path):
            return False, f"agent.md no encontrado en {self.agent_md_path}"
        try:
            with open(self.agent_md_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return False, f"No se pudo leer agent.md: {str(e)}"
        if not content.strip():
            return False, "agent.md esta vacio"
        nuevo_hash = hashlib.sha256(content.encode()).hexdigest()
        if self.agent_md_hash and self.agent_md_hash != nuevo_hash:
            self.violaciones.append({
                'tipo': 'GOVERNANCE_VIOLATION:WARNING',
                'detalle': 'agent.md modificado desde ultima verificacion',
                'hash_anterior': self.agent_md_hash, 'hash_nuevo': nuevo_hash
            })
        self.agent_md_hash = nuevo_hash
        self.agent_md_content = content
        return True, f"agent.md OK [{nuevo_hash[:12]}...]"

    def _check_no_invent_policy(self) -> Tuple[bool, str]:
        if not self.agent_md_content:
            return False, "agent.md no cargado"
        keywords = ['PREGUNTAR al usuario', 'NO INVENTAR', 'alucinar', 'falta un dato', 'DATA_GAP']
        found = sum(1 for kw in keywords if kw.lower() in self.agent_md_content.lower())
        return (True, f'Politica OK ({found}/5)') if found >= 2 else (False, f'Solo {found}/5 keywords')

    def _check_memory_available(self) -> Tuple[bool, str]:
        mem_dir = "governance/memory"
        try:
            os.makedirs(mem_dir, exist_ok=True)
            return True, f"Memoria disponible en {mem_dir}"
        except Exception as e:
            return False, f"No se pudo crear: {str(e)}"

    def _check_business_rules(self) -> Tuple[bool, str]:
        # Reglas que agent.md debe contener: las del curso de Adrián Sáenz. Antes se exigían
        # «Margen 70%» y «Peso 1.2 kg», que el curso NO fija y se retiraron de agent.md;
        # con ellas el pre-flight fallaba siempre y bloqueaba a todos los agentes.
        rules_hints = {'Mínimo 2x': '* 2', 'Objetivo 3x': '* 3', 'ROAS': 'ROAS',
                       'AIDA': 'AIDA', 'Superlativos': 'superlativos'}
        if not self.agent_md_content:
            return False, "agent.md no cargado"
        missing = [n for n, h in rules_hints.items() if h.lower() not in self.agent_md_content.lower()]
        return (False, f'Faltan: {", ".join(missing)}') if missing else (True, 'Todas OK')

    @staticmethod
    def _sin_tildes(texto: str) -> str:
        import unicodedata
        return unicodedata.normalize('NFD', texto or '').encode('ascii', 'ignore').decode().lower()

    def _detectar_superlativos(self, texto: str) -> List[str]:
        """Detecta superlativos vacíos ignorando tildes ("increíble" = "increible") y solo
        como palabra completa o su plural/género ("único" sí, "unicornio" no)."""
        tl = self._sin_tildes(texto)
        return [a for a in self.CRITICAL_ADJETIVOS_PROHIBIDOS
                if re.search(r'\b' + re.escape(self._sin_tildes(a)) + r'(?:s|es|a|as|os)?\b', tl)]

    def _detect_hallucinations(self, data: Dict) -> Tuple[bool, str]:
        if not isinstance(data, dict):
            return True, "No analizable"
        ds = json.dumps(data).lower()
        sospechas = []
        if '$' in ds and 'costo' not in ds and 'cost' not in ds:
            sospechas.append('precio sin costo base')
        for m in ['%', 'tasa', 'ratio']:
            if m in ds and 'benchmark' not in ds:
                sospechas.append(f'metrica {m} sin benchmark')
        return (False, f'Alucinaciones: {", ".join(sospechas)}') if sospechas else (True, 'Sin indicios')

    def _log_validation_result(self, agent_name: str, resultado: Dict):
        try:
            with self.db_manager.get_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    CREATE TABLE IF NOT EXISTS governance_validations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        agent_name TEXT NOT NULL, status TEXT NOT NULL,
                        violations TEXT, detalles TEXT,
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                c.execute("INSERT INTO governance_validations (agent_name,status,violations,detalles) VALUES (?,?,?,?)",
                          (agent_name, resultado.get('status', 'UNKNOWN'),
                           json.dumps(resultado.get('violations', [])),
                           json.dumps(resultado.get('detalles', {}))))
                conn.commit()
        except Exception as e:
            print(f"[RulesValidator] Warning: {str(e)}")

    def get_validation_history(self, agent_name: Optional[str] = None, limit: int = 50) -> List[Dict]:
        try:
            with self.db_manager.get_connection() as conn:
                c = conn.cursor()
                if agent_name:
                    c.execute("SELECT * FROM governance_validations WHERE agent_name=? ORDER BY timestamp DESC LIMIT ?",
                              (agent_name, limit))
                else:
                    c.execute("SELECT * FROM governance_validations ORDER BY timestamp DESC LIMIT ?", (limit,))
                rows = c.fetchall()
                cols = [d[0] for d in c.description]
                return [dict(zip(cols, r)) for r in rows]
        except Exception as e:
            print(f"[RulesValidator] Error: {str(e)}")
            return []

    def compliance_score(self) -> Dict:
        total = self.checks_ejecutados
        ok = self.checks_ok
        score = round((ok / total) * 100, 1) if total > 0 else 0.0
        return {
            'total_checks': total, 'passed': ok, 'failed': self.checks_fallidos,
            'compliance_score': score,
            'status': 'GREEN' if score >= 90 else ('YELLOW' if score >= 70 else 'RED'),
            'violaciones_activas': len(self.violaciones),
            'ultima_actualizacion': datetime.now(timezone.utc).isoformat()
        }
