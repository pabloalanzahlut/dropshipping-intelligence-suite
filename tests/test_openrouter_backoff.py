"""
test_openrouter_backoff.py — Tests unitarios para llamadas OpenRouter con backoff.
Cubre: generar_con_openrouter (CopywritingEngine) y generar_guion_con_ia (TikTokScriptGenerator).
"""
import json
import time
import unittest
from unittest.mock import MagicMock, patch, call

import requests


# ── helpers ──────────────────────────────────────────────────────────────────

def _openrouter_ok_response(text: str = "copy generado") -> MagicMock:
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = {"choices": [{"message": {"content": text}}]}
    r.raise_for_status = MagicMock()
    return r


def _openrouter_rate_limit_response() -> MagicMock:
    r = MagicMock()
    r.status_code = 429
    r.raise_for_status.side_effect = requests.HTTPError(response=r)
    return r


def _openrouter_server_error_response() -> MagicMock:
    r = MagicMock()
    r.status_code = 500
    r.raise_for_status.side_effect = requests.HTTPError(response=r)
    return r


# ── CopywritingEngine ─────────────────────────────────────────────────────────

class TestCopywritingEngineOpenRouter(unittest.TestCase):
    """Tests para el path OpenRouter directo (legacy) en CopywritingEngine."""

    def _make_engine(self):
        from app.services.copywriting_engine import CopywritingEngine
        engine = CopywritingEngine.__new__(CopywritingEngine)
        engine.openrouter_api_key = "sk-test-key"
        engine.db_manager = MagicMock()
        engine.copywriting_log = []
        engine._hybrid_pool = None
        return engine

    @patch("requests.post")
    def test_success_first_attempt(self, mock_post):
        """Respuesta 200 en el primer intento → se obtiene el texto."""
        mock_post.return_value = _openrouter_ok_response("# Título\n\nCopy OK")

        engine = self._make_engine()
        result = engine.generar_con_openrouter(
            nombre_producto="Gadget X",
            categoria="fitness",
            costo_origen=5.0,
            pvp=15.0,
            peso_kg=0.3,
        )
        self.assertIn("copy_texto", result)
        self.assertIn("Título", result["copy_texto"])
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_returns_template_on_all_failures(self, mock_post):
        """Si OpenRouter falla en todos los intentos se usa template local."""
        mock_post.side_effect = requests.ConnectionError("network error")

        engine = self._make_engine()
        result = engine.generar_con_openrouter(
            nombre_producto="Gadget X",
            categoria="fitness",
            costo_origen=5.0,
            pvp=15.0,
            peso_kg=0.3,
        )
        self.assertIn("copy_texto", result)
        # El texto de fallback existe (template local siempre genera algo)
        self.assertIsNotNone(result["copy_texto"])

    @patch("requests.post")
    def test_no_key_uses_template(self, mock_post):
        """Sin API key no llama a OpenRouter y devuelve template."""
        engine = self._make_engine()
        engine.openrouter_api_key = None

        result = engine.generar_con_openrouter(
            nombre_producto="Gadget X",
            categoria="fitness",
            costo_origen=5.0,
            pvp=15.0,
            peso_kg=0.3,
        )
        mock_post.assert_not_called()
        self.assertIn("copy_texto", result)


# ── TikTokScriptGenerator ─────────────────────────────────────────────────────

