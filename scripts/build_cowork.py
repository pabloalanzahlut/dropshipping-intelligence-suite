#!/usr/bin/env python3
"""Genera lo que Cowork consume a partir de las fuentes de verdad del repositorio.

Cowork corre en la nube: no ve `.claude/commands/`, ni `CLAUDE.md`, ni `app/`. Este
script empaqueta lo necesario sin mover ninguna fuente de sitio:

  plugin    → plugins/gem-os/ + .claude-plugin/marketplace.json   (se versiona)
  contexto  → cowork/contexto/  espejo de solo lectura de reglas, KB y proyecto activo
              (no se versiona; es lo único del repo que la carpeta de Cowork contiene)

Uso:
  python scripts/build_cowork.py              # plugin + contexto
  python scripts/build_cowork.py plugin
  python scripts/build_cowork.py contexto
  python scripts/build_cowork.py --check      # no escribe; sale con 1 si el plugin
                                              # versionado difiere o falla una compuerta
  python scripts/build_cowork.py --quiet      # sin salida si todo va bien (hook)
  python scripts/build_cowork.py --zip        # además dist_cowork/gem-os.zip

El plugin se construye en memoria, se valida y solo entonces se escribe: si una
compuerta falla, `plugins/gem-os/` se queda como estaba.

Stdlib pura. No llama a ningún modelo ni a la red.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parent
sys.path.insert(0, str(AQUI))
import precommit_secrets  # noqa: E402  (mismos patrones que bloquean el auto-commit)

SRC = AQUI / "cowork_src"
COMMANDS = ROOT / ".claude" / "commands"
AGENTS = ROOT / ".claude" / "agents"
MEMORY = ROOT / ".claude" / "memory"
GATE = ROOT / "app" / "services" / "deterministic_gate.py"
CLAUDE_MD = ROOT / "CLAUDE.md"
AUTO_DISPATCH = ROOT / "ai_workspace" / "config" / "auto_dispatch.md"

PLUGIN = "gem-os"
MARKETPLACE = "gem-os-suite"
PLUGIN_DIR = ROOT / "plugins" / PLUGIN
MARKETPLACE_JSON = ROOT / ".claude-plugin" / "marketplace.json"
CONTEXTO = ROOT / "cowork" / "contexto"
ZIP = ROOT / "dist_cowork" / f"{PLUGIN}.zip"
LOG = ROOT / "logs" / "cowork_build.log"

DESCRIPCION = (
    "GEM OS — inteligencia para dropshipping en Shopify: buscar, clasificar, refutar y "
    "validar productos; hooks, guiones, fichas y anuncios; caja, ROAS y escalado. Con las "
    "reglas financieras de Adrián Sáenz y un gate determinista."
)

# ── Qué se exporta ────────────────────────────────────────────────────────────
# Lista blanca explícita: un comando nuevo NO llega a Cowork hasta que se añade aquí.
SKILLS_COWORK: Tuple[str, ...] = (
    "buscar-producto", "clasificar-producto", "refutar-producto", "validar-financiero",
    "matriz-precios", "fake-door", "hook-matrix", "redactar-guion", "oferta-multiunidad",
    "estructurar-landing", "redactar-ficha-shopify", "clonar-seccion",
    "redactar-anuncios-meta", "gestionar-meta-ads", "investigar-nicho", "monitorear-caja",
    "escalar-campana", "consultar-kb", "consolidar-manual", "configurar-tienda",
    "trafico-organico", "google-ads", "tiktok-ads", "amazon-dropshipping", "tiktok-shop",
    "experto-make", "autods-notas", "pipeline-completo",
)
# Necesitan `.env`, scripts locales, cookies o git: se quedan en Claude Code.
SOLO_CODE: Tuple[str, ...] = (
    "importar-masivo", "generar-video-ia", "monitorear-skool", "recuperar-carrito",
    "resolver-github", "destilar-skill", "experto-claude",
)
PROCEDIMIENTOS_SOLO_CODE = frozenset({
    "importar_masivo", "monitorear_skool", "recuperar_carrito_abandonado", "resolver_github",
    "publicar_tiktok_automatico", "generar_imagen_producto", "experto_claude",
    "ingerir_transcripcion_kb",
})
# La descripción decide cuándo Cowork carga la skill. Sale de la tabla de skills de
# CLAUDE.md; aquí solo se fijan las que no están en esa tabla o la tienen poco precisa.
FUNCIONES = {
    "validar-financiero": (
        "Valida un producto con las reglas financieras de GEM OS: multiplicador mínimo 2x y "
        "objetivo 3x sobre coste landed (producto + envío), fees 4,0 %, cancelaciones 10,1 % "
        "y CPA de equilibrio"
    ),
    "matriz-precios": (
        "Genera la matriz de precios 2x/3x de un lote de productos sobre coste landed, con "
        "PVP terminados en .99 y clasificación HOT/WARM/COLD/DISCARD"
    ),
    "autods-notas": (
        "Redacta en inglés las notas para proveedores de AutoDS/AliExpress: declaración de "
        "dropshipping, packaging, factura sin precios, control de calidad, envío y devoluciones"
    ),
}
AGENTES_COWORK: Tuple[str, ...] = ("gem-financial-guard", "gem-bulk-copy")
SKILLS_BASE: Tuple[str, ...] = ("reglas-gem-os", "verificar-salida")

SECCIONES_NUCLEO: Tuple[str, ...] = (
    "IDENTIDAD Y MISIÓN", "REGLA SUPREMA: NO INVENTAR", "JERARQUÍA DE FUENTES",
    "REGLAS FINANCIERAS", "PIPELINE DE AGENTES (DAG)", "RESTRICCIONES POR ROL",
    "VERIFICACIÓN DE SALIDAS",
)

# ── Adaptación de rutas y conectores ──────────────────────────────────────────
RE_REF = re.compile(r"ai_workspace/(?:skills/[a-z0-9_]+/procedimiento\.md|templates/[A-Za-z0-9_.-]+\.md)")
SUSTITUCIONES: Tuple[Tuple[str, str], ...] = (
    (".claude/memory/reglas-financieras.md", "reglas-gem-os/reglas-financieras.md"),
    (".claude/memory/verificacion-determinista.md", "reglas-gem-os/verificacion-determinista.md"),
    (".continue/rules/dropshipping_financial_rules.md", "reglas-gem-os/reglas-financieras.md"),
    ("app/services/deterministic_gate.py", "verificar-salida/scripts/deterministic_gate.py"),
    ("ai_workspace/knowledge_base/", "contexto/kb/"),
    ("ai_workspace/context/", "contexto/manual/"),
    ("ai_workspace/projects/producto_01/", "contexto/proyecto_activo/"),
    ("ai_workspace/projects/", "contexto/proyecto_activo/"),
    ("ai_workspace/memory/kb_index.json", "contexto/kb_index.json"),
)
# Los IDs `mcp__xxxxxxxx` son de una sesión de Claude Code; en Cowork se usa el nombre.
CONECTORES = {
    "69f3b6ec": "Google Sheets", "1cc6d3ec": "Stripe", "ae68f902": "Gmail",
    "73e33a54": "Google Drive", "490e8c15": "Google Calendar", "d3daeaff": "AutoDS",
}
RE_CONECTOR_PAREN = re.compile(r"\s*\(`mcp__[0-9a-f]{8}[^`]*`\)")
RE_CONECTOR = re.compile(r"`?mcp__([0-9a-f]{8})[A-Za-z0-9_*-]*`?")

# ── Compuertas ────────────────────────────────────────────────────────────────
# Texto que contradice `.claude/memory/reglas-financieras.md`. Si aparece en una
# fuente, el plugin no se regenera: en Cowork no hay CLAUDE.md que lo corrija.
PROHIBIDOS = {
    "multiplicador sobre el producto solo (debe ser sobre coste landed)":
        re.compile(r"PVP\s*/\s*(?:CO\b|Costo[_ ]origen|costo[_ ]origen|coste de origen)"),
    "umbral 1,5x (el mínimo es 2x)": re.compile(r"\b1[.,]5\s*x\b"),
    "dato asumido en vez de DATA_GAP_REQUEST": re.compile(r"como estimado|defaults? (?:de envío|por vertical)", re.I),
    "ID de conector de sesión": re.compile(r"mcp__[0-9a-f]{8}"),
}
RE_WEBHOOK = re.compile(r"hook\.[a-z0-9]+\.make\.com/(?!X+\b)[A-Za-z0-9]{8,}")
RE_NOMBRE_SKILL = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TEXTO = (".md", ".json", ".py", ".txt")

# ── Espejo de contexto ────────────────────────────────────────────────────────
ESPEJO: Tuple[Tuple[str, Tuple[str, ...], str], ...] = (
    (".claude/memory", ("reglas-financieras.md", "verificacion-determinista.md"), "reglas"),
    ("ai_workspace/knowledge_base", ("**/*.md", "skool_productos.json"), "kb"),
    ("ai_workspace/context", ("*.md",), "manual"),
    ("ai_workspace/projects/producto_01", ("**/*.md", "**/*.json"), "proyecto_activo"),
    ("ai_workspace/memory", ("kb_index.json",), ""),
)
LEEME_CONTEXTO = """# contexto/ — espejo de solo lectura

