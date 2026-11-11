# OpenRouter — Reducir Costos de Generación Masiva

Configuración para usar modelos económicos via OpenRouter en tareas de volumen alto (fichas Shopify masivas, variantes de copy, traducción de listings). Los modelos oficiales de Anthropic se reservan para decisiones críticas.

---

## Política de Uso por Tarea

| Tarea GEM OS | Modelo recomendado | Costo aprox. | Claude oficial |
|---|---|---|---|
| Regla 3x / validación financiera | `anthropic/claude-sonnet-5.5` | $3/M tokens | ✅ Siempre |
| Generación ficha Shopify (1 producto) | `anthropic/claude-sonnet-5.5` | $3/M tokens | ✅ Preferido |
| Generación masiva fichas (10+ productos) | `anthropic/claude-haiku-5.5` | $0.14/M tokens | ❌ OpenRouter |
| Traducción ES→EN de listings | `google/gemini-2.5-flash` | $0.08/M tokens | ❌ OpenRouter |
| Variantes de copy A/B testing | `anthropic/claude-haiku-5.5` | $0.14/M tokens | ❌ OpenRouter |
| Scripts TikTok (borrador inicial) | `anthropic/claude-haiku-5.5` | $0.14/M tokens | ❌ OpenRouter |
| Scripts TikTok (revisión final) | `anthropic/claude-sonnet-5.5` | $3/M tokens | ✅ Calidad |
| Clasificación HOT/WARM/COLD | `anthropic/claude-sonnet-5.5` | $3/M tokens | ✅ Siempre |

---

## Configuración OpenRouter

### 1. Obtener API Key
1. Ir a [openrouter.ai](https://openrouter.ai)
2. Sign Up → API Keys → Create Key
3. Copiar el key (empieza con `sk-or-v1-...`)

### 2. Variables de Entorno
Añadir a `H:\dropshipping_intelligence_suite\.env`:
```
# Claude oficial (Anthropic directo)
ANTHROPIC_API_KEY=sk-ant-XXXXXXXX

# OpenRouter (modelos económicos)
OPENROUTER_API_KEY=sk-or-v1-XXXXXXXX
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

### 3. Uso en Python (fichas masivas)
```python
import anthropic
import os

def get_client(task_type: str) -> anthropic.Anthropic:
    """
    Devuelve el cliente apropiado según el tipo de tarea.
    Tareas críticas (validacion, clasificacion) → Anthropic oficial.
    Tareas de volumen (fichas masivas, traducciones) → OpenRouter.
    """
    CRITICAL_TASKS = {"validar_financiero", "clasificar_producto", "regla_3x"}

    if task_type in CRITICAL_TASKS:
        return anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
    else:
        return anthropic.Anthropic(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        )

def get_model(task_type: str) -> str:
    CRITICAL_TASKS = {"validar_financiero", "clasificar_producto", "regla_3x"}
    if task_type in CRITICAL_TASKS:
        return "anthropic/claude-sonnet-5.5"
    return "deepseek/deepseek-chat-v3-0324"


# Ejemplo: generar 20 fichas en batch usando OpenRouter
def generar_fichas_masivas(productos: list[dict]) -> list[dict]:
    client = get_client("fichas_masivas")
    model = get_model("fichas_masivas")
    resultados = []

    for producto in productos:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": f"Genera ficha Shopify para: {producto['nombre']}. "
                           f"PVP: ${producto['pvp_usd']}. "
                           f"Material: {producto.get('material', 'no especificado')}. "
                           f"Idioma: {producto.get('idioma', 'es')}. "
                           f"Sigue las reglas GEM OS: sin superlativos, specs inmutables, "
                           f"envío 6-15 días hábiles."
            }]
        )
        resultados.append({
            "producto": producto["nombre"],
            "ficha": response.content[0].text,
            "modelo_usado": model,
            "tokens": response.usage.input_tokens + response.usage.output_tokens
        })

    return resultados
```

---

## Modelos Recomendados en OpenRouter (IDs verificados 2026-11-11)

| Modelo | Mejor para | Costo/M tokens |
|--------|-----------|----------------|
| `anthropic/claude-haiku-5.5` | Copy masivo, fichas, traducciones (defecto de volumen desde 2026-11-11) | $0.10 in / $0.50 out |
| `google/gemini-2.5-flash` | Multimodal + multilenguaje | $0.30 in / $2.50 out |
| `meta-llama/llama-3.3-70b-instruct` | Fallback de volumen (los `:free` ya no están en el catálogo) | $0.71 |
| `deepseek/deepseek-chat-v3-0324` | Alternativa de volumen / reversión | $0.29 in / $1.14 out |
| `deepseek/deepseek-r1-0528` | Razonamiento complejo (ficha técnica difícil) | $0.50 in / $2.15 out |

---

## Ahorro Estimado para GEM OS

Supuesto: 100 fichas Shopify/mes + 30 scripts TikTok/mes

| Escenario | Costo mensual |
|-----------|--------------|
| Todo en Claude Sonnet (oficial) | ~$12-18 USD/mes |
| Híbrido (crítico=oficial, masivo=OpenRouter) | ~$2-4 USD/mes |
| **Ahorro mensual** | **~$10-14 USD/mes (80%)** |

---

## Límites y Restricciones

- **Nunca** usar OpenRouter para: validar Regla 3x, clasificar HOT/WARM/COLD, revisar specs técnicas
- Los modelos de OpenRouter no tienen las mismas garantías de coherencia que Claude oficial
- Para producción: siempre revisar el output de OpenRouter antes de publicar en Shopify
- Rotar modelo si hay errores > 3 consecutivos (`FALLBACK_MODE` → Claude oficial)

---

---

## Stack 100% Sin Costo de APIs Externas (activado 2026-11-03)

| Componente | Solución gratuita | Archivo |
|------------|------------------|---------|
| YouTube Monitor | RSS feed público + yt-dlp | `app/services/youtube_rss_fetcher.py` |
| LLM routing | OpenRouter (clave ya configurada) | `app/services/llm_router.py` |
| Google Sheets | MCP connector (ya instalado, autenticar) | — |
| Imágenes de producto | remove.bg free tier (50/mes) | `.env` → `REMOVEBG_API_KEY` |
| TikTok publish | Make.com free tier + webhook | `.env` → `MAKE_WEBHOOK_TIKTOK` |
| Shopify | Shopify MCP connector (gratis añadir) | `/mcp` → Shopify |

### Módulo llm_router — uso

```python
from app.services.llm_router import chat

# Clasificación crítica → Claude Sonnet vía OpenRouter
resultado = chat(
    task="clasificar_producto",
    system_prompt="Clasifica HOT/WARM/COLD según reglas GEM OS...",
    user_message=transcripcion_limpia,
)

# Ficha masiva → DeepSeek V3 (volumen barato)
ficha = chat(
    task="generar_ficha_shopify",
    system_prompt="Genera ficha Shopify sin superlativos...",
    user_message=f"Producto: {nombre}, PVP: {pvp}",
)
```

*GEM OS v2.1 — Stack gratuito activado | Actualizado 2026-11-03*
