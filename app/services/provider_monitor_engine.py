"""
ProviderMonitorEngine — Motor de Monitoreo e Ingesta de Canales YouTube
=========================================================================
Arquitectura FASE 1:
  - PathManager centralizado para TODAS las rutas
  - UserAgentRotation para evitar rate limits
  - ThrottleController (max 10 videos/hora)
  - Exponential Backoff con Jitter en operaciones de red
  - QueueStateManager para persistencia resiliente
  - cookies.txt opcional para autenticación

Regla de Gobernanza:
  - NO altera Tkinter UI
  - NO altera esquema SQLite
  - NO altera lógica adaptativa FreeLLMAPI
"""

import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
from typing import Callable, Dict, List, Optional, Any

from app.config.path_manager import PathManager
from app.database.connection import DatabaseConnection
from app.services.queue_state_manager import (
    QueueStateManager,
    STATUS_PENDING,
    STATUS_PROCESSING,
    STATUS_COMPLETED,
    STATUS_FAILED,
)
from app.services.kb_cache_validator import KBCacheValidator
from app.services.kb_router import KBRouter
from app.services.openrouter_client import OpenRouterTranscriptionCleaner
from app.services.throttle_controller import ThrottleController
from app.services.user_agent_rotation import UserAgentRotator
from app.services.transcript_cleaner import TranscriptCleaner
from app.core.retry_decorator import with_retry


_GEM_PATHS = PathManager.get_paths()
DATA_DIR = str(_GEM_PATHS['data'])
TEMP_TRANSCRIPT_DIR = str(_GEM_PATHS['data'] / "temp_transcripts")

# Cuántos videos recientes mirar por canal cuando no hay max_videos_scan.
# YouTube los lista del más nuevo al más viejo, así que el corte deja fuera
# el histórico ya ingerido en vez de reenumerarlo en cada ejecución.
DEFAULT_SCAN_LIMIT = 30


def _safe_print(msg: str) -> None:
    """
    print() por defecto del engine.

    La consola de Windows usa cp1252 y estos logs llevan emojis: con print()
    a secas, un UnicodeEncodeError aborta la ingesta entera.
    """
    try:
        print(msg)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "ascii"
        print(str(msg).encode(enc, errors="replace").decode(enc, errors="replace"))

# Validación de URLs de canal YouTube (FASE 6C — fuente de verdad unificada)
# Soporta: @handle, /channel/UC..., /c/..., /user/...
_YOUTUBE_CHANNEL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/"
    r"(?:@[A-Za-z0-9._-]+|channel/UC[A-Za-z0-9_-]+|c/[A-Za-z0-9_.-]+|user/[A-Za-z0-9_.-]+)"
    r"/?$"
)


