"""
N2 - SYSTEM HEALTH (Nivel 2: Healthcheck)
═════════════════════════════════════════
Validación DB, API keys, disco, config, dependencias.
Reportes JSON + HTML (mismo formato que PowerShell).
Cumple con: Health Check & Resiliencia I/O (Agent-KB.md)
═════════════════════════════════════════
"""
import os, sys, json, shutil, sqlite3, importlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from app.services.elite_logger import logger, set_correlation_id
from app.config.path_manager import PathManager

HEALTH_REPORT_DIR = PathManager.get_paths()['logs'] / "reports"


class HealthCheckResult:
    def __init__(self, component: str, ok: bool, detail: str = "",
                 category: str = "General", severity: str = "medium"):
        self.component = component; self.ok = ok; self.detail = detail
        self.category = category; self.severity = severity
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict:
        return {"component": self.component, "ok": self.ok, "detail": self.detail,
                "category": self.category, "severity": self.severity, "timestamp": self.timestamp}


class SystemHealth:
    def __init__(self):
        self.results: List[HealthCheckResult] = []; self.passed = True

    def _check(self, component: str, ok: bool, detail: str = "",
               category: str = "General", severity: str = "medium"):
        self.results.append(HealthCheckResult(component, ok, detail, category, severity))
        self.passed = self.passed and ok
        logger.info(f"Health|{component}| {'OK' if ok else 'FAIL'}: {detail}")

    def check_database(self, db_path=None):
        if db_path is None:
            from app.config.path_manager import PathManager
            db_path = str(PathManager.get_paths()['db'])
        path = Path(db_path)
        if not path.exists():
            return self._check("Database SQLite", False, f"No encontrado: {db_path}", "Infraestructura", "critical")
        try:
            conn = sqlite3.connect(str(path))
            cur = conn.cursor(); cur.execute("SELECT COUNT(*) FROM sqlite_master")
            tables = cur.fetchone()[0]; conn.close()
            size_mb = path.stat().st_size / (1024*1024)
            self._check("Database SQLite", True, f"{size_mb:.1f}MB, {tables} tablas", "Infraestructura", "critical")
        except sqlite3.Error as e:
            self._check("Database SQLite", False, f"Error: {e}", "Infraestructura", "critical")

    def check_env_vars(self, required_vars=None):
        if required_vars is None: required_vars = ["OPENROUTER_API_KEY"]
        for var in required_vars:
            value = os.getenv(var); ok = bool(value)
            if var.lower().endswith(("key","secret","token")) and value:
                masked = value[:8]+"..." if len(value)>8 else "***"; detail = masked
            else: detail = "CONFIGURADA" if ok else "NO CONFIGURADA"
            self._check(f"ENV: {var}", ok, detail, "Configuracion", "critical")

    def check_disk_space(self, min_gb=0.5, paths=None):
        if paths is None: paths = [".", "logs"]
        for p in paths:
            try:
                total, used, free = shutil.disk_usage(p); free_gb = free/(1024**3); ok = free_gb >= min_gb
                detail = f"{free_gb:.2f}GB libres (min: {min_gb}GB)" if ok else f"SOLO {free_gb:.2f}GB (min: {min_gb}GB)"
                self._check(f"Disco: {p}", ok, detail, "Infraestructura", "high")
            except FileNotFoundError:
                self._check(f"Disco: {p}", False, "Ruta no encontrada", "Infraestructura", "medium")

    def check_kb_cache(self, db_path=None):
        if db_path is None:
            from app.config.path_manager import PathManager
            db_path = str(PathManager.get_paths()['db'])
        path = Path(db_path)
        if not path.exists(): return self._check("KB Cache", False, "DB no encontrada", "KnowledgeBase", "critical")
        try:
            conn = sqlite3.connect(str(path)); cur = conn.cursor()
            for table, label in [("video_sources","Fuentes"),("product_trends","Tendencias"),
                                  ("conversion_formulas","Conversion"),("operations_traffic","Trafico")]:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table}"); count = cur.fetchone()[0]
                    self._check(f"KB: {label}", True, f"{count} registros", "KnowledgeBase", "medium")
                except sqlite3.OperationalError:
                    self._check(f"KB: {label}", False, f"Tabla '{table}' no existe", "KnowledgeBase", "high")
            conn.close()
        except sqlite3.Error as e:
            self._check("KB Cache", False, f"Error: {e}", "KnowledgeBase", "critical")

    def check_modules(self, modules=None):
        if modules is None: modules = ["requests","sqlite3","json","tkinter","hashlib","pathlib"]
        for mod in modules:
            try: importlib.import_module(mod); self._check(f"Module: {mod}", True, "Disponible", "Dependencias", "low")
            except ImportError: self._check(f"Module: {mod}", False, "NO INSTALADO", "Dependencias", "high")

    def check_logs_dir(self):
        from app.config.path_manager import PathManager
        base_logs_dir = PathManager.get_paths()['logs']
        for d in [base_logs_dir, base_logs_dir/"errors", base_logs_dir/"reports", base_logs_dir/"audit"]:
            d.mkdir(parents=True, exist_ok=True); self._check(f"Dir: {d.name}", d.exists(), str(d), "Infraestructura", "low")

    def run_all(self, db_path=None, env_vars=None):
        if db_path is None:
            from app.config.path_manager import PathManager
            db_path = str(PathManager.get_paths()['db'])
        logger.info("Healthcheck| Iniciando checks...")
        self.check_logs_dir(); self.check_database(db_path); self.check_env_vars(env_vars)
        self.check_disk_space(); self.check_kb_cache(db_path); self.check_modules()
        logger.info(f"Healthcheck| OK: {sum(1 for r in self.results if r.ok)}/{len(self.results)}")
        return self

    def to_dict(self) -> Dict:
        total = len(self.results); passed = sum(1 for r in self.results if r.ok)
        score = round(passed/total*100,1) if total>0 else 0.0
        return {"timestamp":datetime.now(timezone.utc).isoformat(),"total_checks":total,
                "passed":passed,"failed":total-passed,"score":score,"global_pass":self.passed,
                "results":[r.to_dict() for r in self.results]}

    def to_json(self, path=None) -> str:
        data = self.to_dict(); js = json.dumps(data, indent=2, ensure_ascii=False)
        if path: HEALTH_REPORT_DIR.mkdir(parents=True,exist_ok=True); open(path,"w",encoding="utf-8").write(js)
        return js

    def to_html(self, path=None) -> str:
        data = self.to_dict(); rows = ""
        for r in self.results:
            icon = "✅" if r.ok else "❌"; cls = "pass" if r.ok else "fail"
            rows += f"<tr class='{cls}'><td>{icon}</td><td>{r.component}</td><td>{r.category}</td><td>{r.detail}</td></tr>\n"
        gst = "✅ ALL OK" if self.passed else "⚠️ SOME FAILED"
        html = f"""<!DOCTYPE html><html lang='es'><head><meta charset='UTF-8'><title>Healthcheck GEM OS</title>
<style>body{{font-family:'Segoe UI',sans-serif;background:#0d1117;color:#c9d1d9;padding:20px}}
h1{{color:#58a6ff;border-bottom:2px solid #30363d}}
.summary{{background:#161b22;border-radius:8px;padding:15px;margin:10px 0}}
.score{{font-size:2em;font-weight:700;color:#58a6ff}}
table{{width:100%;border-collapse:collapse;margin:15px 0}} th{{background:#21262d;color:#8b949e;padding:10px;text-align:left}}
td{{padding:8px 10px;border-bottom:1px solid #30363d}}
tr.pass td{{color:#3fb950}} tr.fail td{{color:#f85149;background:#2d1b1b}}
.footer{{color:#484f58;font-size:.85em;margin-top:20px}}</style></head>
<body><h1>🏥 GEM OS Healthcheck Report</h1>
<div class='summary'><p><strong>Host:</strong> {data.get('hostname','unknown')} | <strong>User:</strong> {data.get('user','unknown')}</p>
<p><strong>Timestamp:</strong> {data['timestamp']}</p>
<p><strong>Checks:</strong> {data['passed']}/{data['total_checks']} | <strong>Score:</strong> <span class='score'>{data['score']}%</span></p>
<p><strong>Global:</strong> <span class='{"pass" if self.passed else "fail"}'>{gst}</span></p></div>
<table><tr><th>Status</th><th>Component</th><th>Category</th><th>Detail</th></tr>{rows}</table>
<div class='footer'><p>Generated by GEM OS | Logs: logs/elite/</p></div></body></html>
"""
        if path: HEALTH_REPORT_DIR.mkdir(parents=True,exist_ok=True); open(path,"w",encoding="utf-8").write(html)
        return html

    def save_reports(self) -> Tuple[str,str]:
        HEALTH_REPORT_DIR.mkdir(parents=True,exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        jp = str(HEALTH_REPORT_DIR / f"healthcheck_{ts}.json")
        hp = str(HEALTH_REPORT_DIR / f"healthcheck_{ts}.html")
        self.to_json(jp); self.to_html(hp)
        logger.success(f"Healthcheck| Reportes: JSON={jp}, HTML={hp}")
        return jp, hp


def run_healthcheck(db_path=None, env_vars=None, save=True) -> SystemHealth:
    if db_path is None:
        from app.config.path_manager import PathManager
        db_path = str(PathManager.get_paths()['db'])
    h = SystemHealth(); h.run_all(db_path, env_vars)
    if save: h.save_reports()
    return h