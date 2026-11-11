# Comparador (Nosotros vs. Opción Genérica)
> producto_01 · Fase 2 · Módulo 04
> Pegar en: página de producto, debajo de la ficha AIDA
> Equivale a: "Constructor de Comparador" del documento complementario

> ⚠️ No comparar por nombre contra un competidor real/marca registrada — riesgo de publicidad comparativa ilegal. Usar siempre "Opción genérica"/"Alternativa habitual del mercado".

```html
<section style="padding:40px 16px; max-width:600px; margin:0 auto;">
  <h2 style="text-align:center; margin-bottom:24px;">¿Por qué elegir [MARCA]?</h2>
  <table style="width:100%; border-collapse:collapse; font-size:14px;">
    <thead>
      <tr>
        <th style="padding:12px; text-align:left; border-bottom:2px solid [HEX_SECUNDARIO];"></th>
        <th style="padding:12px; border-bottom:2px solid [HEX_SECUNDARIO];">[MARCA]</th>
        <th style="padding:12px; border-bottom:2px solid #ddd; opacity:.6;">Opción genérica</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td style="padding:12px;">[CRITERIO_1]</td>
        <td style="padding:12px; text-align:center;">✅ [VALOR_1_MARCA]</td>
        <td style="padding:12px; text-align:center; opacity:.6;">❌ [VALOR_1_GENERICO]</td>
      </tr>
      <tr>
        <td style="padding:12px;">[CRITERIO_2]</td>
        <td style="padding:12px; text-align:center;">✅ [VALOR_2_MARCA]</td>
        <td style="padding:12px; text-align:center; opacity:.6;">❌ [VALOR_2_GENERICO]</td>
      </tr>
      <tr>
        <td style="padding:12px;">Envío</td>
        <td style="padding:12px; text-align:center;">✅ Rastreado, {{DIAS_ENVIO_PROVEEDOR}} días</td>
        <td style="padding:12px; text-align:center; opacity:.6;">❌ Sin seguimiento</td>
      </tr>
      <tr>
        <td style="padding:12px;">Garantía</td>
        <td style="padding:12px; text-align:center;">✅ Devolución 30 días</td>
        <td style="padding:12px; text-align:center; opacity:.6;">❌ No especificada</td>
      </tr>
    </tbody>
  </table>
</section>
```

---

## Notas de Implementación

- `[CRITERIO_1/2]` y sus valores deben basarse en especificaciones **reales** del producto, tomadas de [../02_producto/ficha_shopify.md](../02_producto/ficha_shopify.md) — no inventar ventajas no verificables.
- Las filas de Envío y Garantía ya están fijadas según las políticas de Fase 1 (`envio_entrega.md`, `politica_reembolso.md`) — no deben contradecirlas.
- No usar superlativos ("el mejor del mercado") ni afirmaciones absolutas no demostrables.
