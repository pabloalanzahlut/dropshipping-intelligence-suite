"""
TiendaPanel — Shopify y AutoDS en el escritorio.

Hace lo mismo que la pantalla «Tienda» de la web y comparte con ella los datos (misma base SQLite y mismos
servicios): lo que se sincroniza aquí lo ve la web y el Agente IA de ambas.

  · Shopify: probar conexión y sincronizar pedidos/costes (API de lectura).
  · AutoDS: importar su export (CSV/Excel) para conocer el coste real de proveedor y envío.
  · Estadísticas reales y el bloque exacto que recibe el agente IA como contexto.
"""
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

from app.config.path_manager import PathManager
from app.services import autods_import, store_context, tienda_store
from app.services.shopify_client import ShopifyClient, ShopifyError, estado_credenciales
from app.ui.themes.design_tokens import DARK_BASE, NEON_COLORS, TEXT_COLORS

PERIODOS = {"7 días": 7, "30 días": 30, "60 días": 60, "90 días": 90}


def _pct(x):
    return "—" if x is None else f"{x * 100:.1f} %".replace(".", ",")


def _imp(x, moneda=""):
    return "—" if x is None else f"{x:,.2f} {moneda}".replace(",", " ").replace(".", ",").strip()


class TiendaPanel(ttk.Frame):
    """Panel de conexión y estadísticas de la tienda."""

    def __init__(self, parent, db_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.db_path = getattr(db_manager, "db_path", None) or str(PathManager.get_paths()["db"])
        self._busy = False
        self._kpis = {}
        self._build_ui()
        self.refrescar()
        self._sync_si_obsoleto()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        cab = ttk.Frame(self)
        cab.pack(fill=tk.X, padx=12, pady=(10, 4))
        ttk.Label(cab, text="🛒 Tienda — Shopify y AutoDS", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        self._estado = ttk.Label(cab, text="● Listo", foreground=NEON_COLORS["green"])
        self._estado.pack(side=tk.RIGHT)
        self._periodo = ttk.Combobox(cab, values=list(PERIODOS), state="readonly", width=9)
        self._periodo.set("30 días")
        self._periodo.bind("<<ComboboxSelected>>", lambda e: self.refrescar())
        self._periodo.pack(side=tk.RIGHT, padx=10)

        con = ttk.LabelFrame(self, text="Conexiones", padding=10)
        con.pack(fill=tk.X, padx=12, pady=4)
        self._shop_lbl = ttk.Label(con, text="", justify=tk.LEFT, wraplength=1000)
        self._shop_lbl.pack(anchor="w")
        self._autods_lbl = ttk.Label(con, text="", justify=tk.LEFT, wraplength=1000, foreground=TEXT_COLORS["secondary"])
        self._autods_lbl.pack(anchor="w", pady=(4, 8))
        fila = ttk.Frame(con)
        fila.pack(fill=tk.X)
        self._btns = [
            ttk.Button(fila, text="🔌 Probar conexión", command=self.probar),
            ttk.Button(fila, text="🔄 Sincronizar Shopify (60 días)", command=lambda: self.sincronizar(60)),
            ttk.Button(fila, text="📥 Importar export de AutoDS…", command=self.importar_autods),
            ttk.Button(fila, text="↻ Actualizar", command=self.refrescar),
        ]
        for b in self._btns:
            b.pack(side=tk.LEFT, padx=(0, 8))

        kp = ttk.LabelFrame(self, text="Estadísticas reales", padding=10)
        kp.pack(fill=tk.X, padx=12, pady=4)
        nombres = ["Pedidos", "Ingresos netos", "Ticket medio", "Cancel. + devol.", "ROAS real", "Margen real"]
        for i, n in enumerate(nombres):
            caja = tk.Frame(kp, bg=DARK_BASE["bg_card"], padx=10, pady=8)
            caja.grid(row=0, column=i, padx=4, pady=2, sticky="nsew")
            kp.columnconfigure(i, weight=1)
            tk.Label(caja, text=n, bg=DARK_BASE["bg_card"], fg=TEXT_COLORS["tertiary"], font=("Segoe UI", 8)).pack(anchor="w")
            v = tk.Label(caja, text="—", bg=DARK_BASE["bg_card"], fg=TEXT_COLORS["primary"], font=("Segoe UI", 15, "bold"))
            v.pack(anchor="w")
            s = tk.Label(caja, text="", bg=DARK_BASE["bg_card"], fg=TEXT_COLORS["disabled"], font=("Segoe UI", 8),
                         wraplength=150, justify=tk.LEFT)
            s.pack(anchor="w")
            self._kpis[n] = (v, s)

        ag = ttk.LabelFrame(self, text="Lo que ve el Agente IA (CONTEXTO TIENDA) y lo que falta", padding=10)
        ag.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 10))
        self._texto = ScrolledText(ag, wrap=tk.WORD, bg=DARK_BASE["bg_secondary"], fg=TEXT_COLORS["primary"],
                                   font=("Consolas", 10), relief=tk.FLAT, padx=10, pady=8, state=tk.DISABLED)
        self._texto.pack(fill=tk.BOTH, expand=True)

    def _dias(self) -> int:
        return PERIODOS.get(self._periodo.get(), 30)

    def _set_estado(self, texto: str, color: str):
        self._estado.config(text=texto, foreground=color)

    def _set_texto(self, texto: str):
        self._texto.config(state=tk.NORMAL)
        self._texto.delete("1.0", tk.END)
        self._texto.insert("1.0", texto)
        self._texto.config(state=tk.DISABLED)

    # ── datos ────────────────────────────────────────────────────────────────

    def refrescar(self):
        try:
            est = tienda_store.estado(self.db_path)
            r = tienda_store.resumen(self.db_path, self._dias())
            ctx = store_context.construir(self.db_path, self._dias())["texto"]
        except Exception as exc:
            self._set_estado("● Error", NEON_COLORS["pink"])
            self._set_texto(f"No se pudieron leer los datos de la tienda:\n{exc}")
            return
        sh, ad = est["shopify"], est["autods"]
        if not sh["configurada"]:
            falta = sh["aviso"] or ("Faltan en .env: " + ", ".join(sh["faltan"]))
            self._shop_lbl.config(text=f"Shopify: ⚠ falta configurar — {falta}", foreground=NEON_COLORS["yellow"])
        elif sh["ultima_ok"]:
            h = tienda_store.horas_desde(sh["ultima_ok"]["terminado_at"])
            self._shop_lbl.config(
                text=f"Shopify: ✔ {sh['tienda']} · sincronizado hace {h:g} h · {sh['pedidos_guardados']} pedidos guardados"
                     + ("  (datos de más de 24 h)" if sh["obsoleta"] else ""),
                foreground=NEON_COLORS["yellow"] if sh["obsoleta"] else NEON_COLORS["green"])
        else:
            self._shop_lbl.config(text=f"Shopify: {sh['tienda']} configurado, todavía sin sincronizar.",
                                  foreground=NEON_COLORS["yellow"])
        if ad["pedidos"] or ad["productos"]:
            self._autods_lbl.config(text=f"AutoDS: importación manual — {ad['pedidos']} líneas de pedido y "
                                         f"{ad['productos']} productos importados.")
        else:
            self._autods_lbl.config(text="AutoDS: sin importar. Su API exige aprobación y pago de activación: "
                                         "exporta Pedidos desde AutoDS (CSV/Excel) e impórtalo aquí.")
        m = r["moneda"]
        cd = r["cancelaciones_y_devoluciones"]
        mr = r["margen_real"]
        valores = {
            "Pedidos": (str(r["pedidos"]), f"{r['cancelados']} cancelados · {r['unidades']} uds", None),
            "Ingresos netos": (_imp(r["ingresos_netos"], m), f"bruto {_imp(r['ingresos_brutos'], m)}", None),
            "Ticket medio": (_imp(r["ticket_medio"], m), "ingresos netos / pedido", None),
            "Cancel. + devol.": (_pct(cd["pct_real"]), f"referencia {_pct(cd['pct_referencia'])}",
                                 NEON_COLORS["pink"] if cd["estado"] == "POR_ENCIMA" else NEON_COLORS["green"]),
            "ROAS real": (f"{r['roas_real']}×" if r["roas_real"] else "—",
                          f"{_imp(r['gasto_ads'], m)} en ads" if r["gasto_ads"] > 0 else "sin gasto en ads registrado",
                          {"RENTABLE": NEON_COLORS["green"], "AJUSTADO": NEON_COLORS["yellow"]}.get(
                              r["roas_estado"]["estado"], NEON_COLORS["pink"] if r["roas_real"] else None)),
            "Margen real": (_imp(mr["margen"], m) if mr else "—",
                            (f"{_pct(mr['margen_pct'])} · {mr['pedidos_con_coste']} de {r['pedidos']} pedidos con coste"
                             if mr else "sin coste conocido"),
                            (NEON_COLORS["green"] if mr and mr["margen"] >= 0 else NEON_COLORS["pink"]) if mr else None),
        }
        for n, (v, s, color) in valores.items():
            self._kpis[n][0].config(text=v, fg=color or TEXT_COLORS["primary"])
            self._kpis[n][1].config(text=s)
        self._set_texto(ctx or "(sin datos)")
        if not self._busy:
            self._set_estado("● Listo", NEON_COLORS["green"])

    # ── acciones en segundo plano ────────────────────────────────────────────

    def _en_hilo(self, trabajo, listo=None, mensaje="⏳ Trabajando…"):
        if self._busy:
            return
        self._busy = True
        for b in self._btns:
            b.config(state=tk.DISABLED)
        self._set_estado(mensaje, NEON_COLORS["yellow"])

        def correr():
            try:
                res, err = trabajo(), None
            except Exception as exc:                      # se muestra al usuario, no se traga
                res, err = None, exc
            self.after(0, lambda: self._terminar(res, err, listo))
        threading.Thread(target=correr, daemon=True).start()

    def _terminar(self, res, err, listo):
        self._busy = False
        for b in self._btns:
            b.config(state=tk.NORMAL)
        if err is not None:
            self._set_estado("● Error", NEON_COLORS["pink"])
            messagebox.showerror("Tienda", str(err))
        elif listo:
            listo(res)
        self.refrescar()

    def _sync_si_obsoleto(self):
        """El escritorio no tiene el planificador del servidor web: si los datos tienen más de 1 h, repone."""
        est = estado_credenciales()
        if not est["configurada"]:
            return
        ok = tienda_store.ultima_sync(self.db_path, solo_ok=True)
        h = tienda_store.horas_desde(ok["terminado_at"]) if ok else None
        if h is None or h >= 1:
            self.sincronizar(tienda_store.DIAS_SYNC_RAPIDA if ok else tienda_store.DIAS_SYNC_COMPLETA, silencioso=True)

    def probar(self):
        def listo(r):
            if r["ok"]:
                t = r["tienda"]
                messagebox.showinfo("Tienda", f"{r['mensaje']}\n\n{t['nombre']} · plan {t.get('plan') or '—'} · "
                                              f"{t['moneda']}\nPermisos: {', '.join(r['scopes'])}")
            else:
                messagebox.showwarning("Tienda", r["mensaje"])
        self._en_hilo(tienda_store.probar_conexion, listo, "⏳ Probando conexión…")

    def sincronizar(self, dias: int = 60, silencioso: bool = False):
        est = estado_credenciales()
        if not est["configurada"]:
            if not silencioso:
                messagebox.showwarning("Tienda", est["aviso"] or ("Faltan en .env: " + ", ".join(est["faltan"])))
            return

        def trabajo():
            def progreso(m):
                self.after(0, lambda: self._set_estado("⏳ " + m, NEON_COLORS["yellow"]))
            return tienda_store.sincronizar_shopify(self.db_path, ShopifyClient(), dias, progreso)

        def listo(r):
            if silencioso:
                return
            avisos = ("\n\nAvisos:\n- " + "\n- ".join(r["avisos"])) if r["avisos"] else ""
            messagebox.showinfo("Tienda", f"Sincronizado: {r['pedidos']} pedidos y {r['variantes']} variantes "
                                          f"({r['dias']} días).{avisos}")
        self._en_hilo(trabajo, listo, "⏳ Sincronizando Shopify…")

    def importar_autods(self):
        ruta = filedialog.askopenfilename(
            title="Export de AutoDS", filetypes=[("Exportaciones AutoDS", "*.csv *.tsv *.xlsx *.xlsm"), ("Todos", "*.*")])
        if not ruta:
            return
        por_unidad = messagebox.askyesno(
            "Coste por unidad",
            "¿El coste de tu export está dado POR UNIDAD?\n\nSí = por unidad (se multiplicará por la cantidad)\n"
            "No = es el total de la línea del pedido")

        moneda = (simpledialog.askstring(
            "Divisa del coste", "¿En qué divisa viene el COSTE en tu export?\n(USD para AliExpress/CJ, EUR si ya está "
            "en euros). Se convertirá a la divisa de tu tienda.", initialvalue="USD", parent=self) or "").strip().upper()
        if not moneda:
            return
        ok_sync = tienda_store.ultima_sync(self.db_path, solo_ok=True) or {}
        moneda_tienda = ok_sync.get("moneda") or "EUR"

        def trabajo():
            p = Path(ruta)
            parsed = autods_import.parsear(p.read_bytes(), p.name, "auto", por_unidad, "auto", moneda, moneda_tienda)
            return parsed, autods_import.previsualizar(self.db_path, parsed)

        def listo(res):
            parsed, v = res
            e = v["ejemplo"]
            fila = (f"{e.get('titulo') or e.get('sku')} · coste {e.get('coste')}" if v["tipo"] == "productos" else
                    f"pedido {e.get('pedido_tienda') or '(sin nº)'} · {e['fecha']} · {e['cantidad']} ud · "
                    f"coste de producto TOTAL {e['coste_proveedor']} · envío {e.get('coste_envio')}")
            conv = (f"{v['moneda_coste']} → {v['moneda_tienda']} × {v['tasa_cambio']}"
                    if v["moneda_coste"] != v["moneda_tienda"] else f"{v['moneda_coste']} (sin convertir)")
            texto = (f"Archivo: {v['archivo']} ({v['tipo']}) · costes en {conv}\n"
                     f"Filas: {v['filas']} · nuevas {v['nuevas']} · ya existentes {v['actualizadas']}\n\n"
                     "Columnas reconocidas:\n  " + "\n  ".join(f"{k} ← «{c}»" for k, c in v["columnas"].items()) +
                     (f"\n\nSin usar: {', '.join(v['sin_mapear'])}" if v["sin_mapear"] else "") +
                     f"\n\nCompruébalo con una fila que conozcas:\n  {fila}" +
                     ("\n\nAvisos:\n- " + "\n- ".join(v["avisos"]) if v["avisos"] else "") +
                     ("\n\nEste archivo ya se importó antes: no cambiará nada." if v["archivo_ya_importado"] else "") +
                     "\n\n¿Importar?")
            if not messagebox.askyesno("Importar de AutoDS", texto):
                return
            r = autods_import.aplicar(self.db_path, parsed)
            messagebox.showinfo("AutoDS", r.get("mensaje") or
                                f"Importadas {r['nuevas']} filas nuevas ({r['actualizadas']} actualizadas).")
        self._en_hilo(trabajo, listo, "⏳ Leyendo export de AutoDS…")
