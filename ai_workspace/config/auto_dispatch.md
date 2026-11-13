# GEM OS — Auto-Dispatch Routing Table

Cuando el usuario hace una consulta en lenguaje natural, GEM OS mapea automáticamente al skill + conectores + Claude skills correspondientes.

## Tabla de routing por intención

| Palabras clave detectadas | Skill activado | Conectores | Claude Skills |
|--------------------------|---------------|------------|---------------|
| buscar producto, trending, viral, qué vender, producto ganador | `/buscar-producto` | Google Sheets | dataviz |
| clasificar, HOT, WARM, COLD, puntuar producto, score | `/clasificar-producto` | Google Sheets | dataviz |
| guion, script, TikTok, video, 15 segundos, 30 segundos | `/redactar-guion` | — | artifact-design |
| landing, página, AIDA, copy de venta, estructura tienda | `/estructurar-landing` | Ahrefs | artifact-design |
| validar margen, margen, 3x, 2x, coste landed, precio venta | `/validar-financiero` | Google Sheets, Stripe | dataviz |
| matriz de precios, precios de un lote, PVP 2x 3x, tabla de precios | `/matriz-precios` | Google Sheets | dataviz |
| notas proveedor, nota AutoDS, mensaje al proveedor, instrucciones de packaging | `/autods-notas` | — | — |
| ficha shopify, descripción producto, título SEO | `/redactar-ficha-shopify` | Ahrefs, Google Sheets | artifact-design |
| anuncio meta, Facebook Ads, Instagram Ads, copy ads | `/redactar-anuncios-meta` | Ahrefs, Google Sheets, Figma | artifact-design |
| hook, gancho, primeros 3 segundos, matriz de hooks | `/hook-matrix` | Ahrefs | artifact-design |
| investigar nicho, ángulos de ataque, keywords nicho | `/investigar-nicho` | Ahrefs, Google Sheets | dataviz, artifact-design, deep-research |
| flujo de caja, ROAS del día, revenue, margen neto | `/monitorear-caja` | Google Sheets, Stripe, Gmail | dataviz, artifact-design |
| escalar campaña, subir presupuesto, cortar campaña | `/escalar-campana` | Google Sheets, Stripe | dataviz |
| importar productos, lista de URLs, AliExpress, CJ, Temu | `/importar-masivo` | Google Sheets | dataviz |
| campaign naming, nomenclatura campañas, s0 s1 s2 s3, Roger Viladrosa | `/gestionar-meta-ads` | Ahrefs, Google Sheets, Figma | artifact-design |
| google ads, search campaign, shopping, pmax, keywords google | `/google-ads` | Ahrefs, Google Sheets, Stripe | dataviz |
| tiktok ads pagados, pixel tiktok, campaña tiktok | `/tiktok-ads` | Google Sheets, Stripe | dataviz |
| amazon, listing amazon, BSR, fulfillment | `/amazon-dropshipping` | Google Sheets | dataviz |
| tiktok shop, afiliados, LIVE tiktok, sin stock tiktok | `/tiktok-shop` | Google Sheets, Ahrefs | dataviz |
| configurar tienda, shopify setup, dominio, pagos shopify | `/configurar-tienda` | Stripe, Google Sheets | artifact-design |
| tráfico orgánico, contenido orgánico, cuenta tiktok | `/trafico-organico` | Ahrefs, Google Sheets | dataviz |
| consultar KB, qué tenemos en la KB, estrategias guardadas | `/consultar-kb` | Google Sheets, Google Drive | dataviz |
| skool, comunidad ecommerce, Dr. Marcus Chen | `/monitorear-skool` | Google Sheets, Google Drive | artifact-design |
| carrito abandonado, recuperar carrito, email nocturno | `/recuperar-carrito` | Gmail, Google Sheets, Stripe | dataviz |
| make, escenario, webhook, router, filtro make, módulo http, créditos make, automatización make | `/experto-make` | Gmail, Google Sheets | artifact-design |
| mejorar prompt, cómo pedirle a Claude, claude code, cowork, crear skill, proyecto de claude, memoria de claude, omitir permisos, qué modelo usar, gasto de tokens, claude responde mal | `/experto-claude` | — | anthropic-skills:skill-creator, claude-api |
| github, CI, PR bloqueado, Dependabot, secrets | `/resolver-github` | Google Drive, Gmail | — |
| refutar, demoler tesis, 8 intentos, método Pavel | `/refutar-producto` | — | — |
| fake door, medir demanda, sin stock, pop-up captura | `/fake-door` | Google Sheets | artifact-design |
| oferta multiunidad, 1+1, 2+2, escalones precio | `/oferta-multiunidad` | Google Sheets | artifact-design |
| clonar sección, HTML competencia, Liquid shopify | `/clonar-seccion` | — | artifact-design |
| video IA, Higgsfield, generar video, TikTok sin filmar | `/generar-video-ia` | — | — |
| pipeline completo, todo el pipeline, desde transcripción | `/pipeline-completo` | Todos | dataviz, artifact-design |
| consolidar manual, manual operativo, todo en un manual | `/consolidar-manual` | Google Drive | artifact-design |
| destilar skill, reescribir skill, mejorar procedimiento | `/destilar-skill` | — | — |
| sitio web, web hostinger, landing hostinger | `/crear-web-hostinger` | — | artifact-design |

