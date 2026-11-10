"""
agent_chat — la capa conversacional del Agente IA (la comparten la web y el escritorio).

El motor de agentes (`AgentExecutor`) contesta en JSON porque la gobernanza valida esa estructura. Ese
JSON es el transporte, no lo que debe leer una persona: aquí se convierte en una conversación.

  · `responder()` es la única entrada. Recibe la pregunta y los turnos anteriores, monta el contexto
    (tienda real + insights de la KB + conversación previa), llama al motor y devuelve texto natural,
    las fuentes citadas y los datos de apoyo ya legibles. Ninguna pantalla enseña JSON.
  · Saludos, «gracias» y «¿qué sabes hacer?» se contestan al instante y sin gastar tokens.
  · Los fallos del proveedor se traducen a una frase que dice qué hacer.

Las instrucciones de estilo viajan en la petición (no solo en el procedimiento de la skill), así el
formato de la conversación no depende de un archivo que el propio motor puede reescribir.

Todo lo que no es la llamada al modelo es Python determinista: lo cubre tests/test_agente_chat.py.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, Iterator, List, Optional, Tuple

from app.services import agent_router, insights_service, store_context

MAX_TURNOS = 6            # mensajes anteriores que acompañan a cada pregunta (tres idas y vueltas)
MAX_CHARS_TURNO = 700     # cada turno anterior se recorta: es contexto, no el tema
MAX_PREGUNTA = 2000
MAX_BLOQUES = 12
MAX_FILAS = 14

ESTILO = (
    "ESTILO DE LA RESPUESTA (obligatorio): el operador solo lee el campo \"respuesta\", dentro de un chat. "
    "Escríbelo como le hablaría un compañero que conoce el negocio: en español, de tú, directo y con frases "
    "cortas. Empieza por la respuesta, sin saludar y sin repetir la pregunta. Si hay varios elementos, ponlos "
    "en una lista con guiones, uno por línea. No metas JSON, llaves ni nombres de campo dentro de "
    "\"respuesta\". Deja cada cita [n] o [TIENDA] pegada al dato que respalda. Si falta un dato, dilo en una "
    "frase y pide justo lo que necesitas. Ten en cuenta la conversación anterior: si el operador dice «ese», "
    "«el segundo» o «¿y con envío?», se refiere a lo último que hablasteis. Termina con un siguiente paso "
    "concreto solo si aporta algo. Los datos de apoyo van en \"datos\", no en el texto."
)

SIN_CLAVE = ("Todavía no tengo una clave de IA para contestar. Pega tu clave de OpenRouter en Configuración "
             "y vuelve a preguntarme.")
SIN_TEXTO = "No he podido formular una respuesta con eso. ¿Me lo preguntas de otra forma?"
INCOMPLETA = ("La respuesta me ha llegado cortada. Vuelve a preguntármelo o acota la pregunta "
              "(por ejemplo, a un producto o a un canal).")


class AgenteNoDisponible(RuntimeError):
    """El agente no puede contestar ahora; el mensaje ya está escrito para el operador."""


# ── charla sin modelo ────────────────────────────────────────────────────────────────────────────

_CHARLA: Tuple[Tuple[str, "re.Pattern[str]"], ...] = (
    ("saludo", re.compile(
        r"^(hola+|holi|buenas|buen(os)? dias?|buenas (tardes|noches)|hey|ey|ciao|hello|hi|saludos|que tal|"
        r"como estas|como va|como va todo)( (hola|buenas|que tal|como estas|como va|agente|gem|equipo))*$")),
    ("ayuda", re.compile(
        r"^(ayuda|help|que (puedes|sabes) hacer|que haces|quien eres|que eres|para que sirves|como funcionas|"
        r"en que (me )?puedes ayudar(me)?|que te puedo preguntar)$")),
    ("gracias", re.compile(
        r"^((muchas |mil )?gracias( por todo| a ti)?|(ok|okay|vale|perfecto|entendido|de acuerdo|listo)"
        r"( (muchas )?gracias)?)$")),
    ("adios", re.compile(r"^(adios|hasta (luego|manana|pronto|otra)|chao|chau|nos vemos|bye)$")),
)


def charla(texto: str) -> Optional[str]:
    """«saludo», «ayuda», «gracias» o «adios» si el mensaje es SOLO eso; None si trae una pregunta."""
    limpio = re.sub(r"[^a-z0-9 ]", " ", agent_router._normalizar(texto))
    limpio = re.sub(r"\s+", " ", limpio).strip()
    if not limpio or len(limpio) > 60:
        return None
    for tipo, patron in _CHARLA:
        if patron.match(limpio):
            return tipo
    return None


def respuesta_rapida(tipo: str, db_path: str) -> str:
    """Contestación inmediata a la charla. Las cifras que menciona son reales (se leen de la BD)."""
    if tipo == "gracias":
        return "De nada. Aquí sigo si necesitas algo más."
    if tipo == "adios":
        return "Hasta luego."
    if tipo == "ayuda":
        return (
            "Soy el agente de GEM OS y trabajo con tus datos, no con suposiciones. Puedes preguntarme por:\n"
            "- Lo que enseñan tus mentores: productos, hooks, ofertas, tráfico y logística, siempre con el vídeo de origen.\n"
            "- Tu tienda: pedidos, ingresos, márgenes y catálogo, según lo último sincronizado de Shopify y AutoDS.\n"
            "- Las cuentas de un producto: dime coste, envío y precio de venta y te digo si cumple el 2× y el 3×.\n"
            "- Dudas técnicas de la propia herramienta.\n"
            "Si me falta un dato te lo pido en vez de inventarlo."
        )
    try:
        total = int(insights_service.insights_resumen(db_path).get("total") or 0)
    except Exception:                                    # sin BD todavía: el saludo no debe fallar
        total = 0
    try:
        conectada = bool(store_context.construir(db_path).get("conectada"))
    except Exception:
        conectada = False
    kb = (f"Tengo {total} apuntes de tus mentores indexados" if total
          else "Todavía no tengo apuntes de tus mentores (lanza la ingesta de YouTube para empezar)")
    tienda = ("y los datos de tu tienda sincronizados" if conectada
              else "y tu tienda aún no está conectada, así que de ventas no te puedo hablar")
    return (f"¡Hola! Soy tu agente de GEM OS. {kb} {tienda}. "
            "Pregúntame por un producto, una estrategia o las cuentas de algo que quieras vender.")


# ── del JSON del motor al texto de la conversación ───────────────────────────────────────────────

_CLAVES_TEXTO = ("respuesta", "output", "mensaje", "message", "answer", "texto", "resumen")
_CLAVES_META = set(_CLAVES_TEXTO) | {
    "tipo", "tipo_consulta", "fuentes", "confianza", "fecha_consulta", "fecha", "agent_id", "agente", "status",
    "estado", "timestamp",
}
_CLAVES_TITULO = ("producto", "nombre", "titulo", "product_name", "name", "concepto", "regla", "canal")
_SIGLAS = {"pvp", "roas", "cpa", "cpc", "cpm", "ctr", "sku", "kb", "id", "url", "aov", "iva", "ia"}
_SUFIJOS = {"eur": "(EUR)", "usd": "(USD)", "pct": "(%)", "kg": "(kg)"}
_MARCA_TIENDA = re.compile(r"[ \t]*\[\s*TIENDA(?:\s*:[^\]]*)?\]", re.IGNORECASE)
_MARCA_GAP = re.compile(r"[ \t]*\[\s*DATA_GAP\s*:?\s*([^\]]*)\]", re.IGNORECASE)


def sin_fences(texto: str) -> str:
    """Los modelos suelen envolver el JSON en ```json ... ```; deja solo el contenido."""
    t = (texto or "").strip()
    if not t.startswith("```"):
        return t
    t = t.split("\n", 1)[1] if "\n" in t else ""
    if t.rstrip().endswith("```"):
        t = t.rstrip()[:-3]
    return t.strip()


def limpiar_marcas(texto: str) -> Tuple[str, bool]:
    """Quita las marcas internas ([TIENDA], [DATA_GAP: …]) del texto. Devuelve (texto, usa_tienda).

    Las citas numeradas [3] se conservan: son las notas al pie que enlazan con las fuentes."""
    t = texto or ""
    usa_tienda = bool(_MARCA_TIENDA.search(t))
    t = _MARCA_TIENDA.sub("", t)
    t = _MARCA_GAP.sub(lambda m: f" (falta: {m.group(1).strip()})" if m.group(1).strip() else "", t)
    t = re.sub(r"[ \t]+([.,;:!?)])", r"\1", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip(), usa_tienda


def etiqueta(clave: Any) -> str:
    """«multiplicador_sobre_coste_producto» → «Multiplicador sobre coste producto»; «pvp_eur» → «PVP (EUR)»."""
    partes = [p for p in re.split(r"[_\s]+", str(clave).strip()) if p]
    if not partes:
        return ""
    sufijo = _SUFIJOS.get(partes[-1].lower()) if len(partes) > 1 else None
    if sufijo:
        partes = partes[:-1]
    palabras = [p.upper() if p.lower() in _SIGLAS else p.lower() for p in partes]
    if not palabras[0].isupper():
        palabras[0] = palabras[0].capitalize()
    return " ".join(palabras) + (f" {sufijo}" if sufijo else "")


def valor(v: Any, profundidad: int = 0) -> str:
    """Un valor tal como lo leería una persona: «42,99», «Sí», «—»…"""
    if v is None or v == "":
        return "—"
    if isinstance(v, bool):
        return "Sí" if v else "No"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e15:
            return str(int(v))
        return f"{v:.2f}".rstrip("0").rstrip(".").replace(".", ",")
    if isinstance(v, str):
        t, usa = limpiar_marcas(v)
        return t or ("Tu tienda (Shopify y AutoDS)" if usa else "—")
    if isinstance(v, (list, tuple)):
        if not v:
            return "—"
        if profundidad >= 1:
            return f"{len(v)} elementos"
        return ", ".join(valor(x, profundidad + 1) for x in list(v)[:8]) + ("…" if len(v) > 8 else "")
    if isinstance(v, dict):
        if profundidad >= 1:
            return f"{len(v)} datos"
        return "; ".join(f"{etiqueta(k)}: {valor(x, profundidad + 1)}" for k, x in list(v.items())[:6])
    return str(v)


def _bloque(d: Dict[str, Any], n: int) -> Optional[Dict[str, Any]]:
    clave_titulo = next((k for k in _CLAVES_TITULO if isinstance(d.get(k), (str, int, float)) and str(d.get(k)).strip()), None)
    if clave_titulo:
        titulo = valor(d[clave_titulo])
    elif "TIENDA" in str(d.get("fuente", "")).upper():
        titulo = "Tu tienda"
    else:
        titulo = f"Dato {n}"
    filas = [[etiqueta(k), valor(v)] for k, v in d.items() if k != clave_titulo and str(k).lower() != "fuente"]
    if "TIENDA" in str(d.get("fuente", "")).upper() and clave_titulo:
        filas.append(["Origen", "Tu tienda (Shopify y AutoDS)"])
    elif d.get("fuente") and "TIENDA" not in str(d.get("fuente")).upper():
        filas.append(["Origen", valor(d["fuente"])])
    return {"titulo": titulo[:90], "filas": filas[:MAX_FILAS]} if filas else None


def datos_legibles(data: Any) -> List[Dict[str, Any]]:
    """Los datos de apoyo de la respuesta como bloques {titulo, filas:[[etiqueta, valor]]}; nunca JSON."""
    bloques: List[Dict[str, Any]] = []

    def anadir(obj: Any, nombre: str = "") -> None:
        if len(bloques) >= MAX_BLOQUES or obj in (None, "", [], {}):
            return
        if isinstance(obj, dict):
            b = _bloque(obj, len(bloques) + 1)
            if b:
                if nombre and b["titulo"].startswith("Dato "):
                    b["titulo"] = nombre
                bloques.append(b)
        elif isinstance(obj, (list, tuple)):
            if all(isinstance(x, dict) for x in obj):
                for x in obj:
                    anadir(x, nombre)
            else:
                bloques.append({"titulo": nombre or "Datos",
                                "filas": [[str(i), valor(x)] for i, x in enumerate(list(obj)[:MAX_FILAS], 1)]})
        else:
            bloques.append({"titulo": nombre or "Dato", "filas": [["Valor", valor(obj)]]})

    if isinstance(data, dict):
        for k, v in data.items():
            if str(k).lower() in _CLAVES_META:
                continue
            anadir(v, "" if str(k).lower() in ("datos", "data", "resultado", "resultados", "items") else etiqueta(k))
    else:
        anadir(data)
    return bloques


def bloques_a_texto(bloques: List[Dict[str, Any]]) -> str:
    """Los bloques en texto plano (escritorio, copiar al portapapeles, respuestas sin «respuesta»)."""
    partes = []
    for b in bloques:
        partes.append(b["titulo"] + "\n" + "\n".join(f"- {e}: {v}" for e, v in b["filas"]))
    return "\n\n".join(partes)


def _rescatar_respuesta(texto: str) -> str:
    """Si el JSON llegó cortado (límite de tokens), recupera al menos el campo «respuesta»."""
    m = re.search(r'"respuesta"\s*:\s*"((?:[^"\\]|\\.)*)', texto)
    if not m:
        return ""
    cuerpo = re.sub(r"\\+$", "", m.group(1))
    try:
        return json.loads('"' + cuerpo + '"')
    except json.JSONDecodeError:
        return cuerpo.replace('\\"', '"').replace("\\n", "\n")


def a_natural(bruto: str) -> Dict[str, Any]:
    """Salida cruda del motor → {texto, datos, confianza, usa_tienda}. `texto` nunca es JSON."""
    limpio = sin_fences(bruto)
    parece_json = limpio.startswith(("{", "["))
    try:
        data: Any = json.loads(limpio) if parece_json else None
    except json.JSONDecodeError:
        data = None
    confianza, bloques, texto = None, [], ""
    if isinstance(data, dict):
        texto = next((str(data[k]).strip() for k in _CLAVES_TEXTO
                      if isinstance(data.get(k), str) and data[k].strip()), "")
        if isinstance(data.get("confianza"), str) and data["confianza"].strip():
            confianza = data["confianza"].strip().capitalize()
        bloques = datos_legibles(data)
        if not texto:
            texto = bloques_a_texto(bloques) or SIN_TEXTO
    elif isinstance(data, list):
        bloques = datos_legibles(data)
        texto = bloques_a_texto(bloques) or SIN_TEXTO
        bloques = []
    elif parece_json:                                     # parecía JSON pero no se pudo leer
        texto = _rescatar_respuesta(limpio) or INCOMPLETA
    else:
        texto = limpio or SIN_TEXTO
    texto, usa_tienda = limpiar_marcas(texto)
    return {"texto": texto or SIN_TEXTO, "datos": bloques, "confianza": confianza, "usa_tienda": usa_tienda}


# ── conversación: historial, ruta y petición ─────────────────────────────────────────────────────

def _turnos(historial: Optional[List[Dict[str, Any]]]) -> List[Tuple[str, str]]:
    """[(rol, texto)] de los últimos turnos válidos; rol ∈ {«user», «agente»}."""
    salida: List[Tuple[str, str]] = []
    for m in historial or []:
        if not isinstance(m, dict):
            continue
        rol = str(m.get("rol") or "").lower()
        rol = "user" if rol in ("user", "usuario", "operador") else "agente" if rol in ("agente", "assistant") else ""
        texto = re.sub(r"\s+", " ", str(m.get("texto") or "")).strip()
        if rol and texto:
            salida.append((rol, texto[:MAX_CHARS_TURNO]))
    return salida[-MAX_TURNOS:]


def historial_a_texto(historial: Optional[List[Dict[str, Any]]]) -> str:
    return "\n".join(f"{'Operador' if rol == 'user' else 'Agente'}: {texto}" for rol, texto in _turnos(historial))


def _pregunta_anterior(historial: Optional[List[Dict[str, Any]]]) -> str:
    return next((t for rol, t in reversed(_turnos(historial)) if rol == "user"), "")


def consulta_para_buscar(pregunta: str, historial: Optional[List[Dict[str, Any]]] = None) -> str:
    """Texto con el que se buscan insights: una repregunta corta («¿y el segundo?») hereda la anterior."""
    if len(insights_service.terminos_busqueda(pregunta)) >= 3:
        return pregunta
    anterior = _pregunta_anterior(historial)
    return f"{pregunta} {anterior}".strip() if anterior else pregunta


def elegir_ruta(pregunta: str, agente: str = "auto",
                historial: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Qué agente atiende. Una repregunta sin señales propias sigue con el tema de la anterior."""
    ruta = agent_router.elegir_agente(pregunta, agente)
    anterior = _pregunta_anterior(historial)
    if ruta["tipo"] == "general" and anterior and not charla(pregunta):
        seguida = agent_router.elegir_agente(f"{anterior} {pregunta}", agente)
        if seguida["tipo"] != "general":
            seguida["motivo"] = "continúa la conversación · " + seguida.get("motivo", "")
            ruta = seguida
    ruta["rol"] = agent_router.AGENTES.get(ruta["agente"], {}).get("rol", "Agente")
    return ruta


