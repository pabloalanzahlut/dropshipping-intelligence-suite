---
name: dropshipping-financial-validation
description: Habilidad para auditar viabilidad de listings bajo las reglas de Adrián Sáenz e Iván Caicedo.
scope: workspace
---

# Lógica Operativa de la Habilidad
Cada vez que el usuario te solicite evaluar código de extracción de productos o bases de datos de listings:
1. Valida el multiplicador sobre el coste landed (producto + envío): mínimo 2x (rechazar) y objetivo 3x (advertir).
2. Calcula el margen neto descontando fees 4,0 % y cancelaciones 10,1 % del PVP.
3. Rechaza baterías de litio sueltas. No apliques umbral de margen % ni límite de peso: el curso no los fija.
