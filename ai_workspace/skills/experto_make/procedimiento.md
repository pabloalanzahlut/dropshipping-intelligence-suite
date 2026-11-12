# Skill: Experto Make (v0.1 — parcial)

Agente especialista en **Make.com** para GEM OS: diseña, diagnostica y documenta los escenarios que
conectan GEM OS con Gmail, Sheets, Klaviyo y TikTok/Meta. Uso personal, no producto a la venta.

**Base:** curso de Adrián Sáenz → `ai_workspace/knowledge_base/make_curso_adrian.md` (con marcas de tiempo)
+ práctica real de GEM OS (2026-11-12). **Estado:** v0.1. Falta leer 2 de las 3 fuentes (ver KB).
Si algo no tiene fuente (curso o práctica verificada), se dice que es conocimiento general o se pregunta.

## Regla suprema
No inventar. Si falta un dato (estructura del payload, nombre del campo, límite del plan, versión de un
módulo) → `DATA_GAP_REQUEST`: pedir captura o texto del error. Nunca supongas cómo es un módulo por dentro.

## Qué puede y qué no puede hacer este agente
- **Puede:** diseñar escenarios, escribir los cuerpos JSON y filtros, diagnosticar errores a partir de capturas,
  enviar pruebas desde Python al webhook, actualizar `.env`, documentar.
- **No puede:** entrar a Make (pide login; nunca introducir credenciales del usuario). El usuario
  hace los clics y el agente dicta pasos exactos y verifica con capturas.
- Evaluar más adelante el **Make MCP** («Build and run scenarios from Claude or ChatGPT», visible en el panel de Make):
  daría acceso directo, pero es una autorización del usuario. No asumir que existe.

## Reglas de diseño (cada una con su origen)

### Del curso (`make_curso_adrian.md`)
1. Disparador **instantáneo (webhook)** en vez de por intervalo: el de intervalo gasta créditos aunque no haya datos (`WxCxyRAnVQM 01:06:02`, `01:07:32`).
2. Una operación = un crédito: presupuestar `ejecuciones × módulos` (`01:32:32`). Mirar el consumo real en *Organization → Usage*, no estimarlo.
3. Nombrar siempre las conexiones y los módulos (`00:27:50`, `01:09:51`).
4. Router: un filtro por rama; sin filtro el dato va por todas (`02:17:40`); orden de arriba abajo (`02:26:16`).
5. Probar con **Run once** y revisar el detalle módulo a módulo y qué filtro dejó pasar (`02:08:43`, `00:48:46`).
6. **Desactivar la recarga automática de créditos**: el ponente la sufrió y recomienda quitarla (`WxCxyRAnVQM 00:41:33`–`00:41:52`). Comprobar en la cuenta que no está activa.

### De la práctica en GEM OS (2026-11-12, verificado en el propio Make)
7. **Plan gratuito: máximo 2 escenarios activos.** Por eso el diseño es **un solo webhook + Router** (ver «Escenario unificado»).
8. **Un webhook pertenece a un solo escenario.** Al copiar módulos entre escenarios, NO copiar el módulo Webhook: error «The hook already has a scenario assigned».
9. **El Router va justo después del Webhook.** Con un filtro entre ambos, bloquea las demás rutas.
10. **Filtros de rama por existencia de campo**, operador *Exists*. Un `Equal to` con valor vacío deja pasar todo lo que no trae el campo (vacío = vacío).
11. **Variables:** solo son variables las etiquetas de color. Un `[1. campo]` escrito a mano es texto literal. Si el panel no ofrece el campo, el webhook aún no lo ha visto: lanzar *Run once* y enviar una prueba.
12. **Datos viejos en la cola del webhook** («Unprocessed data in webhook queue»): pueden venir en otro formato y fallar. Elegir *Wait for new data* para una prueba limpia, o *Use existing data* solo para diagnosticar.
13. «**Exceeded maximum wait time**» tras *Run once* sin datos **no es un fallo**: nadie envió nada.
14. **Gmail con Raw HTML:** el texto va en *Content*. Con «Collection of contents» el cuerpo va en *Body contents*; rellenar *Signature content* deja el cuerpo vacío.
15. **Aislar errores por ruta** con un error handler *Ignore* en las rutas no críticas. *Conocimiento general de Make, no del curso* (el curso no trata los error handlers; se comprobó con la transcripción completa): Make desactiva un escenario tras varios errores seguidos, y con un solo webhook caerían todas las rutas a la vez. Comprobar el ajuste exacto en la configuración del escenario.
16. **Secretos:** la URL del webhook es un secreto (`.env`, nunca en logs ni en el chat). Las claves de API (ej. Klaviyo `pk_`) se pegan solo en el módulo; si salen en una captura, **rotarlas**.

### Ampliadas tras contrastar con la transcripción completa (2026-11-12)
17. **Instantáneo o programado:** el rayito en el disparador indica instantáneo. Sheets «Watch rows» y Gmail «Watch emails» **no** lo son (`01:07:41`, `01:04:02`, `01:51:08`). Para avisos de GEM OS usar siempre webhook.
18. **Créditos por operación:** cada módulo ejecutado gasta. Activar las monedas en *Canvas options* para verlo (`00:48:47`–`00:49:06`). Un escenario con Router gasta solo los módulos de la ruta que recorre.
19. **Gmail caduca:** la conexión se reautoriza cada ~6 meses (`01:45:55`). La de este Make avisa de **4 mayo 2027, 21:44** (visto en el panel del propio módulo). Reautorizar antes; si no, las alertas dejan de llegar sin error visible.
20. **Poner el campo From** en el módulo Gmail (`01:44:54`–`01:45:33`); hoy está vacío.
21. **Datos de clientes:** valorar marcar el escenario como de datos confidenciales (`00:59:52`–`01:00:09`), ya que el carrito lleva el email del cliente. Comprobar el nombre exacto en *Scenario settings*.
22. **Fallos conocidos de Make:** módulo fantasma (guardar y recargar, `02:02:56`); columnas de Sheets sin actualizar (borrar y recolocar el módulo, `01:31:40`); no hay «pin data» (`02:48:33`).

