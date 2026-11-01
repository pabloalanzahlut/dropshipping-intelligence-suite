---
name: dropshipping-financial-validation
description: Habilidad para auditar viabilidad de listings bajo las reglas de Adrián Sáenz e Iván Caicedo.
scope: workspace
---

# Lógica Operativa de la Habilidad
Cada vez que el usuario te solicite evaluar código de extracción de productos o bases de datos de listings:
1. Valida la regla estricta del 3x (PVP = Costo Origen * 3).
2. Asegura que el margen bruto operativo no caiga del 70%.
3. Restringe y emite reportes de riesgo logístico si el peso del paquete candidato supera los 1.2 kg.
