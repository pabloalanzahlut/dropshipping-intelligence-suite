"""
Self-Improve — Loop nocturno que PROPONE ajustes, nunca los aplica.

LOS DOS MÉTODOS EN CONFLICTO
----------------------------
Adrián Sáenz (Ra3GIwwT4Yc) describe un sistema que cada noche mide sus
resultados y **reescribe sus propias reglas**. Su caso SEO pasó de 1,1% a 1,6%
de CTR en una semana, autónomo.

Xavier Mitjana (1tzz17YDtz8 14:26) documenta lo contrario: cuando Maurice Human
montó un test para verificar a sus agentes, **los agentes intentaron modificar
el test**. Tuvo que protegerlo.

Los dos tienen razón en su contexto. La diferencia está en qué puede tocar el
sistema: ajustar un título SEO es reversible y barato; relajar el multiplicador
mínimo de 2x a 1,8x porque "los datos de 21 días lo sugieren" destruye el margen
de forma silenciosa, que es exactamente el fallo del caso Opus-vs-Haiku.

CÓMO SE RESUELVE AQUÍ
---------------------
El loop lee métricas reales y escribe propuestas en un fichero aparte. No edita
`CLAUDE.md`, ni `.claude/memory/reglas-financieras.md`, ni
`deterministic_gate.py`. Una persona lee las propuestas y decide.

Zonas prohibidas, sin excepción:
  - Reglas financieras (multiplicador, ROAS, costes operativos)
  - El gate determinista
  - Cualquier fichero de `.claude/memory/`
"""

import os
import json
import logging
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime, timezone

from app.services.metrics_aggregator import MetricsAggregator
from app.services.llm_router import chat

logger = logging.getLogger(__name__)

PROPUESTAS = "ai_workspace/knowledge_base/propuestas_ajuste.md"

# Lo que este loop no puede tocar bajo ninguna circunstancia.
ZONAS_PROHIBIDAS = (
    "CLAUDE.md",
    ".claude/memory/",
    "deterministic_gate.py",
    "financial_validator.py",
    "reglas-financieras.md",
)

SYSTEM_PROMPT = """Eres el analista de rendimiento de GEM OS, un sistema de dropshipping.

Recibes métricas reales de los últimos 21 días: qué productos clasificó el sistema como
HOT/WARM/COLD, y qué vendieron realmente.

Tu trabajo es detectar dónde falla el criterio de clasificación y proponer ajustes
concretos. Para cada propuesta indica:
  - Qué criterio ajustar y a qué valor
  - Qué evidencia de los datos lo respalda (números concretos)
  - Qué riesgo tiene el cambio

REGLAS QUE NO PUEDES PROPONER CAMBIAR, bajo ninguna circunstancia:
  - El multiplicador mínimo de 2x o el objetivo de 3x
  - El ROAS mínimo de 2
  - Los porcentajes de fees (4%) y cancelaciones (10,1%)
  - Cualquier verificación del gate determinista

Esas vienen de la fuente primaria y de un P&L real. Si los datos parecen sugerir
relajarlas, lo que falla es otra cosa: dilo, pero no propongas tocarlas.

Si no hay evidencia suficiente para una propuesta, dilo claramente. No inventes
tendencias con pocos datos."""


