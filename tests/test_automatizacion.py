"""Automatización: centro de alertas, resumen diario y reutilización de transcripciones guardadas.
Sin red, sin IA y con BD temporal (nunca toca data/dropshipping_suite.db)."""
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import DatabaseConnection
from app.services import alerts, daily_brief
from app.services import business_metrics as bm
from app.services import product_catalog as pc
from app.services import product_trends_promoter, propuestas_review
from app.services.provider_monitor_engine import ProviderMonitorEngine
from app.services.queue_state_manager import STATUS_COMPLETED, STATUS_FAILED


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        raiz = Path(self.tmp.name)
        (raiz / "data").mkdir()
        self.db = str(raiz / "data" / "t.db")
        self.cfg = str(raiz / "data" / "youtube_channels.json")
        Path(self.cfg).write_text("[]", encoding="utf-8")
        DatabaseConnection(self.db)
        os.environ.setdefault("OPENROUTER_API_KEY", "")

    def tearDown(self):
        self.tmp.cleanup()

    def claves(self, **kw):
        return {a["clave"]: a for a in alerts.listar(self.db, **kw)["items"]}

    def registrar_negocio(self, ingresos, gasto, saldo, cogs=0, pedidos=3):
        bm.registrar_dia(self.db, {"fecha": date.today().isoformat(), "gasto_ads": gasto,
                                   "ingresos": ingresos, "pedidos": pedidos, "cogs_pagado": cogs})
        bm.registrar_caja(self.db, {"fecha": date.today().isoformat(), "saldo_cuenta": saldo})


class AlertasTests(Base):
    def test_sin_datos_no_inventa_alertas_de_negocio(self):
        alerts.evaluar(self.db, self.cfg)
        claves = self.claves()
        self.assertNotIn("caja_critica", claves)
        self.assertNotIn("roas_sangrado", claves)
        self.assertIn("sin_productos", claves)              # el único aviso honesto: catálogo vacío

    def test_caja_critica_y_roas_sangrando(self):
        self.registrar_negocio(ingresos=40, gasto=100, saldo=150, cogs=20)   # 150 / 120 al día = 1,25 días
        alerts.evaluar(self.db, self.cfg)
        claves = self.claves()
        self.assertEqual(claves["caja_critica"]["nivel"], "critico")
        self.assertEqual(claves["roas_sangrado"]["nivel"], "critico")
        self.assertEqual(alerts.listar(self.db)["criticas"], 2)

    def test_roas_bajo_pero_no_sangrado_es_aviso(self):
        self.registrar_negocio(ingresos=150, gasto=100, saldo=5000)          # ROAS 1,5
        alerts.evaluar(self.db, self.cfg)
        self.assertEqual(self.claves()["roas_bajo"]["nivel"], "aviso")
        self.assertNotIn("roas_sangrado", self.claves())

    def test_no_duplica_y_se_resuelve_sola(self):
        self.registrar_negocio(ingresos=40, gasto=100, saldo=150)
        alerts.evaluar(self.db, self.cfg)
        r = alerts.evaluar(self.db, self.cfg)
        self.assertEqual(r["nuevas"], 0)                                      # misma clave: se actualiza
        total = alerts.listar(self.db, incluir_resueltas=True)["total_activas"]
        bm.registrar_caja(self.db, {"fecha": date.today().isoformat(), "saldo_cuenta": 90000})
        bm.registrar_dia(self.db, {"fecha": date.today().isoformat(), "gasto_ads": 100, "ingresos": 400, "pedidos": 8})
        alerts.evaluar(self.db, self.cfg)
        self.assertLess(alerts.listar(self.db)["total_activas"], total)
        self.assertNotIn("caja_critica", self.claves())                       # resuelta: ya no aparece
        self.assertIn("caja_critica", self.claves(incluir_resueltas=True))    # pero queda en el historial

    def test_vista_no_la_resuelve_y_reaparece_si_vuelve(self):
        self.registrar_negocio(ingresos=40, gasto=100, saldo=150)
        alerts.evaluar(self.db, self.cfg)
        self.assertGreater(alerts.listar(self.db)["sin_ver"], 0)
        alerts.marcar_vista(self.db)
        self.assertEqual(alerts.listar(self.db)["sin_ver"], 0)
        self.assertIn("caja_critica", self.claves())                          # vista ≠ resuelta
        bm.registrar_caja(self.db, {"fecha": date.today().isoformat(), "saldo_cuenta": 90000})
        alerts.evaluar(self.db, self.cfg)
        bm.registrar_caja(self.db, {"fecha": date.today().isoformat(), "saldo_cuenta": 100})
        alerts.evaluar(self.db, self.cfg)
        self.assertEqual(self.claves()["caja_critica"]["vista_at"], None)     # vuelve como «no vista»

    def test_producto_que_toca_cortar(self):
        p = pc.crear(self.db, {"nombre": "Pelota", "costo_origen": 5, "costo_envio": 2, "pvp": 15})
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE productos SET estado = 'tienda' WHERE id = ?", (p["id"],))
        for i in range(4):
            bm.registrar_dia(self.db, {"fecha": (date.today() - timedelta(days=3 - i)).isoformat(),
                                       "producto_id": p["id"], "gasto_ads": 30, "ingresos": 0, "pedidos": 0})
        alerts.evaluar(self.db, self.cfg)
        self.assertEqual(self.claves()[f"producto_cortar_{p['id']}"]["nivel"], "critico")

    def test_canal_no_encontrado_y_sin_verificar(self):
        Path(self.cfg).write_text(json.dumps([
            {"nombre": "Roto", "url": "https://www.youtube.com/@roto", "activo": True},
            {"nombre": "Nuevo", "url": "https://www.youtube.com/@nuevo", "activo": True}]), encoding="utf-8")
        with sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO canales_favoritos (handle, nombre, url, ultimo_estado) VALUES "
                         "('@roto', 'Roto', 'https://www.youtube.com/@roto', 'no_encontrado')")
        alerts.evaluar(self.db, self.cfg)
        claves = self.claves()
        self.assertTrue(any(k.startswith("canal_404_") for k in claves))
        self.assertIn("canales_sin_verificar", claves)

    def test_sincronizacion_limitada_y_antigua(self):
        ruta = Path(self.cfg).with_name("last_sync.json")
        ruta.write_text(json.dumps({"fecha_sincronizacion": "2020-01-01T10:00:00", "limitado": True}), encoding="utf-8")
        alerts.evaluar(self.db, self.cfg)
        claves = self.claves()
        self.assertIn("sync_antigua", claves)
        self.assertIn("sync_limitada", claves)
        self.assertNotIn("pronto", claves["sync_limitada"]["detalle"])

    def test_una_comprobacion_rota_no_tumba_las_demas(self):
        original = alerts._canales
        alerts._canales = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            vigentes = alerts.calcular(self.db, self.cfg)
        finally:
            alerts._canales = original
        self.assertTrue(any(a["clave"] == "sin_productos" for a in vigentes))
        self.assertTrue(any(a["titulo"] == "No se pudo hacer una comprobación" for a in vigentes))


