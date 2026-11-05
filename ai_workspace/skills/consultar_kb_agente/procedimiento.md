# Skill: Consultar Knowledge Base (Agente IA Interno)

**ID:** `consultar_kb_agente`
**Versión:** 1.0.0
**Propósito:** Permite al agente IA web interno responder consultas del operador sobre productos, estrategias y métricas indexadas en la Knowledge Base.

**Audiencia:** SOLO el operador (uso interno). Este agente NO responde a clientes finales de la tienda.
**Fuente de datos:** `ai_workspace/knowledge_base/kb_*.md` + `ai_workspace/memory/kb_index.json`

---

## Tipos de Consulta Soportados

### 1. Consultas de Producto
- "¿Qué productos HOT tenemos indexados esta semana?"
- "¿Hay algún producto de fitness con margen >5x?"
- "Muéstrame los últimos 3 productos WARM"

**Respuesta esperada:**
```
Producto: {nombre}
Clasificación: HOT/WARM
Margen: {margen}x | Precio ref: ${precio}
Fuente: {canal} ({video_id}) — {fecha}
```

### 2. Consultas de Estrategia
- "¿Qué estrategia de TikTok Ads funcionó mejor según la KB?"
- "¿Qué hooks usa {canal}?"
- "¿Cuál es el ROAS promedio que mencionan los creadores?"

**Respuesta esperada:**
```
Estrategia: {nombre}
Resultado: {resultado}
Fuente: {canal} ({video_id})
Notas: {descripcion}
```

### 3. Consultas de Proveedor
- "¿Qué proveedores de electrónica están bien valorados en la KB?"
- "¿Aparece CJ Dropshipping en algún video reciente?"

### 4. Consultas de Métricas Agregadas
- "¿Cuál es el margen promedio de los productos HOT en la KB?"
- "¿Qué conversion rate mencionan los creadores?"

**Respuesta esperada:** Valor calculado + rango (min-max) + número de fuentes

### 5. Consultas de Lecciones
- "¿Qué errores comunes menciona la KB?"
- "¿Qué aciertos se repiten en varios videos?"

---

## Protocolo de Respuesta

1. **Buscar** en `kb_index.json` los archivos relevantes (filtrar por clasificacion, fecha, canal)
2. **Leer** los archivos KB correspondientes
3. **Extraer** la entidad pedida
4. **Formatear** la respuesta con: dato + fuente (video_id + canal) + fecha de indexación
5. **Citar siempre la fuente**: nunca dar un dato sin indicar de qué video proviene

### Formato estándar de respuesta
```
[CONSULTA KB — {fecha_hoy}]

{respuesta_principal}

Fuentes:
- {video_id} | {canal} | Indexado: {fecha} | Clasificación: {clasificacion}
(+ N más si aplica)

Confianza: Alta/Media/Baja
Última actualización KB: {fecha_ultimo_kb}
```

---

## Restricciones

- **Nunca inventar datos** no presentes en la KB → si no hay información, responder: "No tengo datos indexados sobre eso. ¿Quieres que busque un video sobre el tema?"
- **No responder preguntas de clientes finales** sobre pedidos, envíos o garantías → redirigir a Shopify Inbox
- **No ejecutar acciones** (no publicar, no escribir a Shopify) desde esta consulta → solo lectura
- **Datos financieros**: siempre aclarar que son referencias de videos, no garantías

---

## Integración con el Pipeline

```
YouTube Monitor
      ↓
import_playlist.py
      ↓
clasificar_productos (HOT/WARM)
      ↓
ingerir_transcripcion_kb  ← guarda en KB
      ↓
consultar_kb_agente  ← operador consulta
```

El agente web lee la KB generada por `ingerir_transcripcion_kb`. No tiene acceso directo a las transcripciones crudas ni a la base de datos SQLite.
