"""
Deterministic Gate — Verificación no persuadible de salidas de agentes.

POR QUÉ EXISTE ESTE MÓDULO
--------------------------
Maurice Human puso 17 agentes a reconstruir el código de Call of Duty y, para
verificarlos, puso otro agente a vigilarlos. No funcionó: los agentes explicaban
por qué su trabajo era correcto y el monitor simplemente les creía. Solo cuando
montó un test que no se podía persuadir —recompilar cada pieza y compararla con
el original— empezó a detectar los fallos. Entonces los agentes intentaron
manipular el propio test, y tuvo que protegerlo.

GEM OS tenía el mismo defecto: `@gem-qa-validation` es un LLM auditando a otros
LLM. Este módulo es la alternativa: reglas en Python puro, sin llamadas a ningún
modelo, sin interpretación semántica. Un agente no puede argumentar contra una
comparación numérica.

REGLA DE ORO
------------
Ningún agente debe poder editar este archivo. Si una verificación resulta
demasiado estricta, el cambio lo aprueba una persona — nunca el agente al que
la regla le acaba de bloquear una salida.
"""

import re
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ── Superlativos prohibidos ───────────────────────────────────────────────────
# Las políticas de TikTok y Meta sancionan las promesas vacías. Lista cerrada:
# se comprueba por coincidencia exacta de palabra, sin criterio del modelo.
SUPERLATIVOS_PROHIBIDOS = frozenset({
    "increíble", "increible", "fantástico", "fantastico", "alucinante",
    "espectacular", "asombroso", "milagroso", "revolucionario", "único en el mundo",
    "el mejor del mundo", "el mejor producto", "insuperable", "perfecto",
    "garantizado 100", "resultados garantizados", "sin igual", "inigualable",
})

# ── Promesas logísticas irreales ──────────────────────────────────────────────
# El curso muestra 2-5 días (Shopify) y 5-7 días (TikTok Shop). Prometer menos
# sin confirmación del proveedor genera cancelaciones: el P&L real registra un
# 10,1% de la facturación perdido por esa vía (rqMrq2MGdpw).
PATRONES_ENVIO_IRREAL = [
    re.compile(r"\b24\s*[-–/]?\s*48\s*h", re.IGNORECASE),
    re.compile(r"\benv[íi]o\s+(express|exprés|inmediato|urgente)\b", re.IGNORECASE),
    re.compile(r"\b(entrega|recíbelo|recibelo)\s+(mañana|hoy|en\s+24)", re.IGNORECASE),
    re.compile(r"\b1\s*[-–]\s*2\s*d[íi]as\b", re.IGNORECASE),
]


@dataclass
class GateResult:
    """Resultado de una verificación. `passed` es la única señal que cuenta."""
    passed: bool
    check_name: str
    violations: List[str] = field(default_factory=list)
    evidence: Dict = field(default_factory=dict)

    def __str__(self) -> str:
        estado = "PASS" if self.passed else "FAIL"
        return f"[{estado}] {self.check_name}: {len(self.violations)} violación(es)"


# ── Verificaciones ────────────────────────────────────────────────────────────

def check_superlativos(texto: str) -> GateResult:
    """Busca superlativos de la lista cerrada. Sin interpretación semántica."""
    bajo = texto.lower()
    encontrados = [s for s in SUPERLATIVOS_PROHIBIDOS if s in bajo]
    return GateResult(
        passed=not encontrados,
        check_name="superlativos_prohibidos",
        violations=[f"Superlativo prohibido: '{s}'" for s in encontrados],
        evidence={"encontrados": encontrados},
    )


def check_promesas_envio(texto: str) -> GateResult:
    """Detecta plazos de envío que el proveedor no puede sostener."""
    hits = []
    for patron in PATRONES_ENVIO_IRREAL:
        hits.extend(patron.findall(texto))
    return GateResult(
        passed=not hits,
        check_name="promesas_envio_irreales",
        violations=[f"Promesa de envío no sostenible: '{h}'" for h in hits],
        evidence={"coincidencias": [str(h) for h in hits]},
    )


def check_specs_inmutables(texto_generado: str, specs_proveedor: Dict) -> GateResult:
    """
    Comprueba que los datos duros del proveedor aparezcan sin alterar.

    Alterar dimensiones, pesos o materiales provoca contracargos y bloqueos de
    pasarela. La comprobación es textual: el valor del proveedor está en el
    texto, o no está.
    """
    violaciones = []
    for campo, valor in specs_proveedor.items():
        if valor is None or valor == "":
            continue
        valor_str = str(valor).strip()
        # Solo verificamos campos cuyo nombre aparece mencionado en el texto
        if campo.lower() in texto_generado.lower() and valor_str not in texto_generado:
            violaciones.append(
                f"El texto menciona '{campo}' pero no contiene el valor del proveedor "
                f"('{valor_str}')"
            )
    return GateResult(
        passed=not violaciones,
        check_name="specs_inmutables",
        violations=violaciones,
        evidence={"specs_verificadas": list(specs_proveedor.keys())},
    )


