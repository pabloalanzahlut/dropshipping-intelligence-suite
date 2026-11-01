"""
Motor de Control de Ciclo — Ollama Startup Engine (FASE A)
============================================================
Verifica si el servicio de Ollama está corriendo en Windows.
Si no detecta el proceso levantado, intenta inicializar el
ejecutable local de Ollama en background de forma silenciosa
y realiza polling/retry hasta certificar el estado Verde.

Integración:
    Usado por HybridInferencePool._try_auto_start_ollama()
    cuando la capa 3 (Ollama Local) no está disponible.
"""

import os
import sys
import time
import logging
import subprocess
import threading
from typing import Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

OLLAMA_PORT = 11434
OLLAMA_API = f"http://127.0.0.1:{OLLAMA_PORT}"

# Rutas típicas de instalación de Ollama en Windows
OLLAMA_PATHS_WIN = [
    os.path.expandvars("%LOCALAPPDATA%\\Programs\\Ollama\\ollama.exe"),
    os.path.expandvars("%PROGRAMFILES%\\Ollama\\ollama.exe"),
    os.path.expandvars("%PROGRAMFILES(X86)%\\Ollama\\ollama.exe"),
    os.path.join(os.environ.get("USERPROFILE", ""), ".local", "bin", "ollama.exe"),
    "ollama.exe",
]

OLLAMA_PATHS_UNIX = [
    "/usr/local/bin/ollama",
    "/usr/bin/ollama",
    "ollama",
]

MAX_STARTUP_WAIT = 45  # segundos máximos esperando respuesta inicial
POLL_INTERVAL = 2       # segundos entre intentos de health-check
RETRY_BACKOFF = [1, 2, 4, 8, 15]  # backoff exponencial en segundos


