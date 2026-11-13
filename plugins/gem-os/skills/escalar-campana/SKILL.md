---
name: escalar-campana
description: "Decide si escalar, mantener, optimizar o cortar campaña con reglas cuantitativas (Nivel 5→6). Usar cuando el usuario hable de: escalar campaña, subir presupuesto, cortar campaña."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/escalar-campana.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

# /escalar-campana

Lee `referencias/escalar_campana.md` y decide si escalar, mantener, optimizar o cortar la campaña.

## Conectores a activar automáticamente
- **Google Sheets**: leer métricas actuales de la campaña desde Dashboard tab "ROAS_Diario". Si el usuario pega datos, escribirlos en el Dashboard con `update_values`.
- **Stripe**: verificar revenue real con `stripe_analytics` antes de tomar decisión de escalado — nunca escalar basándose solo en el ROAS declarado por la plataforma de ads

## Skills Claude a cargar
- `dataviz` → generar árbol de decisión visual o gráfico de tendencia de ROAS
- `artifact-design` → si se genera reporte de decisión de escalado como artefacto

## Árbol de decisión rápido
```
ROAS ≥ 3 + tendencia estable 3 días → ESCALAR +20% presupuesto
ROAS 2-3 + estable → MANTENER y optimizar creativos
ROAS < 2 → ADVERTENCIA → revisar CPA y creativos
ROAS < 1,5 por 2 días → CORTAR campaña
```

## Regla de ROAS (Adrián Sáenz `Q4Ykcwh5Osc 09:40`)
ROAS mínimo = 2. Cruzar SIEMPRE con Stripe como fuente de verdad.
No escalar si Stripe muestra ROAS real < 2 aunque la plataforma declare > 2.
