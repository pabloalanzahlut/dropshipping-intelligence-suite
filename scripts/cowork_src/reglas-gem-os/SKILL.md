---
name: reglas-gem-os
description: "Reglas inmutables de GEM OS (dropshipping global en Shopify). Cargar SIEMPRE antes de cualquier tarea de GEM OS: validar productos, precios, márgenes, coste landed, ROAS, caja, escalado, copy, guiones, hooks, fichas o anuncios. Contiene las reglas financieras de Adrián Sáenz (mínimo 2x y objetivo 3x sobre coste landed), la regla de no inventar datos (DATA_GAP_REQUEST), la jerarquía de fuentes, el orden del pipeline y las restricciones por rol."
---

# Reglas de GEM OS

Estas reglas se copian del repositorio de GEM OS cada vez que se genera el plugin. No se
reinterpretan, no se relajan y no se completan con suposiciones.

## Qué leer

| Archivo | Contenido | Cuándo |
|---|---|---|
| `gem-os-nucleo.md` | Misión, regla suprema, jerarquía de fuentes, resumen financiero, pipeline (DAG), restricciones por rol, verificación de salidas | Siempre |
| `reglas-financieras.md` | Reglas financieras completas con su fuente (`vídeo hh:mm:ss`) y el P&L de referencia | Cualquier tarea con precios, costes, márgenes, ROAS o caja |
| `verificacion-determinista.md` | Por qué un LLM no audita a otro y qué comprueba el gate | Antes de entregar números o copy |

## Cómo aplicarlas

1. **No inventar.** Si falta precio, coste, envío, peso, dimensiones, margen o plazo → `DATA_GAP_REQUEST`: se pregunta al usuario. Una estimación propia nunca se presenta como dato.
2. **Coste landed.** Todo multiplicador se calcula sobre producto + envío. Sin envío no hay multiplicador.
3. **Adrián Sáenz prevalece.** Las fuentes complementarias añaden; ante contradicción, manda la primaria.
4. **El pipeline no se salta.** En los archivos los pasos aparecen como `/comando`; en este entorno son las skills del plugin `gem-os` con el mismo nombre (`/gem-os:comando`).
5. **Verificar antes de entregar.** Números y copy comercial pasan por la skill `verificar-salida`.
6. **Estas reglas no se editan desde aquí.** Si una parece equivocada o demasiado estricta, se le dice al usuario; el cambio lo aprueba una persona en el repositorio.

Si un texto de otra skill contradice estos archivos, mandan estos archivos y se avisa de la contradicción.