def check_aritmetica_financiera(
    costo_origen: float,
    costo_envio: float,
    pvp: float,
    multiplicador_declarado: float,
    fx_rate: float = 1.0,
    tolerancia: float = 0.01,
) -> GateResult:
    """
    Recalcula el multiplicador desde los costes crudos y lo compara con el
    que declaró el agente.

    Este es el equivalente a recompilar el binario y compararlo: si el número
    no cuadra, no cuenta, sin importar cómo lo justifique el agente.

    El recálculo parte siempre de los inputs originales (coste producto, coste
    envío, tipo de cambio) — nunca del coste landed que venga ya calculado en
    la salida, que es justo el valor que se quiere verificar.

    Args:
        fx_rate: tipo aplicado si el coste y el PVP están en divisas distintas.
                 1.0 cuando comparten divisa.
    """
    landed = (costo_origen + costo_envio) * fx_rate
    if landed <= 0:
        return GateResult(
            passed=False,
            check_name="aritmetica_financiera",
            violations=["Coste landed es cero o negativo — imposible calcular"],
            evidence={"costo_landed": landed},
        )

    real = pvp / landed
    desvio = abs(real - multiplicador_declarado)
    ok = desvio <= tolerancia

    violaciones = []
    if not ok:
        violaciones.append(
            f"Multiplicador declarado {multiplicador_declarado:.2f}x no coincide con "
            f"el real {real:.2f}x (PVP {pvp:.2f} / landed {landed:.2f} "
            f"[({costo_origen} + {costo_envio}) × fx {fx_rate}]). "
            f"Desvío {desvio:.2f} supera la tolerancia {tolerancia}"
        )

    return GateResult(
        passed=ok,
        check_name="aritmetica_financiera",
        violations=violaciones,
        evidence={
            "costo_landed": round(landed, 2),
            "fx_rate": fx_rate,
            "multiplicador_real": round(real, 2),
            "multiplicador_declarado": multiplicador_declarado,
            "desvio": round(desvio, 4),
        },
    )


def check_estructura_json(data: Dict, campos_requeridos: List[str]) -> GateResult:
    """Verifica que la salida traiga todos los campos del contrato."""
    faltantes = [c for c in campos_requeridos if c not in data or data[c] is None]
    return GateResult(
        passed=not faltantes,
        check_name="estructura_json",
        violations=[f"Campo requerido ausente o nulo: '{c}'" for c in faltantes],
        evidence={"faltantes": faltantes, "presentes": list(data.keys())},
    )


def check_utf8_integridad(texto: str) -> GateResult:
    """Detecta mojibake y caracteres de reemplazo típicos de encoding roto."""
    marcadores = ["�", "Ã©", "Ã¡", "Ã±", "Ã³", "Ãº", "â€"]
    hits = [m for m in marcadores if m in texto]
    return GateResult(
        passed=not hits,
        check_name="utf8_integridad",
        violations=[f"Carácter corrupto detectado: '{m}'" for m in hits],
        evidence={"marcadores": hits},
    )


# ── Orquestación ──────────────────────────────────────────────────────────────

def verificar_copy(
    texto: str,
    specs_proveedor: Optional[Dict] = None,
) -> Dict:
    """
    Pasa un texto comercial por todas las verificaciones aplicables.

    Returns:
        {'passed': bool, 'checks': [...], 'violations': [...]}
    """
    resultados = [
        check_superlativos(texto),
        check_promesas_envio(texto),
        check_utf8_integridad(texto),
    ]
    if specs_proveedor:
        resultados.append(check_specs_inmutables(texto, specs_proveedor))

    todas = [v for r in resultados for v in r.violations]
    passed = all(r.passed for r in resultados)

    if not passed:
        logger.warning(f"[GATE] Copy rechazado: {len(todas)} violación(es)")

    return {
        "passed": passed,
        "checks": [str(r) for r in resultados],
        "violations": todas,
        "detail": {r.check_name: r.evidence for r in resultados},
    }


def verificar_validacion_financiera(validacion: Dict) -> Dict:
    """
    Reverifica la salida de FinancialValidator recalculando los números.

    No confía en los campos que vienen en el dict: los recalcula desde los
    costes de entrada y compara.
    """
    requeridos = ["costo_origen", "pvp_calculado", "multiplicador", "costo_landed"]
    estructura = check_estructura_json(validacion, requeridos)
    if not estructura.passed:
        return {
            "passed": False,
            "checks": [str(estructura)],
            "violations": estructura.violations,
            "detail": {estructura.check_name: estructura.evidence},
        }

    aritmetica = check_aritmetica_financiera(
        costo_origen=validacion["costo_origen"],
        costo_envio=validacion.get("costo_envio", 0.0),
        pvp=validacion["pvp_calculado"],
        multiplicador_declarado=validacion["multiplicador"],
    )

    resultados = [estructura, aritmetica]
    todas = [v for r in resultados for v in r.violations]
    passed = all(r.passed for r in resultados)

    if not passed:
        logger.error(f"[GATE] Validación financiera inconsistente: {todas}")

    return {
        "passed": passed,
        "checks": [str(r) for r in resultados],
        "violations": todas,
        "detail": {r.check_name: r.evidence for r in resultados},
    }
