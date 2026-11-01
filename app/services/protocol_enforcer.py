"""
protocol_enforcer.py — Asegurador de "PREGUNTAR antes de INVENTAR" GEM OS v2.0
Implementa el punto 2.2 del agent.md (Prioridad Absoluta: NO INVENTAR).
Detecta datos faltantes y fuerza al agente a preguntar al usuario.
"""

import re
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
from app.services.validator_rules import RulesValidator


class ProtocolEnforcer:
    """
    Intercepta solicitudes de agentes con datos faltantes.
    Si falta un dato crítico, genera una solicitud de aclaración al usuario.
    Implementa: 'Si al agente le falta un dato, debe PREGUNTAR al usuario'.
    """

    # Campos que NUNCA deben ser inventados
    CRITICAL_FIELDS = [
        'costo_origen', 'peso_kg', 'sku', 'precio_proveedor',
        'dimensiones', 'material', 'pais_origen', 'tiempo_envio'
    ]

    # Patrones de alucinación comunes
    HALLUCINATION_PATTERNS = [
        r'\$\d+\.?\d*\s*(?:USD|dólares|usd)',  # Precios sin fuente
        r'(?:tasa|ratio|porcentaje)\s+de\s+(?:conversión|apertura|click).*?\d+%',
        r'ROI\s+de\s+\d+%',
        r'envío\s+(?:express|gratis|24\s*horas)',
        r'[Mm]argen\s+de\s+\d+%',
    ]

    def __init__(self, validator: Optional[RulesValidator] = None):
        self.validator = validator or RulesValidator()
        self.pending_questions: List[Dict] = []
        self.blocked_executions = 0

    def check_data_gaps(self, required_fields: Dict[str, type],
                        available_data: Dict[str, Any]) -> List[Dict]:
        """
        Verifica si hay datos faltantes en la solicitud de un agente.

        Args:
            required_fields: Dict con campos requeridos y su tipo esperado
            available_data: Datos disponibles que tiene el agente

        Returns:
            Lista de gaps (datos faltantes) encontrados

        Si retorna lista no vacía → el agente DEBE preguntar antes de continuar.
        """
        gaps = []
        for field, expected_type in required_fields.items():
            if field not in available_data or available_data[field] is None:
                gaps.append({
                    'field': field,
                    'expected_type': expected_type.__name__ if hasattr(expected_type, '__name__') else str(expected_type),
                    'severity': 'CRITICAL' if field in self.CRITICAL_FIELDS else 'WARNING',
                    'message': f"El campo '{field}' ({expected_type.__name__ if hasattr(expected_type, '__name__') else str(expected_type)}) no está disponible. "
                               f"Debes preguntar al usuario antes de continuar."
                })
            elif isinstance(available_data[field], str) and not available_data[field].strip():
                gaps.append({
                    'field': field,
                    'expected_type': expected_type.__name__ if hasattr(expected_type, '__name__') else str(expected_type),
                    'severity': 'WARNING',
                    'message': f"El campo '{field}' está vacío. Pregunta al usuario."
                })

        return gaps

    def generate_question(self, gap: Dict) -> str:
        """Genera una pregunta al usuario para resolver un data gap."""
        sicon = "🔴" if gap['severity'] == 'CRITICAL' else "🟡"
        return (f"[PROTOCOLO DATA_GAP] {sicon} El campo '{gap['field']}' "
                f"({gap['expected_type']}) es requerido. Por favor, proporciona este valor.")

    def generate_questions_batch(self, gaps: List[Dict]) -> str:
        """Genera bloque de preguntas para múltiples gaps."""
        if not gaps:
            return ""
        lines = [f"⚠️ Se detectaron {len(gaps)} datos faltantes:", ""]
        crit = [g for g in gaps if g['severity'] == 'CRITICAL']
        warns = [g for g in gaps if g['severity'] != 'CRITICAL']
        if crit:
            lines.append("🔴 DATOS CRÍTICOS (OBLIGATORIOS):")
            for g in crit:
                lines.append(f"  • {g['field']} ({g['expected_type']}) — {g['message']}")
            lines.append("")
        if warns:
            lines.append("🟡 DATOS RECOMENDADOS:")
            for g in warns:
                lines.append(f"  • {g['field']} ({g['expected_type']}) — {g['message']}")
            lines.append("")
        lines.append("Responde con los valores solicitados para continuar.")
        self.pending_questions.extend(gaps)
        return '\n'.join(lines)

    def validate_output(self, agent_output: str) -> Dict:
        """Valida salida del agente buscando alucinaciones."""
        findings = []
        for pattern in self.HALLUCINATION_PATTERNS:
            matches = re.findall(pattern, agent_output, re.IGNORECASE)
            if matches:
                findings.append({'pattern': pattern, 'matches': matches[:5], 'severity': 'WARNING'})
        return {
            'length': len(agent_output),
            'suspicious': len(findings),
            'findings': findings,
            'veredict': 'BLOCKED' if len(findings) >= 3 else 'FLAGGED' if findings else 'CLEAN'
        }

    def block_if_hallucinating(self, output_data: Dict) -> Tuple[bool, str]:
        """Bloquea salida si detecta alucinaciones."""
        if isinstance(output_data, dict) and 'agent_id' in output_data:
            result = self.validator.post_execution_validation(
                output_data.get('agent_id', 'unknown'), output_data)
            if result['status'] == 'FAIL':
                self.blocked_executions += 1
                return (True, f"Bloqueado: {result.get('violations', [])}")
        return (False, "Sin bloqueos")

    def get_stats(self) -> Dict:
        """Estadísticas del enforcer."""
        return {
            'pending_questions': len(self.pending_questions),
            'blocked': self.blocked_executions,
            'critical_fields': self.CRITICAL_FIELDS
        }

    def create_required_fields_request(self, fields: List[Dict[str, type]]) -> str:
        """Crea bloque estructurado para solicitar datos al usuario."""
        lines = [
            "=== DIRECTRICES: DATOS REQUERIDOS ===",
            "Los siguientes campos son OBLIGATORIOS.",
            "Si NO dispones de ellos, DEBES PREGUNTAR al usuario.",
            "ESTÁ PROHIBIDO INVENTAR O ESTIMAR ESTOS VALORES.", ""
        ]
        for fi in fields:
            for fn, ft in fi.items():
                lines.append(f"  • {fn} ({ft.__name__}): REQUERIDO")
        lines.extend(["", "Ante duda → ejecuta protocolo DATA_GAP_REQUEST."])
        return '\n'.join(lines)