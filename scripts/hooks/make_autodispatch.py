"""Hook UserPromptSubmit: activa el skill /experto-make de forma automatica.

Se dispara en cada mensaje del usuario. Si el texto habla de Make.com, o el
mensaje trae capturas de pantalla, devuelve contexto adicional para que Claude
cargue el skill antes de responder. No modifica el mensaje ni bloquea nada.

Reglas:
  - Solo stdlib. Nunca debe fallar: ante cualquier error sale en silencio (exit 0).
  - No registra el contenido del mensaje (puede llevar URLs de webhook o claves).
    Solo escribe en la carpeta temporal del sistema un diagnostico con claves del
    payload, banderas y tipos de registro; nunca texto del usuario.

Deteccion de capturas (comprobado el 2026-11-12):
  El payload del hook trae solo el TEXTO (claves: cwd, hook_event_name, permission_mode,
  prompt, prompt_id, scratchpad_dir, session_id, transcript_path). La imagen no viene.
  Se lee la transcripcion (`transcript_path`): el mensaje del usuario se guarda como un
  registro `user` con bloque `image` y otro `isMeta` con `[Image: source: ...]`, ambos
  con `promptId`. Primer intento, sobre el hallazgo: replicado con 35 mensajes reales.
  En vivo la deteccion FALLO dos veces aunque el registro se creo ~280 ms antes del hook
  (causa sin determinar: volcado tardio a disco o prompt_id distinto), por eso:
    1. se reintenta unos instantes hasta que aparezca el registro de este mensaje,
    2. si no aparece, se usa un respaldo por antiguedad (registros muy recientes),
    3. el diagnostico queda en %TEMP%/gem_make_hook_debug.json.
"""
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone

# Terminos fuertes: casi siempre significan Make.com.
FUERTES = re.compile(
    r"(\bmake\.com\b|\beu\d\.make\b|\bintegromat\b|MAKE_WEBHOOK|"
    r"\bmake\b(?!\s+(?:sure|a|an|the|it|this|that|me|your|sense)\b))",
    re.IGNORECASE,
)
# Terminos del vocabulario de Make; en este proyecto casi siempre hablan de Make.
DEBILES = re.compile(
    r"\b(webhooks?|escenarios?|router|rutas? del router|m[oó]dulos?|"
    r"cr[eé]ditos de make|operaciones de make|run once|bundle|iterator)\b",
    re.IGNORECASE,
)
# Marcas de adjuntos de imagen que pueden aparecer en el texto del mensaje.
IMAGEN_EN_TEXTO = re.compile(
    r"(\[Image[^\]]*\]|\.(?:png|jpe?g|gif|webp)\b|data:image/)", re.IGNORECASE
)
MARCA_IMAGEN = re.compile(r"\[Image: source:")

ESPERAS = 5      # reintentos mientras el registro del mensaje no aparece
PAUSA_S = 0.3    # entre reintentos (maximo ~1,5 s de espera total)
EDAD_RESPALDO_S = 20


