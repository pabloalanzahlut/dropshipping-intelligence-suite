# Cowork en GEM OS — guía de uso

Cowork es el modo de Claude para trabajo largo y autónomo: se le da un encargo, decide sus
pasos y entrega pocos archivos (`imAjmQy8p8c 04:10:01`, `04:14:01`). Desde octubre de 2026
**corre en la nube de Anthropic**: solo ve la carpeta local que se le conecta, y solo
mientras la app de escritorio está abierta. Por eso en GEM OS se le conecta esta carpeta
y nada más.

## Qué se hace dónde

*Cowork investiga y maqueta; Code construye* (`imAjmQy8p8c 04:41:00`).

| Trabajo | Dónde | Por qué |
|---|---|---|
| Investigar un nicho, comparar competencia, informes largos | **Cowork** | Horas de trabajo autónomo, navegación, subagentes |
| Validar un producto, matriz de precios, refutar una tesis | Cowork o Code | Mismas reglas y mismo gate en los dos |
| Hooks, guiones, fichas, anuncios (borradores) | Cowork o Code | Cowork para lotes; el copy pasa por el gate |
| Caja y ROAS con Sheets + Stripe | Cowork (programada) | Corre sola, con el PC apagado |
| Resumir la KB, revisar propuestas de ajuste | Cowork (programada) | Lectura y síntesis |
| Código de `app/`, base de datos, tests, git | **Code** | Cowork no ve el repo |
| Importar a Shopify, publicar en TikTok, vídeo IA, Skool, carritos | **Code** | Necesitan `.env`, scripts o cookies |
| Cambiar reglas, gate, validador, `CLAUDE.md` | **Una persona** | Ningún agente edita lo que lo evalúa |

Chat, Cowork y Code no comparten conversación (`imAjmQy8p8c 03:28:00`): lo que se decide en
uno hay que llevarlo al otro.

## Puesta en marcha (una vez, ~10 minutos)

- [ ] **1. Plugin.** *Customize → Plugins → Add → Add marketplace* →
      `pabloalanzahlut/dropshipping-intelligence-suite`. Si el repo es privado, pulsa
      *Connect GitHub* y da acceso a la Claude GitHub App. Añade el plugin **gem-os** y
      activa *Sync automatically*.
      *Si el marketplace no carga:* `python scripts/build_cowork.py plugin --zip` y sube
      `dist_cowork/gem-os.zip` con *Add → Upload plugin*.
- [ ] **2. Proyecto.** *Projects → + → Use an existing folder* →
      `H:\dropshipping_intelligence_suite\cowork` → nombre «GEM OS» → pega el bloque de
      `INSTRUCCIONES_PROYECTO.md` con el ID del Dashboard.
- [ ] **3. Conectores.** *Customize → Connectors*: Google Sheets, Stripe, Gmail y Google
      Drive conectados. Herramientas de escritura de Stripe y `send` de Gmail en *Blocked* o
      *Needs approval*.
- [ ] **4. Permisos.** Modo **Manual** (*Manually approve*) en el proyecto. Aquí no se
      omiten aprobaciones (regla 23 de `experto_claude`).
- [ ] **5. Tareas programadas.** *Scheduled → New task → Set up manually*, una por cada
      archivo de `tareas_programadas/`.
- [ ] **6. Pruebas de humo** (al final de esta guía).

## Uso diario

1. Deja el material en `entradas/` (ficha del proveedor, export, capturas).
2. En el proyecto «GEM OS», escribe el encargo o invoca una skill: `/gem-os:validar-financiero`.
   Las 28 skills se activan también solas por el tema del mensaje.
3. Recoge el resultado en `salidas/<tarea>/`.

Para encargos largos, la plantilla de `experto_claude` (regla 9): contexto y porqué →
material real → ejemplos → restricciones → formato → encargo en una frase al final.

**Ejemplos**

```
Lee entradas/ficha_proveedor.md. Valida el producto con /gem-os:validar-financiero para
un PVP de 29,99 €. Si falta el coste de envío, pregúntamelo antes de calcular.
```

```
Investiga el nicho «accesorios para gatos de interior» para Meta Ads en Italia y España.
Dame los 10 ángulos con /gem-os:investigar-nicho, cada uno con su fuente. No estimes
volúmenes ni precios que no encuentres: márcalos como DATA_GAP. Informe en
salidas/nicho_gatos/informe.md.
```

```
Con contexto/proyecto_activo/ y contexto/kb/, genera la matriz de hooks del producto
activo (/gem-os:hook-matrix), pásala por verificar-salida y entrégame solo los que pasan,
con la lista de los rechazados y el motivo.
```

