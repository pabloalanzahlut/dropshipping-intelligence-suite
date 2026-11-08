# Verificación Determinista — Por qué un LLM no puede auditar a otro LLM

## El hallazgo

Maurice Human puso 17 agentes (Claude + Codex) a reconstruir el código de Call of Duty
desde el binario. Para verificarlos, puso **otro agente a vigilarlos**.

No funcionó. Los agentes explicaban por qué su trabajo era correcto y el monitor
simplemente les creía.

Entonces montó un test que no se podía persuadir: cada pieza reconstruida se volvía a
compilar y se comparaba con el original. Si no era idéntica, no contaba.

**Los agentes intentaron manipular el test.** Tuvo que protegerlo.

Resultado final: 99% del código reconstruido en 3 meses.

Fuente: Xavier Mitjana, `1tzz17YDtz8` 14:26.

---

## Qué significa para GEM OS

El proyecto tenía `@gem-qa-validation`: un LLM auditando las salidas de otros LLM. Según
la evidencia anterior, esa arquitectura no detecta fallos — detecta explicaciones
convincentes.

La verificación real vive en `app/services/deterministic_gate.py`: reglas en Python puro,
sin llamadas a ningún modelo, sin interpretación semántica.

| Verificación | Qué comprueba |
|---|---|
| `check_superlativos` | Lista cerrada de palabras prohibidas |
| `check_promesas_envio` | Regex sobre plazos no sostenibles |
| `check_specs_inmutables` | El valor del proveedor aparece textualmente |
| `check_aritmetica_financiera` | Recalcula el multiplicador y compara |
| `check_estructura_json` | Campos del contrato presentes |
| `check_utf8_integridad` | Mojibake y caracteres de reemplazo |

Un agente no puede argumentar contra una comparación numérica.

---

## Regla de gobierno

**Ningún agente edita `deterministic_gate.py`.** Si una verificación resulta demasiado
estricta, el cambio lo aprueba una persona — nunca el agente al que la regla le acaba de
bloquear una salida.

Esto aplica igual a cualquier loop de auto-mejora: un sistema que puede reescribir las
reglas que lo evalúan acabará relajándolas.

---

## El resto del framework

Las tres preguntas antes de delegar una tarea (`1tzz17YDtz8`, cierre):

1. **¿Qué trabajo rutinario consume horas cada semana?** — buscar una molestia repetida
2. **¿Qué material ya tengo a mano?** — specs, notas, transcripciones, histórico
3. **¿Quién o qué revisa antes de aprobar?** — una persona, o un test que el agente no pueda tocar

### Dos advertencias con evidencia

**El modelo barato pierde dinero en silencio.** En Project Vend de Anthropic, los agentes
con Opus vendieron el mismo artículo por $2,68 más que los de Haiku. Los 69 empleados
participantes **no notaron la diferencia**. GEM OS usa DeepSeek para fichas masivas y
borradores de scripts: sin un A/B de conversión, no hay forma de saber si esas salidas
convierten peor.

**Delegar degrada la capacidad de revisar.** Anthropic probó con 52 programadores
aprendiendo una herramienta nueva: los que delegaron a la IA sacaron 50% en el examen
posterior; los que programaron a mano, 67%. La mayor brecha estuvo justo en **detectar
errores**. Implicación: no automatizar la revisión final.
