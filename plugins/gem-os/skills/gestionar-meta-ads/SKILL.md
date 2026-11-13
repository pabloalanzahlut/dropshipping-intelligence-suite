---
name: gestionar-meta-ads
description: "Genera naming de campañas Business Manager + 3 hooks s0–s3 estilo Roger Viladrosa. Usar cuando el usuario hable de: campaign naming, nomenclatura campañas, s0 s1 s2 s3, Roger Viladrosa."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/gestionar-meta-ads.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

# /gestionar-meta-ads

Lee `referencias/gestionar_meta_ads.md` y genera naming de campañas + hooks s0–s3 estilo Roger Viladrosa.

## Conectores a activar automáticamente
- **Ahrefs** (`mcp__plugin_marketing_ahrefs`): usar `content-helper-topics` para identificar los pain points más resonantes del nicho — alimentan los hooks s0–s3. Cargar `doc` antes de la primera llamada.
- **Google Sheets**: escribir la estructura de campaña en Dashboard tab "Pipeline" — columnas: campaña, ad_set, hook_code, estado
- **Figma** (`mcp__plugin_marketing_figma`): si se pide mockup de los creativos, generar diseño de los anuncios en Figma

## Skills Claude a cargar
- `artifact-design` → generar la estructura de campaña como artefacto compartible
- `dataviz` → si hay métricas previas de hooks, visualizar CTR por fórmula

## Naming convention Roger Viladrosa
```
[PAÍS]-[OBJETIVO]-[PRODUCTO]-[AUDIENCIA]-[FECHA]
Ejemplo: ES-VTA-MASAJEADOR-LOOKALIKE-241108
```

## Estructura de hooks s0–s3
- **s0** (awareness): presentar el problema sin mencionar el producto
- **s1** (interés): mostrar la solución de forma visual en 3s
- **s2** (consideración): prueba social o demostración real
- **s3** (conversión): CTA directo con urgencia o garantía

## Regla
Mínimo 3 variantes de hook por nivel para test A/B. Sin superlativos vacíos.