class ResumenTests(Base):
    def test_sin_datos_lo_dice_en_vez_de_inventar(self):
        r = daily_brief.generar(self.db, self.cfg)
        texto = r["texto"]
        self.assertIn("no hay métricas registradas", texto)
        self.assertIn("Caja: sin registrar", texto)
        self.assertIn("catálogo está vacío", texto)
        self.assertNotIn("critico", {p["nivel"] for p in r["prioridades"]})     # nada urgente inventado
        self.assertTrue(any("primer producto" in p["texto"] for p in r["prioridades"]))

    def test_con_datos_calcula_ayer_y_prioriza_lo_critico(self):
        ayer = (date.today() - timedelta(days=1)).isoformat()
        bm.registrar_dia(self.db, {"fecha": ayer, "gasto_ads": 100, "ingresos": 250, "pedidos": 5})
        bm.registrar_caja(self.db, {"fecha": ayer, "saldo_cuenta": 50})
        r = daily_brief.generar(self.db, self.cfg)
        self.assertIn("ingresos 250,00", r["secciones"][0]["lineas"][0])
        self.assertIn("ROAS 2.50×", r["secciones"][0]["lineas"][0])
        self.assertEqual(r["prioridades"][0]["nivel"], "critico")             # caja crítica primero

    def test_se_guarda_y_se_recupera(self):
        self.assertIsNone(daily_brief.ultimo(self.db))
        daily_brief.generar(self.db, self.cfg)
        guardado = daily_brief.ultimo(self.db)
        self.assertEqual(guardado["fecha"], date.today().isoformat())
        self.assertEqual(len(daily_brief.historial(self.db)), 1)
        daily_brief.generar(self.db, self.cfg)                                # el mismo día se sustituye
        self.assertEqual(len(daily_brief.historial(self.db)), 1)

    def test_formato_eur(self):
        self.assertEqual(daily_brief._eur(1234.5), "1.234,50")
        self.assertEqual(daily_brief._eur(None), "—")


class _Cola:
    def __init__(self, estados):
        self.estados = estados

    def video_status(self, canal, video_id):
        return self.estados.get((canal, video_id))


