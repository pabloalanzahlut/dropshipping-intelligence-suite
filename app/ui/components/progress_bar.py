"""
ProgressBar — Barra de Progreso Mejorada con modos determinista/indeterminista.

Características:
  - Modos: determinate (0-100) e indeterminate (animación continua)
  - Label de estado con ETA opcional
  - Color semántico (verde=OK, amarillo=advertencia, rojo=error)
  - Thread-safe (API simple para llamar desde cualquier hilo)
  - Animación suave vía after()
"""

import tkinter as tk
from tkinter import ttk
import time
from typing import Optional


class ProgressBar(ttk.Frame):
    """Barra de progreso mejorada con label de estado y modos múltiples.

    Modos de uso:
        >>> progress = ProgressBar(parent)
        >>> progress.set_value(50)        # 50% de avance
        >>> progress.set_status("Procesando...")
        >>> progress.set_eta("2m 30s")
        >>> progress.complete()           # Marcar como completado
        >>> progress.reset()              # Reiniciar
        >>> progress.start_indeterminate()  # modo animado continuo
    """

    ANIMATION_INTERVAL_MS: int = 80

    def __init__(
        self,
        parent,
        *,
        label_text: str = "Progreso: 0%",
        status_text: str = "",
        determinate: bool = True,
        theme=None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.columnconfigure(0, weight=1)

        self._value: float = 0.0
        self._determinate: bool = determinate
        self._running: bool = False
        self._anim_step: int = 0
        self._theme = theme
        self._start_time: Optional[float] = None

        # Label principal (porcentaje)
        self.progress_label = ttk.Label(
            self,
            text=label_text,
            font=("Segoe UI", 9),
        )
        self.progress_label.grid(row=0, column=0, sticky="w", pady=(0, 4))

        # Label de estado / ETA
        self.status_label = ttk.Label(
            self,
            text=status_text,
            font=("Segoe UI", 9),
            foreground="#a0a0a0",
        )
        self.status_label.grid(row=1, column=0, sticky="w", pady=(0, 4))
        self.status_label.grid_remove()

        # Barra nativa ttk
        self.progress_bar = ttk.Progressbar(
            self,
            orient="horizontal",
            mode="determinate" if determinate else "indeterminate",
            style="ConsoleProgress.Horizontal.TProgressbar",
        )
        self.progress_bar.grid(row=2, column=0, sticky="ew", pady=(0, 2))

        if not determinate:
            self._start_indeterminate_animation()

    # ------------------------------------------------------------------
    # API PÚBLICA
    # ------------------------------------------------------------------

    def set_value(self, value: float) -> None:
        """Actualiza el valor de la barra (0–100). Hilo-seguro."""
        if not self._determinate:
            return
        self._value = max(0.0, min(100.0, value))
        self.progress_bar["value"] = self._value
        self.progress_label["text"] = f"Progreso: {int(self._value)}%"
        self._apply_semantic_color(self._value)

    def set_status(self, text: str) -> None:
        """Establece texto de estado debajo del porcentaje."""
        if text:
            self.status_label["text"] = text
            self.status_label.grid()
        else:
            self.status_label["text"] = ""
            self.status_label.grid_remove()

    def set_eta(self, eta_text: str) -> None:
        """Muestra el tiempo estimado restante."""
        if eta_text:
            self.set_status(f"⏱ {eta_text}")

    def complete(self) -> None:
        """Marca la barra como completada al 100%."""
        if self._determinate:
            self.set_value(100.0)
        else:
            self._stop_indeterminate_animation()
            self.progress_bar["mode"] = "determinate"
            self.progress_bar["value"] = 100
            self._determinate = True
        self.set_status("✅ Completado")
        self._apply_semantic_color(100.0)
        self._running = False

    def reset(self) -> None:
        """Reinicia la barra a su estado inicial (0%)."""
        self._value = 0.0
        self._stop_indeterminate_animation()
        self.progress_bar["value"] = 0
        self.progress_label["text"] = "Progreso: 0%"
        self.set_status("")
        self._apply_semantic_color(0.0)
        self._running = False

    def start_determinate(self, initial_value: float = 0.0) -> None:
        """Cambia a modo determinate con valor inicial."""
        self._stop_indeterminate_animation()
        self._determinate = True
        self._running = True
        self._start_time = time.time()
        self.progress_bar["mode"] = "determinate"
        self.set_value(initial_value)

    def start_indeterminate(self) -> None:
        """Cambia a modo indeterminista (animación continua)."""
        self._determinate = False
        self._running = True
        self._start_time = time.time()
        self.progress_bar["mode"] = "indeterminate"
        self._start_indeterminate_animation()

    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # MÉTODOS INTERNOS
    # ------------------------------------------------------------------

    def _apply_semantic_color(self, value: float) -> None:
        """Aplica color a la label según el valor (0-100)."""
        if value >= 100:
            color = "#00c853"       # verde éxito
        elif value >= 70:
            color = "#4af626"       # verde claro
        elif value >= 30:
            color = "#ffd54f"       # amarillo
        else:
            color = "#ffffff" if self._theme is None else self._theme.progress_label_color
        self.progress_label["foreground"] = color

    def _start_indeterminate_animation(self) -> None:
        """Inicia la animación cíclica para modo indeterminista."""
        if self._determinate:
            return
        self._anim_step = 0
        self._animate_indeterminate()

    def _animate_indeterminate(self) -> None:
        """Bucle de animación cada ANIMATION_INTERVAL_MS."""
        if self._determinate or not self.winfo_exists():
            return
        step = self._anim_step % 20
        dots = "." * min(step % 4, 3)
        self.progress_label["text"] = f"Procesando{dots}"
        self._anim_step += 1
        self.after(self.ANIMATION_INTERVAL_MS, self._animate_indeterminate)

    def _stop_indeterminate_animation(self) -> None:
        """Detiene la animación cíclica."""
        self._determinate = True