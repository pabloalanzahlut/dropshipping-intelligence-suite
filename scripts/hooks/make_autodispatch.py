"""Hook UserPromptSubmit: activa el skill /experto-make de forma automatica.

Se dispara en cada mensaje del usuario. Si el texto habla de Make.com, o el
mensaje trae capturas de pantalla, devuelve contexto adicional para que Claude
cargue el skill antes de responder. No modifica el mensaje ni bloquea nada.

Reglas:
  - Solo stdlib. Nunca debe fallar: ante cualquier error sale en silencio (exit 0).
  - No registra el contenido del mensaje (puede llevar URLs de webhook o claves).
    Solo escribe en la carpeta temporal del sistema un resumen con las CLAVES del
    payload y banderas booleanas, para poder comprobar que el hook funciona.
"""
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone

# Terminos fuertes: casi siempre significan Make.com.
FUERTES = re.compile(
    r"(\bmake\.com\b|\beu\d\.make\b|\bintegromat\b|MAKE_WEBHOOK|"
    r"\bmake\b(?!\s+(?:sure|a|an|the|it|this|that|me|your|sense|sure)\b))",
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


def _hay_imagen(payload):
    """True si el payload indica adjuntos de imagen, en el texto o en campos extra."""
    prompt = payload.get("prompt")
    if isinstance(prompt, str) and IMAGEN_EN_TEXTO.search(prompt):
        return True
    for clave in ("images", "attachments", "image_paths", "files"):
        valor = payload.get(clave)
        if valor:
            return True
    if isinstance(prompt, list):  # por si el prompt llega como bloques
        for bloque in prompt:
            if isinstance(bloque, dict) and bloque.get("type") == "image":
                return True
    return False


MARCA_IMAGEN = re.compile(r"\[Image: source:")


def _imagen_en_transcripcion(payload, max_edad_s=120, tope_bytes=6_000_000):
    """Detecta capturas adjuntas leyendo la transcripcion de la sesion.

    Comprobado el 2026-11-12: el hook recibe solo el TEXTO del mensaje (claves: cwd,
    hook_event_name, permission_mode, prompt, prompt_id, scratchpad_dir, session_id,
    transcript_path), pero la imagen ya esta escrita en la transcripcion cuando el hook
    corre: un registro `user` con un bloque `image` y otro `isMeta` con el texto
    `[Image: source: ...]`, ambos con el mismo `promptId` que `prompt_id` del hook.
    Se recorren los registros desde el final hasta la respuesta anterior del asistente.
    """
    ruta = payload.get("transcript_path")
    pid = payload.get("prompt_id")
    if not isinstance(ruta, str) or not os.path.isfile(ruta):
        return False
    tam = os.path.getsize(ruta)
    with open(ruta, "rb") as f:
        f.seek(max(0, tam - tope_bytes))
        datos = f.read()
    lineas = datos.split(b"\n")
    if tam > tope_bytes:
        lineas = lineas[1:]  # la primera linea puede venir cortada
    ahora = datetime.now(timezone.utc)
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
        if tipo == "assistant":
            break  # llegamos a la respuesta anterior: el mensaje actual ya se reviso
        if tipo != "user":
            continue
        if pid and d.get("promptId") != pid:
            break  # es de un mensaje anterior (o un resumen de compactacion sin promptId)
        if not pid:
            marca = d.get("timestamp")
            try:
                edad = (ahora - datetime.fromisoformat(marca.replace("Z", "+00:00"))).total_seconds()
                if edad > max_edad_s:
                    break
            except Exception:
                pass
        contenido = (d.get("message") or {}).get("content")
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
        examinados += 1
        if examinados >= 8:
            break
    return False


def _texto(payload):
    prompt = payload.get("prompt")
    if isinstance(prompt, str):
        return prompt
    if isinstance(prompt, list):
        return " ".join(
            b.get("text", "") for b in prompt if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def _depuracion(payload, fuerte, debil, imagen):
    """Resumen sin contenido, para verificar que el hook se ejecuta y que ve."""
    try:
        resumen = {
            "claves": sorted(payload.keys()),
            "largo_prompt": len(_texto(payload)),
            "fuerte": bool(fuerte),
            "debil": bool(debil),
            "imagen": bool(imagen),
        }
        ruta = os.path.join(tempfile.gettempdir(), "gem_make_hook_debug.json")
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(resumen, f)
    except Exception:
        pass


def main():
    try:
        crudo = sys.stdin.buffer.read().decode("utf-8", "replace")
        payload = json.loads(crudo) if crudo.strip() else {}
        if not isinstance(payload, dict):
            return 0
        texto = _texto(payload)
        fuerte = FUERTES.search(texto)
        debil = DEBILES.search(texto)
        imagen = _hay_imagen(payload) or _imagen_en_transcripcion(payload)
        _depuracion(payload, fuerte, debil, imagen)

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
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
