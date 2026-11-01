"""
CopywrightingEngine - Motor de Redacción de Copys Shopify (AIDA Framework)
Genera copys sin adjetivos superlativos, con contexto de KB limpia de YouTube.

Framework AIDA:
- Attention: Título que capta atención
- Interest: Describe el problema/beneficio
- Decision: Por qué es la solución
- Action: Call-to-action clara
"""

import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv

from app.database.connection import DatabaseConnection


class CopywrightingEngine:
    """Motor de copywriting con AIDA framework sin superlativos."""
    
    # Adjetivos superlativos prohibidos
    ADJETIVOS_PROHIBIDOS = {
    'increíble', 'alucinante', 'genial', 'magnífico', 'fantástico',
    'asombroso', 'espectacular', 'extraordinario', 'sensacional',
    'maravilloso', 'formidable', 'prodigioso', 'colosal', 'monumental',
    'excepcional', 'incomparable', 'insuperable', 'inigualable',
    'inmejorable', 'estupendo', 'magnífico', 'esplendido'
    }
    
    def __init__(self, db_manager: Optional[DatabaseConnection] = None, openrouter_api_key: str = None):
        """
        Args:
        db_manager: Gestor de BD
        openrouter_api_key: API key de OpenRouter (opcional)
        """
        self.db_manager = db_manager if db_manager else DatabaseConnection()
        self.openrouter_api_key = openrouter_api_key or os.getenv('OPENROUTER_API_KEY')
        self.copywriting_log = []
        # Pool de orquestación híbrida tripartito (FASE A)
        self._hybrid_pool = None

    def _get_hybrid_pool(self):
        """Lazy import del pool híbrido tripartito (FASE A)."""
        if self._hybrid_pool is None:
            try:
                from app.core.ollama_pool import HybridInferencePool
                self._hybrid_pool = HybridInferencePool()
            except Exception as exc:
                print(f"[COPYWRITING] Error cargando pool híbrido: {exc}")
        return self._hybrid_pool

    def obtener_contexto_kb(self, limite: int = 5) -> str:
        """

        Obtiene últimas transcripciones limpias de YouTube para usar como contexto.


        Args:
        limite: Número de transcripciones a recuperar

        Returns:
        Texto consolidado de transcripciones (contexto)
        """
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
                        contextos = [row[0][:500] for row in rows]  # Primeros 500 chars de cada
                        return "\n\n---\n\n".join(contextos)
        except Exception as e:
            print(f"[ERROR] Obtener contexto KB: {str(e)}")
            return ""

    def validar_sin_superlativos(self, texto: str) -> Tuple[bool, List[str]]:
        """
        Valida que el texto no contenga adjetivos superlativos.

        Args:
        texto: Texto a validar

        Returns:
        (es_valido, lista_adjetivos_encontrados)
        """
        palabras = texto.lower().split()
        adjetivos_encontrados = []

        for palabra in palabras:
                    # Limpiar puntuación
                    palabra_limpia = palabra.strip('.,!?;:')
                    if palabra_limpia in self.ADJETIVOS_PROHIBIDOS:
                        adjetivos_encontrados.append(palabra_limpia)

        es_valido = len(adjetivos_encontrados) == 0
        return es_valido, adjetivos_encontrados

    def calcular_scores_aida(self, titulo: str, descripcion: str) -> Dict:
        """
        Calcula scores AIDA para un copy (basado en análisis textual).

        Args:
        titulo: Título del copy
        descripcion: Descripción del copy

        Returns:
        Dict con scores: attention, interest, decision, action (0-100)
        """

        # Score Attention: Longitud y primeras palabras (activas)
        palabras_titulo = titulo.split()
        attention_score = min(100, len(palabras_titulo) * 15)  # Penalizar títulos muy cortos

        # Score Interest: Palabras clave de beneficio
        palabras_beneficio = {'soluciona', 'resuelve', 'mejora', 'aumenta', 'reduce', 
                         'ahorra', 'acelera', 'facilita', 'optimiza', 'permite'}
        interest_score = sum(1 for w in descripcion.lower().split() if w in palabras_beneficio) * 20
        interest_score = min(100, interest_score)

        # Score Decision: Menciona por qué (validación, prueba)
        palabras_decision = {'porque', 'validado', 'comprobado', 'testado', 'garantizado',
                        'certificado', 'probado', 'demostrado', 'verificado'}
        decision_score = sum(1 for w in descripcion.lower().split() if w in palabras_decision) * 25
        decision_score = min(100, decision_score)

        # Score Action: CTA clara (compra, agrega, obtén)
        palabras_cta = {'compra', 'ordena', 'agrega', 'obtén', 'consigue', 'descarga',
                   'prueba', 'accede', 'súmate', 'únete', 'aprox', 'boleto'}
        action_score = sum(1 for w in descripcion.lower().split() if w in palabras_cta) * 30
        action_score = min(100, action_score)

        return {
        'attention': min(100, attention_score),
        'interest': interest_score,
        'decision': decision_score,
        'action': action_score,
        'promedio': round((attention_score + interest_score + decision_score + action_score) / 4, 1)
        }

    def generar_copy_template(self, 
                        nombre_producto: str,
                        categoria: str,
                        costo_origen: float,
                        pvp: float,
                        peso_kg: float,
                        contexto_kb: str = "") -> Dict:
        """
        Genera un copy completo (mock) sin APIs externas.
        En producción, llamar a OpenRouter con prompt + contexto.

        Args:
        nombre_producto: Nombre del producto
        categoria: Categoría
        costo_origen: Costo de origen
        pvp: Precio de venta público
        peso_kg: Peso del producto
        contexto_kb: Contexto de KB limpia

        Returns:
        Dict con copy generado
        """

        margen_pct = round(((pvp - costo_origen) / pvp) * 100, 1)

        # Template AIDA sin superlativos
        titulo = f"{nombre_producto} - Solución Premium [{categoria}]"

        descripcion = f"""
    {nombre_producto}: La solución que estabas buscando para tu negocio de {categoria}.

    ATTENTION: ¿Cansado de buscar productos que no funcionan?

    INTEREST: Este producto ha sido validado por nuestra comunidad de emprendedores.
    Precio optimizado: ${pvp} (margen: {margen_pct}%). Peso: {peso_kg} kg (logística ágil).
    Características probadas en mercado real.

    DECISION: Por qué funciona:
    - Precio justo según Regla 3x
    - Margen de operación sostenible
    - Logística manejable
    - Demanda verificada en comunidad

    ACTION: Agrega a tu tienda hoy. Stock limitado. Comienza a vender en 24 horas.
        """.strip()

        scores = self.calcular_scores_aida(titulo, descripcion)
        es_valido, adjetivos = self.validar_sin_superlativos(descripcion)

        return {
                    'titulo': titulo,
                    'descripcion': descripcion,
                    'scores_aida': scores,
                    'sin_superlativos': es_valido,
        'adjetivos_encontrados': adjetivos,
        'contexto_fuente': "template_aida",
        'timestamp': datetime.now().isoformat()
        }

    def _cargar_contexto_archivos(self) -> str:
        """
        Carga los archivos de contexto de la KB (matriz_tendencias, formulas_conversion, operaciones_trafico)
        para inyectarlos en el prompt de OpenRouter.

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
                               costo_origen: float,
                               pvp: float,
                               peso_kg: float,
                               contexto_kb: str = "") -> Dict:
        """
        Genera un copy AIDA usando el enrutador híbrido tripartito (FASE A):
        1. FreeLLMAPI Proxy (Costo $0.00)  → Prioridad Élite
        2. OpenRouter API (Nube)           → Respaldo
        3. Ollama Local (Sin Internet)     → Fallback Crítico
        4. Template local                  → Fallback final

        Args:
            nombre_producto: Nombre del producto
            categoria: Categoría
            costo_origen: Costo de origen
            pvp: Precio de venta público
            peso_kg: Peso del producto
            contexto_kb: Contexto de transcripciones de YouTube

        Returns:
            Dict con copy generado
        """
        texto_generado = None

        # 1. Intentar con pool híbrido tripartito
        pool = self._get_hybrid_pool()
        if pool:
            import requests
            margen_pct = round(((pvp - costo_origen) / pvp) * 100, 1)
            contexto_archivos = self._cargar_contexto_archivos()

            system_prompt = (
                "Eres un Redactor Publicitario Experto (Copywriter) especializado en Dropshipping Global en Shopify. "
                "Tu objetivo es generar un copy de ventas siguiendo el framework AIDA (Attention, Interest, Decision, Action).\n\n"
                "REGLAS ESTRICTAS:\n"
                "1. Queda estrictamente prohibido usar adjetivos superlativos vacíos como: "
                "increíble, alucinante, genial, magnífico, fantástico, asombroso, espectacular, "
                "extraordinario, sensacional, maravilloso, formidable, prodigioso, colosal, monumental, "
                "excepcional, incomparable, insuperable, inigualable, inmejorable, estupendo, esplendido.\n"
                "2. No alteres dimensiones, materiales, pesos o capacidades técnicas reales del producto.\n"
                "3. El PVP debe garantizar un margen bruto superior al 70% (Regla 3x).\n"
                "4. El tono debe ser persuasivo, directo y libre de humo o exageraciones comerciales.\n\n"
            )

            user_prompt = (
                f"Genera un copy AIDA para el siguiente producto:\n\n"
                f"**Nombre:** {nombre_producto}\n"
                f"**Categoría:** {categoria}\n"
                f"**Costo de Origen:** ${costo_origen:.2f} USD\n"
                f"**PVP Calculado (Regla 3x):** ${pvp:.2f} USD\n"
                f"**Margen Bruto:** {margen_pct}%\n"
                f"**Peso:** {peso_kg} kg\n\n"
            )
            if contexto_kb:
                user_prompt += f"**Contexto de transcripciones de mentores:**\n{contexto_kb[:3000]}\n\n"
            if contexto_archivos:
                user_prompt += f"**Contexto de KB (matriz de tendencias, fórmulas, operaciones):**\n{contexto_archivos[:3000]}\n\n"
            user_prompt += "Devuelve solo el copy en Markdown, sin explicaciones adicionales."

            texto_generado = pool.execute_hybrid_query(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=2048
            )
            if texto_generado:
                print(f"[COPYWRITING] Copy generado vía pool híbrido (capa activa: {pool.get_active_layer()})")

        # 2. Si el pool híbrido no funcionó, intentar OpenRouter directo (legacy)
        if not texto_generado and self.openrouter_api_key:
            print("[INFO] Usando OpenRouter directo (legacy).")
            import requests
            margen_pct = round(((pvp - costo_origen) / pvp) * 100, 1)
            contexto_archivos = self._cargar_contexto_archivos()

            system_prompt = (
                "Eres un Redactor Publicitario Experto (Copywriter) especializado en Dropshipping Global en Shopify. "
                "Tu objetivo es generar un copy de ventas siguiendo el framework AIDA (Attention, Interest, Decision, Action).\n\n"
                "REGLAS ESTRICTAS:\n"
                "1. Queda estrictamente prohibido usar adjetivos superlativos vacíos como: "
                "increíble, alucinante, genial, magnífico, fantástico, asombroso, espectacular, "
                "extraordinario, sensacional, maravilloso, formidable, prodigioso, colosal, monumental, "
                "excepcional, incomparable, insuperable, inigualable, inmejorable, estupendo, esplendido.\n"
                "2. No alteres dimensiones, materiales, pesos o capacidades técnicas reales del producto.\n"
                "3. El PVP debe garantizar un margen bruto superior al 70% (Regla 3x).\n"
                "4. El tono debe ser persuasivo, directo y libre de humo o exageraciones comerciales.\n\n"
                "ESTRUCTURA OBLIGATORIA DEL ENTREGABLE (Markdown):\n\n"
                "# [Título Magnético - Máximo 6 palabras]\n\n"
                "## [Subtítulo de Gancho - Ataca el dolor principal en 2 líneas]\n\n"
                "### 💎 Beneficios Clave\n"
                "- **[Beneficio Emocional]:** [Explicación de 1 línea vinculando característica con mejora].\n"
                "- **[Beneficio Emocional]:** [Explicación de 1 línea].\n"
                "- **[Beneficio Emocional]:** [Explicación de 1 línea].\n\n"
                "### 🛠️ Especificaciones Técnicas (Datos Duros Verificados)\n"
                "[Listar fielmente los datos del producto sin modificarlos].\n\n"
                "### 📦 Garantía y Confianza Internacional\n"
                "- **Envíos Asegurados:** Monitoreo internacional con código de rastreo.\n"
                "- **Garantía sin Riesgos:** Reembolso si el producto no cumple lo especificado.\n\n"
                "### 🏁 Call to Action\n"
                "[CTA directo e imperativo].\n"
            )

            user_prompt = (
                f"Genera un copy AIDA para el siguiente producto:\n\n"
                f"**Nombre:** {nombre_producto}\n"
                f"**Categoría:** {categoria}\n"
                f"**Costo de Origen:** ${costo_origen:.2f} USD\n"
                f"**PVP Calculado (Regla 3x):** ${pvp:.2f} USD\n"
                f"**Margen Bruto:** {margen_pct}%\n"
                f"**Peso:** {peso_kg} kg\n\n"
            )
            if contexto_kb:
                user_prompt += f"**Contexto de transcripciones de mentores:**\n{contexto_kb[:3000]}\n\n"
            if contexto_archivos:
                user_prompt += f"**Contexto de KB (matriz de tendencias, fórmulas, operaciones):**\n{contexto_archivos[:3000]}\n\n"
            user_prompt += "Devuelve solo el copy en Markdown, sin explicaciones adicionales."

            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com"
            }
            payload = {
                "model": "google/gemini-2.0-flash-exp:free",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 2048
            }

            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                texto_generado = response.json()['choices'][0]['message']['content'].strip()
            except Exception as e:
                print(f"[ERROR] Fallo al generar copy con OpenRouter: {str(e)}")

        # 3. Si todo falló, usar template local
        if not texto_generado:
            print("[INFO] Pool híbrido y OpenRouter no disponibles. Usando template local.")
            return self.generar_copy_template(nombre_producto, categoria, costo_origen, pvp, peso_kg, contexto_kb)

        # Procesar respuesta de IA
        lineas = texto_generado.split("\n")
        titulo_generado = nombre_producto
        for linea in lineas:
            if linea.startswith("# ") and not linea.startswith("## "):
                titulo_generado = linea.replace("# ", "").strip()
                break

        scores = self.calcular_scores_aida(titulo_generado, texto_generado)
        es_valido, adjetivos = self.validar_sin_superlativos(texto_generado)

        return {
            'titulo': titulo_generado,
            'descripcion': texto_generado,
            'scores_aida': scores,
            'sin_superlativos': es_valido,
            'adjetivos_encontrados': adjetivos,
            'contexto_fuente': 'openrouter_aida',
            'timestamp': datetime.now().isoformat(),
        }
    def guardar_copy(self, producto_id: int, copy_data: Dict) -> int:
        """
        Guarda un copy generado en BD para auditoría.

        Args:
        producto_id: ID del producto (de productos_validados)
        copy_data: Dict con data del copy

        Returns:
        ID del copy guardado, o -1 si falla
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

            # Crear tabla si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS copys_generados (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto_id INTEGER,
                    titulo_copy TEXT NOT NULL,
                    descripcion TEXT NOT NULL,
                    attention_score REAL,
                    interest_score REAL,
                    decision_score REAL,
                    action_score REAL,
                    promedio_score REAL,
                    sin_superlativos BOOLEAN,
                    rating_usuario INTEGER DEFAULT 0,
                    context_kb_reference TEXT,
                    creada_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (producto_id) REFERENCES productos_validados(id) ON DELETE CASCADE
                )
            """)

            scores = copy_data.get('scores_aida', {})
            cursor.execute("""
                INSERT INTO copys_generados
                (producto_id, titulo_copy, descripcion, attention_score, interest_score,
                 decision_score, action_score, promedio_score, sin_superlativos, context_kb_reference)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                producto_id,
                copy_data['titulo'],
                copy_data['descripcion'],
                scores.get('attention'),
                scores.get('interest'),
                scores.get('decision'),
                scores.get('action'),
                scores.get('promedio'),
                copy_data['sin_superlativos'],
                copy_data.get('contexto_fuente', 'template')
            ))

            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"[ERROR] Guardar copy: {str(e)}")
        return -1

    def obtener_reporte_copywriting(self) -> Dict:
        """Obtiene reporte consolidado de copys generados."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as total,
                       AVG(promedio_score) as score_promedio,
                       SUM(CASE WHEN sin_superlativos = 1 THEN 1 ELSE 0 END) as sin_superlativos
                FROM copys_generados
            """)

            row = cursor.fetchone()
            if row:
                return {
                    'total_copys': row['total'] or 0,
                    'score_promedio': round(row['score_promedio'] or 0, 2),
                    'copys_sin_superlativos': row['sin_superlativos'] or 0
                }
        except Exception as e:
            print(f"[ERROR] Obtener reporte: {str(e)}")

        return {'total_copys': 0, 'score_promedio': 0.0, 'copys_sin_superlativos': 0}

    


