# MENÚ PRINCIPAL — [MARCA]
> Pegar en Shopify Admin → Online Store → Navigation → Main Menu
> AVISO (contraste con el curso, `Q4Ykcwh5Osc`): en la estrategia de un producto / un mercado no hay catálogo ni colecciones: en 03:16:37 el menú "Catálogo" se sustituye por un enlace directo al producto. Este árbol multicategoría solo aplica si la tienda pasa a varios productos. Requisito del curso para Google/Merchant (22:10:46): la página de contacto debe estar en el menú de cabecera y en el footer.

---

## Estructura (máx. 6 items nivel 1 — criterio GEM OS, tienda multiproducto)

```
Inicio
Tienda
  ├── [CATEGORÍA 1]          ← ej. "Para el Hogar"
  ├── [CATEGORÍA 2]          ← ej. "Gadgets Tech"
  └── Más Vendidos
Ofertas
Seguimiento de Pedido
Contacto
```

---

## Configuración en Shopify

| Nombre visible | Destino (URL) | Notas |
|---|---|---|
| Inicio | `/` | |
| Tienda | `/collections/all` | dropdown activo |
| → [CATEGORÍA 1] | `/collections/[handle-1]` | submenu |
| → [CATEGORÍA 2] | `/collections/[handle-2]` | submenu |
| → Más Vendidos | `/collections/mas-vendidos` | submenu |
| Ofertas | `/collections/ofertas` | resaltar en rojo si el tema lo permite |
| Seguimiento de Pedido | `/pages/seguimiento-pedido` | |
| Contacto | `/pages/contacto` | |

---

## Reglas de GEM OS para el menú (criterio propio, no del curso)

1. **Máximo 6 items** en el nivel superior — más confunde al cliente
2. **"Más Vendidos" siempre visible** — genera prueba social automática
3. **Seguimiento de Pedido en el header** — opcional: el curso no tiene página de seguimiento; el tracking va en la política de envío y por email automático (`Q4Ykcwh5Osc` 22:14:28)
4. No enlazar páginas legales desde el header (van al footer)
5. El nombre de las categorías debe ser el **problema que resuelve**, no el nombre técnico del producto
