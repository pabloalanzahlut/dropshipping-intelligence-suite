"""
indicators.py — Indicadores visuales: LoadingSpinner, ProgressIndicator.
"""
import tkinter as tk
from tkinter import ttk
from typing import Optional
from app.ui.themes.design_tokens import COLORS, TYPOGRAPHY, ANIMATIONS


class LoadingSpinner(ttk.Frame):
    """Spinner animado de carga (indeterminado).
    Uso: spinner = LoadingSpinner(parent); spinner.start(); spinner.stop()
    """
    FRAMES = ["◐", "◓", "◑", "◒"]  # ciclo de spinner

    def __init__(self, parent, text: str = "Cargando...", **kwargs):
        super().__init__(parent, **kwargs)
        self._running = False
        self._frame = 0
        self._label = ttk.Label(self, text=f"{self.FRAMES[0]} {text}",
                                font=(TYPOGRAPHY.body_family, 9),
                                foreground=COLORS.info)
        self._label.pack()

    def start(self):
        self._running = True
        self._animate()

    def stop(self, final_text: str = "✅ Listo"):
        self._running = False
        self._label.config(text=final_text, foreground=COLORS.success)

    def _animate(self):
        if not self._running or not self.winfo_exists(): return
        self._frame = (self._frame + 1) % len(self.FRAMES)
        current = self._label.cget("text")
        text_part = current[1:] if len(current) > 1 else ""
        self._label.config(text=f"{self.FRAMES[self._frame]}{text_part}")
        self.after(ANIMATIONS.progress_update, self._animate)


class ProgressRing(ttk.Frame):
    """Anillo de progreso circular simulado.
    Muestra el porcentaje como texto centrado.
    """
    def __init__(self, parent, value: int = 0, max_value: int = 100,
                 size: int = 60, **kwargs):
        super().__init__(parent, width=size, height=size, **kwargs)
        self._val = value; self._max = max_value; self._size = size
        self.pack_propagate(False)
        self._label = ttk.Label(self, text=f"{int(value)}%",
                               font=(TYPOGRAPHY.body_family, 9, "bold"),
                               foreground=self._get_color())
        self._label.place(relx=0.5, rely=0.5, anchor="center")

    def _get_color(self):
        pct = self._val / max(self._max, 1) * 100
        if pct >= 100: return COLORS.success
        if pct >= 70: return COLORS.success
        if pct >= 30: return COLORS.warning
        return COLORS.info

    def set_value(self, value: int):
        self._val = max(0, min(self._max, value))
        self._label.config(text=f"{int(self._val)}%", foreground=self._get_color())