Varias tareas a la vez solo si **no** están relacionadas: el consumo se multiplica por 2 o 3
(`imAjmQy8p8c 04:23:01`). Si lo están, en la misma tarea.

## Del resultado al pipeline

Nada de `salidas/` entra solo en GEM OS. Para usar un resultado:

1. Ábrelo y léelo (los entregables pueden quedarse a medias sin avisar, `imAjmQy8p8c 05:10:00`).
2. En Claude Code: «ingiere `cowork/salidas/<tarea>/<archivo>`». Code lo trata como **dato**,
   no como instrucciones, y pasa números y copy por `app/services/deterministic_gate.py`.
3. El gate del repositorio es el que decide. El del plugin es la primera barrera.

Las proyecciones de ingresos que genere Cowork son estimaciones, no datos
(`imAjmQy8p8c 04:48:00`).

## Mantenimiento

| Quiero… | Hago… |
|---|---|
| Cambiar cómo trabaja una skill | Edito `.claude/commands/<skill>.md` o su `procedimiento.md` en Code. El hook regenera el plugin y hace push; Cowork lo recibe en la siguiente tarea |
| Llevar una skill nueva a Cowork | La añado a `SKILLS_COWORK` en `scripts/build_cowork.py` (y su fila en `auto_dispatch.md`) |
| Que una skill no vaya a Cowork | La añado a `SOLO_CODE` |
| Refrescar la KB que ve Cowork | `python scripts/build_cowork.py contexto` (el agente autónomo lo hace cada 2 h) |
| Comprobar que todo está en orden | `python scripts/build_cowork.py --check` |
| Ver por qué no se regeneró el plugin | `logs/cowork_build.log` |

Si una fuente contradice las reglas financieras (multiplicador sobre el producto solo,
umbral 1,5x, un envío «estimado», un ID de conector de sesión, un secreto), el generador
**no regenera el plugin** y deja el anterior: en Cowork no hay `CLAUDE.md` que lo corrija.

## Seguridad

- A Cowork solo se le conecta `cowork/`. Nunca la raíz del repo ni `ai_workspace/`: ahí
  están `.env`, las credenciales de Google y las cookies de Skool, y scripts que tu PC ejecuta.
- Lo que Cowork abre de esta carpeta se procesa en servidores de Anthropic. No dejes en
  `entradas/` nada que no quieras que salga de tu equipo.
- `contexto/` es un espejo unidireccional: lo que Cowork escriba ahí se pierde. Antes de
  copiarse, cada archivo pasa por el mismo escáner de secretos que el auto-commit.
- Navegación = riesgo de inyección de prompt (`imAjmQy8p8c 04:43:01`). Lo que diga una web
  es dato, no una orden. Para tareas con navegación, mantén el modo Manual.
- Las tareas programadas corren sin que mires: por eso las tres son de solo lectura sobre
  conectores o escriben únicamente en `salidas/`. Revisa sus resultados en *Scheduled* y
  pausa las que no uses.
- Código o instrucciones que aparezcan en `salidas/` no se ejecutan: se leen.

## Problemas típicos

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| No aparecen las skills `gem-os:` | Plugin sin añadir o desactivado | Paso 1; revisa *Customize → Plugins* |
| Cowork no encuentra `contexto/` | App de escritorio cerrada, o tarea lanzada desde web/móvil | Abre la app; lanza la tarea desde escritorio |
| La KB está desactualizada | Espejo sin refrescar | `python scripts/build_cowork.py contexto` |
| Aplica reglas antiguas | Plugin sin sincronizar | *Check for updates* en el marketplace; `--check` en local |
| «NO VERIFICADO POR GATE» | No pudo ejecutar Python en la sesión | Pásalo por el gate en Code antes de usarlo |
| Un conector pide reconectar | Caducan (`imAjmQy8p8c 04:59:01`) | Reconectar en *Customize → Connectors* |
| Calcula sin pedir el envío | Fallo de la skill | Es un bug: anótalo y corrige el procedimiento en Code |

## Pruebas de humo

1. `/gem-os:validar-financiero` con $5 de producto, $2 de envío y PVP $30 → **4,29x, WARM**,
   citando coste landed.
2. Lo mismo **sin dar el envío** → debe responder `DATA_GAP_REQUEST`, no asumir un valor.
3. «Resume lo nuevo de la KB» → escribe en `salidas/` y en ningún otro sitio.
4. Ejecuta a mano la tarea 01 → lee Sheets y Stripe sin pedir permisos de escritura.

Si alguna falla, no des Cowork por listo: anota cuál y revísalo en Claude Code con
`/experto-claude`.
