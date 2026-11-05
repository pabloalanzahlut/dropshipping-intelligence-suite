"""
Pool de Orquestación Híbrida — GEM OS Core (FASE A)
=====================================================
Enrutador tripartito de inferencia con prioridad inmutable:

    1. FreeLLMAPI Proxy  (Costo $0.00)        → Prioridad Élite
    2. OpenRouter API    (Llaves limitadas)    → Respaldo Cloud
    3. Ollama Local      (Sin API ni Internet) → Fallback Crítico

Principio ADD_ONLY:
    No elimina ni modifica la lógica adaptativa FreeLLMAPI existente
    en openrouter_client.py. Esta clase la extiende agregando el
    tercer escalón Ollama como fallback final.

Uso:
    pool = HybridInferencePool()
    respuesta = pool.execute_hybrid_query(
        system_prompt="...",
        user_prompt="..."
    )
"""

import os
import sys
import json
import time
import logging
import threading
from typing import Optional, Callable, Dict, Any
from datetime import datetime
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# Import tardío del controlador de presupuesto para evitar dependencias circulares
_BUDGET_CONTROLLER = None
_BUDGET_LOCK = threading.Lock()

def _get_budget_controller():
    """Singleton perezoso del BudgetController."""
    global _BUDGET_CONTROLLER
    if _BUDGET_CONTROLLER is None:
        with _BUDGET_LOCK:
            if _BUDGET_CONTROLLER is None:
                try:
                    from app.services.budget_controller import BudgetController
                    _BUDGET_CONTROLLER = BudgetController()
                except Exception as exc:
                    logger.warning(f"[HYBRID] No se pudo cargar BudgetController: {exc}")
                    _BUDGET_CONTROLLER = None
    return _BUDGET_CONTROLLER

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "qwen2.5-coder:1.5b")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_DEFAULT_MODEL = "google/gemini-2.0-flash-exp:free"

FREELLM_DEFAULT_MODEL = "qwen2.5-coder:latest"

HYBRID_TIMEOUT = int(os.getenv("HYBRID_TIMEOUT", "120"))

# ---------------------------------------------------------------------------
# Pool Singleton
# ---------------------------------------------------------------------------


