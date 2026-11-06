# Skill: Redactar Ficha de Producto Shopify

**ID:** `redactar_ficha_shopify`
**Versión:** 1.0.0
**Agente responsable:** `@gem-orchestrator-core`
**Propósito:** Generar la ficha completa de producto para Shopify (título SEO, descripción AIDA, bullets de beneficios, specs técnicas y metadatos) usando datos reales del proveedor. Cero invención de datos físicos.

---

## 1. Input Esperado

```json
{
  "producto": {
    "nombre": "str",
    "nicho": "str",
    "costo_origen_usd": "float",
    "pvp_usd": "float",
    "peso_kg": "float",
    "dimensiones": "str (LxAxH cm)",
    "material": "str",
    "colores_disponibles": ["str"],
    "wow_factor": "str",
    "proveedor": "str (AliExpress|CJDropshipping|Zendrop)"
  },
  "mercado_objetivo": "USA|CA|ES|EU",
  "idioma_salida": "es|en"
}
```

### Validaciones de entrada

| Condición | Acción |
|-----------|--------|
| `costo_origen_usd` ausente | `[DATA_GAP: costo_origen_usd]` — no continuar |
| `pvp_usd / costo_origen_usd < 3.0` | ERROR: viola Regla 3x — rechazar |
| `peso_kg > 1.2` | ERROR: viola restricción logística — rechazar |
| `nombre` ausente | `[DATA_GAP: nombre]` — no continuar |
| `material` ausente | Usar "Material no especificado" y advertir |

---

## 2. Pipeline de Redacción

Ejecutar los pasos **en orden**. No saltar ninguno.

### Paso 1: Título SEO (≤60 caracteres)

Formato: `[Beneficio principal] + [Nombre del producto] + [Diferenciador]`

Reglas:
- Incluir la palabra clave principal del nicho al inicio
- Sin superlativos vacíos (increíble, fantástico, revolucionario)
- Sin marcas de terceros si no están verificadas
- Máximo 60 caracteres para evitar truncamiento en Google Shopping

Ejemplo: `Cargador Magnético RGB Inalámbrico 3-en-1 Qi 15W`

### Paso 2: Hook de Dolor (2 líneas)

Primera línea visible bajo el título en Shopify. Activar el punto de dolor del buyer persona en ≤20 palabras.

Formato: `¿[Problema que resuelve]? [Producto] lo soluciona sin [fricción asociada].`

Restricción: No mencionar velocidades de envío específicas ni fechas de entrega.

### Paso 3: Bullets de Beneficios Emocionales (3 bullets)

Cada bullet: emoji + beneficio emocional (no feature) en ≤12 palabras.

| ❌ Feature (prohibido) | ✅ Beneficio emocional |
|------------------------|----------------------|
| "Batería de 5000 mAh" | "📱 Carga toda la noche sin buscar el cable al despertar" |
| "Material ABS resistente" | "🛡️ Resiste caídas sin que parezca que lo usaste" |

### Paso 4: Especificaciones Técnicas (INMUTABLES)

Transcribir literalmente del proveedor. **Prohibido alterar o redondear.**

```
• Material: [valor exacto del proveedor]
• Dimensiones: [LxAxH] cm
• Peso: [valor exacto] kg
• Colores disponibles: [lista exacta]
• Compatibilidad: [exacta del proveedor]
• Voltaje/Corriente: [si aplica, exacto]
```

Nota de cumplimiento: Alterar estos datos causa contracargos en Stripe/PayPal y bloqueos de cuenta.

### Paso 5: Sección de Confianza Internacional

Incluir siempre para mercados USA/EU:

```
✅ Envío internacional rastreado (estimado 6-15 días hábiles)
✅ 30 días para devolución sin preguntas
✅ Pago 100% seguro (SSL + cifrado de grado bancario)
✅ Atención al cliente en español e inglés
```

Restricción: El rango de días debe coincidir con el proveedor seleccionado:
- AliExpress → 10-20 días
- CJDropshipping → 7-15 días
- Zendrop → 5-10 días

### Paso 6: CTA Final

Una sola línea. Sin puntuación exclamativa. Sin superlativos.

Formato: `Agregar al carrito` (botón Shopify nativo — no modificar el texto del botón, sí el copy de apoyo)

Copy de apoyo (≤8 palabras): `Stock limitado · Pedido sale en 24 h`

