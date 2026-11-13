---
name: buscar-producto
description: "Descubre candidatos en AutoDS Trending + Ad Spy + Shopify Analytics. Usar cuando el usuario hable de: buscar producto, trending, viral, qué vender, producto ganador."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/buscar-producto.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

# Skill: Buscar Productos Ganadores

Descubre candidatos aplicando los 5 criterios de producto ganador.

Fuente: `qgK3GfY5ZC4` 08:00–12:00 — ratio real **1.000 explorados → 50 seleccionados
(5%)** en 10–15 minutos.

---

## Vía preferente: MCP oficial de AutoDS

AutoDS publicó un conector MCP. Con él, Claude navega los 8M de productos del
catálogo y **publica directo en Shopify**, sin scraping.

### Configuración (una vez)

1. En Claude: **Personalizar → Conectores → Añadir conector personalizado**
2. Conectar e iniciar sesión en AutoDS
3. Activar **modo colaborar** antes de lanzar la búsqueda

Si el conector no está disponible en esta sesión, díselo al usuario y usa la vía
alternativa de abajo. No simules resultados de un MCP que no responde.

### Prompt de búsqueda

```
Explora el catálogo de AutoDS buscando productos que cumplan estos 5 criterios:

1. Resuelve un problema real — prioriza salud, belleza y cuidado personal
2. No se consigue en tiendas convencionales del barrio
3. Potencial x3 sobre coste landed (producto + envío); pequeño y ligero
4. Ya se está vendiendo: busca demanda probada con pocos competidores
5. Envío disponible en 10 días o menos

Explora alrededor de 1.000 productos y selecciona los 50 mejores.
Para cada uno dame: coste producto, coste envío, PVP sugerido, nº de ventas,
nº de competidores, plazo de envío y una nota 0-100.
Ordena por nota descendente.
```

---

## Vía alternativa (sin MCP)

AutoDS Trending + Meta Ad Library + Shopify Analytics, según
`referencias/buscar_producto.md`. Mismo criterio de salida.

---

## Filtro obligatorio antes de entregar

Cada candidato pasa por el validador con **coste landed**, no con el coste de
producto suelto:

```python
from app.services.financial_validator import FinancialValidator
v = FinancialValidator()
r = v.validar_producto(sku, costo_origen=coste, costo_envio=envio,
                       pvp_sugerido=pvp, moneda_costo="USD", moneda_pvp="EUR")
```

Se descarta en el acto todo lo que esté por debajo de 2× sobre landed, y todo lo
que lleve baterías de litio sueltas.

---

## Output

```
BÚSQUEDA — [nicho o criterio]

Explorados: N    Seleccionados: M    (ratio X%)

 #  Producto              Nicho      Landed   PVP     Mult   Ventas  Comp  Nota
 1  [nombre]              belleza    $7,00    $30     4,29×  500     1     89
 2  [nombre]              salud      $9,50    $35     3,68×  320     3     81
 ...

Descartados por regla 2x:        N
Descartados por baterías litio:  N

Siguiente paso: /clasificar-producto sobre los 5 primeros,
luego /refutar-producto antes de invertir.
```

---

## Perfil objetivo

La ficha de referencia del vídeo (11:30): **$5 producto + $2 envío, PVP $30,
500 ventas, 1 competidor, envío 10 días**. Demanda probada sin saturación.

Un producto con 5.000 ventas y 40 competidores no es una oportunidad: es un
mercado ya repartido.
