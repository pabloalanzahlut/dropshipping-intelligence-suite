"""
KBAgentPanel - Panel del Agente IA interno (consultar_kb_agente)
Permite al operador hacer consultas en lenguaje natural a la Knowledge Base.
"""

import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import threading
import json
from datetime import datetime

from app.agents_engine.executor import AgentExecutor
from app.config.path_manager import PathManager
from app.services import store_context
from app.ui.themes.design_tokens import NEON_COLORS, DARK_BASE, TEXT_COLORS


EJEMPLOS = [
    "¿Qué productos HOT tenemos indexados esta semana?",
    "¿Qué hooks de TikTok funcionaron según la KB?",
    "¿Hay productos de fitness con margen >5x?",
    "¿Qué fuentes de tráfico recomienda la KB?",
    "¿Qué errores comunes menciona la KB?",
]


class KBAgentPanel(ttk.Frame):
    """Panel de consulta al Agente IA interno sobre la Knowledge Base."""

    def __init__(self, parent, db_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.db_manager = db_manager
        self.executor = AgentExecutor(db_manager=db_manager)
        self._build_ui()

    # ─────────────────────────── UI ────────────────────────────────

    def _build_ui(self):
        # Cabecera
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=12, pady=(10, 4))

        ttk.Label(
            header,
            text="🤖 Agente IA — Knowledge Base",
            font=("Segoe UI", 14, "bold"),
        ).pack(side=tk.LEFT)

        self._status_lbl = ttk.Label(header, text="● Listo", foreground=NEON_COLORS["green"])
        self._status_lbl.pack(side=tk.RIGHT)

        # Sección de consulta
        query_frame = ttk.LabelFrame(self, text="Consulta al Agente", padding=10)
        query_frame.pack(fill=tk.X, padx=12, pady=4)

        # Campo de texto
        self.query_text = tk.Text(
            query_frame,
            height=4,
            wrap=tk.WORD,
            bg=DARK_BASE["bg_input"],
            fg=TEXT_COLORS["primary"],
            insertbackground=NEON_COLORS["cyan"],
            relief=tk.FLAT,
            font=("Segoe UI", 11),
            padx=8,
            pady=6,
        )
        self.query_text.pack(fill=tk.X, pady=(0, 6))
        self.query_text.insert("1.0", "Escribe tu pregunta aquí...")
        self.query_text.bind("<FocusIn>", self._clear_placeholder)
        self.query_text.bind("<Return>", lambda e: self._on_consultar() or "break")

        # Botones
        btn_row = ttk.Frame(query_frame)
        btn_row.pack(fill=tk.X)

        self.btn_consultar = ttk.Button(
            btn_row, text="🔍 Consultar KB", command=self._on_consultar
        )
        self.btn_consultar.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_limpiar = ttk.Button(
            btn_row, text="🗑 Limpiar", command=self._limpiar
        )
        self.btn_limpiar.pack(side=tk.LEFT)

        # Ejemplos rápidos
        ej_frame = ttk.LabelFrame(self, text="Consultas de ejemplo (clic para usar)", padding=8)
        ej_frame.pack(fill=tk.X, padx=12, pady=4)

        for ej in EJEMPLOS:
            btn = tk.Button(
                ej_frame,
                text=ej,
                anchor="w",
                bg=DARK_BASE["bg_card"],
                fg=NEON_COLORS["cyan"],
                activebackground=DARK_BASE["bg_hover"],
                activeforeground=NEON_COLORS["blue"],
                relief=tk.FLAT,
                font=("Segoe UI", 9),
                cursor="hand2",
                padx=8,
                pady=3,
                command=lambda t=ej: self._usar_ejemplo(t),
            )
            btn.pack(fill=tk.X, pady=1)

        # Área de respuesta
        resp_frame = ttk.LabelFrame(self, text="Respuesta del Agente", padding=10)
        resp_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 10))

        self.response_text = ScrolledText(
            resp_frame,
            wrap=tk.WORD,
            bg=DARK_BASE["bg_secondary"],
            fg=TEXT_COLORS["primary"],
            font=("Consolas", 10),
            relief=tk.FLAT,
            padx=10,
            pady=8,
            state=tk.DISABLED,
        )
        self.response_text.pack(fill=tk.BOTH, expand=True)

        # Barra de metadatos
        meta = ttk.Frame(self)
        meta.pack(fill=tk.X, padx=12, pady=(0, 6))
        self._meta_lbl = ttk.Label(meta, text="", foreground=TEXT_COLORS["tertiary"])
        self._meta_lbl.pack(side=tk.LEFT)

    # ─────────────────────────── Eventos ───────────────────────────

    def _clear_placeholder(self, _event):
        content = self.query_text.get("1.0", tk.END).strip()
        if content == "Escribe tu pregunta aquí...":
            self.query_text.delete("1.0", tk.END)

    def _usar_ejemplo(self, texto: str):
        self.query_text.delete("1.0", tk.END)
        self.query_text.insert("1.0", texto)

    def _limpiar(self):
        self.query_text.delete("1.0", tk.END)
        self._set_response("")
        self._meta_lbl.config(text="")

    def _on_consultar(self):
        query = self.query_text.get("1.0", tk.END).strip()
        if not query or query == "Escribe tu pregunta aquí...":
            return
        self._set_status("⏳ Consultando...", NEON_COLORS["yellow"])
        self.btn_consultar.config(state=tk.DISABLED)
        self._set_response("Consultando la Knowledge Base…")
        threading.Thread(target=self._run_query, args=(query,), daemon=True).start()

    def _run_query(self, query: str):
        t0 = datetime.now()
        try:
            # Cifras reales de la tienda (Shopify + AutoDS) desde SQLite: el agente no inventa ventas
            db_path = getattr(self.db_manager, "db_path", None) or str(PathManager.get_paths()["db"])
            bloque = store_context.bloque_para_prompt(db_path)
            result = self.executor.execute_agent_task(
                agent_name="consultar_kb_agente",
                skill_name="consultar_kb_agente",
                project_name="kb_query",
                user_request=f"{bloque}PREGUNTA DEL OPERADOR:
{query}" if bloque else query,
            )
            elapsed = (datetime.now() - t0).total_seconds()
            self._show_result(result, elapsed, bool(bloque))
        except Exception as e:
            self._show_error(str(e))

    # ─────────────────────────── Display ───────────────────────────

    def _show_result(self, raw: str, elapsed: float, con_tienda: bool = False):
        try:
            data = json.loads(raw)
            formatted = json.dumps(data, ensure_ascii=False, indent=2)
            confianza = data.get("confianza", "?")
            tipo = data.get("tipo_consulta", "?")
            meta = f"Tipo: {tipo}  |  Confianza: {confianza}  |  {elapsed:.1f}s"
        except json.JSONDecodeError:
            formatted = raw
            meta = f"Respuesta en texto plano  |  {elapsed:.1f}s"

        if con_tienda:
            meta += "  |  con datos de la tienda"
        self.after(0, lambda: (
            self._set_response(formatted),
            self._set_status("● Listo", NEON_COLORS["green"]),
            self._meta_lbl.config(text=meta),
            self.btn_consultar.config(state=tk.NORMAL),
        ))

    def _show_error(self, error: str):
        msg = f"[ERROR]\n{error}\n\nVerifica que OPENROUTER_API_KEY esté configurada en .env"
        self.after(0, lambda: (
            self._set_response(msg),
            self._set_status("● Error", NEON_COLORS["pink"]),
            self.btn_consultar.config(state=tk.NORMAL),
        ))

    def _set_response(self, text: str):
        self.response_text.config(state=tk.NORMAL)
        self.response_text.delete("1.0", tk.END)
        self.response_text.insert("1.0", text)
        self.response_text.config(state=tk.DISABLED)

    def _set_status(self, text: str, color: str):
        self._status_lbl.config(text=text, foreground=color)
