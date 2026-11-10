# Plan orgánico 14 días: TikTok + Instagram Reels + Facebook Reels (NovaBuy)

Fuente: skill `trafico_organico` (Adrián Sáenz `Q4Ykcwh5Osc 14:18:11`). Sin ads, sin píxel Meta (portfolio restringido). Mercado: Italia primero.

## Regla de producción: 1 vídeo → 3 plataformas
- Grabar y editar UNA vez en CapCut (9:16, subtítulos, sin marca de agua).
- Exportar el archivo original de CapCut y subirlo tal cual a las 3. No descargar de TikTok con marca de agua para reutilizarlo.
- Cambiar solo texto de descripción y hashtags por plataforma. Mismo vídeo con textos distintos evita duplicado evidente.
- Si se usa vídeo generado con IA (`/generar-video-ia`), activar la etiqueta de contenido generado por IA en cada plataforma.
- Música: biblioteca de sonidos de cada app. Sin copyright.

## Bloqueos antes de publicar (no inventar)
| Dato | Estado | Quién |
|------|--------|-------|
| Producto validado (coste, envío, PVP, multiplicador >= 2x landed) | PENDIENTE | usuario + `/validar-financiero` |
| Producto físico o clips reales para grabar | PENDIENTE | usuario |
| Días de entrega reales del proveedor | PENDIENTE | proveedor |
| Tienda Shopify activa para el enlace en bio | PENDIENTE (daba "Store unavailable") | usuario |

Nunca mencionar envío en 24-48h. Usar solo el plazo confirmado por el proveedor.

## Día 0 — Setup (2 h)
- [ ] Mismo nombre de usuario en las 3 (sin números aleatorios, con palabra del nicho).
- [ ] Foto de perfil: producto, fondo limpio, sin texto.
- [ ] Bio de 1 línea con el problema que resuelve. SIN enlace hasta el día 7.
- [ ] Facebook: página NovaBuy (id 1376569378878124). Instagram: cuenta enlazada. No pulsar "Promocionar" ni crear cuentas publicitarias.
- [ ] Notificaciones de comentarios activas (responder en las primeras 2 h).

## Ritmo
- Días 1-14: 3 vídeos/día, nunca más de 4.
- Franjas (hora de Italia): 07-09 h, 12-14 h, 19-22 h.
- Cada vídeo sale en las 3 plataformas dentro de la misma franja.

## Calendario de fórmulas (rotación)
Fórmulas: DEM = Demostración directa, REA = Reacción/Sorpresa, COM = Antes/Después, POV = POV, UNB = Unboxing rápido.

| Día | Mañana | Mediodía | Noche |
|-----|--------|----------|-------|
| 1 | DEM | POV | REA |
| 2 | COM | UNB | DEM |
| 3 | REA | DEM | POV |
| 4 | UNB | COM | REA |
| 5 | DEM | REA | COM |
| 6 | POV | DEM | UNB |
| 7 | COM | REA | DEM |
| 8 | UNB | POV | COM |
| 9 | DEM | COM | REA |
| 10 | REA | UNB | POV |
| 11 | COM | DEM | UNB |
| 12 | POV | REA | DEM |
| 13 | DEM | UNB | COM |
| 14 | REA | COM | POV |

Cada vídeo: hook visual en 0-2 s, demostración 2-10 s, beneficio 10-20 s, CTA suave 20-25 s. Máximo 6 palabras por frame. Hooks: generar con `/hook-matrix` cuando haya producto.

## Textos por plataforma
- TikTok: descripción corta + 3-5 hashtags de nicho en italiano.
- Instagram Reels: descripción de 1-2 líneas + 3-5 hashtags; portada legible.
- Facebook Reels: descripción más descriptiva; sin hashtags excesivos.

## Medición cada 3 días (registrar en Sheets, pestaña "Orgánico")
Columnas: Fecha | Plataforma | Video_ID | Formula | Vistas | Watch_rate | Clicks_link | Ventas | Seguidores

| Métrica | Umbral | Lectura |
|---------|--------|---------|
| Watch rate (>50% visto) | >30% | el hook funciona |
| Click al enlace | >1% de vistas | el producto interesa |
| Ventas orgánicas | >=1 en 2 semanas | validación básica |
| Seguidores | >50/semana | hay tracción |

## Decisión (Adrián `15:03:58`)
- Algún vídeo >10.000 vistas: producto con potencial.
- >50.000 vistas con enlace en bio: valorar `/tiktok-ads` (Meta Ads solo cuando se resuelva la restricción).
- Ningún vídeo >500 vistas tras 20 vídeos: revisar producto o hook.

## Día 7: añadir enlace en bio
Solo si la tienda Shopify está activa y la página de producto/captura funciona (`/fake-door` si aún no hay stock).
