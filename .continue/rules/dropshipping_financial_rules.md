# REGLAS FINANCIERAS DE VALIDACIÓN (ADRIÁN SÁENZ & IVÁN CAICEDO)

Cada vez que el usuario te pida analizar un producto, calcular un margen o estructurar datos en SQLite, debes aplicar y validar estas directrices:

1. **Regla Estricta del 3x:** El precio de venta sugerido (PVP) debe ser obligatoriamente tres veces el costo de origen del proveedor (CO).
2. **Margen Bruto del 70%:** El margen neto operacional no puede bajar del 70%. Si un cálculo da menor a este benchmark, adviértelo inmediatamente en la consola.
3. **Fricción Logística:** Restringe de forma rígida cualquier artículo con un peso superior a 1.2 kg o que contenga baterías de litio sueltas para mitigar contracargos y disputas en Stripe/PayPal.
