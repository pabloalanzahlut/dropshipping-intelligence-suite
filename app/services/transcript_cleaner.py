"""
TranscriptCleaner - Ultra-Limpieza de Transcripciones YouTube
Reduce consumo de tokens un 40-60% eliminando ruido, muletillas y paja comercial.

Funciones principales:
1. remove_vtt_timestamps()   - Borra timestamps VTT/SRT
2. remove_filler_words()     - Elimina muletillas de voz
3. remove_commercial_fluff() - Triture paja comercial (promos, CTAs, suscripciones) [NUEVO FASE 1]
4. detect_sections()         - Detecta cambios de tema por pausas
5. normalize_paragraphs()    - Unifica líneas en párrafos coherentes
6. validate_utf8()           - Valida encoding UTF-8
7. count_tokens_estimate()   - Estima tokens antes/después
8. clean_for_ia()            - Versión premium: retorna texto o "VACÍO" [NUEVO FASE 1]
"""

import re
import os
from typing import Dict, Tuple, List, Optional
from datetime import datetime


class TranscriptCleaner:
    """Limpiador agresivo de transcripciones para optimizar costos de IA."""

    # SOLO disfluencias sin significado propio. Palabras con significado ('no',
    # 'bueno', 'mira', 'tipo', 'esto', 'verdad'...) NO van aquí: borrarlas cambia
    # el sentido ("no funciona" -> "funciona") y falsea reglas y cifras.
    FILLER_WORDS_DEFAULT = [
        'eh', 'ehh', 'ehhh', 'ehm', 'em', 'emm',
        'umm', 'um', 'uh', 'uhh', 'uhm', 'err', 'erm',
        'mmm', 'mm', 'hmm', 'hmmm', 'o sea',
    ]

    # Etiquetas de sonido de los subtítulos automáticos: [Música], [Aplausos]...
    SOUND_TAG_PATTERN = (
        r'\[\s*(?:m[úu]sica|music|aplausos|applause|risas|laughter|'
        r'silencio|ruido|inaudible)[^\]]*\]|♪+'
    )

    TIMESTAMP_PATTERNS = [
        r'\d{1,2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{1,2}:\d{2}:\d{2}\.\d{3}',
        r'\d{1,2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{1,2}:\d{2}:\d{2},\d{3}',
        r'^\d+$\n',
    ]

    META_PATTERNS = [
        r'\[.*?\]',
        r'\(.*?\)',
        r'♪+',
        r'>>+',
        r'^\s*Speaker\s+\d+\s*:',
        r'^\s*-\s*$',
    ]

    COMMERCIAL_FLUFF_PATTERNS = [
        r'(?:suscr[íi]bete|suscr[íi]bance|dale\s+like|regalame\s+un\s+like)',
        r'(?:activa\s+la\s+(?:campanita|notificaciones)|comparte\s+el\s+v[íi]deo)',
        r'(?:no\s+olvides\s+(?:suscribirte|compartir|dar\s+like))',
        r'(?:c[oó]digo\s+(?:de\s+)?descuento|cup[oó]n\s+exclusivo)',
        r'(?:enlace\s+(?:en\s+)?la\s+(?:descripci[oó]n|biograf[íi]a|comentarios))',
        r'(?:link\s+en\s+descripci[oó]n|link\s+in\s+bio|más\s+info\s+en\s+link)',
        # No se borran 'oferta limitada', 'precio especial', 'compra ahora' ni
        # 'mi curso': los mentores los citan como ejemplos de copy/tácticas y
        # quitarlos destruye contenido útil. Solo se quita el boilerplate del canal.
        r'(?:s[ío]gueme\s+en\s+(?:insta|tiktok|twitter|telegram))',
        r'(?:únete\s+a\s+mi\s+(?:comunidad|grupo|newsletter|lista))',
        r'(?:no\s+te\s+lo\s+pierdas|te\s+va\s+encantar|esto\s+es\s+incre[íi]ble)',
        r'(?:quédate\s+hasta\s+el\s+final|no\s+te\s+vayas|espera\s+al\s+final)',
        r'(?:esto\s+te\s+cambiar[áa]\s+la\s+vida)',
        r'(?:v[íi]deo\s+(?:producido|editado|patrocinado)\s+por)',
    ]
    
    def __init__(self, filler_words: List[str] = None, min_pause_seconds: int = 5):
        """
        Args:
            filler_words: Lista personalizada de palabras relleno (si no se proporciona, usa defaults)
            min_pause_seconds: Duración mínima de pausa para detectar cambio de sección
        """
        self.filler_words = set(filler_words or self.FILLER_WORDS_DEFAULT)
        self.min_pause_seconds = min_pause_seconds
        self.cleaning_log = []
    
    def remove_vtt_timestamps(self, text: str) -> str:
        """
        Elimina timestamps VTT/SRT y números de secuencia.
        
        Args:
            text: Transcripción raw
        
        Returns:
            Texto sin timestamps
        """
        result = text
        for pattern in self.TIMESTAMP_PATTERNS:
            result = re.sub(pattern, '', result, flags=re.MULTILINE)
        return result
    
    def remove_filler_words(self, text: str) -> str:
        """
        Elimina muletillas y palabras relleno.
        También elimina repeticiones consecutivas de la misma palabra.
        
        Args:
            text: Transcripción raw
        
        Returns:
            Texto sin muletillas
        """
        # Eliminar muletillas (límites de palabra, sin distinguir mayúsculas).
        # Se consume también la coma que las acompaña ("eh, bueno" -> "bueno").
        result = text
        for word in sorted(self.filler_words, key=len, reverse=True):
            pattern = r'(?<!\w)' + re.escape(word) + r'(?!\w)[,;]?[ \t]*'
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)

        # Repeticiones consecutivas de la misma palabra ("de de la"): solo
        # palabras de letras; los números ("10 10") se respetan.
        result = re.sub(r'\b([^\W\d_]{2,})(\s+\1)+\b', r'\1', result, flags=re.IGNORECASE)

        # Puntuación huérfana que dejan las muletillas
        result = re.sub(r'\s+([,.;:!?])', r'\1', result)
        result = re.sub(r'([,;])\s*([,;])+', r'\1', result)
        result = re.sub(r'(^|[.!?]\s+|\n)[,;]\s*', r'\1', result)

        return result

    def remove_sound_tags(self, text: str) -> str:
        """Quita etiquetas de sonido de subtítulos ([Música], [Aplausos], ♪)."""
        return re.sub(self.SOUND_TAG_PATTERN, ' ', text, flags=re.IGNORECASE)
    
    def detect_sections(self, text: str) -> str:
        """
        Detecta cambios de tema por saltos de línea múltiples (pausas > min_pause_seconds).
        Agrega marcadores de sección "\\n---\\n" para separar temas.
        
        Args:
            text: Transcripción raw
        
        Returns:
            Texto con marcadores de sección
        """
        # Detectar múltiples saltos de línea como indicador de pausa
        result = re.sub(r'\n{3,}', '\n---\n', text)
        return result
    
    def normalize_paragraphs(self, text: str) -> str:
        """
        Normaliza párrafos: unifica líneas rotas, elimina espacios múltiples.
        Prepara el texto para conteo de tokens.
        
        Args:
            text: Transcripción raw
        
        Returns:
            Texto normalizado
        """
        # Eliminar espacios múltiples
        result = re.sub(r' {2,}', ' ', text)
        
        # Eliminar tabulaciones
        result = result.replace('\t', ' ')
        
        # Normalizar saltos de línea (máximo 2 consecutivos)
        result = re.sub(r'\n{2,}', '\n\n', result)
        
        # Eliminar espacios al inicio/final de líneas
        lines = result.split('\n')
        lines = [line.strip() for line in lines]
        result = '\n'.join(lines)
        
        # Eliminar líneas vacías en exceso
        result = re.sub(r'\n\n\n+', '\n\n', result)
        
        return result
    
    def validate_utf8(self, text: str) -> Tuple[str, bool, str]:
        """
        Valida y limpia caracteres UTF-8 problemáticos.
        
        Args:
            text: Transcripción raw
        
        Returns:
            (texto_limpio, es_valido, mensaje)
        """
        try:
            # Intentar encoding/decoding para detectar problemas
            text_bytes = text.encode('utf-8', errors='replace')
            text_cleaned = text_bytes.decode('utf-8', errors='replace')
            
            # Eliminar caracteres de control excepto saltos de línea
            text_cleaned = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text_cleaned)
            
            return text_cleaned, True, "UTF-8 válido"
        except Exception as e:
            return text, False, f"Error UTF-8: {str(e)}"
    
    def count_tokens_estimate(self, text: str) -> int:
        """Estima tokens: 1 token ≈ 3 caracteres para español."""
        return len(text) // 3

    def remove_commercial_fluff(self, text: str) -> str:
        """
        Triture paja comercial: elimina patrones de ventas, CTAs,
        solicitudes de suscripción, auto-promoción y ganchos vacíos.

        Reduce el texto hasta un 40% adicional.
        """
        result = text
        for pattern in self.COMMERCIAL_FLUFF_PATTERNS:
            result = re.sub(pattern, '', result,
                            flags=re.IGNORECASE | re.MULTILINE)
        # Limpiar espacios y líneas residuales
        result = re.sub(r' {2,}', ' ', result)
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result

    def clean(self, text: str, log_stats: bool = True,
              remove_fluff: bool = True) -> Dict:
        """
        Ejecuta pipeline completo de limpieza de forma secuencial.

        Args:
            text: Transcripción raw
            log_stats: Si True, registra estadísticas
            remove_fluff: Si True, activa triturado de paja comercial

        Returns:
            Dict con resultado completo y estadísticas
        """
        tokens_original = self.count_tokens_estimate(text)
        resultado = text
        pasos = []

        # 1. Validar UTF-8
        resultado, es_valido, msg_utf8 = self.validate_utf8(resultado)
        pasos.append(f"Validar UTF-8: {msg_utf8}")

        # 2. Eliminar timestamps
        resultado = self.remove_vtt_timestamps(resultado)
        pasos.append("Timestamps eliminados")

        # 3. Etiquetas de sonido y muletillas
        resultado = self.remove_sound_tags(resultado)
        resultado = self.remove_filler_words(resultado)
        pasos.append("Muletillas eliminadas")

        # 4. Triture paja comercial (hasta -40% tokens)
        if remove_fluff:
            resultado = self.remove_commercial_fluff(resultado)
            pasos.append("Paja comercial triturada")

        # 5. Detectar secciones
        resultado = self.detect_sections(resultado)
        pasos.append("Secciones detectadas")

        # 6. Normalizar párrafos
        resultado = self.normalize_paragraphs(resultado)
        pasos.append("Párrafos normalizados")

        # 7. Contar tokens finales
        tokens_limpio = self.count_tokens_estimate(resultado)
        reduccion_pct = (
            (tokens_original - tokens_limpio) / tokens_original * 100
        ) if tokens_original > 0 else 0

        salida = {
            'text_limpio': resultado,
            'tokens_original': tokens_original,
            'tokens_limpio': tokens_limpio,
            'reduccion_pct': round(reduccion_pct, 2),
            'pasos_ejecutados': pasos,
            'es_valido': es_valido,
            'timestamp_limpieza': datetime.now().isoformat(),
        }

        if log_stats:
            self.cleaning_log.append(salida)
            del self.cleaning_log[:-500]  # no crecer sin límite en procesos largos
        return salida

    def clean_for_ia(self, text: str) -> str:
        """
        Versión premium para consumo de IA.

        Workflow:
          1. Pipeline completo con triturado de fluff
          2. Si el texto resultante es muy corto o sin keywords técnicas,
             retorna "VACÍO" para ahorrar tokens de entrada.

        El system prompt constitucional con 3 subheadings debe ser inyectado
        por el llamador (ver SYSTEM_PROMPT_CRO).

        Returns:
            Texto limpio listo para el prompt, o "VACÍO" si no hay valor CRO.
        """
        cleaned = self.clean(text, log_stats=True, remove_fluff=True)
        text_limpio = cleaned["text_limpio"].strip()

        if len(text_limpio) < 50:
            return "VACÍO"

        # Detección de keywords técnicas de e-commerce/dropshipping
        tech_keywords = [
            'producto', 'precio', 'margen', 'venta', 'shopify', 'dropshipping',
            'proveedor', 'envío', 'cliente', 'conversión', 'anuncio',
            'facebook', 'tiktok', 'tráfico', 'costo', 'ganancia', 'nicho',
            'publicidad', 'landing', 'página', 'checkout', 'carrito',
            'embudo', 'segmentación', 'audiencia', 'compra',
            'logística', 'peso', 'aduana', 'stripe', 'paypal',
            'hook', 'creativo', 'campaña', 'presupuesto',
            'escalar', 'rentable', 'roi', 'cpa', 'coste', 'pedido',
        ]
        text_lower = text_limpio.lower()
        tech_count = sum(1 for kw in tech_keywords if kw in text_lower)

        if tech_count < 3 and len(text_limpio) < 200:
            return "VACÍO"

        return text_limpio

    def get_cleaning_stats(self) -> Dict:
        """
        Retorna estadísticas consolidadas de todas las limpiezas ejecutadas.
        
        Returns:
            Dict con promedios y totales
        """
        if not self.cleaning_log:
            return {'total_limpiezas': 0, 'promedio_reduccion_pct': 0}
        
        total_limpiezas = len(self.cleaning_log)
        promedio_reduccion = sum(log['reduccion_pct'] for log in self.cleaning_log) / total_limpiezas
        tokens_original_total = sum(log['tokens_original'] for log in self.cleaning_log)
        tokens_limpio_total = sum(log['tokens_limpio'] for log in self.cleaning_log)
        
        return {
            'total_limpiezas': total_limpiezas,
            'promedio_reduccion_pct': round(promedio_reduccion, 2),
            'tokens_original_total': tokens_original_total,
            'tokens_limpio_total': tokens_limpio_total,
            'ahorro_total_tokens': tokens_original_total - tokens_limpio_total,
            'ahorro_total_estimado_usd': round((tokens_original_total - tokens_limpio_total) * 0.000001, 4),  # Referencia: ~1 USD por 1M tokens
        }


