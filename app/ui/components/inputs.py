"""
inputs.py — Componentes de input mejorados: SearchBox, FilterCombo.
"""
import tkinter as tk
from tkinter import ttk
from typing import List, Optional, Callable
from app.ui.themes.design_tokens import TYPOGRAPHY, COLORS


class SearchBox(ttk.Frame):
    """Caja de búsqueda con icono y placeholder.
    Dispara callback en cada pulsación de tecla.
    """
    def __init__(self, parent, placeholder: str = "Buscar...",
                 on_search: Optional[Callable[[str], None]] = None,
                 width: int = 20, **kwargs):
        super().__init__(parent, **kwargs)
        self._var = tk.StringVar(value="")
        self._cb = on_search
        ttk.Label(self, text="🔍", font=(TYPOGRAPHY.body_family, 9)).pack(side=tk.LEFT, padx=(4,2))
        self._entry = ttk.Entry(self, textvariable=self._var, width=width)
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        # placeholder simulado
        self._entry.insert(0, placeholder)
        self._entry.bind("<KeyRelease>", self._on_key)

    def _on_key(self, e=None):
        if self._cb: self._cb(self._var.get())

    def get_text(self) -> str: return self._var.get()
    def set_text(self, text: str): self._var.set(text); self._entry.delete(0, tk.END); self._entry.insert(0, text)
    def clear(self): self._var.set(""); self._entry.delete(0, tk.END)


class FilterCombo(ttk.Frame):
    """Combobox de filtro con label.
    Uso: FilterCombo(parent, label="Status", options=["Todos","OK","Error"])
    """
    def __init__(self, parent, label: str = "", options: List[str] = None,
                 default: str = "", on_change: Optional[Callable[[str], None]] = None,
                 **kwargs):
        super().__init__(parent, **kwargs)
        self._cb = on_change
        if label:
            ttk.Label(self, text=label, font=(TYPOGRAPHY.body_family, 9)).pack(side=tk.LEFT, padx=(0,4))
        opts = options or ["Todos"]
        self._combo = ttk.Combobox(self, values=opts, state="readonly", width=12)
        self._combo.set(default or opts[0])
        self._combo.pack(side=tk.LEFT)
        self._combo.bind("<<ComboboxSelected>>", lambda e: self._on_change())

    def _on_change(self):
        if self._cb: self._cb(self._combo.get())

    def get(self) -> str: return self._combo.get()