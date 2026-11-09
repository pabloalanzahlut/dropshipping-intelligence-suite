"""El .exe portable: rutas en modo congelado, almacén de claves, sembrado de la carpeta del usuario e
importación de datos. Todo en carpetas temporales: no toca tu .env, tu AppData ni tu base de datos."""
import logging
import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import runtime_setup, secrets_store
from app.config.path_manager import PathManager

REPO = Path(__file__).resolve().parent.parent


class Congelado(unittest.TestCase):
    """Simula el .exe: sys.frozen, sys._MEIPASS (bundle de solo lectura) y %APPDATA% temporal."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        raiz = Path(self.tmp.name)
        self.bundle = raiz / "bundle"
        self.appdata = raiz / "appdata"
        self.bundle.mkdir()
        self.appdata.mkdir()
        self.parches = [
            mock.patch.object(sys, "frozen", True, create=True),
            mock.patch.object(sys, "_MEIPASS", str(self.bundle), create=True),
            mock.patch.object(sys, "executable", str(raiz / "app" / "GEM_OS_Suite.exe")),
            mock.patch.dict(os.environ, {"APPDATA": str(self.appdata)}),
        ]
        for p in self.parches:
            p.start()
        os.environ.pop("GEM_OS_DATA_DIR", None)
        self.user = self.appdata / "GEM_OS_Suite"
        self.cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self.cwd)
        for p in reversed(self.parches):
            p.stop()
        self.tmp.cleanup()


class RutasTests(Congelado):
    def test_todo_lo_que_se_escribe_va_a_la_carpeta_del_usuario(self):
        r = PathManager.get_paths()
        self.assertEqual(r["base"], self.bundle.resolve())
        self.assertEqual(r["data"], self.user / "data")
        self.assertEqual(r["db"], self.user / "data" / "dropshipping_suite.db")
        self.assertEqual(r["logs"], self.user / "logs" / "elite")
        self.assertEqual(r["backups"], self.user / "backups")
        self.assertEqual(r["ai_workspace"], self.user / "ai_workspace")
        self.assertEqual(r["context"], self.user / "ai_workspace" / "context")
        self.assertEqual(r["resources"], self.bundle.resolve() / "app" / "ui" / "resources")  # recursos: del bundle
        self.assertTrue(r["data"].is_dir() and r["logs"].is_dir())
        self.assertFalse(any(self.bundle.iterdir()))              # nada se crea dentro del bundle de solo lectura

    def test_gem_os_data_dir_sigue_mandando(self):
        otro = Path(self.tmp.name) / "mis_datos"
        with mock.patch.dict(os.environ, {"GEM_OS_DATA_DIR": str(otro)}):
            r = PathManager.get_paths()
        self.assertEqual(r["data"], otro)
        self.assertEqual(r["logs"], self.user / "logs" / "elite")

    def test_el_modo_desarrollo_no_cambia(self):
        for p in self.parches[:3]:
            p.stop()
        try:
            self.assertFalse(PathManager._is_executable())
            with mock.patch.dict(os.environ, {"GEM_OS_DATA_DIR": ""}):
                r = PathManager.get_paths()
            self.assertEqual(r["base"], REPO)
            self.assertEqual(r["db"], REPO / "data" / "dropshipping_suite.db")
            self.assertEqual(r["ai_workspace"], REPO / "ai_workspace")
        finally:
            for p in self.parches[:3]:
                p.start()


class AlmacenDeClavesTests(Congelado):
    def setUp(self):
        super().setUp()
        self.nombres = ["GEMTEST_A", "GEMTEST_B", "GEMTEST_C"]
        for n in self.nombres:
            os.environ.pop(n, None)

    def tearDown(self):
        for n in self.nombres:
            os.environ.pop(n, None)
        super().tearDown()

    def test_la_ruta_de_escritura_es_la_del_usuario_y_se_lee_tambien_junto_al_exe(self):
        self.assertEqual(secrets_store.ruta_env_escritura(), self.user / ".env")
        rutas = secrets_store.rutas_env()
        self.assertEqual(rutas[0], Path(sys.executable).resolve().parent / ".env")
        self.assertEqual(rutas[1], self.user / ".env")

    def test_guardar_crea_actualiza_y_conserva_el_resto(self):
        destino = secrets_store.ruta_env_escritura()
        destino.parent.mkdir(parents=True)
        destino.write_text("# mis claves\nOTRA=1\nGEMTEST_A=vieja\n", encoding="utf-8")
        secrets_store.guardar_valores({"GEMTEST_A": "nueva", "GEMTEST_B": "con espacios y # hash"})
        texto = destino.read_text(encoding="utf-8")
        self.assertIn("# mis claves", texto)
        self.assertIn("OTRA=1", texto)
        self.assertIn("GEMTEST_A=nueva", texto)
        self.assertNotIn("vieja", texto)
        self.assertIn('GEMTEST_B="con espacios y # hash"', texto)
        self.assertEqual(os.environ["GEMTEST_A"], "nueva")                       # aplicada sin reiniciar
        from dotenv import dotenv_values
        self.assertEqual(dotenv_values(destino)["GEMTEST_B"], "con espacios y # hash")   # ida y vuelta

    def test_valor_vacio_la_elimina(self):
        secrets_store.guardar_valores({"GEMTEST_A": "x"})
        secrets_store.guardar_valores({"GEMTEST_A": ""})
        self.assertNotIn("GEMTEST_A", secrets_store.ruta_env_escritura().read_text(encoding="utf-8"))
        self.assertNotIn("GEMTEST_A", os.environ)

    def test_rechaza_nombres_y_valores_peligrosos(self):
        for malo in ("minuscula", "CON ESPACIO", "A=B", "1ABC", ""):
            with self.assertRaises(ValueError, msg=malo):
                secrets_store.guardar_valores({malo: "x"})
        with self.assertRaises(ValueError):
            secrets_store.guardar_valores({"GEMTEST_A": "linea1\nGEMTEST_B=inyectada"})
        self.assertFalse(secrets_store.ruta_env_escritura().exists())

    def test_cargar_respeta_prioridad_y_no_pisa_el_entorno(self):
        a, b = Path(self.tmp.name) / "a.env", Path(self.tmp.name) / "b.env"
        a.write_text("GEMTEST_A=de_a\nGEMTEST_B=de_a\n", encoding="utf-8")
        b.write_text("GEMTEST_B=de_b\nGEMTEST_C=de_b\n", encoding="utf-8")
        os.environ["GEMTEST_A"] = "del_sistema"
        with mock.patch.object(secrets_store, "rutas_env", return_value=[a, b, Path(self.tmp.name) / "no_existe.env"]):
            leidos = secrets_store.cargar_entorno()
        self.assertEqual(leidos, [a, b])
        self.assertEqual(os.environ["GEMTEST_A"], "del_sistema")         # el sistema manda
        self.assertEqual(os.environ["GEMTEST_B"], "de_a")                # el primer .env manda
        self.assertEqual(os.environ["GEMTEST_C"], "de_b")

    def test_nunca_revela_ni_registra_el_valor(self):
        secreto = "sk-or-v1-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
        with self.assertLogs(level=logging.DEBUG) as logs:
            logging.getLogger("prueba").debug("inicio")
            secrets_store.guardar_valores({"GEMTEST_A": secreto})
            secrets_store.cargar_entorno()
        self.assertNotIn("SECRETO", " ".join(logs.output))
        self.assertEqual(secrets_store.estado_claves(["GEMTEST_A", "GEMTEST_B"]), {"GEMTEST_A": True, "GEMTEST_B": False})
        self.assertEqual(secrets_store.enmascarar(secreto), "…XXXX")
        self.assertEqual(secrets_store.enmascarar("corta"), "••••")
        self.assertEqual(secrets_store.enmascarar(""), "")


def _bundle_con_recursos(bundle: Path):
    (bundle / "ai_workspace" / "skills" / "buscar").mkdir(parents=True)
    (bundle / "ai_workspace" / "skills" / "buscar" / "procedimiento.md").write_text("pasos", encoding="utf-8")
    (bundle / "ai_workspace" / "config").mkdir()
    (bundle / "ai_workspace" / "config" / "google_credentials.json").write_text("{SECRETO}", encoding="utf-8")
    (bundle / "ai_workspace" / "config" / "openrouter_setup.md").write_text("doc", encoding="utf-8")
    (bundle / "ai_workspace" / "scripts").mkdir()
    (bundle / "ai_workspace" / "scripts" / "skool_cookies.json").write_text("{SECRETO}", encoding="utf-8")
    (bundle / "ai_workspace" / "web.zip").write_bytes(b"PK")
    (bundle / "agent.md").write_text("# agente", encoding="utf-8")
    (bundle / "data_template").mkdir()
    (bundle / "data_template" / "youtube_channels.json").write_text("[]", encoding="utf-8")


class SembradoTests(Congelado):
    def test_siembra_lo_necesario_y_nunca_los_secretos(self):
        _bundle_con_recursos(self.bundle)
        r = runtime_setup.sembrar_datos_iniciales()
        self.assertEqual((r["agent_md"], r["plantillas"]), (1, 1))
        self.assertEqual((self.user / "agent.md").read_text(encoding="utf-8"), "# agente")
        self.assertTrue((self.user / "ai_workspace" / "skills" / "buscar" / "procedimiento.md").is_file())
        self.assertTrue((self.user / "ai_workspace" / "config" / "openrouter_setup.md").is_file())
        self.assertTrue((self.user / "data" / "youtube_channels.json").is_file())
        copiados = {p.name for p in self.user.rglob("*") if p.is_file()}
        self.assertNotIn("google_credentials.json", copiados)
        self.assertNotIn("skool_cookies.json", copiados)
        self.assertNotIn("web.zip", copiados)

    def test_es_idempotente_y_no_pisa_lo_del_usuario(self):
        _bundle_con_recursos(self.bundle)
        runtime_setup.sembrar_datos_iniciales()
        (self.user / "agent.md").write_text("# editado por mí", encoding="utf-8")
        (self.user / "data" / "youtube_channels.json").write_text('[{"x": 1}]', encoding="utf-8")
        r = runtime_setup.sembrar_datos_iniciales()
        self.assertEqual((r["ai_workspace"], r["agent_md"], r["plantillas"]), (0, 0, 0))
        self.assertEqual((self.user / "agent.md").read_text(encoding="utf-8"), "# editado por mí")
        self.assertIn('"x"', (self.user / "data" / "youtube_channels.json").read_text(encoding="utf-8"))

    def test_iniciar_entorno_congelado_cambia_el_cwd_y_carga_las_claves(self):
        _bundle_con_recursos(self.bundle)
        self.user.mkdir(parents=True, exist_ok=True)
        (self.user / ".env").write_text("GEMTEST_INICIO=hola\n", encoding="utf-8")
        os.environ.pop("GEMTEST_INICIO", None)
        try:
            info = runtime_setup.iniciar_entorno()
            self.assertTrue(info["exe"])
            self.assertEqual(Path(os.getcwd()).resolve(), self.user.resolve())    # rutas relativas funcionan
            self.assertTrue(Path("agent.md").is_file())
            self.assertTrue(Path("ai_workspace/skills/buscar/procedimiento.md").is_file())
            self.assertEqual(os.environ["GEMTEST_INICIO"], "hola")
        finally:
            os.environ.pop("GEMTEST_INICIO", None)

    def test_sin_consola_redirige_la_salida_a_un_registro(self):
        antes = (sys.stdout, sys.stderr)
        sys.stdout = sys.stderr = None
        try:
            runtime_setup._redirigir_salida_sin_consola()
            self.assertIsNotNone(sys.stdout)
            print("no debe fallar")                                  # con --noconsole esto reventaba
            sys.stdout.flush()
            log = self.user / "logs" / "elite" / "arranque.log"
            self.assertIn("no debe fallar", log.read_text(encoding="utf-8"))
        finally:
            if sys.stdout not in (None, antes[0]):
                sys.stdout.close()
            sys.stdout, sys.stderr = antes


class ImportarDatosTests(Congelado):
    def origen(self, filas=3, nombre="data_origen"):
        carpeta = Path(self.tmp.name) / nombre
        carpeta.mkdir(exist_ok=True)
        with closing(sqlite3.connect(carpeta / "dropshipping_suite.db")) as c:
            c.execute("CREATE TABLE IF NOT EXISTS mis_cosas (x TEXT)")
            c.executemany("INSERT INTO mis_cosas VALUES (?)", [(f"fila{i}",) for i in range(filas)])
            c.commit()
        (carpeta / "youtube_channels.json").write_text('[{"nombre": "Canal"}]', encoding="utf-8")
        return carpeta

    def filas_destino(self):
        with closing(sqlite3.connect(PathManager.get_paths()["db"])) as c:
            return c.execute("SELECT COUNT(*) FROM mis_cosas").fetchone()[0]

    def test_trae_la_base_y_los_json(self):
        r = runtime_setup.importar_datos(self.origen(3))
        self.assertEqual(self.filas_destino(), 3)
        self.assertEqual(r["json"], ["youtube_channels.json"])
        self.assertIsNone(r["respaldo"])                              # no había nada que respaldar
        self.assertIn("Canal", (PathManager.get_paths()["data"] / "youtube_channels.json").read_text(encoding="utf-8"))

    def test_respalda_lo_que_hubiera_antes(self):
        runtime_setup.importar_datos(self.origen(2, "primera"))
        (PathManager.get_paths()["data"] / "youtube_channels.json").write_text("[]", encoding="utf-8")
        r = runtime_setup.importar_datos(self.origen(5, "segunda"))
        self.assertTrue(Path(r["respaldo"]).is_file())
        with closing(sqlite3.connect(r["respaldo"])) as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM mis_cosas").fetchone()[0], 2)   # la anterior sigue a salvo
        self.assertEqual(self.filas_destino(), 5)
        self.assertTrue((PathManager.get_paths()["data"] / "youtube_channels.json.bak").is_file())

    def test_rechaza_origen_roto_ausente_o_el_mismo(self):
        vacia = Path(self.tmp.name) / "vacia"
        vacia.mkdir()
        with self.assertRaises(FileNotFoundError):
            runtime_setup.importar_datos(vacia)
        rota = Path(self.tmp.name) / "rota"
        rota.mkdir()
        (rota / "dropshipping_suite.db").write_bytes(b"esto no es sqlite" * 300)
        with self.assertRaises(ValueError):
            runtime_setup.importar_datos(rota)
        self.assertFalse(PathManager.get_paths()["db"].exists())     # nada se tocó
        runtime_setup.importar_datos(self.origen())
        with self.assertRaisesRegex(ValueError, "ya es la carpeta"):
            runtime_setup.importar_datos(PathManager.get_paths()["data"])


class RecursosYAgenteTests(Congelado):
    def test_resolve_resource_prefiere_lo_del_usuario_y_cae_al_bundle(self):
        _bundle_con_recursos(self.bundle)
        # sin sembrar: se resuelve al bundle (agent.md existe allí)
        self.assertEqual(Path(PathManager.resolve_resource("agent.md")), self.bundle / "agent.md")
        runtime_setup.sembrar_datos_iniciales()
        self.assertEqual(Path(PathManager.resolve_resource("agent.md")), self.user / "agent.md")   # ahora el editable
        self.assertEqual(Path(PathManager.resolve_resource("ai_workspace")), self.user / "ai_workspace")
        absoluta = str(Path(self.tmp.name) / "x.md")
        self.assertEqual(PathManager.resolve_resource(absoluta), absoluta)
        # algo que no existe en ningún sitio → la ruta escribible (usuario)
        self.assertEqual(Path(PathManager.resolve_resource("no_existe.md")), self.user / "no_existe.md")

    def test_el_agente_encuentra_agent_md_sin_depender_del_cwd(self):
        """Antes: rutas relativas al cwd → en el .exe el pre-flight daba FAIL y el Agente IA no arrancaba."""
        _bundle_con_recursos(self.bundle)
        (self.bundle / "agent.md").write_text((REPO / "agent.md").read_text(encoding="utf-8"), encoding="utf-8")
        runtime_setup.sembrar_datos_iniciales()
        os.chdir(self.tmp.name)                                   # un cwd cualquiera, sin agent.md
        from app.services.validator_rules import RulesValidator
        ok, msg = RulesValidator(db_manager=mock.Mock())._check_agent_md()
        self.assertTrue(ok, msg)
        from app.agents_engine.executor import AgentExecutor
        ex = AgentExecutor(db_manager=mock.Mock())
        self.assertEqual(Path(ex.workspace_path), self.user / "ai_workspace")
        self.assertEqual(Path(ex.validator.agent_md_path), self.user / "agent.md")


def _cargar_verificador():
    import importlib.util
    spec = importlib.util.spec_from_file_location("verificar_dist", REPO / "scripts" / "verificar_dist.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class VerificarDistTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.dist = Path(self.tmp.name) / "GEM_OS_Suite"
        (self.dist / "_internal" / "app" / "templates").mkdir(parents=True)
        (self.dist / "_internal" / "app" / "templates" / "base.html").write_text("<html>", encoding="utf-8")
        (self.dist / "_internal" / "agent.md").write_text("# a", encoding="utf-8")
        (self.dist / "_internal" / ".env.example").write_text("OPENROUTER_API_KEY=sk-or-v1-XXXX\n", encoding="utf-8")
        (self.dist / "GEM_OS_Suite.exe").write_bytes(b"MZ")
        self.v = _cargar_verificador()

    def tearDown(self):
        self.tmp.cleanup()

    def test_un_dist_limpio_pasa(self):
        r = self.v.verificar(self.dist)
        self.assertEqual(r, {"prohibidos": [], "claves": [], "faltan": []})
        self.assertEqual(self.v.main([str(self.dist)]), 0)

    def test_detecta_env_credenciales_cookies_y_bases_de_datos(self):
        interno = self.dist / "_internal"
        (interno / ".env").write_text("A=1", encoding="utf-8")
        (interno / "ai_workspace" / "config").mkdir(parents=True)
        (interno / "ai_workspace" / "config" / "google_credentials.json").write_text("{}", encoding="utf-8")
        (interno / "skool_cookies.json").write_text("{}", encoding="utf-8")
        (interno / "data").mkdir()
        (interno / "data" / "dropshipping_suite.db").write_bytes(b"SQLite")
        r = self.v.verificar(self.dist)
        self.assertEqual(len(r["prohibidos"]), 4)
        self.assertEqual(self.v.main([str(self.dist)]), 2)

    def test_detecta_una_clave_real_escondida_en_un_texto(self):
        (self.dist / "_internal" / "notas.txt").write_text("mi clave sk-or-v1-" + "a1B2c3D4e5" * 4, encoding="utf-8")
        r = self.v.verificar(self.dist)
        self.assertEqual(r["claves"], ["_internal/notas.txt"])
        self.assertEqual(self.v.main([str(self.dist)]), 2)

    def test_el_example_no_cuenta_pero_los_recursos_si_hacen_falta(self):
        (self.dist / "_internal" / "agent.md").unlink()
        r = self.v.verificar(self.dist)
        self.assertEqual(r["prohibidos"], [])
        self.assertEqual(r["faltan"], ["agent.md"])
        self.assertEqual(self.v.main([str(self.dist)]), 3)
        self.assertEqual(self.v.main([str(Path(self.tmp.name) / "no_existe")]), 1)


if __name__ == "__main__":
    unittest.main()