## Escenario unificado de GEM OS (estado a 2026-11-12)
Escenario **8432832** «GEM OS – Carrito abandonado → Klaviyo». Un webhook → Router con 3 rutas.
`.env`: `MAKE_WEBHOOK_ABANDONED_CART`, `MAKE_WEBHOOK_ALERTAS` y `MAKE_WEBHOOK_TIKTOK` apuntan a la misma URL.

| Ruta | Filtro | Destino | Emisor | Campos clave del payload |
|------|--------|---------|--------|--------------------------|
| Alertas / resumen diario | `asunto` existe | Gmail | `notifier.py` | `origen`, `tipo`, `fecha`, `total`, `criticas`, `asunto`, `mensaje`, `panel`, `alertas[]` |
| Carrito abandonado | `email` válido **y** `abandoned_checkout_url` existe | HTTP → Klaviyo `/api/events/` | **Shopify, directo** (no pasa por GEM OS) | `email`, `customer.first_name`, `line_items[].title`, `total_price`, `currency`, `abandoned_checkout_url` |
| TikTok | `guion` **o** `video_url` existe | Sheets «GEM OS - TikTok Publicaciones» → Gmail | `tiktok_publisher.py`, `publicador.py` | `producto`, `categoria`, `guion{hook,demostracion,cta,hashtags,descripcion_post}`, `media`, `schedule` / `video_url`, `plataforma`, `caption`, `slot_id` |

- Klaviyo: `Authorization: Klaviyo-API-Key …` + `revision: 2024-10-15`, cuerpo JSON:API (`data.type=event`, métrica «Abandoned Cart»).
- Pruebas: `python -c "from app.services import notifier; print(notifier.enviar_prueba())"` ·
  `python -m app.services.abandoned_cart_handler --test-shopify` (formato Shopify) · `--test` (formato GEM OS).
- Escenarios antiguos 8530626 (alertas) y 8356938 (TikTok): desactivar al validar el unificado; no borrar hasta entonces.
- Falta: ruta Facebook/Instagram (`MAKE_WEBHOOK_PUBLICADOR_FB_IG` no tiene escenario).

## Protocolo de diagnóstico (en este orden)
1. ¿Es un error o una espera? («Exceeded maximum wait time» no es error, regla 13.)
2. Abrir el módulo que falla → pestaña **Error/Output**: copiar el código y el `detail` (sin claves).
3. Mirar el **Input** que recibió: ¿vacío? → el dato de la cola era otro formato o el mapeo apunta a un módulo borrado.
4. ¿Qué filtro dejó pasar o bloqueó el dato? (inspector del filtro: ✓ pasó, ⊘ no pasó.)
5. ¿Es cuota? (escenarios activos, créditos, plan.) Verificar en *Organization → Usage*.
6. Reproducir con una prueba controlada desde Python, con la **misma forma** que el emisor real.
7. Corregir una cosa cada vez y volver a probar.

## Checklist antes de activar un escenario
- [ ] Nombre descriptivo del escenario, de los módulos y de las conexiones.
- [ ] Webhook único; Router justo después; cada rama con filtro *Exists* o patrón.
- [ ] Cada módulo mapeado desde el Webhook (sin etiquetas rojas ni variables de módulos borrados).
- [ ] Prueba con datos reales del emisor, una por ruta, y cada una entra solo por su ruta.
- [ ] Error handler *Ignore* en rutas no críticas.
- [ ] Consumo estimado `ejecuciones × módulos` frente al plan; comprobar en *Usage*.
- [ ] URLs de webhook solo en `.env`; ninguna clave en capturas ni en git.
- [ ] Datos de prueba borrados (filas de Sheets, perfiles de Klaviyo).

## Qué NO hacer
- No crear escenarios nuevos si el límite de activos está en 2: primero fusionar en el Router.
- No usar disparadores por intervalo para algo que pueda ser un webhook.
- No dejar que un modelo barato decida cifras ni mapeos de importes: el multiplicador va por `deterministic_gate.py`.
- No asumir la estructura de un payload ajeno (Shopify, Klaviyo): pedir un ejemplo real.

## Pendiente para v1.0
- Leer `Phal-sPAunk` desde `07:17:35` (Funciones de Make) y `MGvUGEk1O9Y` (n8n) y volcar a la KB con marcas de tiempo.
- Comprobar en la cuenta de Make que la recarga automática de créditos está desactivada (regla 6).
- Valorar la notificación push por la app de Make (`WxCxyRAnVQM 02:11:32`) como canal alternativo de alertas; falta ver si el plan gratuito la permite.
- Reautorizar Gmail antes del 4 mayo 2027 (regla 19).
- Decidir si se evalúa el Make MCP.
- Subir la ruta Facebook/Instagram al Router y desactivar los escenarios antiguos.
