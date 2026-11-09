"""
NegocioPanel — ROAS real, caja, escalado y registro diario, igual que /negocio en la web.

Las cuentas las hacen `business_metrics` (reglas literales de los procedimientos monitorear_flujo_caja
y escalar_campana) y `metrics_import` (CSV de Meta Ads Manager / Shopify). Nada se estima en silencio.
"""
from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Optional

from app.services import business_metrics as bm
from app.services import metrics_import as mi
from app.services import product_catalog as pc
from app.ui.components.panel_kit import (
    BG_CARD, BG_TERTIARY, COLOR_ERROR, COLOR_PRIMARY, COLOR_SECONDARY, COLOR_SUCCESS, COLOR_WARNING, Dialogo,
    FONT_SM, KPI, PanelBase, TXT, TXT_2, TXT_3, boton, etiqueta, importe, llenar_tabla, tabla, tarjeta,
)

_COLOR = {"SALUDABLE": COLOR_SUCCESS, "RENTABLE": COLOR_SUCCESS, "AJUSTADO": COLOR_WARNING, "PRECAUCION": COLOR_WARNING,
          "ADVERTENCIA": COLOR_WARNING, "PERDIDA": COLOR_ERROR, "ALERTA": COLOR_ERROR, "CRITICO": COLOR_ERROR,
          "SANGRADO": COLOR_ERROR}
_SENAL = {"SALUDABLE": "🟢 Saludable", "ADVERTENCIA": "🟡 Advertencia", "CRITICO": "🔴 Crítico", "SIN_DATOS": "⚪ Sin datos suficientes"}


def _num(texto: str) -> Optional[float]:
    t = (texto or "").strip().replace(",", ".")
    return float(t) if t else None