## Lógica de routing

1. **Detectar intención** — escanear la consulta del usuario contra palabras clave de la tabla
2. **Skill primario** — activar el skill más específico que matchea
3. **Conectores** — cargar automáticamente los conectores listados para ese skill
4. **Claude Skills** — cargar las Claude skills indicadas antes de ejecutar
5. **Ambigüedad** — si más de 2 skills matchean con igual peso → preguntar al usuario cuál es el objetivo principal

## Delegación por modelo (Claude Code, desktop y web)

Aunque el usuario no use slash commands, delegar en el subagente adecuado (`.claude/agents/`):

| Tipo de tarea | Subagente | Modelo |
|---------------|-----------|--------|
| Fichas, hooks, guiones, anuncios Meta, clonar sección, AIDA (borradores) | `gem-bulk-copy` | Haiku |
| Validación 3x/2x, coste landed, HOT/WARM/COLD, escalado, caja | `gem-financial-guard` | Sonnet |
| Auditoría o diseño de arquitectura global | `gem-architect` | Fable, solo si el usuario lo pide explícitamente |

- El copy de `gem-bulk-copy` siempre pasa por `verificar_copy` (`deterministic_gate.py`) antes de publicarse.
- Los números los valida `gem-financial-guard` y el gate; el modelo barato nunca decide cifras.
- Fable nunca se activa automáticamente.

## En Cowork

Cowork no lee esta tabla ni `.claude/commands/`: allí las skills llegan por el plugin `gem-os`
(`plugins/gem-os/`, generado por `scripts/build_cowork.py`).

- **Routing:** cada skill del plugin lleva en su `description` la función y las palabras clave
  de su fila de arriba. Editar una fila aquí cambia cuándo se activa la skill en Cowork.
- **Conectores:** por nombre (Google Sheets, Stripe, Gmail, Google Drive). Los IDs
  `mcp__xxxxxxxx` son de una sesión de Claude Code y el generador los elimina.
- **Qué se exporta:** solo la lista blanca `SKILLS_COWORK` del generador. Las skills que
  necesitan `.env`, scripts locales, cookies o git se quedan en Claude Code.
- **Subagentes:** `gem-financial-guard` y `gem-bulk-copy` viajan en el plugin; `gem-architect` no.
- Guía de uso: `cowork/GUIA.md`.

## Prioridad de pipeline

Si la consulta es sobre un producto nuevo → forzar orden del DAG:
`/buscar-producto` → `/clasificar-producto` → `/refutar-producto` → `/validar-financiero` → `/hook-matrix` → `/redactar-guion`

No saltar pasos del DAG aunque el usuario pida el último paso directamente.
Excepción: si el usuario tiene datos financieros ya validados, puede entrar en `/redactar-ficha-shopify` directamente.
