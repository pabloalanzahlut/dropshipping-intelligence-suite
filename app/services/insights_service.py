"""
insights_service — consulta de los insights de la KB y contexto para el Agente IA.

Antes esta lógica vivía dentro de `dashboard_server.py` (arrastraba FastAPI al importarla); ahora la
comparten la web y el escritorio. Todas las funciones reciben `db_path`, no tocan estado global y
devuelven exactamente lo mismo que devolvían los métodos privados del servidor.
"""
from __future__ import annotations

import logging
import re
import sqlite3
from typing import Any, Dict, List, Tuple

from app.services import agent_router

log = logging.getLogger(__name__)

INSIGHTS_UNION = """
    SELECT id, 'product_trends' AS source_table, video_id,
           CASE WHEN product_name = 'Producto Extraído por IA'
                THEN 'Sin nombre · ' || COALESCE(niche, 'producto') ELSE product_name END AS titulo,
           niche AS subtitulo, wow_factor AS contenido,
           validated_at AS created_at
    FROM product_trends
    UNION ALL
    SELECT id, 'conversion_formulas', video_id,
           category, framework_name, raw_structure, NULL
    FROM conversion_formulas
    UNION ALL
    SELECT id, 'operations_traffic', video_id,
           traffic_source, NULL, COALESCE(NULLIF(scaling_strategy, ''), logistics_notes), NULL
    FROM operations_traffic
"""
INSIGHT_TIPOS = ("product_trends", "conversion_formulas", "operations_traffic")

STOPWORDS_BUSQUEDA = {
    "que", "cual", "cuales", "como", "cuando", "donde", "quien", "para", "por", "con", "sin", "sobre",
    "entre", "desde", "hasta", "esta", "este", "esto", "estos", "estas", "tiene", "tienen", "hay",
    "ser", "son", "una", "uno", "unos", "unas", "los", "las", "del", "mas", "menos", "muy", "mejor",
    "mejores", "dame", "dime", "dices", "menciona", "mencionan", "base", "conocimiento", "kb",
    "registradas", "registrados", "sobre", "segun", "cada", "todo", "todos", "algun", "alguna",
    "puedo", "debo", "quiero", "necesito", "ultimas", "ultimos", "resumen",
}

# Qué tipo de insight conviene priorizar según el tipo de pregunta (agent_router)
TIPO_PREFERIDO = {
    "producto": "product_trends", "estrategia": "conversion_formulas",
    "operaciones": "operations_traffic", "metricas": None, "lecciones": None,
    "validacion": None, "tecnico": None, "general": None,
}

INSTRUCCION_FUENTES = (
    "Responde SOLO con lo que aparece en el CONTEXTO KB. Cita cada dato con su número entre "
    "corchetes, por ejemplo [3], y menciona el canal de origen. Si el contexto no tiene la "
    "respuesta, dilo en vez de inventar."
)


def like_escape(term: str) -> str:
    return "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def limpiar_preview(texto: Any, max_chars: int) -> str:
    """Quita el encabezado numerado ("2. Estructuras de ...") que el extractor deja al inicio."""
    t = str(texto or "").strip()
    t = re.sub(r"^\s*\d\.\s+[^\n]*\n", "", t, count=1)
    return re.sub(r"\s+", " ", t).strip()[:max_chars]


def query_insights(db_path: str, tipo: str = "", buscar: str = "", canal: str = "",
                   limite: int = 50, offset: int = 0, preview_chars: int = 220) -> Dict[str, Any]:
    """Insights de las 3 tablas KB con filtros y paginación. Devuelve {items, total}."""
    where, params = [], []
    if tipo in INSIGHT_TIPOS:
        where.append("u.source_table = ?")
        params.append(tipo)
    if buscar.strip():
        like = like_escape(buscar.strip())
        where.append("(u.titulo LIKE ? ESCAPE '\\' OR u.contenido LIKE ? ESCAPE '\\' "
                     "OR v.title LIKE ? ESCAPE '\\' OR v.channel_name LIKE ? ESCAPE '\\')")
        params += [like, like, like, like]
    if canal.strip():
        where.append("v.channel_name = ?")
        params.append(canal.strip())
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    base = (f"FROM ({INSIGHTS_UNION}) u "
            f"LEFT JOIN video_sources v ON v.video_id = u.video_id {clause}")
    try:
        with sqlite3.connect(db_path, timeout=30) as conn:
            conn.row_factory = sqlite3.Row
            total = conn.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]
            rows = conn.execute(
                f"""SELECT u.id, u.source_table, u.video_id, u.titulo, u.subtitulo,
                           u.contenido, u.created_at, v.title AS video_title,
                           v.channel_name AS channel_name
                    {base}
                    ORDER BY COALESCE(u.created_at, '') DESC, u.id DESC
                    LIMIT ? OFFSET ?""",
                params + [max(1, min(int(limite), 200)), max(0, int(offset))],
            ).fetchall()
    except sqlite3.Error as exc:
        log.warning(f"[INSIGHTS] {exc}")
        return {"items": [], "total": 0}
    items = []
    for r in rows:
        d = dict(r)
        d["content_preview"] = limpiar_preview(d.pop("contenido"), preview_chars)
        items.append(d)
    return {"items": items, "total": total}


