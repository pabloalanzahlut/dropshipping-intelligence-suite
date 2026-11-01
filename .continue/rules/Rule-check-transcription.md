---
name: rule-check-transcription
description: Protocolo de validación técnica y normalización de transcripciones entrantes.
---

# 🔍 TRANSCRIPTION VALIDATION PROTOCOL

### <condiciones_de_integridad>
1. **Contenido:** La transcripción debe contener texto (no vacía).
2. **Unicidad:** El `hash` de la transcripción no debe existir previamente en la base de datos (evitar duplicados).
3. **Encoding:** El texto debe estar estrictamente normalizado en **UTF-8**.
4. **Sanitización:** No debe contener caracteres nulos (`\0`) o secuencias de control inválidas que corrompan la base de datos.
</condiciones_de_integridad>

### <acciones_de_clasificación>
- **PASS:** Si cumple todos los criterios, etiquetar como `STATUS: VALIDA`.
- **FAIL:** Si falla un solo criterio, etiquetar como `STATUS: FALLIDA` y emitir una alerta técnica detallando el error.
- **Log:** Registrar obligatoriamente el `timestamp` del proceso de verificación.
</acciones_de_clasificación>

<connection_point>
Esta regla es el disparador obligatorio para `@gem-data-insertion`. Ningún dato llega al GEM sin el sello de `VALIDA` de este protocolo.
</connection_point>
