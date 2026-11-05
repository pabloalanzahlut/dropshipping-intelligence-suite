# app/static/ — Assets locales GEM OS

Este directorio sirve archivos estáticos montados en FastAPI bajo `/static`.

## Estructura

```
app/static/
├── vendor/          ← librerías JS/CSS descargadas de CDN
│   ├── alpine.min.js        (Alpine.js 3.14.1)
│   └── tailwind.cdn.js      (Tailwind CDN play — solo dev)
├── css/
│   └── gem.css              (tokens CSS globales GEM OS)
└── README.md
```

## Uso

Montar en dashboard_server.py:
```python
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="app/static"), name="static")
```

Referenciar en templates:
```html
<script src="/static/vendor/alpine.min.js" defer></script>
```

## Descargar vendors

```bash
# Alpine.js
curl -Lo app/static/vendor/alpine.min.js \
  https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js

# Tailwind CDN (dev only — para prod usar CLI build)
curl -Lo app/static/vendor/tailwind.cdn.js \
  https://cdn.tailwindcss.com
```

> Nota: Tailwind CDN play es solo para desarrollo. Para producción
> usar `npx tailwindcss` y generar un CSS minificado.
