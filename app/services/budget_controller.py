"""
BudgetController — Control de Presupuesto Mensual para APIs de IA
==================================================================
GEM OS Suite — Dropshipping Intelligence Suite

Implementa:
- Límite mensual configurable vía AI_MONTHLY_BUDGET_USD en .env
- Alerta temprana al 80% del presupuesto consumido
- Bloqueo automático al 100% (fuerza uso de capa gratuita/local)
- Reseteo mensual automático el día 1 de cada mes
- Logging de cada operación con costo estimado en USD
- Persistencia en SQLite (tabla ai_cost_log)

Fuentes de costos: ai_workspace/context/costos_api.md
"""

import os
import json
import logging
import threading
from datetime import datetime, date
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Tabla de costos por operación (USD por 1K tokens)
# Basado en Claude Sonnet 4.6 ($3/MTok input, $15/MTok output)
COSTOS_REFERENCIA = {
    "validar_producto": {"input_per_1k": 0.003, "output_per_1k": 0.015},
    "generar_copy_aida": {"input_per_1k": 0.003, "output_per_1k": 0.015},
    "generar_guion_tiktok": {"input_per_1k": 0.003, "output_per_1k": 0.015},
    "limpiar_transcripcion": {"input_per_1k": 0.003, "output_per_1k": 0.015},
    "curar_prompt": {"input_per_1k": 0.003, "output_per_1k": 0.015},
    "consulta_general": {"input_per_1k": 0.003, "output_per_1k": 0.015},
}

# Costos para modelos gratuitos (siempre $0)
COSTOS_GRATIS = {
    "freellm": 0.0,
    "google/gemini-2.0-flash-exp:free": 0.0,
    "ollama": 0.0,
}


