"""
log_viewer — lectura de los registros del servidor para la pantalla «Registros».

Fuentes:
  servidor : logs/elite/servidor.log   (lo que escribe el propio servidor web: avisos, errores, tareas)
  elite    : logs/elite/elite_suite.jsonl (log estructurado del resto de la suite)
Se lee solo el final de cada archivo (no se carga entero en memoria).
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

NIVELES = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
_FORMATO_SERVIDOR = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_RE_SERVIDOR = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| (\w+)\s*\| ([^|]*)\| (.*)$")


def configurar_log_servidor(ruta: Path) -> None:
    """Añade al logger raíz un archivo rotativo (1 MB × 3). Idempotente."""
    raiz = logging.getLogger()
    ruta = Path(ruta)
    for h in raiz.handlers:
        if isinstance(h, logging.handlers.RotatingFileHandler) and Path(h.baseFilename) == ruta.resolve():
            return
    ruta.parent.mkdir(parents=True, exist_ok=True)
    h = logging.handlers.RotatingFileHandler(ruta, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    h.setFormatter(logging.Formatter(_FORMATO_SERVIDOR, "%Y-%m-%d %H:%M:%S"))
    h.setLevel(logging.INFO)
    raiz.addHandler(h)
    if raiz.level in (logging.NOTSET, logging.WARNING):
        raiz.setLevel(logging.INFO)


def leer_cola(ruta: Path, max_lineas: int = 2000, max_bytes: int = 1_500_000) -> List[str]:
    """Últimas líneas de un archivo de texto (lee como mucho max_bytes desde el final)."""
    try:
        with open(ruta, "rb") as f:
            f.seek(0, 2)
            tam = f.tell()
            f.seek(max(0, tam - max_bytes))
            datos = f.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    lineas = datos.splitlines()
    if tam > max_bytes and lineas:
        lineas = lineas[1:]          # la primera puede estar cortada
    return lineas[-max_lineas:]


def _parsear_servidor(linea: str) -> Optional[Dict[str, Any]]:
    m = _RE_SERVIDOR.match(linea)
    if not m:
        return None
    return {"ts": m.group(1), "nivel": m.group(2).upper(), "origen": m.group(3).strip(), "msg": m.group(4)}


def _parsear_elite(linea: str) -> Optional[Dict[str, Any]]:
    try:
        d = json.loads(linea)
    except ValueError:
        return None
    return {"ts": str(d.get("timestamp", ""))[:19].replace("T", " "), "nivel": str(d.get("level", "INFO")).upper(),
            "origen": d.get("module", ""), "msg": d.get("message", "")}


def consultar(fuente: str, ruta: Path, nivel: str = "", texto: str = "", limite: int = 200) -> List[Dict[str, Any]]:
    """Registros más recientes primero, filtrados por nivel mínimo y texto."""
    parse = _parsear_elite if fuente == "elite" else _parsear_servidor
    minimo = NIVELES.get((nivel or "").upper(), 0)
    q = (texto or "").strip().lower()
    salida: List[Dict[str, Any]] = []
    for linea in reversed(leer_cola(ruta)):
        e = parse(linea)
        if not e:
            continue
        if NIVELES.get(e["nivel"], 20) < minimo:
            continue
        if q and q not in (e["msg"] + " " + e["origen"]).lower():
            continue
        salida.append(e)
        if len(salida) >= limite:
            break
    return salida
