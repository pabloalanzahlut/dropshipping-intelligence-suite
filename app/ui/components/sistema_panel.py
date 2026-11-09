"""
SistemaPanel — alertas, resumen del día, historial/exportar, registros y mantenimiento.

Es el equivalente de la campana de alertas, el «Resumen del día», /historial y /registros de la web;
usa los mismos servicios (`alerts`, `daily_brief`, `exports`, `log_viewer`, `mantenimiento`).
"""
from __future__ import annotations

import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Optional

from app.config.path_manager import PathManager
from app.services import alerts, daily_brief, exports, log_viewer, mantenimiento
from app.ui.components.panel_kit import (
    BG_CARD, BG_PRIMARY, BG_TERTIARY, COLOR_ERROR, COLOR_PRIMARY, COLOR_SECONDARY, COLOR_SUCCESS, COLOR_WARNING,
    FONT_BODY, FONT_SM, PanelBase, TXT, TXT_2, TXT_3, boton, etiqueta, llenar_tabla, tabla,
)

_NIVEL = {"critico": ("🔴 Crítica", "rojo"), "aviso": ("🟠 Aviso", "ambar"), "info": ("🔹 Info", "")}
_TIPOS_HISTORIAL = [("productos", "Productos"), ("validaciones", "Validaciones"), ("copys", "Copys"), ("guiones", "Guiones TikTok"),
                    ("metricas", "Métricas diarias"), ("transcripciones", "Transcripciones"), ("insights", "Insights KB"),
                    ("canales", "Canales")]