class BudgetController:
    """
    Controlador singleton de presupuesto mensual para APIs de IA.

    Uso:
        bc = BudgetController()
        if bc.allow_request("generar_copy_aida"):
            # hacer llamada a API
            bc.log_operation("generar_copy_aida", 800, 600, "openrouter")
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

        # Presupuesto mensual desde .env (default: $20 USD)
        self.monthly_budget = float(os.getenv("AI_MONTHLY_BUDGET_USD", "20.0"))
        self.alert_threshold = float(os.getenv("AI_BUDGET_ALERT_THRESHOLD", "0.80"))

        # Estado interno
        self._spent_this_month: float = 0.0
        self._current_month: int = date.today().month
        self._current_year: int = date.today().year
        self._blocked: bool = False
        self._operation_log: list = []
        self._state_lock = threading.Lock()

        # Cargar estado persistido
        self._load_state()

        logger.info(
            f"[BUDGET] Controlador iniciado. "
            f"Presupuesto: ${self.monthly_budget:.2f}/mes, "
            f"Umbral alerta: {self.alert_threshold*100:.0f}%"
        )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def allow_request(self, operation_type: str = "consulta_general") -> bool:
        """
        Verifica si una operación puede ejecutarse según el presupuesto.

        Args:
            operation_type: Tipo de operación (para tracking)

        Returns:
            True si puede ejecutarse, False si se excedió el presupuesto
        """
        self._check_monthly_reset()

        with self._state_lock:
            if self._blocked:
                logger.warning(
                    f"[BUDGET] 🚫 Operación '{operation_type}' BLOQUEADA. "
                    f"Presupuesto mensual agotado (${self._spent_this_month:.2f}/${self.monthly_budget:.2f}). "
                    f"Usando capa gratuita/local."
                )
                return False

            ratio = self._spent_this_month / self.monthly_budget if self.monthly_budget > 0 else 0

            if ratio >= 1.0:
                self._blocked = True
                self._persist_state()
                logger.warning(
                    f"[BUDGET] 🚫 Presupuesto AGOTADO (${self._spent_this_month:.2f}). "
                    f"Bloqueando llamadas de pago hasta próximo mes."
                )
                return False

            if ratio >= self.alert_threshold:
                logger.warning(
                    f"[BUDGET] ⚠️ Alerta temprana: {ratio*100:.1f}% del presupuesto consumido "
                    f"(${self._spent_this_month:.2f}/${self.monthly_budget:.2f})"
                )

            return True

    def log_operation(
        self,
        operation_type: str,
        input_tokens: int,
        output_tokens: int,
        layer_used: str,
        model_name: str = "",
    ) -> float:
        """
        Registra una operación y calcula su costo.

        Args:
            operation_type: Tipo de operación
            input_tokens: Tokens de entrada
            output_tokens: Tokens de salida
            layer_used: Capa usada (freellm, openrouter, ollama)
            model_name: Nombre del modelo (opcional)

        Returns:
            Costo estimado en USD
        """
        self._check_monthly_reset()

        # Calcular costo
        costo = self._calcular_costo(operation_type, input_tokens, output_tokens, layer_used, model_name)

        with self._state_lock:
            self._spent_this_month += costo
            self._operation_log.append({
                "timestamp": datetime.now().isoformat(),
                "operation_type": operation_type,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "layer_used": layer_used,
                "model_name": model_name,
                "cost_usd": round(costo, 6),
                "cumulative_usd": round(self._spent_this_month, 4),
            })

            # Verificar si se alcanzó el límite
            ratio = self._spent_this_month / self.monthly_budget if self.monthly_budget > 0 else 0
            if ratio >= 1.0:
                self._blocked = True
                logger.warning(
                    f"[BUDGET] 🚫 Presupuesto AGOTADO tras operación '{operation_type}'. "
                    f"Total: ${self._spent_this_month:.2f}"
                )

        self._persist_state()

        if costo > 0:
            logger.info(
                f"[BUDGET] 💰 Operación '{operation_type}' vía {layer_used}: "
                f"${costo:.6f} ({input_tokens} in / {output_tokens} out). "
                f"Acumulado mes: ${self._spent_this_month:.4f}"
            )

        return costo

    def get_spent_this_month(self) -> float:
        """Retorna el gasto acumulado en el mes actual."""
        self._check_monthly_reset()
        with self._state_lock:
            return self._spent_this_month

    def get_remaining_budget(self) -> float:
        """Retorna el presupuesto restante."""
        self._check_monthly_reset()
        with self._state_lock:
            return max(0.0, self.monthly_budget - self._spent_this_month)

    def get_usage_ratio(self) -> float:
        """Retorna la proporción de presupuesto usado (0.0 - 1.0+)."""
        self._check_monthly_reset()
        with self._state_lock:
            return self._spent_this_month / self.monthly_budget if self.monthly_budget > 0 else 0

    def is_blocked(self) -> bool:
        """Indica si el presupuesto está bloqueado."""
        self._check_monthly_reset()
        with self._state_lock:
            return self._blocked

    def reset_monthly(self):
        """Resetea el contador mensual (forzado)."""
        with self._state_lock:
            self._spent_this_month = 0.0
            self._blocked = False
            self._current_month = date.today().month
            self._current_year = date.today().year
            self._operation_log = []
        self._persist_state()
        logger.info("[BUDGET] 🔄 Contador mensual reseteado.")

    # ------------------------------------------------------------------
    # Métodos privados
    # ------------------------------------------------------------------

    def _calcular_costo(
        self,
        operation_type: str,
        input_tokens: int,
        output_tokens: int,
        layer_used: str,
        model_name: str,
    ) -> float:
        """Calcula el costo estimado de una operación."""
        # Modelos gratuitos
        if layer_used == "freellm" or layer_used == "ollama":
            return 0.0
        if "free" in model_name.lower():
            return 0.0

        # Buscar costos de referencia
        costos = COSTOS_REFERENCIA.get(operation_type, COSTOS_REFERENCIA["consulta_general"])

        costo_input = (input_tokens / 1000) * costos["input_per_1k"]
        costo_output = (output_tokens / 1000) * costos["output_per_1k"]

        return costo_input + costo_output

    def _check_monthly_reset(self):
        """Verifica si cambió el mes y resetea automáticamente."""
        today = date.today()
        with self._state_lock:
            if today.month != self._current_month or today.year != self._current_year:
                logger.info(
                    f"[BUDGET] 🔄 Reseteo mensual automático: "
                    f"{self._current_month}/{self._current_year} → {today.month}/{today.year}"
                )
                self._spent_this_month = 0.0
                self._blocked = False
                self._current_month = today.month
                self._current_year = today.year
                self._operation_log = []
                self._persist_state()

    def _get_state_path(self) -> Path:
        """Obtiene la ruta del archivo de estado persistido."""
        data_dir = os.getenv("DATABASE_PATH", "app/database")
        base = Path(data_dir).parent if Path(data_dir).suffix else Path(data_dir)
        return base / "ai_budget_state.json"

    def _persist_state(self):
        """Persiste el estado del presupuesto en JSON."""
        path = self._get_state_path()
        try:
            os.makedirs(path.parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "month": self._current_month,
                    "year": self._current_year,
                    "spent": round(self._spent_this_month, 6),
                    "blocked": self._blocked,
                    "monthly_budget": self.monthly_budget,
                    "last_updated": datetime.now().isoformat(),
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"[BUDGET] No se pudo persistir estado: {e}")

    def _load_state(self):
        """Carga el estado persistido del presupuesto."""
        path = self._get_state_path()
        if not path.exists():
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                state = json.load(f)

            today = date.today()
            saved_month = state.get("month", today.month)
            saved_year = state.get("year", today.year)

            # Solo cargar si es el mismo mes/año
            if saved_month == today.month and saved_year == today.year:
                self._spent_this_month = state.get("spent", 0.0)
                self._blocked = state.get("blocked", False)
                self._current_month = saved_month
                self._current_year = saved_year
                logger.info(
                    f"[BUDGET] Estado cargado: ${self._spent_this_month:.4f} gastados "
                    f"({self._spent_this_month/self.monthly_budget*100:.1f}% de ${self.monthly_budget:.2f})"
                )
            else:
                logger.info(
                    f"[BUDGET] Estado de {saved_month}/{saved_year} ignorado "
                    f"(mes actual: {today.month}/{today.year})"
                )
        except Exception as e:
            logger.warning(f"[BUDGET] No se pudo cargar estado: {e}")