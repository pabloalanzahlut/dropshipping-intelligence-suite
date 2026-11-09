import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import github_self_heal as gsh  # noqa: E402

LOG_GITLEAKS = """2026-11-09T05:34:27.0000000Z Finding:     api_key = REDACTED
2026-11-09T05:34:27.0000000Z Secret:      REDACTED
2026-11-09T05:34:27.0000000Z RuleID:      generic-api-key
2026-11-09T05:34:27.0000000Z Entropy:     {entropia}
2026-11-09T05:34:27.0000000Z File:        tests/test_exe_portable.py
2026-11-09T05:34:27.0000000Z Line:        146
2026-11-09T05:34:27.0000000Z Commit:      ef4f8b47c769a3077ed686874eaf204d2b282d58
2026-11-09T05:34:27.0000000Z leaks found: 1
"""


class ClasificarTest(unittest.TestCase):
    def setUp(self):
        self.cat = gsh.cargar_catalogo()

    def test_catalogo_coincide_con_tabla_kb(self):
        kb = (ROOT / "ai_workspace" / "knowledge_base" / "github_kb.md").read_text(encoding="utf-8")
        for fix in self.cat["fixes"]:
            if fix["id"] != "F-012":
                self.assertIn(f"| {fix['id']} |", kb, fix["id"])

    def test_gitleaks_se_parsea_con_timestamp(self):
        r = gsh.clasificar(LOG_GITLEAKS.format(entropia=3.73), self.cat)
        self.assertEqual(r["tipo"], "gitleaks")
        self.assertEqual(r["hallazgos"][0]["file"], "tests/test_exe_portable.py")
        self.assertAlmostEqual(r["hallazgos"][0]["entropy"], 3.73)

    def test_placeholder_no_es_fuga(self):
        h = {"rule": "generic-api-key", "entropy": 3.73}
        self.assertFalse(gsh.es_fuga_real(h, "sk-or-v1-SECRETOSECRETOSECRETO1234"))

    def test_entropia_alta_es_fuga(self):
        h = {"rule": "generic-api-key", "entropy": 4.9}
        self.assertTrue(gsh.es_fuga_real(h, "sk-or-v1-SECRETOSECRETOSECRETO1234"))

    def test_regla_especifica_siempre_es_fuga(self):
        self.assertTrue(gsh.es_fuga_real({"rule": "private-key", "entropy": 1.0}, "XXXXXXXXXXXXXXXXXXXX"))

    def test_valor_desconocido_es_fuga(self):
        self.assertTrue(gsh.es_fuga_real({"rule": "generic-api-key", "entropy": 3.0}, None))

    def test_version_inexistente_f008(self):
        r = gsh.clasificar("ERROR: No matching distribution found for uvicorn==9.9.9", self.cat)
        self.assertEqual(r["fix_id"], "F-008")

    def test_dirty_pr_f002(self):
        r = gsh.clasificar("Pull request is not mergeable", self.cat)
        self.assertEqual(r["fix_id"], "F-002")

    def test_log_desconocido(self):
        self.assertEqual(gsh.clasificar("algo totalmente nuevo", self.cat)["tipo"], "desconocido")

    def test_rutas_prohibidas(self):
        self.assertTrue(gsh.ruta_prohibida("CLAUDE.md", self.cat))
        self.assertTrue(gsh.ruta_prohibida(".claude/memory/x.md", self.cat))
        self.assertFalse(gsh.ruta_prohibida("requirements.txt", self.cat))

    def test_dry_run_no_escribe_y_reporta_fuga(self):
        informe = gsh.resolver(LOG_GITLEAKS.format(entropia=4.8), self.cat, dry_run=True)
        self.assertTrue(any("FUGA REAL" in l for l in informe))


class FixesTest(unittest.TestCase):
    def test_secrets_a_env(self):
        with tempfile.TemporaryDirectory() as d:
            wf = Path(d) / "wf.yml"
            wf.write_text(
                "jobs:\n  a:\n    steps:\n      - name: X\n        run: |\n          curl -H ${{ secrets.TOKEN }} x\n",
                encoding="utf-8")
            original_root = gsh.ROOT
            gsh.ROOT = Path(d)
            try:
                tocados = gsh.fix_secrets_a_env(wf)
            finally:
                gsh.ROOT = original_root
            texto = wf.read_text(encoding="utf-8")
            self.assertEqual(tocados, ["wf.yml"])
            self.assertIn("_TOKEN: ${{ secrets.TOKEN }}", texto)
            self.assertIn('"$_TOKEN"', texto)
            self.assertNotIn("run: |\n          curl -H ${{", texto)

    def test_registrar_kb_incrementa_contador(self):
        with tempfile.TemporaryDirectory() as d:
            kb = Path(d) / "kb.md"
            kb.write_text(
                "| F-005 | X | y | z | 1 |\n" + gsh.KB_MARCADOR + "\n## INC-20261109-011 | A | B\n",
                encoding="utf-8")
            original = gsh.KB
            gsh.KB = kb
            try:
                inc = gsh.registrar_kb("F-005", "AUTO", "firma", "ok")
            finally:
                gsh.KB = original
            texto = kb.read_text(encoding="utf-8")
            self.assertEqual(inc.split("-")[-1], "012")
            self.assertIn("| F-005 | X | y | z | 2 |", texto)


class ReadmeTest(unittest.TestCase):
    def test_readme_sincronizado(self):
        import sync_readme
        actual = sync_readme.README.read_text(encoding="utf-8")
        self.assertEqual(sync_readme.renderizar(actual), actual)


if __name__ == "__main__":
    unittest.main()
