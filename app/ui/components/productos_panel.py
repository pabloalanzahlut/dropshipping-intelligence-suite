"""
ProductosPanel — el recorrido de cada producto, igual que /productos en la web.

candidato → clasificado → refutado → validado → creativo → tienda → escalado | descartado

Cada paso comprueba datos reales (no se puede saltar ninguno) y lo hace `app.services.product_catalog`:
aquí solo se dibuja, se piden los datos y se muestra por qué un paso no está permitido.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, List, Optional

from app.services import business_metrics, product_catalog as pc
from app.ui.components.panel_kit import (
    Dialogo, BG_CARD, BG_TERTIARY, COLOR_ERROR, COLOR_PRIMARY, COLOR_SECONDARY, COLOR_SUCCESS, COLOR_WARNING,
    FONT_BODY, FONT_SECTION, FONT_SM, PanelBase, TXT, TXT_2, TXT_3, boton, etiqueta, importe, llenar_tabla,
    tabla, tarjeta,
)

_COLOR_ESTADO = {"candidato": TXT_2, "clasificado": COLOR_PRIMARY, "refutado": COLOR_SECONDARY, "validado": COLOR_SUCCESS,
                 "creativo": COLOR_SUCCESS, "tienda": COLOR_WARNING, "escalado": COLOR_SUCCESS, "descartado": COLOR_ERROR}
_COLOR_CLASIF = {"HOT": COLOR_SUCCESS, "WARM": COLOR_WARNING, "COLD": COLOR_PRIMARY, "DISCARD": COLOR_ERROR}


class ProductosPanel(PanelBase):
    def __init__(self, parent, db_manager=None, **kw):
        super().__init__(parent, db_manager=db_manager, titulo="📦 Productos",
                         subtitulo="Cada producto recorre el mismo camino y no se puede saltar ningún paso: "
                                   "clasificar → refutar → validar → creativo → tienda → escalar.", scroll=False, **kw)
        self.db = self.db_manager.db_path
        self._sel: Optional[int] = None
        self._ids: List[int] = []
        boton(self.acciones, "＋ Nuevo producto", self._nuevo, COLOR_SUCCESS).pack(side=tk.LEFT, padx=4)
        boton(self.acciones, "🔄", self.cargar, BG_TERTIARY, TXT_2).pack(side=tk.LEFT)
        self._construir()
        self.cargar()

    # ── interfaz ─────────────────────────────────────────────────────────────

    def _construir(self) -> None:
        panel = ttk.PanedWindow(self.cuerpo, orient=tk.HORIZONTAL)
        panel.pack(fill=tk.BOTH, expand=True)
        izq = tk.Frame(panel, bg=BG_CARD)
        der = tk.Frame(panel, bg=BG_CARD, highlightthickness=1, highlightbackground=BG_TERTIARY)
        panel.add(izq, weight=3)
        panel.add(der, weight=2)

        filtros = tk.Frame(izq, bg=BG_CARD)
        filtros.pack(fill=tk.X, pady=(0, 6))
        self._estado_f = tk.StringVar(value="")
        cb = ttk.Combobox(filtros, textvariable=self._estado_f, state="readonly", width=14,
                          values=[""] + pc.TODOS_LOS_ESTADOS)
        cb.pack(side=tk.LEFT)
        cb.bind("<<ComboboxSelected>>", lambda e: self.cargar())
        self._buscar = tk.StringVar()
        ent = ttk.Entry(filtros, textvariable=self._buscar, width=28)
        ent.pack(side=tk.LEFT, padx=6)
        ent.bind("<KeyRelease>", lambda e: self.cargar())
        self._resumen = etiqueta(filtros, "", "tenue")
        self._resumen.pack(side=tk.RIGHT)

        marco, self._tree = tabla(izq, ["Producto", "Estado", "Clasif.", "Mult.", "Coste landed", "PVP", "Actualizado"],
                                  [190, 90, 70, 60, 90, 70, 120], alto=18, alineacion=["w", "w", "center", "e", "e", "e", "w"])
        marco.pack(fill=tk.BOTH, expand=True)
        self._tree.bind("<<TreeviewSelect>>", self._al_seleccionar)

        self._detalle = tk.Frame(der, bg=BG_CARD)
        self._detalle.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)
        self._pintar_detalle(None)

    # ── datos ────────────────────────────────────────────────────────────────

    def cargar(self) -> None:
        filas = pc.listar(self.db, self._estado_f.get(), self._buscar.get())
        self._ids = [p["id"] for p in filas]
        datos, etiquetas = [], []
        for p in filas:
            c = pc.calculo_financiero(p) or {}
            datos.append([p["nombre"], p["estado"], p.get("clasificacion") or c.get("clasificacion") or "—",
                          c.get("multiplicador", "—"), importe(c.get("costo_landed")), importe(p.get("pvp")),
                          (p.get("actualizado_at") or "")[:16].replace("T", " ")])
            etiquetas.append("rojo" if p["estado"] == "descartado" else "")
        llenar_tabla(self._tree, datos, etiquetas)
        cuentas = pc.resumen_estados(self.db)
        self._resumen.config(text=" · ".join(f"{e} {n}" for e, n in cuentas.items() if n) or "Sin productos todavía")
        if self._sel in self._ids:
            self._tree.selection_set(self._tree.get_children()[self._ids.index(self._sel)])
        else:
            self._sel = None
            self._pintar_detalle(None)

    def _al_seleccionar(self, _e=None) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        idx = self._tree.get_children().index(sel[0])
        self._sel = self._ids[idx]
        self._pintar_detalle(pc.obtener(self.db, self._sel))

    # ── detalle ──────────────────────────────────────────────────────────────

    def _pintar_detalle(self, p: Optional[Dict[str, Any]]) -> None:
        for w in self._detalle.winfo_children():
            w.destroy()
        if not p:
            etiqueta(self._detalle, "Elige un producto de la lista o crea uno nuevo.", "tenue", wrap=360).pack(anchor="w")
            return
        tk.Label(self._detalle, text=p["nombre"], font=(FONT_SECTION[0], 14, "bold"), fg=TXT, bg=BG_CARD,
                 anchor="w", wraplength=360, justify=tk.LEFT).pack(fill=tk.X)
        tk.Label(self._detalle, text=f"Estado: {p['estado'].upper()}", font=FONT_SM, bg=BG_CARD, anchor="w",
                 fg=_COLOR_ESTADO.get(p["estado"], TXT)).pack(fill=tk.X)
        c = p.get("calculo")
        if c:
            caja = tk.Frame(self._detalle, bg=BG_TERTIARY)
            caja.pack(fill=tk.X, pady=8)
            filas = [("Coste landed (producto + envío)", importe(c["costo_landed"])),
                     ("Multiplicador sobre coste landed", f"{c['multiplicador']}×"),
                     ("Clasificación", c["clasificacion"]),
                     ("Margen neto por unidad / CPA máx.", importe(c["cpa_max"])),
                     ("CPA objetivo", importe(c["cpa_objetivo"]))]
            for k, v in filas:
                f = tk.Frame(caja, bg=BG_TERTIARY)
                f.pack(fill=tk.X, padx=8, pady=1)
                tk.Label(f, text=k, font=FONT_SM, fg=TXT_2, bg=BG_TERTIARY, anchor="w").pack(side=tk.LEFT)
                tk.Label(f, text=v, font=FONT_SM, bg=BG_TERTIARY,
                         fg=_COLOR_CLASIF.get(v, TXT)).pack(side=tk.RIGHT)
            etiqueta(self._detalle, "El multiplicador va sobre el coste landed, nunca sobre el producto solo "
                                    "(mínimo 2×, objetivo 3×).", "tenue", wrap=360).pack(fill=tk.X)
        else:
            etiqueta(self._detalle, "Faltan el coste de origen y el PVP para calcular el multiplicador.",
                     "aviso", wrap=360).pack(fill=tk.X, pady=6)
        if p.get("veredicto_refutacion"):
            etiqueta(self._detalle, "Refutación: " + p["veredicto_refutacion"], "suave", wrap=360).pack(fill=tk.X, pady=4)
        dem = p.get("demanda") or {}
        if dem:
            etiqueta(self._detalle, "Demanda: " + ", ".join(f"{k} {v}" for k, v in dem.items() if k != "notas")
                     + (" · creativo confirmado" if p.get("creativo_ok") else ""), "suave", wrap=360).pack(fill=tk.X)

        botones = tk.Frame(self._detalle, bg=BG_CARD)
        botones.pack(fill=tk.X, pady=8)
        sig = p.get("siguiente")
        if p["estado"] != "descartado":
            if sig:
                boton(botones, f"➡ Pasar a «{sig}»", lambda: self._mover(p["id"], sig), COLOR_SUCCESS).pack(fill=tk.X, pady=2)
            if p["estado"] in ("clasificado", "refutado"):
                boton(botones, "⚔ Refutar (8 intentos)", lambda: self._refutar(p), COLOR_SECONDARY).pack(fill=tk.X, pady=2)
            if p["estado"] in ("validado", "creativo"):
                boton(botones, "🎯 Demanda y creativo", lambda: self._demanda(p), COLOR_SECONDARY).pack(fill=tk.X, pady=2)
            if p["estado"] in ("validado", "creativo", "tienda", "escalado"):
                boton(botones, "✨ Hook Matrix", lambda: self._hook_matrix(p), COLOR_SECONDARY).pack(fill=tk.X, pady=2)
            boton(botones, "✏ Editar datos", lambda: self._editar(p), BG_TERTIARY, TXT_2).pack(fill=tk.X, pady=2)
            boton(botones, "✖ Descartar", lambda: self._mover(p["id"], "descartado", pedir_nota=True),
                  BG_TERTIARY, COLOR_ERROR).pack(fill=tk.X, pady=2)
        boton(botones, "🗑 Borrar", lambda: self._borrar(p), BG_TERTIARY, COLOR_ERROR).pack(fill=tk.X, pady=2)

        etiqueta(self._detalle, "Historial", "suave").pack(fill=tk.X, pady=(8, 2))
        for e in (p.get("eventos") or [])[:6]:
            etiqueta(self._detalle, f"{(e.get('fecha') or '')[:16].replace('T', ' ')} · "
                                    f"{(e.get('estado_anterior') or '—')} → {(e.get('estado_nuevo') or '—')} · {e.get('nota') or ''}",
                     "tenue", wrap=360).pack(fill=tk.X)

    # ── acciones ─────────────────────────────────────────────────────────────

    def _mover(self, pid: int, nuevo: str, pedir_nota: bool = False) -> None:
        nota = ""
        if pedir_nota:
            from tkinter import simpledialog
            nota = simpledialog.askstring("Descartar", "Motivo (opcional):", parent=self) or ""
            if not messagebox.askyesno("Descartar", "¿Descartar este producto?", parent=self):
                return
        try:
            pc.mover(self.db, pid, nuevo, nota)
        except (ValueError, KeyError) as exc:
            messagebox.showwarning("No se puede avanzar", str(exc), parent=self)
            return
        self.aviso(f"Producto movido a «{nuevo}».", "ok")
        self._sel = pid
        self.cargar()
        self._pintar_detalle(pc.obtener(self.db, pid))

    def _borrar(self, p: Dict[str, Any]) -> None:
        if messagebox.askyesno("Borrar", f"¿Borrar «{p['nombre']}» y su historial? No se puede deshacer.", parent=self):
            pc.borrar(self.db, p["id"])
            self._sel = None
            self.cargar()

    def _nuevo(self) -> None:
        self._dialogo_datos(None)

    def _editar(self, p: Dict[str, Any]) -> None:
        self._dialogo_datos(p)

    def _dialogo_datos(self, p: Optional[Dict[str, Any]]) -> None:
        d = Dialogo(self, "Editar producto" if p else "Nuevo producto candidato")
        campos = [("nombre", "Nombre del producto", 40), ("categoria", "Categoría", 24), ("url_proveedor", "URL del proveedor", 40),
                  ("costo_origen", "Coste de origen (5–15 recomendado)", 12), ("costo_envio", "Coste de envío", 12),
                  ("pvp", "PVP", 12), ("notas", "Notas", 40)]
        vars_: Dict[str, tk.StringVar] = {}
        for clave, texto, ancho in campos:
            v = tk.StringVar(value="" if not p or p.get(clave) is None else str(p.get(clave)))
            vars_[clave] = v
            d.fila(texto, v, ancho)

        def guardar() -> None:
            datos = {k: v.get().strip() for k, v in vars_.items() if v.get().strip() != ""}
            try:
                res = pc.actualizar(self.db, p["id"], datos) if p else pc.crear(self.db, datos)
            except (ValueError, KeyError) as exc:
                messagebox.showwarning("Datos no válidos", str(exc), parent=d)
                return
            d.destroy()
            self._sel = res["id"]
            self.cargar()
            self._pintar_detalle(pc.obtener(self.db, res["id"]))
            self.aviso("Producto guardado.", "ok")

        d.botones("Guardar", guardar)

    def _refutar(self, p: Dict[str, Any]) -> None:
        d = Dialogo(self, "Refutar el producto — 8 intentos de matar la tesis", ancho=760)
        previas = p.get("refutaciones") or {}
        resultados: Dict[int, tk.StringVar] = {}
        datos: Dict[int, tk.StringVar] = {}

        def generar_borrador() -> None:
            def trabajo():
                from app.services import refutacion_debate
                return refutacion_debate.redactar_debate(self.db, p["id"])

            def listo(resultado):
                for item in resultado.get("refutaciones", []):
                    n = item["numero"]
                    resultados[n].set("" if item["veredicto"] == "sin_datos" else item["veredicto"])
                    datos[n].set(item.get("evidencia", ""))
                self.aviso("Borrador generado — revísalo antes de guardar." if resultado.get("generado")
                          else "El modelo no respondió; revisa a mano.", "info")

            self.en_hilo(trabajo, listo, lambda e: self.aviso(f"Error al generar el borrador: {e}", "error"))

        boton(d.cuerpo, "🤖 Generar borrador", generar_borrador, COLOR_PRIMARY).pack(anchor="w", pady=(0, 8))

        for n, texto in pc.REFUTACIONES.items():
            marco = tk.Frame(d.cuerpo, bg=BG_CARD)
            marco.pack(fill=tk.X, pady=3)
            etiqueta(marco, f"{n}. {texto}", "normal", wrap=700).pack(fill=tk.X)
            f = tk.Frame(marco, bg=BG_CARD)
            f.pack(fill=tk.X)
            r = tk.StringVar(value=(previas.get(str(n)) or {}).get("resultado", ""))
            resultados[n] = r
            for etq, val in (("Sigue en pie (pasa)", "pasa"), ("Refutada", "refutada")):
                ttk.Radiobutton(f, text=etq, value=val, variable=r).pack(side=tk.LEFT, padx=(0, 10))
            dv = tk.StringVar(value=(previas.get(str(n)) or {}).get("dato", ""))
            datos[n] = dv
            ttk.Entry(f, textvariable=dv, width=46).pack(side=tk.LEFT, fill=tk.X, expand=True)

        def guardar() -> None:
            resp = {str(n): {"resultado": r.get(), "dato": datos[n].get()} for n, r in resultados.items() if r.get()}
            try:
                res = pc.guardar_refutaciones(self.db, p["id"], resp)
            except (ValueError, KeyError) as exc:
                messagebox.showwarning("No se pudo guardar", str(exc), parent=d)
                return
            d.destroy()
            self._pintar_detalle(res)
            self.cargar()
            self.aviso(res.get("veredicto_refutacion") or "Refutaciones guardadas (faltan respuestas para el veredicto).", "info")

        d.botones("Guardar respuestas", guardar)

    def _hook_matrix(self, p: Dict[str, Any]) -> None:
        d = Dialogo(self, f"Hook Matrix — {p['nombre']}", ancho=720)
        _, contexto_var, _ = self.campo(d.cuerpo, "Ángulo o contexto (opcional)", ancho=50,
                                        valor=p.get("categoria") or "")
        resultados_frame = tk.Frame(d.cuerpo, bg=BG_CARD)
        resultados_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        def pintar_historico():
            for w in resultados_frame.winfo_children():
                w.destroy()
            from app.services import hook_matrix_service
            for m in hook_matrix_service.listar(self.db, p["id"]):
                cab = etiqueta(resultados_frame,
                              f"{'✓ Gate OK' if m['gate_pass'] else '✗ Gate falló'} · {m['total_hooks']} hooks · {m['creado_at']}",
                              "ok" if m["gate_pass"] else "error")
                cab.pack(anchor="w", pady=(6, 0))
                for h in m["hooks"]:
                    etiqueta(resultados_frame, f"{h.get('formula', '?')}: {h.get('texto', '')}",
                            "suave", wrap=680).pack(anchor="w")

        def generar():
            def trabajo():
                from app.services import hook_matrix_service
                contexto = contexto_var.get().strip() or f"{p['nombre']} ({p.get('categoria') or 'sin categoría'})"
                resultado = hook_matrix_service.generar(contexto)
                hook_matrix_service.guardar(self.db, p["id"], resultado)
                return resultado

            def listo(resultado):
                self.aviso("Hook matrix generada." if resultado.get("generado") else "El modelo no respondió.",
                          "ok" if resultado.get("gate_pass") else "aviso")
                pintar_historico()

            self.en_hilo(trabajo, listo, lambda e: self.aviso(f"Error al generar: {e}", "error"))

        boton(d.cuerpo, "✨ Generar", generar, COLOR_PRIMARY).pack(anchor="w", pady=(8, 0))
        pintar_historico()

    def _demanda(self, p: Dict[str, Any]) -> None:
        import os
        d = Dialogo(self, "Demanda (fake door) y creativo")
        puerto = os.getenv("DASHBOARD_PORT", "47821")
        url = f"http://localhost:{puerto}/fd/{p['id']}"
        etiqueta(d.cuerpo, f"Página pública para compartir: {url}", "suave", wrap=480).pack(anchor="w", pady=(0, 4))
        fd_resumen = etiqueta(d.cuerpo, "", "suave", wrap=480)
        fd_resumen.pack(anchor="w")

        dem = p.get("demanda") or {}
        vars_ = {k: tk.StringVar(value=str(dem.get(k, ""))) for k in ("visitantes", "clics_comprar", "emails", "dias_test")}
        nombres = {"visitantes": "Visitantes del pop-up", "clics_comprar": "Clics en «comprar»", "emails": "Emails capturados",
                   "dias_test": "Días de test"}

        def calcular_desde_eventos() -> None:
            def trabajo():
                from app.services import fake_door_service, deterministic_gate
                resumen = fake_door_service.resumen_producto(self.db, p["id"])
                mediana = fake_door_service.mediana_ctr(self.db, excluir_producto_id=p["id"])
                gate = deterministic_gate.check_fake_door_ctr(
                    resumen["ctr"], mediana, resumen["visitas"], resumen["concentracion"])
                return resumen, gate

            def listo(resultado):
                resumen, gate = resultado
                vars_["visitantes"].set(str(resumen["visitas"]))
                vars_["clics_comprar"].set(str(resumen["clics_comprar"]))
                vars_["emails"].set(str(resumen["emails"]))
                fd_resumen.config(text=f"CTR {resumen['ctr']:.1%} · veredicto: {gate.evidence.get('veredicto', '—')}")

            self.en_hilo(trabajo, listo, lambda e: self.aviso(f"Error: {e}", "error"))

        boton(d.cuerpo, "🔄 Calcular desde eventos", calcular_desde_eventos, COLOR_PRIMARY).pack(anchor="w", pady=(0, 10))

        for k, v in vars_.items():
            d.fila(nombres[k], v, 12)
        ok = tk.BooleanVar(value=bool(p.get("creativo_ok")))
        ttk.Checkbutton(d.cuerpo, text="El creativo funciona (engancha en los primeros 3 s)", variable=ok).pack(anchor="w", pady=6)

        def guardar() -> None:
            try:
                res = pc.guardar_demanda(self.db, p["id"], {k: v.get() for k, v in vars_.items()}, ok.get())
            except (ValueError, KeyError) as exc:
                messagebox.showwarning("Datos no válidos", str(exc), parent=d)
                return
            d.destroy()
            self._pintar_detalle(res)
            self.aviso("Demanda y creativo guardados.", "ok")

        d.botones("Guardar", guardar)
