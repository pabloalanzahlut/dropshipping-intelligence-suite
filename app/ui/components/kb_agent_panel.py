"""
KBAgentPanel — Agente IA como conversación, igual que /agente en la web.

Antes este panel mandaba una pregunta suelta y mostraba el JSON crudo que devuelve el motor de
agentes (`{"respuesta": "...", "tipo_consulta": "...", ...}`), ilegible para el operador. Ahora:

  · Es un chat de verdad: los mensajes se acumulan, cada pregunta nueva recuerda las últimas
    respuestas (igual que el endpoint /api/kb/chat de la web) y el texto se ve formateado
    (negritas, listas, citas [n] enlazadas a su vídeo), nunca como JSON.
  · Toda la lógica de qué dice el agente — enrutar la pregunta, construir el contexto, convertir
    la salida del motor en texto natural — vive en `app/services/agent_chat.py` y la comparte
    con la web: aquí solo se dibuja y se hilan las llamadas.
  · `_lineas_formato()` / `_segmentos_en_linea()` son funciones puras (sin Tk) para que el
    formato markdown-ligero se pueda probar sin levantar una pantalla.
"""
from __future__ import annotations

import re
import threading
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import ttk
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.agents_engine.executor import AgentExecutor
from app.config.path_manager import PathManager
from app.services import agent_chat, agent_router
from app.ui.components.panel_kit import (
    BG_CARD, BG_PRIMARY, BG_SECONDARY, BG_TERTIARY, BORDER, COLOR_ERROR, COLOR_PRIMARY, COLOR_SECONDARY,
    COLOR_SUCCESS, COLOR_WARNING, FONT_SM, PanelBase, TXT, TXT_2, TXT_3, boton,
)

MAX_HISTORIAL_CONTEXTO = 6     # turnos que se reenvían como memoria de la conversación (igual que la web)

SUGERENCIAS = [
    ("Tu tienda", "¿Cómo va mi tienda este mes?"),
    ("Productos", "¿Qué productos recomiendan mis mentores ahora mismo?"),
    ("Cuentas", "Coste 6 $, envío 2 $ y lo vendo a 24 $: ¿cumple las reglas?"),
    ("Creativos", "¿Qué hooks de TikTok funcionan según la KB?"),
]

_COLOR_RUTA = {"gem-qa-validation": COLOR_WARNING, "gem-backend-core": COLOR_SECONDARY}

# ─────────────────────────── formato markdown-ligero (sin Tk, probable sin pantalla) ───────────

_PATRON_INLINE = re.compile(r"\*\*([^*\n]+)\*\*|\[(\d{1,2})\]")
_PATRON_VINETA = re.compile(r"^[-•*]\s+(.*)$")
_PATRON_NUMERADA = re.compile(r"^(\d{1,2})[.)]\s+(.*)$")
_PATRON_TITULO = re.compile(r"^#{1,4}\s+(.*)$")


def _segmentos_en_linea(texto: str) -> List[Tuple[str, Tuple[str, ...]]]:
    """Una línea de texto → [(fragmento, tags)]. Tags: () normal, ("bold",) o ("cita", "n")."""
    segmentos: List[Tuple[str, Tuple[str, ...]]] = []
    pos = 0
    for m in _PATRON_INLINE.finditer(texto):
        if m.start() > pos:
            segmentos.append((texto[pos:m.start()], ()))
        if m.group(1) is not None:
            segmentos.append((m.group(1), ("bold",)))
        else:
            segmentos.append((m.group(2), ("cita", f"cita_{m.group(2)}")))
        pos = m.end()
    if pos < len(texto):
        segmentos.append((texto[pos:], ()))
    return segmentos or [("", ())]


