"""
canales_panel.py — Checklist operativo + copy guiado por IA para canales pagados
(Google Ads, TikTok Ads, Amazon, TikTok Shop). Fase 6, opcional: sin integración de API
en vivo con esas plataformas — equivalente de escritorio de /canales en la web.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List

from app.ui.components.panel_kit import COLOR_PRIMARY, PanelBase, boton, etiqueta, tarjeta

_CANALES = [("google_ads", "Google Ads"), ("tiktok_ads", "TikTok Ads"),
           ("amazon", "Amazon"), ("tiktok_shop", "TikTok Shop")]


class CanalesPanel(PanelBase):
    def __init__(self, parent, db_manager=None, **kw):
        super().__init__(parent, db_manager=db_manager, titulo="📢 Canales Pagados",
                         subtitulo="Checklist operativo + copy guiado por IA — sin conexión en vivo a Google/TikTok/Amazon.",
                         scroll=False, **kw)
        self._canal = tk.StringVar(value=_CANALES[0][0])
        self._construir_ui()
        self._cargar()

    def _construir_ui(self) -> None:
        barra = tk.Frame(self.cuerpo, bg=self.cuerpo["bg"])
        barra.pack(fill=tk.X, pady=(0, 10))
        etiqueta(barra, "Canal:", tipo="suave").pack(side=tk.LEFT, padx=(0, 8))
        combo = ttk.Combobox(barra, values=[n for _, n in _CANALES], state="readonly", width=20)
        combo.current(0)
        combo.pack(side=tk.LEFT)
        combo.bind("<<ComboboxSelected>>", lambda e: self._cambiar_canal(combo.get()))

        fila = tk.Frame(self.cuerpo, bg=self.cuerpo["bg"])
        fila.pack(fill=tk.BOTH, expand=True)

        card_checklist = tarjeta(fila, "Checklist operativo", acento=COLOR_PRIMARY, lado=tk.LEFT, expand=True)
        self._checklist_frame = tk.Frame(card_checklist, bg=card_checklist["bg"])
        self._checklist_frame.pack(fill=tk.BOTH, expand=True)

        card_copy = tarjeta(fila, "Copy guiado por IA", acento=COLOR_PRIMARY, lado=tk.RIGHT, expand=True)
        self._contexto = tk.Text(card_copy, height=3, wrap=tk.WORD, bg="#08091a", fg="#a8b0d8",
                                 relief=tk.FLAT, font=("Segoe UI", 9))
        self._contexto.pack(fill=tk.X, pady=(0, 8))
        boton(card_copy, "✨ Generar copy", self._generar, COLOR_PRIMARY).pack(anchor="w", pady=(0, 8))
        self._historial_frame = tk.Frame(card_copy, bg=card_copy["bg"])
        self._historial_frame.pack(fill=tk.BOTH, expand=True)

    def _cambiar_canal(self, nombre_visible: str) -> None:
        self._canal.set(next(v for v, n in _CANALES if n == nombre_visible))
        self._cargar()

    def _cargar(self) -> None:
        def trabajo():
            from app.services import canal_checklist_service
            canal = self._canal.get()
            return canal_checklist_service.checklist(canal), canal_checklist_service.listar(
                self.db_manager.db_path, canal=canal)

        def listo(resultado):
            items, historial = resultado
            self._pintar_checklist(items)
            self._pintar_historial(historial)

        self.en_hilo(trabajo, listo, lambda e: self.aviso(f"Error: {e}", "error"))

    def _pintar_checklist(self, items: List[str]) -> None:
        for w in self._checklist_frame.winfo_children():
            w.destroy()
        for item in items:
            fila = tk.Frame(self._checklist_frame, bg=self._checklist_frame["bg"])
            fila.pack(fill=tk.X, pady=2)
            tk.Checkbutton(fila, bg=self._checklist_frame["bg"], activebackground=self._checklist_frame["bg"]
                          ).pack(side=tk.LEFT)
            etiqueta(fila, item, tipo="suave", wrap=340).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _pintar_historial(self, filas: List[Dict[str, Any]]) -> None:
        for w in self._historial_frame.winfo_children():
            w.destroy()
        if not filas:
            etiqueta(self._historial_frame, "Sin copy generado todavía para este canal.", tipo="tenue").pack(anchor="w")
            return
        for f in filas:
            etiqueta(self._historial_frame, f"{'✓ Gate OK' if f['gate_pass'] else '✗ Gate falló'} · {f['creado_at']}",
                    "ok" if f["gate_pass"] else "error").pack(anchor="w", pady=(6, 0))
            for k, v in (f.get("copy") or {}).items():
                etiqueta(self._historial_frame, f"{k}: {v}", "suave", wrap=340).pack(anchor="w")

    def _generar(self) -> None:
        contexto = self._contexto.get("1.0", tk.END).strip()
        self.aviso("Generando…", "info")

        def trabajo():
            from app.services import canal_checklist_service
            resultado = canal_checklist_service.generar(self._canal.get(), contexto)
            canal_checklist_service.guardar(self.db_manager.db_path, None, resultado)
            return resultado

        def listo(resultado):
            self.aviso("Copy generado." if resultado.get("generado") else "El modelo no respondió.",
                      "ok" if resultado.get("gate_pass") else "aviso")
            self._cargar()

        self.en_hilo(trabajo, listo, lambda e: self.aviso(f"Error: {e}", "error"))
