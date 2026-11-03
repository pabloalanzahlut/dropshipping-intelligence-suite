# Contribuir a GEM OS

## Reglas de negocio inmutables

Antes de cualquier cambio, leer [`CLAUDE.md`](CLAUDE.md). Las siguientes reglas **no se negocian**:

| Regla | Valor |
|-------|-------|
| Margen mínimo | ≥ 3× costo origen |
| Peso máximo | < 1.2 kg |
| Baterías de litio sueltas | Prohibido |
| Tiempo de envío en copy | 6-12 días laborables (nunca 24-48h) |

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
- ❌ Prometer envío en menos de 6 días en copy
- ❌ Push directo a `master` (usar PR)
- ❌ Modificar reglas financieras sin revisión del owner
