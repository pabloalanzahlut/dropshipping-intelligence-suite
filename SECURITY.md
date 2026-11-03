# Security Policy — GEM OS

## Variables de entorno y secrets

**NUNCA** commitear archivos `.env` o API keys directamente en el código.

| Variable | Almacenamiento correcto |
|----------|------------------------|
| `MAKE_WEBHOOK_TIKTOK` | GitHub Secrets / `.env` local |
| `OPENROUTER_API_KEY` | GitHub Secrets / `.env` local |
| `REMOVEBG_API_KEY` | GitHub Secrets / `.env` local |
| `SHOPIFY_ACCESS_TOKEN` | GitHub Secrets / `.env` local |

Usar siempre `.env.example` como plantilla, nunca el `.env` real.

## Reportar una vulnerabilidad

Enviar reporte privado a: **pabloalanzahlut@gmail.com**

Incluir:
1. Descripción del problema
2. Pasos para reproducir
3. Impacto potencial

Tiempo de respuesta: **48 horas**.

## Versiones soportadas

| Versión | Soporte |
|---------|---------|
| GEM OS v2.x | ✅ Activo |
| GEM OS v1.x | ❌ Sin soporte |