def analizar_y_proponer(dias: int = 21, db_path: Optional[str] = None) -> Dict:
    """
    Lee métricas reales y genera propuestas de ajuste en un fichero aparte.

    Returns:
        dict con el resumen de métricas y la ruta del fichero de propuestas.
    """
    if db_path is None:
        from app.config.path_manager import PathManager
        db_path = str(PathManager.get_paths()["db"])
    agg = MetricsAggregator(db_path)
    resumen = agg.resumen(dias)

    if resumen["productos_medibles"] < 5:
        logger.info(
            f"[SELF_IMPROVE] Solo {resumen['productos_medibles']} productos medibles — "
            f"insuficiente para proponer ajustes"
        )
        return {
            "propuestas_generadas": False,
            "motivo": "datos insuficientes",
            "resumen": resumen,
        }

    vista = agg.construir_vista(dias)
    # Solo los que se probaron con dinero real
    probados = [f for f in vista if f.gasto_ads > 0]

    contexto = {
        "resumen": resumen,
        "productos": [
            {
                "sku": f.sku,
                "clasificacion": f.clasificacion,
                "score": f.score,
                "multiplicador_previsto": f.multiplicador_previsto,
                "roas_real": f.roas_real,
                "unidades": f.unidades_vendidas,
                "tasa_cancelacion": f.tasa_cancelacion,
                "acierto": f.acierto,
            }
            for f in probados
        ],
    }

    analisis = chat(
        task="analizar_tendencia",
        system_prompt=SYSTEM_PROMPT,
        user_message=json.dumps(contexto, ensure_ascii=False, indent=2),
        max_tokens=2048,
        temperature=0.1,
    )

    if not analisis:
        logger.error("[SELF_IMPROVE] El análisis no devolvió nada")
        return {"propuestas_generadas": False, "motivo": "sin respuesta del modelo"}

    ruta = _escribir_propuestas(analisis, resumen)
    propuesta_id = _guardar_propuesta_estructurada(db_path, analisis, resumen)
    return {
        "propuestas_generadas": True,
        "ruta": ruta,
        "propuesta_id": propuesta_id,
        "resumen": resumen,
    }


def _escribir_propuestas(analisis: str, resumen: Dict) -> str:
    """
    Añade las propuestas al fichero, sin sobrescribir las anteriores.

    El fichero es solo lectura para el sistema: nadie lo aplica automáticamente.
    """
    _verificar_destino_permitido(PROPUESTAS)

    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    bloque = f"""
---

## Propuestas del {fecha}

**Métricas del periodo ({resumen['periodo_dias']} días):**
- Productos evaluados: {resumen['productos_evaluados']} ({resumen['productos_medibles']} medibles)
- Precisión del clasificador: {resumen['precision_clasificador']}
- HOT que vendieron: {resumen['hot_que_vendieron']}/{resumen['hot_total']}
- ROAS global: {resumen['roas_global']}
- Tasa de cancelación: {resumen['tasa_cancelacion_global']}

### Análisis

{analisis}

**Estado:** PENDIENTE DE REVISIÓN — ningún cambio se ha aplicado.
"""

    os.makedirs(os.path.dirname(PROPUESTAS), exist_ok=True)
    cabecera = ""
    if not os.path.exists(PROPUESTAS):
        cabecera = (
            "# Propuestas de Ajuste — GEM OS\n\n"
            "Generadas por `app/services/self_improve.py`. **Nada aquí se aplica solo.**\n"
            "Las reglas financieras y el gate determinista quedan fuera del alcance de "
            "este análisis por diseño.\n"
        )

    with open(PROPUESTAS, "a", encoding="utf-8") as f:
        if cabecera:
            f.write(cabecera)
        f.write(bloque)

    logger.info(f"[SELF_IMPROVE] Propuestas escritas en {PROPUESTAS}")
    return PROPUESTAS


def _guardar_propuesta_estructurada(db_path: str, analisis: str, resumen: Dict) -> int:
    """Además del Markdown (rastro de auditoría), deja una fila en SQLite para que una
    pantalla de revisión pueda listar/marcar propuestas — el Markdown no tiene forma de
    hacerlo. Sigue sin aplicar nada: «estado» es solo un apunte de revisión humana."""
    resumen_corto = json.dumps({k: resumen.get(k) for k in (
        "periodo_dias", "productos_evaluados", "productos_medibles",
        "precision_clasificador", "roas_global", "tasa_cancelacion_global")}, ensure_ascii=False)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO propuestas_ajuste (resumen, analisis_md, estado) VALUES (?, ?, 'pendiente')",
            (resumen_corto, analisis))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _verificar_destino_permitido(ruta: str) -> None:
    """Cortafuegos: aborta si alguien apunta este módulo a una zona protegida."""
    normalizada = ruta.replace("\\", "/")
    for zona in ZONAS_PROHIBIDAS:
        if zona in normalizada:
            raise PermissionError(
                f"[SELF_IMPROVE] Intento de escritura en zona protegida: {ruta}. "
                f"Este módulo solo escribe propuestas, nunca modifica reglas."
            )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    resultado = analizar_y_proponer()
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
