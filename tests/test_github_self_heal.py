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


class AccionesCableadasTest(unittest.TestCase):
    """Cada acción 'auto' del catálogo debe tener implementación en resolver()."""

    def test_toda_accion_auto_esta_cableada(self):
        fuente = (ROOT / "scripts" / "github_self_heal.py").read_text(encoding="utf-8")
        cat = gsh.cargar_catalogo()
        for fix in cat["fixes"]:
            if fix["auto"]:
                self.assertTrue(
                    fix["accion"] in fuente or fix["accion"] in ("allowlist_gitleaks", "untrack_archivo"),
                    f"{fix['id']} -> {fix['accion']} sin implementar")
        for accion in ("bump_actions", "cerrar_dependabot_obsoleto", "pin_version_existente", "secrets_a_env"):
            self.assertIn(f'"{accion}"', fuente)

    def test_untrack_se_planifica_en_dry_run(self):
        log = ("Finding: x\nSecret: REDACTED\nRuleID: generic-api-key\nEntropy: 4.9\n"
               "File: .playwright-mcp/sesion.json\nLine: 3\nCommit: abc1234\n")
        informe = gsh.resolver(log, gsh.cargar_catalogo(), dry_run=True)
        self.assertTrue(any("git rm --cached" in l and "F-010" in l for l in informe))

    def test_bump_actions_solo_sube(self):
        with tempfile.TemporaryDirectory() as d:
            wfdir = Path(d) / ".github" / "workflows"
            wfdir.mkdir(parents=True)
            wf = wfdir / "a.yml"
            wf.write_text("steps:\n  - uses: actions/checkout@v4\n  - uses: foo/bar@v9\n", encoding="utf-8")
            original = gsh.ROOT
            gsh.ROOT = Path(d)
            try:
                tocados = gsh.fix_bump_actions(
                    gsh.cargar_catalogo(), None, consulta=lambda repo, tok: {"actions/checkout": "v7", "foo/bar": "v3"}[repo])
            finally:
                gsh.ROOT = original
            texto = wf.read_text(encoding="utf-8")
            self.assertEqual(tocados, [".github/workflows/a.yml"])
            self.assertIn("actions/checkout@v7", texto)
            self.assertIn("foo/bar@v9", texto)  # nunca baja de versión

    def test_toca_workflows(self):
        self.assertTrue(gsh.toca_workflows([".github/workflows/x.yml"]))
        self.assertFalse(gsh.toca_workflows(["requirements.txt"]))


try:
    import yaml  # noqa: F401
    _YAML = True
except ImportError:
    _YAML = False


@unittest.skipUnless(_YAML, 'requiere PyYAML')
class LintWorkflowsTest(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import lint_workflows
        self.lw = lint_workflows

    def test_name_con_dos_puntos_es_invalido_y_se_repara(self):
        roto = "name: X\njobs:\n  a:\n    steps:\n      - name: Tests (sin Tk ni .exe: no corren)\n        run: echo hola\n"
        self.assertIsNotNone(self.lw.validar(roto))
        arreglado = self.lw.entrecomillar_names(roto)
        self.assertIsNone(self.lw.validar(arreglado))
        self.assertIn('"Tests (sin Tk ni .exe; no corren)"', arreglado)

    def test_yaml_valido_no_se_toca(self):
        ok = "name: X\njobs:\n  a:\n    steps:\n      - name: Paso normal\n        run: echo 'a: b'\n"
        self.assertEqual(self.lw.entrecomillar_names(ok), ok)

    def test_todos_los_workflows_del_repo_son_validos(self):
        for wf in sorted(self.lw.WORKFLOWS.glob("*.yml")):
            self.assertIsNone(self.lw.validar(wf.read_bytes().decode("utf-8")), wf.name)


if __name__ == "__main__":
    unittest.main()
