# Skill: TikTok Ads para Dropshipping

**ID:** `tiktok_ads`
**Versión:** 1.0.0
**Fuente:** Adrián Sáenz `Q4Ykcwh5Osc 23:56:06`
**Propósito:** Configurar y gestionar campañas de TikTok Ads de pago: Business Manager, pixel, campañas de ventas, análisis de métricas y retargeting.

**Diferencia clave vs. `/publicar-tiktok`:**
- `/publicar-tiktok` = publicación orgánica gratuita vía Make.com
- `/tiktok-ads` = inversión publicitaria pagada con pixel de conversión

---

## Fase 1 — Crear Cuenta Business Manager (Adrián `24:00:26` – `24:07:44`)

1. business.tiktok.com → Crear cuenta nueva
2. Verificar cuenta de empresa (DNI + documentación del negocio)
3. Dentro de Business Manager, crear **TikTok Ads Manager**:
   - ads.tiktok.com → vincular con Business Manager
4. Configurar método de pago (tarjeta de crédito recomendada, no débito)
5. Zona horaria: usar la del mercado objetivo, no la tuya
6. Moneda: € si vendes a Europa

### Recuperar cuenta baneada (Adrián `24:00:19`)
Si la cuenta es suspendida:
1. Apelar dentro de los primeros 7 días (formulario en TikTok Business)
2. Proporcionar: URL de la tienda, producto vendido, últimos anuncios
3. Si no se recupera en 14 días → crear cuenta nueva con:
   - IP diferente (VPN o conexión distinta)
   - Email nuevo
   - Dispositivo diferente o modo incógnito

---

## Fase 2 — Pixel de TikTok (Adrián `24:25:06`)

**El pixel es obligatorio antes de cualquier campaña de ventas.**

### Instalación en Shopify
1. TikTok Ads Manager → Activos → Eventos → Crear Pixel
2. Método de instalación: **Shopify App** (más fiable que código manual)
   - Instalar app "TikTok" desde Shopify App Store
   - Conectar con cuenta TikTok Business → el pixel se instala automáticamente
3. Verificar eventos que deben disparar:
   - `ViewContent` — producto visto
   - `AddToCart` — añadido al carrito
   - `InitiateCheckout` — inicio de pago
   - `CompletePayment` — compra completada (el más importante)
4. Test: TikTok Pixel Helper (extensión Chrome) → hacer una compra de prueba

### Configuración de Eventos Avanzados
- Activar **Advanced Matching** con email y teléfono del cliente (mejora atribución)
- Activar **Automatic Advanced Matching** en la app Shopify → TikTok

---

## Fase 3 — Analizar Métricas (Adrián `24:41:17`)

### Métricas clave en TikTok Ads

| Métrica | Umbral óptimo | Qué indica |
|---------|--------------|------------|
| **CPM** | <€10-15 | Coste por 1000 impresiones |
| **CTR** | >1,5% | % que hace clic en el anuncio |
| **CPC** | <€0,50 | Coste por clic |
| **CVR** | >1% | % de clics que compran |
| **CPA** | < 1/3 del PVP | Coste por adquisición — regla Adrián |
| **ROAS** | ≥2 mínimo | Retorno sobre inversión |

### Regla de ROAS (Adrián `Q4Ykcwh5Osc 09:40`)
ROAS mínimo = 2 · ROAS objetivo = 3+
El ROAS que declara TikTok puede ser mayor al real por:
- Atribución multi-touch (mismo cliente visto en varios canales)
- Ventana de atribución larga (7-14 días)
Contrastar siempre con Shopify Analytics como fuente de verdad.

---

## Fase 4 — Tipos de Campañas (Adrián `24:51:36`)

| Tipo | Objetivo | Cuándo usar |
|------|---------|-------------|
| **Awareness** | Impresiones/alcance | Lanzar marca nueva |
| **Consideración** | Vistas de video, tráfico | Calentar audiencia |
| **Conversión (Ventas)** | Compras | Principal para dropshipping |
| **Retargeting** | Reimpactar visitantes | Después de tener tráfico |

