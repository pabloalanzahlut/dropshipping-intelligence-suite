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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import DatabaseConnection
from app.services import alerts, daily_brief
from app.services import business_metrics as bm
from app.services import product_catalog as pc
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


if __name__ == "__main__":
    unittest.main()
