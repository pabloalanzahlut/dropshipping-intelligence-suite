# Skill: Redactar Anuncios Meta Ads (Estáticos)

**ID:** `redactar_anuncios_meta`
**Versión:** 1.0.0
**Propósito:** Generar copy para anuncios estáticos de Meta Ads (Facebook/Instagram): imagen única, carousel y texto principal. Complementa `redactar_guiones_tiktok` que cubre el formato de video.

**Referencias:**
  - `contexto/manual/formulas_conversion.md` — benchmarks KPIs y estructura AIDA
  - `referencias/estructurar_landing.md` — framework AIDA de referencia
  - `referencias/redactar_guiones_tiktok.md` — NO duplicar contenido de video

---

## 1. Input Esperado

```
Nombre del producto: [nombre]
Problema principal que resuelve: [descripción]
Beneficio clave (medible): [dato concreto, ej: "ahorra 2 horas semanales"]
PVP: [€/$]
Garantía/política de devolución: [días]
Público objetivo: [descripción]
Ángulo del anuncio: [problema / wow-factor / precio / transformación]
```

---

## 2. Formatos a Generar

### Formato A: Anuncio de Imagen Única

**Primary Text** (máx. 125 caracteres visibles antes del "ver más"):
```
[Frase que describe el problema en primera persona o situación familiar]
[Beneficio concreto del producto]
[CTA implícito o pregunta que genera curiosidad]
```

**Headline** (máx. 27 caracteres):
```
[Acción + beneficio directo]
Ejemplos válidos: "Organiza tu cocina hoy", "Envío en 5-7 días"
```

**Descripción** (máx. 30 caracteres, aparece bajo el headline en desktop):
```
[Garantía o refuerzo de confianza]
Ejemplos: "Garantía 30 días", "Más de 5.000 pedidos"
```

**Reglas para imagen única:**
- El hook visual debe comunicar el problema O el resultado en 1-2 segundos
- Sin texto superpuesto que supere el 20% del área de la imagen
- Prohibido: palabras "gratis", "mejor del mundo", promesas de salud sin evidencia

---

### Formato B: Carousel (3 tarjetas)

**Tarjeta 1 — El Problema:**
- Headline: [nombre del problema en 5 palabras max]
- Descripción: [consecuencia de NO tener el producto]

**Tarjeta 2 — La Solución:**
- Headline: [nombre del producto + beneficio principal]
- Descripción: [cómo resuelve el problema, dato medible]

**Tarjeta 3 — La Oferta:**
- Headline: [PVP + garantía]
- Descripción: [CTA directo + urgencia real]

**Regla carousel:** Cada tarjeta debe funcionar de forma independiente (alguien que empiece por la tarjeta 2 debe entender el mensaje).

---

### Formato C: Variantes A/B (2 versiones del Primary Text)

Generar siempre 2 variantes del primary text para test A/B:
- **Variante Dolor:** empieza describiendo el problema
- **Variante Resultado:** empieza describiendo la transformación/beneficio

---

## 3. Benchmarks de Referencia (de `formulas_conversion.md`)

| KPI | Objetivo España/EU | Objetivo USA/CA |
|-----|-------------------|-----------------|
| CTR de salida | > 2.00% | > 2.50% |
| CPA objetivo | CPA_max × 0.70 | CPA_max × 0.70 |

Si el copy no pasa la "prueba de dedo" (¿haría clic yo mismo en este anuncio?) → reescribir.

---

## 4. Reglas de Comportamiento

- **Prohibido**: superlativos vacíos ("increíble", "revolucionario", "el mejor")
- **Prohibido**: tiempo de envío < 6 días (cumplir política de CLAUDE.md: 5-7 días (TikTok Shop) o 2-5 días hábiles (Shopify))
- **Prohibido**: promesas de resultado médico o de pérdida de peso sin evidencia
- Siempre incluir las 2 variantes A/B — nunca entregar una sola versión
- El copy de Meta Ads es distinto al guión de TikTok: no adaptar un guión de video directamente; re-escribir desde cero con la estructura de este procedimiento
- Basar los beneficios únicamente en datos proporcionados por el usuario; no inventar especificaciones del producto
