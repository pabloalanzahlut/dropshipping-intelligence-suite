# Skill: Configurar Tienda Shopify

**ID:** `configurar_tienda`
**Versión:** 1.0.0
**Fuente:** Adrián Sáenz `Q4Ykcwh5Osc 03:33:07`
**Propósito:** Checklist completo de configuración inicial de Shopify antes de lanzar tráfico: dominio, pagos, políticas, envíos y conexión AutoDS.

**Trigger:** Manual vía `/configurar-tienda` una vez que la tienda está diseñada.
**Prerrequisito:** Tienda Shopify creada (trial o plan activo).

---

## Checklist de Configuración (en orden)

### 1. Dominio
- [ ] Comprar dominio propio (recomendado: Namecheap o Shopify Domains)
- [ ] Conectar en Shopify → Configuración → Dominios → Conectar dominio existente
- [ ] Configurar dominio principal (quitar `.myshopify.com` como principal)
- [ ] Verificar SSL activo (candado en la URL — puede tardar 24-48h)
- [ ] Redirigir `www` y raíz al mismo dominio

### 2. Pagos
- [ ] Shopify Payments (si disponible en tu país) → Configuración → Pagos
  - Documentación necesaria: DNI/pasaporte + datos bancarios
  - Comisión: 0% de tarifa de transacción con Shopify Payments
- [ ] PayPal Express como alternativa (obligatorio para clientes que no usan tarjeta)
- [ ] Configurar moneda de la tienda (€ o $ según mercado objetivo)
- [ ] Activar "Pago en 1 clic" si está disponible

### 3. Políticas Legales (obligatorias antes de lanzar)
Shopify → Configuración → Políticas → usar generador automático y personalizar:
- [ ] **Política de devoluciones**: 30 días, producto sin abrir, cliente paga envío de retorno
- [ ] **Política de privacidad**: RGPD si vendes a Europa
- [ ] **Términos de servicio**: incluir tiempo de envío real (2-5 días hábiles según Adrián `22:27`)
- [ ] **Política de envíos**: tiempos reales del proveedor, sin prometer 24-48h
- Añadir las políticas al footer de la tienda

### 4. Zonas de Envío
Shopify → Configuración → Envíos y entrega:
- [ ] Crear zona para tu mercado principal (ej. "Europa Occidental")
- [ ] Envío gratuito para pedidos > umbral (calcular sobre coste landed para mantener margen)
- [ ] Tarifa fija para pedidos pequeños (ej. €3,99)
- [ ] Eliminar zonas de envío que no usas (reduce confusión al checkout)
- [ ] Tiempo de procesamiento: 1-3 días laborables (AutoDS + proveedor)

### 5. Checkout
Shopify → Configuración → Checkout:
- [ ] Activar "Cuentas de cliente: opcionales" (no forzar registro)
- [ ] Campos de dirección: solo los necesarios (quitar campos innecesarios)
- [ ] Activar email de confirmación automático
- [ ] Añadir logo en el checkout
- [ ] Configurar moneda de presentación si difiere de la de pago

### 6. Conectar AutoDS a Shopify
*(Adrián `Q4Ykcwh5Osc 26:10:45`)*
- [ ] AutoDS → Configuración → Tiendas → Añadir tienda → Shopify
- [ ] Instalar app AutoDS desde Shopify App Store
- [ ] Autorizar permisos (gestión de pedidos + productos)
- [ ] Configurar precio automático: regla 2x mínimo, objetivo 3x sobre coste landed
- [ ] Activar fulfillment automático (AutoDS procesa pedidos sin intervención manual)
- [ ] Configurar notificaciones: alerta si un producto sube de precio > 10%
- [ ] Test: importar 1 producto, hacer pedido de prueba

### 7. Email y Notificaciones
- [ ] Configurar email de soporte (usar dominio propio, ej. hola@tutienda.com)
- [ ] Shopify Inbox: activar chat en tienda
- [ ] Configurar secuencia de emails post-compra (Make.com o Klaviyo)
- [ ] Email de carrito abandonado: activar en Shopify (gratuito) o Klaviyo

### 8. Píxeles y Analytics
- [ ] Meta Pixel: Shopify → Apps → Meta → conectar cuenta Business Manager
- [ ] Google Analytics 4: añadir ID en Shopify → Configuración → Apps y canales de ventas
- [ ] TikTok Pixel: app TikTok for Shopify (necesario antes de TikTok Ads)
- [ ] Verificar que los 3 píxeles disparan en checkout con Shopify Test Order

---

## Output

```json
{
  "tienda_id": "",
  "fecha_configuracion": "YYYY-MM-DD",
  "checklist": {
    "dominio": true,
    "pagos": true,
    "politicas": true,
    "envios": true,
    "checkout": true,
    "autods_conectado": true,
    "emails": true,
    "pixeles": {
      "meta": true,
      "google": true,
      "tiktok": true
    }
  },
  "listo_para_trafico": true,
  "notas": ""
}
```

**Regla:** `listo_para_trafico = true` solo si todos los checkboxes están marcados.
No lanzar ninguna campaña de pago hasta que los 3 píxeles estén verificados.
