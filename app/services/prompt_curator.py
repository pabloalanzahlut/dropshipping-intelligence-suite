# app/services/prompt_curator.py
import os
import logging
import requests


def sanitize_api_key(key: str) -> str:
    """Sanitiza una API key para logging, mostrando solo los últimos 4 caracteres."""
    if not key:
        return "<vacia>"
    if len(key) <= 8:
        return f"{'*' * (len(key) - 4)}{key[-4:]}"
    return f"{key[:3]}...{key[-4:]}"


class PromptCurator:
    def __init__(self, workspace_path: str = "ai_workspace"):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.library_dir = os.path.join(workspace_path, "skills_library")
        self.skills_dir = os.path.join(workspace_path, "skills")
        logger = logging.getLogger(__name__)
        logger.info(f"[PROMPT-CURATOR] Inicializado. API Key: {sanitize_api_key(self.api_key)}")

    def curate_and_activate(self, raw_filename: str, skill_folder_name: str):
        """
        Toma una plantilla genérica de la biblioteca, la localiza para 
        E-commerce internacional y la activa como una skill operativa.
        """
        if not self.api_key:
            raise ValueError("CRITICO: No se detecta OPENROUTER_API_KEY en el entorno.")

        raw_path = os.path.join(self.library_dir, raw_filename)
        if not os.path.exists(raw_path):
            raise FileNotFoundError(f"No se encontro la plantilla base: {raw_filename}")

        with open(raw_path, "r", encoding="utf-8") as f:
            raw_prompt_content = f.read()

        system_instruction = (
            "Eres el Ingeniero de Prompts experto de GEM OS.\n"
            "Tu tarea es tomar un prompt generico de codigo abierto, traducirlo a Espanol Neutro "
            "si esta en ingles, y adaptarlo inyectando tres metadatos contextuales rigidos:\n"
            "1. Sector: Dropshipping global en Shopify.\n"
            "2. Cliente Objetivo: Comprador internacional de alto poder adquisitivo.\n"
            "3. Tono: Persuasivo, directo y libre de adjetivos corporativos exagerados o humo.\n\n"
            "Conserva las variables entre llaves (ej: {{market_item}}) intactas para que el "
            "orquestador inyecte los datos de SQLite despues. Devuelve solo el prompt curado en Markdown."
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com"
        }
        payload = {
            "model": "google/gemini-2.0-flash-exp:free",
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Prompt original a refinar:\n\n{raw_prompt_content}"}
            ],
            "temperature": 0.2
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            curated_prompt = response.json()['choices']['message']['content'].strip()

            output_path = os.path.join(self.skills_dir, skill_folder_name, "procedimiento.md")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(curated_prompt)
                
            print(f"✨ SISTEMA: Prompt curado y activado en skills/{skill_folder_name}/procedimiento.md")
        except Exception as e:
            print(f"Error en la curacion automatica de prompts: {str(e)}")
