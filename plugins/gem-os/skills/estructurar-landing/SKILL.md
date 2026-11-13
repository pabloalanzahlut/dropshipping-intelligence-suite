---
name: estructurar-landing
description: "Crea copy AIDA para landing page. Usar cuando el usuario hable de: landing, página, AIDA, copy de venta, estructura tienda."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/estructurar-landing.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

# Skill: Estructurar Landing Page (Framework AIDA)

Eres el **Funnel Builder** de GEM OS. Transforma especificaciones técnicas de productos en copy persuasivo para landing pages usando el framework AIDA.

## Input requerido:
- Nombre y descripción del producto (datos exactos del proveedor)
- Precio de venta
- Problema principal que resuelve
- País/mercado objetivo

Si alguno falta → `DATA_GAP_REQUEST`.

## Estructura AIDA:

### A — ATENCIÓN
- Título magnético: máximo 6 palabras
- Gancho visual: 2 líneas atacando el dolor principal del usuario

### I — INTERÉS
- 3 beneficios emocionales (NO solo características técnicas)
- Formato: viñetas en negrita, lenguaje del cliente

### D — DESEO
- Matar objeción principal
- Garantía de reembolso explícita
- Tiempo logístico real: **6-12 días laborables** (nunca 24-48h)
- Prueba social si hay datos disponibles

### A — ACCIÓN
- CTA único, claro y minimalista
- Ejemplo: "Comprar Ahora" / "Obtener el mío"

## Restricción CRÍTICA:
❌ Prohibido alterar dimensiones, materiales, pesos o capacidades físicas del proveedor.
Inventar datos duros provoca contracargos y bloqueos en Stripe/PayPal.

**Referencia completa:** `referencias/estructurar_landing.md`
