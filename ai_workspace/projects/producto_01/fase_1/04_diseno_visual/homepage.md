# HOMEPAGE — [MARCA]
> Shopify Admin → Online Store → Themes → Dawn → Customize → Home page
> Construir de arriba abajo en el editor de secciones

---

## Estructura de secciones (orden exacto)

```
1. [Header — ya configurado]
2. HERO — Image Banner
3. BENEFICIOS — Rich Text / Icon Columns
4. PRODUCTO ESTRELLA — Featured Product
5. PRUEBA SOCIAL — Testimonials (opcional, añadir en Fase 2)
6. [Footer — ya configurado]
```

---

## SECCIÓN 1 — HERO (Image Banner)

**Configuración en Dawn:**
- Sección: `Image Banner`
- Altura del banner: `Large` (pantalla completa en desktop)
- Adaptar imagen: Activado
- Superposición de color: Negro, opacidad 30-40%

### Copy del Hero

> Criterio GEM OS (no del curso): el hero debe responder en pocos segundos a "¿Esto es para mí?".

**Título (H1 — máx. 6 palabras):**
```
[PROBLEMA QUE RESUELVE EL PRODUCTO]
```
*Ejemplos reales:*
- "Tu hogar más inteligente, hoy."
- "Cuida a tu mascota con estilo."
- "El gadget que cambia tu rutina."

**Subtítulo (1 línea — beneficio emocional):**
```
[RESULTADO CONCRETO] sin [FRICCIÓN PRINCIPAL].
Envío en {{DIAS_ENVIO_PROVEEDOR}} días. {{GARANTIA_REAL_DE_LA_TIENDA}}.
```
*Ejemplos:*
- "Ahorra tiempo en la cocina sin complicaciones. Envío en {{DIAS_ENVIO_PROVEEDOR}} días. {{GARANTIA_REAL_DE_LA_TIENDA}}."
- "Tu mascota feliz, tú tranquilo. Envío en {{DIAS_ENVIO_PROVEEDOR}} días. {{GARANTIA_REAL_DE_LA_TIENDA}}."

**CTA (botón principal):**
```
Ver productos →
```

**Imagen del hero:**
- Fondo: imagen del producto en uso (lifestyle) o imagen del problema resuelto
- Formato: JPG, mínimo 1800×900px, comprimida a <500KB
- Si aún no tienes producto: usar imagen lifestyle del nicho (Unsplash/Pexels — gratis)

---

## SECCIÓN 2 — TRES BENEFICIOS (Icon Columns / Rich Text)

**Configuración en Dawn:**
- Sección: `Icon with text` o `Rich text` con 3 columnas
- Fondo: `[COLOR_SECUNDARIO]` (sección con fondo alterno para contraste)

### Estructura de los 3 beneficios

> **Regla:** Cada beneficio responde una objeción específica del cliente de dropshipping.

| # | Icono | Título | Subtítulo |
|---|---|---|---|
| 1 | 🚀 (o SVG flecha) | **Envío con seguimiento** | Seguimiento en tiempo real. Recibes tu pedido en {{DIAS_ENVIO_PROVEEDOR}} días laborables. |
| 2 | ⭐ (o SVG estrella) | **Calidad Verificada** | Cada producto pasa por nuestro control de calidad antes de llegar a ti. |
| 3 | 🔄 (o SVG ciclo) | **Garantía 30 Días** | Si hay cualquier problema, lo resolvemos. Sin preguntas, sin complicaciones. |

> **Nota:** Los iconos en Dawn pueden ser SVG inline o emojis. Para un look más premium, usar los iconos SVG de Heroicons (gratuitos, coherentes con Dawn).

**Alternativas por nicho:**
- Mascotas: "Productos testados", "Envío seguro para tu peludo", "30 días de garantía"
- Belleza: "Fórmulas probadas", "Envío discreto", "Resultados o reembolso"
- Gadgets: "Tecnología real", "Envío rastreado", "Soporte técnico incluido"

---

## SECCIÓN 3 — PRODUCTO ESTRELLA (Featured Product)

**Configuración en Dawn:**
- Sección: `Featured product`
- Producto: seleccionar el producto principal (o `[PRODUCTO_ESTRELLA]`)
- Media: mostrar 2-3 fotos (sin fondo + lifestyle)
- Variantes: mostrar selector si hay variantes

### Copy adicional en la ficha del producto (rellenar en `/redactar-ficha-shopify`)

La sección Featured Product en el homepage muestra automáticamente:
- Nombre del producto (título)
- Precio
- Variantes (si existen)
- Botón "Añadir al carrito"
- Descripción corta (excerpt — primeros 150 caracteres de la descripción)

**El excerpt debe ser:**
```
[BENEFICIO PRINCIPAL EN 1 FRASE]. [DATO CONCRETO O GARANTÍA].
```
*Ejemplo de estructura: "{{BENEFICIO_SEGUN_PROVEEDOR}}. {{GARANTIA_REAL_DE_LA_TIENDA}}."*

---

## Configuración del botón "Añadir al carrito"

En Dawn → Theme Settings → Colors:
- Botones: `[COLOR_PRIMARIO]`
- Texto del botón: "Añadir al carrito" (default de Shopify en español)

Para cambiar el texto: Online Store → Themes → Actions → Edit languages → buscar "Add to cart"

---

## Vista móvil — checklist

> El 70-80% del tráfico de dropshipping llega en móvil. Revisar siempre.

- [ ] Hero: título legible en móvil (mínimo 28px), botón accesible con el pulgar
- [ ] Beneficios: apilados verticalmente (no 3 columnas horizontales)
- [ ] Producto estrella: imagen ocupa el ancho completo
- [ ] Velocidad: cargar la homepage en 4G → debe abrir en <3 segundos

---

## Checklist completo

- [ ] Hero creado con imagen, título y subtítulo (días de envío = los reales del proveedor)
- [ ] 3 beneficios configurados con íconos
- [ ] Producto estrella seleccionado y conectado
- [ ] Vista móvil revisada y correcta
- [ ] Paleta de colores aplicada (`paleta_marca.md`)
- [ ] Homepage publicada (botón "Save" en el editor)
