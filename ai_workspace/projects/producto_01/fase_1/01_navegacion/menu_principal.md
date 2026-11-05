# MENÚ PRINCIPAL — [MARCA]
> Pegar en Shopify Admin → Online Store → Navigation → Main Menu

---

## Estructura (máx. 6 items nivel 1 — metodología Adrián Sáenz)

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

## Reglas de Adrián Sáenz para el Menú

1. **Máximo 6 items** en el nivel superior — más confunde al cliente
2. **"Más Vendidos" siempre visible** — genera prueba social automática
3. **Seguimiento de Pedido en el header** — reduce tickets de soporte hasta un 40%
4. No enlazar páginas legales desde el header (van al footer)
5. El nombre de las categorías debe ser el **problema que resuelve**, no el nombre técnico del producto
