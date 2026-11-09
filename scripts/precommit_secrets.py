#!/usr/bin/env python3
"""Bloquea el auto-commit si lo staged contiene secretos. Exit 1 = bloquear.

Solo mira líneas AÑADIDAS y nombres de archivo; nunca imprime el valor encontrado.
"""
import re
import subprocess
import sys

NOMBRES = re.compile(r"(^|/)(\.env|.*cookies.*\.json|.*credentials.*\.json|id_rsa|.*\.pem|.*\.p12)$", re.I)
NOMBRES_OK = re.compile(r"\.env\.example$|\.example$", re.I)
PLACEHOLDER = re.compile(r"(X{6,}|SECRET|EXAMPLE|PLACEHOLDER|FAKE|DUMMY|TU_CLAVE|TU_API|AQUI|CHANGEME|TEST)", re.I)
PATRONES = {
    "clave privada": re.compile("-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE" + " KEY-----"),
    "clave OpenRouter": re.compile(r"sk-or-v1-[A-Za-z0-9]{20,}"),
    "JWT": re.compile(r"eyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]{15,}"),
    "token GitHub": re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    "AWS": re.compile(r"AKIA[0-9A-Z]{16}"),
}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def main() -> int:
    hallazgos = []
    for ruta in git("diff", "--cached", "--name-only", "--diff-filter=AM").splitlines():
        if NOMBRES.search(ruta) and not NOMBRES_OK.search(ruta):
            hallazgos.append(f"archivo sensible: {ruta}")
    archivo = ""
    for linea in git("diff", "--cached", "-U0", "--no-color").splitlines():
        if linea.startswith("+++ b/"):
            archivo = linea[6:]
        elif linea.startswith("+") and not linea.startswith("+++"):
            for nombre, patron in PATRONES.items():
                m = patron.search(linea)
                if m and not PLACEHOLDER.search(m.group(0)):
                    hallazgos.append(f"{nombre} en {archivo}")
    for h in dict.fromkeys(hallazgos):
        print(f"BLOQUEADO: {h}", file=sys.stderr)
    return 1 if hallazgos else 0


if __name__ == "__main__":
    sys.exit(main())
