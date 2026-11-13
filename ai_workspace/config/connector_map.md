# GEM OS — Connector Map

Mapa completo de conectores activos y sus casos de uso por skill.

## Conectores activos

### Google Sheets (`mcp__69f3b6ec`)
**Dashboard ID**: ver `memory/project_google_sheets_dashboard.md`
**Tabs disponibles**: Pipeline, ROAS_Diario, Nichos (nuevo)

| Skill | Acción | Tab | Herramientas |
|-------|--------|-----|-------------|
| `/validar-financiero` | Leer/escribir validaciones | Pipeline | `get_values`, `update_values` |
| `/monitorear-caja` | Leer últimos 7 días, escribir nuevos | ROAS_Diario | `get_values`, `update_values`, `append_values` |
| `/escalar-campana` | Leer tendencias de ROAS | ROAS_Diario | `get_values` |
| `/importar-masivo` | Escribir resultados importación | Pipeline | `append_values` |
| `/investigar-nicho` | Guardar informe de nicho | Nichos | `append_values` |
| `/buscar-producto` | Registrar candidatos | Pipeline | `append_values` |
| Todos | Dashboard general | Pipeline | `get_spreadsheet` |

---

### Stripe (`mcp__1cc6d3ec`)
**Uso principal**: verificar revenue real vs ROAS declarado por plataformas de ads

| Skill | Acción | Herramientas |
|-------|--------|-------------|
| `/monitorear-caja` | Revenue verificado del período | `stripe_analytics` |
| `/escalar-campana` | Confirmar ROAS real antes de escalar | `stripe_analytics` |
| `/importar-masivo` | Comparar márgenes reales vs proyectados | `stripe_analytics` |
| `/recuperar-carrito` | Verificar conversiones de recuperación | `stripe_analytics` |

---

### Ahrefs (`mcp__plugin_marketing_ahrefs`)
**IMPORTANTE**: Siempre cargar `mcp__plugin_marketing_ahrefs__doc` antes de la primera llamada.

| Skill | Herramientas Ahrefs |
|-------|---------------------|
| `/investigar-nicho` | `keywords-explorer-overview`, `keywords-explorer-matching-terms`, `keywords-explorer-related-terms`, `site-explorer-organic-keywords`, `serp-overview` |
| `/redactar-ficha-shopify` | `keywords-explorer-overview`, `keywords-explorer-matching-terms` |
| `/hook-matrix` | `content-helper-topics` |
| `/redactar-anuncios-meta` | `content-helper-topics` |
| `/gestionar-meta-ads` | `content-helper-topics` |
| `/google-ads` | `keywords-explorer-overview`, `keywords-explorer-matching-terms`, `keywords-explorer-search-suggestions` |
| `/trafico-organico` | `keywords-explorer-overview` |
| `/tiktok-shop` | `keywords-explorer-overview` |

---

### Gmail (`mcp__ae68f902`)
| Skill | Acción | Herramientas |
|-------|--------|-------------|
| `/monitorear-caja` | Buscar payouts Shopify | `search_threads` |
| `/recuperar-carrito` | Verificar emails enviados | `search_threads` |
| `/resolver-github` | Buscar notificaciones GitHub | `search_threads` |

---

### Google Drive (`mcp__73e33a54`)
| Skill | Acción | Herramientas |
|-------|--------|-------------|
| `/consultar-kb` | Buscar archivos KB exportados | `search_files` |
| `/resolver-github` | Buscar documentación técnica | `search_files` |
| `/monitorear-skool` | Guardar reportes de Skool | `create_file` |

---

### Figma (`mcp__plugin_marketing_figma`)
| Skill | Acción |
|-------|--------|
| `/redactar-anuncios-meta` | Mockup visual de anuncios |
| `/gestionar-meta-ads` | Diseño de creativos |
| `/redactar-ficha-shopify` | Mockup de página de producto |

---

## Claude Skills por categoría

| Claude Skill | Cuándo cargar |
|-------------|--------------|
| `dataviz` | Siempre que haya métricas, tablas o comparaciones numéricas |
| `artifact-design` | Siempre que se genere un entregable visual (ficha, copy, informe, matriz) |
| `anthropic-skills:deep-research` | Investigación de nicho compleja o competencia |
| `artifact-capabilities` | Si el artefacto necesita interactividad (calculadoras, formularios) |

---

## En Cowork

Los IDs entre paréntesis (`mcp__69f3b6ec`, `mcp__1cc6d3ec`…) identifican el conector **en una
sesión de Claude Code**. En Cowork el mismo conector se usa por su nombre y hay que tenerlo
conectado en *Customize → Connectors*. `scripts/build_cowork.py` sustituye los IDs por el
nombre al generar el plugin `gem-os`; un ID nuevo se añade a `CONECTORES` en ese script.

Permisos recomendados en Cowork: Stripe y Gmail en solo lectura (escritura y envío en
*Needs approval* o *Blocked*); Google Sheets con escritura bajo aprobación.

---

## Reglas de uso

1. **Nunca inventar IDs de conectores** — usar solo los listados aquí
2. **Ahrefs**: cargar `doc` siempre antes de la primera llamada en cada sesión
3. **Stripe**: solo lectura en todos los skills — nunca ejecutar pagos ni transferencias
4. **Gmail**: solo lectura y `create_draft` — nunca `send_message` sin confirmación explícita del usuario
5. **Google Sheets**: preferir `append_values` sobre `update_values` para no sobreescribir datos existentes