def construir_peticion(db_path: str, pregunta: str, ruta: Dict[str, Any],
                       historial: Optional[List[Dict[str, Any]]] = None) -> Tuple[str, List[Dict[str, Any]], bool]:
    """(petición para el motor, fuentes numeradas, ¿lleva datos de la tienda?)."""
    kb_context, fuentes = insights_service.contexto_kb_para(
        db_path, consulta_para_buscar(pregunta, historial), ruta["tipo"])
    bloque = store_context.bloque_para_prompt(db_path)
    previa = historial_a_texto(historial)
    partes = [
        bloque,
        f"CONTEXTO KB (insights más relevantes, numerados):\n---\n{kb_context}\n---\n\n",
        f"{insights_service.INSTRUCCION_FUENTES}\n",
        f"{ESTILO}\n",
    ]
    if previa:
        partes.append("CONVERSACIÓN HASTA AHORA (sirve para entender a qué se refiere el operador; no la repitas):\n"
                      f"---\n{previa}\n---\n")
    partes.append(f"TIPO DE CONSULTA DETECTADO: {ruta['tipo_etiqueta']}\n")
    partes.append(f"PREGUNTA DEL OPERADOR:\n{pregunta}")
    return "".join(partes), fuentes, bool(bloque)


def explicar_error(exc: BaseException) -> str:
    """El fallo técnico del proveedor, dicho de forma que se sepa qué hacer."""
    if isinstance(exc, AgenteNoDisponible):
        return str(exc)
    t = str(exc)
    bajo = t.lower()
    if "governance block" in bajo:
        return ("El control de gobernanza ha parado la consulta antes de enviarla: falta `agent.md` o le falta "
                "alguna regla obligatoria. Revísalo en la pantalla Gobernanza.")
    if re.search(r"\b401\b", t) or "unauthorized" in bajo:
        return "La clave de OpenRouter no es válida o ha caducado. Cámbiala en Configuración y vuelve a preguntarme."
    if re.search(r"\b402\b", t) or "payment required" in bajo or "insufficient credit" in bajo:
        return "La cuenta de OpenRouter se ha quedado sin saldo. Recárgala y vuelve a preguntarme."
    if re.search(r"\b429\b", t) or "too many requests" in bajo:
        return "El proveedor de IA está limitando las peticiones ahora mismo. Espera un minuto y vuelve a intentarlo."
    if re.search(r"\b404\b", t):
        return ("El modelo configurado para este agente ya no existe en OpenRouter. "
                "Hay que actualizarlo en el motor de agentes.")
    if "timed out" in bajo or "timeout" in bajo:
        return "El modelo ha tardado demasiado en contestar. Vuelve a intentarlo; si se repite, concreta más la pregunta."
    if any(s in bajo for s in ("connection", "max retries", "getaddrinfo", "name resolution", "nodename")):
        return "No consigo conectar con el proveedor de IA. Comprueba tu conexión a internet y vuelve a intentarlo."
    if re.search(r"\b5\d\d\b", t):
        return "El proveedor de IA está teniendo problemas. Vuelve a intentarlo en unos minutos."
    return "No he podido contestar por un fallo técnico. Detalle: " + (t[:200] or type(exc).__name__)