class TestTikTokScriptGeneratorOpenRouter(unittest.TestCase):
    """Tests para el path OpenRouter directo en TikTokScriptGenerator."""

    def _make_generator(self):
        from app.services.tiktok_script_generator import TikTokScriptGenerator
        gen = TikTokScriptGenerator.__new__(TikTokScriptGenerator)
        gen._hybrid_pool = None
        gen.db_manager = MagicMock()
        return gen

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-test-key"})
    @patch("requests.post")
    def test_success_first_attempt(self, mock_post):
        """Respuesta 200 → se obtiene el guión."""
        mock_post.return_value = _openrouter_ok_response("HOOK: Frase\nDEMO: Acción\nCTA: Compra")

        gen = self._make_generator()
        result = gen.generar_guion_con_ia(
            nombre_producto="Gadget X",
            categoria="fitness",
            patron_hook="problema",
            duracion_segundos=15,
        )
        self.assertIn("guion_completo", result)
        mock_post.assert_called_once()

    @patch.dict("os.environ", {}, clear=True)
    @patch("requests.post")
    def test_no_key_skips_openrouter(self, mock_post):
        """Sin OPENROUTER_API_KEY devuelve template sin llamar a la API."""
        gen = self._make_generator()
        result = gen.generar_guion_con_ia(
            nombre_producto="Gadget X",
            categoria="fitness",
            patron_hook="problema",
            duracion_segundos=15,
        )
        mock_post.assert_not_called()
        self.assertIn("guion_completo", result)

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-test-key"})
    @patch("requests.post")
    def test_returns_template_on_connection_error(self, mock_post):
        """Error de conexión → fallback a template."""
        mock_post.side_effect = requests.ConnectionError("network error")

        gen = self._make_generator()
        result = gen.generar_guion_con_ia(
            nombre_producto="Gadget X",
            categoria="fitness",
            patron_hook="problema",
            duracion_segundos=15,
        )
        self.assertIn("guion_completo", result)
        self.assertIsNotNone(result["guion_completo"])


# ── Exponential Backoff util ──────────────────────────────────────────────────

class TestExponentialBackoffUtil(unittest.TestCase):
    """Tests para la función call_openrouter_with_backoff."""

    @patch("time.sleep")
    @patch("requests.post")
    def test_retries_on_429_then_succeeds(self, mock_post, mock_sleep):
        """429 en los primeros intentos → reintenta con backoff → éxito."""
        from app.utils.openrouter_backoff import call_openrouter_with_backoff

        mock_post.side_effect = [
            _openrouter_rate_limit_response(),
            _openrouter_rate_limit_response(),
            _openrouter_ok_response("texto ok"),
        ]
        result = call_openrouter_with_backoff(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": "Bearer sk-test"},
            payload={"model": "test", "messages": []},
            max_retries=3,
        )
        self.assertEqual(result, "texto ok")
        self.assertEqual(mock_post.call_count, 3)
        # sleep llamado en los dos reintentos
        self.assertEqual(mock_sleep.call_count, 2)
        # backoff: 1s, 2s (doubles)
        mock_sleep.assert_has_calls([call(1), call(2)])

    @patch("time.sleep")
    @patch("requests.post")
    def test_raises_after_max_retries(self, mock_post, mock_sleep):
        """Agota los reintentos → lanza RuntimeError."""
        from app.utils.openrouter_backoff import call_openrouter_with_backoff

        # Siempre devuelve la misma respuesta 429
        mock_post.return_value = _openrouter_rate_limit_response()

        with self.assertRaises(RuntimeError) as ctx:
            call_openrouter_with_backoff(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={},
                payload={},
                max_retries=3,
            )
        self.assertIn("reintentos agotados", str(ctx.exception))

    @patch("time.sleep")
    @patch("requests.post")
    def test_no_retry_on_400(self, mock_post, mock_sleep):
        """Error 400 (no retryable) → falla inmediatamente, sin reintentos."""
        from app.utils.openrouter_backoff import call_openrouter_with_backoff

        bad_req = MagicMock()
        bad_req.status_code = 400
        bad_req.raise_for_status.side_effect = requests.HTTPError(response=bad_req)
        mock_post.return_value = bad_req

        with self.assertRaises(requests.HTTPError):
            call_openrouter_with_backoff(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={},
                payload={},
                max_retries=3,
            )
        mock_post.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("time.sleep")
    @patch("requests.post")
    def test_success_on_first_attempt(self, mock_post, mock_sleep):
        """Éxito inmediato → sin sleeps."""
        from app.utils.openrouter_backoff import call_openrouter_with_backoff

        mock_post.return_value = _openrouter_ok_response("first try ok")
        result = call_openrouter_with_backoff(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={},
            payload={},
        )
        self.assertEqual(result, "first try ok")
        mock_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
