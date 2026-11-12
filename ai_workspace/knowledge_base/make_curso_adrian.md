# Make — extractos verificados del curso de Adrián Sáenz

**Regla:** cada afirmación lleva `video hh:mm:ss`, copiado de la transcripción automática de YouTube
(panel «Mostrar transcripción», extraído 2026-11-12). Lo que no tiene marca de tiempo NO viene del curso.
La transcripción es automática: los nombres propios y las cifras pueden estar mal escritos; ante duda, revisar el vídeo.

## Fuentes

| ID | Título | Duración | Estado |
|----|--------|----------|--------|
| `WxCxyRAnVQM` | Curso Completo De Make: Cómo Crear y Vender Automatizaciones IA (Adrián Sáenz con Juan Pe) | 3 h 55 min | **Leído** (transcripción completa extraída; 1.836 segmentos) |
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
- Vigilar el panel de créditos (`00:40:51`). Avisa de una opción activada que puede seguir consumiendo
  operaciones sin límite «hasta quedarnos pobres» y recomienda quitarla (`00:41:26`–`00:41:50`).
  *La transcripción no nombra la opción: comprobar en pantalla cuál es antes de actuar.*
- Un disparador por intervalo se ejecuta y gasta créditos aunque no haya datos nuevos (`01:06:02`);
  uno instantáneo se ejecuta solo cuando entra el dato, no por intervalo (`01:06:45`–`01:07:32`,
  «esto es importante»).

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

## Pendiente de verificar con transcripción
- `Phal-sPAunk` desde `07:17:35` (Funciones de Make, ~33 min): sin leer.
- `MGvUGEk1O9Y` (n8n): sin leer. Decisión mientras tanto: **Make es suficiente**; n8n del curso va
  autoalojado en un VPS (según la descripción del vídeo), lo que añade mantenimiento y coste.
- Manejo de errores avanzado (error handlers, reintentos): el curso lo trata como secundario
  (`00:24:26`: «yo esto no lo utilizo»). Lo que usa GEM OS sobre esto viene de la práctica, no del curso.