class HybridInferencePool:
    """
    Pool singleton de orquestación híbrida.

    Expone el método principal ``execute_hybrid_query()`` que evalúa
    en caliente la disponibilidad de cada capa y conmuta automáticamente
    sin interrumpir el flujo de la aplicación.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True

        # --- Credenciales ---
        # FreeLLMAPI (capa 1)
        self.freellm_api_key = os.getenv("FREELLM_API_KEY", "")
        self.freellm_base_url = os.getenv("FREELLM_BASE_URL", "")
        self.freellm_model = os.getenv("FREELLM_DEFAULT_MODEL", FREELLM_DEFAULT_MODEL)

        # OpenRouter (capa 2)
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.openrouter_model = os.getenv("OPENROUTER_DEFAULT_MODEL", OPENROUTER_DEFAULT_MODEL)

        # Ollama (capa 3)
        self.ollama_base_url = OLLAMA_BASE_URL
        self.ollama_model = os.getenv("OLLAMA_DEFAULT_MODEL", OLLAMA_DEFAULT_MODEL)

        # --- Estado interno ---
        self._ollama_available: Optional[bool] = None  # None = no verificado aún
        self._last_ollama_check: float = 0.0
        self._ollama_check_interval: float = 30.0  # segundos entre health-checks
        self._active_layer: str = "none"
        self._hybrid_stats = {
            "total_queries": 0,
            "by_layer": {"freellm": 0, "openrouter": 0, "ollama": 0, "failed": 0},
            "last_query_time": None,
        }
        self._stats_lock = threading.Lock()

        logger.info(
            f"[HYBRID-POOL] Inicializado. FreeLLMAPI={'✓' if self.freellm_api_key else '✗'} "
            f"OpenRouter={'✓' if self.openrouter_api_key else '✗'} "
            f"Ollama=auto"
        )
        # Log sanitizado de API keys
        logger.info(
            f"[HYBRID-POOL] OpenRouter Key: {self._sanitize_key(self.openrouter_api_key)}, "
            f"FreeLLMAPI Key: {self._sanitize_key(self.freellm_api_key)}, "
            f"Modelo OR: {self.openrouter_model}, Modelo FreeLLM: {self.freellm_model}"
        )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def is_freellm_available(self) -> bool:
        """Capa 1: FreeLLMAPI requiere key + base URL."""
        return bool(self.freellm_api_key and self.freellm_base_url)

    def is_openrouter_available(self) -> bool:
        """Capa 2: OpenRouter solo requiere API key."""
        return bool(self.openrouter_api_key)

    def is_ollama_available(self, force_check: bool = False) -> bool:
        """
        Capa 3: Verifica disponibilidad de Ollama en localhost:11434.
        Usa caché interna con intervalo configurable.
        Si DISABLE_OLLAMA=true, siempre retorna False (modo servidor web).
        """
        if os.getenv("DISABLE_OLLAMA", "").strip().lower() == "true":
            return False
        now = time.time()
        if not force_check and self._ollama_available is not None:
            if now - self._last_ollama_check < self._ollama_check_interval:
                return self._ollama_available

        self._last_ollama_check = now
        try:
            resp = requests.get(
                f"{self.ollama_base_url}/api/tags",
                timeout=3,
            )
            self._ollama_available = resp.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            self._ollama_available = False
        except Exception as exc:
            logger.warning(f"[HYBRID-POOL] Error verificando Ollama: {exc}")
            self._ollama_available = False

        return self._ollama_available

    def get_active_layer(self) -> str:
        """Retorna la capa activa actual: 'freellm', 'openrouter', 'ollama', o 'none'."""
        return self._active_layer

    def get_hybrid_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas de uso del pool híbrido."""
        with self._stats_lock:
            return dict(self._hybrid_stats)

    def get_available_layers(self) -> Dict[str, bool]:
        """Retorna un dict con la disponibilidad de cada capa."""
        return {
            "freellm": self.is_freellm_available(),
            "openrouter": self.is_openrouter_available(),
            "ollama": self.is_ollama_available(),
        }

    @staticmethod
    def _sanitize_key(key: str) -> str:
        """Sanitiza una API key para logging, mostrando solo los últimos 4 caracteres."""
        if not key:
            return "<vacia>"
        if len(key) <= 8:
            return f"{'*' * (len(key) - 4)}{key[-4:]}"
        return f"{key[:3]}...{key[-4:]}"

    # ------------------------------------------------------------------
    # Método principal: execute_hybrid_query
    # ------------------------------------------------------------------

    def execute_hybrid_query(
        self,
        system_prompt: str,
        user_prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
            operation_type: str = "consulta_general",
        ) -> Optional[str]:
            """
            Evalúa las 3 capas en orden de prioridad y retorna la respuesta
            de la primera capa disponible.

            Args:
                system_prompt: Instrucción de sistema para el modelo.
                user_prompt: Consulta del usuario.
                stream_callback: Callback opcional para streaming (soportado solo por Ollama).
                temperature: Temperatura del modelo (0.0 - 1.0).
                max_tokens: Máximo de tokens en la respuesta.
                operation_type: Tipo de operación para control de presupuesto.

            Returns:
                Texto de respuesta, o None si todas las capas fallaron.

            Prioridad:
                1. FreeLLMAPI Proxy      → Si configurado
                2. OpenRouter API        → Si configurado
                3. Ollama Local          → Si disponible o iniciable
            """
            with self._stats_lock:
                self._hybrid_stats["total_queries"] += 1
                self._hybrid_stats["last_query_time"] = datetime.now().isoformat()

            # Verificar presupuesto antes de intentar capas de pago
            budget = _get_budget_controller()
            if budget and not budget.allow_request(operation_type):
                logger.info("[HYBRID] Presupuesto agotado. Saltando capas de pago, yendo a Ollama/local...")
                # Ir directamente a capa gratuita
                return self._try_ollama_fallback(system_prompt, user_prompt, stream_callback, temperature, max_tokens)

            # --- Capa 1: FreeLLMAPI (Costo $0) ---
            if self.is_freellm_available():
                logger.info("[HYBRID] → Capa 1: FreeLLMAPI Proxy")
                self._active_layer = "freellm"
                result = self._query_freellm(
                    system_prompt, user_prompt, temperature, max_tokens
                )
                if result is not None:
                    with self._stats_lock:
                        self._hybrid_stats["by_layer"]["freellm"] += 1
                    # Log de costo (gratuito)
                    if budget:
                        budget.log_operation(operation_type, len(system_prompt) // 4, len(result) // 4, "freellm", "freellm-proxy")
                    return result
                logger.warning("[HYBRID] FreeLLMAPI falló. Conmutando a Capa 2...")

            # --- Capa 2: OpenRouter API ---
            if self.is_openrouter_available():
                logger.info("[HYBRID] → Capa 2: OpenRouter Cloud")
                self._active_layer = "openrouter"
                result = self._query_openrouter(
                    system_prompt, user_prompt, temperature, max_tokens
                )
                if result is not None:
                    with self._stats_lock:
                        self._hybrid_stats["by_layer"]["openrouter"] += 1
                    # Log de costo
                    if budget:
                        budget.log_operation(
                            operation_type,
                            len(system_prompt) // 4,
                            len(result) // 4,
                            "openrouter",
                            self.openrouter_model,
                        )
                    return result
                logger.warning("[HYBRID] OpenRouter falló. Conmutando a Capa 3...")

            # --- Capa 3: Ollama Local ---
            return self._try_ollama_fallback(system_prompt, user_prompt, stream_callback, temperature, max_tokens, operation_type)


    def _try_ollama_fallback(
        self,
        system_prompt: str,
        user_prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        operation_type: str = "consulta_general",
    ) -> Optional[str]:
        """Intenta usar Ollama como fallback, con auto-inicio si es necesario."""
        if not self.is_ollama_available():
            logger.info("[HYBRID] Ollama no disponible. Intentando auto-inicio...")
            self._try_auto_start_ollama()

        if self.is_ollama_available(force_check=True):
            logger.info("[HYBRID] → Capa 3: Ollama Local")
            self._active_layer = "ollama"
            result = self._query_ollama(
                system_prompt, user_prompt, stream_callback, temperature, max_tokens
            )
            if result is not None:
                with self._stats_lock:
                    self._hybrid_stats["by_layer"]["ollama"] += 1
                # Log de costo (gratuito)
                budget = _get_budget_controller()
                if budget:
                    budget.log_operation(operation_type, len(system_prompt) // 4, len(result) // 4, "ollama", "ollama-local")
                return result
            logger.warning("[HYBRID] Ollama falló.")

        # --- Todas las capas fallaron ---
        self._active_layer = "none"
        with self._stats_lock:
            self._hybrid_stats["by_layer"]["failed"] += 1
        logger.error("[HYBRID] ❌ Todas las capas de inferencia fallaron.")
        return None

    # ------------------------------------------------------------------
    # Métodos privados de consulta por capa
    # ------------------------------------------------------------------

    def _query_freellm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> Optional[str]:
        """Consulta a FreeLLMAPI Proxy."""
        headers = {
            "Authorization": f"Bearer {self.freellm_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com",
        }
        payload = {
            "model": self.freellm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            resp = requests.post(
                self.freellm_base_url,
                headers=headers,
                json=payload,
                timeout=HYBRID_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.warning(f"[HYBRID] FreeLLMAPI error: {exc}")
            return None

    def _query_openrouter(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> Optional[str]:
        """Consulta a OpenRouter API."""
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com",
        }
        payload = {
            "model": self.openrouter_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            resp = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=HYBRID_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.warning(f"[HYBRID] OpenRouter error: {exc}")
            return None

    def _query_ollama(
        self,
        system_prompt: str,
        user_prompt: str,
        stream_callback: Optional[Callable[[str], None]],
        temperature: float,
        max_tokens: int,
    ) -> Optional[str]:
        """Consulta a Ollama local con soporte opcional de streaming."""
        url = f"{self.ollama_base_url}/api/chat"
        payload = {
            "model": self.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "stream": stream_callback is not None,
        }
        try:
            if stream_callback:
                return self._query_ollama_stream(url, payload, stream_callback)

            resp = requests.post(url, json=payload, timeout=HYBRID_TIMEOUT)
            resp.raise_for_status()
            return resp.json()["message"]["content"].strip()

        except Exception as exc:
            logger.warning(f"[HYBRID] Ollama error: {exc}")
            return None

    def _query_ollama_stream(
        self,
        url: str,
        payload: Dict[str, Any],
        stream_callback: Callable[[str], None],
    ) -> Optional[str]:
        """Consulta a Ollama con streaming y callback por chunk."""
        full_content: list[str] = []
        try:
            with requests.post(url, json=payload, stream=True, timeout=HYBRID_TIMEOUT) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            full_content.append(content)
                            stream_callback(content)
                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
            return "".join(full_content)
        except Exception as exc:
            logger.warning(f"[HYBRID] Ollama streaming error: {exc}")
            return None

    # ------------------------------------------------------------------
    # Auto-incio de Ollama (delegado al startup engine)
    # ------------------------------------------------------------------

    def _try_auto_start_ollama(self) -> bool:
        """Intenta iniciar Ollama usando el motor de control de ciclo."""
        try:
            from app.core.ollama_startup_engine import OllamaStartupEngine

            engine = OllamaStartupEngine()
            return engine.ensure_ollama_running()
        except Exception as exc:
            logger.warning(f"[HYBRID] Auto-inicio Ollama falló: {exc}")
            return False
