---
name: refutar-producto
description: "8 intentos de demoler la tesis antes de invertir (método Pavel: 74 tests para refutarse). Usar cuando el usuario hable de: refutar, demoler tesis, 8 intentos, método Pavel."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/refutar-producto.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

# Skill: Refutar un Producto Ganador

Antes de invertir en pauta, intenta **demostrar que el producto no funciona**.

Fuente: `1tzz17YDtz8` 13:18 — Pavel Rapsevich encontró un candidato a planeta
analizando 126.000 estrellas, y acto seguido programó **74 tests distintos para
refutar su propia hipótesis**. No buscaba confirmarla: buscaba romperla.

---

## Por qué

El clasificador puntúa un producto como HOT y el pipeline sigue adelante. Todo
el sistema está construido para **confirmar** que el producto es bueno: busca
señales positivas y las suma.

Este skill hace lo contrario. Parte de la premisa de que el producto va a
fracasar e intenta encontrar la razón. Si no la encuentra, la tesis sobrevive.

---

## Qué necesito

La clasificación completa del producto (output de `/clasificar-producto`) con
su score, criterios y datos de competencia.

---

## Las 8 refutaciones

Cada una es un intento de matar la tesis. Respóndelas con datos, no con opinión.

### 1. El margen no aguanta los costes reales
Recalcular con coste landed, fees (4%) y cancelaciones (10,1%). ¿El neto sigue
siendo positivo con un CPA realista?
→ **Refutado si** el neto por unidad no cubre el CPA esperado.

### 2. La demanda es estacional y vamos tarde
¿Las ventas del competidor son de temporada? ¿En qué punto de la curva estamos?
→ **Refutado si** el pico ya pasó.

### 3. Está más saturado de lo que parece
El dato de "1 competidor" suele ser de un solo ad spy. Buscar en TikTok, Meta
Ad Library y AliExpress por separado.
→ **Refutado si** aparecen >5 anunciantes activos con el mismo ángulo.

### 4. El producto genera devoluciones
Productos frágiles, con tallas, electrónicos o que dependen de expectativa
visual tienen tasas de devolución por encima del 10,1% de referencia.
→ **Refutado si** la categoría es propensa a devolución.

### 5. El envío mata la conversión
Plazo real del proveedor vs. lo que espera el mercado objetivo.
→ **Refutado si** el plazo supera 15 días en un mercado acostumbrado a 3.

### 6. Hay una barrera legal o aduanera
Baterías, cosmética, suplementos, productos eléctricos con certificación,
imitaciones de marca.
→ **Refutado si** requiere certificación que no tenemos.

### 7. El wow factor no sobrevive al vídeo
El producto puede ser bueno y no ser **demostrable en 3 segundos**. Si el
beneficio no se ve, no hay hook.
→ **Refutado si** no se puede mostrar el antes/después visualmente.

### 8. El competidor gana por algo que no podemos copiar
Marca establecida, exclusividad con el proveedor, stock local con entrega en 48h.
→ **Refutado si** su ventaja es estructural.

---

## Veredicto

| Refutaciones que pasan | Acción |
|------------------------|--------|
| 0 | **Invertir** — la tesis aguanta |
| 1–2 | Invertir con el presupuesto test de 15 €/día y vigilar justo esa debilidad |
| 3+ | **Descartar** — buscar otro producto |
| Cualquier refutación de tipo 1 o 6 | **Descartar** sin más análisis |

Las refutaciones 1 (margen) y 6 (legal) son eliminatorias por sí solas: una
destruye la rentabilidad y la otra puede costar la cuenta.

---

## Output

```
REFUTACIÓN — [producto]

  #  Refutación                      Veredicto   Evidencia
  1  Margen no aguanta costes        SOBREVIVE   neto X,XX €/ud vs CPA estimado X €
  2  Estacionalidad                  SOBREVIVE   ...
  3  Saturación oculta               REFUTADO    7 anunciantes activos en Meta
  ...

Refutaciones que pasan: N de 8
VEREDICTO: invertir | invertir con cautela | descartar

Si se invierte, vigilar especialmente: [las que estuvieron cerca de refutar]
```

---

Si falta un dato para evaluar una refutación, **no la des por superada**:
márcala como "sin datos" y cuenta como refutación pendiente.
