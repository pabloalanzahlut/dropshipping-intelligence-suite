---
name: consolidar-manual
description: "Toda la KB → manual operativo paso a paso con fuentes y timestamps. Usar cuando el usuario hable de: consolidar manual, manual operativo, todo en un manual."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/consolidar-manual.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

# Skill: Consolidar la KB en un Manual Operativo

Convierte toda la Knowledge Base en **un manual paso a paso**, no en una lista
de datos sueltos.

Fuente: `1tzz17YDtz8` 13:18 — Aditya Umale metió 83 episodios de podcast (40
horas, mezcla de hindi e inglés, más de 100 historias distintas) y sacó un
manual paso a paso de lo que funcionó. El material ya estaba ahí; lo que faltaba
era consolidarlo.

---

## El hueco que cubre

GEM OS ingiere transcripciones de mentores y extrae entidades a la KB:
productos, fórmulas de conversión, tácticas de tráfico. Lo que no hace es el
último paso — convertir ese conocimiento disperso en un procedimiento que se
pueda seguir.

La diferencia es la de tener 100 notas sobre hooks de TikTok, frente a tener
la secuencia de qué hook usar según la categoría del producto.

---

## Qué necesito

- **Tema del manual** (ej. "lanzamiento de producto", "escalado de campañas",
  "estructura de ficha de Shopify")
- Opcional: fuentes a priorizar. Por defecto manda la jerarquía del proyecto —
  Adrián Sáenz como primaria, el resto complementarios.

---

## Proceso

### 1. Reunir el material
Barrer la KB buscando todo lo relacionado con el tema:

```
contexto/kb/     — KB consolidada
contexto/manual/            — manual táctico
contexto/proyecto_activo/*/         — transcripciones crudas
app/database/dropshipping_suite.db — entidades extraídas
```

### 2. Agrupar por paso del proceso, no por fuente
El error sería ordenar por mentor. El manual se organiza por **el orden en que
se ejecutan las cosas**, cruzando lo que dice cada uno en cada paso.

### 3. Resolver contradicciones con la jerarquía
Cuando dos fuentes se contradicen:
- Adrián Sáenz **prevalece siempre** (fuente primaria)
- Entre complementarios, gana el que aporte un número concreto con contexto
- Si la contradicción no se resuelve, **se deja anotada en el manual** en vez de
  elegir en silencio

### 4. Marcar lo que no está respaldado
Cada afirmación del manual lleva su fuente y timestamp. Lo que no tenga respaldo
en la KB se marca como `[SIN FUENTE]` — no se rellena con conocimiento general.

### 5. Añadir los umbrales reales
Donde el manual diga "valida el margen", poner el número: 2× mínimo sobre coste
landed. El manual es operativo o no sirve.

---

## Output

Un fichero en `contexto/kb/manual_[tema].md`:

```markdown
# Manual: [tema]

## Paso 1 — [acción]
[Qué hacer, con los números concretos]

**Fuente:** Adrián Sáenz `Q4Ykcwh5Osc 24:40`
**Confirmado por:** Iván Caicedo (`video_id`), JaviEcom (`video_id`)

> ⚠️ Marc Verdú propone otro criterio aquí (`video_id 12:30`): [cuál].
> No se aplica porque contradice a la fuente primaria.

## Paso 2 — [acción]
...

---
## Lagunas
- [Qué parte del proceso no tiene respaldo en la KB]
```

---

## Criterio de calidad

El manual sirve si alguien que no ha visto ningún video puede ejecutar el
proceso siguiéndolo. Si un paso dice "analiza el producto" sin decir contra qué
criterios, está incompleto.

---

## Nota sobre aprender vs. delegar

Anthropic probó con 52 programadores aprendiendo una herramienta nueva: los que
delegaron en la IA sacaron 50% en el examen posterior; los que lo hicieron a
mano, 67%. La mayor brecha estaba en **detectar errores**.

Leer el manual no es lo mismo que haberlo ejecutado. El manual acelera, pero no
sustituye haber pasado un producto por el pipeline a mano al menos una vez.
