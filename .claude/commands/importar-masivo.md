# /importar-masivo

Lee `ai_workspace/skills/importar_masivo/procedimiento.md` y procesa URLs de AliExpress/CJ/Temu → valida regla 3x → crea borradores en Shopify.

## Conectores a activar automáticamente
- **Google Sheets** (`mcp__69f3b6ec`): escribir resultados de la importación masiva en Dashboard tab "Pipeline" — columnas: URL, producto, coste_landed, PVP_mínimo (2x), PVP_objetivo (3x), estado (VÁLIDO/RECHAZADO/REVISAR)
- **Stripe** (`mcp__1cc6d3ec`): si ya hay productos activos, consultar `stripe_analytics` para comparar márgenes reales vs proyectados

## Skills Claude a cargar
- `dataviz` → generar tabla visual con los resultados de la importación (válidos vs rechazados)
- `artifact-design` → si se genera un reporte de importación como artefacto

## Flujo automático
1. Recibir lista de URLs (una por línea)
2. Para cada URL: extraer precio proveedor + coste envío estimado = coste landed
3. Validar regla 3x: PVP_mínimo = 2× coste_landed; PVP_objetivo = 3× coste_landed
4. Verificar restricciones: sin litio suelto, envío ≤12 días (sin límite de peso: el curso no lo fija)
5. VÁLIDO → crear borrador en Shopify vía AutoDS API | RECHAZADO → registrar motivo

## Regla financiera (Adrián Sáenz `Q4Ykcwh5Osc 24:40`)
El multiplicador es sobre **coste landed** (producto + envío), nunca sobre el producto solo.
Ejemplo: $5 producto + $2 envío = $7 landed → PVP mínimo $14, objetivo $21.
