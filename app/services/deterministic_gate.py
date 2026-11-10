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


# ── Refutar-producto (.claude/commands/refutar-producto.md) ─────────────────
# Constantes propias, independientes de `product_catalog.py`: la gracia de una
# verificación en profundidad es no recalcular con la misma función que se
# quiere auditar — si el skill cambiara, aquí haría falta tocarlo a mano.
_REFUTACIONES_TOTAL = 8
_REFUTACIONES_ELIMINATORIAS = (1, 6)


def check_refutacion_tally(respuestas: Dict) -> GateResult:
    """
    Recalcula el veredicto de refutar-producto desde las 8 respuestas crudas.

    `respuestas` es {numero: {"resultado": "pasa"|"refutada", ...}} (o {numero: "pasa"...}).
    No confía en ningún veredicto que venga ya calculado — solo en el conteo de
    "refutada" por número y en si alguna es eliminatoria (#1 margen, #6 legal).
    """
    estado: Dict[int, str] = {}
    for k, v in (respuestas or {}).items():
        try:
            n = int(k)
        except (TypeError, ValueError):
            continue
        resultado = (v.get("resultado") if isinstance(v, dict) else v) or ""
        if resultado in ("pasa", "refutada"):
            estado[n] = resultado

    faltan = [n for n in range(1, _REFUTACIONES_TOTAL + 1) if n not in estado]
    if faltan:
        return GateResult(
            passed=False, check_name="refutacion_tally",
            violations=[f"Faltan respuestas: {faltan}"],
            evidence={"faltan": faltan, "respondidas": len(estado)},
        )

    refutadas = sorted(n for n, r in estado.items() if r == "refutada")
    eliminatorias = [n for n in refutadas if n in _REFUTACIONES_ELIMINATORIAS]
    if eliminatorias:
        accion = "descartar"
    elif len(refutadas) >= 3:
        accion = "descartar"
    elif refutadas:
        accion = "invertir_test"
    else:
        accion = "invertir"

    return GateResult(
        passed=True, check_name="refutacion_tally", violations=[],
        evidence={"refutadas": refutadas, "eliminatorias": eliminatorias, "accion": accion},
    )


# ── Hook-matrix (.claude/commands/hook-matrix.md) ────────────────────────────
FORMULAS_HOOK = ("Story", "Shock", "Curiosity", "Before/After", "POV", "Urgencia")
_HOOKS_MINIMO_TOTAL = 12
_HOOKS_MINIMO_POR_FORMULA = 2


def check_hook_count(hooks: List[Dict]) -> GateResult:
    """Exige ≥12 hooks totales y ≥2 por cada una de las 6 fórmulas — nunca confía en
    el `total_hooks` que declare el propio LLM."""
    violaciones: List[str] = []
    por_formula: Dict[str, int] = {f: 0 for f in FORMULAS_HOOK}
    desconocidas = []
    for h in (hooks or []):
        formula = str((h or {}).get("formula", "")).strip()
        coincidencia = next((f for f in FORMULAS_HOOK if f.lower() == formula.lower()), None)
        if coincidencia:
            por_formula[coincidencia] += 1
        else:
            desconocidas.append(formula)

    if len(hooks or []) < _HOOKS_MINIMO_TOTAL:
        violaciones.append(f"Solo {len(hooks or [])} hooks; mínimo {_HOOKS_MINIMO_TOTAL}")
    for formula, n in por_formula.items():
        if n < _HOOKS_MINIMO_POR_FORMULA:
            violaciones.append(f"Fórmula '{formula}': {n} hooks; mínimo {_HOOKS_MINIMO_POR_FORMULA}")
    if desconocidas:
        violaciones.append(f"Fórmulas no reconocidas: {sorted(set(desconocidas))}")

    return GateResult(
        passed=not violaciones, check_name="hook_count", violations=violaciones,
        evidence={"total": len(hooks or []), "por_formula": por_formula},
    )


def verificar_hook_matrix(resultado: Dict) -> Dict:
    """`check_hook_count` + `verificar_copy` (superlativos/envío) sobre cada hook."""
    hooks = (resultado or {}).get("hook_matrix") or []
    conteo = check_hook_count(hooks)
    resultados = [conteo]
    violaciones_copy: List[str] = []
    for h in hooks:
        r = verificar_copy(str((h or {}).get("texto", "")))
        if not r["passed"]:
            violaciones_copy.extend(f"Hook #{h.get('id', '?')}: {v}" for v in r["violations"])

    todas = list(conteo.violations) + violaciones_copy
    passed = conteo.passed and not violaciones_copy
    return {
        "passed": passed,
        "checks": [str(conteo), f"copy_por_hook: {len(violaciones_copy)} violación(es)"],
        "violations": todas,
        "detail": {conteo.check_name: conteo.evidence},
    }


# ── Fake-door (.claude/commands/fake-door.md) ────────────────────────────────
_CONCENTRACION_AVISO = 0.8   # >80% de las visitas desde una sola IP: muestra poco fiable


def check_fake_door_ctr(ctr: float, mediana_global: float, visitas: int, concentracion: float = 0.0) -> GateResult:
    """
    Aritmética pura (sin LLM): ≥2× la mediana global → producir; ~mediana (0,5×–2×) →
    repetir; <0,5× → descartar. Sin visitas o sin mediana de referencia, no hay base para
    decidir — se marca como tal en vez de forzar un veredicto.
    """
    if visitas <= 0:
        return GateResult(passed=False, check_name="fake_door_ctr",
                          violations=["Sin visitas registradas — nada que evaluar"],
                          evidence={"veredicto": "sin_datos"})
    if mediana_global <= 0:
        return GateResult(passed=True, check_name="fake_door_ctr", violations=[],
                          evidence={"veredicto": "sin_referencia_historica", "ctr": ctr,
                                    "motivo": "Todavía no hay otros productos probados con los que comparar."})

    ratio = ctr / mediana_global
    if ratio >= 2:
        veredicto = "producir"
    elif ratio < 0.5:
        veredicto = "descartar"
    else:
        veredicto = "repetir"

    avisos = []
    if concentracion >= _CONCENTRACION_AVISO:
        avisos.append(f"{concentracion:.0%} de las visitas vienen de una sola IP — la muestra puede no ser fiable")

    return GateResult(passed=True, check_name="fake_door_ctr", violations=avisos,
                      evidence={"veredicto": veredicto, "ctr": ctr, "mediana_global": mediana_global,
                                "ratio": round(ratio, 2), "concentracion": concentracion})


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
        fx_rate=validacion.get("detalles", {}).get("fx_rate", 1.0),
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
