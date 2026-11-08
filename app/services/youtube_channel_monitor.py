"""
YouTubeChannelMonitor - Monitor Automático de Canales YouTube
Descarga subtítulos de los canales configurados y guarda transcripciones limpias.

Workflow:
1. Cargar canales (youtube_channels.json + canales_favoritos de la BD)
2. Listar vídeos recientes de cada canal (RSS, con yt-dlp como respaldo)
3. Descargar subtítulos SOLO de vídeos que aún no están guardados
4. Limpiar, deduplicar por hash y guardar (transcript_store)
"""

import json
import os
import random
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

from app.database.connection import DatabaseConnection
from app.services import topic_filter, transcript_store
from app.services.transcript_cleaner import TranscriptCleaner
from app.services.youtube_rss_fetcher import RateLimited, download_transcript, fetch_channel_videos

# Pausa aleatoria entre descargas (s) y esperas ante HTTP 429 de YouTube (s)
PAUSA_ENTRE_DESCARGAS = (6.0, 14.0)
ESPERAS_429 = (60, 180, 420)
# YouTube corta tras ~15-20 descargas de subtítulos seguidas y tarda más de 15 min en
# levantar el bloqueo: se trabaja por lotes y, si aun así bloquea, se deja enfriar.
MAX_DESCARGAS_POR_SYNC = 15
COOLDOWN_429_MIN = 45

_YOUTUBE_CHANNEL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?youtube\.com/"
    r"(?:@[A-Za-z0-9._-]+|channel/UC[A-Za-z0-9_-]+|c/[A-Za-z0-9_.-]+|user/[A-Za-z0-9_.-]+)/?$"
)


def _norm_url(url: str) -> str:
    """Clave de comparación de URLs de canal (sin esquema, www ni barra final)."""
    u = (url or "").strip().lower().rstrip("/")
    return re.sub(r"^https?://(www\.)?", "", u)


