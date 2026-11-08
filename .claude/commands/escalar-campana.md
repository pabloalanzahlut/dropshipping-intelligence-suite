# /escalar-campana

Lee `ai_workspace/skills/escalar_campana/procedimiento.md` y decide si escalar, mantener, optimizar o cortar la campaña.

## Conectores a activar automáticamente
- **Google Sheets** (`mcp__69f3b6ec`): leer métricas actuales de la campaña desde Dashboard tab "ROAS_Diario". Si el usuario pega datos, escribirlos en el Dashboard con `update_values`.
- **Stripe** (`mcp__1cc6d3ec`): verificar revenue real con `stripe_analytics` antes de tomar decisión de escalado — nunca escalar basándose solo en el ROAS declarado por la plataforma de ads

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
