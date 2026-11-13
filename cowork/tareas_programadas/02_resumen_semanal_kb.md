# Tarea programada 02 — Resumen semanal de la KB

| Campo | Valor |
|---|---|
| Nombre | GEM OS · Novedades de la KB |
| Cadencia | Semanal (lunes) |
| Modo de aprobación | Manual |
| Carpeta | `cowork/` — **necesita la app de escritorio abierta** |
| Conectores | Ninguno |
| Skills | `reglas-gem-os` (plugin gem-os) |

El espejo `contexto/` se refresca solo cada 2 h con el agente autónomo y en cada edición
desde Claude Code. Para forzarlo: `python scripts/build_cowork.py contexto`.

## Prompt

```
<contexto>
Mi Knowledge Base se alimenta sola con transcripciones de mis mentores de dropshipping
(Adrián Sáenz es la fuente primaria; el resto son complementarias). Cada lunes quiero saber
qué entró nuevo y si algo afecta a cómo trabajo, sin releer todas las transcripciones.
</contexto>

<material>
- contexto/_MANIFEST.json: cada archivo trae su fecha en el campo "modificado".
- contexto/kb/: un archivo por vídeo, con marcas de tiempo.
- contexto/reglas/reglas-financieras.md: las reglas vigentes.
</material>

<restricciones>
- Carga primero la skill `reglas-gem-os`.
- Trabaja solo con los archivos de contexto/kb/ cuyo "modificado" sea de los últimos 7 días.
  Si no hay ninguno, dilo en una línea y termina.
- Cada afirmación lleva su origen: nombre del archivo y marca de tiempo (vídeo hh:mm:ss).
  Lo que no tenga marca de tiempo en el archivo, no lo cites como dicho por el mentor.
- No inventes cifras ni completes lo que la transcripción no dice.
- Si algo nuevo CONTRADICE una regla de reglas-financieras.md, señálalo aparte. No propongas
  cambiar la regla: las reglas de Adrián Sáenz prevalecen y las cambia una persona.
- No navegues por la web: solo los archivos indicados.
- Escribe únicamente en salidas/resumen_kb/. No modifiques contexto/.
</restricciones>

<formato>
Archivo salidas/resumen_kb/AAAA-MM-DD.md con:
1. Qué entró (tabla: archivo, mentor, tema, fecha).
2. Ideas accionables, máximo 7, cada una con su cita.
3. Contradicciones con las reglas vigentes (o «ninguna»).
4. Hoja de incidencias: archivos ilegibles, duplicados, transcripciones sin marcas de tiempo.
</formato>

Resume lo que ha entrado en la KB en los últimos 7 días.
```

## Qué no hace

No ingiere vídeos nuevos (eso es `youtube_monitor` + `transcript_cleaner`) ni cambia reglas,
skills o procedimientos.