### Paso 7: Multi-Ángulo AIDA (3 variantes del bloque Interés+Deseo)

Generar 3 versiones alternativas de los bullets + garantía para A/B testing. Cada versión ataca un ángulo psicológico distinto. Las specs técnicas son idénticas en las tres; solo varía el copy emocional.

**Ángulo 1 — Dolor** (el problema que resuelve)
Bullets enfocados en la frustración actual del buyer. Garantía redactada como alivio.
Ejemplo intro: `"Cansado de [problema]? Esto cambia todo."`

**Ángulo 2 — Aspiración** (el resultado que desea obtener)
Bullets enfocados en la vida mejorada. Garantía redactada como inversión en sí mismo.
Ejemplo intro: `"Imagina [resultado deseado] cada vez que [acción]."`

**Ángulo 3 — Social Proof** (lo que están haciendo otros compradores)
Bullets en tercera persona plural. Garantía redactada como confianza de comunidad.
Ejemplo intro: `"Miles de clientes en [mercado] ya han [resultado]."`

Regla: Ningún ángulo puede inventar testimonios, cifras de ventas o estadísticas no verificadas.

---

## 3. Output Esperado

```json
{
  "ficha": {
    "titulo_seo": "str (≤60 chars)",
    "hook_dolor": "str (≤20 palabras)",
    "bullets_beneficios": ["str", "str", "str"],
    "specs_tecnicas": {
      "material": "str",
      "dimensiones": "str",
      "peso_kg": "float",
      "colores": ["str"],
      "compatibilidad": "str"
    },
    "seccion_confianza": ["str", "str", "str", "str"],
    "copy_apoyo_cta": "str",
    "angulos_aida": {
      "dolor": {
        "intro": "str",
        "bullets": ["str", "str", "str"],
        "garantia": "str"
      },
      "aspiracion": {
        "intro": "str",
        "bullets": ["str", "str", "str"],
        "garantia": "str"
      },
      "social_proof": {
        "intro": "str",
        "bullets": ["str", "str", "str"],
        "garantia": "str"
      }
    }
  },
  "validacion": {
    "regla_3x_ok": true,
    "peso_ok": true,
    "specs_intactas": true,
    "superlativos_detectados": [],
    "advertencias": []
  },
  "metadatos_shopify": {
    "meta_title": "str (≤60 chars)",
    "meta_description": "str (≤155 chars)",
    "h1_sugerido": "str (keyword secundaria, distinto del meta_title)",
    "url_handle": "str (slug sin stopwords, minúsculas, guiones)",
    "alt_text_imagen_principal": "str (≤125 chars, producto + uso + contexto)",
    "schema_product_description": "str (≤300 chars, para Google Rich Results)",
    "tags_seo": ["producto_1", "producto_2", "nicho", "beneficio", "tendencia"],
    "tags": ["str"],
    "vendor": "str",
    "product_type": "str"
  }
}
```

---

## 4. Reglas de Negocio Inmutables

| Regla | Origen | Consecuencia de violar |
|-------|--------|------------------------|
| PVP = CO × 3 mínimo | Adrián Sáenz | Rechazar producto |
| Sin alteración de specs físicas | Protección Stripe/PayPal | CRITICAL + auditoría |
| Sin superlativos vacíos | agent.md §2.2 | WARNING + corrección |
| Sin fechas de envío inventadas | agent.md §2.2 | CRITICAL |

---

## 5. Manejo de Errores

| Condición | Comportamiento |
|-----------|---------------|
| Regla 3x violada | Retornar error, no generar ficha |
| Campo físico faltante | `[DATA_GAP: campo]` + detener |
| Superlativo detectado en output | Auto-corregir y registrar en `advertencias[]` |
| Spec alterada por el modelo | Revertir al valor de input + CRITICAL log |

---

## 6. Integración con KBRouter

| Campo del Output | Acción |
|-----------------|--------|
| `ficha.titulo_seo` | Guardar en `product_trends.shopify_title` |
| `ficha.*` | Exportar a `projects/{producto_id}/ficha_shopify.json` |
| `validacion.advertencias` | Log en `ai_workspace/memory/funnel_memory.txt` |

---

*Fin del procedimiento. Versión 2.0.0 — GEM OS · Fase 3 Copywriting Avanzado*

