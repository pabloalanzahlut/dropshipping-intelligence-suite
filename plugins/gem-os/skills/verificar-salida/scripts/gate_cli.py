#!/usr/bin/env python3
"""CLI del gate determinista para sesiones sin acceso al repositorio (Cowork).

No contiene reglas de negocio: lee la entrada y llama a deterministic_gate.py, que
se copia byte a byte desde app/services/ al generar el plugin (scripts/build_cowork.py).

Uso:
  python gate_cli.py financiera '<json>'
  python gate_cli.py financiera --archivo validacion.json
  python gate_cli.py copy '<texto>' [--specs specs.json]
  python gate_cli.py copy --archivo ficha.md [--specs specs.json]
  python gate_cli.py hooks --archivo hook_matrix.json
  python gate_cli.py refutacion '<json>'
  python gate_cli.py fake-door '<json>'

Salida: JSON por stdout. Código de salida: 0 pasa · 1 no pasa · 2 entrada incompleta.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deterministic_gate as gate  # noqa: E402

# El gate trata un envío ausente como 0; aquí eso sería asumir un dato.
CAMPOS_FINANCIERA = ("costo_origen", "costo_envio", "pvp_calculado", "multiplicador", "costo_landed")
CAMPOS_FAKE_DOOR = ("ctr", "mediana_global", "visitas")


class EntradaIncompleta(Exception):
    pass


def _texto(args) -> str:
    if args.archivo:
        return Path(args.archivo).read_text(encoding="utf-8")
    if args.entrada in (None, "-"):
        return sys.stdin.read()
    return args.entrada


def _json(args) -> dict:
    try:
        datos = json.loads(_texto(args))
    except json.JSONDecodeError as e:
        raise EntradaIncompleta(f"La entrada no es JSON válido: {e}")
    if not isinstance(datos, dict):
        raise EntradaIncompleta("La entrada debe ser un objeto JSON")
    return datos


def _exigir(datos: dict, campos) -> None:
    faltan = [c for c in campos if datos.get(c) is None]
    if faltan:
        raise EntradaIncompleta(
            f"DATA_GAP_REQUEST: faltan {faltan}. Pídeselos al usuario; no se asume ningún valor."
        )


def _a_dict(resultado) -> dict:
    if isinstance(resultado, dict):
        return resultado
    return {
        "passed": resultado.passed,
        "checks": [str(resultado)],
        "violations": resultado.violations,
        "detail": {resultado.check_name: resultado.evidence},
    }


def ejecutar(args) -> dict:
    if args.verificacion == "financiera":
        datos = _json(args)
        _exigir(datos, CAMPOS_FINANCIERA)
        return gate.verificar_validacion_financiera(datos)
    if args.verificacion == "copy":
        specs = json.loads(Path(args.specs).read_text(encoding="utf-8")) if args.specs else None
        return gate.verificar_copy(_texto(args), specs)
    if args.verificacion == "hooks":
        return gate.verificar_hook_matrix(_json(args))
    if args.verificacion == "refutacion":
        return _a_dict(gate.check_refutacion_tally(_json(args)))
    datos = _json(args)
    _exigir(datos, CAMPOS_FAKE_DOOR)
    return _a_dict(gate.check_fake_door_ctr(
        ctr=float(datos["ctr"]),
        mediana_global=float(datos["mediana_global"]),
        visitas=int(datos["visitas"]),
        concentracion=float(datos.get("concentracion", 0.0)),
    ))


def main(argv=None) -> int:
    for flujo in (sys.stdout, sys.stderr):  # el gate avisa por logging → stderr
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Gate determinista de GEM OS")
    parser.add_argument("verificacion", choices=["financiera", "copy", "hooks", "refutacion", "fake-door"])
    parser.add_argument("entrada", nargs="?", help="JSON o texto; '-' o vacío para leer de stdin")
    parser.add_argument("--archivo", help="Ruta de un archivo con la entrada")
    parser.add_argument("--specs", help="JSON con los datos del proveedor (solo 'copy')")
    args = parser.parse_args(argv)

    try:
        resultado = ejecutar(args)
    except (EntradaIncompleta, OSError) as e:
        print(json.dumps({"passed": False, "error": str(e)}, ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if resultado.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