Generado por `scripts/build_cowork.py` desde el repositorio de GEM OS. **No edites nada
aquí:** se sobrescribe en la siguiente sincronización y no llega al sistema.

- `reglas/` — reglas financieras y de verificación
- `kb/` — Knowledge Base de los mentores
- `manual/` — manual táctico consolidado
- `proyecto_activo/` — producto en curso
- `_MANIFEST.json` — origen, sha256 y fecha de modificación de cada archivo
"""


class BuildError(Exception):
    pass


# ── Utilidades ────────────────────────────────────────────────────────────────

def _norm(b: bytes) -> bytes:
    """git (autocrlf) puede dejar CRLF en disco; el contenido es el mismo."""
    return b.replace(b"\r\n", b"\n")


def _leer(p: Path) -> str:
    return p.read_text(encoding="utf-8").replace("\r\n", "\n")


def _b(texto: str) -> bytes:
    return (texto.rstrip("\n") + "\n").encode("utf-8")


def _frontmatter(texto: str) -> Tuple[Dict[str, str], str]:
    if texto.startswith("---\n"):
        fin = texto.find("\n---\n", 4)
        if fin != -1:
            meta = {}
            for linea in texto[4:fin].splitlines():
                if ":" in linea:
                    k, v = linea.split(":", 1)
                    meta[k.strip()] = v.strip()
            return meta, texto[fin + 5:].lstrip("\n")
    return {}, texto


def _secretos(nombre: str, texto: str) -> List[str]:
    hallazgos = []
    if precommit_secrets.NOMBRES.search(nombre) and not precommit_secrets.NOMBRES_OK.search(nombre):
        hallazgos.append("nombre de archivo sensible")
    for etiqueta, patron in precommit_secrets.PATRONES.items():
        m = patron.search(texto)
        if m and not precommit_secrets.PLACEHOLDER.search(m.group(0)):
            hallazgos.append(etiqueta)
    if RE_WEBHOOK.search(texto):
        hallazgos.append("URL de webhook de Make")
    return hallazgos


def adaptar(texto: str) -> str:
    """Rutas del repo → rutas visibles en Cowork; IDs de conector → nombre."""
    for origen, destino in SUSTITUCIONES:
        texto = texto.replace(origen, destino)
    texto = RE_CONECTOR_PAREN.sub("", texto)

    def _nombre(m: re.Match) -> str:
        if m.group(1) not in CONECTORES:
            raise BuildError(f"ID de conector sin nombre: mcp__{m.group(1)} — añádelo a CONECTORES")
        return f"conector {CONECTORES[m.group(1)]}"

    return RE_CONECTOR.sub(_nombre, texto)


def _resolver_refs(texto: str, refs: Dict[str, Path]) -> str:
    """Procedimientos y plantillas citados → `referencias/<nombre>.md` dentro de la skill."""
    def _sub(m: re.Match) -> str:
        ruta = ROOT / m.group(0)
        es_proc = ruta.name == "procedimiento.md"
        if es_proc and ruta.parent.name in PROCEDIMIENTOS_SOLO_CODE:
            return f"(procedimiento «{ruta.parent.name}»: solo disponible en Claude Code)"
        if not ruta.is_file():
            raise BuildError(f"referencia inexistente: {m.group(0)}")
        nombre = (ruta.parent.name if es_proc else ruta.stem) + ".md"
        refs[nombre] = ruta
        return f"referencias/{nombre}"

    return RE_REF.sub(_sub, texto)


# ── Descripciones (routing en Cowork) ─────────────────────────────────────────

def _tabla_funciones() -> Dict[str, str]:
    """CLAUDE.md → `| `/comando` | Función |`."""
    out: Dict[str, str] = {}
    for m in re.finditer(r"^\|\s*`/([a-z0-9-]+)`\s*\|\s*(.+?)\s*\|\s*$", _leer(CLAUDE_MD), re.M):
        out.setdefault(m.group(1), m.group(2))
    return out


def _tabla_keywords() -> Dict[str, str]:
    """auto_dispatch.md → `| palabras clave | `/comando` | … |`."""
    out: Dict[str, str] = {}
    for m in re.finditer(r"^\|\s*([^|`]+?)\s*\|\s*`/([a-z0-9-]+)`\s*\|", _leer(AUTO_DISPATCH), re.M):
        out.setdefault(m.group(2), m.group(1))
    return out


def _titulo(cuerpo: str, cmd: str) -> str:
    for linea in cuerpo.splitlines():
        if linea.startswith("# "):
            t = re.sub(r"^(Skill:\s*)?(/[a-z0-9-]+\s*[—-]?\s*)?", "", linea[2:].strip())
            if t:
                return t
    return cmd.replace("-", " ").capitalize()


def _descripcion(cmd: str, meta: Dict[str, str], cuerpo: str,
                 funciones: Dict[str, str], keywords: Dict[str, str]) -> str:
    if meta.get("description"):
        return meta["description"]
    funcion = (FUNCIONES.get(cmd) or funciones.get(cmd) or _titulo(cuerpo, cmd)).rstrip(". ")
    desc = f"{funcion}."
    if keywords.get(cmd):
        desc += f" Usar cuando el usuario hable de: {keywords[cmd]}."
    return desc


# ── Construcción del plugin (en memoria) ──────────────────────────────────────

def construir_skill(cmd: str, funciones: Dict[str, str], keywords: Dict[str, str]) -> Dict[str, bytes]:
    origen = COMMANDS / f"{cmd}.md"
    if not origen.is_file():
        raise BuildError(f"comando en la lista blanca sin archivo: {origen.relative_to(ROOT).as_posix()}")
    meta, cuerpo_crudo = _frontmatter(_leer(origen))
    refs: Dict[str, Path] = {}
    cuerpo = adaptar(_resolver_refs(cuerpo_crudo, refs))

    archivos: Dict[str, bytes] = {}
    pendientes, hechos = dict(refs), set()
    while pendientes:
        nombre, ruta = pendientes.popitem()
        if nombre in hechos:
            continue
        hechos.add(nombre)
        nuevas: Dict[str, Path] = {}
        archivos[f"referencias/{nombre}"] = _b(adaptar(_resolver_refs(_leer(ruta), nuevas)))
        pendientes.update({k: v for k, v in nuevas.items() if k not in hechos})

    preambulo = _leer(SRC / "preambulo.md").replace("{origen}", f".claude/commands/{cmd}.md").rstrip("\n")
    desc = _descripcion(cmd, meta, cuerpo_crudo, funciones, keywords)
    cabecera = f"---\nname: {cmd}\ndescription: {json.dumps(desc, ensure_ascii=False)}\n---\n"
    archivos["SKILL.md"] = _b(f"{cabecera}\n{preambulo}\n\n{cuerpo}")
    return archivos


def _nucleo() -> str:
    secciones: Dict[str, str] = {}
    titulo, lineas = None, []
    for linea in _leer(CLAUDE_MD).splitlines():
        if linea.startswith("## "):
            if titulo:
                secciones[titulo] = "\n".join(lineas)
            titulo, lineas = linea[3:].strip(), [linea]
        elif titulo:
            lineas.append(linea)
    if titulo:
        secciones[titulo] = "\n".join(lineas)

    faltan = [s for s in SECCIONES_NUCLEO if s not in secciones]
    if faltan:
        raise BuildError(f"CLAUDE.md ya no tiene las secciones {faltan}; actualiza SECCIONES_NUCLEO")
    partes = [re.sub(r"\n-{3,}\s*$", "", secciones[s].rstrip()) for s in SECCIONES_NUCLEO]
    cabecera = (
        "# GEM OS — núcleo de reglas\n\n"
        "Extraído de `CLAUDE.md` del repositorio de GEM OS al generar el plugin. No editar.\n"
        "Los `/comandos` citados son aquí las skills del plugin `gem-os` con el mismo nombre.\n"
    )
    return adaptar(cabecera + "\n" + "\n\n".join(partes))


def construir_plugin() -> Dict[str, bytes]:
    """Devuelve {ruta relativa a plugins/gem-os: contenido}. No toca el disco."""
    funciones, keywords = _tabla_funciones(), _tabla_keywords()
    mapa: Dict[str, bytes] = {}

    for cmd in SKILLS_COWORK:
        for rel, contenido in construir_skill(cmd, funciones, keywords).items():
            mapa[f"skills/{cmd}/{rel}"] = contenido

    mapa["skills/reglas-gem-os/SKILL.md"] = _b(_leer(SRC / "reglas-gem-os" / "SKILL.md"))
    mapa["skills/reglas-gem-os/gem-os-nucleo.md"] = _b(_nucleo())
    for nombre in ("reglas-financieras.md", "verificacion-determinista.md"):
        mapa[f"skills/reglas-gem-os/{nombre}"] = _b(_leer(MEMORY / nombre))

    mapa["skills/verificar-salida/SKILL.md"] = _b(_leer(SRC / "verificar-salida" / "SKILL.md"))
    mapa["skills/verificar-salida/scripts/gate_cli.py"] = _b(_leer(SRC / "verificar-salida" / "gate_cli.py"))
    # El gate no se adapta ni se reescribe: copia exacta.
    mapa["skills/verificar-salida/scripts/deterministic_gate.py"] = _norm(GATE.read_bytes())

    for agente in AGENTES_COWORK:
        mapa[f"agents/{agente}.md"] = _b(adaptar(_leer(AGENTS / f"{agente}.md")))

    mapa["README.md"] = _b(
        f"# Plugin `{PLUGIN}` — GENERADO, no editar\n\n"
        "Lo genera `scripts/build_cowork.py` desde `.claude/commands/`, "
        "`ai_workspace/skills/`, `.claude/memory/`, `CLAUDE.md` y "
        "`app/services/deterministic_gate.py`. Cualquier cambio hecho aquí se pierde en la "
        "siguiente generación: edita la fuente.\n\n"
        f"- Skills: {len(SKILLS_COWORK) + len(SKILLS_BASE)}\n"
        f"- Agentes: {len(AGENTES_COWORK)}\n"
        "- Guía de uso: `cowork/GUIA.md`\n\n"
        "## Instalación\n\n"
        "En Cowork o claude.ai: *Customize → Plugins → Add → Add marketplace* con el "
        "repositorio de GEM OS, y añadir `gem-os`. En Claude Code:\n\n"
        "```\n"
        f"/plugin install {PLUGIN} --marketplace <owner>/<repo>\n"
        "```\n"
    )

    huella = hashlib.sha256()
    for rel in sorted(mapa):
        huella.update(rel.encode("utf-8") + b"\0" + mapa[rel] + b"\0")
    manifiesto = {
        "name": PLUGIN,
        "displayName": "GEM OS",
        # Cambia solo si cambia el contenido: quien lo tiene instalado recibe la actualización.
        "version": f"1.0.0-{huella.hexdigest()[:10]}",
        "description": DESCRIPCION,
        "author": {"name": "GEM OS"},
        "keywords": ["dropshipping", "shopify", "ecommerce", "meta-ads", "tiktok"],
    }
    mapa[".claude-plugin/plugin.json"] = _b(json.dumps(manifiesto, ensure_ascii=False, indent=2))
    return mapa


def construir_marketplace() -> bytes:
    return _b(json.dumps({
        "name": MARKETPLACE,
        "description": "Plugins de GEM OS (uso personal)",
        "owner": {"name": "GEM OS"},
        "plugins": [{"name": PLUGIN, "source": f"./plugins/{PLUGIN}", "description": DESCRIPCION}],
    }, ensure_ascii=False, indent=2))


# ── Compuertas ────────────────────────────────────────────────────────────────

def lint_texto(rel: str, texto: str) -> List[str]:
    """Errores de un archivo de texto del plugin. Función pura (se prueba aparte)."""
    errores = [f"{rel}: {s}" for s in _secretos(rel, texto)]
    if rel.endswith(".md"):
        for motivo, patron in PROHIBIDOS.items():
            m = patron.search(texto)
            if m:
                errores.append(f"{rel}: {motivo} → «{m.group(0)}»")
    return errores


def validar(mapa: Dict[str, bytes]) -> List[str]:
    errores: List[str] = []

    gate_rel = "skills/verificar-salida/scripts/deterministic_gate.py"
    if hashlib.sha256(mapa[gate_rel]).digest() != hashlib.sha256(_norm(GATE.read_bytes())).digest():
        errores.append(f"{gate_rel}: no es copia exacta de app/services/deterministic_gate.py")

    for rel, contenido in sorted(mapa.items()):
        if rel.endswith(TEXTO):
            try:
                texto = contenido.decode("utf-8")
            except UnicodeDecodeError:
                errores.append(f"{rel}: no es UTF-8")
                continue
            errores.extend(lint_texto(rel, texto))

    skills = sorted({rel.split("/")[1] for rel in mapa if rel.startswith("skills/")})
    for skill in skills:
        if skill in SOLO_CODE:
            errores.append(f"skills/{skill}: es solo de Claude Code y no debe exportarse")
        if not RE_NOMBRE_SKILL.match(skill) or len(skill) > 64:
            errores.append(f"skills/{skill}: nombre no válido (kebab-case, máx. 64)")
        skill_md = mapa.get(f"skills/{skill}/SKILL.md")
        if skill_md is None:
            errores.append(f"skills/{skill}: falta SKILL.md")
            continue
        texto_skill = skill_md.decode("utf-8")
        meta, _ = _frontmatter(texto_skill)
        if meta.get("name") != skill:
            errores.append(f"skills/{skill}/SKILL.md: `name` no coincide con la carpeta")
        try:
            desc = json.loads(meta.get("description", ""))
        except json.JSONDecodeError:
            desc = ""
        if not isinstance(desc, str) or not desc.strip() or len(desc) > 1024:
            errores.append(f"skills/{skill}/SKILL.md: `description` vacía, sin comillas o > 1024 caracteres")
        # Toda referencia citada tiene que viajar con la skill
        for ref in set(re.findall(r"referencias/[A-Za-z0-9_.-]+\.md", texto_skill)):
            if f"skills/{skill}/{ref}" not in mapa:
                errores.append(f"skills/{skill}/SKILL.md: cita {ref} y no está empaquetada")

    for rel in (".claude-plugin/plugin.json",):
        try:
            if json.loads(mapa[rel].decode("utf-8")).get("name") != PLUGIN:
                errores.append(f"{rel}: `name` incorrecto")
        except (KeyError, ValueError):
            errores.append(f"{rel}: JSON inválido")
    return errores


def sin_clasificar() -> List[str]:
    """Comandos que no están ni en la lista blanca ni en la de solo-Code (aviso, no error)."""
    conocidos = set(SKILLS_COWORK) | set(SOLO_CODE)
    return sorted(p.stem for p in COMMANDS.glob("*.md") if p.stem not in conocidos)


# ── Disco ─────────────────────────────────────────────────────────────────────

def diferencias(mapa: Dict[str, bytes], base: Path) -> List[str]:
    difs = []
    for rel, contenido in sorted(mapa.items()):
        destino = base / rel
        if not destino.is_file():
            difs.append(f"falta {rel}")
        elif _norm(destino.read_bytes()) != contenido:
            difs.append(f"desactualizado {rel}")
    if base.is_dir():
        for p in sorted(base.rglob("*")):
            if p.is_file() and p.relative_to(base).as_posix() not in mapa:
                difs.append(f"sobra {p.relative_to(base).as_posix()}")
    return difs


def escribir(mapa: Dict[str, bytes], base: Path) -> int:
    """Escribe solo lo que cambia y borra lo que sobra dentro de `base`. Devuelve nº de cambios."""
    cambios = 0
    for rel, contenido in mapa.items():
        destino = base / rel
        if destino.is_file() and _norm(destino.read_bytes()) == contenido:
            continue
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(contenido)
        cambios += 1
    if base.is_dir():
        for p in sorted(base.rglob("*"), reverse=True):
            if p.is_file() and p.relative_to(base).as_posix() not in mapa:
                p.unlink()
                cambios += 1
            elif p.is_dir() and not any(p.iterdir()):
                p.rmdir()
    return cambios


def generar_zip(mapa: Dict[str, bytes]) -> Path:
    ZIP.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(mapa):
            z.writestr(rel, mapa[rel])
    return ZIP


# ── Espejo de contexto ────────────────────────────────────────────────────────

def sincronizar_contexto() -> Dict[str, object]:
    """repo → cowork/contexto/. Unidireccional: lo que haya en el destino se sobrescribe."""
    entradas: Dict[str, Dict[str, str]] = {}
    contenidos: Dict[str, bytes] = {}
    omitidos: List[str] = []

    for origen_rel, patrones, destino_rel in ESPEJO:
        origen = ROOT / origen_rel
        if not origen.is_dir():
            continue
        vistos = set()
        for patron in patrones:
            for p in sorted(origen.glob(patron)):
                if not p.is_file() or p in vistos:
                    continue
                vistos.add(p)
                datos = p.read_bytes()
                rel_origen = p.relative_to(ROOT).as_posix()
                if _secretos(rel_origen, datos.decode("utf-8", errors="replace")):
                    omitidos.append(rel_origen)
                    continue
                rel = "/".join(x for x in (destino_rel, p.relative_to(origen).as_posix()) if x)
                contenidos[rel] = datos
                entradas[rel] = {
                    "origen": rel_origen,
                    "sha256": hashlib.sha256(datos).hexdigest(),
                    "modificado": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
                                          .strftime("%Y-%m-%dT%H:%M:%SZ"),
                }

    contenidos["LEEME.md"] = _b(LEEME_CONTEXTO)
    manifiesto = {
        "descripcion": "Espejo de solo lectura generado por scripts/build_cowork.py",
        "archivos": {k: entradas[k] for k in sorted(entradas)},
    }
    contenidos["_MANIFEST.json"] = _b(json.dumps(manifiesto, ensure_ascii=False, indent=2))

    cambios = 0
    for rel, datos in contenidos.items():
        destino = CONTEXTO / rel
        if destino.is_file() and destino.read_bytes() == datos:
            continue
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(datos)
        cambios += 1
    for p in sorted(CONTEXTO.rglob("*"), reverse=True):
        if p.is_file() and p.relative_to(CONTEXTO).as_posix() not in contenidos:
            p.unlink()
            cambios += 1
        elif p.is_dir() and not any(p.iterdir()):
            p.rmdir()
    return {"archivos": len(entradas), "cambios": cambios, "omitidos": omitidos}


# ── CLI ───────────────────────────────────────────────────────────────────────

def _registrar(errores: List[str]) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')} build_cowork FALLÓ\n")
            f.writelines(f"  {e}\n" for e in errores)
    except OSError:
        pass


def main(argv=None) -> int:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Genera el plugin gem-os y el espejo de contexto para Cowork")
    parser.add_argument("objetivo", nargs="?", default="todo", choices=["todo", "plugin", "contexto"])
    parser.add_argument("--check", action="store_true", help="No escribe; exit 1 si el plugin difiere o no valida")
    parser.add_argument("--quiet", action="store_true", help="Sin salida si todo va bien")
    parser.add_argument("--zip", action="store_true", help="Genera también dist_cowork/gem-os.zip")
    args = parser.parse_args(argv)
    decir = (lambda *_: None) if args.quiet else print

    if args.objetivo in ("todo", "plugin") or args.check:
        try:
            mapa = construir_plugin()
            errores = validar(mapa)
        except (BuildError, OSError) as e:
            mapa, errores = {}, [str(e)]
        if errores:
            _registrar(errores)
            print(f"build_cowork: el plugin NO se ha regenerado ({len(errores)} error(es)):", file=sys.stderr)
            for e in errores:
                print(f"  ✗ {e}", file=sys.stderr)
            return 1

        marketplace = construir_marketplace()
        if args.check:
            difs = [f"plugins/{PLUGIN}: {d}" for d in diferencias(mapa, PLUGIN_DIR)]
            if not MARKETPLACE_JSON.is_file() or _norm(MARKETPLACE_JSON.read_bytes()) != marketplace:
                difs.append(".claude-plugin/marketplace.json: desactualizado")
            if difs:
                print("build_cowork --check: el plugin versionado no coincide con las fuentes:", file=sys.stderr)
                for d in difs:
                    print(f"  ✗ {d}", file=sys.stderr)
                print("  → ejecuta: python scripts/build_cowork.py plugin", file=sys.stderr)
                return 1
            decir(f"build_cowork --check: OK ({len(mapa)} archivos, compuertas en verde)")
            return 0

        cambios = escribir(mapa, PLUGIN_DIR)
        if not MARKETPLACE_JSON.is_file() or _norm(MARKETPLACE_JSON.read_bytes()) != marketplace:
            MARKETPLACE_JSON.parent.mkdir(parents=True, exist_ok=True)
            MARKETPLACE_JSON.write_bytes(marketplace)
            cambios += 1
        decir(f"plugin {PLUGIN}: {len(mapa)} archivos, {cambios} cambio(s)")
        pendientes = sin_clasificar()
        if pendientes:
            decir(f"  aviso: comandos sin clasificar (no exportados): {', '.join(pendientes)}")
        if args.zip:
            decir(f"  zip: {generar_zip(mapa).relative_to(ROOT).as_posix()}")

    if args.objetivo in ("todo", "contexto"):
        try:
            r = sincronizar_contexto()
        except OSError as e:
            _registrar([f"contexto: {e}"])
            print(f"build_cowork: no se pudo sincronizar cowork/contexto/: {e}", file=sys.stderr)
            return 1
        decir(f"contexto: {r['archivos']} archivos, {r['cambios']} cambio(s)")
        if r["omitidos"]:
            decir(f"  omitidos por posible secreto: {', '.join(r['omitidos'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
