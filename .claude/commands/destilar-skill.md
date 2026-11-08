# Skill: Destilar una Skill desde Ejecuciones Reales

Reescribe una skill a partir de lo que **realmente pasó**, no de lo que creíamos
que iba a pasar.

Fuente: `Ra3GIwwT4Yc` — Adrián no escribe sus skills a priori. Ejecuta el proceso
a mano varias veces y luego pide: *"documenta todo el proceso que acabamos de
hacer y conviértelo en una skill"*. Claude escribe la skill desde su propia
experiencia de ejecución, y captura las decisiones tácitas que nadie documentaría.

---

## El problema que resuelve

Las skills de `.claude/commands/` se escribieron antes de usarlas. Codifican una
hipótesis de cómo debería funcionar el proceso. Después de 10 productos reales
pasando por el pipeline, el procedimiento real difiere del escrito — y esa
diferencia es justo donde está el conocimiento.

---

## Qué necesito

1. **Qué skill destilar** (ej. `clasificar-producto`)
2. **Entre 3 y 5 ejecuciones reales** de esa skill, preferiblemente con resultado
   conocido: productos que vendieron y productos que no
3. Para cada una: input, output, y qué pasó después

Si no hay al menos 3 ejecuciones con resultado → `DATA_GAP_REQUEST`. Destilar
desde una sola ejecución produce una skill sobreajustada a ese caso.

---

## Proceso

### 1. Reconstruir qué se hizo realmente
Para cada ejecución, recorrer el histórico y anotar:
- Qué datos se usaron de verdad (no los que la skill pedía)
- Qué decisiones se tomaron fuera del procedimiento escrito
- Dónde el operador corrigió a mano la salida
- Qué pasos de la skill se saltaron por inútiles

### 2. Separar las ganadoras de las perdedoras
Comparar las ejecuciones que acabaron en venta con las que no. Las diferencias
en el procedimiento son la señal.

```python
from app.services.metrics_aggregator import MetricsAggregator
vista = MetricsAggregator().construir_vista(dias=60)
ganadoras = [f for f in vista if f.acierto is True]
perdedoras = [f for f in vista if f.acierto is False]
```

### 3. Extraer el procedimiento real
Escribir los pasos que se siguieron de verdad, en el orden en que ocurrieron,
con los criterios que se aplicaron de verdad — incluidos los que nadie había
escrito.

### 4. Marcar las diferencias
Antes de reemplazar nada, listar en qué se aparta lo destilado de lo escrito.
Cada diferencia es una decisión: o la skill estaba mal, o la ejecución se desvió.

---

## Output

```
DESTILACIÓN — skill: [nombre]

Ejecuciones analizadas: N (X con venta, Y sin venta)

DIFERENCIAS CON LA SKILL ESCRITA
  Paso          Escrito                  Real                    Veredicto
  [paso]        [lo que dice la skill]   [lo que se hizo]        corregir skill
  [paso]        [...]                    [se saltó siempre]      eliminar paso
  —             [no existía]             [se hacía siempre]      añadir paso

CRITERIOS TÁCITOS DETECTADOS
  - [criterio que nadie escribió pero se aplicó en las 5 ejecuciones]

PATRÓN DE LAS GANADORAS
  - [qué tenían en común las que vendieron]

--- SKILL DESTILADA ---
[procedimiento reescrito, listo para reemplazar el archivo]
```

---

## Regla

**La skill destilada no se aplica sola.** Se presenta junto a las diferencias y
la decide una persona. Una ejecución desviada puede ser una mejora o puede ser
un error que se repitió cinco veces.

Esto no aplica a las reglas financieras ni al gate determinista: ningún proceso
de destilación los toca, igual que el loop de auto-mejora.