class SistemaPanel(PanelBase):
    def __init__(self, parent, db_manager=None, al_cambiar_alertas=None, **kw):
        super().__init__(parent, db_manager=db_manager, titulo="🛠 Sistema",
                         subtitulo="Alertas automáticas, resumen del día, historial con exportación CSV, registros y mantenimiento.",
                         scroll=False, **kw)
        self.db = self.db_manager.db_path
        self.rutas = PathManager.get_paths()
        self._al_cambiar_alertas = al_cambiar_alertas
        self._nb = ttk.Notebook(self.cuerpo)
        self._nb.pack(fill=tk.BOTH, expand=True)
        self._pestanas: Dict[str, tk.Frame] = {}
        for clave, titulo, constructor in [("alertas", "🔔 Alertas", self._t_alertas), ("resumen", "📰 Resumen del día", self._t_resumen),
                                           ("historial", "🗃 Historial", self._t_historial), ("registros", "📜 Registros", self._t_registros),
                                           ("mantenimiento", "🧰 Mantenimiento", self._t_mantenimiento)]:
            f = tk.Frame(self._nb, bg=BG_CARD)
            self._nb.add(f, text=titulo)
            self._pestanas[clave] = f
            constructor(f)
        self.cargar_alertas()

    def mostrar_pestana(self, clave: str) -> None:
        if clave in self._pestanas:
            self._nb.select(self._pestanas[clave])

    # ── alertas ──────────────────────────────────────────────────────────────

    def _t_alertas(self, f: tk.Frame) -> None:
        barra = tk.Frame(f, bg=BG_CARD)
        barra.pack(fill=tk.X, padx=10, pady=8)
        boton(barra, "🔄 Revisar ahora", self._revisar_alertas, COLOR_PRIMARY).pack(side=tk.LEFT)
        boton(barra, "👁 Marcar todas como vistas", self._marcar_vistas, BG_TERTIARY, TXT_2).pack(side=tk.LEFT, padx=6)
        self._al_info = etiqueta(barra, "", "suave")
        self._al_info.pack(side=tk.RIGHT)
        marco, self._al_tree = tabla(f, ["Nivel", "Alerta", "Detalle", "Estado"], [90, 280, 520, 70], alto=14)
        marco.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        etiqueta(f, "Se revisan solas cada 15 minutos mientras el programa (o el servidor) está abierto. «Vista» no la "
                    "resuelve: desaparece cuando el problema deja de existir.", "tenue", wrap=900).pack(fill=tk.X, padx=10, pady=(0, 8))

    def cargar_alertas(self) -> None:
        d = alerts.listar(self.db)
        filas, etiquetas = [], []
        for a in d["items"]:
            nivel, tag = _NIVEL.get(a["nivel"], (a["nivel"], ""))
            filas.append([nivel, a["titulo"], a["detalle"], "Vista" if a["vista_at"] else "Nueva"])
            etiquetas.append(tag)
        llenar_tabla(self._al_tree, filas, etiquetas)
        self._al_info.config(text=f"{d['total_activas']} activas · {d['sin_ver']} sin ver" if d["total_activas"] else "Todo en orden")
        if self._al_cambiar_alertas:
            self._al_cambiar_alertas(d)

    def _revisar_alertas(self) -> None:
        self.aviso("Revisando…", "info")
        self.en_hilo(lambda: alerts.evaluar(self.db, str(self.rutas["config"])),
                     lambda r: (self.cargar_alertas(), self.aviso(f"Revisadas: {r['vigentes']} vigentes, {r['nuevas']} nuevas.", "ok")))

    def _marcar_vistas(self) -> None:
        alerts.marcar_vista(self.db)
        self.cargar_alertas()

    # ── resumen ──────────────────────────────────────────────────────────────

    def _t_resumen(self, f: tk.Frame) -> None:
        barra = tk.Frame(f, bg=BG_CARD)
        barra.pack(fill=tk.X, padx=10, pady=8)
        boton(barra, "🔄 Actualizar resumen", self._generar_resumen, COLOR_PRIMARY).pack(side=tk.LEFT)
        self._res_info = etiqueta(barra, "", "suave")
        self._res_info.pack(side=tk.RIGHT)
        self._texto = tk.Text(f, wrap="word", bg=BG_PRIMARY, fg=TXT, insertbackground=TXT, relief=tk.FLAT, font=("Segoe UI", 10),
                              padx=14, pady=10, height=18)
        self._texto.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self._texto.tag_configure("h1", font=("Segoe UI", 14, "bold"), foreground=COLOR_PRIMARY, spacing3=6)
        self._texto.tag_configure("h2", font=("Segoe UI", 11, "bold"), foreground=COLOR_SECONDARY, spacing1=10, spacing3=2)
        self._generar_resumen(forzar=False)

    def _generar_resumen(self, forzar: bool = True) -> None:
        cfg = str(self.rutas["config"])
        self.en_hilo((lambda: daily_brief.generar(self.db, cfg)) if forzar else
                     (lambda: daily_brief.ultimo(self.db, regenerar_si_falta=True, config_path=cfg)), self._pintar_resumen)

    def _pintar_resumen(self, r: Optional[Dict[str, Any]]) -> None:
        t = self._texto
        t.config(state="normal")
        t.delete("1.0", tk.END)
        if r:
            for linea in r["texto"].splitlines():
                if linea.startswith("# "):
                    t.insert(tk.END, linea[2:] + "\n", "h1")
                elif linea.startswith("## "):
                    t.insert(tk.END, linea[3:] + "\n", "h2")
                else:
                    t.insert(tk.END, linea + "\n")
            self._res_info.config(text=f"{r['fecha']} · generado {r['generado_at'][11:16]}")
        t.config(state="disabled")

    # ── historial ────────────────────────────────────────────────────────────

    def _t_historial(self, f: tk.Frame) -> None:
        barra = tk.Frame(f, bg=BG_CARD)
        barra.pack(fill=tk.X, padx=10, pady=8)
        self._h_tipo = tk.StringVar(value=_TIPOS_HISTORIAL[0][1])
        cb = ttk.Combobox(barra, textvariable=self._h_tipo, values=[n for _, n in _TIPOS_HISTORIAL], state="readonly", width=20)
        cb.pack(side=tk.LEFT)
        cb.bind("<<ComboboxSelected>>", lambda e: self._cargar_historial())
        self._h_buscar = tk.StringVar()
        ent = ttk.Entry(barra, textvariable=self._h_buscar, width=30)
        ent.pack(side=tk.LEFT, padx=8)
        ent.bind("<Return>", lambda e: self._cargar_historial())
        boton(barra, "Buscar", self._cargar_historial, COLOR_PRIMARY).pack(side=tk.LEFT)
        boton(barra, "⬇ Exportar CSV…", self._exportar, COLOR_SUCCESS).pack(side=tk.RIGHT)
        self._h_total = etiqueta(barra, "", "suave")
        self._h_total.pack(side=tk.RIGHT, padx=10)
        self._h_marco = tk.Frame(f, bg=BG_CARD)
        self._h_marco.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self._h_tree: Optional[ttk.Treeview] = None
        self._cargar_historial()

    def _tipo_historial(self) -> str:
        return next(k for k, n in _TIPOS_HISTORIAL if n == self._h_tipo.get())

    def _cargar_historial(self) -> None:
        tipo, buscar = self._tipo_historial(), self._h_buscar.get()
        cfg = str(self.rutas["config"])

        def listo(d: Dict[str, Any]) -> None:
            for w in self._h_marco.winfo_children():
                w.destroy()
            cols = [c["t"] for c in d["columnas"]]
            marco, self._h_tree = tabla(self._h_marco, cols, [110] * len(cols), alto=16)
            marco.pack(fill=tk.BOTH, expand=True)
            llenar_tabla(self._h_tree, [[_celda(f.get(c["k"])) for c in d["columnas"]] for f in d["filas"]])
            self._h_total.config(text=f"{len(d['filas'])} de {d['total']}")

        self.en_hilo(lambda: exports.dataset(self.db, cfg, tipo, buscar, 200, 0), listo)

    def _exportar(self) -> None:
        tipo = self._tipo_historial()
        ruta = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile=f"gemos_{tipo}_{time.strftime('%Y%m%d')}.csv", title="Exportar a CSV")
        if not ruta:
            return
        cfg, buscar = str(self.rutas["config"]), self._h_buscar.get()

        def trabajo() -> int:
            d = exports.todas_las_filas(self.db, cfg, tipo, buscar)
            with open(ruta, "wb") as fh:
                fh.write(exports.a_csv(d["columnas"], d["filas"]))
            return len(d["filas"])

        self.en_hilo(trabajo, lambda n: self.aviso(f"Exportadas {n} filas a {ruta}", "ok"))

    # ── registros ────────────────────────────────────────────────────────────

    def _t_registros(self, f: tk.Frame) -> None:
        barra = tk.Frame(f, bg=BG_CARD)
        barra.pack(fill=tk.X, padx=10, pady=8)
        self._r_fuente = tk.StringVar(value="Servidor")
        cb = ttk.Combobox(barra, textvariable=self._r_fuente, values=["Servidor", "Suite (estructurado)"], state="readonly", width=20)
        cb.pack(side=tk.LEFT)
        cb.bind("<<ComboboxSelected>>", lambda e: self._cargar_registros())
        self._r_nivel = tk.StringVar(value="")
        cn = ttk.Combobox(barra, textvariable=self._r_nivel, values=["", "INFO", "WARNING", "ERROR"], state="readonly", width=10)
        cn.pack(side=tk.LEFT, padx=6)
        cn.bind("<<ComboboxSelected>>", lambda e: self._cargar_registros())
        self._r_texto = tk.StringVar()
        ent = ttk.Entry(barra, textvariable=self._r_texto, width=26)
        ent.pack(side=tk.LEFT)
        ent.bind("<Return>", lambda e: self._cargar_registros())
        boton(barra, "🔄", self._cargar_registros, COLOR_PRIMARY).pack(side=tk.LEFT, padx=6)
        marco, self._r_tree = tabla(f, ["Hora", "Nivel", "Origen", "Mensaje"], [140, 70, 180, 640], alto=16)
        marco.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self._cargar_registros()

    def _cargar_registros(self) -> None:
        elite = self._r_fuente.get().startswith("Suite")
        ruta = self.rutas["logs"] / ("elite_suite.jsonl" if elite else "servidor.log")
        nivel, texto = self._r_nivel.get(), self._r_texto.get()

        def listo(items: List[Dict[str, Any]]) -> None:
            tags = ["rojo" if e["nivel"] in ("ERROR", "CRITICAL") else "ambar" if e["nivel"] == "WARNING" else "" for e in items]
            llenar_tabla(self._r_tree, [[e["ts"], e["nivel"], e["origen"], e["msg"]] for e in items], tags)

        self.en_hilo(lambda: log_viewer.consultar("elite" if elite else "servidor", ruta, nivel, texto, 300), listo)

    # ── mantenimiento ────────────────────────────────────────────────────────

    def _t_mantenimiento(self, f: tk.Frame) -> None:
        self._m_info = tk.Label(f, text="", font=FONT_BODY, fg=TXT, bg=BG_CARD, anchor="w", justify=tk.LEFT, wraplength=900)
        self._m_info.pack(fill=tk.X, padx=14, pady=(14, 6))
        self._m_btn = boton(f, "▶ Ejecutar mantenimiento ahora", self._ejecutar_mantenimiento, COLOR_PRIMARY)
        self._m_btn.pack(anchor="w", padx=14)
        etiqueta(f, "Comprueba la integridad de la base de datos, la optimiza, borra temporales y verifica los canales de "
                    "YouTube (≈12 s por canal). Se ejecuta solo los domingos a las 04:00 mientras el programa esté abierto.",
                 "tenue", wrap=900).pack(fill=tk.X, padx=14, pady=8)
        self._pintar_mantenimiento()

    def _pintar_mantenimiento(self) -> None:
        u = mantenimiento.ultimo(str(self.rutas["config"]))
        if not u:
            self._m_info.config(text="Aún no se ha ejecutado.", fg=TXT_2)
            return
        c = u.get("canales") or {}
        self._m_info.config(
            text=(f"Última pasada: {u['fecha'].replace('T', ' ')[:16]}\n"
                  f"Base de datos: {'íntegra' if u.get('integridad_ok') else 'CON ERRORES'}\n"
                  f"Canales revisados: {c.get('revisados', '—')} ({c.get('ok', 0)} correctos, {c.get('no_encontrado', 0)} no encontrados)\n"
                  f"Temporales borrados: {(u.get('temporales') or {}).get('borrados', '—')} · duración {u.get('duracion_s', '—')} s"
                  + ("\nErrores: " + " · ".join(u["errores"]) if u.get("errores") else "")),
            fg=COLOR_SUCCESS if u.get("integridad_ok") else COLOR_ERROR)

    def _ejecutar_mantenimiento(self) -> None:
        if mantenimiento._LOCK.locked():
            self.aviso("Ya hay un mantenimiento en curso.", "aviso")
            return
        self._m_btn.config(state="disabled", text="Ejecutando… (puede tardar varios minutos)")
        cfg = str(self.rutas["config"])

        def fin(_=None) -> None:
            self._m_btn.config(state="normal", text="▶ Ejecutar mantenimiento ahora")
            self._pintar_mantenimiento()
            self.aviso("Mantenimiento terminado.", "ok")

        self.en_hilo(lambda: mantenimiento.ejecutar(self.db, cfg), fin, lambda e: (fin(), self.aviso(f"Falló: {e}", "error")))


def _celda(v: Any) -> Any:
    if isinstance(v, bool):
        return "sí" if v else "no"
    if isinstance(v, str) and len(v) > 160:
        return v[:157] + "…"
    return v
