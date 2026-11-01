"""
data_table.py — Tabla interactiva mejorada con búsqueda, filtros, paginación.
"""
import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Optional
from app.ui.themes.design_tokens import TYPOGRAPHY
from app.ui.themes.base_theme import BaseTheme


class DataTable(ttk.Frame):
    """Tabla con búsqueda, ordenamiento, paginación y exportación CSV."""
    ROWS_OPT = [5, 10, 15, 25, 50]

    def __init__(self, parent, columns: List[str],
                 col_widths: Optional[List[int]] = None,
                 theme: Optional[BaseTheme] = None,
                 enable_search: bool = True, enable_export: bool = True,
                 rows_per_page: int = 10, **kwargs):
        super().__init__(parent, **kwargs)
        self._data: List[Dict] = []; self._filtered: List[Dict] = []
        self._cols = columns; self._cw = col_widths or [80]*len(columns)
        self._sv = tk.StringVar(value=""); self._page = 0; self._rpp = rows_per_page
        self._sc: Optional[int] = None; self._sr = False
        self.columnconfigure(0, weight=1); self.rowconfigure(2, weight=1)
        # Toolbar
        tb = ttk.Frame(self); tb.grid(row=0, column=0, sticky="ew", pady=(0,4))
        self._rl = ttk.Label(tb, text="0 registros", font=(TYPOGRAPHY.body_family,9))
        self._rl.pack(side=tk.RIGHT, padx=8)
        if enable_export:
            ttk.Button(tb, text="📥 CSV", command=self._export,
                       width=6).pack(side=tk.RIGHT, padx=4)
        ttk.Label(tb, text="Mostrar:", font=(TYPOGRAPHY.body_family,9)).pack(side=tk.RIGHT, padx=2)
        self._rc = ttk.Combobox(tb, values=[str(v) for v in self.ROWS_OPT],
                                width=5, state="readonly")
        self._rc.set(str(rows_per_page)); self._rc.pack(side=tk.RIGHT, padx=2)
        self._rc.bind("<<ComboboxSelected>>", lambda e: self._on_rpp())
        if enable_search:
            ttk.Label(tb, text="🔍", font=(TYPOGRAPHY.body_family,9)).pack(side=tk.LEFT, padx=(4,2))
            se = ttk.Entry(tb, textvariable=self._sv, width=18)
            se.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
            se.bind("<KeyRelease>", lambda e: self._refresh())
        # Treeview
        tf = ttk.Frame(self); tf.grid(row=2, column=0, sticky="nsew")
        tf.columnconfigure(0, weight=1); tf.rowconfigure(0, weight=1)
        self._tv = ttk.Treeview(tf, columns=self._cols, show="headings")
        self._tv.heading("#0", text=""); self._tv.column("#0", width=0, stretch=False)
        for i, c in enumerate(self._cols):
            w = self._cw[i] if i < len(self._cw) else 80
            self._tv.heading(c, text=c, command=lambda ci=i: self._sort(ci))
            self._tv.column(c, width=w, minwidth=40, anchor="center")
        sv = ttk.Scrollbar(tf, orient=tk.VERTICAL, command=self._tv.yview)
        self._tv.configure(yscrollcommand=sv.set)
        self._tv.grid(row=0, column=0, sticky="nsew"); sv.grid(row=0, column=1, sticky="ns")
        # Paginación
        pf = ttk.Frame(self); pf.grid(row=3, column=0, sticky="ew")
        self._pb = ttk.Button(pf, text="◀", command=self._prev)
        self._pb.pack(side=tk.LEFT, padx=2)
        self._pl = ttk.Label(pf, text="Pág. 0/0", font=(TYPOGRAPHY.body_family,9))
        self._pl.pack(side=tk.LEFT, padx=8)
        self._nb = ttk.Button(pf, text="▶", command=self._next)
        self._nb.pack(side=tk.LEFT, padx=2)
        self._refresh()

    # API
    def set_data(self, data: List[Dict]):
        self._data = list(data); self._refresh()

    def get_selected(self) -> List[Dict]:
        sel = self._tv.selection(); pd = self._page_data()
        return [pd[int(s.split("_")[1])] for s in sel if "_" in s and int(s.split("_")[1]) < len(pd)]

    def _refresh(self):
        q = self._sv.get().strip().lower()
        self._filtered = [r for r in self._data if not q or
                          any(q in str(v).lower() for v in r.values())]
        self._page = 0; self._render()

    def _on_rpp(self):
        try: self._rpp = int(self._rc.get())
        except: pass
        self._page = 0; self._render()

    def _page_data(self):
        s = self._page*self._rpp; return self._filtered[s:s+self._rpp]

    def _render(self):
        for i in self._tv.get_children(): self._tv.delete(i)
        pd = self._page_data(); t = len(self._filtered)
        tp = max(1, (t+self._rpp-1)//self._rpp)
        for idx, row in enumerate(pd):
            vals = [str(row.get(c, row.get(c.lower(), ""))) for c in self._cols]
            self._tv.insert("", tk.END, iid=f"r_{idx}", values=vals)
        self._rl.config(text=f"{t} registros")
        self._pl.config(text=f"Pág. {self._page+1}/{tp}")
        self._pb.config(state=tk.NORMAL if self._page>0 else tk.DISABLED)
        self._nb.config(state=tk.NORMAL if self._page<tp-1 else tk.DISABLED)

    def _next(self):
        if self._page < max(1,(len(self._filtered)+self._rpp-1)//self._rpp)-1:
            self._page += 1; self._render()

    def _prev(self):
        if self._page > 0: self._page -= 1; self._render()

    def _sort(self, ci: int):
        if self._sc == ci: self._sr = not self._sr
        else: self._sc = ci; self._sr = False
        cn = self._cols[ci]
        self._filtered.sort(key=lambda r: str(r.get(cn, r.get(cn.lower(),""))).lower(),
                            reverse=self._sr)
        self._render()

    def _export(self):
        from tkinter import filedialog, messagebox
        import csv
        p = filedialog.asksaveasfilename(defaultextension=".csv",
            filetypes=[("CSV","*.csv"),("Todos","*.*")], title="Exportar")
        if not p: return
        try:
            with open(p, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=self._cols); w.writeheader(); w.writerows(self._filtered)
        except Exception as e: messagebox.showerror("Error", str(e))