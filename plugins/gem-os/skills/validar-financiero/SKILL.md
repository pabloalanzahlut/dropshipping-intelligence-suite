---
name: validar-financiero
description: "Valida márgenes 3x y reglas logísticas. Usar cuando el usuario hable de: validar margen, margen, 3x, 2x, coste landed, precio venta."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/validar-financiero.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

# Skill: Validación Financiera de Producto

Ejecuta la validación financiera completa de un producto según las reglas inmutables de GEM OS.

Lee `referencias/validar_financiero.md` y aplícalo.

## Input requerido:
- Costo de origen (CO) del proveedor
- Coste de envío del proveedor al cliente
- Precio de venta sugerido (PVP)
- ¿Contiene baterías de litio sueltas? (sí/no)

Si alguno falta → preguntar al usuario (`DATA_GAP_REQUEST`). El envío nunca se estima.
El peso es un dato del proveedor: se muestra, no valida (el curso no fija límite).

## Cálculos obligatorios:

```
Coste landed  = costo_origen + envío
Multiplicador = PVP / coste landed
Margen bruto  = (PVP - coste landed) / PVP × 100  (informativo: el curso no fija umbral)
Margen neto/unidad = PVP - coste landed - PVP × 4,0 % - PVP × 10,1 %
```

## Reglas de validación:

| Criterio | Umbral | Resultado si falla |
|----------|--------|-------------------|
| Multiplicador mínimo (sobre coste landed) | ≥ 2.0 | ❌ RECHAZAR |
| Multiplicador objetivo | ≥ 3.0 | ⚠️ ADVERTIR |
| Coste de origen | $5–15 | ⚠️ ADVERTIR fuera de rango |
| Baterías litio sueltas | No | ❌ RECHAZAR categoría |

## Output:

```
✅ APROBADO / ❌ RECHAZADO / ⚠️ CONDICIONAL

Multiplicador: X.X sobre coste landed (mínimo 2.0 · objetivo 3.0)
Margen neto/unidad: $X.XX tras fees 4,0 % y cancelaciones 10,1 %
Logística: OK / PROBLEMA (baterías de litio sueltas)

Veredicto: [explicación]
```

**Referencia:** `reglas-gem-os/reglas-financieras.md`
