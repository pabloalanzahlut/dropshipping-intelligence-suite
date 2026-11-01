# Fórmulas de Conversión Cuantitativas - Framework AIDA Clásico

<framework_config>
  <![CDATA[
  [METADATA DE CONVERSIÓN]
  Focus: Conversión Directa de Tráfico Frío (TikTok Ads & Meta Ads)
  Model: AIDA Rígido sin adjetivos superlativos vacíos (libre de humo)
  Optimization_Target: Maximización del ROAS basado en Costo por Compra (CPA)
  ]]>
</framework_config>

## 📈 Benchmarks de KPIs por Etapa del Embudo

Las siguientes métricas actúan como umbrales (benchmarks) analíticos que los agentes auditarán para determinar la salud de las campañas de tráfico frío:

| Etapa AIDA | KPI Clave de Control | Benchmark Objetivo (USA/CA) | Benchmark Objetivo (España/UE) | Fórmula de Cálculo Matemático |
| :--- | :--- | :--- | :--- | :--- |
| **Attention** | Hook Rate (Retención 3s) | > 45.00% | > 40.00% | `(Visualizaciones de 3s / Impresiones Totales) * 100` |
| **Interest** | CTR de Salida (Anuncio) | > 2.50% | > 2.00% | `(Clics salientes hacia la tienda / Impresiones) * 100` |
| **Decision** | Tasa de Carritos Añadidos (ATC)| > 8.00% | > 6.50% | `(Sesiones con Añadir al Carrito / Sesiones Totales) * 100` |
| **Action** | Tasa de Conversión (CR) | > 2.20% | > 1.80% | `(Transacciones Completadas / Sesiones Totales) * 100` |

## 🧬 Estructura Rígida de Copywriting Persuasivo (Inyección XML)

<estructuras_copywriting>

  <etapa id="ATTENTION">
    <descripcion>Interrupción de patrón en los primeros 3 segundos del anuncio de video</descripcion>
    <regla_de_control>Prohibido usar textos genéricos o claims falsos no verificables</regla_de_control>
    <plantilla_datos><![CDATA[
    [GANCHO_PROBLEMA]: "¿Sabías que el [Porcentaje_Ahorro]% de las personas daña su [Objeto_Común] por no usar esto?"
    [GANCHO_WOW]: "El invento que está cambiando la forma de organizar [Espacio_Hogar] en [Año]."
    ]]></plantilla_datos>
  </etapa>

  <etapa id="INTEREST">
    <descripcion>Demostración práctica del Factor Wow y resolución de dolores del cliente</descripcion>
    <regla_de_control>Especificar métricas de beneficio medibles directamente de la ficha técnica</regla_de_control>
    <plantilla_datos><![CDATA[
    [BENEFICIO_CUANTITATIVO]: "Diseñado con ingeniería magnética que reduce el tiempo de [Acción] a la mitad."
    [CARACTERISTICA_LIMPIA]: "Material ABS certificado de alta resistencia con un peso neto de solo [Peso_Producto]g."
    ]]></plantilla_datos>
  </etapa>

  <etapa id="DECISION">
    <descripcion>Oferta comercial irresistible aplicando el multiplicador 3x y eliminando barreras de compra</descripcion>
    <regla_de_control>El precio mostrado debe garantizar un margen bruto operativo superior al 70%</regla_de_control>
    <plantilla_datos><![CDATA[
    [OFERTA_BENCHMARK]: "Consigue tu [Nombre_Producto] hoy con un [Porcentaje_Descuento]% de descuento de lanzamiento."
    [GARANTIA_RIESGO_CERO]: "Envío rápido con seguimiento e IVA incluido en el precio final. Garantía de reembolso de 30 días."
    ]]></plantilla_datos>
  </etapa>

  <etapa id="ACTION">
    <descripcion>Llamado a la acción inequívoco y de un solo paso</descripcion>
    <regla_de_control>Evitar palabras de relleno comercial; usar imperativos directos</regla_de_control>
    <plantilla_datos><![CDATA[
    [CTA_DIRECTO]: "Haz clic en 'Comprar Ahora' para asegurar tu envío gratuito antes de agotar existencias."
    ]]></plantilla_datos>
  </etapa>

</estructuras_copywriting>

## 🛠️ Guía de Optimización Basada en Datos
*   **Si el Hook Rate es bajo (<30%):** Cambiar los primeros 3 segundos del creativo (Visual/Texto del gancho). El problema está en la etapa de **Attention**.
*   **Si el CTR es bajo (<1.5%):** El producto no despierta suficiente deseo o el copy de interés es débil. Optimizar etapa de **Interest**.
*   **Si la Tasa de Conversión (CR) es baja (<1%):** Fricción en el precio, tiempos de envío oscuros o falta de confianza en la Landing Page. Optimizar etapas de **Decision** y **Action** (revisar regla de costos y cargos ocultos).

---

## 🧭 Metadatos de Ruteo — FASE 4 (Agentes IA & OpenRouter)

| Campo | Valor |
|-------|-------|
| `context_id` | `formulas_conversion` |
| `agentes_consulta` | `@gem-qa-validation`, `@gem-orchestrator-core` |
| `agentes_escritura` | `@gem-backend-core` |
| `modelo_recomendado` | `google/gemini-2.5-flash:free` (validación), `qwen/qwen-2.5-coder-32b-instruct:free` (procesamiento) |
| `openrouter_ruta` | `https://openrouter.ai/api/v1/chat/completions` |
| `benchmarks_requeridos` | Hook Rate > 45%, CTR > 2.50%, ATC > 8.00%, CR > 2.20% |