def insights_resumen(db_path: str) -> Dict[str, Any]:
    """Totales por tipo y por canal (los contadores de la página Insights)."""
    try:
        with sqlite3.connect(db_path, timeout=30) as conn:
            por_tipo = {t: 0 for t in INSIGHT_TIPOS}
            for tipo, n in conn.execute(
                    f"SELECT source_table, COUNT(*) FROM ({INSIGHTS_UNION}) GROUP BY source_table"):
                por_tipo[tipo] = n
            canales = [
                {"canal": c, "n": n} for c, n in conn.execute(
                    f"""SELECT v.channel_name, COUNT(*) FROM ({INSIGHTS_UNION}) u
                        JOIN video_sources v ON v.video_id = u.video_id
                        GROUP BY v.channel_name ORDER BY COUNT(*) DESC""")
            ]
    except sqlite3.Error as exc:
        log.warning(f"[INSIGHTS] resumen: {exc}")
        return {"total": 0, "por_tipo": {}, "canales": []}
    return {"total": sum(por_tipo.values()), "por_tipo": por_tipo, "canales": canales}


def kb_insights_combined(db_path: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Muestra equilibrada de las 3 tablas (para el contexto del agente KB)."""
    por_tabla = max(1, -(-limit // 3))
    rows: List[Dict[str, Any]] = []
    for tipo in INSIGHT_TIPOS:
        rows += query_insights(db_path, tipo=tipo, limite=por_tabla, preview_chars=400)["items"]
    return rows[:limit]


def terminos_busqueda(pregunta: str) -> List[str]:
    """Palabras útiles de la pregunta (sin tildes, sin palabras vacías, de 4+ letras)."""
    texto = agent_router._normalizar(pregunta)
    vistos: List[str] = []
    for p in re.findall(r"[a-z0-9]{4,}", texto):
        if p not in STOPWORDS_BUSQUEDA and p not in vistos:
            vistos.append(p)
    return vistos[:10]


def insights_relevantes(db_path: str, pregunta: str, tipo_pregunta: str = "general",
                        limite: int = 24) -> List[Dict[str, Any]]:
    """Los insights de la KB que más se parecen a la pregunta (no los 30 últimos).

    Se buscan las palabras de la pregunta en título, nicho, contenido, vídeo y canal; cada
    coincidencia suma puntos (título y nicho pesan más). Si no hay palabras útiles o nada
    coincide, se devuelve una muestra equilibrada de las 3 tablas."""
    terminos = terminos_busqueda(pregunta)
    if not terminos:
        return kb_insights_combined(db_path, limite)
    candidatos: Dict[Any, Dict[str, Any]] = {}
    for t in terminos:
        res = query_insights(db_path, buscar=t, limite=120, preview_chars=420)
        for it in res["items"]:
            candidatos.setdefault((it["source_table"], it["id"]), it)
    if not candidatos:
        return kb_insights_combined(db_path, limite)

    preferido = TIPO_PREFERIDO.get(tipo_pregunta)

    def puntos(it: Dict[str, Any]) -> float:
        campos = (
            (3.0, agent_router._normalizar(it.get("titulo") or "")),
            (2.0, agent_router._normalizar(it.get("subtitulo") or "")),
            (1.0, agent_router._normalizar(it.get("content_preview") or "")),
            (1.0, agent_router._normalizar(it.get("video_title") or "")),
            (0.5, agent_router._normalizar(it.get("channel_name") or "")),
        )
        total = sum(peso for peso, texto in campos for t in terminos if t in texto)
        return total + (1.5 if preferido and it["source_table"] == preferido else 0.0)

    ordenados = sorted(candidatos.values(), key=puntos, reverse=True)
    return ordenados[:limite]


def contexto_kb_para(db_path: str, pregunta: str, tipo_pregunta: str = "general",
                     limite: int = 24) -> Tuple[str, List[Dict[str, Any]]]:
    """(texto de contexto numerado, lista de fuentes) para inyectar al agente."""
    filas = insights_relevantes(db_path, pregunta, tipo_pregunta, limite)
    if not filas:
        return ("(Base de conocimiento vacía — realiza ingesta de videos YouTube primero.)", [])
    fuentes, lineas = [], []
    for n, r in enumerate(filas, 1):
        url = f"https://www.youtube.com/watch?v={r['video_id']}" if r.get("video_id") else ""
        fuentes.append({
            "n": n, "tipo": r.get("source_table"), "titulo": r.get("titulo") or "(sin título)",
            "video_title": r.get("video_title") or "", "canal": r.get("channel_name") or "?", "url": url,
        })
        lineas.append(
            f"[{n}] ({r.get('source_table')}) {r.get('titulo') or '(sin título)'} — "
            f"vídeo «{r.get('video_title') or '?'}» | canal: {r.get('channel_name') or '?'} | {url}\n"
            f"{(r.get('content_preview') or '').strip()}"
        )
    return "\n\n".join(lineas), fuentes


def fuentes_citadas(respuesta: str, fuentes: List[Dict[str, Any]], minimo: int = 4) -> List[Dict[str, Any]]:
    """Fuentes que el agente citó con [n]; si no citó ninguna, las más relevantes."""
    citadas = {int(n) for n in re.findall(r"\[(\d{1,2})\]", respuesta or "")}
    elegidas = [f for f in fuentes if f["n"] in citadas]
    return elegidas or fuentes[:minimo]
