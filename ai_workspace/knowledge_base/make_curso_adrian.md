# Make — extractos verificados del curso de Adrián Sáenz

**Regla:** cada afirmación lleva `video hh:mm:ss`, copiado de la transcripción automática de YouTube
(panel «Mostrar transcripción», extraído 2026-11-12). Lo que no tiene marca de tiempo NO viene del curso.
La transcripción es automática: los nombres propios y las cifras pueden estar mal escritos; ante duda, revisar el vídeo.

## Fuentes

| ID | Título | Duración | Estado |
|----|--------|----------|--------|
| `WxCxyRAnVQM` | Curso Completo De Make: Cómo Crear y Vender Automatizaciones IA (Adrián Sáenz con Juan Pe) | 3 h 55 min | **Leído entero** (1.836 segmentos del panel de YouTube) y **contrastado** con la transcripción completa que pegó el usuario el 2026-11-12. Las marcas son de párrafo (±15 s). |
| `MGvUGEk1O9Y` | Esta IA Crea Contenido Diario Para Redes Sociales (100 % automático) | 48 min | **Solo descripción.** Es de **n8n**, no de Make (enlaza un servidor n8n en Hostinger VPS). Transcripción pendiente. |
| `Phal-sPAunk` | El Mejor Curso Gratis De Inteligencia Artificial | 23 h | **Solo índice.** Para Make: `07:17:35` «Funciones de Make», `07:50:13` «Funciones de N8N», y desde `17:40:48` un bloque que repite el curso `WxCxyRAnVQM`. Transcripción pendiente. |

Índice real de `WxCxyRAnVQM`: 00:00:00 Introducción · 00:09:25 Qué es Make · 00:22:37 Crear cuenta ·
00:26:25 Conceptos básicos · 01:08:58 Captación de leads · 01:48:08 Emails · 02:15:00 Contenido para redes ·
02:30:19 Guiones YouTube · 02:53:00 WhatsApp · 03:16:29 Vender automatizaciones · 03:29:50 Conseguir clientes.

## Conceptos y recomendaciones (de `WxCxyRAnVQM`)

### Qué es y qué no
- Automatizar no es lo mismo que implementar IA: se automatiza para ahorrar tiempo (`00:13:58`).
- Make tiene una curva de aprendizaje suave frente a programar (`00:21:53`); recomienda conocer
  fundamentos de programación (JSON, JavaScript, Python) para entenderlo todo (`02:39:28`, `02:40:03`).

### Créditos y consumo (lo que más puede costar dinero)
- Make funciona por créditos, la «moneda de cambio» (`00:23:39`, `00:23:54`).
- Una operación = un crédito (`01:32:32`). Cada módulo que se ejecuta cuenta.
- Las funciones de IA de Make también consumen créditos (`00:41:22`).
- Vigilar el panel de créditos (`00:40:50`). Los créditos se reponen cada mes y no se acumulan (`00:41:14`).
- **Recarga automática de créditos:** el ponente la tenía activada y «se recargaba hasta el infinito, hasta
  quedarnos pobres». Recomienda **quitarla** para que no se cargue nada sin quererlo (`00:41:33`–`00:41:52`).
  *(Resuelto con la transcripción completa: la opción pendiente era esta.)*
- «Cada ejecución» gasta créditos (`00:23:46`, `00:40:50`), pero en el lienzo cada módulo muestra su moneda
  de crédito (`00:48:47`–`00:49:06`): la cuenta real es por **operación** (módulo), no por escenario.
  Un escenario de varios módulos gasta varios. Se ve activando las monedas en *Canvas options* (`00:49:06`).
  `01:08:44`: unas pruebas gastaron 48 créditos. Verificar el consumo real en *Usage*.
- Un disparador por intervalo se ejecuta y gasta créditos aunque no haya datos nuevos (`01:06:02`);
  uno instantáneo se ejecuta solo cuando entra el dato, no por intervalo (`01:06:45`–`01:07:32`,
  «esto es importante»).
- Cómo distinguirlos: los disparadores llevan etiqueta lila; los **instantáneos llevan un rayito** y ofrecen
  «Immediately as data arrives» (`01:07:41`–`01:07:59`). Google Sheets «Watch rows» **no es instantáneo**: se
  programa, mínimo cada 15 min en el plan del ponente (`00:58:51`, `01:04:02`–`01:04:24`; bajar a 1 min también gasta más, `01:05:39`).
  Gmail «Watch emails» es su único disparador y **tampoco es instantáneo** (`01:51:08`–`01:51:32`).
  Un webhook sí lo es (`01:28:31`–`01:30:11`).

### Conexiones y webhooks
- Poner **siempre** un nombre a cada conexión, para localizarla luego (`00:27:42`, `00:27:50`).
- Las conexiones se crean desde el propio escenario y luego quedan guardadas en un sitio central (`00:35:55`).
- Webhook = una puerta de entrada a Make; Make da el código y se pega en la otra aplicación;
  es solo de ida hacia Make (`00:36:28`–`00:37:29`).
