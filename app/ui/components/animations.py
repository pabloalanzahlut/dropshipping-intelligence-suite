"""
animations.py — Sistema de animaciones y microinteracciones para GEM OS v2.0
Proporciona:
- AnimatedValue: transiciones suaves de números (ej: 0 → 1234)
- ThrottledUpdater: limita actualizaciones a N por segundo (evita lag en Canvas)
- GradientDrawer: dibuja gradientes en Canvas sin CSS
- HoverTracker: maneja efectos hover en componentes (simula CSS :hover)
- PulseAnimation: efecto de pulso brillante para indicadores
"""
import tkinter as tk
from tkinter import ttk
import time
from typing import Optional, Callable, Tuple

from app.ui.themes.design_tokens import ANIMATIONS, COLORS, TYPOGRAPHY


# ═══════════════════════════════════════════════════════════════════
# ANIMATED VALUE — Transición suave de números
# ═══════════════════════════════════════════════════════════════════

class AnimatedValue:
    """Anima un número desde valor_actual hasta valor_target en N pasos.

    Args:
        widget: El widget Label cuyo texto se actualizará
        steps: Número de frames de la animación (más = más suave)
        interval: Milisegundos entre cada frame
        prefix: Texto antes del número (ej: '$')
        suffix: Texto después del número (ej: ' USD')
        formatter: Función para formatear el valor (ej: lambda v: f'{v:,}')
    """
    def __init__(self, widget: ttk.Label, steps: int = 15, interval: int = 30,
                 prefix: str = "", suffix: str = "",
                 formatter: Optional[Callable] = None):
        self.widget = widget
        self.steps = steps
        self.interval = interval
        self.prefix = prefix
        self.suffix = suffix
        self.formatter = formatter or (lambda v: str(v))
        self._current_value: float = 0
        self._running = False
        self._after_id: Optional[str] = None

    def animate(self, target_value: float):
        self._cancel()
        source = self._current_value
        diff = target_value - source
        if abs(diff) < 0.1:
            self._set_text(target_value)
            self._current_value = target_value
            return
        self._running = True
        self._step_count = 0
        self._source = source
        self._target = target_value
        self._diff = diff
        self._tick()

    def _tick(self):
        if not self._running or not self.widget.winfo_exists():
            return
        self._step_count += 1
        progress = min(1.0, self._step_count / self.steps)
        eased = progress * progress * (3 - 2 * progress)
        val = self._source + self._diff * eased
        if self._step_count >= self.steps:
            val = self._target
            self._running = False
        self._set_text(val)
        self._current_value = val
        if self._running:
            self._after_id = self.widget.after(self.interval, self._tick)

    def _set_text(self, val: float):
        try:
            formatted = self.formatter(int(round(val)))
            self.widget.config(text=f"{self.prefix}{formatted}{self.suffix}")
        except Exception:
            self.widget.config(text=f"{self.prefix}{int(val)}{self.suffix}")

    def _cancel(self):
        self._running = False
        if self._after_id:
            try:
                if self.widget.winfo_exists():
                    self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def set_immediate(self, value: float):
        self._cancel()
        self._current_value = float(value)
        self._set_text(value)


# ═══════════════════════════════════════════════════════════════════
# THROTTLED UPDATER — Limita frecuencia de actualizaciones
# ═══════════════════════════════════════════════════════════════════

class ThrottledUpdater:
    """Limita actualizaciones a máximo N por segundo.
    Útil para Canvas updates, redibujado de gráficos, etc.
    """
    def __init__(self, min_interval_ms: float = 100):
        self.min_interval = min_interval_ms / 1000.0
        self._last_update = 0.0

    def should_update(self) -> bool:
        """Returns True si ha pasado suficiente tiempo desde la última llamada."""
        now = time.time()
        if now - self._last_update >= self.min_interval:
            self._last_update = now
            return True
        return False

    def reset(self):
        self._last_update = 0.0


# ═══════════════════════════════════════════════════════════════════
# GRADIENT DRAWER — Dibuja gradientes en Canvas
# ═══════════════════════════════════════════════════════════════════