def responder(db_path: str, pregunta: str, agente: str = "auto",
              historial: Optional[List[Dict[str, Any]]] = None, executor: Any = None,
              proyecto: str = "kb_chat") -> Dict[str, Any]:
    """Una vuelta de conversación.

    Devuelve {texto, ruta, fuentes, datos, confianza, con_tienda, rapida, segundos, bruto}.
    Lanza ValueError si la pregunta está vacía y AgenteNoDisponible (con el mensaje ya redactado para
    el operador) si el modelo no puede contestar."""
    pregunta = (pregunta or "").strip()[:MAX_PREGUNTA]
    if not pregunta:
        raise ValueError("La pregunta está vacía.")
    t0 = time.perf_counter()
    ruta = elegir_ruta(pregunta, agente, historial)

    tipo_charla = charla(pregunta)
    if tipo_charla:
        return {"texto": respuesta_rapida(tipo_charla, db_path), "ruta": ruta, "fuentes": [], "datos": [],
                "confianza": None, "con_tienda": False, "rapida": True,
                "segundos": round(time.perf_counter() - t0, 2), "bruto": ""}

    if executor is None:
        if not os.getenv("OPENROUTER_API_KEY"):
            raise AgenteNoDisponible(SIN_CLAVE)
        from app.agents_engine.executor import AgentExecutor
        executor = AgentExecutor()
    peticion, fuentes, con_tienda = construir_peticion(db_path, pregunta, ruta, historial)
    try:
        bruto = executor.execute_agent_task(
            agent_name=ruta["agente"], skill_name="consultar_kb_agente",
            project_name=proyecto, user_request=peticion)
    except Exception as exc:                               # noqa: BLE001 — se traduce para el operador
        raise AgenteNoDisponible(explicar_error(exc)) from exc

    natural = a_natural(bruto)
    citadas = {int(n) for n in re.findall(r"\[(\d{1,2})\]", natural["texto"])}
    return {
        "texto": natural["texto"], "ruta": ruta,
        "fuentes": [f for f in fuentes if f["n"] in citadas],
        "datos": natural["datos"], "confianza": natural["confianza"],
        "con_tienda": bool(con_tienda and natural["usa_tienda"]), "rapida": False,
        "segundos": round(time.perf_counter() - t0, 2), "bruto": bruto,
    }


def trocear(texto: str, palabras: int = 3) -> Iterator[str]:
    """Parte el texto en trozos de pocas palabras (conserva espacios y saltos) para mostrarlo al vuelo."""
    piezas = re.findall(r"\S+\s*|\s+", texto or "")
    for i in range(0, len(piezas), max(1, palabras)):
        yield "".join(piezas[i:i + max(1, palabras)])
