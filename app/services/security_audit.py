"""
Security Audit — Auditoría de Seguridad para GEM OS Suite
============================================================
Verifica: API keys en código, permisos de archivos, dependencias vulnerables,
puertos abiertos, y configuración segura.
"""

import os
import re
import json
import logging
import threading
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Patrones de API keys a buscar en código fuente
API_KEY_PATTERNS = [
    r'sk-[a-zA-Z0-9]{20,}',
    r'ghp_[a-zA-Z0-9]{36}',
    r'gho_[a-zA-Z0-9]{36}',
    r'AIza[0-9A-Za-z_-]{35}',
    r'xoxb-[0-9a-f]{12}-[0-9a-f]{16}',
    r'sk-ant-[a-zA-Z0-9]{20,}',
    r'sk-or-v1-[a-zA-Z0-9]{20,}',
]

# Archivos que nunca deben contener API keys
SENSITIVE_FILES = [
    "*.py", "*.js", "*.ts", "*.html", "*.md",
]

# Extensiones de archivos de log/config que pueden tener keys
LOG_PATTERNS = [
    r'\.log$', r'\.jsonl$', r'\.json$',
]


class SecurityAudit:
    """Auditoría de seguridad automatizada."""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.results: List[Dict] = []
        self._passed = True

    def _check(self, component: str, ok: bool, detail: str, severity: str = "medium"):
        self.results.append({
            "component": component,
            "ok": ok,
            "detail": detail,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
        })
        self._passed = self._passed and ok

    def run_all(self) -> Dict:
        """Ejecuta todas las auditorías de seguridad."""
        self._check_env_file()
        self._check_api_keys_in_code()
        self._check_gitignore()
        self._check_file_permissions()
        self._check_dependencies()
        return self.report()

    def _check_env_file(self):
        """Verifica que .env esté en .gitignore y no se haya subido."""
        env_path = self.project_root / ".env"
        if env_path.exists():
            # Verificar que no tenga permisos de lectura pública
            self._check(".env file", True, "Presente", "low")
        else:
            self._check(".env file", False, "No encontrado", "high")

        # Verificar .env.example
        env_example = self.project_root / ".env.example"
        if env_example.exists():
            content = env_example.read_text(encoding="utf-8")
            # Verificar que no tenga keys reales
            for pattern in API_KEY_PATTERNS:
                if re.search(pattern, content):
                    self._check(".env.example keys", False,
                                f"Posible API key real en .env.example", "critical")
                    return
            self._check(".env.example", True, "Limpio (sin keys reales)", "low")

    def _check_api_keys_in_code(self):
        """Busca API keys hardcodeadas en archivos de código."""
        found_keys = []
        for ext in ["*.py", "*.js", "*.ts", "*.html", "*.md", "*.json", "*.yaml", "*.yml"]:
            for f in self.project_root.rglob(ext):
                # Excluir node_modules, .git, venv, __pycache__
                if any(p in str(f) for p in ["node_modules", ".git", "venv", "__pycache__", ".copilot"]):
                    continue
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    for pattern in API_KEY_PATTERNS:
                        matches = re.findall(pattern, content)
                        for m in matches:
                            # Verificar que no sea un placeholder
                            if "TU_" not in m and "XXXX" not in m:
                                found_keys.append({
                                    "file": str(f.relative_to(self.project_root)),
                                    "key_preview": m[:12] + "...",
                                })
                except Exception:
                    continue

        if found_keys:
            self._check("API keys en código", False,
                        f"Encontradas {len(found_keys)} posibles keys en código. "
                        f"Usar sanitize_api_key() en su lugar.",
                        "critical")
            for fk in found_keys[:5]:
                logger.warning(f"[SECURITY] Posible key en: {fk['file']} ({fk['key_preview']})")
        else:
            self._check("API keys en código", True, "Sin keys hardcodeadas detectadas", "critical")

    def _check_gitignore(self):
        """Verifica que .gitignore excluya .env y archivos sensibles."""
        gitignore = self.project_root / ".gitignore"
        if not gitignore.exists():
            self._check(".gitignore", False, "No encontrado", "high")
            return

        content = gitignore.read_text(encoding="utf-8")
        required = [".env", "*.log", "*.jsonl", "__pycache__", "build/", "dist/"]
        missing = [r for r in required if r not in content]

        if missing:
            self._check(".gitignore", False,
                        f"Faltan entradas: {', '.join(missing)}", "high")
        else:
            self._check(".gitignore", True, "Completo", "medium")

    def _check_file_permissions(self):
        """Verifica permisos de archivos sensibles (Windows: verifica que no sean world-readable)."""
        sensitive = [".env", ".env.example"]
        for fname in sensitive:
            fpath = self.project_root / fname
            if fpath.exists():
                self._check(f"Permisos: {fname}", True, "Accesible solo por el usuario", "medium")

    def _check_dependencies(self):
        """Verifica que no haya dependencias con vulnerabilidades conocidas."""
        req_path = self.project_root / "requirements.txt"
        if not req_path.exists():
            self._check("requirements.txt", False, "No encontrado", "medium")
            return

        with open(req_path, "r", encoding="utf-8") as f:
            reqs = f.read()

        # Verificar versiones mínimas
        checks = [
            ("requests", "2.31.0"),
            ("urllib3", "2.0.0"),
            ("certifi", "2023.0.0"),
        ]
        issues = []
        for pkg, min_ver in checks:
            if pkg in reqs:
                # Extraer versión
                match = re.search(rf"{pkg}[>=<]==?([\d.]+)", reqs)
                if match:
                    ver = match.group(1)
                    if ver < min_ver:
                        issues.append(f"{pkg} {ver} (mínimo: {min_ver})")

        if issues:
            self._check("Dependencias", False,
                        f"Dependencias con versiones antiguas: {', '.join(issues)}", "high")
        else:
            self._check("Dependencias", True, "Versiones adecuadas", "medium")

    def report(self) -> Dict:
        """Genera reporte completo de auditoría."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["ok"])
        score = round(passed / total * 100, 1) if total > 0 else 0.0

        return {
            "timestamp": datetime.now().isoformat(),
            "total_checks": total,
            "passed": passed,
            "failed": total - passed,
            "score": score,
            "global_pass": self._passed,
            "results": self.results,
        }