class YouTubeChannelMonitor:
    """Monitor de canales YouTube con descarga automática de transcripciones."""

    def __init__(self, db_manager: Optional[DatabaseConnection] = None,
                 config_path: Optional[str] = None):
        """
        Args:
            db_manager: Gestor de BD
            config_path: JSON de canales (por defecto el de PathManager: data/youtube_channels.json)
        """
        self.db_manager = db_manager if db_manager else DatabaseConnection()
        if config_path is None:
            from app.config.path_manager import PathManager
            config_path = str(PathManager.get_paths()["config"])
        self.config_path = config_path
        self._last_sync_path = Path(config_path).with_name("last_sync.json")
        self._descartados_path = Path(config_path).with_name("videos_descartados.json")
        self._cooldown_path = Path(config_path).with_name("sync_cooldown.json")
        self.cleaner = TranscriptCleaner()
        self.monitor_log: List[Dict] = []
        self.ultimo_error = ""
        self._cancel = threading.Event()
        self.canales = self._cargar_canales()

    @property
    def db_path(self) -> str:
        return self.db_manager.db_path

    # ───────────────────────────── canales ──────────────────────────────────

    def _leer_json(self) -> List[Dict]:
        if not os.path.exists(self.config_path):
            return []
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as e:
            print(f"[ERROR] YouTubeChannelMonitor: no se pudo leer {self.config_path}: {e}")
            return []

    def _cargar_canales(self) -> List[Dict]:
        """Une el JSON con los canales activos de la BD (sin duplicar por URL).
        El JSON manda: trae max_videos_scan, rol y notas."""
        canales = self._leer_json()
        vistos = {_norm_url(c.get("url", "")) for c in canales}
        try:
            with self.db_manager.get_connection() as conn:
                rows = conn.execute(
                    """SELECT nombre, url, idioma, tags, prioridad, activo, filtro_tema
                       FROM canales_favoritos
                       WHERE activo = 1 AND url IS NOT NULL AND url != ''"""
                ).fetchall()
            for r in rows:
                if _norm_url(r["url"]) in vistos:
                    continue
                vistos.add(_norm_url(r["url"]))
                canales.append({
                    "url": r["url"], "nombre": r["nombre"], "activo": True,
                    "tags": [t.strip() for t in (r["tags"] or "").split(",") if t.strip()],
                    "prioridad": r["prioridad"] or 5, "idioma": r["idioma"] or "es",
                    "max_videos_scan": 15,
                    # Se decide por canal en la BD (se edita desde la web): con el filtro solo
                    # se guardan vídeos de ecommerce/dropshipping (p. ej. descarta "Gian's Tech")
                    "filtro_tema": bool(r["filtro_tema"]),
                })
        except Exception as e:
            print(f"[WARN] No se pudieron leer canales_favoritos: {e}")
        return canales

    def _guardar_canales(self, canales: List[Dict]) -> bool:
        """Guarda el JSON de forma atómica (archivo temporal + reemplazo)."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.config_path)), exist_ok=True)
            tmp = self.config_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(canales, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.config_path)
            return True
        except Exception as e:
            print(f"[ERROR] No se pudo guardar canales: {e}")
            return False

    def agregar_canal(self, url: str, nombre: str,
                      tags: str = "", idioma: str = "es",
                      prioridad: int = 5, max_videos_scan: int = 30) -> bool:
        """Agrega un canal al JSON y a canales_favoritos. Si falla, el motivo queda
        en self.ultimo_error."""
        self.ultimo_error = ""
        url = (url or "").strip()
        nombre = (nombre or "").strip()
        if not _YOUTUBE_CHANNEL_RE.match(url):
            self.ultimo_error = "URL de canal no válida (ej: https://www.youtube.com/@canal)"
            return False
        if not nombre:
            self.ultimo_error = "Falta el nombre del canal"
            return False
        if any(_norm_url(c.get("url", "")) == _norm_url(url) for c in self.canales):
            self.ultimo_error = "Ese canal ya está registrado"
            return False

        handle = url.rstrip("/").split("/")[-1].lower()
        nuevo = {
            "url": url, "nombre": nombre, "activo": True,
            "tags": [t.strip() for t in tags.split(",") if t.strip()],
            "prioridad": prioridad, "idioma": idioma,
            "max_videos_scan": max_videos_scan,
        }
        # JSON: releer del disco para no pisar cambios hechos por la web
        en_disco = self._leer_json()
        en_disco.append(nuevo)
        if not self._guardar_canales(en_disco):
            self.ultimo_error = "No se pudo escribir el archivo de canales"
            return False
        self.canales.append(nuevo)
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO canales_favoritos
                       (handle, nombre, url, idioma, especialidad, tags, prioridad)
                       VALUES (?,?,?,?,?,?,?)""",
                    (handle, nombre, url, idioma, "general", tags, prioridad),
                )
                conn.commit()
        except Exception as e:
            print(f"[WARN] No se pudo insertar en canales_favoritos: {e}")
        return True

    # ─────────────────────────── transcripciones ────────────────────────────

    def hash_transcripcion(self, contenido: str) -> str:
        """Hash MD5 de una transcripción para deduplicación."""
        return transcript_store.hash_text(contenido)

    def procesar_transcripcion(self, video_id: str, titulo: str, canal: str,
                               transcripcion_raw: str, idioma: str = "es") -> Optional[Dict]:
        """Limpia y guarda una transcripción (ver transcript_store.save_transcript).
        Devuelve None si falla; el motivo queda en self.ultimo_error."""
        try:
            return transcript_store.save_transcript(
                self.db_path, video_id, titulo, canal, transcripcion_raw,
                self.cleaner, idioma,
            )
        except Exception as e:
            self.ultimo_error = str(e)
            print(f"[ERROR] Error guardando transcripción {video_id}: {e}")
            return None

    # ───────────────────────────── sincronización ───────────────────────────

    # ── vídeos descartados por tema (no se vuelven a descargar) ──────────────

    def _leer_descartados(self) -> Dict[str, Dict]:
        try:
            data = json.loads(self._descartados_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def descartar_video(self, video_id: str, titulo: str, canal: str, motivo: str) -> None:
        """Recuerda que este vídeo no es del tema, para no descargarlo otra vez."""
        data = self._leer_descartados()
        data[video_id] = {"titulo": titulo, "canal": canal, "motivo": motivo,
                          "fecha": datetime.now().isoformat(timespec="seconds")}
        try:
            tmp = str(self._descartados_path) + ".tmp"
            Path(tmp).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, self._descartados_path)
        except Exception as e:
            print(f"[WARN] No se pudo guardar videos_descartados.json: {e}")

    def cooldown_hasta(self) -> Optional[datetime]:
        """Hasta cuándo no conviene volver a descargar (tras un 429), o None."""
        try:
            hasta = datetime.fromisoformat(
                json.loads(self._cooldown_path.read_text(encoding="utf-8"))["hasta"])
            return hasta if hasta > datetime.now() else None
        except Exception:
            return None

    def _iniciar_cooldown(self) -> datetime:
        from datetime import timedelta
        hasta = datetime.now() + timedelta(minutes=COOLDOWN_429_MIN)
        try:
            self._cooldown_path.write_text(
                json.dumps({"hasta": hasta.isoformat(timespec="seconds")}), encoding="utf-8")
        except Exception as e:
            print(f"[WARN] No se pudo guardar sync_cooldown.json: {e}")
        return hasta

    def _esperar(self, segundos: float) -> bool:
        """Espera en tramos de 1 s; devuelve False si se canceló mientras tanto."""
        fin = time.monotonic() + segundos
        while time.monotonic() < fin:
            if self._cancel.wait(1.0):
                return False
        return True

    def _descargar(self, video_id: str, idioma: str, say: Callable[[str], None]) -> Optional[str]:
        """Descarga la transcripción; ante un 429 espera y reintenta (60 s, 3 min, 7 min).
        Lanza RateLimited si sigue limitado tras los reintentos."""
        for intento in range(len(ESPERAS_429) + 1):
            try:
                return download_transcript(video_id, lang=idioma)
            except RateLimited:
                if intento == len(ESPERAS_429):
                    raise
                espera = ESPERAS_429[intento]
                say(f"YouTube limita las descargas: espero {espera} s y reintento…")
                if not self._esperar(espera):
                    return None
        return None

    def cancelar_sincronizacion(self) -> None:
        """Pide parar la sincronización en curso (termina el vídeo actual)."""
        self._cancel.set()

    def sincronizar_canales(self, progress: Optional[Callable[[str], None]] = None,
                            max_nuevos_por_canal: int = 10) -> Dict:
        """
        Sincroniza los canales activos: lista vídeos (RSS/yt-dlp) y descarga SOLO
        los que aún no están guardados, con pausa entre descargas para no ser
        bloqueado por YouTube.
        """
        say = progress or (lambda _m: None)
        self._cancel.clear()
        self.canales = self._cargar_canales()
        stats = {
            "fecha_sincronizacion": datetime.now().isoformat(timespec="seconds"),
            "canales_procesados": 0, "videos_descargados": 0,
            "transcripciones_procesadas": 0, "duplicados": 0, "sin_subtitulos": 0,
            "fuera_de_tema": 0, "errores": 0, "tokens_ahorrados": 0,
            "cancelado": False, "limitado": False, "lote_completo": False,
            "reintentar_a": None, "detalles": [],
        }
        # Tras un 429 reciente no se vuelve a insistir: alargaría el bloqueo
        hasta = self.cooldown_hasta()
        if hasta:
            stats["limitado"] = True
            stats["reintentar_a"] = hasta.isoformat(timespec="seconds")
            say(f"YouTube limitó las descargas: reintenta a partir de las {hasta:%H:%M}.")
            return stats
        guardados = transcript_store.video_ids_guardados(self.db_path)
        guardados |= set(self._leer_descartados())   # ya vistos y descartados por tema
        activos = sorted((c for c in self.canales if c.get("activo", True)),
                         key=lambda c: c.get("prioridad", 5))
        descargas = 0

        for canal_info in activos:
            if self._cancel.is_set() or stats["limitado"] or stats["lote_completo"]:
                break
            url = canal_info.get("url", "")
            nombre = canal_info.get("nombre", "Sin nombre")
            idioma = canal_info.get("idioma", "es")
            max_scan = int(canal_info.get("max_videos_scan", 15) or 15)

            say(f"Escaneando {nombre}…")
            videos = fetch_channel_videos(url, max_videos=max_scan)
            stats["canales_procesados"] += 1
            if not videos:
                print(f"[MONITOR] Sin vídeos para {nombre}")
                stats["errores"] += 1
                continue

            nuevos = [v for v in videos if v["video_id"] not in guardados][:max_nuevos_por_canal]
            for video in nuevos:
                if self._cancel.is_set():
                    break
                if descargas >= MAX_DESCARGAS_POR_SYNC:
                    stats["lote_completo"] = True
                    say(f"Lote de {MAX_DESCARGAS_POR_SYNC} descargas completo: "
                        "vuelve a sincronizar en ~30 min para seguir (así YouTube no te bloquea).")
                    break
                if descargas and not self._esperar(random.uniform(*PAUSA_ENTRE_DESCARGAS)):
                    break   # pausa anti-bloqueo; cancelada durante la espera
                descargas += 1
                titulo = video.get("title", "")
                say(f"{nombre}: {titulo[:60]}")
                try:
                    texto = self._descargar(video["video_id"], idioma, say)
                    if self._cancel.is_set():
                        break
                    if not texto:
                        stats["sin_subtitulos"] += 1
                        continue
                    stats["videos_descargados"] += 1
                    if canal_info.get("filtro_tema"):
                        es_tema, motivo = topic_filter.evaluar(titulo, texto)
                        if not es_tema:
                            self.descartar_video(video["video_id"], titulo, nombre, motivo)
                            stats["fuera_de_tema"] += 1
                            say(f"{nombre}: fuera de tema ({motivo}) — {titulo[:50]}")
                            continue
                    res = self.procesar_transcripcion(
                        video["video_id"], titulo, video.get("channel") or nombre,
                        texto, idioma)
                    if not res:
                        stats["errores"] += 1
                    elif res["duplicado"]:
                        stats["duplicados"] += 1
                    else:
                        stats["transcripciones_procesadas"] += 1
                        stats["tokens_ahorrados"] += res["tokens_original"] - res["tokens_limpio"]
                        stats["detalles"].append(res)
                        guardados.add(video["video_id"])
                except RateLimited:
                    stats["limitado"] = True
                    stats["reintentar_a"] = self._iniciar_cooldown().isoformat(timespec="seconds")
                    say("YouTube sigue limitando las descargas: sincronización detenida. "
                        f"Reintenta a partir de las {stats['reintentar_a'][11:16]} "
                        "(lo ya guardado se conserva).")
                    break
                except Exception as e:
                    print(f"[ERROR] Error procesando {titulo}: {e}")
                    stats["errores"] += 1

            self._marcar_escaneo(url)

        stats["cancelado"] = self._cancel.is_set()
        self.monitor_log.append(stats)
        del self.monitor_log[:-20]
        self._guardar_ultima_sync(stats)
        return stats

    def _marcar_escaneo(self, url: str) -> None:
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute(
                    """UPDATE canales_favoritos SET last_scan_at = ?
                       WHERE lower(rtrim(url, '/')) = lower(rtrim(?, '/'))""",
                    (datetime.now().isoformat(timespec="seconds"), url),
                )
                conn.commit()
        except Exception as e:
            print(f"[WARN] No se pudo marcar last_scan_at: {e}")

    def _guardar_ultima_sync(self, stats: Dict) -> None:
        """Persiste el resumen (sin detalles) para verlo tras reiniciar la app."""
        try:
            resumen = {k: v for k, v in stats.items() if k != "detalles"}
            self._last_sync_path.write_text(
                json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[WARN] No se pudo guardar last_sync.json: {e}")

    def _leer_ultima_sync(self) -> Optional[Dict]:
        try:
            return json.loads(self._last_sync_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def obtener_estado_monitor(self) -> Dict:
        """Retorna estado actual del monitor."""
        activos = [c for c in self.canales if c.get("activo", True)]
        ultima = self.monitor_log[-1] if self.monitor_log else self._leer_ultima_sync()
        return {
            "canales_activos": len(activos),
            "canales": self.canales,
            "sincronizaciones": len(self.monitor_log),
            "ultima_sincronizacion": ultima,
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