- Data store = mini base de datos dentro de Make; «no se suele utilizar mucho» (`00:38:35`).
- API vs webhook: parecidos, la API permite también pedir datos (`00:39:01`–`00:39:27`).

### Datos y variables
- Todo lo que viaja entre módulos va en un **bundle** (paquete de datos) (`00:54:49`).
- Las variables son dinámicas: no hay que editarlas al cambiar los datos (`00:55:25`); sirven de
  «localizadores de información» (`00:57:11`).
- El **iterator** divide un bundle en varios (`00:51:43`–`00:51:58`).
- En módulos que leen listas, poner un límite (ej. 1) para procesar de uno en uno (`00:48:07`).

### Estructura del escenario
- Se puede cambiar el nombre de cada módulo (`01:09:36`, `01:09:51`).
- Guardar el escenario con frecuencia, lo recomienda (`00:59:06`).
- **Router + filtros:** cada rama lleva un filtro, y el dato sigue por la rama cuyo filtro cumple
  (`01:48:39`, `01:50:08`, `02:01:09`). El filtro se abre desde el hilo entre módulos (`01:50:08`).
- Router sin filtros: el dato va por todas las ramas (`02:17:40`).
- Con varias ramas, Make las ejecuta en orden, de arriba abajo (`02:26:16`).
- Tras una prueba se ve qué filtro dejó pasar el dato y cuál no (`02:08:43`).
- Probar en un «entorno de pruebas» separado y elegir desde qué módulo arranca la prueba (`02:25:31`, `01:53:33`, `02:50:58`).
- Tras cada ejecución se puede abrir el detalle de lo ocurrido, módulo a módulo, y los créditos gastados (`00:48:46`, `01:44:25`).

### Ajustes, trucos y fallos conocidos (de `WxCxyRAnVQM`)
- Organizar los escenarios en **carpetas** (`00:25:48`). Añadir **notas** al lienzo con clic derecho (`01:00:09`–`01:00:26`).
- **Versiones del escenario** («preview versions») para volver atrás (`01:00:26`–`01:00:43`).
- Ajuste de escenario para marcar los datos como **confidenciales** (p. ej. datos de personas) (`00:59:52`–`01:00:09`).
  Relevante para el carrito abandonado, que lleva el email del cliente. Comprobar el nombre exacto del ajuste en pantalla.
- *Run this module only* (clic derecho) para probar un solo módulo (`00:49:06`, `00:58:19`).
  Clonar un módulo con clic derecho; se engancha al módulo vecino «como un imán» (`01:50:20`–`01:50:38`); no siempre se deja (`02:18:53`).
- **Make no tiene «pin data»** (fijar la salida de un módulo para no repetir el flujo): se repite desde el inicio (`02:48:33`–`02:48:53`).
- **Módulo fantasma:** tras borrar un módulo puede quedar una burbuja sin función; se quita guardando y recargando (`02:02:56`–`02:03:17`).
- **Sheets, columnas que no se actualizan** tras cambiar los encabezados: error común; se arregla borrando el módulo y volviéndolo a poner (`01:31:40`–`01:32:03`).
- **Gmail:** la conexión caduca y hay que reautorizarla cada ~6 meses (`01:45:55`). Con Gmail personal hace falta crear
  un cliente OAuth propio en Google Cloud (ID y secreto) (`01:33:39`–`01:34:12`). Poner el campo **From** es lo recomendable (`01:44:54`–`01:45:33`).
- **Notificación push al móvil** con el módulo de Apple y la app de Make, conectada por QR (`02:11:32`–`02:12:38`). Alternativa a Gmail/Telegram para las alertas.
  *No verificado si funciona en el plan gratuito.*
- **IA dentro de Make:** rol `user` = entrada, `system` = instrucción (`02:20:05`); pedir el prompt a otro modelo (`02:22:47`);
  decirle «solo dame la salida, sin texto extra» (`02:26:58`). Útil si algún día un escenario genera copy.
- WhatsApp automatizado (fuera de alcance hoy): un mensaje automático a alguien que no te ha escrito en 24 h cuenta como marketing y exige plantilla aprobada (`03:10:18`–`03:11:12`).

## Pendiente de verificar con transcripción
- `Phal-sPAunk` desde `07:17:35` (Funciones de Make, ~33 min): sin leer.
- `MGvUGEk1O9Y` (n8n): sin leer. Decisión mientras tanto: **Make es suficiente**; n8n del curso va
  autoalojado en un VPS (según la descripción del vídeo), lo que añade mantenimiento y coste.
- Manejo de errores (error handlers, reintentos): **el curso no lo trata** (comprobado con la transcripción
  completa). Lo que usa GEM OS sobre esto viene de la práctica y del conocimiento general de Make.
  *Corrección 2026-11-12:* una versión anterior de este fichero citaba `00:24:26` como «el curso lo trata como
  secundario». Esa frase habla del panel **Grid** (`00:24:08`–`00:24:32`), no de errores. Citado mal por mí.