def _lineas_formato(texto: str) -> List[Dict[str, Any]]:
    """Texto plano → bloques [{"tipo": "parrafo|vineta|numerada|titulo", "lineas": [segmentos, ...]}].

    Líneas seguidas sin blanco de por medio se tratan como el mismo párrafo (salto suave); una línea
    en blanco cierra el bloque actual. Replica la misma lectura que hace la web en JavaScript."""
    bloques: List[Dict[str, Any]] = []
    actual: Optional[Dict[str, Any]] = None

    def cerrar() -> None:
        nonlocal actual
        if actual is not None:
            bloques.append(actual)
            actual = None

    for cruda in (texto or "").replace("\r", "").split("\n"):
        linea = cruda.strip()
        if not linea:
            cerrar()
            continue
        v, o, t = _PATRON_VINETA.match(linea), _PATRON_NUMERADA.match(linea), _PATRON_TITULO.match(linea)
        if v or o:
            tipo = "vineta" if v else "numerada"
            contenido = v.group(1) if v else o.group(2)
            if actual is None or actual["tipo"] != tipo:
                cerrar()
                actual = {"tipo": tipo, "lineas": []}
            actual["lineas"].append(_segmentos_en_linea(contenido))
        elif t:
            cerrar()
            bloques.append({"tipo": "titulo", "lineas": [_segmentos_en_linea(t.group(1))]})
        else:
            if actual is None or actual["tipo"] != "parrafo":
                cerrar()
                actual = {"tipo": "parrafo", "lineas": []}
            actual["lineas"].append(_segmentos_en_linea(linea))
    cerrar()
    return bloques


def _hora() -> str:
    return datetime.now().strftime("%H:%M")


