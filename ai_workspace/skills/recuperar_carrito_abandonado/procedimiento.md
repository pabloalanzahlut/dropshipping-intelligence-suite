# Skill: Recuperar Carrito Abandonado (GEM-ABANDONED-01)

**Versión:** 1.0 | **Integración:** Shopify → Make.com → Email nocturno

---

## Propósito

Recuperar ventas perdidas enviando un email personalizado a clientes que abandonaron su carrito, **exclusivamente en horario nocturno (20:00–23:00 hora local)** para maximizar tasa de apertura.

---

## Variables a mapear desde el Webhook Shopify

| Variable Make.com | Ruta en JSON Shopify | Uso en email |
|---|---|---|
| `{{email}}` | `email` | Destinatario |
| `{{nombre}}` | `customer.first_name` | Personalización asunto/cuerpo |
| `{{articulos}}` | `line_items[]` | Tabla de productos |
| `{{total_precio}}` | `total_price` | Urgencia en copy |
| `{{moneda}}` | `currency` | Formato del precio |
| `{{recovery_url}}` | `abandoned_checkout_url` | CTA del email |
| `{{timestamp_abandono}}` | `created_at` | Cálculo del retraso |
| `{{articulo_principal}}` | `line_items[0].title` | Hero visual del email |
| `{{imagen_principal}}` | `line_items[0].image.src` | Imagen en el email |

---

## Flujo Make.com — Escenario GEM-ABANDONED-01

```
[1. Custom Webhook]
     URL: MAKE_WEBHOOK_ABANDONED_CART (en .env)
     Método: POST | Content-Type: application/json
        ↓
[2. JSON Parse]
     Extrae todas las variables de la tabla anterior
        ↓
[3. Filter: Email no vacío]
     Condición: {{email}} IS NOT EMPTY
        ↓
[4. Sleep 60 minutos]
     Espera antes de verificar si el cliente ya compró
        ↓
[5. Shopify: Search Orders]
     Busca pedido con email = {{email}} creado después de {{timestamp_abandono}}
        ↓
[6. Filter: Sin pedido existente]
     Condición: número de resultados del paso 5 = 0
        ↓
[7. Router: Filtro horario nocturno]
     ┌─ Rama A: HOUR(NOW()) >= 20 AND HOUR(NOW()) <= 23
     │     → [8A. Gmail/Klaviyo: Enviar email]
     │     → [9A. Google Sheets: Log envío]
     │
     └─ Rama B: fuera de horario
           → [8B. Google Sheets: Guardar pendiente]
                flag: pendiente = true
                (Escenario secundario a las 20:00 procesa pendientes)
```

---

## Escenario secundario: procesador de pendientes (trigger horario 20:00)

```
[Trigger: Every day at 20:00]
        ↓
[Google Sheets: Get rows WHERE pendiente = true]
        ↓
[Iterator: por cada fila]
        ↓
[Gmail/Klaviyo: Enviar email]
        ↓
[Google Sheets: Actualizar fila → pendiente = false, enviado_at = NOW()]
```

---

## Filtro horario — Fórmulas Make.com exactas

**Verificar si es horario válido (módulo Filter):**
```
HOUR(NOW()) >= 20 AND HOUR(NOW()) <= 23
```

**Calcular próximo slot válido (módulo Sleep Until, Rama B):**
```
IF(
  HOUR(NOW()) >= 23,
  SET_HOUR(ADD_DAYS(NOW(), 1), 20),
  SET_HOUR(NOW(), 20)
)
```

---

## Payload JSON — GEM OS → Make.com

```json
{
  "source": "GEM_OS_ABANDONED_CART",
  "correlation_id": "{{checkout_token}}_{{unix_timestamp}}",
  "to": "{{email}}",
  "subject": "{{nombre}}, dejaste algo olvidado",
  "template_vars": {
    "nombre": "{{nombre}}",
    "articulo_principal": "{{articulo_principal}}",
    "imagen_principal": "{{imagen_principal}}",
    "total": "{{total_precio}} {{moneda}}",
    "recovery_url": "{{recovery_url}}",
    "articulos_lista": "{{articulos}}"
  },
  "metadata": {
    "shopify_checkout_token": "{{checkout_token}}",
    "timestamp_abandono": "{{timestamp_abandono}}",
    "timestamp_enviado": "{{NOW()}}"
  }
}
```

---

## Reglas de negocio

- **Un solo email por checkout** — el `correlation_id` evita duplicados en Google Sheets
- **Nunca enviar entre 23:00 y 20:00** — acumular en hoja "pendientes"
- **El email NO menciona tiempos de envío irreales** — usar "5-7 días o 2-5 días hábiles según proveedor" (Q4Ykcwh5Osc, 22:27 y 26:03)
- **Si `email` está vacío** → descartar silenciosamente, no contar como error

---

## Variables de entorno requeridas

```
MAKE_WEBHOOK_ABANDONED_CART=https://hook.eu1.make.com/XXXXXXXXXXXXXXXX
SHOPIFY_WEBHOOK_SECRET=shpss_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

---

## Configuración en Shopify Admin

1. Ir a **Settings → Notifications → Webhooks**
2. Crear webhook:
   - Evento: `Checkouts / Checkout creation` y `Checkout update`
   - URL: `https://tu-dominio.com/webhooks/shopify/abandoned-cart`
   - Formato: JSON
3. Copiar el **Signing secret** → guardarlo en `.env` como `SHOPIFY_WEBHOOK_SECRET`

---

## Prueba local

```bash
# Levantar servidor con ngrok
ngrok http 8000

# Simular payload de prueba (sin enviar a Make.com)
python app/services/abandoned_cart_handler.py --test
```

---

## Manejo de errores

| Error | Acción |
|---|---|
| Webhook timeout | Retry 1x tras 30s |
| `MAKE_WEBHOOK_ABANDONED_CART` no configurado | Retorna `[DATA_GAP]`, detener subtarea |
| Email vacío en checkout | Descartar silenciosamente |
| Firma Shopify inválida | HTTP 401, registrar WARNING |
| Rate limit Make.com | Postponer 1h, registrar WARNING |