class OllamaStartupEngine:
    """
    Motor que garantiza que Ollama esté operativo antes de
    que el pool híbrido intente consultarlo.

    Flujo:
        1. Verificar si el proceso ya corre (health-check HTTP).
        2. Si no, buscar el ejecutable en rutas conocidas.
        3. Lanzar el proceso en background sin ventana.
        4. Polling con backoff hasta que responda la API.
        5. Reportar éxito o fracaso.
    """

    def __init__(self, notifier: Optional[Callable[[str], None]] = None):
        self._process: Optional[subprocess.Popen] = None
        self._notifier = notifier or (lambda msg: None)
        self._startup_lock = threading.Lock()
        self._startup_in_progress = False

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def ensure_ollama_running(self) -> bool:
        """
        Asegura que Ollama esté corriendo y respondiendo.

        Returns:
            True si Ollama está operativo al finalizar.
        """
        with self._startup_lock:
            if self._startup_in_progress:
                self._notifier("[OLLAMA-ENGINE] Ya hay un intento de inicio en progreso.")
                return self._check_api_ready()

            self._startup_in_progress = True

        try:
            # Paso 1: verificar si ya corre
            if self._check_api_ready():
                self._notifier(
                    f"[OLLAMA-ENGINE] ✅ Ollama ya está corriendo (puerto {OLLAMA_PORT})"
                )
                return True

            # Paso 2: buscar ejecutable
            ollama_path = self._find_ollama_exe()
            if not ollama_path:
                self._notifier("[OLLAMA-ENGINE] ❌ Ollama no encontrado en el sistema.")
                return False

            # Paso 3: limpiar zombies previos
            zombies = self._cleanup_zombie_processes()
            if zombies:
                self._notifier(
                    f"[OLLAMA-ENGINE] 🧹 Limpiados {zombies} proceso(s) zombie(s)"
                )

            # Paso 4: iniciar proceso en background
            self._notifier(f"[OLLAMA-ENGINE] 🔄 Iniciando Ollama desde: {ollama_path}")
            success = self._launch_ollama(ollama_path)
            if not success:
                            return False

            # Paso 5: polling con backoff
            return self._poll_until_ready()

        finally:
            with self._startup_lock:
                self._startup_in_progress = False

    def is_running(self) -> bool:
        """Verificación rápida: el proceso existe y la API responde."""
        return self._check_api_ready()

    def get_status(self) -> dict:
        """Retorna un dict con el estado actual"""
        api_ok = self._check_api_ready()
        proc_alive = self._is_process_alive()
        return {
            "api_responding": api_ok,
            "process_running": api_ok or proc_alive,
            "port": OLLAMA_PORT,
            "message": "Operativo" if api_ok else (
                "Proceso lanzado sin respuesta" if proc_alive else "No iniciado"
            )
        }

    # ------------------------------------------------------------------
    # Métodos privados
    # ------------------------------------------------------------------

    def _check_api_ready(self, timeout: float = 3.0) -> bool:
        """Verifica si la API de Ollama responde en el puerto."""
        import requests
        try:
            resp = requests.get(
                f"{OLLAMA_API}/api/tags",
                timeout=timeout,
            )
            return resp.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            return False
        except Exception:
            return False

    def _find_ollama_exe(self) -> Optional[str]:
        """Busca el ejecutable de Ollama en rutas conocidas."""
        if sys.platform == "win32":
            paths = OLLAMA_PATHS_WIN
        else:
            paths = OLLAMA_PATHS_UNIX

        for path in paths:
            resolved = os.path.expandvars(path)
            if os.path.exists(resolved):
                return resolved

        # Intentar con shutil.which como fallback
        import shutil
        return shutil.which("ollama.exe") or shutil.which("ollama")

    def _cleanup_zombie_processes(self) -> int:
        """
        Detecta y mata procesos Ollama huérfanos que ocupen
        el puerto 11434 sin responder.
        """
        if sys.platform != "win32":
            self._kill_zombie_unix()
            return 0

        cleaned = 0
        try:
            output = subprocess.check_output(
                'tasklist /fi "imagename eq ollama.exe" /fo csv',
                shell=True, timeout=5,
            ).decode(errors="replace")

            for line in output.split("\n")[1:]:
                if "ollama.exe" in line.lower():
                    parts = line.split(",")
                    if len(parts) >= 2:
                        pid = parts[1].strip().strip('"')
                        try:
                            # Verificar si responde
                            import requests
                            try:
                                requests.get(f"{OLLAMA_API}/api/tags",imeout=2)
                                continue  # Responde, no matar
                            except Exception:
                                pass

                            subprocess.run(
                                ["taskkill", "/F", "/PID", pid],
                                                            capture_output=True, timeout=5,
                            )
                            cleaned += 1
                        except Exception:
                            pass
        except Exception:
            pass

        return cleaned

    def _kill_zombie_unix(self):
        """Mata procesos Ollama zombi en Unix."""
        try:
            subprocess.run(
                ["pkill", "-f", "ollama serve"],
                capture_output=True, timeout=5,
            )
        except Exception:
            pass

    def _launch_ollama(self, exe_path: str) -> bool:
        """Lanza el proceso de Ollama en background sin ventana."""
        try:
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self._process = subprocess.Popen(
                [exe_path, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            return True
        except Exception as exc:
            logger.warning(f"[OLLAMA-ENGINE] Error lanzando Ollama: {exc}")
            return False

    def _poll_until_ready(self) -> bool:
        """Polling con backoff exponencial hasta que la API responda."""
        self._notifier(
            f"[OLLAMA-ENGINE] ⏳ Esperando respuesta de Ollama "
            f"(máx. {MAX_STARTUP_WAIT}s)..."
        )

        start = time.time()
        attempt = 0

        while time.time() - start < MAX_STARTUP_WAIT:
            if self._check_api_ready():
                elapsed = time.time() - start
                self._notifier(
                    f"[OLLAMA-ENGINE] ✅ Ollama operativo en {elapsed:.1f}s"
                )
                return True

            # Backoff
            delay = RETRY_BACKOFF[attempt] if attempt < len(RETRY_BACKOFF) else 15
            time.sleep(delay)
            attempt += 1

        elapsed = time.time() - start
        self._notifier(
            f"[OLLAMA-ENGINE] ❌ Ollama no respondió tras {elapsed:.1f}s"
        )
        return False

    def _is_process_alive(self) -> bool:
        """Verifica si el proceso lanzado sigue vivo."""
        if self._process is None:
            return False
        return self._process.poll() is None

    def stop_ollama(self) -> bool:
        """Detiene el proceso de Ollama gracefulmente."""
        if self._process is None:
            return True
        try:
            self._process.terminate()
            self._process.wait(timeout=10)
            return True
        except Exception:
            try:
                self._process.kill()
                self._process.wait(timeout=5)
                return True
            except Exception:
                return False

    @staticmethod
    def launch_local_ollama_silently() -> bool:
        """
        Entry point de una linea para bootstrap/arranque silencioso.

        Crea una instancia del motor y ejecuta el ciclo completo de
        verificacion -> inicio -> polling. Ideal para llamar desde
        ``main()`` o ``bootstrap_system()`` antes de desplegar la UI.

        Returns:
            True si Ollama esta operativo al finalizar.
        """
        engine = OllamaStartupEngine()
        return engine.ensure_ollama_running()
