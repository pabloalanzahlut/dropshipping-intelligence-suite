# Skill: Dropshipping en Amazon

**ID:** `amazon_dropshipping`
**Versión:** 1.0.0
**Fuente:** Adrián Sáenz `Q4Ykcwh5Osc 25:50:07`
**Propósito:** Configurar y operar dropshipping en Amazon como canal adicional a Shopify: proveedor, producto, envíos, devoluciones y conexión con AutoDS.

**Posición en el pipeline:** Canal paralelo a Shopify — no reemplaza la tienda propia.
**Ventaja:** Amazon aporta tráfico propio sin inversión en ads.
**Desventaja:** Márgenes más ajustados (fees Amazon ≈ 15%) y dependencia de la plataforma.

---

## Fase 1 — Conseguir Proveedor para Amazon (Adrián `25:53:00`)

### Requisitos del proveedor para Amazon (más estrictos que Shopify)
- Tiempo de envío: **máximo 3-5 días hábiles** (Amazon penaliza entregas lentas)
- Tracking número: obligatorio para cada pedido
- Tasa de cancelación: <2.5% (Amazon suspende la cuenta si se supera)
- Tasa de pedidos defectuosos: <1%

### Proveedores compatibles con Amazon Dropshipping
| Proveedor | Tiempo envío | Compatible AutoDS | Notas |
|-----------|-------------|-------------------|-------|
| Amazon mismo (arbitraje) | 1-3 días Prime | ✅ | Margen muy bajo |
| Walmart | 2-5 días US | ✅ | Solo mercado US |
| CJ Dropshipping | 5-10 días | ✅ | Mejor para EU |
| Spocket (proveedores UE) | 2-5 días EU | ✅ | Más caro, margen menor |

**Regla:** para Amazon, priorizar proveedores con almacén en el mismo país del cliente.

---

## Fase 2 — Elegir Producto para Amazon (Adrián `25:56:20`)

### Criterios adicionales vs. Shopify
- **BSR (Best Seller Rank):** buscar nichos con BSR entre 10.000-100.000 en la categoría
  - BSR < 1.000 = alta competencia, difícil entrar
  - BSR > 500.000 = poca demanda
- **Número de reseñas del líder:** <500 reseñas = nicho accesible
- **Precio de venta:** €20-80 (debajo de €20 los fees de Amazon se comen el margen)
- **Prohibido en Amazon dropshipping:** artículos con marca registrada, electrónica con certificaciones especiales, alimentos, medicamentos

### Herramienta de investigación: Jungle Scout o Helium 10
- Validar BSR histórico (evitar productos estacionales si no es temporada)
- Verificar que la Buy Box no está dominada por Amazon mismo

### Regla financiera en Amazon
```
Precio de venta Amazon
- Fee Amazon: ~15% del PVP
- Fee cierre: €0,99/unidad (plan individual) o incluido (plan profesional €39/mes)
- Coste del producto (proveedor)
- Envío proveedor → cliente
= Beneficio neto

Mínimo viable: beneficio neto ≥ 20% del PVP
```

---

## Fase 3 — Configurar Envíos (Adrián `26:02:28`)

### Configuración en Amazon Seller Central
1. Seller Central → Configuración → Ajustes de envío
2. Crear plantilla de envío para dropshipping:
   - Tiempo de tránsito: usar el tiempo real del proveedor (no mentir)
   - Tiempo de procesamiento: 1-2 días hábiles
3. **NO activar Prime** si usas dropshipping externo (penalización por incumplimiento)
4. Países de envío: solo donde tu proveedor puede llegar en los plazos prometidos

---

## Fase 4 — Configurar Devoluciones (Adrián `26:04:13`)

Amazon tiene política de devoluciones de **30 días** sin preguntas (obligatoria).

### Flujo de devolución en dropshipping
1. Cliente solicita devolución en Amazon
2. Amazon notifica al vendedor
3. Opciones (en orden de preferencia):
   - **Reembolso sin devolución** (si el producto es de bajo coste — evita coste logístico)
   - **Devolución a almacén propio** (si tienes dirección en el país del cliente)
   - **Devolución al proveedor** (solo si el proveedor lo acepta)
4. Tiempo límite para procesar: 48h desde la solicitud

**Presupuestar 10,1% de devoluciones/cancelaciones** (dato P&L Adrián `rqMrq2MGdpw`).

---

## Fase 5 — Conectar Amazon con AutoDS (Adrián `26:06:23` – `26:10:45`)

1. AutoDS → Configuración → Tiendas → Añadir tienda → Amazon Seller
2. Autorizar con credenciales de Amazon Seller Central (MWS o SP-API)
3. Importar productos desde AutoDS → Amazon:
   - AutoDS gestiona automáticamente el inventario y precios
   - Si el proveedor sube el precio → AutoDS actualiza el listing en Amazon
4. Configurar fulfillment automático:
   - Cuando llega un pedido en Amazon → AutoDS lo procesa con el proveedor
   - El número de tracking se sube automáticamente a Amazon (obligatorio)
5. Configurar alertas:
   - Alerta si el proveedor se queda sin stock (pausar listing automáticamente)
   - Alerta si el precio del proveedor sube >15% (revisar margen)

---

## Métricas de Salud de la Cuenta Amazon

Revisar en Seller Central → Salud de la cuenta:

| Métrica | Umbral mínimo | Consecuencia si falla |
|---------|--------------|----------------------|
| Tasa de pedidos defectuosos | <1% | Suspensión de cuenta |
| Tasa de cancelación | <2,5% | Restricción de ventas |
| Tasa de envíos tardíos | <4% | Degradación en resultados |
| Tiempo de respuesta al cliente | <24h | Impacto en métricas de vendedor |

---

## Output JSON de operación

```json
{
  "asin": "",
  "producto": "",
  "proveedor": "",
  "precio_amazon": 0.00,
  "fee_amazon_pct": 15.0,
  "coste_landed": 0.00,
  "beneficio_neto": 0.00,
  "bsr_categoria": 0,
  "autods_conectado": true,
  "fulfillment_automatico": true,
  "estado_cuenta": "saludable | advertencia | restringida"
}
```
