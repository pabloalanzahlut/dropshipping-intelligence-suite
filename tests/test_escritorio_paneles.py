"""Paneles nuevos del escritorio (Productos, Negocio, Insights, Sistema, Configuración, Agente IA, menú).
Se construyen de verdad con Tk sobre una BD temporal; los diálogos del sistema se simulan. Se omiten
si no hay pantalla disponible."""
import os
import sqlite3
import sys
import tempfile
import tkinter as tk
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import DatabaseConnection

try:
    _root = tk.Tk()
    _root.withdraw()
    _root.destroy()
    HAY_PANTALLA = True
except tk.TclError:
    HAY_PANTALLA = False


def dia(n):
    return (date.today() - timedelta(days=n)).isoformat()


@unittest.skipUnless(HAY_PANTALLA, "sin pantalla")
class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()
        from app.ui.themes import DarkTheme
        from app.ui.themes.jack_styles import apply_jack_styles
        DarkTheme().apply()
        apply_jack_styles(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        (Path(self.tmp.name) / "data").mkdir()
        self.db = DatabaseConnection(str(Path(self.tmp.name) / "data" / "t.db"))
        self.msg = mock.patch.multiple("tkinter.messagebox", showinfo=mock.DEFAULT, showwarning=mock.DEFAULT,
                                       showerror=mock.DEFAULT, askyesno=mock.DEFAULT)
        self.cajas = self.msg.start()
        self.cajas["askyesno"].return_value = True
        self.paneles = []

    def tearDown(self):
        for p in self.paneles:
            try:
                p.destroy()
            except tk.TclError:
                pass
        self.msg.stop()
        self.tmp.cleanup()

    def panel(self, clase, **kw):
        p = clase(self.root, db_manager=self.db, **kw)
        p.pack(fill="both", expand=True)
        self.root.update()
        self.paneles.append(p)
        return p

    def sql(self, consulta, *params):
        with sqlite3.connect(self.db.db_path) as c:
            return c.execute(consulta, params).fetchall()


class ProductosTests(Base):
    def test_recorrido_y_reglas(self):
        from app.services import product_catalog as pc
        from app.ui.components.productos_panel import ProductosPanel
        p = pc.crear(self.db.db_path, {"nombre": "Pelota gatos", "costo_origen": 5, "costo_envio": 2, "pvp": 15})
        panel = self.panel(ProductosPanel)
        self.assertEqual(len(panel._tree.get_children()), 1)
        panel._tree.selection_set(panel._tree.get_children()[0])
        panel._al_seleccionar()
        self.assertEqual(panel._sel, p["id"])
        # no se puede saltar de «candidato» a «validado»: el mensaje explica por qué
        panel._mover(p["id"], "validado")
        self.assertTrue(self.cajas["showwarning"].called)
        panel._mover(p["id"], "clasificado")
        self.assertEqual(pc.obtener(self.db.db_path, p["id"])["estado"], "clasificado")
        # el multiplicador va sobre el coste landed (7), no sobre el producto solo: 15/7 = 2,14 → COLD
        self.assertEqual(pc.obtener(self.db.db_path, p["id"])["calculo"]["multiplicador"], 2.14)

    def test_filtro_y_busqueda(self):
        from app.services import product_catalog as pc
        from app.ui.components.productos_panel import ProductosPanel
        pc.crear(self.db.db_path, {"nombre": "Pelota"})
        pc.crear(self.db.db_path, {"nombre": "Collar"})
        panel = self.panel(ProductosPanel)
        panel._buscar.set("Col")
        panel.cargar()
        self.assertEqual(len(panel._tree.get_children()), 1)

    def test_descartar_y_borrar(self):
        from app.services import product_catalog as pc
        from app.ui.components.productos_panel import ProductosPanel
        p = pc.crear(self.db.db_path, {"nombre": "X"})
        panel = self.panel(ProductosPanel)
        with mock.patch("tkinter.simpledialog.askstring", return_value="no engancha"):
            panel._mover(p["id"], "descartado", pedir_nota=True)
        self.assertEqual(pc.obtener(self.db.db_path, p["id"])["estado"], "descartado")
        panel._borrar(pc.obtener(self.db.db_path, p["id"]))
        self.assertEqual(pc.listar(self.db.db_path), [])


class NegocioTests(Base):
    def test_kpis_y_registro_del_dia(self):
        from app.ui.components.negocio_panel import NegocioPanel
        panel = self.panel(NegocioPanel)
        panel._m["gasto_ads"].set("100")
        panel._m["ingresos"].set("300")
        panel._m["pedidos"].set("6")
        panel._guardar_dia()
        self.assertEqual(self.sql("SELECT COUNT(*) FROM metricas_diarias")[0][0], 1)
        self.assertEqual(panel._kpis["roas"]._v.cget("text"), "3.0×")
        panel._c["saldo_cuenta"].set("900")
        panel._guardar_caja()
        self.assertEqual(self.sql("SELECT saldo_cuenta FROM caja_diaria")[0][0], 900.0)
        panel._tree.selection_set(panel._tree.get_children()[0])
        panel._borrar()
        self.assertEqual(self.sql("SELECT COUNT(*) FROM metricas_diarias")[0][0], 0)

    def test_datos_invalidos_avisan(self):
        from app.ui.components.negocio_panel import NegocioPanel
        panel = self.panel(NegocioPanel)
        panel._m["fecha"].set("ayer")
        panel._guardar_dia()
        self.assertTrue(self.cajas["showwarning"].called)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM metricas_diarias")[0][0], 0)

    def test_importar_csv_con_vista_previa_y_filtro_de_campanas(self):
        from app.ui.components.negocio_panel import ImportarCSVDialog
        csv = (f"Día;Nombre de la campaña;Importe gastado (EUR);Visitas a la página de destino\n"
               f"{dia(2)};A;\"12,50\";40\n{dia(2)};B;\"7,50\";22\n{dia(1)};A;\"30,00\";55\n").encode()
        hechos = []
        d = ImportarCSVDialog(self.root, self.db.db_path, csv, "meta.csv", [], al_terminar=lambda: hechos.append(1))
        self.paneles.append(d)
        self.root.update()
        self.assertEqual(len(d._tree.get_children()), 2)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM metricas_diarias")[0][0], 0)      # solo vista previa
        d._sel["B"].set(False)                                                            # excluye la campaña B
        d._previsualizar()
        d._importar()
        filas = self.sql("SELECT fecha, gasto_ads FROM metricas_diarias ORDER BY fecha")
        self.assertEqual(filas, [(dia(2), 12.5), (dia(1), 30.0)])
        self.assertEqual(hechos, [1])

    def test_importar_csv_roto_no_escribe(self):
        from app.ui.components.negocio_panel import ImportarCSVDialog
        d = ImportarCSVDialog(self.root, self.db.db_path, b"a,b\n1,2\n", "x.csv", [])
        self.paneles.append(d)
        self.root.update()
        self.assertEqual(str(d._ok["state"]), "disabled")
        self.assertIn("No reconozco", d._resumen.cget("text"))


class InsightsSistemaTests(Base):
    def sembrar_kb(self):
        with sqlite3.connect(self.db.db_path) as c:
            c.execute("INSERT INTO video_sources (video_id, platform, title, channel_name, content_hash) "
                      "VALUES ('v1', 'youtube', 'Cómo escalar', 'Canal Uno', 'h')")
            c.execute("INSERT INTO product_trends (video_id, product_name, niche, wow_factor) "
                      "VALUES ('v1', 'Pelota interactiva', 'mascotas', 'se mueve sola')")

    def test_insights_filtra_y_muestra_detalle(self):
        from app.ui.components.insights_panel import InsightsPanel
        self.sembrar_kb()
        panel = self.panel(InsightsPanel)
        self.assertEqual(len(panel._tree.get_children()), 1)
        self.assertEqual(panel._kpis["total"]._v.cget("text"), "1")
        panel._tree.selection_set(panel._tree.get_children()[0])
        panel._detalle()
        self.assertIn("se mueve sola", panel._texto.get("1.0", "end"))
        panel._buscar.set("zzzz")
        panel.cargar()
        self.assertEqual(len(panel._tree.get_children()), 0)

    def test_sistema_alertas_resumen_historial(self):
        from app.services import alerts
        from app.ui.components.sistema_panel import SistemaPanel
        vistas = []
        panel = self.panel(SistemaPanel, al_cambiar_alertas=vistas.append)
        cfg = str(Path(self.tmp.name) / "data" / "youtube_channels.json")
        Path(cfg).write_text("[]", encoding="utf-8")
        alerts.evaluar(self.db.db_path, cfg)
        panel.cargar_alertas()
        self.assertGreaterEqual(len(panel._al_tree.get_children()), 1)                  # «catálogo vacío», al menos
        self.assertTrue(vistas and vistas[-1]["total_activas"] >= 1)
        panel._marcar_vistas()
        self.assertEqual(vistas[-1]["sin_ver"], 0)
        panel.mostrar_pestana("historial")
        self.assertEqual(panel._tipo_historial(), "productos")
        self.assertEqual(len(panel._pestanas), 5)

    def test_exportar_csv_del_historial(self):
        from app.services import exports
        from app.services import product_catalog as pc
        pc.crear(self.db.db_path, {"nombre": "=SUMA(1;1)"})                              # intento de inyección de fórmula
        cfg = str(Path(self.tmp.name) / "data" / "youtube_channels.json")
        Path(cfg).write_text("[]", encoding="utf-8")
        d = exports.todas_las_filas(self.db.db_path, cfg, "productos")
        csv = exports.a_csv(d["columnas"], d["filas"]).decode("utf-8")
        self.assertIn("'=SUMA", csv)
        self.assertEqual(exports.todas_las_filas(self.db.db_path, cfg, "canales")["total"], 0)
        with self.assertRaises(KeyError):
            exports.dataset(self.db.db_path, cfg, "no_existe")


class ConfiguracionTests(Base):
    def setUp(self):
        super().setUp()
        self.env = mock.patch.dict(os.environ, {}, clear=False)
        self.env.start()
        os.environ.pop("OPENROUTER_API_KEY", None)
        os.environ.pop("GEMTEST_X", None)
        self.ruta = Path(self.tmp.name) / "usuario" / ".env"
        self.p = mock.patch("app.config.secrets_store.ruta_env_escritura", return_value=self.ruta)
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.env.stop()
        super().tearDown()

    def test_guardar_probar_y_quitar_una_clave(self):
        from app.ui.components.settings_panel import SettingsPanel
        cambios = []
        panel = self.panel(SettingsPanel, al_cambiar_claves=lambda: cambios.append(1), primer_arranque=True)
        panel._campos["OPENROUTER_API_KEY"].set("sk-or-v1-PRUEBAPRUEBAPRUEBA1234")
        panel._guardar()
        self.assertIn("OPENROUTER_API_KEY=sk-or-v1-PRUEBAPRUEBAPRUEBA1234", self.ruta.read_text(encoding="utf-8"))
        self.assertEqual(os.environ["OPENROUTER_API_KEY"], "sk-or-v1-PRUEBAPRUEBAPRUEBA1234")
        self.assertEqual(cambios, [1])
        self.assertEqual(panel._campos["OPENROUTER_API_KEY"].get(), "")                 # el campo se vacía
        self.assertIn("1234", getattr(panel, "_act_OPENROUTER_API_KEY").cget("text"))     # solo los 4 últimos
        self.assertNotIn("PRUEBAPRUEBA", getattr(panel, "_act_OPENROUTER_API_KEY").cget("text"))
        panel._quitar("OPENROUTER_API_KEY")
        self.assertNotIn("OPENROUTER_API_KEY", os.environ)
        self.assertEqual(cambios, [1, 1])

    def test_valida_nombre_de_otra_variable_y_silencio(self):
        from app.ui.components.settings_panel import SettingsPanel
        panel = self.panel(SettingsPanel)
        panel._otra_nombre.set("nombre malo")
        panel._otra_valor.set("x")
        panel._guardar_otra()
        self.assertFalse(self.ruta.exists())
        panel._otra_nombre.set("gemtest_x")
        panel._guardar_otra()
        self.assertEqual(os.environ["GEMTEST_X"], "x")
        panel._av_silencio.set("23-99")
        panel._guardar_avisos()
        self.assertIn("inicio-fin", panel._av_res.cget("text"))
        panel._av_silencio.set("22-6")
        panel._guardar_avisos()
        self.assertEqual(os.environ["GEM_OS_AVISOS_SILENCIO"], "22-6")


class MenuYAgenteTests(Base):
    def test_el_menu_agrupa_selecciona_por_clave_y_se_contrae(self):
        from app.ui.components.navigation_v2 import SECCION, Sidebar
        pulsados = []
        s = Sidebar(self.root, items=[(SECCION, "A", None), ("1", "Uno", lambda: pulsados.append("uno"), 7),
                                      ("2", "Dos", lambda: pulsados.append("dos"), 11),
                                      (SECCION, "B", None), ("3", "Tres", lambda: pulsados.append("tres"), 3)])
        s.pack(fill="y")
        self.paneles.append(s)
        self.root.update()
        self.assertEqual(len(s.buttons), 3)
        self.assertEqual(sorted(s._secciones), [0, 2])
        s.seleccionar(11)
        self.assertEqual([b.is_active for b in s.buttons], [False, True, False])
        s._on_item_click(2)
        self.assertEqual(pulsados, ["tres"])
        s._toggle_collapse()
        self.assertEqual(s.buttons[0].label, "")
        s._toggle_collapse()
        self.root.update()
        self.assertEqual(s.buttons[0].label, "Uno")
        s.seleccionar(999)                                              # clave desconocida: no rompe
        self.assertEqual(s.active_index, 2)

    def test_el_agente_detecta_el_tipo_de_pregunta(self):
        from app.ui.components.kb_agent_panel import KBAgentPanel
        p = KBAgentPanel(self.root, db_manager=self.db)
        p.pack()
        self.paneles.append(p)
        p.query_text.delete("1.0", "end")
        p.query_text.insert("1.0", "Si lo compro a 5 dólares y lo vendo a 12, ¿cuál es el margen?")
        p._actualizar_ruta()
        self.assertIn("gem-qa-validation", p._ruta_lbl.cget("text"))
        p._agente_var.set(next(k for k in p._agentes_opc if "backend" in k))
        p._actualizar_ruta()
        self.assertIn("fijado", p._ruta_lbl.cget("text"))
        self.assertEqual(p._agente_elegido(), "gem-backend-core")
        self.assertEqual(p._sin_fences('```json\n{"a": 1}\n```'), '{"a": 1}')


if __name__ == "__main__":
    unittest.main()
