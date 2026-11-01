"""
navigation.py — Sidebar colapsable + Tab Navigator profesional.
Basado en Material Design.
"""
import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Optional, Callable
from app.ui.themes.design_tokens import COLORS, TYPOGRAPHY, SPACING
from app.ui.themes.base_theme import BaseTheme


class Sidebar(ttk.Frame):
    """Sidebar colapsable con iconos + labels."""
    W = 170; CW = 48

    def __init__(self, parent, items: List[Tuple[str,str,Optional[Callable]]],
                 theme: Optional[BaseTheme] = None, **kwargs):
        super().__init__(parent, **kwargs)
        self._its = items; self._col = False; self._ai = 0
        self.configure(width=self.W, relief="flat"); self.pack_propagate(False)
        ttk.Button(self, text="☰", command=self._toggle, width=3).pack(fill=tk.X, pady=8)
        self._tl = ttk.Label(self, text="FASES", font=("Segoe UI",10,"bold"),
                             foreground=COLORS.dark_fg_secondary)
        self._tl.pack(fill=tk.X, pady=(4,8))
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=4)
        self._nf = ttk.Frame(self); self._nf.pack(fill=tk.BOTH, expand=True)
        self._bts = []
        for i,(ic,lb,_) in enumerate(items):
            b = ttk.Button(self._nf, text=f"  {ic}  {lb}", command=lambda i2=i: self._sel(i2))
            b.pack(fill=tk.X, pady=1); self._bts.append(b)
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        self._cb = ttk.Button(self, text="⚙ Configuración", command=lambda:None)
        self._cb.pack(fill=tk.X, pady=2)

    def _toggle(self):
        self._col = not self._col
        self.configure(width=self.CW if self._col else self.W)
        for i,(ic,lb,_) in enumerate(self._its):
            self._bts[i].config(text=f"  {ic}" if self._col else f"  {ic}  {lb}")
        self._cb.config(text="⚙" if self._col else "⚙ Configuración")

    def _sel(self, idx: int):
        self._ai = idx
        _,_,c = self._its[idx]
        if c: c()

    @property
    def active(self): return self._ai


class TabNavigator(ttk.Frame):
    """Navegador horizontal con indicador coloreado."""
    def __init__(self, parent, tabs: List[str],
                 theme: Optional[BaseTheme] = None,
                 active_color: str = COLORS.primary_action, **kwargs):
        super().__init__(parent, **kwargs)
        self._ts = tabs; self._ac = active_color; self._ai = 0
        self._cbs: dict = {}
        self.columnconfigure(0, weight=1)
        self._tf = ttk.Frame(self); self._tf.grid(row=0, column=0, sticky="ew")
        self._ind = tk.Frame(self, height=3, bg=self._ac)
        self._ind.grid(row=1, column=0, sticky="ew")
        self._lbls = []
        for i,tn in enumerate(tabs):
            l = ttk.Label(self._tf, text=tn, font=("Segoe UI",9,"bold"), padding=(8,4))
            l.pack(side=tk.LEFT, padx=1); l.bind("<Button-1>", lambda e,i2=i: self._sel(i2))
            self._lbls.append(l)
        self._hl(0)

    def _sel(self, idx: int):
        self._ai = idx; self._hl(idx)
        if idx in self._cbs: self._cbs[idx]()

    def _hl(self, idx: int):
        for i,l in enumerate(self._lbls):
            l.config(foreground=self._ac if i==idx else COLORS.dark_fg_secondary)
        x = sum(l.winfo_width() for l in self._lbls[:idx]) if idx>0 else 0
        if self._lbls: self._ind.place(x=x, width=self._lbls[idx].winfo_width(), height=3)

    def bind(self, idx: int, cb: Callable): self._cbs[idx] = cb

    @property
    def active(self): return self._ai