"""
mantenimiento — tareas de cuidado de la herramienta que se ejecutan solas cada semana.

  · integridad de la base de datos (PRAGMA integrity_check)
  · optimización (checkpoint, PRAGMA optimize y VACUUM solo si hay mucho espacio muerto)
  · limpieza de temporales (subtítulos sueltos, copias antiguas de importación)
  · verificación de los canales de YouTube (los que nunca se comprobaron o fallaron)

Cada paso es independiente: si uno falla se registra y los demás siguen. El resultado queda en
`data/mantenimiento.json` y el centro de alertas lo lee (integridad rota = alerta crítica).
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.services import channel_store

_LOCK = threading.Lock()
PAUSA_ENTRE_CANALES = 2.0       # s: 29 comprobaciones seguidas despertarían el límite de YouTube
MAX_CANALES_POR_PASADA = 40
DIAS_TEMPORALES = 2
UMBRAL_ESPACIO_MUERTO = 0.20    # VACUUM solo si más del 20 % de las páginas están libres


def ruta_estado(config_path: str) -> Path:
    return Path(config_path).with_name("mantenimiento.json")


def ultimo(config_path: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(ruta_estado(config_path).read_text(encoding="utf-8"))
    except Exception:
        return None


# ── pasos ────────────────────────────────────────────────────────────────────

def verificar_integridad(db_path: str) -> Dict[str, Any]:
    with closing(sqlite3.connect(db_path, timeout=30)) as conn:
        filas = [r[0] for r in conn.execute("PRAGMA integrity_check")]
    ok = filas == ["ok"]
    return {"ok": ok, "detalle": "ok" if ok else "; ".join(filas[:5])}


def optimizar_db(db_path: str) -> Dict[str, Any]:
    antes = Path(db_path).stat().st_size
    vacuum = False
    with closing(sqlite3.connect(db_path, timeout=30)) as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        paginas = conn.execute("PRAGMA page_count").fetchone()[0] or 1
        libres = conn.execute("PRAGMA freelist_count").fetchone()[0]
        if libres / paginas > UMBRAL_ESPACIO_MUERTO:
            conn.execute("VACUUM")
            vacuum = True
        conn.execute("PRAGMA optimize")
    despues = Path(db_path).stat().st_size
    return {"vacuum": vacuum, "antes_kb": round(antes / 1024), "despues_kb": round(despues / 1024),
            "espacio_muerto_pct": round(100 * libres / paginas, 1)}


def limpiar_temporales(data_dir: str, dias: int = DIAS_TEMPORALES) -> Dict[str, Any]:
    limite = time.time() - dias * 86400
    borrados, liberado = 0, 0
    carpeta = Path(data_dir) / "temp_transcripts"
    if carpeta.is_dir():
        for f in carpeta.iterdir():
            try:
                if f.is_file() and f.stat().st_mtime < limite:
                    liberado += f.stat().st_size
                    f.unlink()
                    borrados += 1
            except OSError:
                continue
    return {"borrados": borrados, "liberado_kb": round(liberado / 1024)}


def verificar_canales(config_path: str, db_path: str, solo_pendientes: bool = True,
                      pausa: float = PAUSA_ENTRE_CANALES,
                      detener: Optional[Callable[[], bool]] = None) -> Dict[str, Any]:
    """Comprueba que cada canal activo existe. Por defecto solo los nunca verificados o fallidos."""
    canales = [c for c in channel_store.listar(config_path, db_path) if c["activo"]]
    if solo_pendientes:
        canales = [c for c in canales if c["ultimo_estado"] != "ok"]
    resultado = {"ok": 0, "sin_videos": 0, "no_encontrado": 0, "indeterminado": 0, "revisados": 0}
    for c in canales[:MAX_CANALES_POR_PASADA]:
        if detener and detener():
            break
        try:
            estado = channel_store.verificar(db_path, c["url"])["estado"]
        except Exception:
            estado = "indeterminado"
        resultado[estado] = resultado.get(estado, 0) + 1
        resultado["revisados"] += 1
        if estado == "indeterminado":      # YouTube limita: no insistir ahora
            break
        time.sleep(pausa)
    return resultado


# ── orquestación ─────────────────────────────────────────────────────────────

def ejecutar(db_path: str, config_path: str, canales: bool = True,
             pausa: float = PAUSA_ENTRE_CANALES) -> Dict[str, Any]:
    """Pasada completa. Segura de lanzar a mano o desde el planificador (no se solapa)."""
    if not _LOCK.acquire(blocking=False):
        return {"omitido": "ya hay un mantenimiento en curso"}
    try:
        inicio = time.time()
        res: Dict[str, Any] = {"fecha": datetime.now().isoformat(timespec="seconds"), "errores": []}
        pasos: List[tuple] = [
            ("integridad", lambda: verificar_integridad(db_path)),
            ("optimizacion", lambda: optimizar_db(db_path)),
            ("temporales", lambda: limpiar_temporales(str(Path(db_path).resolve().parent))),
        ]
        if canales:
            pasos.append(("canales", lambda: verificar_canales(config_path, db_path, pausa=pausa)))
        for nombre, paso in pasos:
            try:
                res[nombre] = paso()
            except Exception as exc:
                res[nombre] = None
                res["errores"].append(f"{nombre}: {str(exc)[:160]}")
        res["integridad_ok"] = bool((res.get("integridad") or {}).get("ok"))
        res["duracion_s"] = round(time.time() - inicio, 1)
        destino = ruta_estado(config_path)
        tmp = destino.with_suffix(".tmp")
        tmp.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, destino)
        return res
    finally:
        _LOCK.release()


def main(argv: Optional[List[str]] = None) -> int:
    """python -m app.services.mantenimiento [--sin-canales]"""
    import sys
    from app.config.path_manager import PathManager
    rutas = PathManager.get_paths()
    r = ejecutar(str(rutas["db"]), str(rutas["config"]), canales="--sin-canales" not in (argv or sys.argv[1:]))
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0 if r.get("integridad_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
