# Skill: /autods-notas — Notas para Proveedores AutoDS

Genera notas profesionales en inglés para enviar a proveedores chinos a través de AutoDS.

## Índice de notas disponibles

| # | Nota | Cuándo usar |
|---|------|------------|
| 1 | Dropshipping Declaration | Primer pedido con proveedor nuevo — SIEMPRE |
| 2 | Packaging Instructions | Cuando el packaging importa o producto frágil |
| 3 | Invoice & Price Removal | Siempre en AliExpress — sin excepción |
| 4 | Quality Control Request | Productos con alto riesgo de devolución |
| 5 | Shipping Speed & Tracking | Cuando el carrier o velocidad importa |
| 6 | Return & Dispute Policy | Establecer expectativas desde el primer pedido |
| 7 | Partnership Introduction | Primer contacto con proveedor nuevo |

## Instrucciones de ejecución

1. Muestra el índice al usuario.
2. Pregunta: "¿Qué nota necesitas? Escribe el número o descripción. Puedes pedir varias."
3. Para la nota seleccionada, identifica las variables requeridas:
   - `{ORDER_ID}`, `{PRODUCT_NAME}`, `{VARIANT_DETAILS}`, `{DESTINATION_COUNTRY}`, `{ITEM_ID}`, `{TARGET_MARKETS}`
4. Pide al usuario los valores de las variables. Si el usuario no tiene un dato:
   - Dejar el placeholder `{VARIABLE}` en la nota final
   - Indicar con **[COMPLETAR: descripción]** junto al placeholder
5. Muestra la nota final en un bloque de código copiable.
6. Ofrece: "¿Quieres combinar varias notas en un solo mensaje para el proveedor?"

## Reglas importantes

- **Los mensajes son en inglés** — proveedores chinos leen mejor inglés que español.
- **Nunca inventar ORDER_ID ni PRODUCT_NAME** — preguntar al usuario si no los tiene.
- **Para pedidos reales**: confirmar ORDER_ID con el usuario antes de generar la nota.
- **Combinación de notas**: si el usuario pide varias, unirlas con una sola línea de separación `---`.

## Ejemplo de uso típico (primer pedido)

Usuario pide Note 1 + Note 3. Respuesta esperada:

```
Subject: Important — Dropshipping Order Instructions & Invoice Policy

[Contenido de Note 1]

---

[Contenido de Note 3]
```

## Referencia completa de templates

`ai_workspace/templates/autods_supplier_notes.md`
