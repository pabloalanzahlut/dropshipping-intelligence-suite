# Make.com — Escenario "GEM OS Publicador FB+IG"

> Este escenario recibe un webhook de `publicador.py`, descarga el vídeo de Google Drive
> y lo publica como Reel en Facebook (página NovaBuy) y en Instagram.
> TikTok usa el webhook `MAKE_WEBHOOK_TIKTOK` ya existente (escenario 8432832 o uno nuevo).

---

## 1. Crear el escenario

1. Make.com → **Scenarios** → **+ Create a new scenario**
2. Nombre: `GEM OS Publicador FB+IG`
3. Guardar como borrador.

---

## 2. Módulo 1 — Webhook (trigger)

| Campo | Valor |
|-------|-------|
| Módulo | **Webhooks > Custom webhook** |
| Nombre | `GEM OS Publicador` |
| Responder | Inmediatamente |

Después de crearlo, copia la URL del webhook y pégala en `.env` como `MAKE_WEBHOOK_PUBLICADOR_FB_IG`.

**Payload que recibirá** (enviado por `publicador.py`):
```json
{
  "video_url": "https://drive.google.com/uc?export=download&id=XXXX",
  "plataforma": "facebook_reels",
  "caption": "Massaggio del cuoio capelluto",
  "hashtags": ["#massaggio", "#relax"],
  "producto": "peine",
  "formula": "DEM",
  "slot_id": "aabbccdd-..."
}
```

---

## 3. Módulo 2 — HTTP: descargar el vídeo de Drive

| Campo | Valor |
|-------|-------|
| Módulo | **HTTP > Make a request** |
| URL | `{{1.video_url}}` |
| Método | GET |
| Parse response | No |
| Guardar como | Archivo binario |

> Drive redirige antes de entregar el archivo; activa **Follow redirect** si existe esa opción.

---

## 4. Router — bifurcar según plataforma

Módulo: **Flow Control > Router**

Ruta A → condición: `{{1.plataforma}} = facebook_reels`
Ruta B → condición: `{{1.plataforma}} = instagram_reels`

---

## 5A. Módulo Facebook Reels

| Campo | Valor |
|-------|-------|
| Módulo | **Facebook Pages > Upload a Video** (o **Create a Reel**) |
| Conexión | Cuenta de Alan Zahlut → Página **NovaBuy** (id `1376569378878124`) |
| Video | `{{2.data}}` (el archivo descargado en módulo 2) |
| Title / Description | `{{1.caption}} {{join(1.hashtags, " ")}}` |
| Published | Sí |

> Si Make.com no tiene módulo nativo de Reels, usa **Facebook Pages > Make an API Call**:
> - Endpoint: `/{page-id}/videos`
> - Method: POST
> - Body (form-data): `source={{2.data}}`, `description={{1.caption}}`

---

## 5B. Módulo Instagram Reels

| Campo | Valor |
|-------|-------|
| Módulo | **Instagram for Business > Upload a Video** |
| Conexión | Cuenta vinculada a NovaBuy |
| Media type | REELS |
| Video URL | `{{1.video_url}}` (Instagram acepta URL directa) |
| Caption | `{{1.caption}} {{join(1.hashtags, " ")}}` |

> Instagram Graph API requiere que el vídeo sea accesible por URL pública. La URL de Drive sirve.

---

## 6. Módulo final — Webhook response

| Campo | Valor |
|-------|-------|
| Módulo | **Webhooks > Webhook response** |
| Status | 200 |
| Body | `{"ok": true, "plataforma": "{{1.plataforma}}"}` |

---

## 7. Activar y probar

1. Activa el escenario (toggle ON).
2. Desde terminal:
```bash
python -m app.services.publicador --cola <ruta_cola.json> --dry-run
```
3. Verifica los logs de Make.com.
4. Con vídeo real:
```bash
python -m app.services.publicador --cola ai_workspace/projects/producto_01/organico/cola_publicacion.json
```

---

## 8. Escenario TikTok (separado)

El webhook `MAKE_WEBHOOK_TIKTOK` ya existe (escenario 8432832).
Si ese escenario no tiene módulo TikTok, agrega:

| Campo | Valor |
|-------|-------|
| Módulo | **TikTok > Upload a Video** |
| Conexión | Cuenta TikTok NovaBuy |
| Video file | Descarga desde `{{1.video_url}}` |
| Caption | `{{1.caption}} {{join(1.hashtags, " ")}}` |

---

## Nota sobre el Service Account de Drive

El Service Account (`google_credentials.json`) no tiene cuota de almacenamiento propia.
Los vídeos hay que subirlos a un **Shared Drive** (Drive compartido) donde el Service Account sea miembro, o usar **OAuth user credentials** en su lugar.

**Solución más simple:** compartir manualmente la carpeta "GEM OS/Videos" en tu Drive personal con el email del Service Account (`gemos-dashboard@...iam.gserviceaccount.com`) como editor; los archivos se crean en tu Drive y el Service Account sube como delegado.

Ver: https://developers.google.com/workspace/drive/api/guides/manage-shareddrives