**Para dropshipping: usar siempre "Conversión" como objetivo principal.**

---

## Fase 5 — Crear Campaña de Ventas (Adrián `25:00:39`)

### Estructura recomendada
```
Campaña: [Producto] — Ventas — [País]
  └── Conjunto de anuncios 1: Broad (sin audiencia)
  │     └── Anuncio A: Hook demostración
  │     └── Anuncio B: Hook problema-solución
  └── Conjunto de anuncios 2: Intereses (nicho del producto)
        └── Anuncio A: mismo
        └── Anuncio B: mismo
```

### Configuración del conjunto de anuncios
- **Presupuesto:** €20-30/día por conjunto (mínimo para que el algoritmo aprenda)
- **Programación:** empezar sin límite de horario
- **Ubicaciones:** Automáticas (TikTok elige dónde convierte mejor)
- **Audiencia Broad:** sin intereses — dejar al algoritmo encontrar compradores
- **Optimización:** "Complete Payment" (no "Add to Cart")
- **Estrategia de puja:** Coste más bajo (fase inicial) → Coste objetivo (una vez con datos)

### Creativo del anuncio
- Usar video de `/redactar-guion` + `/generar-video-ia`
- Duración: 15-30 segundos
- Ratio: 9:16 vertical obligatorio
- Texto del anuncio: beneficio principal en ≤100 caracteres
- CTA: "Comprar ahora" o "Ver más"

---

## Fase 6 — Estructura de Campaña Avanzada (Adrián `25:24:24`)

### Reglas de escalado en TikTok
1. **Día 1-3:** No tocar nada. El algoritmo está aprendiendo.
2. **Día 3:** Si ROAS ≥ 2 → escalar presupuesto un 20%
3. **Si CTR < 0,5%:** El creativo no engancha → pausar y crear nuevo hook
4. **Si CTR > 1,5% pero CVR < 0,5%:** El problema es la landing page, no el anuncio
5. **Nunca duplicar un conjunto de anuncios ganador** sin esperar 48h

---

## Fase 7 — Análisis de la Competencia (Adrián `25:27:17`)

### TikTok Creative Center
ads.tiktok.com/business/creativecenter:
- Buscar por industria / país / fecha
- Filtrar por "más compartidos" o "mayor CTR"
- Analizar: hook primeros 3s, duración, música, texto en pantalla

### Señales de anuncio ganador de la competencia
- Más de 100K vistas con pocos días activo
- Alto engagement (comentarios "¿dónde lo compro?")
- CTA directo a landing de producto

---

## Fase 8 — Campaña de Retargeting (Adrián `25:34:38`)

**Requisito:** mínimo 500 visitantes únicos en la tienda para que el retargeting funcione.

### Audiencias personalizadas para retargeting
1. TikTok Ads Manager → Audiencias → Crear audiencia personalizada
2. Tipos de audiencia:
   - **Visitantes del sitio web** (últimos 30 días) — más amplia
   - **Add to Cart sin comprar** (últimos 14 días) — mayor intención
   - **Iniciaron checkout sin comprar** (últimos 7 días) — mayor intención aún

### Configuración de campaña de retargeting
- Presupuesto: €10-15/día
- Creativo diferente al de prospección (reconocen el anuncio anterior)
- Mensaje: urgencia o garantía ("Aún tienes tu carrito", "Envío gratis hoy")
- Frecuencia máxima: 3 impresiones/usuario/día

---

## Output JSON de campaña

```json
{
  "campana_id": "",
  "tipo": "prospeccion | retargeting",
  "presupuesto_diario": 0.00,
  "ctr": 0.0,
  "cvr": 0.0,
  "roas_tiktok": 0.0,
  "roas_shopify": 0.0,
  "cpa": 0.00,
  "estado": "aprendizaje | activa | escalando | pausada",
  "creativos_activos": 0,
  "proxima_revision": "YYYY-MM-DD"
}
```