class ProviderMonitorEngine:
    """
    Motor de monitoreo con ingesta real usando yt-dlp + rotación User-Agent
    + control de flujo por lotes + persistencia de cola.
    """

    def __init__(self, db_manager: Optional[DatabaseConnection] = None):
        self.db_manager = db_manager if db_manager else DatabaseConnection()
        self.validator = KBCacheValidator(db_path=self.db_manager.db_path)
        self.router = KBRouter(db_path=self.db_manager.db_path)
        self.cleaner = OpenRouterTranscriptionCleaner()
        self.transcript_cleaner = TranscriptCleaner()

        # Nuevas dependencias FASE 1
        self.queue_manager = QueueStateManager()
        self.user_agent_rotator = UserAgentRotator.create_with_pathmanager()
        self.throttle = ThrottleController(
            max_per_hour=10,
            persist_path=str(_GEM_PATHS['data'] / "throttle_state.json"),
        )

        # Callbacks para ConsoleView Tkinter (sin romper UI)
        self.log_callback: Callable = _safe_print
        self.progress_callback: Callable = lambda x: None

        os.makedirs(TEMP_TRANSCRIPT_DIR, exist_ok=True)
        self.scan_limits: Dict[str, int] = {}
        self.channel_roles: Dict[str, str] = {}   # "primaria" | "complementaria"
        self.favorite_channels = self._load_channels_from_json()
        self._sync_channels_to_queue()

    @staticmethod
    def _normalize_youtube_url(url: str) -> str:
        """Normaliza una URL de canal YouTube a formato canónico https://www.youtube.com/..."""
        url = (url or "").strip()
        if not url:
            return ""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        # Unificar subdominio www.
        url = url.replace("https://youtube.com/", "https://www.youtube.com/")
        url = url.replace("http://youtube.com/", "https://www.youtube.com/")
        return url.rstrip("/")

    @staticmethod
    def _valid_youtube_url(url: str) -> bool:
        """Valida que una URL sea un canal de YouTube válido (FASE 6C)."""
        return bool(_YOUTUBE_CHANNEL_RE.match(url))

    def _load_channels_from_json(self) -> Dict[str, str]:
        """
        Carga canales desde youtube_channels.json (única fuente de verdad).
        Valida formato de URL y filtra canales inactivos.
        Fallback a config.json canales_mentores.
        Fallback final a defaults hardcodeados de los 5 mentores reales.
        """
        # 1. Intentar youtube_channels.json
        channels_path = str(_GEM_PATHS['config'])
        if os.path.exists(channels_path):
            try:
                with open(channels_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                channels = {}
                for entry in data:
                    url = entry.get("url", "")
                    nombre = entry.get("nombre", "")
                    activo = entry.get("activo", True)
                    if not url or not nombre or not activo:
                        continue
                    url = self._normalize_youtube_url(url)
                    if not self._valid_youtube_url(url):
                        self.log_callback(
                            f"⚠️ [CHANNELS] URL inválida omitida: {nombre} -> {url}")
                        continue
                    channels[nombre] = url
                    self.scan_limits[nombre] = int(
                        entry.get("max_videos_scan", DEFAULT_SCAN_LIMIT))
                    self.channel_roles[nombre] = entry.get("rol", "complementaria")
                if channels:
                    self.log_callback(
                        f"📡 [CHANNELS] Cargados {len(channels)} canales desde "
                        f"{os.path.basename(channels_path)}")
                    return channels
            except Exception as e:
                self.log_callback(
                    f"❌ [CHANNELS] Error youtube_channels.json: {e}")

        # 2. Fallback: config.json canales_mentores
        app_config_path = str(_GEM_PATHS['app_config'])
        if os.path.exists(app_config_path):
            try:
                with open(app_config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                mentores = cfg.get("canales_mentores", [])
                if mentores:
                    ch = {}
                    for m in mentores:
                        if not m.get("activo", True):
                            continue
                        url = self._normalize_youtube_url(m.get("url", ""))
                        if self._valid_youtube_url(url):
                            ch[m["nombre"]] = url
                    if ch:
                        self.log_callback(
                            f"📡 [CHANNELS] {len(ch)} mentores desde config.json")
                        return ch
            except Exception:
                pass

        # 3. Fallback final: defaults hardcodeados
        self.log_callback("⚠️ [CHANNELS] Usando defaults hardcodeados (5 mentores)")
        return {
            "Adrián Sáenz": "https://www.youtube.com/@adriansaenz",
            "Iván Caicedo": "https://www.youtube.com/@ivancaicedo",
            "JaviEcom": "https://www.youtube.com/@javiecom",
            "Marc Verdú": "https://www.youtube.com/@marcverdu",
            "Vic Ecomilions": "https://www.youtube.com/@vicecomilions",
        }


    def _sync_channels_to_queue(self) -> None:
        """Sincroniza canales cargados con QueueStateManager."""
        for nombre, url in self.favorite_channels.items():
            self.queue_manager.ensure_channel(nombre, url)

    @with_retry(max_retries=3, base_delay=2.0)
    def get_all_channel_videos(
        self, channel_url: str, max_scan: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Extrae los videos más recientes de un canal usando yt-dlp real.
        Con User-Agent rotado y cookies opcionales.

        max_scan limita la enumeración a los N videos más nuevos; con None
        se recorre el canal entero (primera ingesta de un canal).
        """
        if max_scan:
            self.log_callback(
                f"📡 Escaneando últimos {max_scan} videos: {channel_url}")
        else:
            self.log_callback(f"📡 Escaneando HISTORIAL COMPLETO: {channel_url}")

        cmd = [
            "yt-dlp", "--dump-json", "--flat-playlist", "--no-warnings",
            "--user-agent", self.user_agent_rotator.current_user_agent,
            "--add-header", "Accept-Language:es-ES,es;q=0.9,en;q=0.5",
        ]
        if max_scan:
            cmd.extend(["--playlist-end", str(max_scan)])
        if self.user_agent_rotator.has_cookies:
            cmd.extend(["--cookies", self.user_agent_rotator.cookies_path])

        self.user_agent_rotator.rotate()
        cmd.append(channel_url)

        videos: List[Dict[str, str]] = []
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                check=True, encoding="utf-8", timeout=120)
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    vid = data.get("id", "")
                    if vid:
                        videos.append({
                            "video_id": vid,
                            "title": data.get("title", ""),
                            "url": f"https://youtube.com/watch?v={vid}",
                        })
                except json.JSONDecodeError:
                    continue
            # --playlist-end aplica por pestaña (videos, shorts, lives),
            # así que el total puede superar el límite pedido.
            if max_scan and len(videos) > max_scan:
                videos = videos[:max_scan]
            self.log_callback(f"📊 {len(videos)} videos encontrados")
        except subprocess.TimeoutExpired:
            self.log_callback(f"⚠️ Timeout escaneando {channel_url}")
        except subprocess.CalledProcessError as e:
            self.log_callback(f"⚠️ yt-dlp error: {e.stderr[:200]}")
        except Exception as e:
            self.log_callback(f"⚠️ Error escaneando {channel_url}: {e}")
        return videos

    @staticmethod
    def _parse_vtt(raw: str) -> str:
        """
        Extrae el texto de un VTT de YouTube.

        Los subtítulos automáticos van en ventana deslizante: cada cue repite
        las líneas de la anterior, así que sin deduplicar el texto se triplica
        y se dispara el coste de tokens de la llamada a la IA.
        """
        salida: List[str] = []
        for linea in raw.split("\n"):
            linea = linea.strip()
            if (not linea or "-->" in linea or linea.isdigit()
                    or linea.startswith(("WEBVTT", "Kind:", "Language:"))):
                continue
            # Quita tags de karaoke: <00:00:01.234> y <c>...</c>
            linea = re.sub(r"<[^>]+>", "", linea).strip()
            if linea and (not salida or salida[-1] != linea):
                salida.append(linea)
        return " ".join(salida)

    @with_retry(max_retries=3, base_delay=1.0)
    def download_transcript(self, video_id: str) -> str:
        """
        Descarga subtítulos y limpia marcas de tiempo en caliente.
        Usa yt-dlp real con User-Agent rotado y cookies opcionales.
        Directorio temporal gestionado por PathManager.
        """
        video_url = f"https://youtube.com/watch?v={video_id}"
        output_tmpl = os.path.join(TEMP_TRANSCRIPT_DIR, video_id)

        # Sin --convert-subs: esa conversión exige ffmpeg y aquí basta el VTT
        # nativo de YouTube, que _parse_vtt() limpia sin dependencias externas.
        cmd = [
            "yt-dlp", "--skip-download", "--write-subs",
            "--write-auto-subs", "--sub-lang", "es,es-419",
            "--no-warnings",
            "--user-agent", self.user_agent_rotator.current_user_agent,
            "-o", output_tmpl,
        ]
        if self.user_agent_rotator.has_cookies:
            cmd.extend(["--cookies", self.user_agent_rotator.cookies_path])

        self.user_agent_rotator.rotate()
        cmd.append(video_url)

        try:
            subprocess.run(cmd, capture_output=True, text=True,
                           check=True, timeout=60)
            # Buscar archivo SRT
            for fname in os.listdir(TEMP_TRANSCRIPT_DIR):
                if fname.startswith(video_id) and fname.endswith(".srt"):
                    srt_path = os.path.join(TEMP_TRANSCRIPT_DIR, fname)
                    try:
                        with open(srt_path, "r", encoding="utf-8") as f:
                            raw_lines = f.readlines()
                        clean = [l.strip() for l in raw_lines
                                 if not l.strip().isdigit()
                                 and "-->" not in l and l.strip()]
                        return " ".join(clean)
                    finally:
                        try:
                            os.remove(srt_path)
                        except OSError:
                            pass
            # Buscar VTT si no hay SRT
            for fname in os.listdir(TEMP_TRANSCRIPT_DIR):
                if fname.startswith(video_id):
                    vtt_path = os.path.join(TEMP_TRANSCRIPT_DIR, fname)
                    try:
                        with open(vtt_path, "r", encoding="utf-8") as f:
                            return self._parse_vtt(f.read())
                    finally:
                        try:
                            os.remove(vtt_path)
                        except OSError:
                            pass
        except subprocess.TimeoutExpired:
            self.log_callback(f"⏰ Timeout subtítulos {video_id}")
        except subprocess.CalledProcessError as e:
            self.log_callback(f"❌ yt-dlp error {video_id}: {e.stderr[:200]}")
        except Exception as e:
            self.log_callback(f"❌ Error descarga {video_id}: {e}")
        return ""

    def _process_single_video(
        self, video: Dict[str, str], creator: str
    ) -> bool:
        """
        Procesa un video individual: descarga, limpia, inserta en KB.
        Retorna True si se procesó exitosamente o no tenía valor CRO.
        """
        video_id = video["video_id"]
        title = video.get("title", "")

        # 1. Marcar como Procesando
        self.queue_manager.update_video_status(
            creator, video_id, STATUS_PROCESSING, title=title)

        try:
            # 2. Descargar transcripción real
            raw_transcript = self.download_transcript(video_id)
            if not raw_transcript:
                self.queue_manager.update_video_status(
                    creator, video_id, STATUS_FAILED,
                    error_msg="Transcripción vacía o no disponible")
                return False

            # 3. Pre-limpieza con TranscriptCleaner (quita timestamps, muletillas, fluff)
            #    clean_for_ia() retorna "VACÍO" si el texto no tiene valor CRO,
            #    ahorrando así la llamada a la IA (gratis).
            pre_cleaned = self.transcript_cleaner.clean_for_ia(raw_transcript)
            if pre_cleaned == "VACÍO":
                self.log_callback(f"⏩ [VACÍO] {title} — sin valor CRO, saltando IA")
                self.queue_manager.update_video_status(
                    creator, video_id, STATUS_COMPLETED,
                    title=title, error_msg="clean_for_ia: VACÍO")
                return True

            # 4. Hash MD5 sobre texto pre-limpiado
            content_hash = hashlib.md5(
                pre_cleaned.encode("utf-8")).hexdigest()

            # 4. Verificar idempotencia en BD
            if self.validator.check_video_exists(video_id):
                self.log_callback(f"⏩ [DEDUP] {title} — ya en KB")
                self.queue_manager.update_video_status(
                    creator, video_id, STATUS_COMPLETED, title=title)
                return True

            # 5. Limpiar con IA (FreeLLMAPI → OpenRouter → Ollama)
            self.log_callback(f"🤖 Extrayendo valor técnico: {title}")
            # Enviamos texto pre-limpiado en vez de raw (menos tokens, más barato)
            clean_markdown = self.cleaner.clean_transcript(pre_cleaned)

            if clean_markdown:
                self.router.route_and_insert(
                    video_id, title, creator, content_hash, clean_markdown)
                self.log_callback(f"✅ Guardado en KB: {title}")
                self.queue_manager.update_video_status(
                    creator, video_id, STATUS_COMPLETED, title=title)
                # Sincronizar índice y exportar .md para este video
                try:
                    from app.services.kb_index_sync import KBIndexSync
                    syncer = KBIndexSync(db_path=self.db_manager.db_path)
                    syncer.sync()
                    syncer.export_md_for_video(video_id)
                except Exception as _sync_err:
                    self.log_callback(f"⚠️ KBIndexSync: {_sync_err}")
                return True
            else:
                self.log_callback(f"⚠️ IA: VACÍO (sin valor CRO): {title}")
                self.queue_manager.update_video_status(
                    creator, video_id, STATUS_COMPLETED,
                    title=title, error_msg="IA returned VACÍO")
                return True

        except Exception as e:
            self.log_callback(f"❌ Error procesando {title}: {e}")
            self.queue_manager.update_video_status(
                creator, video_id, STATUS_FAILED,
                title=title, error_msg=str(e))
            return False

    def run_deep_knowledge_ingestion(self):
        """
        Orquestador masivo de ingesta de conocimiento.
        Consume canales completos respetando throttling y persistencia.
        """
        self.log_callback("🧠 INICIANDO CONSOLIDACIÓN MAESTRA DE LA KB")
        total_processed = 0
        total_failed = 0

        for creator, url in self.favorite_channels.items():
            self.log_callback(f"\n⚡ Procesando canal: {creator}")

            # Marcar inicio de escaneo
            self.queue_manager.mark_channel_scan_started(creator)

            # Obtener videos (con retry/UA rotation), solo los más recientes
            max_scan = self.scan_limits.get(creator, DEFAULT_SCAN_LIMIT)
            all_videos = self.get_all_channel_videos(url, max_scan=max_scan)
            if not all_videos:
                self.log_callback(f"📭 Sin videos para {creator}")
                continue

            nuevos = [v for v in all_videos
                      if not self.validator.check_video_exists(v["video_id"])]
            self.log_callback(
                f"📊 {len(all_videos)} revisados · {len(nuevos)} nuevos "
                f"· {len(all_videos) - len(nuevos)} ya en KB")
            if not nuevos:
                self.log_callback(f"✅ {creator} al día, nada que ingerir")
                continue

            channel_processed = 0
            for video in nuevos:

                # 2. Throttling: 10 videos/hora máximo
                if not self.throttle.can_proceed():
                    self.log_callback(
                        "⏳ Límite 10v/h alcanzado. Esperando ventana...")
                    if not self.throttle.wait_until_available(timeout=3600):
                        self.log_callback("🛑 Límite de hora excedido.")
                        break

                # 3. Cooldown anti-ban aleatorio
                cooldown = random.uniform(6.0, 15.0)
                self.log_callback(f"⏳ Cooldown {cooldown:.1f}s...")
                time.sleep(cooldown)

                # 4. Registrar hit en throttle
                self.throttle.register_hit()

                # 5. Procesar video
                success = self._process_single_video(video, creator)
                if success:
                    channel_processed += 1
                    total_processed += 1
                else:
                    total_failed += 1

                self.progress_callback(channel_processed)

            self.log_callback(
                f"✅ Canal {creator}: {channel_processed} nuevos procesados")

        self.log_callback(f"\n{'='*50}")
        self.log_callback(f"📊 INGESTA: {total_processed} OK, {total_failed} FAIL")
        self.log_callback(f"{'='*50}")

    def run_global_ingestion(self):
        """
        Alias público llamado por main.py trigger_pipeline_ingestion().
        NO rompe la UI de Tkinter existente.
        """
        self.run_deep_knowledge_ingestion()

    def get_engine_status(self) -> Dict[str, Any]:
        """Estado completo del motor para dashboard/monitoring."""
        return {
            "channels_count": len(self.favorite_channels),
            "channels": list(self.favorite_channels.keys()),
            "queue_state": self.queue_manager.get_all_states(),
            "throttle": {
                "max_per_hour": self.throttle.max_per_hour,
                "remaining": self.throttle.remaining,
                "hits_in_window": self.throttle.hits_in_window,
            },
            "user_agent": {
                "current": self.user_agent_rotator.current_user_agent,
                "has_cookies": self.user_agent_rotator.has_cookies,
            },
            "temp_dir": TEMP_TRANSCRIPT_DIR,
            "data_dir": DATA_DIR,
        }
