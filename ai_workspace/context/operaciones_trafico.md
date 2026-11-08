# Manual de Operaciones de Tráfico - TikTok & Meta Ads

<trafico_config>
  <![CDATA[
  [GOBERNANZA DE MEDIA BUYING]
  - JaviEcom & Marc Verdú: Campañas de testeo rápido con presupuestos ajustados por conjunto de anuncios (ABO) para aislar variables.
  - Adrián Sáenz: Presupuesto diario estricto de validación ($20 - $50 por producto). Regla de salida rápida si los números no dan en las primeras 48 horas.
  - Vic Ecomilions: Reglas automáticas / manuales de apagado basadas en el Costo por Compra (CPA) y el coste por clic (CPC).
  - Iván Caicedo: Escalado agresivo mediante campañas de presupuesto a nivel de campaña (CBO) solo cuando el producto demuestra ROAS > 2.
  ]]>
</trafico_config>

## 📊 Estructura de Campañas y Presupuestos (Benchmarks Cuantitativos)

| Fase de Campaña | Tipo de Presupuesto | Configuración de Audiencia | Presupuesto Base Recomendado | Criterio de Éxito / KPI |
| :--- | :--- | :--- | :--- | :--- |
| **Fase 1: Testeo Rápido** | ABO (Por Conjunto) | Intereses Segmentados / Amplio | \$5.00 a \$10.00 USD por AdSet (Mínimo 5 AdSets) | CTR > 2.00% y CPC < \$0.40 USD |
| **Fase 2: Escalado Vertical** | ABO (Duplicación) | Públicos Ganadores Idénticos | Duplicar presupuesto original x2 o x3 en conjuntos limpios | Mantener CPA por debajo del objetivo |
| **Fase 3: Escalado Horizontal**| CBO (Por Campaña) | Públicos Similares (Lookalikes) y Broad | \$100.00 a \$300.00 USD por campaña | ROAS > 2.0 (medido real, no el que declara Meta) |

## 🧬 Reglas Algorítmicas de Optimización (Inyección XML Segura)

El motor agéntico procesará las siguientes directrices lógicas estructuradas para auditar las cuentas publicitarias simuladas o reales:

<reglas_optimizacion_trafico>

  <regla id="APAGADO_PREVENTIVO_CPC">
    <etapa>Fase 1: Testeo (Primeras 24 horas)</etapa>
    <condicion_metrica>Gasto por conjunto de anuncios > $5.00 USD Y CTR < 1.00%</condicion_metrica>
    <accion_requerida>Apagar Conjunto de Anuncios de inmediato</accion_requerida>
    <justificacion_mentor><![CDATA[Vic Ecomilions & Adrián Sáenz: Si el tráfico inicial es extremadamente caro o el creativo no genera clics, el producto o el gancho visual ha fallado. No se financian ganchos ineficientes.]]></justificacion_mentor>
  </regla>

  <regla id="AUDITORIA_CPA_DECISION">
    <etapa>Fase 1: Testeo (Primeras 48 horas o 1x el costo del producto)</etapa>
    <condicion_metrica>Gasto acumulado por producto == Costo de Origen (CO) Y Ventas == 0</condicion_metrica>
    <accion_requerida>Pausar campaña completa y revaluar Landing Page o Ángulo de Venta</accion_requerida>
    <justificacion_mentor><![CDATA[Iván Caicedo: No se debe permitir que una campaña de tráfico frío consuma el presupuesto equivalente al costo del producto sin registrar al menos una conversión de prueba o carritos iniciados consistentes.]]></justificacion_mentor>
  </regla>

  <regla id="DISPARADOR_ESCALADO_CBO">
    <etapa>Fase 3: Escalado Masivo</etapa>
    <condicion_metrica>Conjunto de anuncios con > 5 conversiones estables en 3 días Y ROAS > Benchmark_Base</condicion_metrica>
    <accion_requerida>Exportar ID de creativos ganadores e inyectar en una campaña CBO consolidada</accion_requerida>
    <justificacion_mentor><![CDATA[JaviEcom & Marc Verdú: El escalado horizontal en CBO protege el pixel de la fatiga de audiencias y permite que el algoritmo de TikTok/Meta distribuya el presupuesto en los públicos de mayor valor adquisitivo automáticamente.]]></justificacion_mentor>
  </regla>

</reglas_optimizacion_trafico>

## 🛠️ Matriz de Decisiones Operativas (Estructura de Control)

Cada vez que el Agente Media Buyer analice métricas de pauta, utilizará este bloque estructurado para ejecutar diagnósticos libres de sesgo narrativo:

```xml
<diagnostico_trafico>
  <metrica_entrada>
    <cpc_actual_usd>0.00</cpc_actual_usd>
    <ctr_actual_porcentaje>0.00</ctr_actual_porcentaje>
    <cpa_actual_usd>0.00</cpa_actual_usd>
  </metrica_entrada>
  <arbol_decision>
    <!-- Si el CPC es alto y el CTR es bajo -> Error de Creativo -->
    <!-- Si el CTR es alto y el CR es bajo -> Error de Oferta/Precio (Revisar Regla 3x) -->
  </arbol_decision>
</diagnostico_trafico>
```
---

## 🧭 Metadatos de Ruteo — FASE 4 (Agentes IA & OpenRouter)

| Campo | Valor |
|-------|-------|
| `context_id` | `operaciones_trafico` |
| `agentes_consulta` | `@gem-qa-validation`, `@gem-orchestrator-core` |
| `agentes_escritura` | `@gem-backend-core` |
| `modelo_recomendado` | `meta-llama/llama-3.1-8b-instruct:free` (orquestación), `google/gemini-2.5-flash:free` (validación) |
| `openrouter_ruta` | `https://openrouter.ai/api/v1/chat/completions` |
| `benchmarks_requeridos` | CPC < $0.40, CTR > 2.00%, ROAS > 2.0, CPA < objetivo |
