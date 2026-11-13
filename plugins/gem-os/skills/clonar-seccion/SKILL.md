---
name: clonar-seccion
description: "HTML de la competencia → Liquid con variables de Shopify. Usar cuando el usuario hable de: clonar sección, HTML competencia, Liquid shopify."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/clonar-seccion.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

# Skill: Clonar Sección de la Competencia a Liquid

Convierte una sección de una tienda que ya funciona en código Liquid para Shopify.

Fuente: `rqMrq2MGdpw` — así clonó los badges de stock bajo y las secciones de
confianza de su competidor.

---

## Qué necesito del usuario

1. **El HTML de la sección** — en el navegador: clic derecho sobre la sección →
   Inspeccionar → clic derecho en el `<div>` contenedor → Copy → Copy outerHTML
2. **Captura de pantalla** de cómo se ve (opcional pero ayuda con el estilo)
3. **Qué parte quieres**: la estructura, el estilo, o ambos

Si no hay HTML → `DATA_GAP_REQUEST`.

---

## Proceso

### 1. Analizar lo que hace la sección
Antes de escribir código, identificar **por qué funciona**:
- ¿Qué objeción del cliente resuelve?
- ¿Es urgencia, prueba social, garantía, comparativa?
- ¿Qué dato variable muestra (stock, reseñas, plazo)?

### 2. Separar contenido de estructura
El HTML copiado trae el contenido del competidor. Se conserva la estructura y el
patrón; el texto y los datos se reemplazan por los del producto propio.

### 3. Convertir a Liquid
Los valores fijos pasan a variables de Shopify:

```liquid
{%- comment -%} Badge de stock bajo {%- endcomment -%}
{%- if product.available and product.selected_or_first_available_variant.inventory_quantity < 20 -%}
  <div class="stock-badge">
    Quedan {{ product.selected_or_first_available_variant.inventory_quantity }} unidades
  </div>
{%- endif -%}
```

Las clases CSS se renombran con prefijo propio para no colisionar con el tema.

### 4. Pasar por el gate
El texto de la sección es copy comercial. Se verifica como cualquier otro:

```python
from app.services.deterministic_gate import verificar_copy
verificar_copy(texto_de_la_seccion)
```

Un badge de urgencia copiado puede traer superlativos o promesas de envío que
el gate rechaza.

---

## Output

```
SECCIÓN CLONADA — [nombre]

Qué resuelve:  [objeción que ataca]
Patrón:        urgencia | prueba social | garantía | comparativa

--- Liquid ---
[código listo para pegar en la plantilla]

--- CSS ---
[estilos con prefijo propio]

Dónde va:      sections/[archivo].liquid, o dentro de product-template
Variables:     [listado de datos de Shopify que usa]
Gate:          PASS / FAIL + violaciones
```

---

## Límites

Se copia el **patrón**, no el contenido. Reproducir textos, imágenes o la marca
del competidor es otra cosa, y no se hace aquí.

Si la sección muestra datos que la tienda no tiene (reseñas reales, unidades
vendidas), no se inventan: o se conecta la fuente real, o la sección no se usa.
