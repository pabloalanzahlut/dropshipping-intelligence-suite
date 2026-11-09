"""
secrets_store — dónde viven las claves (OPENROUTER_API_KEY, webhooks…) y cómo se leen y guardan.

Regla: las claves NUNCA van dentro del .exe ni del repositorio.
  · .exe  → `%APPDATA%\\GEM_OS_Suite\\.env` (carpeta del usuario). También se lee un `.env`
            junto al .exe si existe.
  · desarrollo → el `.env` de la raíz del proyecto (ignorado por git).

Orden de lectura (la primera definición gana; las variables ya presentes en el entorno del
sistema nunca se pisan):  .env junto al .exe  →  .env del usuario  →  .env del proyecto.

Nada de este módulo escribe valores en logs ni los devuelve a la web: `estado_claves()` solo dice
si una variable está definida y `enmascarar()` enseña los 4 últimos caracteres.
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from dotenv import dotenv_values

from app.config.path_manager import PathManager

_NOMBRE_VALIDO = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")


def _es_exe() -> bool:
    return PathManager._is_executable()


def ruta_env_escritura() -> Path:
    """Dónde se guardan las claves nuevas: la carpeta del usuario (.exe) o el .env del proyecto."""
    if _es_exe():
        return PathManager.user_dir() / ".env"
    return PathManager._get_base_dir() / ".env"


def rutas_env() -> List[Path]:
    """Archivos .env candidatos, por orden de prioridad (solo los que existen se leen)."""
    candidatos: List[Path] = []
    if _es_exe():
        candidatos.append(Path(sys.executable).resolve().parent / ".env")
        candidatos.append(PathManager.user_dir() / ".env")
    else:
        candidatos.append(PathManager._get_base_dir() / ".env")
    vistos, unicos = set(), []
    for c in candidatos:
        if c not in vistos:
            vistos.add(c)
            unicos.append(c)
    return unicos


def cargar_entorno() -> List[Path]:
    """Carga los .env a os.environ sin pisar lo que ya esté definido. Devuelve los leídos."""
    leidos: List[Path] = []
    for ruta in rutas_env():
        try:
            if not ruta.is_file():
                continue
            for nombre, valor in dotenv_values(ruta).items():
                if valor is not None and nombre not in os.environ:
                    os.environ[nombre] = valor
            leidos.append(ruta)
        except OSError:
            continue
    return leidos


def estado_claves(nombres: Iterable[str]) -> Dict[str, bool]:
    """Qué variables están definidas (con valor). Nunca devuelve los valores."""
    return {n: bool((os.environ.get(n) or "").strip()) for n in nombres}


def enmascarar(valor: Optional[str]) -> str:
    """«sk-or-v1-…a1b2»: suficiente para reconocerla, no para usarla."""
    v = (valor or "").strip()
    if not v:
        return ""
    return "…" + v[-4:] if len(v) > 8 else "••••"


def _formatear(valor: str) -> str:
    if re.search(r"[\s#'\"\\$]", valor):
        return '"' + valor.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return valor


def guardar_valores(valores: Dict[str, str], ruta: Optional[Path] = None) -> Path:
    """Crea o actualiza `NOMBRE=valor` en el .env de escritura, conservando el resto del archivo.

    Escritura atómica (archivo temporal + reemplazo). También lo aplica al entorno actual para que
    surta efecto sin reiniciar. Un valor vacío elimina la variable."""
    destino = ruta or ruta_env_escritura()
    limpios: Dict[str, str] = {}
    for nombre, valor in valores.items():
        if not _NOMBRE_VALIDO.match(nombre or ""):
            raise ValueError(f"Nombre de variable no válido: {nombre!r}")
        v = "" if valor is None else str(valor).strip()
        if any(c in v for c in ("\n", "\r", "\x00")):
            raise ValueError(f"El valor de {nombre} no puede tener saltos de línea.")
        limpios[nombre] = v

    lineas: List[str] = []
    if destino.is_file():
        lineas = destino.read_text(encoding="utf-8").splitlines()
    pendientes = dict(limpios)
    salida: List[str] = []
    for linea in lineas:
        m = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", linea)
        if m and m.group(1) in pendientes:
            nombre = m.group(1)
            valor = pendientes.pop(nombre)
            if valor:
                salida.append(f"{nombre}={_formatear(valor)}")
            continue
        salida.append(linea)
    for nombre, valor in pendientes.items():
        if valor:
            salida.append(f"{nombre}={_formatear(valor)}")

    destino.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(destino.parent), prefix=".env.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(salida) + ("\n" if salida else ""))
        os.replace(tmp, destino)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    for nombre, valor in limpios.items():
        if valor:
            os.environ[nombre] = valor
        else:
            os.environ.pop(nombre, None)
    return destino
