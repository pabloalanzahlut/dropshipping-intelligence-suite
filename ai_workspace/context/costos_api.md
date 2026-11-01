# 📊 Matriz de Costos de APIs de IA — GEM OS Suite
**Fuente:** Datos oficiales extraídos de Anthropic y OpenRouter (Octubre 2026)
**Propósito:** Base de conocimiento para el control de presupuesto mensual del pool híbrido.

---

## 1. Anthropic API (Directa)

Precios oficiales: https://platform.claude.com/docs/en/about-claude/pricing

| Modelo | Input / MTok | Output / MTok | Cache Writes (5m) / MTok | Cache Hits / MTok |
|--------|-------------|---------------|--------------------------|-------------------|
| Claude Haiku 5.5 (≤100K tokens) | $0.10 | $0.50 | $0.125 | $0.01 |
| Claude Haiku 5.5 (>100K tokens) | $0.50 | $2.50 | $0.625 | $0.05 |
| Claude Sonnet 5.5 | $2.00 | $10.00 | $2.50 | $0.10 |
| Claude Sonnet 4.6 | $3.00 | $15.00 | $3.75 | $0.30 |
| Claude Opus 5 | $5.00 | $25.00 | $6.25 | $0.50 |
| Claude Opus 5.5 | $4.00 | $20.00 | $5.00 | $0.20 |
| Claude Fable 5 | $10.00 | $50.00 | $12.50 | $1.00 |
| Claude Fable 5.1 | $10.00 | $50.00 | $12.50 | $0.25 |

*MTok = Millón de tokens. Cache hits tienen descuento del 90-97.5% sobre input.*

---

## 2. OpenRouter API

Precios oficiales: https://openrouter.ai/pricing

| Concepto | Costo |
|----------|-------|
| Plan Standard (Pay-as-you-go) | 5.5% fee sobre compra de créditos |
| Plan Business | 8% fee sobre compra de créditos |
| Modelos gratuitos disponibles | `google/gemini-2.0-flash-exp:free` y otros |
| BYOK (Bring Your Own Key) | $25,000/mes de inferencia sin fee, luego 5% |

### Modelos Populares vía OpenRouter

| Modelo | Input / MTok | Output / MTok |
|--------|-------------|---------------|
| google/gemini-2.0-flash-exp:free | $0.00 | $0.00 |
| deepseek/deepseek-chat (V3) | ~$0.30 | ~$1.00 |
| anthropic/claude-sonnet-4.6 (EU) | $3.30 | $16.50 |
| qwen/qwen-2.5-72b-instruct | ~$0.35 | ~$0.40 |

---

## 3. FreeLLMAPI Proxy

| Concepto | Costo |
|----------|-------|
| Uso del proxy | **$0.00** (gratuito) |
| Modelos disponibles | Depende de la instancia configurada |

---

## 4. Ollama Local

| Concepto | Costo |
|----------|-------|
| Inferencia local | **$0.00** (sin conexión a internet) |
| Modelo por defecto | qwen2.5-coder:1.5b |
| Requisito | Tener Ollama instalado y servidor corriendo |

---

## 5. Estimación de Consumo por Operación

| Operación | Input (tokens) | Output (tokens) | Costo Sonnet 4.6 | Costo Haiku 5.5 |
|-----------|---------------|-----------------|-------------------|-----------------|
| Validar producto | ~200 | ~100 | $0.0021 | $0.00007 |
| Generar copy AIDA | ~800 | ~600 | $0.0114 | $0.00038 |
| Generar guión TikTok | ~1,000 | ~500 | $0.0105 | $0.00035 |
| Limpiar transcripción | ~2,000 | ~300 | $0.0105 | $0.00035 |
| Curar prompt | ~1,500 | ~800 | $0.0165 | $0.00055 |

---

## 6. Escenarios de Costo Mensual

### 🟢 Escenario A: Solo modelos gratuitos (Recomendado)
- FreeLLMAPI + `google/gemini-2.0-flash-exp:free` + Ollama
- **Costo: $0.00/mes**

### 🟡 Escenario B: OpenRouter con DeepSeek V3
- ~2,000 operaciones/mes × ~1,000 tokens promedio
- **Costo estimado: $1.50 - $3.00/mes**

### 🔴 Escenario C: Anthropic directo (Claude Sonnet 4.6)
- ~2,000 operaciones/mes
- **Costo estimado: $10 - $15/mes**

### 🟢 Escenario D: Anthropic con Claude Haiku 5.5
- ~2,000 operaciones/mes
- **Costo estimado: $0.50 - $1.00/mes**

---

## 7. Reglas de Presupuesto (Budget Controller)

El `BudgetController` en `app/services/budget_controller.py` impone:

1. **Límite mensual configurable** vía `AI_MONTHLY_BUDGET_USD` en `.env`
2. **Alerta temprana** al 80% del presupuesto consumido
3. **Bloqueo automático** al 100% (capa gratuita o local como fallback)
4. **Reseteo mensual** automático el día 1 de cada mes
5. **Logging de cada operación** con costo estimado en USD

---

*Última actualización: 31 Octubre 2026*