# claude_corporate_optimizer.py
import os
import json
import logging
import anthropic

# Configuración de logs corporativos
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ClaudeCorporateOptimizer")

class ClaudeEliteClient:
    """
    Cliente de producción élite para la gestión y optimización de costes en Anthropic Claude.
    Implementa enrutamiento de modelos, Prompt Caching dinámico y procesamiento por lotes (Batch API).
    """
    def __init__(self, api_key: str = None):
        # Inicializa el SDK de Anthropic usando variables de entorno o clave directa
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Error corporativo: Falta la ANTHROPIC_API_KEY en el entorno o parámetros.")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        
        # Mapa de modelos actualizados para enrutamiento corporativo
        self.models = {
            "haiku": "claude-haiku-5-5",    # Tareas masivas, clasificación, enrutamiento rápido
            "sonnet": "claude-sonnet-5-5",  # Motor principal, balance ideal inteligencia/costo
            "opus": "claude-opus-5-5",      # Tareas élite, desarrollo complejo y alta lógica
            "fable": "claude-fable-5-1"     # Razonamiento avanzado de horizonte largo
        }

    def execute_live_request(self, tier: str, system_prompt: list, messages: list, max_tokens: int = 1024):
        """
        Ejecuta una solicitud en tiempo real aplicando Prompt Caching esplicito.
        El breakpoint de la caché se gestiona mediante la inclusión de cache_control en el bloque correspondiente.
        """
        model_name = self.models.get(tier.lower(), self.models["sonnet"])
        try:
            response = self.client.messages.create(
                model=model_name,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages
            )
            self._audit_costs(response)
            return response
        except Exception as e:
            logger.error(f"Fallo en la ejecución live: {e}")
            raise e

    def prewarm_corporate_cache(self, tier: str, system_prompt: list):
        """
        Ejecuta una petición de precalentamiento (Pre-warming) con max_tokens=0.
        Escribe en la memoria caché sin incurrir en costes de generación de tokens de salida.
        """
        model_name = self.models.get(tier.lower(), self.models["sonnet"])
        try:
            # Para el precalentamiento se envía un mensaje segnaposto básico
            warmup_messages = [{"role": "user", "content": "warmup"}]
            response = self.client.messages.create(
                model=model_name,
                max_tokens=0,
                system=system_prompt,
                messages=warmup_messages
            )
            logger.info("Precalentamiento completado con éxito.")
            self._audit_costs(response)
            return response
        except Exception as e:
            logger.error(f"Fallo en el precalentamiento de la caché: {e}")
            raise e

    def create_low_cost_batch(self, tier: str, requests: list):
        """
        Crea un trabajo masivo asíncrono usando la Batch API para ahorrar un 50% en costes de tokens.
        Ideal para procesamiento nocturno o tareas que no requieran respuestas inmediatas.
        """
        model_name = self.models.get(tier.lower(), self.models["sonnet"])
        try:
            # Construcción de los parámetros individuales para el lote
            batch_requests = []
            for idx, req in enumerate(requests):
                batch_requests.append({
                    "custom_id": f"req_{idx}",
                    "params": {
                        "model": model_name,
                        "max_tokens": req.get("max_tokens", 1024),
                        "messages": req.get("messages")
                    }
                })
            
            # Creación del lote a través del cliente de Anthropic
            message_batch = self.client.beta.messages.batches.create(requests=batch_requests)
            logger.info(f"Lote corporativo creado con éxito. ID: {message_batch.id} - Estado: {message_batch.processing_status}")
            return message_batch
        except Exception as e:
            logger.error(f"Fallo al crear el lote masivo en la Batch API: {e}")
            raise e

    def _audit_costs(self, response):
        """
        Analiza las métricas de uso de la API e informa con exactitud el volumen de ahorro 
        por aciertos en la caché de prompts (Cache Hits).
        """
        usage = response.usage
        read_tokens = getattr(usage, 'cache_read_input_tokens', 0)
        created_tokens = getattr(usage, 'cache_creation_input_tokens', 0)
        base_input_tokens = getattr(usage, 'input_tokens', 0)
        output_tokens = getattr(usage, 'output_tokens', 0)
        
        total_input = read_tokens + created_tokens + base_input_tokens
        
        logger.info("----------- AUDITORÍA DE COSTES ÉLITE -----------")
        logger.info(f"Modelo Utilizado: {response.model}")
        logger.info(f"Tokens de Entrada Totales: {total_input}")
        logger.info(f"  -> Recuperados de Caché (Ahorro del 90%): {read_tokens}")
        logger.info(f"  -> Escritos en Caché (Costo inicial): {created_tokens}")
        logger.info(f"  -> Procesados normales (Sin Caché): {base_input_tokens}")
        logger.info(f"Tokens de Salida Generados: {output_tokens}")
        
        if total_input > 0:
            efficiency = (read_tokens / total_input) * 100
            logger.info(f"Eficiencia Financiera de la Caché: {efficiency:.2f}%")
        logger.info("-------------------------------------------------")

# Ejemplo práctico de implementación
if __name__ == "__main__":
    # Ejemplo de inicialización dummy. Asegúrate de tener configurada tu clave de entorno.
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-corporate-dummy-key-replace-me"
    
    try:
        optimizer = ClaudeEliteClient()
        
        # Estructura corporativa del System Prompt con breakpoint explícito
        corporate_system = [
            {
                "type": "text",
                "text": "Eres la inteligencia central de la corporación. Normativas de cumplimiento: ISO 27001, SOC2."
            },
            {
                "type": "text",
                "text": "[Contexto Estático del Proyecto: Manuales técnicos y documentación legal base de la empresa...]",
                "cache_control": {"type": "ephemeral"} # Punto de control manual para almacenamiento de larga duración
            }
        ]
        
        print("[!] Script listo para producción. Modifica la clave de API y el contexto estático para iniciar.")
        
    except ValueError as ve:
        print(ve)
