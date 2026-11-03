"""
YouTubeChannelMonitor - Monitor Automático de Canales YouTube
Descarga transcripciones VTT/SRT automáticamente de canales configurados.

Workflow:
1. Cargar lista de canales (desde config JSON)
2. Escanear canales para nuevos videos
3. Descargar transcripciones VTT/SRT
4. Generar hash MD5 para deduplicación
5. Guardar en BD
6. Ejecutar limpieza ultra
"""

import os
import json
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import subprocess
from pathlib import Path

from app.database.connection import DatabaseConnection
from app.services.transcript_cleaner import TranscriptCleaner
from app.services.youtube_rss_fetcher import fetch_channel_videos, download_transcript, hash_content


class YouTubeChannelMonitor:
    """Monitor de canales YouTube con descarga automática de transcripciones."""
    
    def __init__(self, db_manager: Optional[DatabaseConnection] = None, config_path: str = "youtube_channels.json"):
        """
        Args:
            db_manager: Gestor de BD
            config_path: Ruta al archivo de configuración de canales
        """
        self.db_manager = db_manager if db_manager else DatabaseConnection()
        self.config_path = config_path
        self.canales = self._cargar_canales()
        self.cleaner = TranscriptCleaner()
        self.monitor_log = []
    
    def _cargar_canales(self) -> List[Dict]:
        """
        Carga lista de canales desde archivo JSON.
        Estructura esperada:
        [
            {"url": "https://www.youtube.com/@channel1", "nombre": "Channel 1"},
            ...
        ]
        
        Returns:
            Lista de dicts con canales, o [] si no existe archivo
        """
        if not os.path.exists(self.config_path):
            # Crear archivo de ejemplo si no existe
            canales_default = [
                {"url": "https://www.youtube.com/@canalmentores", "nombre": "Canal Mentores"}
            ]
            self._guardar_canales(canales_default)
            return canales_default
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] YouTubeChannelMonitor: No se pudo cargar {self.config_path}: {str(e)}")
            return []
    
    def _guardar_canales(self, canales: List[Dict]) -> bool:
        """Guarda lista de canales en archivo JSON."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(canales, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[ERROR] No se pudo guardar canales: {str(e)}")
            return False
    
    def agregar_canal(self, url: str, nombre: str,
                      tags: str = "", idioma: str = "es",
                      prioridad: int = 5, max_videos_scan: int = 30) -> bool:
        """Agrega un nuevo canal al JSON y a la tabla canales_favoritos."""
        handle = url.rstrip("/").split("/")[-1].lower()
        nuevo_canal = {
            "url": url, "nombre": nombre, "activo": True,
            "tags": [t.strip() for t in tags.split(",") if t.strip()],
            "prioridad": prioridad, "idioma": idioma,
            "max_videos_scan": max_videos_scan,
        }
        self.canales.append(nuevo_canal)
        guardado = self._guardar_canales(self.canales)
        # Sincronizar también en canales_favoritos
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO canales_favoritos
                       (handle, nombre, url, idioma, especialidad, tags, prioridad)
                       VALUES (?,?,?,?,?,?,?)""",
                    (handle, nombre, url, idioma, "general", tags, prioridad)
                )
                conn.commit()
        except Exception as e:
            print(f"[WARN] No se pudo insertar en canales_favoritos: {e}")
        return guardado
    
    def hash_transcripcion(self, contenido: str) -> str:
        """Genera hash MD5 de una transcripción para deduplicación."""
        return hashlib.md5(contenido.encode('utf-8')).hexdigest()
    
    def descargar_transcripcion_mock(self, video_id: str, titulo: str, canal: str) -> Optional[str]:
        """
        Mock para descargar transcripción (en implementación real, usa yt-dlp).
        
        Para desarrollo, retorna transcripción de ejemplo.
        En producción, integrar con yt-dlp o youtube-transcript-api.
        
        Args:
            video_id: ID del video (ej: "dQw4w9WgXcQ")
            titulo: Título del video
            canal: Nombre del canal
        
        Returns:
            Contenido de transcripción (texto limpio), o None si falla
        """
        # Mock: Retornar transcripción de ejemplo
        ejemplo_transcripcion = f"""
[{canal}] {titulo}

Eh, bueno, mira entonces, umm ok, hoy vamos a hablar de validación de productos en dropshipping.
Entonces, la regla 3x significa que si el producto cuesta $10, el precio debe ser $30.
Además, el margen debe ser mayor al 70%, sabes, eso es crítico para la viabilidad del negocio.

Ehh, también importante es validar el peso, umm, debe ser menor a 1.2 kilogramos.
Verdad, ok, estos tres factores son inmutables en nuestro sistema.

Entonces, cuando validas un producto, asegúrate de que:
- Costo origen es conocido
- PVP cumple Regla 3x
- Margen bruto es >= 70%
- Peso neto es < 1.2 kg

Mira, además, en TikTok y YouTube tienes que comunicar estos insights de forma que el viewer
entienda por qué el producto es viable. Ehh, los hook patterns más efectivos son:
story-telling, curiosity-gap, shock, humor.

Ok, entonces para el copywriting en Shopify, recuerda el framework AIDA:
Attention (títulos llamativos), Interest (descripción del problema), Decision (cómo resuelves),
Action (botón de compra). Nunca uses adjetivos superlativos vacíos como "increíble" o "alucinante".

Bueno, creo que esto cubre los fundamentos. Vamos al siguiente tema...
        """.strip()
        
        return ejemplo_transcripcion
    
    def procesar_transcripcion(self, video_id: str, titulo: str, canal: str, transcripcion_raw: str) -> Optional[Dict]:
        """
        Procesa una transcripción: limpia, deduplica, guarda en BD.
        
        Args:
            video_id: ID del video
            titulo: Título del video
            canal: Nombre del canal
            transcripcion_raw: Contenido raw de transcripción
        
        Returns:
            Dict con resultado del procesamiento, o None si falla
        """
        
        # 1. Generar hash para deduplicación
        hash_md5 = self.hash_transcripcion(transcripcion_raw)
        
        # 2. Verificar si ya existe
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM transcripciones_youtube WHERE hash_md5 = ?", (hash_md5,))
                if cursor.fetchone():
                    return {
                        'video_id': video_id,
                        'duplicado': True,
                        'hash_md5': hash_md5,
                        'mensaje': 'Transcripción duplicada, no procesada'
                    }
        except Exception as e:
            print(f"[ERROR] Error verificando duplicado: {str(e)}")
            return None
        
        # 3. Limpiar transcripción
        resultado_limpieza = self.cleaner.clean(transcripcion_raw, log_stats=True)
        transcripcion_limpia = resultado_limpieza['text_limpio']
        tokens_original = resultado_limpieza['tokens_original']
        tokens_limpio = resultado_limpieza['tokens_limpio']
        
        # 4. Guardar en BD (primero insertar en video_sources para respetar FK)
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                # Asegurar que el video exista en video_sources (idempotente)
                cursor.execute("""
                            INSERT OR IGNORE INTO video_sources
                            (video_id, platform, title, channel_name, content_hash)
                VALUES (?, 'youtube', ?, ?, ?)
                        """, (video_id, titulo, canal, hash_md5))
                # Insertar transcripción
                cursor.execute("""
                            INSERT INTO transcripciones_youtube
                            (video_id, titulo, canal, fecha, transcripcion_texto, transcripcion_limpia, 
                hash_md5, tokens_original, tokens_limpios, procesada)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                video_id,
                titulo,
                canal,
                datetime.now().isoformat(),
                transcripcion_raw[:5000],  # Guardar primeros 5000 chars
                transcripcion_limpia,
                hash_md5,
                tokens_original,
                tokens_limpio,
                True
                ))
                conn.commit()
                
                return {
                    'video_id': video_id,
                    'duplicado': False,
                    'hash_md5': hash_md5,
                    'titulo': titulo,
                    'canal': canal,
                    'tokens_original': tokens_original,
                    'tokens_limpio': tokens_limpio,
                    'reduccion_pct': resultado_limpieza['reduccion_pct'],
                    'mensaje': 'Transcripción procesada exitosamente'
                }
        except Exception as e:
            print(f"[ERROR] Error guardando transcripción: {str(e)}")
            return None
    
    def sincronizar_canales(self) -> Dict:
        """
        Sincroniza todos los canales via RSS + yt-dlp (sin YouTube API key, sin costo).
        """
        stats = {
            'fecha_sincronizacion': datetime.now().isoformat(),
            'canales_procesados': 0,
            'videos_descargados': 0,
            'transcripciones_procesadas': 0,
            'duplicados': 0,
            'errores': 0,
            'tokens_ahorrados': 0,
            'detalles': []
        }

        for canal_info in self.canales:
            if not canal_info.get('activo', True):
                continue

            canal_url = canal_info.get('url', '')
            canal_nombre = canal_info.get('nombre', 'Sin nombre')
            idioma = canal_info.get('idioma', 'es')
            max_scan = canal_info.get('max_videos_scan', 15)

            # Obtener lista de videos via RSS (gratuito)
            videos = fetch_channel_videos(canal_url, max_videos=max_scan)
            if not videos:
                print(f"[MONITOR] Sin videos RSS para {canal_nombre}")
                stats['errores'] += 1
                stats['canales_procesados'] += 1
                continue

            for video in videos:
                video_id = video['video_id']
                titulo = video['title']

                try:
                    # Descargar transcripción con yt-dlp (gratuito)
                    transcripcion = download_transcript(video_id, lang=idioma)
                    if not transcripcion:
                        stats['errores'] += 1
                        continue

                    stats['videos_descargados'] += 1

                    resultado = self.procesar_transcripcion(video_id, titulo, canal_nombre, transcripcion)
                    if resultado:
                        if resultado['duplicado']:
                            stats['duplicados'] += 1
                        else:
                            stats['transcripciones_procesadas'] += 1
                            stats['tokens_ahorrados'] += (resultado['tokens_original'] - resultado['tokens_limpio'])
                        stats['detalles'].append(resultado)
                    else:
                        stats['errores'] += 1

                except Exception as e:
                    print(f"[ERROR] Error procesando {titulo}: {str(e)}")
                    stats['errores'] += 1

            stats['canales_procesados'] += 1

        self.monitor_log.append(stats)
        return stats
    
    def obtener_estado_monitor(self) -> Dict:
        """Retorna estado actual del monitor."""
        activos = [c for c in self.canales if c.get('activo', True)]
        return {
            'canales_activos': len(activos),
            'canales': self.canales,
            'sincronizaciones': len(self.monitor_log),
            'ultima_sincronizacion': self.monitor_log[-1] if self.monitor_log else None
        }

    def obtener_canales_favoritos(self) -> List[Dict]:
        """Lee canales_favoritos desde la DB (incluye metadata extendida)."""
        try:
            with self.db_manager.get_connection() as conn:
                rows = conn.execute(
                    """SELECT nombre, handle, url, idioma, especialidad, tags, prioridad, activo,
                              video_count, last_scan_at, notas
                       FROM canales_favoritos ORDER BY prioridad, nombre"""
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            print(f"[ERROR] obtener_canales_favoritos: {e}")
            return []

    def obtener_videos_favoritos(self, limite: int = 100) -> List[Dict]:
        """Lee videos_favoritos desde la DB."""
        try:
            with self.db_manager.get_connection() as conn:
                rows = conn.execute(
                    """SELECT video_id, titulo, canal, url, razon, tags,
                              transcripcion_procesada, guardado_at
                       FROM videos_favoritos ORDER BY guardado_at DESC LIMIT ?""",
                    (limite,)
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            print(f"[ERROR] obtener_videos_favoritos: {e}")
            return []

    def obtener_playlists(self) -> List[Dict]:
        """Lee playlists_favoritas desde la DB."""
        try:
            with self.db_manager.get_connection() as conn:
                rows = conn.execute(
                    """SELECT playlist_id, titulo, canal, url, es_privada, tags,
                              activa, video_count, last_scan_at, agregada_at
                       FROM playlists_favoritas ORDER BY activa DESC, titulo"""
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            print(f"[ERROR] obtener_playlists: {e}")
            return []

    def obtener_resumen_canales(self) -> List[Dict]:
        """Lee la vista v_resumen_canales para el dashboard."""
        try:
            with self.db_manager.get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM v_resumen_canales ORDER BY prioridad, nombre"
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            print(f"[ERROR] obtener_resumen_canales: {e}")
            return []
    
    def obtener_transcripciones_limpias(self, limite: int = 10) -> List[Dict]:
        """Obtiene últimas transcripciones limpias de BD."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, video_id, titulo, canal, fecha, tokens_original, tokens_limpios
                    FROM transcripciones_youtube
                    WHERE procesada = 1
                    ORDER BY creada_at DESC
                    LIMIT ?
                """, (limite,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"[ERROR] Error obteniendo transcripciones: {str(e)}")
            return []
