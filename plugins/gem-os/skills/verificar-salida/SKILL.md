---
name: verificar-salida
description: "Gate determinista de GEM OS. Usar SIEMPRE antes de entregar un número financiero (multiplicador, coste landed, margen, validación de producto), copy comercial (ficha, landing, anuncio, guion, hooks), una matriz de hooks, un veredicto de refutación o un resultado de fake door. Recalcula con Python puro, sin LLM: un modelo no audita a otro."
---

# Verificar salida (gate determinista)

Un LLM no puede auditar a otro LLM: acepta explicaciones convincentes. Por eso los números y
el copy de GEM OS se comprueban con `scripts/deterministic_gate.py`, que es una copia exacta
del gate del repositorio. **No se edita, no se parchea y no se sustituye por un cálculo propio.**

## Cómo ejecutarlo

Desde la carpeta de esta skill:

```bash
python scripts/gate_cli.py <verificación> '<json>'
python scripts/gate_cli.py <verificación> --archivo ruta/al/archivo
```

| Verificación | Entrada | Comprueba |
|---|---|---|
| `financiera` | JSON con `costo_origen`, `costo_envio`, `pvp_calculado`, `multiplicador`, `costo_landed` (opcional `detalles.fx_rate`) | Recalcula el multiplicador desde los costes crudos y lo compara con el declarado |
| `copy` | Texto, o `--archivo` con el texto; opcional `--specs specs.json` con los datos del proveedor | Superlativos prohibidos, promesas de envío irreales, UTF-8 roto, specs del proveedor sin alterar |
| `hooks` | JSON con `hook_matrix: [{id, formula, texto}]` | ≥12 hooks, ≥2 por fórmula, y el copy de cada hook |
| `refutacion` | JSON `{"1": {"resultado": "pasa"}, …, "8": {…}}` | Veredicto de las 8 refutaciones (1 y 6 son eliminatorias) |
| `fake-door` | JSON con `ctr`, `mediana_global`, `visitas` (opcional `concentracion`) | Producir / repetir / descartar |

Salida: JSON con `passed`, `violations` y `detail`. Código de salida `0` pasa, `1` no pasa,
`2` entrada incompleta.

Ejemplo — $5 de producto + $2 de envío vendido a $15 y declarado como 3,0x:

```bash
python scripts/gate_cli.py financiera '{"costo_origen": 5, "costo_envio": 2, "pvp_calculado": 15, "multiplicador": 3.0, "costo_landed": 7}'
```

No pasa: el multiplicador real es 2,14x.

## Cómo usar el resultado

- `passed: false` → **no se entrega como válido.** Se corrige la salida (nunca el gate) y se vuelve a pasar.
- El multiplicador que se comunica es `detail.aritmetica_financiera.multiplicador_real`, no el que se había declarado. Los umbrales (mínimo 2x, objetivo 3x, HOT/WARM/COLD) son los de `reglas-gem-os`.
- `financiera` exige `costo_envio`. Si no se conoce, es un `DATA_GAP_REQUEST`: se pregunta al usuario; no se pone `0` para que pase.
- En la entrega se indica qué verificación se ejecutó y su resultado.

## Si no se puede ejecutar Python

No se da por verificado. Se muestra el cálculo paso a paso desde los costes crudos y se
marca la salida con **«NO VERIFICADO POR GATE»**. El usuario la pasará por el gate del
repositorio antes de usarla.

Este gate es la primera barrera. Cuando un resultado vuelve al pipeline de GEM OS, el que
decide es el gate del repositorio.
