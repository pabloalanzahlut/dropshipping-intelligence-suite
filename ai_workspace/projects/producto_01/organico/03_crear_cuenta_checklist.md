# ✅ CHECKLIST CREACIÓN DE CUENTAS — TikTok / Instagram / Facebook Business
> Curso Adrián Sáenz `Q4Ykcwh5Osc 14:58:10` | GEM OS v3.0

---

## 📱 TIKTOK BUSINESS

### Antes de crear la cuenta
- [ ] Dispositivo limpio (sin cuentas TikTok baneadas previas)
- [ ] SIM local activa (no VoIP, no número temporal)
- [ ] WiFi doméstico (sin VPN activa)
- [ ] App TikTok actualizada a la última versión

### Creación paso a paso
- [ ] Registrar con **número de teléfono** (más confianza que email)
- [ ] Verificar con SMS
- [ ] Ir a: Perfil → ☰ → Configuración → Administrar cuenta → **Cambiar a cuenta de empresa**
- [ ] Categoría: **Retail and E-commerce**
- [ ] Añadir email de negocio (no Gmail personal)
- [ ] Añadir web (URL de la tienda Shopify)
- [ ] Activar **TikTok Business Suite** (dashboard de métricas)

### Post-creación (primeros 7 días — fase de calentamiento)
- [ ] Día 1-2: Seguir 10-15 cuentas del nicho (no más)
- [ ] Día 1-3: Ver y dar like a 20-30 videos del nicho por sesión
- [ ] Día 3: Publicar primer video (valor puro, sin CTA de venta)
- [ ] Día 5: Publicar segundo video
- [ ] Día 7: Publicar con CTA suave ("link en bio")
- [ ] No cambiar contraseña ni país durante los primeros 14 días

---

## 📸 INSTAGRAM BUSINESS

### Creación paso a paso
- [ ] Crear cuenta nueva desde la app (no desde web)
- [ ] Nombre de usuario: `@nombretienda` (el mismo que TikTok)
- [ ] Ir a: Perfil → ☰ → Configuración → Tipo de cuenta → **Cambiar a cuenta profesional**
- [ ] Categoría: **Tienda** o **Producto/Servicio**
- [ ] Conectar con **página de Facebook** (obligatorio para Meta Ads en el futuro)
- [ ] Activar **Herramientas profesionales** → Estadísticas → Verificar que registra datos

### Configuraciones clave
- [ ] Respuestas rápidas: configurar 3 respuestas automáticas para DMs ("¿Dónde compro?", "¿Cuánto tarda?", "¿Puedo devolver?")
- [ ] Link en bio: Linktree o URL directa
- [ ] Historias destacadas: crear carpetas vacías listas para usar (Reseñas, Envíos, FAQ)
- [ ] Permitir menciones y etiquetas: Activado

---

## 🔵 FACEBOOK (PÁGINA DE NEGOCIO)

> ⚠️ Usar **Página** (no perfil personal). Los Reels orgánicos de Páginas tienen mayor alcance que los de perfiles.

### Creación paso a paso
- [ ] Ir a facebook.com → Crear → **Página**
- [ ] Nombre: mismo que la tienda (ej. "TechHogar")
- [ ] Categoría: **Tienda de comercio electrónico** o **Producto**
- [ ] Añadir foto de perfil y portada (mismas que Instagram para coherencia)
- [ ] Añadir descripción (misma que Instagram bio)
- [ ] Añadir URL del sitio web (Shopify)
- [ ] Número de WhatsApp Business (opcional pero recomendado)
- [ ] Activar: Configuración → Reels → **Distribución de Reels activada**
- [ ] Conectar Instagram a esta Página (en Configuración → Cuentas vinculadas)

### Fase de calentamiento Facebook (primeros 7 días)
- [ ] Invitar a 20-30 contactos personales a seguir la Página
- [ ] Publicar 1 Reel (el mismo de TikTok, recortado si necesario)
- [ ] Responder cualquier comentario en las primeras 2h

---

## 🔗 VINCULACIÓN ENTRE PLATAFORMAS

```
TikTok Business
    ↕
Instagram Business ←→ Facebook Página (Meta Business Suite)
    ↓
Shopify (link en bio de todas)
    ↓
Make.com (publicación automática vía webhook)
```

**Configurar Make.com** (`MAKE_WEBHOOK_TIKTOK` en `.env`) para publicar desde GEM OS → TikTok. Para Instagram/Facebook usar Meta Business Suite o Buffer con API gratuita.

---

## 📊 VERIFICACIÓN (estado actual)

| Plataforma | Estado | Acción |
|-----------|--------|--------|
| TikTok Business | ⬜ Pendiente | Crear según checklist |
| Instagram Business | ⬜ Pendiente | Crear según checklist |
| Facebook Página | ⬜ Pendiente | Crear según checklist |
| Vinculación IG↔FB | ⬜ Pendiente | Tras crear ambas |
| Link bio → Shopify | ⬜ Pendiente | Tras activar tienda |
| Make.com webhook | ✅ Configurado | `MAKE_WEBHOOK_TIKTOK` activo |
