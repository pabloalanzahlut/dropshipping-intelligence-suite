"""Regresiones de la herramienta de transcripciones (escritorio + web).

Sin red: la descarga real de YouTube se prueba a mano. Cada test usa su propia
base de datos temporal; nunca toca data/dropshipping_suite.db.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import DatabaseConnection
from app.services import transcript_store
from app.services.kb_cache_validator import KBCacheValidator
from app.services.transcript_cleaner import TranscriptCleaner
from app.services.youtube_rss_fetcher import _parse_vtt, _pick_vtt

TEXTO = (
    "Hoy hablamos de validar productos. No debes comprar sin validar el precio de origen. "
    "Eh, el margen mínimo es dos veces el coste landed. Suscríbete y dale like. "
) * 2


class CleanerTests(unittest.TestCase):
    def setUp(self):
        self.c = TranscriptCleaner()

    def test_no_invierte_el_significado(self):
        out = self.c.clean("No debes comprar este producto. Esto no funciona si no hay margen.")["text_limpio"]
        self.assertIn("No debes comprar este producto", out)
        self.assertIn("no funciona", out)
        self.assertIn("no hay margen", out)

    def test_quita_disfluencias_y_relleno_del_canal(self):
        out = self.c.clean("Eh, umm el margen es 30.5 euros. Suscríbete y dale like. Sigue.")["text_limpio"]
        self.assertNotIn("Eh", out)
        self.assertNotIn("umm", out)
        self.assertNotIn("like", out.lower())
        self.assertIn("30.5", out)          # no rompe cifras decimales
        self.assertNotIn("..", out.replace("...", ""))

    def test_conserva_ejemplos_de_copy_de_los_mentores(self):
        out = self.c.clean("La oferta limitada funciona porque crea urgencia.")["text_limpio"]
        self.assertIn("oferta limitada", out)

    def test_quita_etiquetas_de_sonido(self):
        self.assertNotIn("Música", self.c.clean("Hola [Música] mundo de las ventas online")["text_limpio"])

    def test_respeta_numeros_repetidos(self):
        self.assertIn("10 10", self.c.clean("Son 10 10 unidades en el pedido de prueba.")["text_limpio"])


class VttTests(unittest.TestCase):
    def test_parse_vtt_quita_tiempos_y_duplicados(self):
        vtt = ("WEBVTT\nKind: captions\nLanguage: es\n\n"
               "00:00:00.000 --> 00:00:02.000\nhola &gt;&gt; amigos\n\n"
               "00:00:02.000 --> 00:00:04.000\nhola &gt;&gt; amigos\nsegunda <c>línea</c>\n")
        self.assertEqual(_parse_vtt(vtt), ">> hola amigos".replace(">> hola", "hola >>") + " segunda línea")

    def test_pick_vtt_prefiere_el_idioma_exacto(self):
        files = [Path("v.es-orig.vtt"), Path("v.es.vtt"), Path("v.en.vtt")]
        self.assertEqual(_pick_vtt(files, "es").name, "v.es.vtt")


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = os.path.join(self.tmp.name, "t.db")
        DatabaseConnection(self.db)
        self.cleaner = TranscriptCleaner()

    def tearDown(self):
        self.tmp.cleanup()

    def test_parse_video_id(self):
        for u in ("https://www.youtube.com/watch?v=WHoS1nknHUM&t=5s", "https://youtu.be/WHoS1nknHUM",
                  "https://www.youtube.com/shorts/WHoS1nknHUM", "WHoS1nknHUM"):
            self.assertEqual(transcript_store.parse_video_id(u), "WHoS1nknHUM")
        self.assertIsNone(transcript_store.parse_video_id("https://example.com/x"))

    def test_guarda_texto_original_completo_sin_recortar(self):
        largo = "palabra útil sobre validación de productos. " * 400   # ~17 000 caracteres
        r = transcript_store.save_transcript(self.db, "abcdefghijk", "T", "C", largo, self.cleaner)
        t = transcript_store.get_transcript(self.db, r["id"])
        self.assertEqual(len(t["transcripcion_texto"]), len(largo.strip()))

    def test_es_idempotente_por_video_y_por_hash(self):
        a = transcript_store.save_transcript(self.db, "abcdefghijk", "T", "C", TEXTO, self.cleaner)
        b = transcript_store.save_transcript(self.db, "abcdefghijk", "T", "C", TEXTO, self.cleaner)
        self.assertFalse(a["duplicado"])
        self.assertTrue(b["duplicado"])
        self.assertEqual(transcript_store.stats(self.db)["total"], 1)

    def test_rechaza_texto_corto(self):
        with self.assertRaises(ValueError):
            transcript_store.ingest_text(self.db, "T", "C", "corto", self.cleaner)

    def test_busqueda_escapa_comodines_y_encuentra_el_original(self):
        transcript_store.save_transcript(self.db, "abcdefghijk", "T", "C", TEXTO + " margen del 70% fijo", self.cleaner)
        self.assertEqual(transcript_store.list_transcripts(self.db, buscar="70%")["total"], 1)
        self.assertEqual(transcript_store.list_transcripts(self.db, buscar="9%9")["total"], 0)   # % no es comodín
        self.assertEqual(transcript_store.list_transcripts(self.db, buscar="a_c")["total"], 0)   # _ no es comodín

    def test_limite_acotado(self):
        res = transcript_store.list_transcripts(self.db, limite=10**6)
        self.assertEqual(res["total"], 0)

    def test_guardar_transcripcion_no_cuenta_como_ya_en_kb(self):
        transcript_store.save_transcript(self.db, "abcdefghijk", "T", "C", TEXTO, self.cleaner)
        self.assertFalse(KBCacheValidator(db_path=self.db).check_video_exists("abcdefghijk"))

    def test_borrar_no_deja_fuentes_huerfanas(self):
        r = transcript_store.save_transcript(self.db, "abcdefghijk", "T", "C", TEXTO, self.cleaner)
        self.assertTrue(transcript_store.delete_transcript(self.db, r["id"]))
        self.assertFalse(transcript_store.delete_transcript(self.db, r["id"]))
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(self.db)) as conn:
            n = conn.execute("SELECT COUNT(*) FROM video_sources").fetchone()[0]
        self.assertEqual(n, 0)

    def test_exportar_markdown(self):
        r = transcript_store.save_transcript(self.db, "abcdefghijk", "Mi título", "Canal", TEXTO, self.cleaner)
        md = transcript_store.to_markdown(transcript_store.get_transcript(self.db, r["id"]))
        self.assertTrue(md.startswith("# Mi título"))
        self.assertIn("watch?v=abcdefghijk", md)


class ApiTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        import app.services.dashboard_server as ds
        self.ds = ds
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = os.path.join(self.tmp.name, "t.db")
        DatabaseConnection(self.db)
        self._old = ds.DB_PATH
        ds.DB_PATH = self.db
        self.c = TestClient(ds.app)

    def tearDown(self):
        self.ds.DB_PATH = self._old
        self.tmp.cleanup()

    def test_ciclo_completo(self):
        r = self.c.post("/api/transcripciones/ingestar", json={"titulo": "Prueba", "canal": "X", "texto": TEXTO})
        self.assertEqual(r.status_code, 201)
        tid = r.json()["id"]
        self.assertEqual(self.c.post("/api/transcripciones/ingestar",
                                     json={"titulo": "Prueba", "canal": "X", "texto": TEXTO}).status_code, 200)
        lst = self.c.get("/api/transcripciones")
        self.assertEqual(lst.headers["x-total-count"], "1")
        self.assertEqual(self.c.get(f"/api/transcripciones/{tid}/exportar?version=original").status_code, 200)
        self.assertEqual(self.c.delete(f"/api/transcripciones/{tid}").status_code, 200)
        self.assertEqual(self.c.get(f"/api/transcripciones/{tid}").status_code, 404)

    def test_validaciones(self):
        self.assertEqual(self.c.get("/api/transcripciones?limite=0").status_code, 422)
        self.assertEqual(self.c.get("/api/transcripciones?limite=-1").status_code, 422)
        self.assertEqual(self.c.get("/api/transcripciones?limite=99999").status_code, 422)
        self.assertEqual(self.c.post("/api/transcripciones/ingestar", json={}).status_code, 422)
        self.assertEqual(self.c.post("/api/transcripciones/ingestar", json={"url": "https://example.com"}).status_code, 422)
        self.assertEqual(self.c.get("/api/transcripciones/exportar").status_code, 422)

    def test_guardas_de_concurrencia(self):
        with self.ds._TRANS_SYNC_LOCK:
            self.ds._TRANS_SYNC["running"] = True
        try:
            self.assertEqual(self.c.post("/api/transcripciones/sincronizar").status_code, 409)
        finally:
            with self.ds._TRANS_SYNC_LOCK:
                self.ds._TRANS_SYNC["running"] = False
        self.ds._INGEST_LOCK.acquire()
        try:
            self.assertIn(self.c.post("/api/process").status_code, (409, 503))
        finally:
            self.ds._INGEST_LOCK.release()


class TopicFilterTests(unittest.TestCase):
    def test_titulo_con_tema_se_acepta(self):
        from app.services import topic_filter
        self.assertTrue(topic_filter.evaluar("Trata el dropshipping como un videojuego", "texto sin nada")[0])

    def test_video_de_otro_tema_se_rechaza(self):
        from app.services import topic_filter
        texto = "hablamos de inteligencia artificial y de mentalidad " * 400 + " shopify "
        self.assertFalse(topic_filter.evaluar("Cómo reprogramar tu mente", texto)[0])

    def test_video_que_trata_el_tema_en_el_texto_se_acepta(self):
        from app.services import topic_filter
        texto = ("primero montas tu tienda en Shopify y luego pruebas el dropshipping con ecommerce " * 10
                 + "relleno " * 300)
        self.assertTrue(topic_filter.evaluar("Seis formas de ganar dinero", texto)[0])

    def test_ignora_tildes_y_mayusculas(self):
        from app.services import topic_filter
        self.assertEqual(topic_filter.contar_menciones("Tienda ONLINE, E-Commerce y comercio electrónico"), 3)


class RateLimitTests(unittest.TestCase):
    def test_429_lanza_ratelimited_solo_si_se_pide(self):
        import subprocess
        from unittest.mock import patch
        from app.services import youtube_rss_fetcher as f
        fake = subprocess.CompletedProcess([], 1, stdout=b"", stderr=b"ERROR: HTTP Error 429: Too Many Requests")
        with patch.object(f.subprocess, "run", return_value=fake):
            with self.assertRaises(f.RateLimited):
                f._run_ytdlp(["x"], raise_on_rate_limit=True)
            self.assertIsNone(f._run_ytdlp(["x"]))


class MonitorTests(unittest.TestCase):
    """Sincronización con descargas simuladas: filtro de tema, descartados y 429."""

    def setUp(self):
        import json
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = os.path.join(self.tmp.name, "t.db")
        self.dbm = DatabaseConnection(self.db)
        self.cfg = os.path.join(self.tmp.name, "youtube_channels.json")
        json.dump([
            {"url": "https://www.youtube.com/@primario", "nombre": "Primario", "activo": True,
             "idioma": "es", "prioridad": 1, "filtro_tema": True},
            {"url": "https://www.youtube.com/@dropshipper", "nombre": "Solo Dropshipping", "activo": True,
             "idioma": "es", "prioridad": 2},
        ], open(self.cfg, "w", encoding="utf-8"))
        import app.services.youtube_channel_monitor as mod
        self.mod = mod
        self._pausa, self._esperas = mod.PAUSA_ENTRE_DESCARGAS, mod.ESPERAS_429
        mod.PAUSA_ENTRE_DESCARGAS, mod.ESPERAS_429 = (0.0, 0.0), (0, 0)
        self.m = mod.YouTubeChannelMonitor(db_manager=self.dbm, config_path=self.cfg)

    def tearDown(self):
        self.mod.PAUSA_ENTRE_DESCARGAS, self.mod.ESPERAS_429 = self._pausa, self._esperas
        self.tmp.cleanup()

    def _videos(self, url, max_videos=15):
        if "primario" in url:
            return [{"video_id": "aaaaaaaaaaa", "title": "Numerología y dinero", "channel": "Primario"},
                    {"video_id": "bbbbbbbbbbb", "title": "Mi tienda Shopify paso a paso", "channel": "Primario"}]
        return [{"video_id": "ccccccccccc", "title": "Habla de IA", "channel": "Solo Dropshipping"}]

    def _texto(self, video_id, lang="es"):
        return (f"contenido {video_id} sobre ventas y anuncios de producto con margen y precio. " * 8)

    def test_filtra_solo_el_canal_marcado_y_no_repite_descartados(self):
        from unittest.mock import patch
        with patch.object(self.mod, "fetch_channel_videos", self._videos),              patch.object(self.mod, "download_transcript", self._texto):
            r1 = self.m.sincronizar_canales()
            self.assertEqual(r1["fuera_de_tema"], 1)            # "Numerología" descartado
            self.assertEqual(r1["transcripciones_procesadas"], 2)  # Shopify + canal sin filtro
            guardados = transcript_store.video_ids_guardados(self.db)
            self.assertEqual(guardados, {"bbbbbbbbbbb", "ccccccccccc"})
            llamadas = []
            with patch.object(self.mod, "download_transcript", lambda v, lang="es": llamadas.append(v)):
                self.m.sincronizar_canales()
            self.assertEqual(llamadas, [])                      # nada que volver a bajar

    def test_ante_429_reintenta_y_luego_se_detiene_sin_perder_lo_guardado(self):
        from unittest.mock import patch
        from app.services.youtube_rss_fetcher import RateLimited
        intentos = []

        def siempre_429(video_id, lang="es"):
            intentos.append(video_id)
            raise RateLimited("429")

        with patch.object(self.mod, "fetch_channel_videos", self._videos),              patch.object(self.mod, "download_transcript", siempre_429):
            r = self.m.sincronizar_canales()
        self.assertTrue(r["limitado"])
        self.assertEqual(len(intentos), 3)                      # 1 intento + 2 reintentos
        self.assertEqual(transcript_store.stats(self.db)["total"], 0)

    def test_429_pasajero_se_recupera(self):
        from unittest.mock import patch
        from app.services.youtube_rss_fetcher import RateLimited
        estado = {"n": 0}

        def una_vez_429(video_id, lang="es"):
            estado["n"] += 1
            if estado["n"] == 1:
                raise RateLimited("429")
            return self._texto(video_id)

        with patch.object(self.mod, "fetch_channel_videos", self._videos),              patch.object(self.mod, "download_transcript", una_vez_429):
            r = self.m.sincronizar_canales()
        self.assertFalse(r["limitado"])
        self.assertGreaterEqual(r["transcripciones_procesadas"], 2)


class EscritorioTests(unittest.TestCase):
    def test_rgba_se_convierte_a_hex_valido_para_tk(self):
        from app.ui.components.financial_validator_panel_v2 import _rgba_to_hex
        self.assertRegex(_rgba_to_hex("rgba(0, 245, 255, 0.1)", "#13131a"), r"^#[0-9a-f]{6}$")
        self.assertEqual(_rgba_to_hex("#abcdef"), "#abcdef")

    def test_main_usa_root_after_y_no_depende_de_colors(self):
        src = (Path(__file__).resolve().parent.parent / "app" / "main.py").read_text(encoding="utf-8")
        self.assertNotIn("self.after(", src)
        self.assertNotRegex(src, r"(?<![A-Z_])COLORS\.")


if __name__ == "__main__":
    unittest.main()
