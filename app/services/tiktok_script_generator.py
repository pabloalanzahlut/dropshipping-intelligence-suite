"""
TikTokScriptGenerator - Generador de Guiones TikTok Virales
Crea guiones basados en patrones hook virales + contexto de KB.

Hook Patterns Virales:
- Story-telling: Narrativa que empieza in medias res
- Curiosity-gap: Pregunta que genera curiosidad
- Shock: Dato sorprendente
- Humor: Chiste o situación cómica
"""

import os
from typing import Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv

from app.database.connection import DatabaseConnection


class TikTokScriptGenerator:
    """Generador de guiones TikTok con contexto de KB."""
    
    # Patrones de hooks virales
    HOOK_PATTERNS = {
        'story-telling': [
            "Descubrí algo que cambió mi vida...",
            "Hace 3 meses no sabía esto...",
            "La mayoría comete este error...",
            "Mi mayor fallo fue..."
        ],
        'curiosity-gap': [
            "No vas a creer lo que pasó cuando...",
            "La razón por la que funciona es...",
            "Aquí está el secreto que nadie te dice...",
            "Todos están haciendo esto mal..."
        ],
        'shock': [
            "Gasto SOLO $100 y gano $1000...",
            "Esto se prohíbe en 3 meses...",
            "Nadie está hablando de esto...",
            "La mayoría pierde dinero aquí..."
        ],
        'humor': [
            "POV: eres dropshipper y...",
            "Cuando tu estrategia falla...",
            "Yo vs mi competencia...",
            "Parte 2 porque la gente pidió..."
        ]
    }
    
    def __init__(self, db_manager: Optional[DatabaseConnection] = None):
        """
        Args:
            db_manager: Gestor de BD
        """
        self.db_manager = db_manager if db_manager else DatabaseConnection()
        self.generator_log = []

                # Pool de orquestación híbrida tripartito (FASE A)
        self._hybrid_pool = None

    def _get_hybrid_pool(self):
                """Lazy import del pool híbrido tripartito (FASE A)."""
                if self._hybrid_pool is None:
                    try:
                        from app.core.ollama_pool import HybridInferencePool
                        self._hybrid_pool = HybridInferencePool()
                    except Exception as exc:
                        print(f"[TIKTOK] Error cargando pool híbrido: {exc}")
                return self._hybrid_pool

    def obtener_contexto_kb(self, limite: int = 3) -> str:
        """Obtiene contexto de KB limpia."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT transcripcion_limpia FROM transcripciones_youtube
                    WHERE procesada = 1 AND transcripcion_limpia IS NOT NULL
                    ORDER BY creada_at DESC
                    LIMIT ?
                """, (limite,))
                
                rows = cursor.fetchall()
                contextos = [row[0][:400] for row in rows]
                return "\n---\n".join(contextos)
        except Exception as e:
            print(f"[ERROR] Obtener contexto KB: {str(e)}")
            return ""
    
    def generar_hook(self, patron: str = 'story-telling') -> str:
        """
        Genera hook según patrón seleccionado.
        
        Args:
            patron: Tipo de hook ('story-telling', 'curiosity-gap', 'shock', 'humor')
        
        Returns:
            Hook generado
        """
        if patron not in self.HOOK_PATTERNS:
            patron = 'story-telling'
        
        hooks = self.HOOK_PATTERNS[patron]
        import random
        return random.choice(hooks)
    
    def generar_cuerpo(self, producto_nombre: str, categoria: str, contexto_kb: str = "") -> str:
        """
        Genera cuerpo del guión (problema + solución).
        
        Args:
            producto_nombre: Nombre del producto
            categoria: Categoría
            contexto_kb: Contexto de KB
        
        Returns:
            Cuerpo del guión
        """
        
        cuerpo = f"""
El {producto_nombre} es la solución para {{categoria}}.

Problema: La mayoría no sabe por dónde empezar.

Solución: Valida 3 criterios:
1. Precio justo (Regla 3x)
2. Margen >= 70%
3. Peso < 1.2kg

Resultado: Rentable desde el primer día.
        """.strip()
        
        return cuerpo
    
    def generar_cta(self) -> str:
        """Genera Call-to-Action para TikTok."""
        ctas = [
            "Mira el enlace en bio para comenzar",
            "Dime en comentarios tu producto favorito",
            "Parte 2 si quieres más tips",
            "Sígueme para más contenido dropshipping",
            "¿Cuál es tu mayor bloqueó? Comenta",
            "Comparte esto con tu mejor amigo",
            "Dale like si te sirvió"
        ]
        import random
        return random.choice(ctas)
    
    def generar_guion_completo(self, 
                              nombre_producto: str,
                              categoria: str,
                              patron_hook: str = 'story-telling',
                              duracion_segundos: int = 60) -> Dict:
        """
        Genera guión completo para TikTok.
        
        Args:
            nombre_producto: Nombre del producto
            categoria: Categoría
            patron_hook: Patrón de hook a usar
            duracion_segundos: Duración target en segundos
        
        Returns:
            Dict con guión completo
        """
        
        contexto = self.obtener_contexto_kb()
        
        hook = self.generar_hook(patron_hook)
        cuerpo = self.generar_cuerpo(nombre_producto, categoria, contexto)
        cta = self.generar_cta()
        
        guion_completo = f"""
{hook}

{cuerpo}

{cta}
        """.strip()
        
        # Estimar duración (1 segundo por ~10 palabras en TikTok)
        palabras = len(guion_completo.split())
        duracion_estimada = max(15, min(180, palabras // 10))
        
        return {
            'titulo': f"{nombre_producto} - Hook {patron_hook}",
            'hook': hook,
            'cuerpo': cuerpo,
            'cta': cta,
            'guion_completo': guion_completo,
            'patron_hook': patron_hook,
            'duracion_segundos': duracion_estimada,
            'contexto_kb_reference': 'KB limpia',
            'timestamp': datetime.now().isoformat()
        }
    
    def generar_variantes_lote(self, nombre_producto: str, categoria: str, cantidad: int = 5) -> List[Dict]:
        """
        Genera múltiples variantes de guión (batch mode).
        
        Args:
            nombre_producto: Nombre del producto
            categoria: Categoría
            cantidad: Cantidad de variantes
        
        Returns:
            Lista de guiones generados
        """
        
        patrones = ['story-telling', 'curiosity-gap', 'shock', 'humor']
        guiones = []
        
        for i in range(cantidad):
            patron = patrones[i % len(patrones)]
            guion = self.generar_guion_completo(nombre_producto, categoria, patron)
            guiones.append(guion)
        
        return guiones
    
    def _cargar_contexto_archivos(self) -> str:
        """
        Carga los archivos de contexto de la KB para inyectarlos en el prompt de OpenRouter.
        
        Returns:
            Texto consolidado de los archivos de contexto
        """
        context_dir = os.path.join("ai_workspace", "context")
        archivos = ["matriz_tendencias.md", "formulas_conversion.md", "operaciones_trafico.md"]
        partes = []
        
        for archivo in archivos:
            ruta = os.path.join(context_dir, archivo)
            if os.path.exists(ruta):
                try:
                    with open(ruta, "r", encoding="utf-8") as f:
                        contenido = f.read()
                    partes.append(f"=== {archivo} ===\n{contenido[:2000]}")
                except Exception as e:
                    print(f"[WARN] No se pudo leer {archivo}: {str(e)}")
        
        return "\n\n".join(partes) if partes else ""

    def generar_con_openrouter(self,
                               nombre_producto: str,
                               categoria: str,
                               patron_hook: str = 'story-telling',
                               duracion_segundos: int = 60,
                               contexto_kb: str = "") -> Dict:
        """
            Genera un guión TikTok usando el enrutador híbrido tripartito (FASE A):
            1. FreeLLMAPI Proxy (Costo $0.00)  → Prioridad Élite
            2. OpenRouter API (Nube)           → Respaldo
            3. Ollama Local (Sin Internet)     → Fallback Crítico
            4. Template local                  → Fallback final

            Args:
                nombre_producto: Nombre del producto
                categoria: Categoría
                patron_hook: Patrón de hook a usar
                duracion_segundos: Duración target en segundos
                contexto_kb: Contexto de transcripciones de YouTube

            Returns:
                Dict con guión generado
            """
        pool = self._get_hybrid_pool()
        texto_generado = None

            # 1. Intentar con pool híbrido tripartito
        if pool:
                contexto_archivos = self._cargar_contexto_archivos()

                system_prompt = (
                    "Eres un Director Creativo multimedia especializado en anuncios virales de video vertical "
                    "(TikTok Ads, Meta Ads e Instagram Reels). Tu misión es diseñar un guion publicitario técnico "
                    "de 15 a 30 segundos optimizado para detener el scroll del usuario e inducir el clic de compra hacia Shopify.\n\n"
                    "REGLAS ESTRICTAS:\n"
                    "1. Queda estrictamente prohibido usar adjetivos superlativos vacíos como: "
                    "increíble, alucinante, genial, magnífico, fantástico, asombroso, espectacular, "
                    "extraordinario, sensacional, maravilloso, formidable, prodigioso, colosal, monumental.\n"
                    "2. No realices promesas falsas de envío express de 24-48 horas. Las políticas de TikTok y Meta "
                    "banean permanentemente las cuentas que prometen plazos logísticos inviables.\n"
                    "3. El guion debe fundamentar el beneficio del producto mediante una demostración visual explícita "
                    "del problema en los primeros 3 segundos (El Gancho).\n"
                    "4. El tono debe ser dinámico, visual, resolutivo y realista.\n\n"
                    "PLANTILLA TÉCNICA DE ENTREGABLE (Tabla Markdown):\n\n"
                    "| Tiempo (seg) | Componente | Estructura de Video (Lo que se VE) | Locución / Texto (Lo que se ESCUCHA o LEE) |\n"
                    "| :--- | :--- | :--- | :--- |\n"
                    "| **00:00 - 00:03** | **EL GANCHO (Hook)** | [Acción visual de impacto mostrando el dolor del usuario] | [Frase contundente que rompa el patrón mental] |\n"
                    "| **00:03 - 00:10** | **EL PROBLEMA (Agitación)** | [Muestra el producto resolviendo el inconveniente] | [Explicación corta del dolor y cómo afecta] |\n"
                    "| **00:10 - 00:20** | **EL BENEFICIO (Demostración)** | [Primer plano de la calidad y funcionamiento real] | [Beneficio emocional y valor añadido verificado] |\n"
                    "| **00:20 - 00:30** | **ACCIÓN (CTA Claro)** | [Pantalla limpia con empaque o interfaz Shopify] | \"Haz clic en 'Comprar Ahora' para asegurar tu envío.\" |\n"
                )

                user_prompt = (
                    f"Genera un guion TikTok para el siguiente producto:\n\n"
                    f"**Nombre:** {nombre_producto}\n"
                    f"**Categoría:** {categoria}\n"
                    f"**Patrón de Hook:** {patron_hook}\n"
                    f"**Duración objetivo:** {duracion_segundos} segundos\n\n"
                )
                if contexto_kb:
                    user_prompt += f"**Contexto de transcripciones de mentores:**\n{contexto_kb[:3000]}\n\n"
                if contexto_archivos:
                    user_prompt += f"**Contexto de KB (tendencias, fórmulas, operaciones):**\n{contexto_archivos[:3000]}\n\n"
                user_prompt += "Devuelve solo el guion en formato tabla Markdown, sin explicaciones adicionales."

                texto_generado = pool.execute_hybrid_query(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.4,
                    max_tokens=2048
                )

                if texto_generado:
                    print(f"[TIKTOK] Guión generado vía pool híbrido (capa activa: {pool.get_active_layer()})")

            # 2. Si el pool no funcionó, usar OpenRouter directo (legacy)
        if not texto_generado:
            openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
            if not openrouter_api_key:
                print("[INFO] Sin OPENROUTER_API_KEY y pool híbrido no disponible. Usando template local.")
                return self.generar_guion_completo(nombre_producto, categoria, patron_hook, duracion_segundos)

            import requests

            contexto_archivos = self._cargar_contexto_archivos()

            system_prompt = (
                "Eres un Director Creativo multimedia especializado en anuncios virales de video vertical "
                "(TikTok Ads, Meta Ads e Instagram Reels). Tu misión es diseñar un guion publicitario técnico "
                "de 15 a 30 segundos optimizado para detener el scroll del usuario e inducir el clic de compra hacia Shopify.\n\n"
                "REGLAS ESTRICTAS:\n"
                "1. Queda estrictamente prohibido usar adjetivos superlativos vacíos como: "
                "increíble, alucinante, genial, magnífico, fantástico, asombroso, espectacular, "
                "extraordinario, sensacional, maravilloso, formidable, prodigioso, colosal, monumental.\n"
                "2. No realices promesas falsas de envío express de 24-48 horas. Las políticas de TikTok y Meta "
                "banean permanentemente las cuentas que prometen plazos logísticos inviables.\n"
                "3. El guion debe fundamentar el beneficio del producto mediante una demostración visual explícita "
                "del problema en los primeros 3 segundos (El Gancho).\n"
                "4. El tono debe ser dinámico, visual, resolutivo y realista.\n\n"
                "PLANTILLA TÉCNICA DE ENTREGABLE (Tabla Markdown):\n\n"
                "| Tiempo (seg) | Componente | Estructura de Video (Lo que se VE) | Locución / Texto (Lo que se ESCUCHA o LEE) |\n"
                "| :--- | :--- | :--- | :--- |\n"
                "| **00:00 - 00:03** | **EL GANCHO (Hook)** | [Acción visual de impacto mostrando el dolor del usuario] | [Frase contundente que rompa el patrón mental] |\n"
                "| **00:03 - 00:10** | **EL PROBLEMA (Agitación)** | [Muestra el producto resolviendo el inconveniente] | [Explicación corta del dolor y cómo afecta] |\n"
                "| **00:10 - 00:20** | **EL BENEFICIO (Demostración)** | [Primer plano de la calidad y funcionamiento real] | [Beneficio emocional y valor añadido verificado] |\n"
                "| **00:20 - 00:30** | **ACCIÓN (CTA Claro)** | [Pantalla limpia con empaque o interfaz Shopify] | \"Haz clic en 'Comprar Ahora' para asegurar tu envío.\" |\n"
            )

            user_prompt = (
                f"Genera un guion TikTok para el siguiente producto:\n\n"
                f"**Nombre:** {nombre_producto}\n"
                f"**Categoría:** {categoria}\n"
                f"**Patrón de Hook:** {patron_hook}\n"
                f"**Duración objetivo:** {duracion_segundos} segundos\n\n"
            )

            if contexto_kb:
                user_prompt += f"**Contexto de transcripciones de mentores:**\n{contexto_kb[:3000]}\n\n"
            if contexto_archivos:
                user_prompt += f"**Contexto de KB (tendencias, fórmulas, operaciones):**\n{contexto_archivos[:3000]}\n\n"

            user_prompt += "Devuelve solo el guion en formato tabla Markdown, sin explicaciones adicionales."

            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com"
            }
            payload = {
                "model": "google/gemini-2.0-flash-exp:free",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.4,
                "max_tokens": 2048
            }

            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                guion_generado = response.json()['choices'][0]['message']['content'].strip()

                # Extraer hook de la primera fila de la tabla
                hook_generado = self.generar_hook(patron_hook)
                lineas = guion_generado.split('\n')
                for linea in lineas:
                    if 'EL GANCHO' in linea or 'Hook' in linea:
                        partes = linea.split('|')
                        if len(partes) >= 4:
                            hook_generado = partes[3].strip()
                        break

                return {
                    'titulo': f"{nombre_producto} - Hook {patron_hook}",
                    'hook': hook_generado,
                    'cuerpo': guion_generado,
                    'cta': "Haz clic en 'Comprar Ahora' para asegurar tu envío.",
                    'guion_completo': guion_generado,
                    'patron_hook': patron_hook,
                    'duracion_segundos': duracion_segundos,
                    'contexto_kb_reference': 'openrouter_kb',
                    'timestamp': datetime.now().isoformat()
                }

            except Exception as e:
                print(f"[ERROR] Fallo al generar guión con OpenRouter: {str(e)}")
                print("[INFO] Fallback al template local.")
                return self.generar_guion_completo(nombre_producto, categoria, patron_hook, duracion_segundos)

    def guardar_guion(self, producto_id: int, guion_data: Dict) -> int:
        """
        Guarda un guión en BD.
        
        Args:
            producto_id: ID del producto
            guion_data: Dict con data del guión
        
        Returns:
            ID del guión guardado, o -1 si falla
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Crear tabla si no existe
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS guiones_tiktok (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        producto_id INTEGER,
                        titulo TEXT,
                        hook TEXT,
                        cuerpo TEXT,
                        cta TEXT,
                        guion_completo TEXT,
                        patron_hook TEXT,
                        duracion_segundos INTEGER,
                        tendencia_utilizada TEXT,
                        context_kb_reference TEXT,
                        rating_usuario INTEGER DEFAULT 0,
                        creada_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (producto_id) REFERENCES productos_validados(id) ON DELETE CASCADE
                    )
                """)
                
                cursor.execute("""
                    INSERT INTO guiones_tiktok
                    (producto_id, titulo, hook, cuerpo, cta, guion_completo, patron_hook, 
                     duracion_segundos, context_kb_reference)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    producto_id,
                    guion_data.get('titulo'),
                    guion_data.get('hook'),
                    guion_data.get('cuerpo'),
                    guion_data.get('cta'),
                    guion_data.get('guion_completo'),
                    guion_data.get('patron_hook'),
                    guion_data.get('duracion_segundos'),
                    guion_data.get('contexto_kb_reference')
                ))
                
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"[ERROR] Guardar guión: {str(e)}")
            return -1
    
    def obtener_reporte_guiones(self) -> Dict:
        """Obtiene reporte consolidado de guiones generados."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as total,
                           AVG(duracion_segundos) as duracion_promedio,
                           patron_hook,
                           COUNT(*) as cantidad
                    FROM guiones_tiktok
                    GROUP BY patron_hook
                    ORDER BY cantidad DESC
                """)
                
                rows = cursor.fetchall()
                patrones_stats = {row['patron_hook']: row['cantidad'] for row in rows}
                
                total = sum(patrones_stats.values())
                duracion_avg = cursor.execute(
                    "SELECT AVG(duracion_segundos) FROM guiones_tiktok"
                ).fetchone()[0] or 0
                
                return {
                    'total_guiones': total,
                    'duracion_promedio_segundos': round(duracion_avg, 1),
                    'patrones_utilizados': patrones_stats
                }
        except Exception as e:
            print(f"[ERROR] Obtener reporte: {str(e)}")
        
        return {'total_guiones': 0, 'duracion_promedio_segundos': 0, 'patrones_utilizados': {}}
