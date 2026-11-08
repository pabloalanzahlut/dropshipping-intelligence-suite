"""Contraseña de acceso, visor de registros y exportación CSV. Sin red; BD temporal."""
import logging
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import DatabaseConnection
from app.services import exports, log_viewer, web_auth


class TokenTests(unittest.TestCase):
    def test_token_valido_caducado_y_manipulado(self):
        with patch.dict(os.environ, {"GEM_OS_PASSWORD": "secreto"}):
            t = web_auth.crear_token()
            self.assertTrue(web_auth.token_valido(t))
            self.assertFalse(web_auth.token_valido(t, ahora=time.time() + 31 * 86400))   # caducado
            exp, firma = t.split(".")
            self.assertFalse(web_auth.token_valido(f"{int(exp) + 99999}.{firma}"))      # fecha manipulada
            self.assertFalse(web_auth.token_valido(exp + ".abc"))
            self.assertFalse(web_auth.token_valido(None))
        with patch.dict(os.environ, {"GEM_OS_PASSWORD": "otra"}):
            self.assertFalse(web_auth.token_valido(t))     # cambiar la contraseña invalida las sesiones

    def test_sin_contrasena_no_hay_sesion_valida(self):
        with patch.dict(os.environ, {"GEM_OS_PASSWORD": ""}):
            self.assertFalse(web_auth.activa())
            self.assertFalse(web_auth.password_correcta(""))

    def test_bloqueo_tras_5_fallos(self):
        ip = "9.9.9.9"
        web_auth.limpiar_fallos(ip)
        ahora = time.time()
        for _ in range(web_auth.MAX_FALLOS):
            web_auth.registrar_fallo(ip, ahora)
        self.assertGreater(web_auth.bloqueado(ip, ahora), 0)
        self.assertEqual(web_auth.bloqueado(ip, ahora + 61), 0)      # el bloqueo expira
        web_auth.limpiar_fallos(ip)

    def test_rutas_libres(self):
        for r in ("/login", "/api/login", "/static/x.css", "/webhooks/shopify"):
            self.assertTrue(web_auth.es_libre(r), r)
        for r in ("/", "/api/transcripciones", "/productos"):
            self.assertFalse(web_auth.es_libre(r), r)


class ServidorConContrasenaTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        import app.services.dashboard_server as ds
        self.ds = ds
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = os.path.join(self.tmp.name, "t.db")
        DatabaseConnection(self.db)
        self._old = ds.DB_PATH
        ds.DB_PATH = self.db
        self.env = patch.dict(os.environ, {"GEM_OS_PASSWORD": "secreto"})
        self.env.start()
        web_auth.limpiar_fallos("testclient")
        self.c = TestClient(ds.app, follow_redirects=False)

    def tearDown(self):
        self.env.stop()
        self.ds.DB_PATH = self._old
        self.tmp.cleanup()

    def test_sin_sesion_se_redirige_o_da_401(self):
        r = self.c.get("/productos", headers={"accept": "text/html"})
        self.assertEqual(r.status_code, 303)
        self.assertTrue(r.headers["location"].startswith("/login"))
        self.assertEqual(self.c.get("/api/transcripciones").status_code, 401)
        self.assertEqual(self.c.post("/api/transcripciones/ingestar", json={}).status_code, 401)

    def test_login_incorrecto_y_correcto(self):
        self.assertEqual(self.c.post("/api/login", json={"password": "mal"}).status_code, 401)
        ok = self.c.post("/api/login", json={"password": "secreto"})
        self.assertEqual(ok.status_code, 200)
        self.assertIn("httponly", ok.headers["set-cookie"].lower())
        self.assertEqual(self.c.get("/api/transcripciones").status_code, 200)      # ya con sesión
        self.assertEqual(self.c.get("/logout").status_code, 303)

    def test_login_se_bloquea_tras_muchos_fallos(self):
        for _ in range(web_auth.MAX_FALLOS):
            self.c.post("/api/login", json={"password": "mal"})
        self.assertEqual(self.c.post("/api/login", json={"password": "secreto"}).status_code, 429)

    def test_login_page_y_webhooks_no_piden_sesion(self):
        self.assertEqual(self.c.get("/login").status_code, 200)
        self.assertNotEqual(self.c.post("/webhooks/shopify/inexistente").status_code, 401)

    def test_sin_contrasena_todo_abierto(self):
        with patch.dict(os.environ, {"GEM_OS_PASSWORD": ""}):
            self.assertEqual(self.c.get("/api/transcripciones").status_code, 200)

    def test_registros_y_exportacion_requieren_sesion(self):
        self.assertEqual(self.c.get("/api/registros").status_code, 401)
        self.assertEqual(self.c.get("/api/exportar/copys.csv").status_code, 401)


class RegistrosTests(unittest.TestCase):
    def test_parseo_filtro_y_orden(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            ruta = Path(d) / "servidor.log"
            ruta.write_text(
                "2026-11-08 10:00:00 | INFO    | app | arranque correcto\n"
                "2026-11-08 10:01:00 | WARNING | app | YouTube limita las descargas\n"
                "línea sin formato\n"
                "2026-11-08 10:02:00 | ERROR   | app | fallo al sincronizar\n", encoding="utf-8")
            todos = log_viewer.consultar("servidor", ruta)
            self.assertEqual([e["nivel"] for e in todos], ["ERROR", "WARNING", "INFO"])   # lo nuevo primero
            self.assertEqual(len(log_viewer.consultar("servidor", ruta, nivel="WARNING")), 2)
            self.assertEqual(log_viewer.consultar("servidor", ruta, texto="youtube")[0]["nivel"], "WARNING")
            self.assertEqual(log_viewer.consultar("servidor", Path(d) / "no_existe.log"), [])

    def test_archivo_rotativo_idempotente(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            ruta = Path(d) / "x" / "servidor.log"
            antes = len(logging.getLogger().handlers)
            log_viewer.configurar_log_servidor(ruta)
            log_viewer.configurar_log_servidor(ruta)
            self.assertEqual(len(logging.getLogger().handlers), antes + 1)
            for h in list(logging.getLogger().handlers):      # no dejar el archivo abierto (Windows)
                if getattr(h, "baseFilename", "") == str(ruta.resolve()):
                    logging.getLogger().removeHandler(h)
                    h.close()


class CsvTests(unittest.TestCase):
    def test_neutraliza_formulas_y_usa_bom(self):
        data = exports.a_csv([{"k": "a", "t": "A"}], [{"a": "=HYPERLINK(1)"}, {"a": "+1"}, {"a": "normal"}, {"a": None}, {"a": True}])
        self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
        filas = data.decode("utf-8-sig").split("\r\n")
        self.assertEqual(filas[1:6], ["'=HYPERLINK(1)", "'+1", "normal", '""', "sí"])

    def test_dataset_con_busqueda(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            db = os.path.join(d, "t.db")
            DatabaseConnection(db)
            self.assertEqual(exports.consultar(db, "productos")["total"], 0)
            with self.assertRaises(KeyError):
                exports.consultar(db, "no_existe")


if __name__ == "__main__":
    unittest.main()
