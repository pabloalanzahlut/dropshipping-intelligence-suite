import os
import logging
import requests
from typing import Optional

from app.core.retry_decorator import with_retry


def sanitize_api_key(key: str) -> str:
    """
    Sanitiza una API key para logging, mostrando solo los últimos 4 caracteres.
    
    Args:
        key: API key completa
    
    Returns:
        Key sanitizada: 'sk-...XYZ' o '<vacia>' si está vacía
    """
    if not key:
        return "<vacia>"
    if len(key) <= 8:
        return f"{'*' * (len(key) - 4)}{key[-4:]}"
    return f"{key[:3]}...{key[-4:]}"


class OpenRouterTranscriptionCleaner:
    def __init__(self, model_name: str = "deepseek/deepseek-chat"):
        # ◄ ADICIONADO: Configuración adaptativa para FreeLLMAPI sin alterar las variables originales
        self.freellm_api_key = os.getenv("FREELLM_API_KEY")
        self.freellm_url = os.getenv("FREELLM_BASE_URL") # Ejemplo: https://tu-instancia-freellmapi.com
        
        # Parámetros originales e inalterados de OpenRouter
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.model_name = model_name
        # Último fallo de comunicación (None si la última llamada respondió). Permite
        # distinguir «la IA dijo VACÍO» de «la IA no respondió»: ambos devuelven None.
        self.last_error: Optional[str] = None

        # Log sanitizado de inicialización
        logger = logging.getLogger(__name__)
        logger.info(
            f"[OPENROUTER] Inicializado. "
            f"OpenRouter Key: {sanitize_api_key(self.api_key)}, "
            f"FreeLLMAPI Key: {sanitize_api_key(self.freellm_api_key)}, "
            f"Modelo: {model_name}"
        )

        # Guardrails de Inicialización: Verifica que al menos exista una vía de conexión válida
        if not self.api_key and not self.freellm_api_key:
            raise ValueError("CRÍTICO: No se encuentra definida ninguna variable de entorno válida (OPENROUTER_API_KEY o FREELLM_API_KEY).")

    def clean_transcript(
        self,
        raw_text: str,
        canal: str = "Desconocido",
        rol_canal: str = "complementaria"
    ) -> Optional[str]:
        """Extrae datos estructurados de una transcripción, etiquetados con su fuente."""

        # Bloque de contexto de fuente: se inyecta en el prompt para que el modelo
        # sepa si está procesando la fuente primaria (Adrián Sáenz) o una complementaria.
        if rol_canal == "primaria":
            contexto_fuente = (
                f"CANAL: {canal} — FUENTE PRIMARIA.\n"
                "Este canal define las reglas financieras del sistema (multiplicadores, "
                "rangos de coste, ROAS). Extrae todos sus criterios con precisión máxima.\n"
            )
        else:
            contexto_fuente = (
                f"CANAL: {canal} — FUENTE COMPLEMENTARIA.\n"
                "Este canal aporta valor adicional (tácticas, productos, creativos, operaciones). "
                "IMPORTANTE: si el contenido sugiere reglas financieras distintas a las de Adrián Sáenz "
                "(multiplicadores, márgenes, costes), NO las extraigas como reglas — extráelas como "
                "'táctica observada en {canal}' sin que reemplacen los criterios de la fuente primaria.\n"
            )

        system_prompt = (
            "Eres un extractor de datos de alto rendimiento especializado en Dropshipping y Shopify.\n"
            "Tu única tarea es analizar la transcripción de un video de un experto, eliminar todo el relleno "
            "(saludos, intros, promociones, pantallas de ganancias falsas, solicitudes de suscripción) "
            "y devolver la información técnica estructurada en Markdown.\n\n"
            + contexto_fuente + "\n"
            "Divide los hallazgos estrictamente bajo estos tres subheadings si existen datos:\n"
            "### 1. Datos de Producto y Tendencias (Criterios, nichos, ángulos)\n"
            "### 2. Estructuras de Conversión y Copy (Ganchos, landing pages, apps)\n"
            "### 3. Logística, Tráfico y Legal (Presupuestos, segmentación, pasarelas, fletes)\n\n"
            "Abre cada sección con estos campos, uno por línea y con dos puntos. "
            "Son los que indexa la base de datos: si falta el dato, escribe 'No especificado' "
            "y no omitas la línea.\n\n"
            "En la sección 1:\n"
            "Producto: <nombre concreto del producto, no el tema del video>\n"
            "Nicho: <nicho de mercado>\n"
            "Wow Factor: <qué lo hace vendible en una frase>\n"
            "Margen: <solo el número del multiplicador, ej. 3.5>\n\n"
            "En la sección 2:\n"
            "Categoría: <landing_page | anuncio | email | ficha>\n"
            "Framework: <AIDA, PAS, u otro nombrado>\n"
            "Apps: <apps o herramientas mencionadas>\n\n"
            "En la sección 3:\n"
            "Fuente de Tráfico: <TikTok Ads, Meta Ads, orgánico...>\n"
            "Escalamiento: <estrategia de escalado>\n"
            "Logística: <notas de envío o proveedor>\n"
            "Peso: <solo el número en kg, ej. 0.4>\n"
            "Pasarela: <pasarelas de pago mencionadas>\n\n"
            "Debajo de esos campos añade las viñetas con el resto de hallazgos.\n\n"
            "Si el texto no contiene datos de valor para ninguna categoría, devuelve únicamente: VACÍO."
        )

        # ◄ ADICIONADO: Enrutamiento lógico asimétrico basado en la disponibilidad de FreeLLMAPI
        if self.freellm_api_key and self.freellm_url:
            target_url = self.freellm_url
            target_key = self.freellm_api_key
            # Si usas FreeLLMAPI y el modelo por defecto es de OpenRouter, puedes cambiarlo por uno gratuito nativo
            target_model = os.getenv("FREELLM_DEFAULT_MODEL", self.model_name)
        else:
            # Mantener el flujo original intacto si no se usa el gestor intermedio
            target_url = self.url
            target_key = self.api_key
            target_model = self.model_name

        headers = {
            "Authorization": f"Bearer {target_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com"
        }

        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Transcripción cruda a procesar:\n\n{raw_text}"}
            ],
            "temperature": 0.1
        }

        self.last_error = None
        try:
            response = self._post_with_retry(target_url, headers, payload)
            content = response.json()['choices'][0]['message']['content'].strip()
            return None if content == "VACÍO" else content
        except Exception as e:
            self.last_error = str(e)[:200]
            print(f"Error de comunicación en la pasarela de IA ({target_url}): {str(e)}")
            return None

    @with_retry(max_retries=3, base_delay=2.0, max_delay=30.0)
    def _post_with_retry(self, url: str, headers: dict, payload: dict) -> requests.Response:
        """POST con exponential backoff para rate limits y timeouts."""
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response
