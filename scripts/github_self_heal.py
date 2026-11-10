#!/usr/bin/env python3
"""Agente GitHub autónomo: detecta, resuelve (PR + merge) y documenta en la KB.

Python puro, sin LLM, solo stdlib. Fuente de fixes: ai_workspace/config/github_fixes.json.
Uso:
    python scripts/github_self_heal.py --dry-run
    python scripts/github_self_heal.py --log-file run.log --dry-run
    python scripts/github_self_heal.py            # en GitHub Actions (GITHUB_TOKEN)
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOGO = ROOT / "ai_workspace" / "config" / "github_fixes.json"
KB = ROOT / "ai_workspace" / "knowledge_base" / "github_kb.md"
GITLEAKS_TOML = ROOT / ".gitleaks.toml"
KB_MARCADOR = "<!-- Las nuevas incidencias se agregan debajo de esta línea -->"
ENTROPIA_REAL = 4.0
PLACEHOLDER = re.compile(
    r"(X{6,}|SECRET[O]?|EXAMPLE|PLACEHOLDER|FAKE|DUMMY|TU_CLAVE|TU_API|AQUI|CHANGEME|TEST)", re.I
)


# ---------------------------------------------------------------- catálogo / clasificación
def cargar_catalogo(path: Path = CATALOGO) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def limpiar_log(log: str) -> str:
    """Quita el timestamp ISO y los códigos ANSI que Actions antepone a cada línea."""
    log = re.sub(r"\x1b\[[0-9;]*m", "", log)
    return re.sub(r"(?m)^\d{4}-\d\d-\d\dT[\d:.]+Z ", "", log)


def parsear_hallazgos_gitleaks(log: str) -> list[dict]:
    """Extrae bloques 'Finding/Secret/RuleID/Entropy/File/Line/Commit' del log de gitleaks."""
    log = limpiar_log(log)
    hallazgos = []
    for bloque in re.split(r"\n(?=Finding:)", log):
        if "RuleID:" not in bloque:
            continue

        def campo(nombre: str) -> str:
            m = re.search(rf"^{nombre}:\s*(.+)$", bloque, re.M)
            return m.group(1).strip() if m else ""

        try:
            entropia = float(campo("Entropy") or 0)
        except ValueError:
            entropia = 0.0
        hallazgos.append({
            "rule": campo("RuleID"), "file": campo("File"), "line": campo("Line"),
            "commit": campo("Commit"), "entropy": entropia,
        })
    return hallazgos


def es_fuga_real(h: dict, valor: str | None) -> bool:
    """Real si la entropía es alta, la regla no es genérica o el valor no parece placeholder."""
    if h["rule"] != "generic-api-key" and h["rule"] != "sk-or-v1":
        return True
    if h["entropy"] >= ENTROPIA_REAL:
        return True
    if valor is None:
        return True
    return PLACEHOLDER.search(valor) is None


def clasificar(log: str, catalogo: dict) -> dict:
    """Devuelve {'tipo': ..., 'fix_id': ..., 'hallazgos': [...]} sin efectos secundarios."""
    log = limpiar_log(log)
    hallazgos = parsear_hallazgos_gitleaks(log)
    if hallazgos:
        return {"tipo": "gitleaks", "fix_id": None, "hallazgos": hallazgos}
    for fix in catalogo["fixes"]:
        if fix["accion"] == "issue_fuga":
            continue
        if re.search(fix["regex"], log, re.I | re.S):
            return {"tipo": "catalogo", "fix_id": fix["id"], "hallazgos": []}
    return {"tipo": "desconocido", "fix_id": None, "hallazgos": []}


def fix_por_id(catalogo: dict, fix_id: str) -> dict:
    return next(f for f in catalogo["fixes"] if f["id"] == fix_id)


def ruta_prohibida(ruta: str, catalogo: dict) -> bool:
    ruta = ruta.replace("\\", "/")
    return any(ruta == p or ruta.startswith(p) for p in catalogo["limites"]["rutas_prohibidas"])


# ---------------------------------------------------------------- fixes (devuelven archivos tocados)
def valor_en_commit(commit: str, archivo: str, linea: str) -> str | None:
    try:
        texto = subprocess.run(
            ["git", "show", f"{commit}:{archivo}"], cwd=ROOT, capture_output=True,
            text=True, encoding="utf-8", check=True,
        ).stdout.splitlines()
        fila = texto[int(linea) - 1]
    except (subprocess.CalledProcessError, ValueError, IndexError):
        return None
    m = re.search(r"[A-Za-z0-9_\-]{16,}", fila)
    return m.group(0) if m else None


def fix_allowlist_gitleaks(valor: str) -> list[str]:
    """Añade el literal exacto (escapado) a la allowlist de regex de .gitleaks.toml."""
    texto = GITLEAKS_TOML.read_text(encoding="utf-8")
    patron = f"'''^{re.escape(valor)}$'''"
    if patron in texto:
        return []
    texto = re.sub(r"(regexes\s*=\s*\[\n)", rf"\1  {patron},\n", texto, count=1)
    GITLEAKS_TOML.write_text(texto, encoding="utf-8")
    return [".gitleaks.toml"]


def fix_untrack(archivo: str) -> list[str]:
    tracked = subprocess.run(["git", "ls-files", "--", archivo], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if not tracked:
        return []
    subprocess.run(["git", "rm", "--cached", "-q", "--", archivo], cwd=ROOT, check=True)
    gi = ROOT / ".gitignore"
    entrada = archivo.rstrip("/") + ("/" if archivo.endswith("/") else "")
    contenido = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if entrada not in contenido.splitlines():
        gi.write_text(contenido.rstrip("\n") + f"\n{entrada}\n", encoding="utf-8")
    return [".gitignore", archivo]


def fix_secrets_a_env(workflow: Path) -> list[str]:
    """Mueve ${{ secrets.X }} de bloques run: a env: del mismo step (prefijo _)."""
    lineas = workflow.read_text(encoding="utf-8").splitlines()
    inicios = [i for i, l in enumerate(lineas) if re.match(r"^\s*- (name|uses|run):", l)]
    inicios.append(len(lineas))
    cambiado = False
    for k in range(len(inicios) - 2, -1, -1):
        a, b = inicios[k], inicios[k + 1]
        bloque = lineas[a:b]
        idx_run = next((i for i, l in enumerate(bloque) if re.match(r"^\s*(- )?run:", l)), None)
        if idx_run is None or any(re.match(r"^\s*env:", l) for l in bloque):
            continue
        secretos = sorted({m for l in bloque[idx_run:] for m in re.findall(r"\$\{\{\s*secrets\.([A-Za-z0-9_]+)\s*\}\}", l)})
        if not secretos:
            continue
        sangria = re.match(r"^(\s*)", bloque[idx_run]).group(1) + ("  " if bloque[idx_run].lstrip().startswith("- ") else "")
        for i in range(idx_run, len(bloque)):
            bloque[i] = re.sub(r"\$\{\{\s*secrets\.([A-Za-z0-9_]+)\s*\}\}", r'"$_\1"', bloque[i])
        env = [f"{sangria}env:"] + [f"{sangria}  _{s}: ${{{{ secrets.{s} }}}}" for s in secretos]
        lineas[a:b] = bloque[:idx_run] + env + bloque[idx_run:]
        cambiado = True
    if cambiado:
        workflow.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        return [str(workflow.relative_to(ROOT)).replace("\\", "/")]
    return []


def version_pypi_mas_reciente(paquete: str) -> str | None:
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{paquete}/json", timeout=20) as r:
            return json.load(r)["info"]["version"]
    except (urllib.error.URLError, KeyError, ValueError):
        return None


def fix_pin_version(paquete: str) -> list[str]:
    req = ROOT / "requirements.txt"
    nueva = version_pypi_mas_reciente(paquete)
    if not nueva:
        return []
    texto = req.read_text(encoding="utf-8")
    nuevo = re.sub(rf"(?im)^({re.escape(paquete)})==\S+", rf"\1=={nueva}", texto)
    if nuevo == texto:
        return []
    req.write_text(nuevo, encoding="utf-8")
    return ["requirements.txt"]


def mayor_mas_reciente_action(repo_action: str, token: str | None = None) -> str | None:
    """Devuelve 'vN' del último release publicado de la action, o None si no se puede saber."""
    cab = {"Accept": "application/vnd.github+json"}
    if token:
        cab["Authorization"] = f"Bearer {token}"
    try:
        r = urllib.request.Request(f"https://api.github.com/repos/{repo_action}/releases/latest", headers=cab)
        with urllib.request.urlopen(r, timeout=20) as resp:
            m = re.match(r"v?(\d+)", json.load(resp)["tag_name"])
        return f"v{m.group(1)}" if m else None
    except (urllib.error.URLError, KeyError, ValueError):
        return None


def fix_bump_actions(catalogo: dict, token: str | None = None, consulta=mayor_mas_reciente_action) -> list[str]:
    """Sube `uses: owner/repo@vN` al último major publicado. Nunca baja de versión."""
    tocados = []
    for wf in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        if ruta_prohibida(f".github/workflows/{wf.name}", catalogo):
            continue
        texto = wf.read_text(encoding="utf-8")

        def subir(m: re.Match) -> str:
            ultimo = consulta(m.group(1), token)
            if ultimo and int(ultimo[1:]) > int(m.group(2)):
                return f"{m.group(1)}@{ultimo}"
            return m.group(0)

        nuevo = re.sub(r"(?<=uses: )([\w.-]+/[\w.-]+)@v(\d+)", subir, texto)
        if nuevo != texto:
            wf.write_text(nuevo, encoding="utf-8")
            tocados.append(str(wf.relative_to(ROOT)).replace("\\", "/"))
    return tocados


SENSIBLES = re.compile(r"(^|/)([^/]*cookies[^/]*\.json|\.playwright-mcp/.*)$", re.I)


def toca_workflows(archivos: list[str]) -> bool:
    return any(a.replace("\\", "/").startswith(".github/workflows/") for a in archivos)


# ---------------------------------------------------------------- KB (aprendizaje)
def registrar_kb(fix_id: str, tipo: str, firma: str, resultado: str, fecha: dt.date | None = None) -> str:
    fecha = fecha or dt.date.today()
    texto = KB.read_text(encoding="utf-8")
    seq = max([int(n) for n in re.findall(r"INC-\d{8}-(\d{3})", texto)] or [0]) + 1
    inc = f"INC-{fecha:%Y%m%d}-{seq:03d}"
    bloque = (
        f"\n---\n\n## {inc} | {tipo} | AUTO\n\n"
        f"**Fecha:** {fecha.isoformat()}\n**Repositorio:** pabloalanzahlut/dropshipping-intelligence-suite\n"
        f"**Firma del error:** `{firma[:200]}`\n**Fix aplicado:** {fix_id} (agente github_self_heal)\n"
        f"**Resultado:** {resultado}\n**Tags:** [AUTO, {fix_id}]\n"
    )
    texto = texto.replace(KB_MARCADOR, KB_MARCADOR + "\n" + bloque, 1)
    if fix_id.startswith("F-"):
        texto = re.sub(
            rf"(?m)^(\| {fix_id} \|.*\| )(\d+)( \|)$", lambda m: f"{m.group(1)}{int(m.group(2)) + 1}{m.group(3)}", texto
        )
    KB.write_text(texto, encoding="utf-8")
    return inc


# ---------------------------------------------------------------- GitHub REST
class GitHub:
    def __init__(self, repo: str, token: str):
        self.repo, self.token = repo, token

    def req(self, metodo: str, ruta: str, cuerpo: dict | None = None, raw: bool = False):
        url = ruta if ruta.startswith("http") else f"https://api.github.com/repos/{self.repo}{ruta}"
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        r = urllib.request.Request(url, data=datos, method=metodo, headers={
            "Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"})
        with urllib.request.urlopen(r, timeout=60) as resp:
            contenido = resp.read()
        if raw:
            return contenido
        return json.loads(contenido) if contenido else {}

    def issue(self, titulo: str, cuerpo: str, labels: list[str]) -> None:
        abiertos = self.req("GET", "/issues?state=open&labels=selfheal&per_page=50")
        if any(i["title"] == titulo for i in abiertos):
            return
        self.req("POST", "/issues", {"title": titulo, "body": cuerpo, "labels": labels})


def log_del_run(gh: GitHub, run_id: int) -> str:
    zbytes = gh.req("GET", f"/actions/runs/{run_id}/logs", raw=True)
    with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
        return "\n".join(z.read(n).decode("utf-8", "replace") for n in z.namelist() if n.endswith(".txt"))


def git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=ROOT, check=True)


def prs_hoy(gh: GitHub) -> int:
    hoy = dt.date.today().isoformat()
    prs = gh.req("GET", "/pulls?state=all&per_page=50")
    return sum(1 for p in prs if p["head"]["ref"].startswith("selfheal/") and p["created_at"].startswith(hoy))


def git_ok(*args: str) -> bool:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True).returncode == 0


def abrir_pr_y_fusionar(gh: GitHub, rama: str, titulo: str, cuerpo: str, archivos: list[str]) -> str:
    """Rama -> commit -> push -> PR -> chequeo local (gitleaks) -> merge squash.

    El GITHUB_TOKEN no puede empujar cambios a .github/workflows/: si el fix los toca y no hay
    SELF_HEAL_TOKEN (PAT con scope workflow), se abre un Issue con el parche en vez de fallar.
    """
    pat = os.getenv("SELF_HEAL_TOKEN") or None
    if toca_workflows(archivos) and not pat:
        parche = subprocess.run(["git", "diff", "--", *[a for a in archivos if a.startswith(".github/workflows/")]],
                                cwd=ROOT, capture_output=True, text=True).stdout
        gh.issue(f"Parche listo para workflow: {titulo}",
                 "El GITHUB_TOKEN no puede modificar `.github/workflows/`. Aplicar este parche a mano o crear el "
                 "secreto `SELF_HEAL_TOKEN` (PAT con scope `workflow`) para que el agente lo haga solo.\n\n"
                 f"```diff\n{parche[:6000]}\n```", ["selfheal", "workflow"])
        git("checkout", "--", ".github/workflows")
        return "Fix de workflow NO empujado (falta SELF_HEAL_TOKEN) -> Issue con parche"
    git("config", "user.name", "gem-os-self-heal")
    git("config", "user.email", "self-heal@users.noreply.github.com")
    git("checkout", "-b", rama)
    for a in archivos:  # un archivo ignorado ya tiene su borrado en el índice (git rm --cached)
        if not git_ok("check-ignore", "-q", "--", a):
            git("add", "--", a)
    git("commit", "-m", f"fix(self-heal): {titulo}")
    destino = f"https://x-access-token:{pat}@github.com/{gh.repo}.git" if pat else "origin"
    git("push", destino, rama)
    try:
        pr = gh.req("POST", "/pulls", {"title": f"fix(self-heal): {titulo}", "head": rama, "base": "master", "body": cuerpo})
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 422):
            gh.issue("Self-heal no puede abrir PRs",
                     f"La rama `{rama}` ya está empujada con el fix. Activar en Settings > Actions > General > "
                     "'Allow GitHub Actions to create and approve pull requests' para que el agente cierre el ciclo solo.",
                     ["selfheal", "config"])
            return f"Rama {rama} empujada pero PR rechazado (HTTP {e.code}) -> Issue de configuración"
        raise
    chequeo = subprocess.run(
        ["gitleaks", "git", ".", "--config", ".gitleaks.toml", "--redact", "--no-banner", "--exit-code", "1"],
        cwd=ROOT, capture_output=True, text=True)
    if chequeo.returncode != 0:
        gh.req("POST", f"/issues/{pr['number']}/comments", {"body": "gitleaks sigue fallando tras el fix; no se fusiona."})
        return f"PR #{pr['number']} abierto, NO fusionado (gitleaks falla)"
    gh.req("PUT", f"/pulls/{pr['number']}/merge", {"merge_method": "squash"})
    return f"PR #{pr['number']} fusionado"


# ---------------------------------------------------------------- orquestación
def resolver(log: str, catalogo: dict, dry_run: bool, gh: GitHub | None = None) -> list[str]:
    informe: list[str] = []
    resultado = clasificar(log, catalogo)
    archivos: list[str] = []
    firma = log.strip().splitlines()[-1] if log.strip() else "log vacío"
    fix_usado, issue_fuga = None, []

    if resultado["tipo"] == "gitleaks":
        for h in resultado["hallazgos"]:
            valor = valor_en_commit(h["commit"], h["file"], h["line"])
            if es_fuga_real(h, valor):
                issue_fuga.append(h)
                informe.append(f"FUGA REAL: {h['rule']} en {h['file']}:{h['line']} ({h['commit'][:8]}) -> Issue crítico")
                continue
            fix_usado = "F-012"
            informe.append(f"Falso positivo {h['file']}:{h['line']} -> allowlist exacta (F-012)")
            if not dry_run:
                archivos += fix_allowlist_gitleaks(valor)
        for h in resultado["hallazgos"]:
            if SENSIBLES.search(h["file"].replace("\\", "/")):
                id_untrack = "F-010" if ".playwright-mcp/" in h["file"] else "F-009"
                fix_usado = fix_usado or id_untrack
                informe.append(f"Archivo sensible rastreado {h['file']} -> git rm --cached + .gitignore ({id_untrack})")
                if not dry_run:
                    archivos += fix_untrack(h["file"])
    elif resultado["tipo"] == "catalogo":
        fix = fix_por_id(catalogo, resultado["fix_id"])
        fix_usado = fix["id"]
        informe.append(f"Match {fix['id']} ({fix['tipo']}) auto={fix['auto']}")
        if fix["auto"] and not dry_run:
            if fix["accion"] == "pin_version_existente":
                m = re.search(fix["regex"], log)
                archivos += fix_pin_version(m.group(1)) if m else []
            elif fix["accion"] == "secrets_a_env":
                for wf in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
                    if not ruta_prohibida(f".github/workflows/{wf.name}", catalogo):
                        archivos += fix_secrets_a_env(wf)
            elif fix["accion"] == "bump_actions":
                archivos += fix_bump_actions(catalogo, os.getenv("GITHUB_TOKEN"))
            elif fix["accion"] == "cerrar_dependabot_obsoleto" and gh is not None:
                informe += cerrar_dependabot_obsoletos(gh, dry_run=False)
    else:
        informe.append("Firma desconocida -> Issue selfheal:nuevo (aprendizaje pendiente)")

    if dry_run or gh is None:
        return informe

    if issue_fuga:
        gh.issue("Fuga REAL de secreto detectada por gitleaks",
                 "Rotar la credencial de inmediato y revisar el historial. El agente NO reescribe historial.\n\n"
                 + "\n".join(f"- {h['rule']} {h['file']}:{h['line']} commit {h['commit']}" for h in issue_fuga),
                 ["selfheal", "security", "critical"])
    if resultado["tipo"] == "desconocido":
        gh.issue(f"Error CI sin fix conocido: {firma[:60]}", f"Registrar el fix con scripts/github_self_heal.py --registrar.\n\n```\n{log[-1500:]}\n```", ["selfheal", "nuevo"])
    archivos = [a for a in dict.fromkeys(archivos) if not ruta_prohibida(a, catalogo)]
    if archivos and prs_hoy(gh) < catalogo["limites"]["max_prs_por_dia"]:
        inc = registrar_kb(fix_usado or "F-000", "AUTO", firma, "✅ PR automático")
        archivos.append("ai_workspace/knowledge_base/github_kb.md")
        informe.append(abrir_pr_y_fusionar(gh, f"selfheal/{inc.lower()}", f"{fix_usado} ({inc})", f"Aplicado por github_self_heal. Ver {inc} en la KB.", archivos))
    return informe


def cerrar_dependabot_obsoletos(gh: GitHub, dry_run: bool) -> list[str]:
    informe = []
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    for pr in gh.req("GET", "/pulls?state=open&per_page=50"):
        m = re.match(r"Bump (\S+) from \S+ to (\S+)", pr["title"])
        if pr["user"]["login"] != "dependabot[bot]" or not m:
            continue
        pin = re.search(rf"(?im)^{re.escape(m.group(1))}==(\S+)", req)
        if pin and tuple(map(int, re.findall(r"\d+", pin.group(1)))) >= tuple(map(int, re.findall(r"\d+", m.group(2)))):
            informe.append(f"Dependabot #{pr['number']} obsoleto ({m.group(1)} ya en {pin.group(1)}) -> cerrar")
            if not dry_run:
                gh.req("PATCH", f"/pulls/{pr['number']}", {"state": "closed"})
    return informe


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--log-file")
    ap.add_argument("--run-id", type=int)
    args = ap.parse_args()

    catalogo = cargar_catalogo()
    repo, token = os.getenv("GITHUB_REPOSITORY"), os.getenv("GITHUB_TOKEN")
    gh = GitHub(repo, token) if repo and token else None
    informe: list[str] = []

    log = ""
    if args.log_file:
        log = Path(args.log_file).read_text(encoding="utf-8", errors="replace")
    elif gh and args.run_id:
        log = log_del_run(gh, args.run_id)
    if log:
        informe += resolver(log, catalogo, args.dry_run, gh)
    if gh:
        informe += cerrar_dependabot_obsoletos(gh, args.dry_run)
    print("\n".join(informe) or "Sin hallazgos: repositorio sano.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
