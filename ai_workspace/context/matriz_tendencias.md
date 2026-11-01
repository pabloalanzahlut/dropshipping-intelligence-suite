# Matriz de Tendencias Base - Criterios de Selección Cuantitativos

<matriz_config>
  <![CDATA[
  [GOBERNANZA DE SELECCIÓN - MENTORES]
  - Adrián Sáenz: Regla matemática estricta del 3x (Margen bruto mínimo del 70%).
  - JaviEcom & Marc Verdú: Validación basada en volumen de engagement en TikTok Creative Center y Minea.
  - Vic Ecomilions: Enfoque en productos Evergreen de alta rotación (Hogar, Belleza).
  - Iván Caicedo: Control estricto de fricción logística (Peso < 1.2 kg) y optimización del CPA.
  ]]>
</matriz_config>

## 📊 Matriz de Tendencias y Benchmarks Regionales

| Vertical de Negocio | Región Objetivo | Costo Origen Promedio (CO) | Precio Venta Sugerido (PVP 3x) | Margen Bruto Esperado (%) | Volatilidad de Precios | Estacionalidad Crítica |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Electrónica y Tech** | Norteamérica (USA/CA) | \$15.00 USD | \$45.00 USD | 70.00% | Alta (Q4 Escala) | Q4 (Black Friday / Navidad) |
| **Electrónica y Tech** | España y UE | €12.00 EUR | €36.00 EUR | 70.00% | Media-Alta | Q4 (Black Friday) |
| **Moda y Accesorios** | Norteamérica (USA/CA) | \$8.00 USD | \$24.99 USD | 71.98% | Baja | Primavera / Verano |
| **Moda y Accesorios** | España y UE | €7.00 EUR | €22.00 EUR | 71.18% | Baja | Rebajas de Verano / Enero |
| **Hogar y Jardín** | Norteamérica (USA/CA) | \$20.00 USD | \$60.00 USD | 70.00% | Muy Baja (Evergreen) | Primavera (Jardín) |
| **Hogar y Jardín** | España y UE | €18.00 EUR | €54.00 EUR | 70.00% | Muy Baja (Evergreen) | Otoño / Invierno (Hogar) |
| **Belleza y Cuidado** | Norteamérica (USA/CA) | \$5.00 USD | \$19.99 USD | 77.48% | Media | Q4 (Regalos) / Primavera |
| **Belleza y Cuidado** | España y UE | €4.50 EUR | €14.99 EUR | 73.18% | Media | Q4 / San Valentín |

## 🧬 Repositorio de Datos de Productos (Estructura XML Segura)

<base_conocimiento_productos>

  <producto_ganador id="TECH_USA_001">
    <meta_datos>
      <nombre>Cargador Inalámbrico Magnético RGB</nombre>
      <vertical>Electrónica y Tech</vertical>
      <origen_datos>TikTok Creative Center / Minea</origen_datos>
    </meta_datos>
    <metricas_financieras>
      <costo_proveedor_usd>9.50</costo_proveedor_usd>
      <precio_venta_usd>29.99</precio_venta_usd>
      <margen_operativo_porcentaje>71.32</margen_operativo_porcentaje>
    </metricas_financieras>
    <validacion_logistica>
      <peso_kg>0.18</peso_kg>
      <dimensiones_cm>12x12x3</dimensiones_cm>
      <restricciones>Batería integrada (Requiere línea de envío especial para líquidos/baterías)</restricciones>
      <tasa_devolucion_estimada_porcentaje>1.50</tasa_devolucion_estimada_porcentaje>
    </validacion_logistica>
  </producto_ganador>

  <producto_ganador id="HOGAR_EU_002">
    <meta_datos>
      <nombre>Organizador de Cocina Modular Ajustable</nombre>
      <vertical>Hogar y Jardín</vertical>
      <origen_datos>Canal Iván Caicedo / Espionaje AliExpress</origen_datos>
    </meta_datos>
    <metricas_financieras>
      <costo_proveedor_eur>11.20</costo_proveedor_eur>
      <precio_venta_eur>34.99</precio_venta_eur>
      <margen_operativo_porcentaje>70.84</margen_operativo_porcentaje>
    </metricas_financieras>
    <validacion_logistica>
      <peso_kg>0.85</peso_kg>
      <dimensiones_cm>30x15x10</dimensiones_cm>
      <restricciones>Ninguna (Producto plástico libre de fricción aduanera)</restricciones>
      <tasa_devolucion_estimada_porcentaje>0.60</tasa_devolucion_estimada_porcentaje>
    </validacion_logistica>
  </producto_ganador>

</base_conocimiento_productos>
---

## 🧭 Metadatos de Ruteo — FASE 4 (Agentes IA & OpenRouter)

| Campo | Valor |
|-------|-------|
| `context_id` | `matriz_tendencias` |
| `agentes_consulta` | `@gem-qa-validation`, `@gem-orchestrator-core`, `@gem-backend-core` |
| `agentes_escritura` | `@gem-backend-core` |
| `modelo_recomendado` | `qwen/qwen-2.5-coder-32b-instruct:free` (procesamiento), `google/gemini-2.5-flash:free` (validación) |
| `openrouter_ruta` | `https://openrouter.ai/api/v1/chat/completions` |
| `benchmarks_requeridos` | Margen 3x mínimo, Peso < 1.2 kg, PVP 3x CO |
