"""
agent_router — reconoce qué tipo de pregunta es y elige el agente adecuado.

Python puro y determinista (sin IA): es gratis, instantáneo y siempre da la misma
respuesta para la misma pregunta, así que se puede mostrar en vivo mientras se escribe.

Agentes (app/agents_engine/*.md.agent.md):
  gem-orchestrator-core — KB, productos, estrategia, tráfico, operaciones (por defecto)
  gem-qa-validation     — validar números y reglas financieras (2x/3x, margen, ROAS)
  gem-backend-core      — preguntas técnicas: código, errores, servidor, base de datos
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Tuple

ORQUESTADOR = "gem-orchestrator-core"
QA = "gem-qa-validation"
BACKEND = "gem-backend-core"

AGENTES: Dict[str, Dict[str, str]] = {
    ORQUESTADOR: {
        "rol": "Orquestador",
        "descripcion": "Consulta la KB: productos, estrategia, tráfico y operaciones",
    },
    QA: {
        "rol": "Validación",
        "descripcion": "Valida números y reglas financieras (2x/3x, margen, ROAS)",
    },
    BACKEND: {
        "rol": "Técnico",
        "descripcion": "Código, errores, servidor, base de datos e integraciones",
    },
}

# tipo -> (agente, etiqueta legible)
TIPOS: Dict[str, Tuple[str, str]] = {
    "producto":     (ORQUESTADOR, "Producto y tendencias"),
    "estrategia":   (ORQUESTADOR, "Conversión, copy y creativos"),
    "operaciones":  (ORQUESTADOR, "Tráfico, ads y logística"),
    "metricas":     (ORQUESTADOR, "Métricas de la KB"),
    "lecciones":    (ORQUESTADOR, "Errores y aciertos"),
    "validacion":   (QA, "Validación financiera"),
    "tecnico":      (BACKEND, "Consulta técnica"),
    "general":      (ORQUESTADOR, "Consulta general"),
}

# (patrón, peso). Se aplican sobre el texto normalizado (minúsculas, sin tildes).
_REGLAS: Dict[str, List[Tuple[str, int]]] = {
    "producto": [
        (r"\bproductos?\b", 2), (r"\b(hot|warm|cold)\b", 3), (r"\bganadores?\b", 3),
        (r"\btendencias?\b", 2), (r"\bnichos?\b", 2), (r"\bwinning\b", 2),
        (r"\bque (vender|producto)", 2), (r"\bproveedor(es)?\b", 1),
    ],
    "estrategia": [
        (r"\bconversion(es)?\b", 3), (r"\bformulas?\b", 2), (r"\bcopys?\b", 3),
        (r"\bhooks?\b", 3), (r"\bguion(es)?\b", 2), (r"\blanding\b", 3), (r"\baida\b", 3),
        (r"\bcreativos?\b", 3), (r"\bfichas?\b", 2), (r"\bofertas?\b", 2), (r"\bestrategias?\b", 1),
        (r"\bpagina de producto\b", 2),
    ],
    "operaciones": [
        (r"\btrafico\b", 3), (r"\bmeta ads?\b", 3), (r"\btiktok ads?\b", 3), (r"\banuncios?\b", 2),
        (r"\bcampanas?\b", 2), (r"\bescalar\b", 3), (r"\blogistica\b", 3), (r"\benvios?\b", 2),
        (r"\bfletes?\b", 2), (r"\baduanas?\b", 2), (r"\bpasarelas?\b", 2), (r"\bsegmentacion\b", 2),
        (r"\bpresupuestos?\b", 2), (r"\bpublico\b", 1), (r"\bestrategias? de trafico\b", 2),
    ],
    "metricas": [
        (r"\bpromedio\b", 3), (r"\bmedia\b", 2), (r"\bcuantos\b", 2), (r"\bcuantas\b", 2),
        (r"\btotal(es)?\b", 2), (r"\brango\b", 2), (r"\bporcentaje\b", 2), (r"\bestadisticas?\b", 2),
        (r"\bindexad[oa]s?\b", 2), (r"\bmas mencionad[oa]\b", 3), (r"\bresumen numerico\b", 2),
    ],
    "lecciones": [
        (r"\berrores? comunes?\b", 5), (r"\bque errores\b", 4), (r"\baciertos?\b", 4),
        (r"\blecciones?\b", 4), (r"\bse repiten\b", 3), (r"\bque (no )?hacer\b", 2),
        (r"\bmala[s]? practicas?\b", 3), (r"\bevitar\b", 2),
    ],
    "validacion": [
        (r"\bvalida(r|me|cion)?\b", 4), (r"\bverifica(r|me)?\b", 3), (r"\bcumple\b", 4),
        (r"\bregla 3x\b", 5), (r"\bregla 2x\b", 5), (r"\b[23]x\b", 3), (r"\bmultiplicador\b", 3),
        (r"\bcoste landed\b", 4), (r"\bcosto landed\b", 4), (r"\bcpa maximo\b", 4),
        (r"\bmargen\b", 2), (r"\bpvp\b", 2), (r"\brechaza(r)?\b", 3), (r"\baprueba(s)?\b", 2),
        (r"\bes rentable\b", 4), (r"\bsalen las cuentas\b", 4), (r"\bcalcula(r|me)?\b", 3),
        (r"\broas\b", 2), (r"\bfees?\b", 1), (r"\bcancelaciones?\b", 1),
    ],
    "tecnico": [
        (r"\bcodigo\b", 4), (r"\bpython\b", 5), (r"\bscript\b", 4), (r"\bsql(ite)?\b", 5),
        (r"\bendpoint\b", 5), (r"\bapi\b", 3), (r"\btraceback\b", 6), (r"\bexception\b", 5),
        (r"\bbug\b", 5), (r"\bservidor\b", 3), (r"\bpuerto\b", 3), (r"\byt-?dlp\b", 5),
        (r"\bbase de datos\b", 4), (r"\bjson\b", 3), (r"\bgit(hub)?\b", 4), (r"\bdeploy\b", 4),
        (r"\binstal(ar|acion)\b", 3), (r"\bconfigurar? (el )?(servidor|env|entorno)\b", 4),
        (r"\b(da|sale|me da|me sale|tengo|aparece) (un )?error\b", 4), (r"\bcrash(ea)?\b", 4),
        (r"\bno (arranca|inicia|abre|carga)\b", 3), (r"\berror (http )?\d{3}\b", 5),
        (r"\bhttp \d{3}\b", 4), (r"\b(arregla|corrige|depura)\b", 3), (r"\bfuncion\b", 2),
        (r"\bescritorio\b", 2), (r"\btkinter\b", 5), (r"\bfastapi\b", 5), (r"\bwebhook\b", 2),
    ],
}

# Con estas señales, un número + palabra de dinero apunta a validar cuentas
_DINERO = re.compile(r"(\d+[.,]?\d*\s*(\$|€|usd|eur|dolares|euros)|(\$|€)\s*\d+|\bcoste?\b.*\d|\bcosto\b.*\d|\bpvp\b.*\d)")


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sin_tildes.lower()).strip()


def clasificar(pregunta: str) -> Dict[str, Any]:
    """Devuelve {tipo, tipo_etiqueta, agente, confianza, motivo, puntuaciones}.

    confianza: 'alta' (diferencia clara), 'media' o 'baja' (sin señales: consulta general).
    """
    texto = _normalizar(pregunta)
    puntos: Dict[str, int] = {}
    pistas: Dict[str, List[str]] = {}
    for tipo, reglas in _REGLAS.items():
        for patron, peso in reglas:
            m = re.search(patron, texto)
            if m:
                puntos[tipo] = puntos.get(tipo, 0) + peso
                pistas.setdefault(tipo, []).append(m.group(0))

    # Cifras con dinero: quieren cuentas, no consultar la KB
    if _DINERO.search(texto):
        puntos["validacion"] = puntos.get("validacion", 0) + 3
        pistas.setdefault("validacion", []).append("cifras de coste/precio")

    if not puntos or max(puntos.values()) < 3:
        agente, etiqueta = TIPOS["general"]
        return {"tipo": "general", "tipo_etiqueta": etiqueta, "agente": agente,
                "confianza": "baja", "motivo": "sin señales claras: se usa el orquestador",
                "puntuaciones": puntos}

    # Desempate estable: técnico y validación primero (son los más específicos)
    prioridad = ["tecnico", "validacion", "lecciones", "metricas", "operaciones", "estrategia", "producto"]
    ordenados = sorted(puntos.items(), key=lambda kv: (-kv[1], prioridad.index(kv[0])))
    tipo, mejor = ordenados[0]
    segundo = ordenados[1][1] if len(ordenados) > 1 else 0
    confianza = "alta" if mejor - segundo >= 3 else "media"
    agente, etiqueta = TIPOS[tipo]
    motivo = "detectado por: " + ", ".join(dict.fromkeys(pistas[tipo]))
    return {"tipo": tipo, "tipo_etiqueta": etiqueta, "agente": agente,
            "confianza": confianza, "motivo": motivo, "puntuaciones": puntos}


def elegir_agente(pregunta: str, agente_pedido: str = "auto") -> Dict[str, Any]:
    """Resuelve el agente final. 'auto' (o vacío) usa el clasificador; un nombre
    válido se respeta (agente fijado a mano)."""
    ruta = clasificar(pregunta)
    pedido = (agente_pedido or "auto").strip().lstrip("@")
    if pedido in AGENTES:
        ruta["automatico"] = False
        ruta["sugerido"] = ruta["agente"]
        ruta["agente"] = pedido
    else:
        ruta["automatico"] = True
    return ruta
