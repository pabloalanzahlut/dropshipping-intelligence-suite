"""Plugin gem-os para Cowork: lo versionado coincide con las fuentes y pasa las compuertas. Sin red."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

import build_cowork as bc  # noqa: E402

GATE_CLI = bc.PLUGIN_DIR / "skills" / "verificar-salida" / "scripts" / "gate_cli.py"


def gate(*args):
    r = subprocess.run([sys.executable, str(GATE_CLI), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, json.loads(r.stdout)


class PluginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapa = bc.construir_plugin()

    def test_las_fuentes_pasan_todas_las_compuertas(self):
        self.assertEqual(bc.validar(self.mapa), [])

    def test_el_plugin_versionado_coincide_con_las_fuentes(self):
        # Si falla: python scripts/build_cowork.py plugin
        self.assertEqual(bc.diferencias(self.mapa, bc.PLUGIN_DIR), [])
        self.assertEqual(bc._norm(bc.MARKETPLACE_JSON.read_bytes()), bc.construir_marketplace())

    def test_construir_es_determinista(self):
        self.assertEqual(self.mapa, bc.construir_plugin())

    def test_el_gate_es_copia_exacta(self):
        copia = self.mapa["skills/verificar-salida/scripts/deterministic_gate.py"]
        self.assertEqual(copia, bc._norm(bc.GATE.read_bytes()))

    def test_solo_se_exporta_la_lista_blanca(self):
        skills = {rel.split("/")[1] for rel in self.mapa if rel.startswith("skills/")}
        self.assertEqual(skills, set(bc.SKILLS_COWORK) | set(bc.SKILLS_BASE))
        self.assertFalse(skills & set(bc.SOLO_CODE))
        self.assertFalse(set(bc.SKILLS_COWORK) & set(bc.SOLO_CODE))

    def test_ningun_procedimiento_solo_code_viaja_como_referencia(self):
        refs = {Path(rel).stem for rel in self.mapa if "/referencias/" in rel}
        self.assertFalse(refs & bc.PROCEDIMIENTOS_SOLO_CODE)

    def test_cada_skill_tiene_nombre_y_descripcion_validos(self):
        for skill in set(bc.SKILLS_COWORK) | set(bc.SKILLS_BASE):
            meta, cuerpo = bc._frontmatter(self.mapa[f"skills/{skill}/SKILL.md"].decode("utf-8"))
            self.assertEqual(meta["name"], skill)
            desc = json.loads(meta["description"])
            self.assertTrue(0 < len(desc) <= 1024, skill)
            self.assertTrue(cuerpo.strip(), skill)

    def test_las_skills_exportadas_remiten_a_las_reglas_y_al_gate(self):
        for skill in bc.SKILLS_COWORK:
            texto = self.mapa[f"skills/{skill}/SKILL.md"].decode("utf-8")
            self.assertIn("reglas-gem-os", texto, skill)
            self.assertIn("verificar-salida", texto, skill)
            self.assertIn("DATA_GAP_REQUEST", texto, skill)

    def test_sin_ids_de_conector_de_sesion(self):
        for rel, contenido in self.mapa.items():
            if rel.endswith(".md"):
                self.assertIsNone(bc.PROHIBIDOS["ID de conector de sesión"].search(contenido.decode("utf-8")), rel)

    def test_las_reglas_financieras_viajan_sin_tocar(self):
        for nombre in ("reglas-financieras.md", "verificacion-determinista.md"):
            self.assertEqual(self.mapa[f"skills/reglas-gem-os/{nombre}"],
                             bc._b(bc._leer(bc.MEMORY / nombre)))

    def test_manifiestos(self):
        plugin = json.loads(self.mapa[".claude-plugin/plugin.json"])
        market = json.loads(bc.construir_marketplace())
        self.assertEqual(plugin["name"], "gem-os")
        self.assertTrue(plugin["version"].startswith("1.0.0-"))
        self.assertEqual(market["plugins"][0]["source"], "./plugins/gem-os")
        self.assertTrue((bc.ROOT / market["plugins"][0]["source"]).is_dir())


class CompuertasTests(unittest.TestCase):
    """Las compuertas tienen que saltar cuando una fuente contradice las reglas."""

    def test_detecta_multiplicador_sobre_el_producto_solo(self):
        self.assertTrue(bc.lint_texto("skills/x/SKILL.md", "Ratio 3x = PVP / CO (debe ser ≥ 3.0)"))
        self.assertTrue(bc.lint_texto("skills/x/SKILL.md", "Multiplicador = PVP / Costo_origen"))
        self.assertEqual(bc.lint_texto("skills/x/SKILL.md", "Multiplicador = PVP / coste landed"), [])

    def test_detecta_umbral_antiguo_y_datos_asumidos(self):
        self.assertTrue(bc.lint_texto("skills/x/SKILL.md", "| 1.5x – 2.99x | COLD |"))
        self.assertTrue(bc.lint_texto("skills/x/SKILL.md", "si no, usar 4.50 como estimado"))
        self.assertTrue(bc.lint_texto("skills/x/SKILL.md", "usa defaults por vertical"))

    def test_detecta_id_de_conector_y_lo_sustituye_al_adaptar(self):
        self.assertTrue(bc.lint_texto("skills/x/SKILL.md", "Usar `mcp__69f3b6ec`"))
        self.assertEqual(bc.adaptar("- **Stripe** (`mcp__1cc6d3ec`): leer"), "- **Stripe**: leer")
        self.assertEqual(bc.adaptar("usa mcp__69f3b6ec"), "usa conector Google Sheets")
        with self.assertRaises(bc.BuildError):
            bc.adaptar("usa mcp__00000000")

    def test_detecta_webhook_real_pero_no_el_de_ejemplo(self):
        self.assertTrue(bc.lint_texto("skills/x/a.md", "https://hook.eu1.make.com/abc123def456ghi"))
        self.assertEqual(bc.lint_texto("skills/x/a.md", "https://hook.eu1.make.com/XXXXXXXX"), [])

    def test_adaptar_traduce_las_rutas_del_repo(self):
        self.assertEqual(bc.adaptar("lee ai_workspace/knowledge_base/kb_x.md"), "lee contexto/kb/kb_x.md")
        self.assertEqual(bc.adaptar("ver .claude/memory/reglas-financieras.md"),
                         "ver reglas-gem-os/reglas-financieras.md")

    def test_validar_rechaza_un_gate_modificado(self):
        mapa = dict(bc.construir_plugin())
        mapa["skills/verificar-salida/scripts/deterministic_gate.py"] += b"\n# relajado\n"
        self.assertTrue(any("copia exacta" in e for e in bc.validar(mapa)))


class GateEmpaquetadoTests(unittest.TestCase):
    """El gate que viaja en el plugin se ejecuta solo, sin el repositorio."""

    def test_caso_de_claude_md_5_mas_2_a_15_no_es_3x(self):
        codigo, r = gate("financiera", json.dumps(
            {"costo_origen": 5, "costo_envio": 2, "pvp_calculado": 15, "multiplicador": 3.0, "costo_landed": 7}))
        self.assertEqual(codigo, 1)
        self.assertFalse(r["passed"])
        self.assertEqual(r["detail"]["aritmetica_financiera"]["multiplicador_real"], 2.14)

    def test_multiplicador_correcto_pasa(self):
        codigo, r = gate("financiera", json.dumps(
            {"costo_origen": 5, "costo_envio": 2, "pvp_calculado": 30, "multiplicador": 4.29, "costo_landed": 7}))
        self.assertEqual((codigo, r["passed"]), (0, True))

    def test_sin_envio_es_data_gap_y_no_se_asume_cero(self):
        codigo, r = gate("financiera", json.dumps(
            {"costo_origen": 5, "pvp_calculado": 15, "multiplicador": 3.0, "costo_landed": 5}))
        self.assertEqual(codigo, 2)
        self.assertIn("DATA_GAP_REQUEST", r["error"])

    def test_copy_con_superlativo_y_envio_irreal_no_pasa(self):
        codigo, r = gate("copy", "Producto increíble con envío 24-48h")
        self.assertEqual(codigo, 1)
        self.assertEqual(len(r["violations"]), 2)


if __name__ == "__main__":
    unittest.main()
