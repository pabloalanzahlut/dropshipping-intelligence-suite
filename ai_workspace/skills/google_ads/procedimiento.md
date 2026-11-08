# Skill: Google Ads para Dropshipping

**ID:** `google_ads`
**Versión:** 1.0.0
**Fuente:** Adrián Sáenz `Q4Ykcwh5Osc 17:38:44`
**Propósito:** Configurar y gestionar campañas de Google Ads para dropshipping: búsqueda, Shopping y Performance Max, con análisis y optimización basados en datos reales.

**Cuándo usar Google Ads:**
- Productos con demanda existente (la gente ya los busca)
- Ticket medio alto (>€40) donde el cliente investiga antes de comprar
- Complemento a TikTok Ads para capturar intención de compra

---

## Qué es Google Ads y cómo funciona (Adrián `17:39:51` – `17:46:31`)

Google Ads captura **demanda existente** (alguien ya está buscando el producto).
TikTok/Meta **crean demanda** (muestran el producto a quien no lo busca).

**Tipos de campaña relevantes para dropshipping:**
| Tipo | Cuándo usar | CPC medio |
|------|-------------|-----------|
| **Búsqueda** | Producto con marca o nombre conocido | €0,30-1,50 |
| **Shopping** | Catálogo de productos con imagen y precio | €0,20-0,80 |
| **Performance Max (PMax)** | Escalar con poco trabajo manual | Variable |

---

## Fase 1 — Crear Cuenta (Adrián `18:18:00`)

1. ads.google.com → Crear cuenta nueva (usar email del negocio, no personal)
2. Seleccionar objetivo: "Ventas" → "Sitio web"
3. Configurar conversiones antes de lanzar cualquier campaña:
   - Instalar Google Tag en Shopify (vía Google & YouTube app)
   - Crear conversión "Compra" con valor dinámico
   - Esperar 24-48h para verificar que las conversiones disparan correctamente
4. Vincular Google Merchant Center con Google Ads (necesario para Shopping)
5. Configurar facturación con tarjeta de crédito (no débito para evitar interrupciones)

---

## Fase 2 — Palabras Clave (Adrián `18:41:31`)

### Tipos de concordancia
| Tipo | Sintaxis | Cuándo usar |
|------|---------|-------------|
| **Exacta** | [comprar cepillo eléctrico] | Control máximo, volumen bajo |
| **Frase** | "cepillo eléctrico barato" | Balance control/volumen |
| **Amplia modificada** | +cepillo +eléctrico | Volumen alto, más ruido |

### Proceso de investigación de keywords
1. Google Keyword Planner → búsqueda por producto
2. Filtrar: volumen >500/mes, competencia media/baja
3. Priorizar keywords con intención de compra: "comprar", "precio", "oferta", "mejor"
4. Añadir palabras clave negativas desde el día 1:
   - Negativas obligatorias: "gratis", "segunda mano", "cómo hacer", "DIY", "tutorial"
5. Agrupar por intención (grupos de anuncios separados por tema)

### Presupuesto inicial recomendado
- €10-15/día por campaña durante los primeros 14 días (fase de aprendizaje)
- No tocar el presupuesto ni las pujas durante los primeros 7 días
- El algoritmo necesita ≥50 conversiones/mes para optimizar bien

---

## Fase 3 — Extensiones de Anuncios (Adrián `19:47:05`)

Añadir todas las extensiones disponibles (mejoran CTR un 10-15%):
- **Sitelinks:** categorías de la tienda, ofertas, política de devoluciones
- **Texto destacado:** "Envío en 2-5 días", "Devolución 30 días", "Pago seguro"
- **Fragmentos estructurados:** tipos de productos, marcas
- **Extensión de precio:** mostrar precio directamente en el anuncio
- **Extensión de llamada:** si tienes soporte telefónico

---

## Fase 4 — Crear Campaña de Búsqueda (Adrián `21:13:28`)

### Estructura recomendada
```
Campaña: [Producto] — Búsqueda ES
  └── Grupo 1: Keywords de compra (comprar X, precio X, X oferta)
  └── Grupo 2: Keywords de marca (si el producto tiene marca conocida)
  └── Grupo 3: Keywords de problema (solución para X, cómo X)
```

### Configuración de campaña
- Red de búsqueda únicamente (desactivar Red de Display en campaña de búsqueda)
- Estrategia de puja: "Maximizar conversiones" (una vez que tengas historial)
  - Primeros 7 días: CPC manual (€0,50 máx) para controlar el gasto
- Ubicaciones: solo los países donde tienes configurado el envío
- Idioma: idioma del mercado objetivo + inglés
- Programación: empezar las 24h, ajustar según datos de conversión por hora

### Texto del anuncio (responsive)
- 15 títulos posibles (Google combina los mejores)
- Incluir keyword en al menos 3 títulos
- 4 descripciones: beneficio + urgencia + garantía + CTA
- URL display: tutienda.com/producto

---

## Fase 5 — Google Shopping / Merchant Center (Adrián `22:05:01`)

1. Crear cuenta Google Merchant Center → merchant.google.com
2. Verificar y reclamar el dominio
3. Configurar feed de productos:
   - Shopify → Google & YouTube app → sincronización automática del catálogo
   - Verificar que todos los productos tienen: título, descripción, precio, imagen, GTIN/EAN
4. Crear campaña Shopping en Google Ads:
   - Presupuesto: €15-20/día
   - Prioridad de campaña: media
   - CPC máximo: €0,40 inicial
5. Excluir productos con margen bajo del feed

---

## Fase 6 — Análisis y Optimización (Adrián `21:05:06`)

### Métricas clave a revisar (cada 3-7 días)
| Métrica | Umbral óptimo | Acción si falla |
|---------|--------------|-----------------|
| CTR | >3% búsqueda, >0,5% Shopping | Mejorar textos/imágenes |
| CPC | <€1 búsqueda, <€0,50 Shopping | Ajustar pujas o keywords |
| Tasa de conversión | >1,5% | Revisar landing page |
| ROAS | ≥2 (mínimo Adrián) | Cortar keywords no rentables |
| Impression Share | >50% para keywords principales | Aumentar presupuesto si ROAS ok |

### Reglas de optimización
- Pausar keywords con >50 clics y 0 conversiones
- Aumentar puja en keywords con ROAS >3
- Añadir como negativas los términos de búsqueda irrelevantes (revisar semanalmente)
- A/B test de anuncios: siempre tener ≥2 variantes activas por grupo

---

## Casos Prácticos Ecommerce (Adrián `23:23:16`)

### Producto de demanda existente (ej. organizador de cables)
- Canal principal: Google Shopping
- Presupuesto: €15/día
- Keywords: "organizador cables escritorio", "soporte cables mesa"
- CTA en el anuncio: "Envío en 2-5 días · Desde €X"

### Producto de impulso (ej. gadget TikTok viral)
- Google Ads complementa a TikTok: captura a quien buscó después de ver el video
- Usar keywords de marca del producto + nombre viral
- Presupuesto bajo (€5-8/día) como red de captura

---

## Output JSON de sesión

```json
{
  "campana_id": "",
  "tipo": "busqueda | shopping | pmax",
  "presupuesto_diario": 0.00,
  "keywords_activas": 0,
  "keywords_negativas": 0,
  "ctr_actual": 0.0,
  "roas_actual": 0.0,
  "estado": "aprendizaje | activa | pausada | escalando",
  "proxima_revision": "YYYY-MM-DD"
}
```
