"""
runtime_setup — prepara el entorno al arrancar (sobre todo cuando corre como .exe).

`iniciar_entorno()` hace, una sola vez y en este orden:
  1. Si no hay consola (--noconsole) `sys.stdout/stderr` son None y uvicorn/print fallarían:
     los redirige a `logs/elite/arranque.log`.
  2. En el .exe crea la carpeta del usuario y siembra lo que el bundle trae de solo lectura:
     `ai_workspace/` (sin credenciales ni cookies), `agent.md` y las plantillas JSON de canales
     y configuración. Solo copia lo que falta: nunca pisa lo del usuario.
  3. En el .exe cambia el directorio de trabajo a la carpeta del usuario, porque muchos módulos
     usan rutas relativas (`ai_workspace/...`, `data/...`, `agent.md`).
  4. Carga las claves (`secrets_store.cargar_entorno`).
En desarrollo solo hace el paso 1 (si aplica) y el 4: el comportamiento no cambia.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List

from app.config import secrets_store
from app.config.path_manager import PathManager

# Nunca se siembran en la carpeta del usuario aunque estén en el bundle
_EXCLUIR = ("google_credentials.json", "skool_cookies.json", ".env")


def _redirigir_salida_sin_consola() -> None:
    if sys.stdout is not None and sys.stderr is not None:
        return
    try:
        logs = PathManager.get_paths()["logs"]
        logs.mkdir(parents=True, exist_ok=True)
        flujo = open(logs / "arranque.log", "a", encoding="utf-8", buffering=1)
    except OSError:
        flujo = open(os.devnull, "w")
    if sys.stdout is None:
        sys.stdout = flujo
    if sys.stderr is None:
        sys.stderr = flujo


def _copiar_arbol_sin_secretos(origen: Path, destino: Path) -> int:
    """Copia lo que falta de `origen` en `destino`, saltando secretos. Devuelve cuántos archivos copió."""
    copiados = 0
    for ruta in origen.rglob("*"):
        if ruta.is_dir() or ruta.name in _EXCLUIR or "cookies" in ruta.name.lower() or ruta.suffix == ".zip":
            continue
        rel = ruta.relative_to(origen)
        objetivo = destino / rel
        if objetivo.exists():
            continue
        objetivo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ruta, objetivo)
        copiados += 1
    return copiados


def sembrar_datos_iniciales() -> Dict[str, int]:
    """Primer arranque del .exe: deja lista la carpeta del usuario. Idempotente."""
    recursos = PathManager._get_base_dir()
    usuario = PathManager.user_dir()
    usuario.mkdir(parents=True, exist_ok=True)
    resultado = {"ai_workspace": 0, "agent_md": 0, "plantillas": 0}
    if (recursos / "ai_workspace").is_dir():
        resultado["ai_workspace"] = _copiar_arbol_sin_secretos(recursos / "ai_workspace", usuario / "ai_workspace")
    agent = recursos / "agent.md"
    if agent.is_file() and not (usuario / "agent.md").exists():
        shutil.copy2(agent, usuario / "agent.md")
        resultado["agent_md"] = 1
    plantillas = recursos / "data_template"
    if plantillas.is_dir():
        datos = PathManager._get_data_dir()
        datos.mkdir(parents=True, exist_ok=True)
        for f in plantillas.glob("*.json"):
            if not (datos / f.name).exists():
                shutil.copy2(f, datos / f.name)
                resultado["plantillas"] += 1
    return resultado


_JSON_DE_DATOS = ("youtube_channels.json", "config.json", "queue_state.json", "last_sync.json",
                  "videos_descartados.json")


def importar_datos(origen: Path) -> Dict[str, object]:
    """Trae tus datos de otra carpeta `data/` (p. ej. la del proyecto) a la carpeta de datos actual.

    · La base de datos se copia con la API de backup de SQLite (segura aunque esté en uso) y se
      comprueba su integridad ANTES de tocar nada.
    · Si ya había una base de datos con contenido, antes se guarda una copia en `backups/`.
    · Los JSON de configuración se copian dejando un `.bak` del que había.
    Devuelve un resumen. Lanza ValueError / FileNotFoundError con un mensaje legible."""
    import sqlite3
    from contextlib import closing

    origen = Path(origen)
    bd_origen = origen / "dropshipping_suite.db"
    if not bd_origen.is_file():
        raise FileNotFoundError("No encuentro «dropshipping_suite.db» en esa carpeta.")
    rutas = PathManager.get_paths()
    destino = rutas["db"]
    if destino.exists() and destino.resolve() == bd_origen.resolve():
        raise ValueError("Esa ya es la carpeta de datos que estás usando.")
    uri = f"file:{bd_origen.resolve().as_posix()}?mode=ro"
    try:
        with closing(sqlite3.connect(uri, uri=True)) as c:
            if c.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("La base de datos de origen no pasa la comprobación de integridad.")
    except sqlite3.DatabaseError as exc:
        raise ValueError(f"El archivo no es una base de datos válida: {exc}") from exc

    respaldo = None
    if destino.exists() and destino.stat().st_size > 0:
        from app.services import kb_maintenance
        respaldo = kb_maintenance.backup_db(str(destino), "antes_de_importar")
    destino.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(uri, uri=True)) as src, closing(sqlite3.connect(str(destino))) as dst:
        src.backup(dst)
    try:                                   # aplica las migraciones que falten a una BD más antigua
        from app.database.connection import DatabaseConnection
        DatabaseConnection(str(destino))
    except Exception:
        pass

    copiados: List[str] = []
    for nombre in _JSON_DE_DATOS:
        s = origen / nombre
        if not s.is_file():
            continue
        d = rutas["data"] / nombre
        if d.exists():
            shutil.copy2(d, d.with_suffix(d.suffix + ".bak"))
        shutil.copy2(s, d)
        copiados.append(nombre)
    return {"bd": str(destino), "respaldo": respaldo, "json": copiados}


def iniciar_entorno() -> Dict[str, object]:
    """Ver la descripción del módulo. Devuelve un resumen (útil para registros y pruebas)."""
    _redirigir_salida_sin_consola()
    info: Dict[str, object] = {"exe": PathManager._is_executable(), "sembrado": {}, "env": []}
    if PathManager._is_executable():
        info["sembrado"] = sembrar_datos_iniciales()
        os.chdir(PathManager.user_dir())
    info["env"] = [str(p) for p in secrets_store.cargar_entorno()]
    return info