def _texto(payload):
    prompt = payload.get("prompt")
    if isinstance(prompt, str):
        return prompt
    if isinstance(prompt, list):
        return " ".join(
            b.get("text", "") for b in prompt if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def _hay_imagen_en_payload(payload):
    """Por si algun cliente entrega la imagen en el propio payload."""
    prompt = payload.get("prompt")
    if isinstance(prompt, str) and IMAGEN_EN_TEXTO.search(prompt):
        return True
    for clave in ("images", "attachments", "image_paths", "files"):
        if payload.get(clave):
            return True
    if isinstance(prompt, list):
        for bloque in prompt:
            if isinstance(bloque, dict) and bloque.get("type") == "image":
                return True
    return False


def _contiene_imagen(registro):
    contenido = (registro.get("message") or {}).get("content")
    if isinstance(contenido, list):
        for bloque in contenido:
            if not isinstance(bloque, dict):
                continue
            if bloque.get("type") == "image":
                return True
            if bloque.get("type") == "text" and MARCA_IMAGEN.search(bloque.get("text", "")):
                return True
    elif isinstance(contenido, str) and MARCA_IMAGEN.search(contenido):
        return True
    return False


def _leer_cola(ruta, tope_bytes=6_000_000):
    tam = os.path.getsize(ruta)
    with open(ruta, "rb") as f:
        f.seek(max(0, tam - tope_bytes))
        datos = f.read()
    lineas = datos.split(b"\n")
    if tam > tope_bytes:
        lineas = lineas[1:]  # la primera linea puede venir cortada
    return tam, lineas


def _escanear(lineas, pid, por_edad):
    """Recorre la transcripcion desde el final hasta la respuesta anterior del asistente.

    Devuelve (hay_imagen, vio_registro_de_este_mensaje, ultimos_tipos_para_diagnostico).
    Con por_edad=True se ignora el prompt_id y solo cuentan registros muy recientes.
    """
    ahora = datetime.now(timezone.utc)
    imagen = False
    visto = False
    ultimos = []
    examinados = 0
    for crudo in reversed(lineas):
        crudo = crudo.strip()
        if not crudo:
            continue
        try:
            d = json.loads(crudo)
        except Exception:
            continue
        tipo = d.get("type")
        if len(ultimos) < 6:
            ultimos.append([tipo, (d.get("promptId") or "")[:8], bool(d.get("isMeta"))])
        if tipo == "assistant":
            break  # respuesta anterior: el mensaje actual ya se reviso
        if tipo != "user":
            continue
        if por_edad:
            try:
                marca = d.get("timestamp")
                edad = (ahora - datetime.fromisoformat(marca.replace("Z", "+00:00"))).total_seconds()
                if edad > EDAD_RESPALDO_S:
                    break
            except Exception:
                break
        elif d.get("promptId") != pid:
            break  # mensaje anterior (o resumen de compactacion sin promptId)
        visto = True
        if _contiene_imagen(d):
            imagen = True
            break
        examinados += 1
        if examinados >= 8:
            break
    return imagen, visto, ultimos


def _imagen_en_transcripcion(payload, diag):
    ruta = payload.get("transcript_path")
    pid = payload.get("prompt_id")
    diag["prompt_id"] = (pid or "")[:8]
    if not isinstance(ruta, str) or not os.path.isfile(ruta):
        diag["transcript"] = False
        return False
    diag["transcript"] = True
    if pid:
        for intento in range(ESPERAS + 1):
            tam, lineas = _leer_cola(ruta)
            imagen, visto, ultimos = _escanear(lineas, pid, por_edad=False)
            diag.update(intento=intento, vio_registro=visto, bytes=tam, ultimos=ultimos)
            if imagen:
                diag["via"] = "prompt_id"
                return True
            if visto:
                diag["via"] = "prompt_id_sin_imagen"
                return False  # el registro de este mensaje ya esta y no trae imagen
            time.sleep(PAUSA_S)  # aun no esta escrito (o el id no coincide): esperar
    tam, lineas = _leer_cola(ruta)
    imagen, _, ultimos = _escanear(lineas, pid, por_edad=True)
    diag.update(ultimos=ultimos)
    diag["via"] = "respaldo_edad" if imagen else "ninguna"
    return imagen


def _guardar_diagnostico(diag):
    try:
        ruta = os.path.join(tempfile.gettempdir(), "gem_make_hook_debug.json")
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(diag, f)
    except Exception:
        pass


def main():
    diag = {"inicio": datetime.now(timezone.utc).isoformat()}
    try:
        crudo = sys.stdin.buffer.read().decode("utf-8", "replace")
        payload = json.loads(crudo) if crudo.strip() else {}
        if not isinstance(payload, dict):
            return 0
        texto = _texto(payload)
        fuerte = bool(FUERTES.search(texto))
        debil = bool(DEBILES.search(texto))
        diag.update(claves=sorted(payload.keys()), largo_prompt=len(texto), fuerte=fuerte, debil=debil)

        imagen = _hay_imagen_en_payload(payload)
        if not imagen and not (fuerte or debil):
            # Solo se mira la transcripcion si hace falta decidir (ahorra tiempo en mensajes con palabras clave).
            imagen = _imagen_en_transcripcion(payload, diag)
        diag["imagen"] = imagen
        diag["fin"] = datetime.now(timezone.utc).isoformat()
        _guardar_diagnostico(diag)

        if not (fuerte or debil or imagen):
            return 0

        motivos = []
        if fuerte or debil:
            motivos.append("el mensaje habla de Make.com")
        if imagen:
            motivos.append("el mensaje trae capturas de pantalla")

        contexto = (
            "[AUTO-DISPATCH /experto-make] Motivo: " + " y ".join(motivos) + ". "
            "ANTES de responder: carga el skill con la herramienta Skill (experto-make) o lee "
            "ai_workspace/skills/experto_make/procedimiento.md y ai_workspace/knowledge_base/make_curso_adrian.md, "
            "y aplica sus reglas y su protocolo de diagnostico. "
            "Si hay capturas, examinalas: si muestran Make (eu1.make.com, escenarios, modulos, filtros, "
            "History, errores), responde como especialista Make. Si la captura NO es de Make, ignora este aviso. "
            "Reglas fijas: no inventes datos (DATA_GAP_REQUEST); no entres a Make ni introduzcas credenciales; "
            "si una captura muestra una clave de API o una URL de webhook completa, avisa de que hay que rotarla "
            "y no la repitas en tu respuesta."
        )
        salida = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": contexto,
            }
        }
        sys.stdout.write(json.dumps(salida))  # ensure_ascii por defecto: seguro en cp1252
    except Exception as exc:
        diag["error"] = type(exc).__name__
        _guardar_diagnostico(diag)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
