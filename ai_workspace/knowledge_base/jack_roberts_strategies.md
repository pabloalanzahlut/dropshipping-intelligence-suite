# Estrategias GEM OS — Insights de Jack Roberts (@Itssssss_Jack)
**Canal:** 290K suscriptores | 415 videos | ex-fundador startup Top-100 UK
**Fuente verificada:** 2026-11-01

---

## 1. SISTEMA DE SKILLS (AntiGravity ≈ GEM OS)

Jack Roberts usa "AntiGravity" — su propio sistema de skills para Claude Code, conceptualmente idéntico al pipeline de GEM OS. Validación externa: este approach funciona a escala (668K views en su video más popular).

**Principios que aplica:**
- Skills modulares activadas por comando slash
- Zero-prompt mode via `settings.json` con permisos pre-autorizados
- Archivos de referencia en `reference/` para reglas por dominio
- Verifier script post-generación para calidad

**Para GEM OS:** nuestro pipeline (Product Hunter → Funnel Builder → Media Buyer) sigue el mismo patrón. Correcto. Continuar.

---

## 2. WEBS PREMIUM CON CLAUDE CODE

**Videos clave (views):**
- Claude Code + Nano Banana 2 = $10,000 websites (668K)
- AntiGravity + Spline = 3D Websites (191K)
- Claude Design + motion graphics (309K, 156K)
- Claude Fable 5 → web en 21 min (162K)

**Insights aplicables al skill de Adrián Sáenz:**

### 2.1 Integrar Spline para 3D
```html
<!-- Spline viewer (sin npm, solo script tag) -->
<script type="module" src="https://unpkg.com/@splinetool/viewer@1.9.27/build/spline-viewer.js"></script>
<spline-viewer url="https://prod.spline.design/YOUR_SCENE/scene.splinecode"></spline-viewer>
```
**Advertencia:** Jack usa Spline para heroes 3D de alto impacto. Para dropshipping, usar solo en hero section — el resto del funnel debe cargar rápido.

### 2.2 Claude Design / Motion Graphics
- Generar assets SVG animados directamente con Claude (sin Figma)
- Lottie animations inline para micro-interacciones de producto
- Para fichas de producto Shopify: animación de "wow reveal" en la imagen principal

### 2.3 Tiempo real de generación (benchmark)
- 1 landing page premium: ~17-33 minutos con el skill
- 1 sitio multi-página: ~47 minutos
- Iteraciones de ajuste: 5-10 min adicionales

---

## 3. SOCIAL MEDIA 100% AUTOMATIZADO

**Video:** "Ruba questo sistema di social media (100% automatizzato)" — 201K views

**Stack que usa Jack:**
```
Claude (generación de contenido)
  ↓
Make.com (orquestación de automatización)
  ↓
Buffer / Publer (scheduling)
  ↓
Instagram / TikTok / X / LinkedIn
```

**Para GEM OS — Media Buyer Agent:**
El agente `redactar_guiones_tiktok` ya genera los scripts. Falta la automatización de publicación:

| Paso | Herramienta | Estado en GEM OS |
|------|------------|-----------------|
| Generar guión | Claude (skill existente) | ✅ Implementado |
| Generar imagen/video | Claude Design o CapCut API | ⬜ Pendiente |
| Publicar automáticamente | Make.com webhook → TikTok | ⬜ Pendiente |
| Analizar performance | Make.com → Google Sheets | ⬜ Pendiente |

**Flujo Make.com básico:**
1. Webhook recibe guión JSON de GEM OS
2. Make llama a CapCut/Canva API para generar video
3. Make publica en TikTok Business API
4. Make registra URL publicada en Google Sheets

---

## 4. CLAUDE CODE GRATIS (Reducir costos)

**Videos:** "Claude Code gratis via OpenRouter" (222K) | "Gemma 4 + Ollama = FREE Claude Code" (184K) | "DeepSeek Harness" (256K)

**Stack de costo-cero para GEM OS:**

### Opción A: OpenRouter + DeepSeek V4
```
ANTHROPIC_BASE_URL=https://openrouter.ai/api/v1
ANTHROPIC_API_KEY=<openrouter_key>
CLAUDE_MODEL=deepseek/deepseek-chat-v3-0324
```
**Costo:** ~$0.14/M tokens vs $3/M de Claude Sonnet
**Limitación:** No tiene las capacidades visuales de Claude Design

### Opción B: Gemma 4 + Ollama (100% local)
```
ANTHROPIC_BASE_URL=http://localhost:11434/v1
ANTHROPIC_API_KEY=ollama
CLAUDE_MODEL=gemma4:latest
```
**Costo:** $0 (local)
**Limitación:** Mucho más lento, sin internet access

### Opción C: DeepSeek Harness (el más popular de Jack)
- Acceso a DeepSeek V4 via su "Harness" personalizado
- ~95% de las capacidades de Claude Code al ~5% del costo

**Recomendación para GEM OS:** usar Claude Sonnet para Product Hunter y Funnel Builder (alta calidad crítica). Usar OpenRouter + DeepSeek para tareas repetitivas como formateo de fichas y generación masiva de variantes.

---

## 5. SISTEMA "JACK v2/v3" — Arquitectura de Agentes

De sus videos "jack v2" (29K) y "jack v3" (39K):
- Claude Code con múltiples sub-agentes especializados
- Memory persistence entre sesiones (idéntico a nuestro sistema en `ai_workspace/memory/`)
- Cada agente tiene su propio `SKILL.md` con reglas inmutables

**Diferencia clave:** Jack usa "AntiGravity" como capa de orquestación global. En GEM OS, el equivalente es el CLAUDE.md principal + el DAG de agentes.

---

## 6. APLICACIÓN INMEDIATA A GEM OS

### Acciones de alto impacto:
1. **Make.com webhook** → conectar output de `redactar_guiones_tiktok` con publicación automática
2. **Spline 3D** → agregar al skill de Hostinger para hero sections de productos WOW factor
3. **OpenRouter** → reducir costos de generación masiva de fichas Shopify
4. **Claude Design assets** → generar imágenes de producto con fondo removido automáticamente

### NO aplicar:
- Ollama local para decisiones financieras (Regla 3x) — solo Claude oficial
- Automation de publicación antes de validar el guión manualmente (compliance TikTok)

---

*Referencia: Canal YouTube @Itssssss_Jack — Jack Roberts | Verificado 2026-11-01*