class GradientDrawer:
    """Dibuja fondos degradados en Canvas Tkinter."""
    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))  # type: ignore

    @staticmethod
    def rgb_to_hex(r: int, g: int, b: int) -> str:
        return f"#{max(0,min(255,r)):02x}{max(0,min(255,g)):02x}{max(0,min(255,b)):02x}"

    @classmethod
    def interpolate_color(cls, color1: str, color2: str, ratio: float) -> str:
        r1, g1, b1 = cls.hex_to_rgb(color1)
        r2, g2, b2 = cls.hex_to_rgb(color2)
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        return cls.rgb_to_hex(r, g, b)

    @classmethod
    def draw_vertical(cls, canvas: tk.Canvas, width: int, height: int,
                      color_start: str, color_end: str, steps: int = 20):
        for i in range(steps):
            ratio = i / steps
            y = int(height * ratio)
            h = int(height / steps) + 1
            color = cls.interpolate_color(color_start, color_end, ratio)
            canvas.create_rectangle(0, y, width, y + h, fill=color, outline="")

    @classmethod
    def draw_horizontal(cls, canvas: tk.Canvas, width: int, height: int,
                        color_start: str, color_end: str, steps: int = 20):
        for i in range(steps):
            ratio = i / steps
            x = int(width * ratio)
            w = int(width / steps) + 1
            color = cls.interpolate_color(color_start, color_end, ratio)
            canvas.create_rectangle(x, 0, x + w, height, fill=color, outline="")

    @classmethod
    def draw_bar_gradient(cls, canvas: tk.Canvas, x: int, y: int,
                           bar_width: int, bar_height: int,
                           color_start: str, color_end: str, steps: int = 10):
        for i in range(steps):
            ratio = i / steps
            by = y + int(bar_height * ratio)
            bh = int(bar_height / steps) + 1
            color = cls.interpolate_color(color_start, color_end, ratio)
            canvas.create_rectangle(x, by, x + bar_width, by + bh,
                                   fill=color, outline="")


# ═══════════════════════════════════════════════════════════════════
# HOVER TRACKER — Simula efectos CSS :hover en Tkinter
# ═══════════════════════════════════════════════════════════════════

class HoverTracker:
    """Maneja eventos hover para dar feedback visual."""
    @staticmethod
    def bind(widget, on_enter: Callable, on_leave: Callable):
        widget.bind("<Enter>", lambda e: on_enter(widget))
        widget.bind("<Leave>", lambda e: on_leave(widget))

    @staticmethod
    def bind_recursive(widget, on_enter: Callable, on_leave: Callable):
        widget.bind("<Enter>", lambda e: on_enter(widget))
        widget.bind("<Leave>", lambda e: on_leave(widget))
        try:
            for child in widget.winfo_children():
                HoverTracker.bind_recursive(child, on_enter, on_leave)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════
# PULSE ANIMATION — Efecto de pulso para indicadores
# ═══════════════════════════════════════════════════════════════════

class PulseAnimation:
    """Animación de pulso brillante para llamar la atención."""
    def __init__(self, widget: ttk.Label, color_original: str,
                 color_bright: str = "#ffffff", interval_ms: int = 800):
        self.widget = widget
        self.original = color_original
        self.bright = color_bright
        self.interval = interval_ms
        self._running = False
        self._bright_phase = False
        self._after_id = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._pulse()

    def stop(self):
        self._running = False
        if self._after_id:
            try:
                if self.widget.winfo_exists():
                    self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        try:
            self.widget.config(foreground=self.original)
        except Exception:
            pass

    def _pulse(self):
        if not self._running or not self.widget.winfo_exists():
            return
        self._bright_phase = not self._bright_phase
        color = self.bright if self._bright_phase else self.original
        try:
            self.widget.config(foreground=color)
        except Exception:
            pass
        self._after_id = self.widget.after(self.interval, self._pulse)


__all__ = [
    "AnimatedValue", "ThrottledUpdater", "GradientDrawer",
    "HoverTracker", "PulseAnimation",
]