# Skill: Publicar Guión TikTok Automáticamente (Make.com)

**ID:** `publicar_tiktok_automatico`
**Versión:** 1.0.0
**Agente responsable:** `@gem-orchestrator-core`
**Propósito:** Recibe el JSON de `redactar_guiones_tiktok` y lo envía a Make.com para publicación automática en TikTok Business sin intervención manual.

---

## 1. Arquitectura del Flujo

```
GEM OS (redactar_guiones_tiktok)
        ↓ JSON output
publicar_tiktok_automatico (este skill)
        ↓ HTTP POST
Make.com Webhook (Escenario #GEM-TIKTOK-01)
        ↓
  ├── Módulo: Text-to-Video (CapCut API / Canva API)
  ├── Módulo: TikTok Business API → Upload + Publish
  └── Módulo: Google Sheets → Log publicación
```

---

## 2. Input Esperado

Recibe directamente el output de `redactar_guiones_tiktok`:

```json
{
  "guion": {
    "hook": "str (≤3 segundos)",
    "demostracion": "str",
    "cta": "str",
    "duracion_seg": 15,
    "hashtags": ["str"],
    "descripcion_post": "str (≤150 chars)"
  },
  "producto": {
    "nombre": "str",
    "pvp_usd": "float",
    "url_imagen": "str"
  },
  "webhook_url": "str (Make.com webhook URL)"
}
```

---

## 3. Configuración Make.com (paso a paso)

### Paso 1: Crear el Escenario en Make.com

1. Ir a **make.com** → New Scenario
2. Añadir módulo: **Webhooks → Custom Webhook**
3. Copiar la URL generada (formato: `https://hook.eu1.make.com/XXXXXXXX`)
4. Guardar esa URL como `MAKE_WEBHOOK_TIKTOK` en `.env`

### Paso 2: Módulos del Escenario

```
[Webhook] → [JSON Parse] → [HTTP Request CapCut] → [TikTok Business] → [Google Sheets]
```

**Módulo 1 – Webhook:**
- Tipo: Custom Webhook
- Data structure: definir campos `hook`, `demostracion`, `cta`, `hashtags`, `descripcion_post`, `url_imagen`

**Módulo 2 – HTTP Request (generar video):**
Opción A — CapCut for Business API:
```
URL: https://business-api.capcut.com/api/v1/video/create
Method: POST
Headers: { "Authorization": "Bearer {{CAPCUT_TOKEN}}" }
Body: {
  "script": "{{1.hook}} {{1.demostracion}} {{1.cta}}",
  "product_image_url": "{{1.url_imagen}}",
  "template_id": "dropshipping_clean_001",
  "duration": {{1.duracion_seg}}
}
```

Opción B — Sin video generado (solo imagen + texto):
- Usar Canva Make module si tienen Canva Pro
- O subir directamente imagen con texto superpuesto via TikTok Photo mode

**Módulo 3 – TikTok Business API (publicar):**
```
Module: TikTok for Business → Upload Video
video_url: {{2.video_url}}
caption: "{{1.descripcion_post}} {{1.hashtags | join: ' '}}"
privacy_level: PUBLIC_TO_EVERYONE
```

**Módulo 4 – Google Sheets (log):**
```
Spreadsheet: GEM OS - Publicaciones TikTok
Row: [fecha, producto, hook, url_publicada, estado]
```

### Paso 3: Variables de Entorno

Agregar a `H:\dropshipping_intelligence_suite\.env`:
```
MAKE_WEBHOOK_TIKTOK=https://hook.eu1.make.com/XXXXXXXX
TIKTOK_BUSINESS_ACCESS_TOKEN=<tu_token>
CAPCUT_API_TOKEN=<tu_token>
```

---

## 4. Pipeline de Ejecución (Claude Code)

Cuando el usuario confirma publicar un guión:

```python
import httpx, json, os

def publicar_guion_tiktok(guion_json: dict) -> dict:
    """
    Envía guión validado a Make.com para publicación automática.
    Requiere: MAKE_WEBHOOK_TIKTOK en .env
    """
    webhook_url = os.getenv("MAKE_WEBHOOK_TIKTOK")
    if not webhook_url:
        return {"error": "DATA_GAP: MAKE_WEBHOOK_TIKTOK no configurado"}

    payload = {
        "guion": guion_json["guion"],
        "producto": guion_json["producto"],
        "timestamp": guion_json.get("timestamp", ""),
        "source": "GEM_OS_v2"
    }

    response = httpx.post(webhook_url, json=payload, timeout=30)

    if response.status_code == 200:
        return {"status": "ENVIADO", "make_response": response.text}
    else:
        return {"status": "ERROR", "code": response.status_code, "detail": response.text}
```

---

## 5. Reglas de Negocio

| Regla | Valor | Acción si falla |
|-------|-------|-----------------|
| Guión sin CTA | Prohibido publicar | ERROR + detener |
| Descripción > 150 chars | Truncar automáticamente | WARNING |
| Hashtags mínimos | 3 hashtags | ERROR si <3 |
| Horario de publicación | 18:00-21:00 hora local | Make.com scheduler |
| Frecuencia máxima | 1 video/día por cuenta | Make.com rate limit |

---

## 6. Horario Óptimo de Publicación (TikTok Dropshipping)

Configurar en Make.com → Schedule:

| Día | Hora | Audiencia objetivo |
|-----|------|--------------------|
| L-V | 19:00 local | Adultos jóvenes post-trabajo |
| Sáb | 11:00 local | Compradores de fin de semana |
| Dom | 20:00 local | Pico histórico e-commerce |

---

## 7. Manejo de Errores

| Condición | Comportamiento |
|-----------|---------------|
| Webhook timeout | Reintentar 1x después de 30s |
| TikTok API rate limit | Posponer 24h, log en Sheets |
| Video generation failed | Publicar como Photo mode con imagen producto |
| `MAKE_WEBHOOK_TIKTOK` ausente | `[DATA_GAP]` + instrucciones de configuración |

---

## 8. Validación Pre-Publicación (obligatoria)

Antes de enviar al webhook, verificar:
- [ ] Regla 3x del producto asociado: `pvp ≥ 3 × costo_origen`
- [ ] Hook sin superlativos vacíos
- [ ] Sin promesas de envío express irreal
- [ ] Hashtags relevantes al nicho (mínimo 3)
- [ ] `descripcion_post` ≤ 150 caracteres

---

*Fin del procedimiento. Versión 1.0.0 — GEM OS*
