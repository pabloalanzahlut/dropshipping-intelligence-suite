(function () {
  "use strict";
  window.__BRAND__ = {
    name: "GEM OS",
    tagline: "Inteligencia para dropshipping global.",
    version: "v2.1",
    cta: "Empezar Gratis",
    ctaUrl: "#pricing",

    nav: [
      { label: "Cómo funciona", href: "#pipeline" },
      { label: "Funciones", href: "#features" },
      { label: "Precios", href: "#pricing" },
      { label: "Testimonios", href: "#testimonials" },
      { label: "FAQ", href: "#faq" },
    ],

    stats: [
      { value: "50K+", label: "Productos analizados" },
      { value: "3x", label: "Margen mínimo garantizado" },
      { value: "98%", label: "Precisión en clasificación" },
      { value: "< 2min", label: "Del vídeo a la ficha" },
    ],

    features: [
      {
        icon: "🔍",
        title: "Product Hunter",
        desc: "Clasifica productos en HOT, WARM o COLD en segundos. Solo pasan los que superan el margen 3x.",
        tag: "IA",
      },
      {
        icon: "✍️",
        title: "Funnel Builder",
        desc: "Copy AIDA completo para landing pages. Título, beneficios, garantías y CTA listos para publicar.",
        tag: "Copy",
      },
      {
        icon: "🎬",
        title: "Media Buyer",
        desc: "Scripts TikTok de 15–30 segundos con hook en los primeros 3 segundos. Listos para grabar.",
        tag: "Video",
      },
      {
        icon: "🏪",
        title: "Ficha Shopify",
        desc: "Descripción optimizada SEO, bullet points y metadatos. Lista para pegar en tu tienda.",
        tag: "Shopify",
      },
      {
        icon: "🤖",
        title: "Auto-publicación",
        desc: "Envía guiones a Make.com y publica en TikTok de forma automática. Cero intervención manual.",
        tag: "Make.com",
      },
      {
        icon: "🖼️",
        title: "Imagen Premium",
        desc: "Remoción de fondo automática con remove.bg. Fotos limpias para Shopify en un clic.",
        tag: "remove.bg",
      },
    ],

    pipeline: [
      { step: "01", label: "Monitor YouTube", desc: "Detecta vídeos virales de productos en tendencia." },
      { step: "02", label: "Transcript Cleaner", desc: "Limpia y extrae datos del vídeo automáticamente." },
      { step: "03", label: "Product Hunter", desc: "Clasifica HOT / WARM / COLD con reglas 3x." },
      { step: "04", label: "Funnel Builder", desc: "Genera copy AIDA para landing page completa." },
      { step: "05", label: "Media Buyer", desc: "Crea script TikTok listo para grabar." },
      { step: "06", label: "Publicar", desc: "Auto-publica en TikTok vía Make.com." },
    ],

    plans: [
      {
        name: "Starter",
        price: "0",
        period: "gratis para siempre",
        features: ["5 productos/mes", "Product Hunter básico", "Ficha Shopify", "Soporte comunidad"],
        cta: "Empezar Gratis",
        highlight: false,
      },
      {
        name: "Pro",
        price: "47",
        period: "/mes",
        features: ["Productos ilimitados", "Pipeline completo", "Auto-publicación TikTok", "remove.bg 50/mes", "Soporte prioritario", "Acceso a Knowledge Base"],
        cta: "Empezar 7 días gratis",
        highlight: true,
      },
      {
        name: "Agency",
        price: "147",
        period: "/mes",
        features: ["Todo en Pro", "5 tiendas Shopify", "OpenRouter económico", "API access", "Onboarding 1:1", "Slack privado"],
        cta: "Contactar",
        highlight: false,
      },
    ],

    testimonials: [
      {
        name: "Marcos V.",
        role: "Dropshipper · España",
        text: "Pasé de analizar 3 productos al día a 40. El sistema rechaza automáticamente lo que no cumple el margen 3x. Es como tener un socio analítico disponible 24h.",
        avatar: "M",
        stars: 5,
      },
      {
        name: "Laura P.",
        role: "Tienda Shopify · México",
        text: "El script de TikTok que genera es exactamente lo que yo tardaba 2 horas en escribir. Ahora lo tengo en 2 minutos. La diferencia en ventas fue inmediata.",
        avatar: "L",
        stars: 5,
      },
      {
        name: "Andrés K.",
        role: "Agencia de dropshipping · Colombia",
        text: "Con GEM OS gestionamos 5 tiendas en paralelo. El pipeline completo automatiza lo que antes requería 3 personas. ROI en la primera semana.",
        avatar: "A",
        stars: 5,
      },
    ],

    faqs: [
      {
        q: "¿Necesito saber programar para usar GEM OS?",
        a: "No. GEM OS funciona con comandos slash simples como /clasificar-producto o /pipeline-completo. Si puedes escribir en un chat, puedes usar GEM OS.",
      },
      {
        q: "¿Qué pasa si un producto no cumple el margen 3x?",
        a: "GEM OS lo rechaza automáticamente con un aviso claro. El sistema nunca alucina datos financieros ni asume costos — si falta un dato, te lo pide antes de continuar.",
      },
      {
        q: "¿Funciona con cualquier proveedor de dropshipping?",
        a: "Sí. GEM OS analiza la información que tú le proporcionas (precio de origen, peso, dimensiones) y aplica las reglas financieras sobre esos datos reales.",
      },
      {
        q: "¿Cómo se conecta con Make.com y TikTok?",
        a: "Configuras un webhook en Make.com y añades tu clave en el archivo .env. Después, el comando /publicar-tiktok envía el guión automáticamente al flujo.",
      },
      {
        q: "¿Qué pasa con los baterías de litio y productos prohibidos?",
        a: "GEM OS tiene reglas inmutables: baterías de litio sueltas y productos que superan 1.2 kg se rechazan automáticamente. No hay forma de saltarse estas reglas.",
      },
    ],

    contact: {
      email: "hola@gemos.io",
    },
  };
})();
