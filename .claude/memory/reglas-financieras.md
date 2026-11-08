# Reglas Financieras — GEM OS

Fuente primaria: **Adrián Sáenz**. Solo se aplican reglas que sus contenidos dicen
explícitamente, cada una con su referencia. No se inventa ninguna.

---

## Multiplicador y coste

| Regla | Valor | Fuente | Acción si falla |
|-------|-------|--------|-----------------|
| Multiplicador mínimo | PVP ≥ 2× **coste landed** | `Q4Ykcwh5Osc 24:40` | RECHAZAR |
| Multiplicador objetivo | PVP ≥ 3× **coste landed** | `Q4Ykcwh5Osc 24:40` | ADVERTIR — subir si el producto lo permite |
| Coste de origen | $5–15 recomendado | `Q4Ykcwh5Osc 17:50` | ADVERTIR fuera de rango |
| Baterías de litio sueltas | Prohibido | restricción aduanera | RECHAZAR |

### Coste landed — crítico

El multiplicador se calcula sobre **producto + envío**, nunca sobre el producto solo.

Ficha real del vídeo (`qgK3GfY5ZC4 11:30`): **$5 producto + $2 envío = $7 landed** → PVP $30 → beneficio $22,97.

Calcular sobre el producto solo infla el multiplicador. Un producto de $5 + $2 de envío
vendido a $15 aparenta 3,0× cuando en realidad es **2,14×** — por debajo del objetivo.

---

## Costes operativos reales

Del P&L de 30 días (`rqMrq2MGdpw`). No aparecen en el curso base pero sí en su cuenta real,
y suman **14,1%** de la facturación que de otro modo desaparece sin registrarse.

| Concepto | % facturación | Importe del caso |
|----------|---------------|------------------|
| Fees Shopify + cambio de divisa | 4,0% | 3.109 € / 77.748 € |
| Cancelaciones y devoluciones | 10,1% | 7.887 € / 77.748 € |

Las cancelaciones se dispararon **porque el almacén no absorbió la escalada**. El riesgo
logístico crece con el volumen: al escalar, vigilar este porcentaje.

### P&L completo del caso de referencia

| Concepto | Importe | % |
|----------|---------|---|
| Facturado (1.024 pedidos) | 77.748 € | 100% |
| Ads | 24.962 € | 32,1% |
| Producto + packaging | 15.016 € | 19,3% |
| Fees Shopify + divisa | 3.109 € | 4,0% |
| Cancelaciones y devoluciones | 7.887 € | 10,1% |
| **Margen operativo** | **27.089 €** | **34,8%** |

---

## Métricas de campaña

| Métrica | Valor | Fuente |
|---------|-------|--------|
| ROAS mínimo | ≥ 2 en campañas activas | `Q4Ykcwh5Osc 09:40` |
| Presupuesto test | 15 €/día como base | `Q4Ykcwh5Osc 11:06` |
| Ticket medio de referencia | 75,93 € | `rqMrq2MGdpw` |

**ROAS declarado ≠ ROAS real.** En el caso de referencia Meta declaraba 3,15 y el real era
~2,8. Medir siempre contra ingresos reales, no contra lo que reporta la plataforma.

---

## Lo que el curso NO dice

No existe umbral de margen en %, ni límite de peso en kg. Esas reglas no se aplican
porque no provienen de la fuente primaria.

---

## Implementación

- `app/services/financial_validator.py` — cálculo con coste landed y costes operativos
- `app/services/deterministic_gate.py` — recálculo independiente, no persuadible
- Skill `/validar-financiero`

Ejemplo del curso (`Q4Ykcwh5Osc 23:54`): 21 € → 49,99 € = **2,38×, 58% de margen** →
VALIDADO con advertencia de subir a 3×.
