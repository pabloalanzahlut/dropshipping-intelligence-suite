# Ideas de contenido — Electric Vibration Massage Comb (Red Light, scalp brush)

Fuente de datos: ficha AutoDS Marketplace (Haili Happy Shopping Store, ID 3256808990542242), leída el 2026-11-10.

## Datos de la ficha (tal cual, sin asumir)
| Dato | Valor AutoDS |
|------|--------------|
| Coste artículo | $21.74 |
| Envío | $11.41 / 15 días hábiles, desde CN, **a Estados Unidos** |
| Precio de venta en AutoDS | $129 (competidores: $129 y $79.99) |
| Pedidos | 7+ · Reseñas: 0 |
| Engagement score | 20 (Inactive/Mild) · Saturation score 80 (Full market) |
| Público | 20-40 años, hombres y mujeres, cuidado capilar/autocuidado |

## Alertas según reglas GEM OS (validar antes de invertir)
- **Coste landed (US): $21.74 + $11.41 = $33.15.** Con PVP $79.99 el multiplicador es 2,41x (COLD). Para llegar a 3x hace falta PVP >= $99.45.
- **Coste de origen $21.74 está fuera del rango $5-15** de la regla de Adrián.
- **DATA_GAP:** envío a **Italia** (coste y días), tipo de batería, marcado CE/ficha técnica del proveedor, política de devolución. Sin esto no se puede cerrar `/validar-financiero`.
- Saturación 80 (mercado lleno) y actividad baja: pasar `/refutar-producto` antes de producir muchos vídeos.
- Fees 4,0% + cancelaciones 10,1% restan margen: con PVP 79.99 queda poco para publicidad (ROAS >= 2).

## Qué NO decir nunca en los vídeos (el pipeline lo bloquea)
Crecimiento del cabello, anticaída, calvicie, "cura", "terapia", "clínicamente probado". La ficha del proveedor los menciona, pero en UE/Meta/TikTok son claims de salud sin prueba. La luz roja se muestra como característica, sin prometer efecto.
Tampoco plazos de envío de 24-48h: usar los días reales que confirme el proveedor para Italia.

## Qué SÍ se puede mostrar
Sensación de masaje, vibración, uso durante la ducha o la rutina, aplicador de aceite, tamaño en la mano, antes/después de **la rutina** (no del pelo).

## Hooks por fórmula (italiano, con traducción)
| # | Fórmula | Hook en pantalla (<= 6 palabras) | Idea de plano |
|---|---------|-----------------------------------|---------------|
| 1 | DEM | Massaggio alla testa in 10 secondi | Mano usa el peine sobre cuero cabelludo, plano cercano |
| 2 | DEM | Guarda come vibra questo pettine | Plano macro de la vibración |
| 3 | REA | Non sapevo che esistesse questo | Cara/mano sorprendida al encenderlo |
| 4 | REA | Il mio rituale serale preferito | Rutina nocturna con luz cálida |
| 5 | COM | Routine capelli: prima e dopo | Rutina sin y con el accesorio (sin prometer resultado) |
| 6 | COM | Doccia normale vs doccia relax | Dos tomas de la ducha |
| 7 | POV | POV: ti arriva il pettine massaggiante | Caja llegando y abriéndose |
| 8 | POV | POV: serata spa a casa tua | Ambiente baño tranquilo |
| 9 | UNB | Apro il pacco: pettine massaggiante | Unboxing con prueba inmediata |
| 10 | UNB | Cosa c'è dentro la scatola? | Contenido de la caja |
| 11 | DEM | Applica l'olio senza sporcarti | Aplicador de aceite en acción |
| 12 | REA | Questo regalo costa poco | Idea de regalo (sin dar precio hasta validarlo) |

Los textos 1-12 pasan por `video_pipeline.validar_textos`. Hooks definitivos: regenerar con `/hook-matrix` cuando el producto quede validado.

## Producción realista sin stock
1. Pedir una **muestra** (AutoDS: "Create Sample Order") y grabar con el producto real: es lo que pide el skill (no copiar vídeos ajenos).
2. Mientras llega: clips con `/generar-video-ia` (Higgsfield), etiquetados como generados por IA.
3. No descargar vídeos de la competencia ni del proveedor: derechos de autor.