class NegocioPanel(PanelBase):
    def __init__(self, parent, db_manager=None, **kw):
        super().__init__(parent, db_manager=db_manager, titulo="📈 Negocio · ROAS, caja y escalado",
                         subtitulo="Registra los números de cada día; el sistema calcula con las reglas de tus "
                                   "procedimientos. Nada se estima en silencio.", **kw)
        self.db = self.db_manager.db_path
        self._dias = tk.StringVar(value="7")
        self._productos: List[Dict[str, Any]] = []
        cb = ttk.Combobox(self.acciones, textvariable=self._dias, values=["7", "14", "30"], width=4, state="readonly")
        cb.pack(side=tk.LEFT)
        tk.Label(self.acciones, text="días", fg=TXT_3, bg=self.acciones["bg"], font=FONT_SM).pack(side=tk.LEFT, padx=(2, 10))
        cb.bind("<<ComboboxSelected>>", lambda e: self.cargar())
        boton(self.acciones, "📥 Importar CSV…", self._importar, COLOR_SECONDARY).pack(side=tk.LEFT, padx=4)
        boton(self.acciones, "🔄", self.cargar, BG_TERTIARY, TXT_2).pack(side=tk.LEFT)
        self._construir()
        self.cargar()

    # ── interfaz ─────────────────────────────────────────────────────────────

    def _construir(self) -> None:
        self._banner = tk.Label(self.cuerpo, text="", font=(FONT_SM[0], 12, "bold"), anchor="w", justify=tk.LEFT,
                                bg=BG_TERTIARY, fg=TXT, padx=14, pady=10, wraplength=900)
        self._banner.pack(fill=tk.X, pady=(0, 10))

        fila = tk.Frame(self.cuerpo, bg=self.cuerpo["bg"])
        fila.pack(fill=tk.X, pady=(0, 10))
        self._kpis: Dict[str, KPI] = {}
        for i, (clave, titulo) in enumerate([("roas", "ROAS real"), ("cpa", "CPA real"), ("resultado", "Resultado del periodo"),
                                             ("margen", "Margen neto"), ("caja", "Caja disponible"), ("dias_caja", "Días de caja")]):
            fila.columnconfigure(i, weight=1)
            k = KPI(fila, titulo)
            k.grid(row=0, column=i, sticky="nsew", padx=3)
            self._kpis[clave] = k

        c = tarjeta(self.cuerpo, "Ingresos y gasto en ads por día", COLOR_PRIMARY)
        self._lienzo = tk.Canvas(c, height=170, bg=BG_CARD, highlightthickness=0)
        self._lienzo.pack(fill=tk.X)
        self._lienzo.bind("<Configure>", lambda e: self._dibujar())
        self._leyenda = etiqueta(c, "■ Ingresos   ■ Gasto en ads", "tenue")
        self._leyenda.pack(anchor="w")
        self._acciones_lbl = etiqueta(c, "", "suave", wrap=900)
        self._acciones_lbl.pack(fill=tk.X, pady=(6, 0))

        # Registrar día y caja
        cols = tk.Frame(self.cuerpo, bg=self.cuerpo["bg"])
        cols.pack(fill=tk.X)
        cols.columnconfigure(0, weight=3)
        cols.columnconfigure(1, weight=2)
        izq = tarjeta(cols, "Registrar el día", COLOR_SUCCESS)
        izq.master.pack_forget()
        izq.master.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._m: Dict[str, tk.StringVar] = {}
        rejilla = tk.Frame(izq, bg=BG_CARD)
        rejilla.pack(fill=tk.X)
        campos = [("fecha", "Fecha", date.today().isoformat()), ("producto", "Producto", ""), ("plataforma", "Plataforma", "meta"),
                  ("gasto_ads", "Gasto en ads", "0"), ("ingresos", "Ingresos (Shopify)", "0"), ("pedidos", "Pedidos", "0"),
                  ("cogs_pagado", "Coste pagado al proveedor", "0"), ("devoluciones", "Devoluciones (opc.)", ""),
                  ("visitantes", "Visitantes (opc.)", ""), ("presupuesto_diario", "Presupuesto diario (opc.)", "")]
        for i, (k, t, v) in enumerate(campos):
            var = tk.StringVar(value=v)
            self._m[k] = var
            marco = tk.Frame(rejilla, bg=BG_CARD)
            marco.grid(row=i // 5, column=i % 5, sticky="ew", padx=3, pady=3)
            rejilla.columnconfigure(i % 5, weight=1)
            tk.Label(marco, text=t, font=FONT_SM, fg=TXT_2, bg=BG_CARD, anchor="w").pack(fill=tk.X)
            if k == "producto":
                self._cb_prod = ttk.Combobox(marco, textvariable=var, state="readonly", width=16)
                self._cb_prod.pack(fill=tk.X)
            elif k == "plataforma":
                ttk.Combobox(marco, textvariable=var, values=["meta", "tiktok", "shopify", "otros"], state="readonly",
                             width=10).pack(fill=tk.X)
            else:
                ttk.Entry(marco, textvariable=var, width=12).pack(fill=tk.X)
        boton(izq, "💾 Guardar día", self._guardar_dia, COLOR_SUCCESS).pack(fill=tk.X, pady=(8, 0))

        der = tarjeta(cols, "Caja de hoy", COLOR_WARNING)
        der.master.pack_forget()
        der.master.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self._c: Dict[str, tk.StringVar] = {}
        for k, t in [("saldo_cuenta", "Saldo en cuenta"), ("liberaciones_pasarela", "Liberado por pasarela"),
                     ("pagos_proveedor_pendientes", "Pagos pendientes a proveedor")]:
            var = tk.StringVar(value="0" if k != "saldo_cuenta" else "")
            self._c[k] = var
            tk.Label(der, text=t, font=FONT_SM, fg=TXT_2, bg=BG_CARD, anchor="w").pack(fill=tk.X)
            ttk.Entry(der, textvariable=var, width=18).pack(fill=tk.X, pady=(0, 6))
        boton(der, "💾 Guardar caja", self._guardar_caja, COLOR_WARNING, BG_TERTIARY).pack(fill=tk.X)

        # Escalado
        e = tarjeta(self.cuerpo, "¿Escalar una campaña?", COLOR_SECONDARY)
        fila_e = tk.Frame(e, bg=BG_CARD)
        fila_e.pack(fill=tk.X)
        self._esc_prod = tk.StringVar()
        self._cb_esc = ttk.Combobox(fila_e, textvariable=self._esc_prod, state="readonly", width=34)
        self._cb_esc.pack(side=tk.LEFT)
        self._cb_esc.bind("<<ComboboxSelected>>", lambda ev: self._evaluar())
        self._esc_res = etiqueta(e, "", "suave", wrap=900)
        self._esc_res.pack(fill=tk.X, pady=(6, 0))

        # Registros
        r = tarjeta(self.cuerpo, "Registros del periodo", COLOR_PRIMARY)
        marco, self._tree = tabla(r, ["Fecha", "Producto", "Plat.", "Gasto", "Ingresos", "Pedidos", "Coste", "Visitas"],
                                  [90, 150, 70, 80, 80, 70, 80, 70], alto=7,
                                  alineacion=["w", "w", "w", "e", "e", "e", "e", "e"])
        marco.pack(fill=tk.X)
        self._ids: List[int] = []
        boton(r, "🗑 Borrar el registro seleccionado", self._borrar, BG_TERTIARY, COLOR_ERROR).pack(anchor="w", pady=(6, 0))

    # ── datos ────────────────────────────────────────────────────────────────

    def cargar(self) -> None:
        dias = int(self._dias.get() or 7)
        r = bm.resumen(self.db, dias)
        self._serie = bm.serie_diaria(self.db, max(dias, 14))
        filas = bm.listar_metricas(self.db, dias)
        senal = r.get("senal", "SIN_DATOS")
        self._banner.config(text=f"{_SENAL.get(senal, senal)}  —  {(r.get('acciones') or [''])[0]}",
                            fg=_COLOR.get(senal, TXT))
        est_roas = (r.get("roas_estado") or {}).get("estado")
        self._kpis["roas"].set(f"{r['roas']}×" if r.get("roas") is not None else "—", est_roas or "", _COLOR.get(est_roas, TXT))
        self._kpis["cpa"].set(importe(r.get("cpa_real")), "gasto / pedidos")
        res = r.get("resultado_periodo")
        self._kpis["resultado"].set(importe(res), "ingresos − ads − coste", COLOR_SUCCESS if (res or 0) >= 0 else COLOR_ERROR)
        mn = r.get("margen_neto")
        self._kpis["margen"].set(importe(mn), "devoluciones estimadas (10,1 %)" if r.get("devoluciones_estimadas") else "con devoluciones reales",
                                 COLOR_SUCCESS if (mn or 0) >= 0 else COLOR_ERROR)
        self._kpis["caja"].set(importe(r.get("caja_disponible")), "saldo + liberaciones − pagos")
        est_caja = (r.get("caja_estado") or {}).get("estado")
        self._kpis["dias_caja"].set("—" if r.get("dias_de_caja") is None else str(r["dias_de_caja"]), est_caja or "",
                                    _COLOR.get(est_caja, TXT))
        texto = "\n".join(["• " + a for a in r.get("acciones", [])] + ["! " + h for h in r.get("datos_que_faltan", [])])
        self._acciones_lbl.config(text=texto)
        self._dibujar()

        self._productos = [p for p in pc.listar(self.db) if p["estado"] != "descartado"]
        nombres = [f"{p['nombre']} ({p['estado']})" for p in self._productos]
        self._cb_prod.config(values=["Toda la tienda"] + [p["nombre"] for p in self._productos])
        if not self._m["producto"].get():
            self._m["producto"].set("Toda la tienda")
        self._cb_esc.config(values=nombres)

        self._ids = [f["id"] for f in filas]
        llenar_tabla(self._tree, [[f["fecha"], f.get("producto") or "Tienda", f["plataforma"], importe(f["gasto_ads"]),
                                   importe(f["ingresos"]), f["pedidos"], importe(f["cogs_pagado"]), f.get("visitantes") or "—"]
                                  for f in filas])

    def _dibujar(self) -> None:
        c = self._lienzo
        c.delete("all")
        serie = getattr(self, "_serie", [])
        if not serie:
            c.create_text(12, 20, anchor="w", fill=TXT_3, font=FONT_SM, text="Sin datos todavía: registra el primer día o importa un CSV.")
            return
        ancho, alto = max(c.winfo_width(), 400), 150
        maximo = max(1.0, *(max(d["ingresos"], d["gasto_ads"]) for d in serie))
        paso = min(70, (ancho - 20) / max(1, len(serie)))
        for i, d in enumerate(serie):
            x = 12 + i * paso
            hi, hg = d["ingresos"] / maximo * (alto - 24), d["gasto_ads"] / maximo * (alto - 24)
            c.create_rectangle(x, alto - hi, x + paso * 0.32, alto, fill=COLOR_PRIMARY, outline="")
            c.create_rectangle(x + paso * 0.36, alto - hg, x + paso * 0.68, alto, fill=COLOR_ERROR, outline="")
            c.create_text(x + paso * 0.34, alto + 10, text=d["fecha"][5:], fill=TXT_3, font=(FONT_SM[0], 7))

    # ── acciones ─────────────────────────────────────────────────────────────

    def _guardar_dia(self) -> None:
        m = self._m
        try:
            nombre = m["producto"].get()
            pid = next((p["id"] for p in self._productos if p["nombre"] == nombre), None)
            datos = {"fecha": m["fecha"].get().strip(), "producto_id": pid, "plataforma": m["plataforma"].get()}
            for k in ("gasto_ads", "ingresos", "cogs_pagado", "devoluciones", "presupuesto_diario"):
                datos[k] = _num(m[k].get())
            for k in ("pedidos", "visitantes"):
                v = _num(m[k].get())
                datos[k] = None if v is None else int(v)
            bm.registrar_dia(self.db, {k: v for k, v in datos.items() if v is not None})
        except ValueError as exc:
            messagebox.showwarning("Datos no válidos", str(exc), parent=self)
            return
        self.aviso("Día guardado.", "ok")
        self.cargar()

    def _guardar_caja(self) -> None:
        try:
            bm.registrar_caja(self.db, {k: _num(v.get()) for k, v in self._c.items()})
        except ValueError as exc:
            messagebox.showwarning("Datos no válidos", str(exc), parent=self)
            return
        self.aviso("Caja guardada.", "ok")
        self.cargar()

    def _borrar(self) -> None:
        sel = self._tree.selection()
        if not sel:
            self.aviso("Elige primero un registro de la tabla.", "aviso")
            return
        if messagebox.askyesno("Borrar", "¿Borrar este registro?", parent=self):
            bm.borrar_dia(self.db, self._ids[self._tree.get_children().index(sel[0])])
            self.cargar()

    def _evaluar(self) -> None:
        idx = self._cb_esc.current()
        if idx < 0:
            return
        d = bm.evaluar_escalado(self.db, self._productos[idx])
        m = d.get("metricas") or {}
        partes = [f"Decisión: {d['decision']}" + (f" · {d['escenario']} · día {d['dia']}" if d.get("escenario") else ""), d["accion"]]
        if m.get("ventas") is not None:
            partes.append(f"Ventas {m['ventas']} · ROAS {m['roas']} · CPA {m.get('cpa_real') or '—'} / máx {m.get('cpa_max') or '—'}"
                          f" · CR {m['cr'] if m.get('cr') is not None else '—'}")
        partes += ["! " + a for a in d.get("advertencias", [])]
        self._esc_res.config(text="\n".join(partes))

    def _importar(self) -> None:
        ruta = filedialog.askopenfilename(title="CSV de Meta Ads Manager o de Shopify",
                                          filetypes=[("CSV", "*.csv"), ("Todos", "*.*")])
        if not ruta:
            return
        try:
            with open(ruta, "rb") as f:
                datos = f.read(mi.MAX_BYTES + 1)
        except OSError as exc:
            messagebox.showerror("Importar CSV", f"No se pudo leer el archivo: {exc}", parent=self)
            return
        ImportarCSVDialog(self, self.db, datos, ruta, self._productos, al_terminar=self.cargar)


class ImportarCSVDialog(Dialogo):
    """Vista previa del CSV (Meta o Shopify) y confirmación. Nada se guarda hasta pulsar «Importar»."""

    def __init__(self, padre, db: str, datos: bytes, ruta: str, productos: List[Dict[str, Any]], al_terminar=None):
        super().__init__(padre, "Importar métricas desde CSV", ancho=860)
        self.db, self.datos, self.productos, self.al_terminar = db, datos, productos, al_terminar
        self._sel: Dict[str, tk.BooleanVar] = {}
        self._prev: Optional[Dict[str, Any]] = None
        etiqueta(self.cuerpo, f"Archivo: {ruta}", "tenue", wrap=800).pack(fill=tk.X)
        fila = tk.Frame(self.cuerpo, bg=BG_CARD)
        fila.pack(fill=tk.X, pady=6)
        tk.Label(fila, text="Producto:", font=FONT_SM, fg=TXT_2, bg=BG_CARD).pack(side=tk.LEFT)
        self._prod = tk.StringVar(value="Toda la tienda")
        cb = ttk.Combobox(fila, textvariable=self._prod, state="readonly", width=28,
                          values=["Toda la tienda"] + [p["nombre"] for p in productos])
        cb.pack(side=tk.LEFT, padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self._previsualizar())
        self._meta = tk.BooleanVar(value=False)
        self._cogs = tk.BooleanVar(value=False)
        self._chk_meta = ttk.Checkbutton(self.cuerpo, variable=self._meta, command=self._previsualizar,
                                         text="Importar también las compras y el valor DECLARADOS por Meta (no son los reales)")
        self._chk_cogs = ttk.Checkbutton(self.cuerpo, variable=self._cogs, command=self._previsualizar,
                                         text="Estimar el coste pagado = pedidos × coste landed del producto (nunca pisa lo tecleado)")
        self._resumen = etiqueta(self.cuerpo, "Leyendo…", "suave", wrap=800)
        self._resumen.pack(fill=tk.X, pady=(4, 0))
        self._campanas = tk.Frame(self.cuerpo, bg=BG_CARD)
        self._campanas.pack(fill=tk.X)
        self._chk_meta.pack(anchor="w")
        self._chk_cogs.pack(anchor="w")
        marco, self._tree = tabla(self.cuerpo, ["Fecha", "Estado", "Gasto", "Ingresos", "Pedidos", "Visitas", "Coste est."],
                                  [90, 80, 80, 90, 70, 70, 80], alto=8, alineacion=["w", "w", "e", "e", "e", "e", "e"])
        marco.pack(fill=tk.BOTH, expand=True, pady=6)
        self._avisos = etiqueta(self.cuerpo, "", "aviso", wrap=800)
        self._avisos.pack(fill=tk.X)
        f = tk.Frame(self.cuerpo, bg=BG_CARD)
        f.pack(fill=tk.X, pady=(8, 0))
        self._ok = boton(f, "Importar", self._importar, COLOR_SUCCESS)
        self._ok.pack(side=tk.RIGHT)
        self._ok.config(state="disabled")
        boton(f, "Cancelar", self.destroy, BG_TERTIARY, TXT_2).pack(side=tk.RIGHT, padx=6)
        self._previsualizar(primera=True)

    def _pid(self) -> Optional[int]:
        return next((p["id"] for p in self.productos if p["nombre"] == self._prod.get()), None)

    def _campanas_elegidas(self) -> Optional[List[str]]:
        if not self._sel:
            return None
        elegidas = [n for n, v in self._sel.items() if v.get()]
        return None if len(elegidas) == len(self._sel) else elegidas

    def _previsualizar(self, primera: bool = False) -> None:
        try:
            filtro = None if primera else self._campanas_elegidas()
            if filtro is not None and not filtro:
                self._avisos.config(text="Elige al menos una campaña.")
                return
            parsed = mi.parsear(self.datos, "auto", filtro)
            prev = mi.previsualizar(self.db, parsed, self._pid(), self._meta.get(), self._cogs.get())
        except ValueError as exc:
            self._resumen.config(text="✖ " + str(exc), fg=COLOR_ERROR)
            self._ok.config(state="disabled")
            return
        self._prev = prev
        if primera or not self._sel:
            self._pintar_campanas(prev.get("campanas") or [])
        if prev["plataforma"] != "meta" or not prev.get("tiene_declarado_meta"):
            self._chk_meta.pack_forget()
        t = prev["totales"]
        resumen = (f"{'Meta Ads' if prev['plataforma'] == 'meta' else 'Shopify'} · {len(prev['dias'])} días · "
                   f"{prev['nuevos']} nuevos · {prev['actualizados']} se actualizan · "
                   + (f"gasto total {importe(t.get('gasto_ads'))}" if prev["plataforma"] == "meta"
                      else f"ingresos {importe(t.get('ingresos'))} · {t.get('pedidos', 0)} pedidos")
                   + (f" · importes en {prev['moneda']} (no se convierte)" if prev.get("moneda") else ""))
        self._resumen.config(text=resumen, fg=TXT_2)
        llenar_tabla(self._tree, [[d["fecha"], "Nuevo" if d["estado"] == "nuevo" else "Actualiza", importe(d.get("gasto_ads")) if "gasto_ads" in d else "—",
                                   importe(d.get("ingresos")) if "ingresos" in d else "—", d.get("pedidos", "—"),
                                   d.get("visitantes", "—"), importe(d.get("cogs_pagado")) if "cogs_pagado" in d else "—"]
                                  for d in prev["dias"]])
        self._avisos.config(text="\n".join("! " + a for a in prev["avisos"]))
        self._ok.config(state="normal", text=f"Importar {len(prev['dias'])} días")
        self._ajustar()

    def _pintar_campanas(self, campanas: List[Dict[str, Any]]) -> None:
        for w in self._campanas.winfo_children():
            w.destroy()
        self._sel = {}
        if len(campanas) < 2:
            return
        etiqueta(self._campanas, "Campañas a importar:", "suave").pack(anchor="w")
        for c in campanas:
            v = tk.BooleanVar(value=True)
            self._sel[c["nombre"]] = v
            ttk.Checkbutton(self._campanas, text=f"{c['nombre']}  ({importe(c['gasto'])})", variable=v,
                            command=self._previsualizar).pack(anchor="w")

    def _importar(self) -> None:
        try:
            parsed = mi.parsear(self.datos, "auto", self._campanas_elegidas())
            res = mi.aplicar(self.db, parsed, self._pid(), self._meta.get(), self._cogs.get())
        except ValueError as exc:
            messagebox.showwarning("No se pudo importar", str(exc), parent=self)
            return
        messagebox.showinfo("Importación", f"Importados {res['dias']} días ({res['nuevos']} nuevos, "
                                           f"{res['actualizados']} actualizados).", parent=self)
        if self.al_terminar:
            self.al_terminar()
        self.destroy()
