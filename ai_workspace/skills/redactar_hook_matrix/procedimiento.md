# Skill: Redactar Matriz de Hooks

**ID:** `redactar_hook_matrix`
**Versión:** 1.0.0
**Agente responsable:** `@gem-orchestrator-core`
**Propósito:** Generar una matriz de ≥10 hooks de alta conversión para TikTok, Instagram Reels y Meta Ads a partir de los datos del producto. Cada hook se clasifica por fórmula, ángulo psicológico y formato de distribución.

**Fuente metodológica:** Marc Verdú + Javi Ecomm (`estrategia_organica_tiktok.html`) · Roger Viladrosa (`guia_completa_dropshipping_2026.md`)

---

## 1. Input Esperado

```json
{
  "producto": {
    "nombre": "str",
    "nicho": "str",
    "problema_principal": "str (descripción del dolor del buyer persona)",
    "wow_factor": "str (qué hace visualmente impactante al producto)",
    "pvp_usd": "float",
    "solucion_vieja": "str (cómo lo hacía el comprador antes)"
  },
  "mercado_objetivo": "USA|CA|ES|EU",
  "idioma_salida": "es|en"
}
```

### Validaciones de entrada

| Condición | Acción |
|-----------|--------|
| `problema_principal` ausente | `[DATA_GAP: problema_principal]` — no continuar |
| `nombre` ausente | `[DATA_GAP: nombre]` — no continuar |
| `wow_factor` ausente | Usar nombre del producto como sustituto + advertir |

---

## 2. Las 6 Fórmulas de Hook (Marc Verdú / Javi Ecomm)

Generar **2 variaciones por fórmula** = 12 hooks totales mínimos.

### Fórmula 1 — Story-telling (Transformación)
Narrativa breve de transformación personal. Primera persona o tercera persona identificable.

Patrón: `"[Situación inicial frustrante] → [Producto] → [Resultado emocional]"`

Regla: La transformación debe ser verificable visualmente. No inventar testimonios.

Ejemplos de estructura:
- `"Llevaba años buscando esto sin saber que existía"`
- `"Le mostré esto a mi madre y no pudo creerlo"`

### Fórmula 2 — Shock / Dato estadístico
Dato impactante que genera disonancia cognitiva. Si no hay dato real, usar formulación de creencia generalizada.

Patrón: `"[X]% de la gente [hace algo mal/no sabe que existe/pierde tiempo]"` o `"Nadie te contó que [verdad incómoda]"`

Regla: Si el dato es inventado, usar formulación de creencia ("La mayoría de personas no sabe que..."), nunca cifras falsas con porcentaje exacto.

### Fórmula 3 — Curiosity-gap (Brecha de curiosidad)
Pregunta o afirmación que no se puede ignorar. Obliga al espectador a seguir mirando para resolver la tensión.

Patrón: `"¿Por qué [grupo de personas] están comprando esto en [mercado]?"` o `"Esto no debería existir pero aquí está"`

Regla: La respuesta al curiosity-gap debe estar en el propio vídeo o landing. No crear frustración sin resolución.

### Fórmula 4 — Before/After Visual
Contraste puro sin texto. Para rótulo de vídeo o primera línea de caption. Mínimo de palabras, máximo de imagen mental.

Patrón: `"[Estado malo] → [Estado bueno]"` en ≤6 palabras totales.

Ejemplos: `"Antes: caos. Ahora: esto."` / `"Sin [producto]: X minutos. Con [producto]: 30 segundos."`

Regla: Debe ser demostrable en los primeros 3 segundos del vídeo sin narración.

### Fórmula 5 — POV / Humor (Perspectiva identificable)
Situación cotidiana desde la perspectiva del buyer persona usando [solucion_vieja].

Patrón: `"POV: llevas [tiempo] usando [solucion_vieja] sin saber que existe [nombre_producto]"`

Regla: El humor debe ser de reconocimiento, no de burla. El espectador se ríe de sí mismo, no de otros.

### Fórmula 6 — Urgencia / Escasez (Solo si es real)
Solo activar si hay stock limitado real o descuento temporal verificable. **Prohibido inventar urgencia.**

Patrón: `"Solo [X] unidades al precio de lanzamiento"` / `"Oferta termina el [fecha real]"`

Regla: Si no hay urgencia real, **omitir esta fórmula** y generar una tercera variación de Fórmula 1 o 3 en su lugar.

---

## 3. Reglas Inmutables de los Hooks

| Regla | Consecuencia de violar |
|-------|------------------------|
| Primera línea del hook ≤8 palabras | No cumple límite de caption TikTok — corregir |
| Hook Meta Ads ≤125 caracteres totales | Truncado en Facebook feed — corregir |
| Prohibido superlativos vacíos | `regex: /mejor\|increíble\|asombroso\|revolucionario\|extraordinario/i` → WARNING + autocorrección |
| Prohibido prometer envío 24-48h | CRITICAL — rompe política TikTok Ads y Meta Ads |
| Urgencia/escasez solo si es real | Crear urgencia falsa → ban de cuenta publicitaria |
| Sin marcas de terceros sin verificar | Riesgo legal de trademark |

---

## 4. Output Esperado

```json
{
  "hook_matrix": [
    {
      "id": "hook_01",
      "formula": "story_telling|shock_data|curiosity_gap|before_after|pov_humor|urgencia",
      "angulo": "dolor|aspiracion|social_proof",
      "formato": "video_tiktok|meta_ad|email_subject|push_notification",
      "texto": "str",
      "primera_linea_chars": 0,
      "apto_tiktok_caption": true,
      "apto_meta_ad": true,
      "notas_produccion": "str (qué mostrar en pantalla en los primeros 3s)"
    }
  ],
  "total_hooks": 12,
  "validacion": {
    "superlativos_detectados": [],
    "hooks_con_envio_inventado": [],
    "urgencia_sin_verificar": false,
    "advertencias": []
  },
  "recomendacion_test": "str (qué fórmula priorizar para este nicho según el KB)"
}
```

---

## 5. Formato de los 12 Hooks (Distribución por fórmula)

| # | Fórmula | Ángulo | Formato principal |
|---|---------|--------|-------------------|
| 01 | story_telling | dolor | video_tiktok |
| 02 | story_telling | aspiracion | meta_ad |
| 03 | shock_data | dolor | video_tiktok |
| 04 | shock_data | social_proof | meta_ad |
| 05 | curiosity_gap | aspiracion | video_tiktok |
| 06 | curiosity_gap | dolor | meta_ad |
| 07 | before_after | dolor | video_tiktok |
| 08 | before_after | aspiracion | email_subject |
| 09 | pov_humor | dolor | video_tiktok |
| 10 | pov_humor | social_proof | meta_ad |
| 11 | urgencia* | aspiracion | push_notification |
| 12 | story_telling | social_proof | video_tiktok |

*Hook 11: solo si hay urgencia real. Si no, usar variante adicional de curiosity_gap.

---

## 6. Integración con KBRouter

| Campo del Output | Acción |
|-----------------|--------|
| `hook_matrix` completo | Exportar a `projects/{producto_id}/hook_matrix.json` |
| `validacion.advertencias` | Log en `ai_workspace/memory/funnel_memory.txt` |
| `hook_matrix[formato=video_tiktok]` | Usar como input para skill `redactar_guiones_tiktok` |

---

*Fin del procedimiento. Versión 1.0.0 — GEM OS · Fase 3 Copywriting Avanzado*
