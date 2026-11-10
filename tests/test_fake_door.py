"""Fase 3: fake-door — eventos, mediana/CTR, gate determinista y el único bypass de
auth de toda la app (RUTAS_LIBRES). Sin red. BD temporal."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import DatabaseConnection
from app.services import deterministic_gate as gate
from app.services import fake_door_service as fd
from app.services import product_catalog as pc
from app.services import web_auth


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        raiz = Path(self.tmp.name)
        (raiz / "data").mkdir()
        self.db = str(raiz / "data" / "t.db")
        DatabaseConnection(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def _producto(self, nombre="Lámpara"):
        return pc.crear(self.db, {"nombre": nombre, "costo_origen": 6, "costo_envio": 2, "pvp": 25})


class WebAuthBypassTests(unittest.TestCase):
    """El único prefijo público de toda la app debe ser /fd/ — nada más se amplía."""

    def test_fd_es_libre(self):
        self.assertTrue(web_auth.es_libre("/fd/1"))
        self.assertTrue(web_auth.es_libre("/fd/1/evento"))

    def test_rutas_autenticadas_siguen_protegidas(self):
        for ruta in ("/productos", "/api/productos/1", "/api/productos/1/fake-door",
                     "/api/productos/1/fake-door/calcular", "/gobernanza", "/configuracion"):
            self.assertFalse(web_auth.es_libre(ruta), f"{ruta} no debería ser libre")

    def test_prefijo_no_se_confunde_con_otras_rutas_parecidas(self):
        # "/fd" sin barra, o algo que empiece distinto, no debe colarse.
        self.assertFalse(web_auth.es_libre("/fd"))
        self.assertFalse(web_auth.es_libre("/fdx/1"))


class RegistrarEventoTests(Base):
    def test_evento_de_producto_inexistente_no_se_guarda(self):
        ok = fd.registrar_evento(self.db, 99999, "visita")
        self.assertFalse(ok)

    def test_tipo_invalido_no_se_guarda(self):
        p = self._producto()
        ok = fd.registrar_evento(self.db, p["id"], "compra_real")
        self.assertFalse(ok)

    def test_registra_visita_clic_y_email(self):
        p = self._producto()
        self.assertTrue(fd.registrar_evento(self.db, p["id"], "visita"))
        self.assertTrue(fd.registrar_evento(self.db, p["id"], "clic_comprar"))
        self.assertTrue(fd.registrar_evento(self.db, p["id"], "email", email="a@b.com"))
        r = fd.resumen_producto(self.db, p["id"])
        self.assertEqual((r["visitas"], r["clics_comprar"], r["emails"]), (1, 1, 1))
        self.assertEqual(r["ctr"], 1.0)

    def test_nunca_guarda_la_ip_en_claro(self):
        p = self._producto()
        fd.registrar_evento(self.db, p["id"], "visita", ip="203.0.113.5")
        import sqlite3
        with sqlite3.connect(self.db) as conn:
            fila = conn.execute("SELECT ip_hash FROM fake_door_eventos LIMIT 1").fetchone()
        self.assertIsNotNone(fila[0])
        self.assertNotIn("203.0.113.5", fila[0])

    def test_limite_por_ip_descarta_el_exceso(self):
        p = self._producto()
        ip = "198.51.100.9"
        resultados = [fd.registrar_evento(self.db, p["id"], "visita", ip=ip) for _ in range(fd._LIMITE_POR_MINUTO + 5)]
        self.assertTrue(all(resultados[:fd._LIMITE_POR_MINUTO]))
        self.assertFalse(any(resultados[fd._LIMITE_POR_MINUTO:]))

    def test_concentracion_alta_cuando_una_sola_ip_domina(self):
        p = self._producto()
        for _ in range(9):
            fd.registrar_evento(self.db, p["id"], "visita", ip="10.0.0.1")
        fd.registrar_evento(self.db, p["id"], "visita", ip="10.0.0.2")
        r = fd.resumen_producto(self.db, p["id"])
        self.assertEqual(r["concentracion"], 0.9)


class MedianaGlobalTests(Base):
    def test_mediana_con_varios_productos(self):
        a, b, c = self._producto("A"), self._producto("B"), self._producto("C")
        for _ in range(10):
            fd.registrar_evento(self.db, a["id"], "visita")
        for _ in range(2):
            fd.registrar_evento(self.db, a["id"], "clic_comprar")   # ctr 0.2
        for _ in range(10):
            fd.registrar_evento(self.db, b["id"], "visita")
        for _ in range(4):
            fd.registrar_evento(self.db, b["id"], "clic_comprar")   # ctr 0.4
        for _ in range(10):
            fd.registrar_evento(self.db, c["id"], "visita")
        for _ in range(6):
            fd.registrar_evento(self.db, c["id"], "clic_comprar")   # ctr 0.6
        self.assertEqual(fd.mediana_ctr(self.db), 0.4)
        # Excluyendo el propio producto (B), la mediana de los otros dos (0.2, 0.6) es 0.4 también
        self.assertEqual(fd.mediana_ctr(self.db, excluir_producto_id=b["id"]), 0.4)

    def test_sin_eventos_mediana_es_cero(self):
        self.assertEqual(fd.mediana_ctr(self.db), 0.0)


class CheckFakeDoorCtrTests(unittest.TestCase):
    def test_sin_visitas_no_decide(self):
        r = gate.check_fake_door_ctr(ctr=0.0, mediana_global=0.1, visitas=0)
        self.assertFalse(r.passed)

    def test_sin_mediana_historica(self):
        r = gate.check_fake_door_ctr(ctr=0.1, mediana_global=0.0, visitas=50)
        self.assertTrue(r.passed)
        self.assertEqual(r.evidence["veredicto"], "sin_referencia_historica")

    def test_ctr_al_doble_de_la_mediana_produce(self):
        r = gate.check_fake_door_ctr(ctr=0.2, mediana_global=0.1, visitas=100)
        self.assertEqual(r.evidence["veredicto"], "producir")

    def test_ctr_cerca_de_la_mediana_repite(self):
        r = gate.check_fake_door_ctr(ctr=0.09, mediana_global=0.1, visitas=100)
        self.assertEqual(r.evidence["veredicto"], "repetir")

    def test_ctr_muy_por_debajo_descarta(self):
        r = gate.check_fake_door_ctr(ctr=0.03, mediana_global=0.1, visitas=100)
        self.assertEqual(r.evidence["veredicto"], "descartar")

    def test_concentracion_alta_marca_aviso_sin_cambiar_el_passed(self):
        r = gate.check_fake_door_ctr(ctr=0.2, mediana_global=0.1, visitas=100, concentracion=0.9)
        self.assertTrue(r.passed)
        self.assertTrue(r.violations)


class GuardarDemandaDesdeEventosTests(Base):
    def test_calcula_y_reutiliza_guardar_demanda_sin_tocar_creativo_ok(self):
        p = self._producto()
        for _ in range(10):
            fd.registrar_evento(self.db, p["id"], "visita")
        for _ in range(3):
            fd.registrar_evento(self.db, p["id"], "clic_comprar")
        resultado = pc.guardar_demanda_desde_eventos(self.db, p["id"])
        self.assertEqual(resultado["demanda"]["visitantes"], 10)
        self.assertEqual(resultado["demanda"]["clics_comprar"], 3)
        self.assertFalse(resultado["creativo_ok"])    # nunca lo toca: sigue en False por defecto
        self.assertIn("fake_door_gate", resultado)

    def test_producto_inexistente_lanza_keyerror(self):
        with self.assertRaises(KeyError):
            pc.guardar_demanda_desde_eventos(self.db, 99999)


if __name__ == "__main__":
    unittest.main()
