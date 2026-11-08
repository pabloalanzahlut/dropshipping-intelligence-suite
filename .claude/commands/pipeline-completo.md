# Skill: Pipeline Completo GEM OS

Ejecuta el pipeline completo de GEM OS sobre una transcripción de video o datos de producto. Sigue el DAG en orden estricto. No saltear pasos.

## DAG de ejecución:

```
PASO 1 → Clasificar Producto   (Product Hunter)
PASO 2 → Validar Financiero    (Rules Engine)
PASO 3 → Estructurar Landing   (Funnel Builder)  ← solo si WARM/HOT
PASO 4 → Redactar Guión        (Media Buyer)     ← solo si WARM/HOT
```

## Instrucciones:

### PASO 1: Clasificar
Lee `ai_workspace/skills/clasificar_productos/procedimiento.md` y clasifica el producto: HOT / WARM / COLD / DISCARD.

→ Si DISCARD → DETENER. Reportar razón al usuario.
→ Si COLD → DETENER. Registrar para monitoreo.
→ Si WARM o HOT → continuar con PASO 2.

### PASO 2: Validar Financiero
Aplica las reglas de `.continue/rules/dropshipping_financial_rules.md`:
- Multiplicador ≥ 2.0 sobre coste landed (rechaza) y objetivo ≥ 3.0 (advierte)
- Sin umbral de margen % ni límite de peso (el curso no los fija)
- Sin baterías de litio sueltas

→ Si RECHAZADO → DETENER. Reportar al usuario.
→ Si APROBADO → continuar.

### PASO 3: Estructurar Landing
Lee `ai_workspace/skills/estructurar_landing/procedimiento.md` y genera copy AIDA completo.

### PASO 4: Redactar Guión
Lee `ai_workspace/skills/redactar_guiones_tiktok/procedimiento.md` y genera script TikTok 15-30s.

## Output final:

Entrega un reporte consolidado con:
1. Clasificación del producto + score
2. Validación financiera (tabla con valores reales)
3. Copy AIDA completo
4. Script de video completo
5. Próximos pasos recomendados

## Regla de oro:
Si en cualquier paso falta un dato crítico → `DATA_GAP_REQUEST` → preguntar al usuario → no inventar.
