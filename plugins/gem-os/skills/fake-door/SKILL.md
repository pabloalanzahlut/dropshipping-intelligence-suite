---
name: fake-door
description: "Mide demanda real sin stock ni ads — pop-up de captura en vez de checkout. Usar cuando el usuario hable de: fake door, medir demanda, sin stock, pop-up captura."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/fake-door.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

# Skill: Validar Demanda con Fake Door

Mide si un producto interesa **antes de comprar stock o gastar en ads**.

Fuente: `LycpBgBiWKw` — montó 8 funciones premium que no existían; al pulsarlas
aparecía un pop-up pidiendo email a cambio de 50% de descuento. **2 de las 8
captaron el 83% de los clicks.** Desarrolló solo esas dos.

---

## Qué es

Publicas el producto en la tienda como si existiera. Cuando alguien pulsa
"Comprar", en vez del checkout aparece:

> **Agotado temporalmente.** Déjanos tu email y te avisamos en cuanto vuelva —
> con un 20% de descuento por la espera.

Nadie paga. Nadie recibe nada. Mides intención de compra real con tráfico real,
sin inventario ni riesgo de contracargo.

---

## Qué necesito del usuario

- Entre 4 y 8 productos candidatos (salidos de `/clasificar-producto`)
- Presupuesto de tráfico para el test
- Plazo del test (recomendado: 5–7 días)

Si falta → `DATA_GAP_REQUEST`.

---

## Proceso

### 1. Preparar las fichas
Una ficha por candidato, con `/redactar-ficha-shopify`. Mismo nivel de calidad en
todas: si una está mejor escrita, mides el copy y no el producto.

### 2. Sustituir el botón de compra
El botón dispara el modal de captura en vez del checkout. En Shopify se hace
marcando el producto sin inventario y poniendo un formulario de Klaviyo en la
plantilla de producto agotado.

```liquid
{% unless product.available %}
  <div class="notify-form" data-product="{{ product.handle }}">
    <!-- formulario Klaviyo con el handle como propiedad -->
  </div>
{% endunless %}
```

### 3. Repartir el tráfico
Partes iguales a cada candidato. Sin favoritos: el objetivo es que los datos
decidan, no la intuición.

### 4. Medir

| Métrica | Qué indica |
|---------|-----------|
| **Clicks en comprar / visitas** | intención de compra — la señal principal |
| **Emails capturados / clicks** | cuánto aguanta la fricción |
| Tiempo en la ficha | interés genuino vs. rebote |

El reparto desigual es el hallazgo. Si un producto se lleva el 40% de los clicks
con el 12% del tráfico, ese es el que va a producción.

---

## Umbral de decisión

| Resultado | Acción |
|-----------|--------|
| ≥2× la tasa de click media del grupo | **Producir** — pedir stock, lanzar campaña |
| En la media | Repetir con otro creativo antes de descartar |
| <0,5× la media | Descartar |

---

## Output

```
FAKE DOOR — resultados tras N días

Producto              Visitas   Clicks   CTR     Emails   Veredicto
[nombre]              XXX       XX       X,X%    XX       PRODUCIR
[nombre]              XXX       XX       X,X%    XX       repetir
...

Concentración: los N primeros captaron el XX% de los clicks
Coste del test: XX € (solo tráfico, sin stock)
```

---

## Límites

- Avisa siempre de que está agotado. Prometer una fecha de entrega que no existe
  sí es engañoso y puede costarte la pasarela.
- Los emails capturados crean una expectativa: si decides no producir, hay que
  escribirles. Klaviyo sirve para eso.
- No sirve para medir precio, solo interés. El precio se valida después.
