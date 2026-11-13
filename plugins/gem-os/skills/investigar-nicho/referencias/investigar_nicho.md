# Skill: Investigar Nicho y Generar Informe de Ángulos

**ID:** `investigar_nicho`
**Versión:** 1.0.0
**Propósito:** Generar un informe de 10 ángulos de ataque para un nicho de dropshipping, identificando problemas reales, públicos objetivo y diferenciación para Meta Ads. Nivel 2 del framework de 7 niveles.

**Referencias:**
  - `contexto/manual/matriz_tendencias.md` — tendencias activas
  - `referencias/clasificar_productos.md` — para validar productos encontrados
  - `contexto/manual/formulas_conversion.md` — benchmarks de KPIs

---

## 1. Input Esperado

```
Nicho: [nombre del nicho, ej: mascotas, hogar, motor, fitness, bebés]
Mercado objetivo: [España / LATAM / USA / EU] (opcional, default: España/EU)
Presupuesto de test disponible: [€/$] (opcional, para ajustar recomendaciones de precio)
```

---

## 2. Pipeline de Generación

### Paso 1: Análisis del Nicho

Identificar las características estructurales del nicho:
- Estacionalidad (¿hay picos de demanda?)
- Sensibilidad al precio del público (¿compran por impulso o por necesidad?)
- Nivel de competencia estimado (alto/medio/bajo)
- Restricciones logísticas frecuentes en el nicho

### Paso 2: Generación de 10 Ángulos

Para cada ángulo, generar la siguiente ficha:

```
ÁNGULO [N]: [nombre del ángulo]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Problema severo que resuelve:
  [descripción del dolor real del cliente, específico y verificable]

Público objetivo ideal:
  Demográfico: [edad, género, situación]
  Intereses Meta Ads: [3-5 intereses concretos para segmentar]
  Comportamiento: [qué hace online este público]

Tipo de producto a buscar:
  [descripción funcional del producto, sin marca]

Rango de precio sugerido:
  Costo origen estimado: [X]€
  PVP sugerido: [X]€  (≥3x)
  Validación rápida 3x: [SÍ/NO]

Hook de anuncio sugerido (3 segundos):
  "[texto del gancho visual/verbal]"

Señal de demanda:
  [cómo verificar que hay búsqueda: palabras clave, TikTok hashtags, Amazon BSR]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Paso 3: Ranking por Potencial

Al final del informe, ordenar los 10 ángulos de mayor a menor potencial usando:

| Criterio | Peso |
|----------|------|
| Urgencia del problema (escala 1-5) | 40% |
| Facilidad de encontrar producto ≥3x | 30% |
| Capacidad de targeting en Meta | 20% |
| Riesgo logístico bajo | 10% |

---

## 3. Output

Entregar:
1. Resumen del nicho (5 líneas máximo)
2. Los 10 ángulos con fichas completas
3. Tabla de ranking final con recomendación del ángulo #1 para empezar

---

## 4. Reglas de Comportamiento

- Basar los ángulos en problemas reales y verificables, no en suposiciones
- Si el nicho tiene restricciones legales conocidas (ej: productos médicos sin certificación) → advertir en cada ángulo afectado
- Los precios sugeridos son estimados; siempre validar con `/validar-financiero` antes de lanzar
- Consultar `matriz_tendencias.md` para priorizar ángulos con señales activas de tendencia
- Nunca inventar datos de demanda (búsquedas, ventas); indicar cómo verificarlos
