# Contribuir a GEM OS

## Reglas de negocio inmutables

Antes de cualquier cambio, leer [`CLAUDE.md`](CLAUDE.md). Las siguientes reglas **no se negocian**:

| Regla | Valor |
|-------|-------|
| Margen mínimo | ≥ 3× costo origen |
| Baterías de litio sueltas | Prohibido |
| Tiempo de envío en copy | días reales del proveedor: 2-5 hábiles (Shopify) o 5-7 (TikTok Shop); nunca 24-48h sin confirmación |

## Flujo de trabajo

```
master → feature/nombre-cambio → PR → review → merge
```

1. Crear rama desde `master`: `git checkout -b feature/mi-mejora`
2. Hacer cambios
3. Verificar que no hay `.env` ni secrets en el commit
4. Abrir PR — el template aparece automáticamente
5. Los workflows de CI validan el pipeline

## Nomenclatura de commits

```
feat: nueva funcionalidad
fix: corrección de bug
ci: cambios en workflows
docs: documentación
refactor: refactorización sin cambio de funcionalidad
```

## Qué NO hacer

- ❌ Commitear `.env` o API keys
- ❌ Hardcodear precios o costos (usar variables)
- ❌ Prometer plazos de envío que el proveedor no confirma
- ❌ Cambios a reglas financieras, `CLAUDE.md` o workflows sin revisión (el hook de auto-sync y el agente `self-heal` sí empujan a `master`; el resto de cambios por PR)
- ❌ Modificar reglas financieras sin revisión del owner