def load_filler_words_from_env() -> List[str]:
    """Carga palabras relleno desde variable de entorno."""
    from dotenv import load_dotenv
    load_dotenv()
    filler_csv = os.getenv('TRANSCRIPT_CLEANER_FILLER_WORDS', '')
    if filler_csv:
        return [word.strip() for word in filler_csv.split(',')]
    return TranscriptCleaner.FILLER_WORDS_DEFAULT


# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT CONSTITUCIONAL — 3 Subheadings + VACÍO
# ═══════════════════════════════════════════════════════════════════════════
# Este prompt debe ser inyectado como system_prompt en las llamadas a la IA
# (FreeLLMAPI, OpenRouter, Ollama) para garantizar que la respuesta se
# estructure bajo los tres subheadings constitucionales y devuelva "VACÍO"
# si el material no tiene valor CRO.
# ═══════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT_CRO = (
    "Eres un extractor de datos de alto rendimiento especializado en "
    "Dropshipping y Shopify.\n"
    "Tu única tarea es analizar la transcripción de un video de un experto, "
    "eliminar todo el relleno "
    "(saludos, intros, promociones, pantallas de ganancias falsas, "
    "solicitudes de suscripción) y "
    "devolver la información técnica estructurada en Markdown.\n\n"
    "Divide los hallazgos estrictamente bajo estos tres subheadings "
    "si existen datos en el texto:\n"
    "### 1. Datos de Producto y Tendencias "
    "(Criterios, nichos, ángulos)\n"
    "### 2. Estructuras de Conversión y Copy "
    "(Ganchos, landing pages, apps)\n"
    "### 3. Logística, Tráfico y Legal "
    "(Presupuestos, segmentación, pasarelas, fletes)\n\n"
    "Si el texto no contiene datos de valor para ninguna categoría, "
    "devuelve únicamente la palabra: VACÍO."
)
