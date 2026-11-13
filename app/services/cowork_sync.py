"""
Refresca `cowork/contexto/`, el espejo de solo lectura que ve Cowork.

Cowork corre en la nube y solo alcanza la carpeta `cowork/`. La KB crece sola (ingesta y
transcripciones automáticas) sin pasar por Claude Code, así que el espejo se regenera
también desde el planificador. La lógica vive en `scripts/build_cowork.py`; aquí solo se
lanza. Es unidireccional: nada de `cowork/` vuelve al sistema por esta vía.
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict

log = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "scripts" / "build_cowork.py"


def sincronizar(timeout: int = 120) -> Dict:
    """Ejecuta `build_cowork.py contexto`. Nunca lanza: devuelve {'ok', 'motivo'}."""
    if getattr(sys, "frozen", False) or not SCRIPT.is_file():
        # El ejecutable portable no lleva scripts/ ni la carpeta cowork/
        return {"ok": False, "motivo": "scripts/build_cowork.py no disponible en esta instalación"}
    try:
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "contexto", "--quiet"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, cwd=str(RAIZ),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "motivo": str(exc)}
    return {"ok": r.returncode == 0, "motivo": (r.stderr or "").strip()[:300]}