class TranscripcionesGuardadasTests(Base):
    """El motor usa lo ya descargado en vez de volver a pedirlo a YouTube."""

    def motor(self, estados=None, resultado=True):
        m = ProviderMonitorEngine.__new__(ProviderMonitorEngine)
        m.db_manager = SimpleNamespace(db_path=self.db)
        m.queue_manager = _Cola(estados or {})
        m.log_callback = lambda msg: None
        m.llamadas = []

        def procesar(video, canal):
            m.llamadas.append(video["video_id"])
            return resultado
        m._process_single_video = procesar
        return m

    def guardar(self, vid, canal="Canal", texto="texto original"):
        with sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO transcripciones_youtube (video_id, titulo, canal, fecha, transcripcion_texto, hash_md5) "
                         "VALUES (?,?,?,?,?,?)", (vid, f"Título {vid}", canal, "2026-11-08", texto, vid))

    def test_devuelve_el_texto_guardado(self):
        self.guardar("abc", texto="hola mundo")
        m = self.motor()
        self.assertEqual(m._transcripcion_guardada("abc"), "hola mundo")
        self.assertEqual(m._transcripcion_guardada("no-existe"), "")

    def test_procesa_las_pendientes_y_salta_las_resueltas(self):
        for v in ("a", "b", "c"):
            self.guardar(v)
        with sqlite3.connect(self.db) as conn:   # «b» ya está en la KB
            conn.execute("INSERT INTO video_sources (video_id, platform, title, channel_name, content_hash) VALUES ('b', 'youtube', 'x', 'Canal', 'h-b')")
        m = self.motor({("Canal", "c"): STATUS_COMPLETED})   # «c» ya se resolvió (p. ej. fuera de tema)
        self.assertEqual(m._ingestar_transcripciones_guardadas(), 1)
        self.assertEqual(m.llamadas, ["a"])

    def test_una_fila_youtube_transcript_no_cuenta_como_analizada(self):
        self.guardar("a")
        with sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO video_sources (video_id, platform, title, channel_name, content_hash) VALUES ('a', 'youtube_transcript', 'x', 'Canal', 'h-a')")
        m = self.motor()
        m._ingestar_transcripciones_guardadas()
        self.assertEqual(m.llamadas, ["a"])

    def test_respeta_el_tope_por_ciclo(self):
        for i in range(8):
            self.guardar(f"v{i}")
        m = self.motor()
        self.assertEqual(m._ingestar_transcripciones_guardadas(maximo=3), 3)
        self.assertEqual(len(m.llamadas), 3)

    def test_se_detiene_tras_3_fallos_seguidos(self):
        for i in range(8):
            self.guardar(f"v{i}")
        m = self.motor(resultado=False)
        self.assertEqual(m._ingestar_transcripciones_guardadas(maximo=10), 0)
        self.assertEqual(len(m.llamadas), 3)                                   # circuit breaker

    def test_las_que_ya_fallaron_van_al_final(self):
        for v in ("rota", "buena1", "buena2"):
            self.guardar(v)
        m = self.motor({("Canal", "rota"): STATUS_FAILED})
        m._ingestar_transcripciones_guardadas(maximo=10)
        self.assertEqual(m.llamadas[-1], "rota")

    def test_ia_sin_respuesta_no_se_da_por_analizada(self):
        """Antes un fallo de red quedaba como «IA returned VACÍO» (completado para siempre)."""
        self.guardar("x", texto="contenido")
        m = ProviderMonitorEngine.__new__(ProviderMonitorEngine)
        estados = {}
        m.db_manager = SimpleNamespace(db_path=self.db)
        m.queue_manager = SimpleNamespace(
            update_video_status=lambda canal, vid, estado, title="", error_msg="": estados.update({vid: (estado, error_msg)}))
        m.log_callback = lambda msg: None
        m.channel_topic_filter, m.channel_roles = {}, {}
        m.transcript_cleaner = SimpleNamespace(clean_for_ia=lambda t: t)
        m.validator = SimpleNamespace(check_video_exists=lambda v: False)
        m.cleaner = SimpleNamespace(clean_transcript=lambda *a, **k: None, last_error="timeout")
        m.router = SimpleNamespace()
        self.assertFalse(m._process_single_video({"video_id": "x", "title": "T"}, "Canal"))
        self.assertEqual(estados["x"][0], STATUS_FAILED)
        m.cleaner.last_error = None                                            # ahora sí es «sin valor»
        self.assertTrue(m._process_single_video({"video_id": "x", "title": "T"}, "Canal"))
        self.assertEqual(estados["x"][0], STATUS_COMPLETED)


