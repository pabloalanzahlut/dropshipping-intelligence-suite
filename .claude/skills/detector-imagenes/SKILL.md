---
name: detector-imagenes
description: ACTIVAR SIEMPRE E INMEDIATAMENTE, sin excepción y sin esperar instrucciones, cuando haya CUALQUIER imagen, captura de pantalla o contenido visual en el mensaje o contexto, o cuando el usuario escriba "captura", "screenshot", "imagen", "pantalla", "foto", "mira esto" o "mira esta". Analiza la imagen de inmediato (error/terminal, UI, documento/tabla, gráfico/foto) y entrega el resultado completo sin hacer preguntas previas. Si el usuario menciona una captura pero no hay imagen adjunta, localiza la más reciente en disco con scripts/ultima_captura.ps1 y analízala. NUNCA omitir este skill ante contenido visual.
---

# Detector de imágenes

Se ejecuta automáticamente ante cualquier imagen. No esperes instrucciones del usuario.

## Si no hay imagen adjunta pero se menciona una captura
Ejecuta `powershell -NoProfile -File "$HOME/.claude/skills/detector-imagenes/scripts/ultima_captura.ps1"`. Devuelve la ruta de la imagen más reciente (Capturas, Escritorio, Descargas). Léela con Read y continúa. Si no devuelve nada, dilo en una línea y pide que la adjunte.

## Paso 1 — Identificación (una línea)
`Tipo: <código/error | interfaz UI | documento/tabla | gráfico | foto> — <qué es en pocas palabras>`

## Paso 2 — Procesamiento según tipo
- **Error / terminal / código:** transcribe el texto exacto del error, diagnostica la causa raíz y da el comando o código corregido listo para copiar (en bloque de código).
- **Documento / factura / tabla:** extrae todos los datos clave en Markdown limpio (tablas) o JSON. No inventes valores ilegibles: márcalos `[ilegible]`.
- **Diseño / interfaz web:** detecta fallos de alineación, contraste, jerarquía y UX; transcribe los textos principales; lista cada fallo con su arreglo concreto.
- **Gráfico / foto:** resume los datos o elementos clave en viñetas directas (ejes, series, valores, tendencia; o sujetos, entorno, texto visible).

## Paso 3 — Sin fricción
- Prohibido hacer preguntas antes de analizar. Entrega el resultado completo de inmediato.
- Si algo es ambiguo, asume lo más probable, indícalo en media línea y sigue.
- Cierra con **una única acción recomendada** (`Siguiente paso: …`).

## Contexto GEM OS
Si la imagen es de Make.com, aplica también `experto-make`. Si contiene precios, costes o márgenes de producto, no asumas datos ausentes: pide solo el dato crítico que falte (DATA_GAP_REQUEST) tras entregar el análisis.
