# MENÚ FOOTER — [MARCA]
> Pegar en Shopify Admin → Online Store → Navigation → Footer Menu

---

## Estructura (3 columnas)

```
AYUDA                    LEGAL                      EMPRESA
─────────────────────    ────────────────────────   ─────────────────────
Preguntas Frecuentes     Política de Reembolso      Sobre Nosotros
Seguimiento de Pedido    Términos del Servicio       [MARCA] en Redes
Contacto                 Envío y Entrega            
                         Aviso Legal
```

---

## Configuración en Shopify

**Columna AYUDA**
| Nombre | URL |
|---|---|
| Preguntas Frecuentes | `/pages/faq` |
| Seguimiento de Pedido | `/pages/seguimiento-pedido` |
| Contacto | `/pages/contacto` |

**Columna LEGAL**
| Nombre | URL |
|---|---|
| Política de Reembolso | `/policies/refund-policy` |
| Términos del Servicio | `/policies/terms-of-service` |
| Envío y Entrega | `/policies/shipping-policy` |
| Aviso Legal | `/pages/aviso-legal` |

**Columna EMPRESA**
| Nombre | URL |
|---|---|
| Sobre Nosotros | `/pages/sobre-nosotros` |

---

## Pasos exactos para aplicarlo en Shopify Admin

No tengo acceso de escritura a la navegación de tu tienda (el token API conectado solo tiene scopes de productos/pedidos/inventario, no `write_online_store_navigation`), así que esto lo pegas tú:

1. **Shopify Admin → Online Store → Navigation**
2. Abre el menú **"Footer"** (si no existe, créalo con el handle `footer`)
3. Click **Add menu item** por cada fila de las 3 tablas de arriba:
   - Name: el texto de la columna "Nombre"
   - Link: pega la URL de la columna "URL" (Shopify te deja buscar la página/policy directamente, no hace falta escribir la ruta a mano)
4. Para que las 3 columnas se vean separadas, usa el menú que tu tema soporte para footer de varias columnas (en Dawn: **Theme Customize → Footer → Menu**, puedes añadir hasta 3 bloques de menú — crea 3 menús separados: `footer-ayuda`, `footer-legal`, `footer-empresa`, o agrúpalos como sub-items de un único menú "Footer" si tu tema no soporta multi-columna)
5. **Verifica en vivo:** abre la tienda publicada y confirma que los 4 enlaces LEGAL (Reembolso, Términos, Envío, Aviso Legal) aparecen y cada uno carga la página correcta (no 404)

---

## Notas

- Las políticas legales deben estar en `/policies/` (nativo de Shopify) para que aparezcan en el checkout automáticamente
- El footer es donde el cliente busca confianza — las 3 columnas cubren sus 3 preguntas clave: "¿Me ayudáis?", "¿Estáis protegidos legalmente?", "¿Quiénes sois?"
- Incluir el logo de la marca en el footer (el tema lo gestionará)
