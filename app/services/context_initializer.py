import os
import requests

class ContextInitializer:
    def __init__(self, workspace_path: str = "ai_workspace"):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.context_dir = os.path.join(workspace_path, "context")
        os.makedirs(self.context_dir, exist_ok=True)

    def generate_initial_context(self):
        """Invoca a la IA para crear y persistir los archivos de contexto base."""
        if not self.api_key:
            raise ValueError("CRÍTICO: No se detecta la variable OPENROUTER_API_KEY en el entorno.")

        print("🧠 Generando archivos de contexto iniciales mediante IA...")

        system_instruction = (
            "Eres el Arquitecto de Datos del GEM OS. Generas archivos de contexto iniciales "
            "para e-commerce. Devuelve el contenido exacto de los archivos usando bloques "
            "separadores claros: === MATRIZ_TENDENCIAS === y === FORMULAS_CONVERSION ==="
        )

        user_prompt = """
        Crea los contenidos para:
        1. matriz_tendencias.md: Incluye al menos 2 productos ganadores ficticios con el factor Wow, 
           nicho, restricciones logísticas y la regla matemática de margen de ganancia 3x.
        2. formulas_conversion.md: Estructura los cascarones base de copywriting para el framework AIDA 
           bloqueando alucinaciones físicas del producto.
        
        Usa formato Markdown estructurado con etiquetas XML internas inyectadas con bloques CDATA.
        """

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "google/gemini-flash", # Modelo analítico rápido idóneo para estructuración de datos
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            raw_output = response.json()['choices']['message']['content']

            # Segmentación de la respuesta física para guardado en disco
            parts = raw_output.split("===")
            matriz_content = ""
            formulas_content = ""

            for i, part in enumerate(parts):
                if "MATRIZ_TENDENCIAS" in part:
                    matriz_content = parts[i+1].strip().strip("```markdown").strip("```")
                elif "FORMULAS_CONVERSION" in part:
                    formulas_content = parts[i+1].strip().strip("```markdown").strip("```")

            # Escritura física en la carpeta /context/
            with open(os.path.join(self.context_dir, "matriz_tendencias.md"), "w", encoding="utf-8") as f:
                f.write(matriz_content if matriz_content else "# Matriz de Tendencias Base\n")
            
            with open(os.path.join(self.context_dir, "formulas_conversion.md"), "w", encoding="utf-8") as f:
                f.write(formulas_content if formulas_content else "# Fórmulas de Conversión Base\n")

            print("💾 Archivos creados con éxito en /ai_workspace/context/")
        except Exception as e:
            print(f"❌ Error en la inicialización automática de contexto: {str(e)}")

if __name__ == "__main__":
    initializer = ContextInitializer()
    initializer.generate_initial_context()
