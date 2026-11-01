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

    def clean_transcript(self, raw_text: str) -> Optional[str]:
        """Tritura intros, saludos y humos para extraer la data dura de e-commerce."""
        system_prompt = (
            "Eres un extractor de datos de alto rendimiento especializado en Dropshipping y Shopify.\n"
            "Tu única tarea es analizar la transcripción de un video de un experto, eliminar todo el relleno "
            "(saludos, intros, promociones, pantallas de ganancias falsas, solicitudes de suscripción) and "
            "devolver la información técnica estructurada en Markdown.\n\n"
            "Divide los hallazgos estrictamente bajo estos tres subheadings si existen datos en el texto:\n"
            "### 1. Datos de Producto y Tendencias (Criterios, nichos, ángulos)\n"
            "### 2. Estructuras de Conversión y Copy (Ganchos, landing pages, apps)\n"
            "### 3. Logística, Tráfico y Legal (Presupuestos, segmentación, pasarelas, fletes)\n\n"
            "Si el texto no contiene datos de valor para ninguna categoría, devuelve únicamente la palabra: VACÍO."
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

        try:
            response = self._post_with_retry(target_url, headers, payload)
            content = response.json()['choices'][0]['message']['content'].strip()
            return None if content == "VACÍO" else content
        except Exception as e:
            print(f"Error de comunicación en la pasarela de IA ({target_url}): {str(e)}")
            return None

    @with_retry(max_retries=3, base_delay=2.0, max_delay=30.0)
    def _post_with_retry(self, url: str, headers: dict, payload: dict) -> requests.Response:
        """POST con exponential backoff para rate limits y timeouts."""
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response