class KBAgentPanel(PanelBase):
    """Chat con el Agente IA interno (misma conversación que /agente en la web)."""

    def __init__(self, parent, db_manager=None, **kwargs):
        super().__init__(parent, db_manager=db_manager, titulo="🤖 Agente IA",
                         subtitulo="Habla con él como con un compañero: recuerda la conversación y usa tu "
                                   "Knowledge Base y los datos reales de tu tienda.", scroll=False, **kwargs)
        self.db_path = getattr(self.db_manager, "db_path", None) or str(PathManager.get_paths()["db"])
        self.executor = AgentExecutor(db_manager=self.db_manager)
        self._mensajes: List[Dict[str, Any]] = []       # [{rol, texto, meta...}] — lo que recuerda el chat
        self._cargando = False
        self._cancelado = False
        self._fuentes_visibles: Dict[int, bool] = {}
        self._datos_visibles: Dict[int, bool] = {}

        kb = ttk.Label(self.acciones, text="", foreground=TXT_3, background=BG_SECONDARY, font=FONT_SM)
        kb.pack(side=tk.LEFT, padx=(0, 10))
        self._kb_lbl = kb
        self._nueva_btn = boton(self.acciones, "＋ Nueva conversación", self._nueva, BG_TERTIARY, TXT_2)
        self._nueva_btn.pack(side=tk.LEFT)

        self._construir_chat()
        self._construir_entrada()
        self._refrescar_kb_count()
        self._mostrar_bienvenida()

    # ── estructura ───────────────────────────────────────────────────────────

    def _construir_chat(self) -> None:
        marco = tk.Frame(self.cuerpo, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        marco.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.texto = tk.Text(
            marco, wrap=tk.WORD, bg="#08091a", fg=TXT, font=("Segoe UI", 10), relief=tk.FLAT,
            padx=16, pady=14, cursor="arrow", spacing1=1, spacing3=5, state=tk.DISABLED,
        )
        barra = ttk.Scrollbar(marco, orient=tk.VERTICAL, command=self.texto.yview)
        self.texto.configure(yscrollcommand=barra.set)
        barra.pack(side=tk.RIGHT, fill=tk.Y)
        self.texto.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.texto.bind("<MouseWheel>", lambda e: self.texto.yview_scroll(-1 if e.delta > 0 else 1, "units"))

        self.texto.tag_configure("hora_user", foreground=TXT_3, justify=tk.RIGHT, font=("Segoe UI", 8),
                                 spacing1=2, spacing3=10)
        self.texto.tag_configure("burbuja_user", background="#15122a", foreground=TXT, justify=tk.RIGHT,
                                 lmargin1=90, lmargin2=90, rmargin=4, spacing1=4, spacing3=2,
                                 font=("Segoe UI", 10))
        self.texto.tag_configure("cab_agente", foreground=COLOR_SECONDARY, font=("Segoe UI", 8, "bold"),
                                 spacing1=10, spacing3=2)
        self.texto.tag_configure("burbuja_agente", background=BG_TERTIARY, foreground="#d7dcf5",
                                 lmargin1=4, lmargin2=4, rmargin=90, spacing1=2, spacing3=2,
                                 font=("Segoe UI", 10))
        self.texto.tag_configure("vineta_agente", background=BG_TERTIARY, foreground="#d7dcf5",
                                 lmargin1=22, lmargin2=34, rmargin=90, spacing1=1, spacing3=1,
                                 font=("Segoe UI", 10))
        self.texto.tag_configure("titulo_agente", background=BG_TERTIARY, foreground=TXT,
                                 lmargin1=4, lmargin2=4, rmargin=90, spacing1=6, spacing3=2,
                                 font=("Segoe UI", 10, "bold"))
        self.texto.tag_configure("bold", font=("Segoe UI", 10, "bold"), foreground=TXT)
        self.texto.tag_configure("meta", foreground=TXT_3, font=("Segoe UI", 8), spacing1=3, spacing3=8)
        self.texto.tag_configure("escribiendo", background=BG_TERTIARY, foreground=TXT_3,
                                 lmargin1=4, rmargin=90, spacing1=2, spacing3=2, font=("Segoe UI", 10, "italic"))
        self.texto.tag_configure("error", background="#1a0d15", foreground="#fecdd3",
                                 lmargin1=4, rmargin=90, spacing1=2, spacing3=2, font=("Segoe UI", 10))
        self.texto.tag_configure("bienvenida", foreground=TXT_2, justify=tk.CENTER, font=("Segoe UI", 10),
                                 spacing1=20, spacing3=14)

    def _construir_entrada(self) -> None:
        pie = tk.Frame(self.cuerpo, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        pie.pack(fill=tk.X)
        interior = tk.Frame(pie, bg=BG_CARD)
        interior.pack(fill=tk.X, padx=12, pady=10)

        self._ruta_lbl = tk.Label(interior, text="", bg=BG_CARD, fg=TXT_3, font=FONT_SM, anchor="w", justify=tk.LEFT)
        self._ruta_lbl.pack(fill=tk.X, pady=(0, 6))

        fila = tk.Frame(interior, bg=BG_CARD)
        fila.pack(fill=tk.X)

        self.entrada = tk.Text(fila, height=2, wrap=tk.WORD, bg="#08091a", fg=TXT,
                               insertbackground=COLOR_PRIMARY, relief=tk.FLAT, font=("Segoe UI", 10), padx=8, pady=6)
        self.entrada.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.entrada.bind("<KeyRelease>", self._al_escribir)
        self.entrada.bind("<Return>", self._enter_envia)
        self.entrada.bind("<Shift-Return>", lambda e: None)   # deja el salto de línea normal

        self.btn_enviar = boton(fila, "➤ Enviar", self._on_enviar, COLOR_PRIMARY)
        self.btn_enviar.pack(side=tk.LEFT)
        self.btn_cancelar = boton(fila, "✖ Cancelar", self._on_cancelar, BG_TERTIARY, COLOR_ERROR)

        sel = tk.Frame(interior, bg=BG_CARD)
        sel.pack(fill=tk.X, pady=(8, 0))
        tk.Label(sel, text="Responde:", bg=BG_CARD, fg=TXT_3, font=FONT_SM).pack(side=tk.LEFT)
        self._agente_var = tk.StringVar(value="Automático")
        self._agentes_opc = {"Automático": "auto"}
        for nombre, info in agent_router.AGENTES.items():
            self._agentes_opc[info["rol"]] = nombre
        cb = ttk.Combobox(sel, textvariable=self._agente_var, values=list(self._agentes_opc),
                          state="readonly", width=16)
        cb.pack(side=tk.LEFT, padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self._actualizar_ruta())

    # ── bienvenida / sugerencias ─────────────────────────────────────────────

    def _refrescar_kb_count(self) -> None:
        def trabajo() -> int:
            from app.services import insights_service
            return int(insights_service.insights_resumen(self.db_path).get("total") or 0)

        def listo(n: int) -> None:
            self._kb_lbl.config(text=f"{n} apuntes en la KB" if n else "KB vacía")
        self.en_hilo(trabajo, listo, lambda e: None)

    def _mostrar_bienvenida(self) -> None:
        self.texto.config(state=tk.NORMAL)
        self.texto.delete("1.0", tk.END)
        self.texto.insert(tk.END, "¿En qué te ayudo?\n", "bienvenida")
        self.texto.insert(tk.END, "Pregunta con tus palabras. Si me falta un dato te lo pido; no me lo invento.\n\n",
                          "bienvenida")
        for tema, pregunta in SUGERENCIAS:
            marco = tk.Frame(self.texto, bg=BG_TERTIARY, highlightthickness=1, highlightbackground=BORDER,
                             cursor="hand2")
            tk.Label(marco, text=tema, bg=BG_TERTIARY, fg=COLOR_PRIMARY, font=("Segoe UI", 8, "bold")).pack(
                anchor="w", padx=10, pady=(6, 0))
            lbl = tk.Label(marco, text=pregunta, bg=BG_TERTIARY, fg=TXT_2, font=("Segoe UI", 9),
                          wraplength=280, justify=tk.LEFT, cursor="hand2")
            lbl.pack(anchor="w", padx=10, pady=(0, 6))
            for w in (marco, lbl):
                w.bind("<Button-1>", lambda e, q=pregunta: self._enviar(q))
            self.texto.window_create(tk.END, window=marco, padx=20, pady=4)
            self.texto.insert(tk.END, "\n")
        self.texto.config(state=tk.DISABLED)

    def _nueva(self) -> None:
        if self._cargando:
            return
        self._mensajes.clear()
        self._fuentes_visibles.clear()
        self._datos_visibles.clear()
        self._mostrar_bienvenida()
        self._ruta_lbl.config(text="")
        self.entrada.focus_set()

    # ── enrutado en vivo ─────────────────────────────────────────────────────

    def _agente_elegido(self) -> str:
        return self._agentes_opc.get(self._agente_var.get(), "auto")

    def _al_escribir(self, _event=None) -> None:
        self._actualizar_ruta()

    def _actualizar_ruta(self) -> None:
        texto = self.entrada.get("1.0", tk.END).strip()
        if not texto:
            self._ruta_lbl.config(text="")
            return
        ruta = agent_chat.elegir_ruta(texto, self._agente_elegido(),
                                      self._mensajes[-MAX_HISTORIAL_CONTEXTO:])
        prefijo = "Lo atenderá" if self._agente_elegido() == "auto" else "Fijado:"
        self._ruta_lbl.config(text=f"{prefijo} {ruta['rol']} · {ruta['tipo_etiqueta']}",
                              fg=_COLOR_RUTA.get(ruta["agente"], TXT_3))

    # ── enviar / cancelar ────────────────────────────────────────────────────

    def _enter_envia(self, event) -> str:
        if event.state & 0x0001:       # Shift: deja pasar el salto de línea normal
            return ""
        self._on_enviar()
        return "break"

    def _on_enviar(self) -> None:
        texto = self.entrada.get("1.0", tk.END).strip()
        if not texto or self._cargando:
            return
        self.entrada.delete("1.0", tk.END)
        self._enviar(texto)

    def _enviar(self, pregunta: str) -> None:
        if self._cargando:
            return
        if not self._mensajes:                         # primera pregunta: sustituye la bienvenida
            self.texto.config(state=tk.NORMAL)
            self.texto.delete("1.0", tk.END)
            self.texto.config(state=tk.DISABLED)
        historial = [{"rol": m["rol"], "texto": m["texto"]} for m in self._mensajes
                    if m["rol"] in ("user", "agente") and m.get("texto")][-MAX_HISTORIAL_CONTEXTO:]
        self._mensajes.append({"rol": "user", "texto": pregunta})
        self._pintar_user(pregunta)
        self._pintar_escribiendo()
        self._cargando = True
        self._cancelado = False
        self.btn_enviar.pack_forget()
        self.btn_cancelar.pack(side=tk.LEFT)
        self._ruta_lbl.config(text="")

        agente = self._agente_elegido()

        def trabajo() -> Dict[str, Any]:
            return agent_chat.responder(self.db_path, pregunta, agente, historial,
                                        executor=self.executor, proyecto="kb_chat_escritorio")

        def listo(r: Dict[str, Any]) -> None:
            self._fin_envio()
            if self._cancelado:
                return
            self._mensajes.append({"rol": "agente", "texto": r["texto"]})
            self._quitar_escribiendo()
            self._pintar_agente(r)
            self.entrada.focus_set()

        def fallo(exc: Exception) -> None:
            self._fin_envio()
            if self._cancelado:
                return
            self._quitar_escribiendo()
            mensaje = exc.args[0] if isinstance(exc, agent_chat.AgenteNoDisponible) and exc.args else str(exc)
            self._pintar_error(mensaje, pregunta)
            self._mensajes.pop()                       # la pregunta se reintenta, no queda "contestada" a medias

        self.en_hilo(trabajo, listo, fallo)

    def _fin_envio(self) -> None:
        self._cargando = False
        self.btn_cancelar.pack_forget()
        self.btn_enviar.pack(side=tk.LEFT)

    def _on_cancelar(self) -> None:
        """La llamada en curso no se puede abortar a medias (es una sola petición HTTP), pero se
        descarta su resultado y el operador recupera el control al momento."""
        self._cancelado = True
        self._fin_envio()
        self._quitar_escribiendo()
        self._pintar_meta_sistema("Cancelado.")
        self.entrada.focus_set()

    # ── pintar mensajes ──────────────────────────────────────────────────────

    def _al_final(self) -> None:
        self.texto.see(tk.END)

    def _pintar_user(self, texto: str) -> None:
        self.texto.config(state=tk.NORMAL)
        self.texto.insert(tk.END, texto + "\n", "burbuja_user")
        self.texto.insert(tk.END, _hora() + "\n", "hora_user")
        self.texto.config(state=tk.DISABLED)
        self._al_final()

    def _pintar_escribiendo(self) -> None:
        self.texto.config(state=tk.NORMAL)
        self.texto.mark_set("inicio_escribiendo", tk.END)
        self.texto.insert(tk.END, "🤖 Agente\n", "cab_agente")
        self.texto.insert(tk.END, "Escribiendo…\n", "escribiendo")
        self.texto.config(state=tk.DISABLED)
        self._al_final()

    def _quitar_escribiendo(self) -> None:
        try:
            self.texto.config(state=tk.NORMAL)
            self.texto.delete("inicio_escribiendo", tk.END)
            self.texto.config(state=tk.DISABLED)
        except tk.TclError:
            pass

    def _pintar_meta_sistema(self, texto: str) -> None:
        self.texto.config(state=tk.NORMAL)
        self.texto.insert(tk.END, texto + "\n", "meta")
        self.texto.config(state=tk.DISABLED)
        self._al_final()

    def _insertar_segmentos(self, segmentos: Sequence[Tuple[str, Tuple[str, ...]]], tag_base: str,
                            fuentes_por_n: Dict[str, Dict[str, Any]], contador: List[int]) -> None:
        for fragmento, tags in segmentos:
            if not fragmento:
                continue
            if tags and tags[0] == "cita":
                n = tags[1].split("_", 1)[1]
                f = fuentes_por_n.get(n)
                contador[0] += 1
                tag_cita = f"cita_{contador[0]}_{n}"
                self.texto.tag_configure(tag_cita, foreground=COLOR_PRIMARY, underline=bool(f and f.get("url")))
                self.texto.insert(tk.END, f"[{n}]", (tag_base, tag_cita))
                if f and f.get("url"):
                    url = f["url"]
                    self.texto.tag_bind(tag_cita, "<Button-1>", lambda e, u=url: webbrowser.open(u))
                    self.texto.tag_bind(tag_cita, "<Enter>", lambda e: self.texto.config(cursor="hand2"))
                    self.texto.tag_bind(tag_cita, "<Leave>", lambda e: self.texto.config(cursor="arrow"))
            elif tags and tags[0] == "bold":
                self.texto.insert(tk.END, fragmento, (tag_base, "bold"))
            else:
                self.texto.insert(tk.END, fragmento, tag_base)

    def _pintar_agente(self, r: Dict[str, Any]) -> None:
        fuentes = r.get("fuentes") or []
        fuentes_por_n = {str(f["n"]): f for f in fuentes}
        idx = len(self._mensajes)

        self.texto.config(state=tk.NORMAL)
        cab = r["ruta"]["rol"] if not r.get("rapida") else "Agente"
        self.texto.insert(tk.END, f"🤖 {cab}\n", "cab_agente")
        contador_citas = [0]
        for bloque in _lineas_formato(r["texto"]) or [{"tipo": "parrafo", "lineas": [[("—", ())]]}]:
            tag = {"vineta": "vineta_agente", "numerada": "vineta_agente",
                  "titulo": "titulo_agente"}.get(bloque["tipo"], "burbuja_agente")
            for i, linea in enumerate(bloque["lineas"]):
                prefijo = ""
                if bloque["tipo"] == "vineta":
                    prefijo = "• "
                elif bloque["tipo"] == "numerada":
                    prefijo = f"{i + 1}. "
                if prefijo:
                    self.texto.insert(tk.END, prefijo, tag)
                self._insertar_segmentos(linea, tag, fuentes_por_n, contador_citas)
                self.texto.insert(tk.END, "\n", tag)

        partes_meta = [_hora()]
        if not r.get("rapida"):
            partes_meta.append(r["ruta"]["tipo_etiqueta"])
        if r.get("con_tienda"):
            partes_meta.append("con datos de tu tienda")
        if r.get("confianza"):
            partes_meta.append(f"confianza {r['confianza'].lower()}")
        self.texto.insert(tk.END, "  ·  ".join(partes_meta), "meta")

        if fuentes:
            self.texto.insert(tk.END, "   ", "meta")
            btn = tk.Button(self.texto, text=f"Fuentes ({len(fuentes)})", font=("Segoe UI", 8), bg=BG_TERTIARY,
                            fg=COLOR_PRIMARY, relief=tk.FLAT, bd=0, cursor="hand2", padx=6, pady=1,
                            command=lambda: self._alternar_fuentes(idx, fuentes))
            self.texto.window_create(tk.END, window=btn)
        if r.get("datos"):
            self.texto.insert(tk.END, "   ", "meta")
            btn = tk.Button(self.texto, text="Ver datos", font=("Segoe UI", 8), bg=BG_TERTIARY, fg=COLOR_PRIMARY,
                            relief=tk.FLAT, bd=0, cursor="hand2", padx=6, pady=1,
                            command=lambda: self._alternar_datos(idx, r["datos"]))
            self.texto.window_create(tk.END, window=btn)
        self.texto.insert(tk.END, "   ", "meta")
        btn_copiar = tk.Button(self.texto, text="Copiar", font=("Segoe UI", 8), bg=BG_TERTIARY, fg=TXT_2,
                               relief=tk.FLAT, bd=0, cursor="hand2", padx=6, pady=1,
                               command=lambda: self._copiar(r["texto"]))
        self.texto.window_create(tk.END, window=btn_copiar)
        self.texto.insert(tk.END, "\n\n", "meta")
        self.texto.config(state=tk.DISABLED)
        self._al_final()

    def _copiar(self, texto: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(texto)

    def _alternar_fuentes(self, idx: int, fuentes: List[Dict[str, Any]]) -> None:
        visible = not self._fuentes_visibles.get(idx, False)
        self._fuentes_visibles[idx] = visible
        if not visible:
            return
        self.texto.config(state=tk.NORMAL)
        for f in fuentes:
            marco = tk.Frame(self.texto, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER, cursor="hand2")
            texto_f = f"[{f['n']}] {f.get('titulo') or '(sin título)'} · {f.get('canal') or '?'}"
            if f.get("video_title"):
                texto_f += f" · {f['video_title']}"
            lbl = tk.Label(marco, text=texto_f, bg=BG_CARD, fg="#a8b0d8", font=("Segoe UI", 8), padx=8, pady=4,
                          wraplength=560, justify=tk.LEFT, cursor="hand2")
            lbl.pack(anchor="w")
            if f.get("url"):
                url = f["url"]
                for w in (marco, lbl):
                    w.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
            self.texto.insert(tk.END, "", "meta")
            self.texto.window_create(tk.END, window=marco, padx=(26, 0), pady=1)
            self.texto.insert(tk.END, "\n")
        self.texto.config(state=tk.DISABLED)
        self._al_final()

    def _alternar_datos(self, idx: int, bloques: List[Dict[str, Any]]) -> None:
        visible = not self._datos_visibles.get(idx, False)
        self._datos_visibles[idx] = visible
        if not visible:
            return
        self.texto.config(state=tk.NORMAL)
        for b in bloques:
            marco = tk.Frame(self.texto, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
            tk.Label(marco, text=b["titulo"], bg=BG_CARD, fg=TXT, font=("Segoe UI", 8, "bold"), anchor="w").pack(
                fill=tk.X, padx=8, pady=(5, 2))
            for e, v in b["filas"]:
                fila = tk.Frame(marco, bg=BG_CARD)
                fila.pack(fill=tk.X, padx=8)
                tk.Label(fila, text=e, bg=BG_CARD, fg=TXT_3, font=("Segoe UI", 8), anchor="w").pack(side=tk.LEFT)
                tk.Label(fila, text=v, bg=BG_CARD, fg="#d7dcf5", font=("Segoe UI", 8), anchor="e").pack(
                    side=tk.RIGHT)
            tk.Frame(marco, bg=BG_CARD, height=4).pack()
            self.texto.window_create(tk.END, window=marco, padx=(26, 0), pady=2)
            self.texto.insert(tk.END, "\n")
        self.texto.config(state=tk.DISABLED)
        self._al_final()

    def _pintar_error(self, mensaje: str, pregunta: str) -> None:
        self.texto.config(state=tk.NORMAL)
        self.texto.insert(tk.END, "⚠ No he podido contestar\n", "cab_agente")
        self.texto.insert(tk.END, mensaje + "\n", "error")
        btn = tk.Button(self.texto, text="Reintentar", font=("Segoe UI", 8), bg=BG_TERTIARY, fg=COLOR_PRIMARY,
                        relief=tk.FLAT, bd=0, cursor="hand2", padx=6, pady=1,
                        command=lambda: self._enviar(pregunta))
        self.texto.insert(tk.END, "   ", "meta")
        self.texto.window_create(tk.END, window=btn)
        self.texto.insert(tk.END, "\n\n", "meta")
        self.texto.config(state=tk.DISABLED)
        self._al_final()
