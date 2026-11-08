# Skill: Construir Oferta Multi-Unidad

Diseña la estructura de oferta que sube el ticket medio sin tocar el precio unitario.

Fuente: `rqMrq2MGdpw` — caso real con ticket medio de **75,93 €**.

---

## El patrón que funcionó

| Oferta | PVP | Unidades entregadas | Coste real |
|--------|-----|---------------------|------------|
| Principal | $79 | **1+1 gratis** = 2 uds | 14,50 € |
| Upsell | ~$119 | **2+2 gratis** = 4 uds | 22,50 € |

El "gratis" no lo es: el coste de ambas unidades está dentro del precio. Lo que
compra el cliente es la sensación de volumen, y lo que gana la tienda es ticket
medio sin aumentar el coste de adquisición.

---

## Qué necesito del usuario

- Coste landed por unidad (producto + envío)
- Divisa del coste y divisa de venta
- Precio de referencia de la competencia, si lo hay

Si falta → `DATA_GAP_REQUEST`.

---

## Proceso

### 1. Verificar que la oferta aguanta el multiplicador

El multiplicador se mide sobre el **coste landed total de las unidades entregadas**,
no sobre una sola:

```
Oferta 1+1 → coste = landed × 2
Oferta 2+2 → coste = landed × 4
```

Una oferta 1+1 a $79 con landed de $7 por unidad son $14 de coste → **5,6×**. Correcto.
La misma oferta a $25 serían 1,78× → por debajo del mínimo, **rechazar**.

```python
from app.services.financial_validator import FinancialValidator
v = FinancialValidator()
v.validar_producto(sku, costo_origen=coste*2, costo_envio=0, pvp_sugerido=precio_oferta)
```

### 2. Construir los tres escalones

| Escalón | Estructura | Rol |
|---------|-----------|-----|
| Entrada | 1 unidad | ancla de precio — hace ver cara la unidad suelta |
| **Principal** | **1+1 gratis** | el que debe convertir |
| Upsell | 2+2 gratis | sube el ticket en el checkout |

El escalón de entrada existe para que el principal parezca la opción sensata.

### 3. Validar cada escalón

Los tres pasan por el validador. Si el upsell no llega a 2× sobre su coste total,
se descarta: un upsell que no deja margen solo añade riesgo logístico.

---

## Output

```
OFERTA — [producto]

Coste landed/ud:  X,XX €    (divisa origen → venta al tipo del día)

  Entrada    1 ud        XX,XX €   mult X,XX×   neto X,XX €
  PRINCIPAL  1+1 gratis  XX,XX €   mult X,XX×   neto X,XX €   ← convierte
  Upsell     2+2 gratis  XX,XX €   mult X,XX×   neto X,XX €

Ticket medio estimado: XX,XX €
Veredicto por escalón: validado / rechazado

Riesgo logístico: entregar N unidades por pedido multiplica el peso del envío
y la exposición a cancelaciones (10,1% en el P&L de referencia).
```

---

## Advertencia

Escalar una oferta multi-unidad multiplica las unidades que el almacén debe mover.
En el caso de referencia las cancelaciones se dispararon **porque el almacén no
absorbió la escalada**. Antes de lanzar 2+2, confirmar stock con el proveedor.
