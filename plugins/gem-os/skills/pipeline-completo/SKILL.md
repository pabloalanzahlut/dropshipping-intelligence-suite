---
name: pipeline-completo
description: "Ejecuta todo el pipeline desde transcripción. Usar cuando el usuario hable de: pipeline completo, todo el pipeline, desde transcripción."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/pipeline-completo.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

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
Lee `referencias/clasificar_productos.md` y clasifica el producto: HOT / WARM / COLD / DISCARD.

→ Si DISCARD → DETENER. Reportar razón al usuario.
→ Si COLD → DETENER. Registrar para monitoreo.
→ Si WARM o HOT → continuar con PASO 2.

### PASO 2: Validar Financiero
Aplica las reglas de `reglas-gem-os/reglas-financieras.md`:
- Multiplicador ≥ 2.0 sobre coste landed (rechaza) y objetivo ≥ 3.0 (advierte)
- Sin umbral de margen % ni límite de peso (el curso no los fija)
- Sin baterías de litio sueltas

→ Si RECHAZADO → DETENER. Reportar al usuario.
→ Si APROBADO → continuar.

### PASO 3: Estructurar Landing
Lee `referencias/estructurar_landing.md` y genera copy AIDA completo.

### PASO 4: Redactar Guión
Lee `referencias/redactar_guiones_tiktok.md` y genera script TikTok 15-30s.

## Output final:

Entrega un reporte consolidado con:
1. Clasificación del producto + score
2. Validación financiera (tabla con valores reales)
3. Copy AIDA completo
4. Script de video completo
5. Próximos pasos recomendados

## Regla de oro:
Si en cualquier paso falta un dato crítico → `DATA_GAP_REQUEST` → preguntar al usuario → no inventar.
