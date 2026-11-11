# Ficha Producto — Primer Producto
> producto_01 · Fase 2 · Módulo 02
> Generado con `/redactar-ficha-shopify`

---

## Datos de entrada (completar antes de ejecutar el skill)

| Campo | Valor |
|-------|-------|
| Nombre producto | `[NOMBRE_PRODUCTO]` |
| Categoría | `[CATEGORIA]` |
| Costo origen (USD) | `[COSTO_ORIGEN]` |
| PVP propuesto (USD) | `[PVP]` ← validar con `/validar-financiero` |
| Peso (kg) | `[PESO_KG]` |
| Material | `[MATERIAL]` |
| Dimensiones | `[DIMENSIONES]` |

---

## Output esperado tras ejecutar `/redactar-ficha-shopify`

### Título SEO
`[TITULO_SEO]` (< 60 caracteres)

### Meta descripción
`[META_DESCRIPCION]` (< 160 caracteres, incluye keyword principal)

### Descripción AIDA (HTML Shopify)

```html
<!-- ATENCIÓN -->
<h2>[TITULO_ATENCION]</h2>

<!-- INTERÉS -->
<ul>
  <li><strong>[BENEFICIO_1]:</strong> [EXPLICACION_1]</li>
  <li><strong>[BENEFICIO_2]:</strong> [EXPLICACION_2]</li>
  <li><strong>[BENEFICIO_3]:</strong> [EXPLICACION_3]</li>
</ul>

<!-- DESEO -->
<p>[GARANTIA_REAL]</p>

<!-- ACCIÓN -->
<p><strong>[CTA]</strong></p>
```

### Especificaciones técnicas
> No alterar datos del proveedor

| Especificación | Valor |
|----------------|-------|
| Material | `[MATERIAL]` |
| Peso | `[PESO_KG]` kg |
| Dimensiones | `[DIMENSIONES]` |
| Origen | `[PAIS_ORIGEN]` |

---

## Checklist multiplicador

- [ ] PVP ≥ 2× coste landed (mínimo) y, si es posible, 3× → calculado con `/validar-financiero`
- [ ] Margen neto positivo tras fees 4,0 % y cancelaciones 10,1 %
- [ ] Sin superlativos vacíos en el copy
- [ ] Tiempo de envío: "{{DIAS_ENVIO_PROVEEDOR}} días laborables" (real del proveedor)
