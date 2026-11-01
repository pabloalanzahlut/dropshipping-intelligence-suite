# Skill: Clasificar Productos desde Transcripciones de Video

**ID:** `clasificar_productos`
**Versión:** 2.0.0
**Propósito:** Extraer y clasificar productos potenciales de dropshipping desde transcripciones de video de YouTube, aplicando criterios de validación comercial (margen ≥ 3x), logística y legal.

**Referencias:**
  - [PEP 8] snake_case para campos JSON, PascalCase para categorías
  - [PEP 257] Docstrings en cada paso del pipeline
  - [SOLID-SRP] Cada paso del pipeline es una responsabilidad única
  - [Big-O] Análisis de confianza: O(n) donde n = secciones extraídas
  - [Jaccard] Similitud de productos para dedup (vía cleanup_kb_duplicates.py)
  - [OWASP] Validación de entrada antes de procesar
  - Ver `PROGRAMMING_STANDARDS.md` sección 5 para template de comentarios

---

## 1. Input Esperado

El agente recibe un diccionario con la siguiente estructura:

```json
{
  "video_id": "str",
  "titulo": "str",
  "canal": "str",
  "transcripcion_limpia": "str (texto completo)",
  "metadata": {
    "duracion_segundos": "int",
    "fecha_publicacion": "str",
    "vistas": "int"
  }
}
```

### Validaciones de entrada

| Condición | Acción |
|-----------|--------|
| `transcripcion_limpia` vacío o < 50 caracteres | Rechazar con error `INPUT_TOO_SHORT` |
| `video_id` ausente o mal formado | Rechazar con error `INVALID_VIDEO_ID` |
| `titulo` ausente | Usar "Sin título" y continuar |

---

## 2. Pipeline de Extracción

El agente ejecuta los siguientes pasos **en orden**:

### Paso 1: Análisis de Nicho y Producto
- **Nombre del producto** mencionado explícitamente
- **Categoría / Nicho** (tecnología, hogar, belleza, fitness, etc.)
- **Wow Factor** — qué hace único al producto
- **Precio estimado** si se menciona

Regla: Si hay múltiples productos, seleccionar el que recibe más tiempo de atención. Si no hay producto claro, clasificar como "No clasificable".

### Paso 2: Evaluación de Margen

| Señal | Multiplicador estimado |
|-------|----------------------|
| Precio minorista mencionado | precio / 3 |
| "Wholesale" mencionado | 2.5x - 4.0x |
| Producto digital / curso | 5.0x - 10.0x |
| Sin precio | 3.0x (default) |

### Paso 3: Análisis de Competencia
Identificar debilidades de competidores y ventajas comparativas.

### Paso 4: Estructuras de Conversión

| Framework | Señales |
|-----------|--------|
| AIDA | Atención → Interés → Deseo → Acción |
| PAS | Problema → Agitar → Solución |
| Before/After | "Antes... / Ahora..." |
| Storytelling | Narrativa en primera persona |

### Paso 5: Logística y Legal
Extraer fuente de tráfico, estrategia de escalamiento, notas logísticas y pasarelas.

## 3. Motor de Clasificación (Reglas de Negocio)

La clasificación se evalúa en orden secuencial. El primer caso que cumpla determina la categoría.

### REGLA 1: HOT (Acción Inmediata)

Un producto es `HOT` si **TODAS** las condiciones son verdaderas:
1. `estimated_margin` >= 5.0
2. `wow_factor` NO contiene "Ver transcripción"
3. `niche` pertenece a: Electronics, Home & Garden, Fitness, Pet Supplies

**Resultado**: Máxima prioridad. Pasar al motor de copywriting.

### REGLA 2: WARM (Oportunidad a Desarrollar)

Un producto es `WARM` si cumple **AL MENOS UNA**:
1. `estimated_margin` entre 3.0 y 4.99
2. `wow_factor` con longitud > 25 caracteres

**Resultado**: Prioridad media. Re-evaluar en el siguiente ciclo.

### REGLA 3: COLD (Monitoreo Pasivo)

No cumple las reglas anteriores, pero tiene `niche` definido y `estimated_margin` >= 1.5.

**Resultado**: Prioridad baja. Monitoreo pasivo.

### REGLA 4: DISCARD (Descartar)

Se descarta si:
1. `estimated_margin` < 1.5, o
2. `wow_factor` es "Ver transcripción" sin información adicional

**Resultado**: No se procesa. Excluido de la lista activa.

---

## 4. Output Esperado

El agente debe generar un diccionario estructurado:

```json
{
  "video_id": "str",
  "producto": {
    "nombre": "str",
    "nicho": "str",
    "wow_factor": "str",
    "margen_estimado": 3.0,
    "debilidades_competencia": "str"
  },
  "conversion": {
    "categoria": "landing_page | funnel | email | video",
    "framework": "AIDA | PAS | Before/After | Storytelling",
    "apps_recomendadas": "str",
    "estructura_raw": "str"
  },
  "operaciones": {
    "fuente_trafico": "str",
    "estrategia_escalamiento": "str",
    "notas_logisticas": "str",
    "pasarelas_legales": "str"
  },
  "clasificacion": {
    "categoria": "HOT | WARM | COLD | DISCARD",
    "score": 0,
    "justificacion": "str",
    "secciones_completadas": [],
    "advertencias": []
  }
}
```

### Score de Confianza

| Sección | Peso |
|---------|------|
| Producto detectado | 0.35 |
| Framework de conversión | 0.25 |
| Fuente de tráfico | 0.20 |
| Margen estimable | 0.10 |
| Competencia analizada | 0.10 |

Si `score < 0.4`, el agente marca `advertencias` y no recomienda publicación automática.

---

## 5. Tablas Markdown

Cuando el agente identifique datos tabulares en la transcripción, debe estructurarlos como tabla Markdown.

**Ejemplo:**

| Característica | Producto A | Producto B |
|---------------|-----------|-----------|
| Batería | 5000 mAh | 3000 mAh |
| Peso | 150 g | 200 g |
| Precio | $29.99 | $34.99 |

---

## 6. Integración con KBRouter

El output del skill se mapea directamente a las tablas del esquema GEM OS:

| Campo del Output | Tabla en DB |
|-----------------|-------------|
| `producto.*` | `product_trends` |
| `conversion.*` | `conversion_formulas` |
| `operaciones.*` | `operations_traffic` |

---

## 7. Manejo de Errores

| Condición | Comportamiento |
|-----------|---------------|
| Transcripción demasiado corta | Error, no clasificar |
| Producto no identificable | Retornar `producto: null` |
| Timeout de análisis | Clasificación parcial |
| Error de conexión a DB | Cachear en memoria, reintentar |

---

## 8. Ejecución

1. El agente lee los últimos 100 registros no clasificados de `product_trends`.
2. Aplica las reglas de clasificación.
3. Anota resultados en `ai_workspace/skills/clasificar_productos/clasificacion_reciente.json`.
4. Si hay productos `HOT`, notificar al Orchestrator Core para copywriting.

### Idempotencia
Si un `video_id` ya existe en el archivo de resultados, no se duplica.

### Tolerancia a Fallos
Si la base de datos está bloqueada, loguear el error y reintentar en el siguiente ciclo sin detener el pipeline.

---

*Fin del procedimiento. Versión 2.0.0*

