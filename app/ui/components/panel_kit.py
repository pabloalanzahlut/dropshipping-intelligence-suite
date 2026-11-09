"""
panel_kit — piezas comunes para los paneles nuevos del escritorio (misma paleta que la web).

  PanelBase      marco con cabecera, línea de estado y cuerpo (opcionalmente con scroll)
  tarjeta()      tarjeta con título y contenido
  boton()        botón plano con hover
  tabla()        Treeview con barra de scroll y filas alternas  →  (marco, tree)
  llenar_tabla() reemplaza las filas de un Treeview
  KPI            tarjeta de cifra con color
  en_hilo()      ejecuta trabajo pesado fuera del hilo de Tk y devuelve el resultado con seguridad

Todo el trabajo de datos lo hacen los servicios de `app/services` (los mismos que usa la web),
así que estos paneles solo dibujan y llaman.
"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Iterable, List, Optional, Sequence, Tuple

from app.database.connection import DatabaseConnection
from app.ui.themes.design_tokens import (
    DARK_BASE, NEON_COLORS, SPACING, STATUS_COLORS, TEXT_COLORS, TYPOGRAPHY,
)

COLOR_PRIMARY = NEON_COLORS["cyan"]
COLOR_SECONDARY = NEON_COLORS["purple"]
COLOR_SUCCESS = STATUS_COLORS["success"]
COLOR_WARNING = STATUS_COLORS["warning"]
COLOR_ERROR = STATUS_COLORS["error"]
COLOR_INFO = NEON_COLORS["blue"]
BG_PRIMARY = DARK_BASE["bg_primary"]
BG_SECONDARY = DARK_BASE["bg_secondary"]
BG_TERTIARY = DARK_BASE["bg_tertiary"]
BG_CARD = DARK_BASE["bg_card"]
BORDER = DARK_BASE["bg_hover"]
TXT = TEXT_COLORS["primary"]
TXT_2 = TEXT_COLORS["secondary"]
TXT_3 = TEXT_COLORS["tertiary"]

FONT_TITLE = (TYPOGRAPHY.heading_family, 18, "bold")
FONT_SECTION = (TYPOGRAPHY.heading_family, 10, "bold")
FONT_BODY = (TYPOGRAPHY.body_family, 10)
FONT_SM = (TYPOGRAPHY.body_family, 9)
FONT_KPI = (TYPOGRAPHY.heading_family, 20, "bold")

_TIPOS = {"ok": COLOR_SUCCESS, "error": COLOR_ERROR, "aviso": COLOR_WARNING, "info": TXT_2}


def boton(parent, texto: str, comando: Optional[Callable] = None, color: str = COLOR_PRIMARY,
          texto_color: str = TXT) -> tk.Button:
    """Botón plano con efecto hover (mismo aspecto que el Dashboard)."""
    b = tk.Button(parent, text=texto, command=comando, font=FONT_SM, bg=color, fg=texto_color,
                  border=0, padx=SPACING.md, pady=SPACING.xs, activebackground=color,
                  activeforeground=texto_color, cursor="hand2", relief=tk.FLAT, highlightthickness=0,
                  disabledforeground=TXT_3)

    def _aclarar(c: str) -> str:
        try:
            h = c.lstrip("#")
            rgb = tuple(min(255, int(int(h[i:i + 2], 16) * 1.2)) for i in (0, 2, 4))
            return "#{:02x}{:02x}{:02x}".format(*rgb)
        except ValueError:
            return c

    b.bind("<Enter>", lambda e: b.config(bg=_aclarar(color)) if str(b["state"]) != "disabled" else None)
    b.bind("<Leave>", lambda e: b.config(bg=color))
    return b


def tarjeta(parent, titulo: str, acento: str = COLOR_PRIMARY, expand: bool = False,
            lado: Optional[str] = None) -> tk.Frame:
    """Tarjeta con cabecera de color. Devuelve el marco interior donde añadir contenido."""
    caja = tk.Frame(parent, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
    cab = tk.Frame(caja, bg=BG_TERTIARY)
    cab.pack(fill=tk.X)
    tk.Label(cab, text=titulo, font=FONT_SECTION, fg=acento, bg=BG_TERTIARY, anchor="w").pack(
        fill=tk.X, padx=SPACING.md, pady=SPACING.sm)
    interior = tk.Frame(caja, bg=BG_CARD)
    interior.pack(fill=tk.BOTH, expand=True, padx=SPACING.md, pady=SPACING.md)
    opciones = dict(fill=tk.BOTH if expand else tk.X, expand=expand, pady=(0, SPACING.md))
    if lado:
        opciones.update(side=lado, padx=(0, SPACING.md))
    caja.pack(**opciones)
    return interior


def etiqueta(parent, texto: str = "", tipo: str = "normal", wrap: int = 0, **kw) -> tk.Label:
    color = {"normal": TXT, "suave": TXT_2, "tenue": TXT_3, **_TIPOS}.get(tipo, TXT)
    return tk.Label(parent, text=texto, font=kw.pop("font", FONT_BODY if tipo == "normal" else FONT_SM),
                    fg=color, bg=kw.pop("bg", parent["bg"] if "bg" in parent.keys() else BG_CARD),
                    justify=tk.LEFT, anchor="w", wraplength=wrap, **kw)


def tabla(parent, columnas: Sequence[str], anchos: Optional[Sequence[int]] = None, alto: int = 8,
          alineacion: Optional[Sequence[str]] = None) -> Tuple[tk.Frame, ttk.Treeview]:
    """Treeview con scroll vertical y filas alternas. Devuelve (marco, tree)."""
    marco = tk.Frame(parent, bg=BG_CARD)
    tree = ttk.Treeview(marco, columns=list(columnas), show="headings", height=alto, selectmode="browse")
    for i, col in enumerate(columnas):
        ancho = anchos[i] if anchos and i < len(anchos) else 110
        ali = alineacion[i] if alineacion and i < len(alineacion) else "w"
        tree.heading(col, text=col, anchor=ali)
        tree.column(col, width=ancho, minwidth=50, anchor=ali, stretch=True)
    tree.tag_configure("even", background=BG_SECONDARY)
    tree.tag_configure("odd", background=BG_TERTIARY)
    tree.tag_configure("rojo", foreground=COLOR_ERROR)
    tree.tag_configure("verde", foreground=COLOR_SUCCESS)
    tree.tag_configure("ambar", foreground=COLOR_WARNING)
    barra = ttk.Scrollbar(marco, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=barra.set)
    barra.pack(side=tk.RIGHT, fill=tk.Y)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    return marco, tree


def llenar_tabla(tree: ttk.Treeview, filas: Iterable[Sequence[Any]], etiquetas: Optional[List[str]] = None) -> int:
    """Reemplaza las filas. `etiquetas[i]` añade una etiqueta de color a la fila i."""
    tree.delete(*tree.get_children())
    n = 0
    for i, fila in enumerate(filas):
        tags = ["even" if i % 2 == 0 else "odd"]
        if etiquetas and i < len(etiquetas) and etiquetas[i]:
            tags.append(etiquetas[i])
        tree.insert("", tk.END, values=["" if v is None else v for v in fila], tags=tuple(tags))
        n += 1
    return n


def importe(valor: Any, decimales: int = 2) -> str:
    """12345.6 → «12.345,60»; None → «—»."""
    if valor is None:
        return "—"
    try:
        return f"{float(valor):,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(valor)


class KPI(tk.Frame):
    """Tarjeta de cifra: título pequeño, valor grande y nota."""

    def __init__(self, parent, titulo: str, valor: str = "—", nota: str = "", color: str = TXT):
        super().__init__(parent, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        self._t = tk.Label(self, text=titulo, font=FONT_SM, fg=TXT_2, bg=BG_CARD, anchor="w")
        self._t.pack(fill=tk.X, padx=SPACING.md, pady=(SPACING.sm, 0))
        self._v = tk.Label(self, text=valor, font=FONT_KPI, fg=color, bg=BG_CARD, anchor="w")
        self._v.pack(fill=tk.X, padx=SPACING.md)
        self._n = tk.Label(self, text=nota, font=(TYPOGRAPHY.body_family, 8), fg=TXT_3, bg=BG_CARD, anchor="w")
        self._n.pack(fill=tk.X, padx=SPACING.md, pady=(0, SPACING.sm))

    def set(self, valor: str, nota: Optional[str] = None, color: Optional[str] = None) -> None:
        self._v.config(text=valor, **({"fg": color} if color else {}))
        if nota is not None:
            self._n.config(text=nota)


class MarcoDesplazable(tk.Frame):
    """Marco con scroll vertical; añade el contenido en `.interior`."""

    def __init__(self, parent, bg: str = BG_PRIMARY):
        super().__init__(parent, bg=bg)
        self._canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self._barra = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._barra.set)
        self._barra.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.interior = tk.Frame(self._canvas, bg=bg)
        self._ventana = self._canvas.create_window((0, 0), window=self.interior, anchor="nw")
        self.interior.bind("<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfigure(self._ventana, width=e.width))
        self._canvas.bind("<Enter>", lambda e: self._canvas.bind_all("<MouseWheel>", self._rueda))
        self._canvas.bind("<Leave>", lambda e: self._canvas.unbind_all("<MouseWheel>"))

    def _rueda(self, e) -> None:
        self._canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")


class PanelBase(tk.Frame):
    """Marco de panel: cabecera con título, línea de estado y cuerpo (con o sin scroll)."""

    def __init__(self, parent, db_manager: Optional[DatabaseConnection] = None, titulo: str = "",
                 subtitulo: str = "", scroll: bool = True, **kw):
        super().__init__(parent, bg=BG_PRIMARY, **kw)
        self.db_manager = db_manager or DatabaseConnection()
        cab = tk.Frame(self, bg=BG_SECONDARY)
        cab.pack(fill=tk.X)
        interior = tk.Frame(cab, bg=BG_SECONDARY)
        interior.pack(fill=tk.X, padx=SPACING.lg, pady=SPACING.md)
        izq = tk.Frame(interior, bg=BG_SECONDARY)
        izq.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(izq, text=titulo, font=FONT_TITLE, fg=TXT, bg=BG_SECONDARY, anchor="w").pack(fill=tk.X)
        if subtitulo:
            tk.Label(izq, text=subtitulo, font=FONT_SM, fg=TXT_3, bg=BG_SECONDARY, anchor="w",
                     justify=tk.LEFT, wraplength=720).pack(fill=tk.X)
        self.acciones = tk.Frame(interior, bg=BG_SECONDARY)       # botones a la derecha de la cabecera
        self.acciones.pack(side=tk.RIGHT)
        tk.Frame(self, height=1, bg=BORDER).pack(fill=tk.X)
        self._estado = tk.Label(self, text="", font=FONT_SM, fg=TXT_2, bg=BG_PRIMARY, anchor="w", justify=tk.LEFT)
        self._estado.pack(fill=tk.X, padx=SPACING.lg, pady=(SPACING.xs, 0))
        if scroll:
            self._marco = MarcoDesplazable(self)
            self._marco.pack(fill=tk.BOTH, expand=True)
            self.cuerpo = tk.Frame(self._marco.interior, bg=BG_PRIMARY)
        else:
            self.cuerpo = tk.Frame(self, bg=BG_PRIMARY)
        self.cuerpo.pack(fill=tk.BOTH, expand=True, padx=SPACING.lg, pady=SPACING.md)

    def aviso(self, texto: str, tipo: str = "info") -> None:
        """Línea de estado bajo la cabecera (ok / error / aviso / info)."""
        try:
            self._estado.config(text=texto, fg=_TIPOS.get(tipo, TXT_2))
        except tk.TclError:
            pass

    def en_hilo(self, trabajo: Callable[[], Any], al_terminar: Optional[Callable[[Any], None]] = None,
                al_fallar: Optional[Callable[[Exception], None]] = None) -> None:
        """Ejecuta `trabajo` en un hilo y entrega el resultado en el hilo de Tk (si el panel sigue vivo)."""
        def _correr() -> None:
            try:
                resultado, error = trabajo(), None
            except Exception as exc:        # noqa: BLE001 — se entrega a la interfaz
                resultado, error = None, exc

            def _entregar() -> None:
                if not self.winfo_exists():
                    return
                if error is not None:
                    (al_fallar or (lambda e: self.aviso(f"Error: {e}", "error")))(error)
                elif al_terminar:
                    al_terminar(resultado)
            try:
                self.after(0, _entregar)
            except (tk.TclError, RuntimeError):
                pass

        threading.Thread(target=_correr, daemon=True).start()

    def campo(self, parent, etiqueta_txt: str, ancho: int = 14, valor: str = "", mostrar: str = "") -> Tuple[tk.Frame, tk.StringVar, ttk.Entry]:
        """Etiqueta + entrada en vertical. Devuelve (marco, variable, entrada)."""
        marco = tk.Frame(parent, bg=parent["bg"])
        tk.Label(marco, text=etiqueta_txt, font=FONT_SM, fg=TXT_2, bg=parent["bg"], anchor="w").pack(fill=tk.X)
        var = tk.StringVar(value=valor)
        ent = ttk.Entry(marco, textvariable=var, width=ancho, show=mostrar)
        ent.pack(fill=tk.X)
        return marco, var, ent