class MantenimientoTests(Base):
    """Integridad, optimización, temporales y verificación de canales (sin red)."""

    def setUp(self):
        super().setUp()
        from app.services import mantenimiento
        self.m = mantenimiento

    def test_integridad_ok_y_detecta_corrupcion(self):
        self.assertTrue(self.m.verificar_integridad(self.db)["ok"])
        roto = Path(self.tmp.name) / "data" / "roto.db"
        roto.write_bytes(b"esto no es una base de datos sqlite" * 200)
        with self.assertRaises(sqlite3.DatabaseError):          # el paso falla y ejecutar() lo registra
            self.m.verificar_integridad(str(roto))

    def test_optimizar_solo_hace_vacuum_con_mucho_espacio_muerto(self):
        r = self.m.optimizar_db(self.db)
        self.assertFalse(r["vacuum"])
        with sqlite3.connect(self.db) as conn:                   # crea y borra datos → páginas libres
            conn.execute("CREATE TABLE basura (x TEXT)")
            conn.executemany("INSERT INTO basura VALUES (?)", [("x" * 4000,)] * 600)
            conn.commit()
            conn.execute("DROP TABLE basura")
            conn.commit()
        self.assertTrue(self.m.optimizar_db(self.db)["vacuum"])

    def test_limpia_solo_temporales_antiguos(self):
        carpeta = Path(self.tmp.name) / "data" / "temp_transcripts"
        carpeta.mkdir()
        viejo, nuevo = carpeta / "viejo.vtt", carpeta / "nuevo.vtt"
        viejo.write_text("a")
        nuevo.write_text("b")
        antiguo = __import__("time").time() - 5 * 86400
        os.utime(viejo, (antiguo, antiguo))
        r = self.m.limpiar_temporales(str(Path(self.tmp.name) / "data"))
        self.assertEqual(r["borrados"], 1)
        self.assertFalse(viejo.exists())
        self.assertTrue(nuevo.exists())

    def test_verificar_canales_solo_pendientes_y_para_si_youtube_limita(self):
        Path(self.cfg).write_text(json.dumps([
            {"nombre": f"C{i}", "url": f"https://www.youtube.com/@c{i}", "activo": True} for i in range(4)]), encoding="utf-8")
        original = self.m.channel_store.verificar
        vistos = []

        def falso(db, url):
            vistos.append(url)
            return {"url": url, "estado": "indeterminado" if len(vistos) == 2 else "ok"}
        self.m.channel_store.verificar = falso
        try:
            r = self.m.verificar_canales(self.cfg, self.db, pausa=0)
        finally:
            self.m.channel_store.verificar = original
        self.assertEqual(len(vistos), 2)                         # se detiene al primer «indeterminado»
        self.assertEqual((r["ok"], r["indeterminado"], r["revisados"]), (1, 1, 2))

    def test_ejecutar_guarda_el_resultado_y_un_paso_roto_no_para_los_demas(self):
        original = self.m.optimizar_db
        self.m.optimizar_db = lambda *_: (_ for _ in ()).throw(RuntimeError("disco lleno"))
        try:
            r = self.m.ejecutar(self.db, self.cfg, canales=False)
        finally:
            self.m.optimizar_db = original
        self.assertTrue(r["integridad_ok"])
        self.assertIsNone(r["optimizacion"])
        self.assertTrue(any("optimizacion" in e for e in r["errores"]))
        self.assertEqual(self.m.ultimo(self.cfg)["fecha"], r["fecha"])

    def test_no_se_solapa_consigo_mismo(self):
        self.m._LOCK.acquire()
        try:
            self.assertIn("omitido", self.m.ejecutar(self.db, self.cfg, canales=False))
        finally:
            self.m._LOCK.release()

    def test_alertas_integridad_rota_y_mantenimiento_pendiente(self):
        alerts.evaluar(self.db, self.cfg)
        self.assertIn("mantenimiento_pendiente", self.claves())  # nunca se ha ejecutado
        self.m.ruta_estado(self.cfg).write_text(json.dumps(
            {"fecha": date.today().isoformat() + "T04:00:00", "integridad_ok": False,
             "integridad": {"ok": False, "detalle": "page 7 corrupta"}}), encoding="utf-8")
        alerts.evaluar(self.db, self.cfg)
        claves = self.claves()
        self.assertEqual(claves["bd_integridad"]["nivel"], "critico")
        self.assertNotIn("mantenimiento_pendiente", claves)
        self.assertIn("page 7", claves["bd_integridad"]["detalle"])

    def test_verificar_no_marca_no_encontrado_si_youtube_limita(self):
        from app.services import channel_store, youtube_rss_fetcher
        original = youtube_rss_fetcher.fetch_channel_videos
        youtube_rss_fetcher.fetch_channel_videos = lambda *a, **k: (_ for _ in ()).throw(youtube_rss_fetcher.RateLimited("429"))
        try:
            r = channel_store.verificar(self.db, "https://www.youtube.com/@x")
        finally:
            youtube_rss_fetcher.fetch_channel_videos = original
        self.assertEqual(r["estado"], "indeterminado")


if __name__ == "__main__":
    unittest.main()
