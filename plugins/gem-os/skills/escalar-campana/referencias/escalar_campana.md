# Skill: Escalar Campaña Publicitaria

**ID:** `escalar_campana`
**Versión:** 1.0.0
**Propósito:** Decidir si escalar, mantener o cortar una campaña de pago basándose en datos de los primeros 3 días de test. Aplica reglas cuantitativas para evitar decisiones emocionales. Nivel 5→6 del framework de 7 niveles.

**Referencias:**
  - `referencias/validar_financiero.md` — para CPA_max de referencia
  - `referencias/monitorear_flujo_caja.md` — verificar caja antes de escalar
  - `contexto/manual/formulas_conversion.md` — benchmarks KPIs
  - `app/services/traffic_analyzer.py` — datos históricos de campañas

---

## 1. Input Esperado

```
Día de campaña: [1 / 2 / 3 / 4+]
Presupuesto diario actual: [€/$]
Ventas totales del período: [número]
Gasto total acumulado: [€/$]
CPA_max calculado (de /validar-financiero): [€/$]
CR (Tasa de conversión) de la tienda: [%]
ROAS acumulado: [calculado por usuario o pegar datos brutos]
```

---

## 2. Árbol de Decisión

### Día 1-2: Período de Aprendizaje

| Señal | Acción |
|-------|--------|
| 0 ventas, CPM > €20 | Revisar audiencia y creatividad — no cortar aún |
| 0 ventas, CPM ≤ €20 | Esperar día 3 antes de decidir |
| ≥ 1 venta, CPA ≤ CPA_max | Dejar correr sin cambios |
| ≥ 1 venta, CPA > CPA_max × 1.5 | Pausar conjunto de anuncios ineficiente |

**Regla día 1-2:** No realizar cambios de presupuesto. El algoritmo de Meta necesita datos para optimizar.

### Día 3: Punto de Decisión Principal

Calcular resultados acumulados al final del día 3:

```
CPA_real_acumulado = Gasto_total / Ventas_totales
ROAS_acumulado = Ingresos_brutos / Gasto_total
```

| Escenario | Criterio | Decisión |
|-----------|----------|----------|
| **WINNER** | ROAS ≥ 2.5 Y CPA_real ≤ CPA_max | **ESCALAR** → subir presupuesto 20% |
| **POSITIVO** | ROAS 1.8–2.49 Y CR > 1.5% | **MANTENER** → optimizar públicos, no subir presupuesto |
| **DUDOSO** | ROAS 1.0–1.79 O CR 1.0–1.49% | **OPTIMIZAR** → pausar creatividades peores, mantener presupuesto 3 días más |
| **NEGATIVO** | ROAS < 1.0 O 0 ventas en 3 días | **CORTAR** → volver al Nivel 2, buscar nuevo producto |

### Días 4+: Reglas de Escalado Progresivo

Solo aplicables si el día 3 fue WINNER:

```
Incremento_presupuesto = Presupuesto_actual × 0.20
Nuevo_presupuesto = Presupuesto_actual + Incremento_presupuesto
```

**Frecuencia máxima de escalado:** cada 2-3 días.
**Nunca** doblar presupuesto de golpe (resetea el aprendizaje del algoritmo).

| Condición adicional para escalar | Regla |
|----------------------------------|-------|
| Días de caja < 4 | NO escalar — esperar liberación de pagos |
| CPA_real supera CPA_max en ese día | NO escalar ese día — esperar recuperación |
| ROAS ≥ 2.5 por 2 días consecutivos | Duplicar conjunto de anuncios ganador |

---

## 3. Output Estructurado

```
╔══════════════════════════════════════════╗
║   DECISIÓN DE ESCALADO GEM OS            ║
╠══════════════════════════════════════════╣
║ Día de campaña: [X]
║ Presupuesto actual: [X]€/día
║
║ MÉTRICAS ACUMULADAS
║   Ventas:        [X]
║   Gasto total:   [X]€
║   ROAS:          [X]x
║   CPA real:      [X]€  vs  CPA_max: [X]€
║   CR tienda:     [X]%
║
║ ESCENARIO: [WINNER / POSITIVO / DUDOSO / NEGATIVO]
║
║ DECISIÓN: [ESCALAR / MANTENER / OPTIMIZAR / CORTAR]
║
║ ACCIÓN CONCRETA:
║   [instrucción específica: "subir a X€/día", "pausar conjunto Y",
║    "volver a /clasificar-producto con nuevo nicho", etc.]
║
║ ADVERTENCIAS:
║   [días de caja, alertas de CPA, etc. si aplican]
╚══════════════════════════════════════════╝
```

---

## 4. Reglas de Comportamiento

- **Nunca** recomendar escalar sin verificar días de caja con `/monitorear-caja`
- Si el veredicto es CORTAR → no desmotivar; indicar que cortar rápido es disciplina profesional, no fracaso
- El criterio de 3 días es un mínimo estadístico; con < €30/día de presupuesto puede necesitar hasta 5 días
- En caso de duda entre MANTENER y OPTIMIZAR → elegir OPTIMIZAR (error conservador)
- Los umbrales ROAS son para mercado España/EU; para USA/CA el umbral mínimo rentable puede ser diferente
