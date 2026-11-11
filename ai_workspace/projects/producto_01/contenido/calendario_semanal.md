# 📅 CALENDARIO SEMANAL DE CONTENIDO — GEM OS

**Producto:** {{NOMBRE_PRODUCTO}} | **Semana:** {{FECHA_INICIO}} – {{FECHA_FIN}}
**Plataformas:** TikTok + Instagram | **Automatización:** Make.com webhook

---

| Día | Hora | Formato | Archivo | Estado |
|-----|------|---------|---------|--------|
| **Lunes** | 19:00 | 🎬 TikTok/Reels | `guion_tiktok.md` | ⬜ Pendiente |
| **Martes** | 09:00 | 📝 Blog SEO | `articulo_blog_seo.md` | ⬜ Pendiente |
| **Martes** | 18:00 | 📱 Stories (3 slides) | `copy_stories.md` | ⬜ Pendiente |
| **Miércoles** | 12:00 | 📸 Instagram Feed | `copy_instagram_feed.md` | ⬜ Pendiente |
| **Miércoles** | 19:00 | 🎬 TikTok/Reels (variante) | `guion_tiktok.md` | ⬜ Pendiente |
| **Jueves** | 09:00 | 📝 Blog SEO (variante) | `articulo_blog_seo.md` | ⬜ Pendiente |
| **Jueves** | 18:00 | 📱 Stories (repromocional) | `copy_stories.md` | ⬜ Pendiente |
| **Viernes** | 19:00 | 🎬 TikTok/Reels (UGC style) | `guion_tiktok.md` | ⬜ Pendiente |
| **Sábado** | 11:00 | 📸 Instagram Feed (lifestyle) | `copy_instagram_feed.md` | ⬜ Pendiente |
| **Domingo** | 20:00 | 🎬 TikTok/Reels (oferta fin semana) | `guion_tiktok.md` | ⬜ Pendiente |

---

## ⏱️ TIEMPO POR TAREA (tabla del texto aportado por el usuario, no extraída del vídeo)

| Tarea | Tiempo | Dispositivo |
|-------|--------|-------------|
| Monitorear métricas y ventas | 3-5 min | App Móvil Shopify |
| Revisar clasificación producto | 5 min | Ordenador (GEM OS `/clasificar-producto`) |
| Importar copy a programador | 5-10 min | Ordenador (Make.com / Buffer / Metricool) |
| Atención al cliente | 5 min | App Shopify Inbox |
| **Total diario** | **~20 min** | — |

---

## 🔄 FLUJO DE PUBLICACIÓN (Make.com)

```
GEM OS genera guion_tiktok.md
    → /publicar-tiktok (webhook MAKE_WEBHOOK_TIKTOK)
        → CapCut/Canva API (añade subtítulos y música)
            → TikTok Business API (programa publicación)
                → Google Sheets (log de publicación)
```

**Para Instagram:** Usar Metricool o Buffer con los copies de `copy_instagram_feed.md` y `copy_stories.md`.

---

## ✅ CHECKLIST ANTES DE PUBLICAR

- [ ] Producto validado como HOT (≥5x) o WARM (3-5x) por `/clasificar-producto`
- [ ] Copy pasado por `verificar_copy` (`deterministic_gate.py`): sin superlativos ni plazos de envío no confirmados
- [ ] Días de envío mencionados = los reales del proveedor ({{DIAS_ENVIO_PROVEEDOR}})
- [ ] Garantía mencionada = la de la política de reembolso real de la tienda
- [ ] Hashtags mínimos: 3 (TikTok) / hasta 30 (Instagram)
- [ ] Link en bio actualizado con URL del producto Shopify
