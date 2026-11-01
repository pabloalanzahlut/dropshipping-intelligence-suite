"""
ollama_panel.py — Panel UI para el Enrutador Híbrido Tripartito (FASE A)
=======================================================================
Muestra en una pestaña del Notebook:
    - Estado de cada capa (FreeLLMAPI / OpenRouter / Ollama)
    - Capa activa actual
    - Estadísticas de uso del pool híbrido
    - Botón de health-check manual
    - Configuración básica

Integración:
    Se agrega como pestaña en app/main.py (GEMOSApplication.__init__)
"""

import logging
import tkinter as tk
from tkinter import ttk
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class OllamaPanel(ttk.Frame):
    """
    Panel de monitoreo y control del Enrutador Híbrido Tripartito.
    Se integra como pestaña en el Notebook principal de GEM OS.
    """

    def __init__(self, parent, db_manager=None):
        super().__init__(parent)
        self.db_manager = db_manager

        # Pool híbrido (import lazy para evitar circular imports)
        self._pool = None
        self._pool_imported = False

        # Variable para actualización periódica
        self._update_job = None

        self._build_ui()
        self._refresh_status()

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        """Construye los widgets del panel."""
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ── Título ──
        title = ttk.Label(
            main_frame,
            text="🔀 Enrutador Híbrido Tripartito",
            font=("Segoe UI", 14, "bold"),
        )
        title.pack(anchor=tk.W, pady=(0, 5))

        subtitle = ttk.Label(
            main_frame,
            text="FreeLLMAPI Proxy → OpenRouter Cloud → Olama Local",
            font=("Segoe UI", 9),
            foreground="#666666",
        )
        subtitle.pack(anchor=tk.W, padx=2, pady=(0, 15))

        # ── Marco de Estado ──
        status_frame = ttk.Labelframe(main_frame, text="Estado de Capas", padding=10)
        status_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # FreeLLMAPI
        row_f = ttk.Frame(status_frame)
        row_f.pack(fill=tk.X, pady=2)
        ttk.Label(row_f, text="① FreeLLMAPI Proxy:", width=25, anchor=tk.W).pack(side=tk.LEFT)
        self._freellm_label = ttk.Label(row_f, text="⏳ verificando...", foreground="#999")
        self._freellm_label.pack(side=tk.LEFT, padx=(5, 0))

        # OpenRouter
        or_f = ttk.Frame(status_frame)
        or_f.pack(fill=tk.X, pady=2)
        ttk.Label(or_f, text="② OpenRouter API:", width=25, anchor=tk.W).pack(side=tk.LEFT)
        self._openrouter_label = ttk.Label(or_f, text="⏳ verificando...", foreground="#999")
        self._openrouter_label.pack(side=tk.LEFT, padx=(5, 0))

        # Ollama
        ollama_f = ttk.Frame(status_frame)
        ollama_f.pack(fill=tk.X, pady=2)
        ttk.Label(ollama_f, text="③ Ollama Local:", width=25, anchor=tk.W).pack(side=tk.LEFT)
        self._ollama_label = ttk.Label(ollama_f, text="⏳ verificando...", foreground="#999")
        self._ollama_label.pack(side=tk.LEFT, padx=(5, 0))

        # ── Capa Activa ──
        active_frame = ttk.LabelFrame(main_frame, text="Capa Activa Actual", padding=10)
        active_frame.pack(fill=tk.X, pady=(0, 10))

        self._active_label = ttk.Label(
            active_frame, text="🔴 Ninguna", font=("Segoe UI", 12, "bold"), foreground="#cc3333"
        )
        self._active_label.pack()

        # ── Estadísticas ──
        stats_frame = ttk.LabelFrame(main_frame, text="Estadísticas de Uso", padding=10)
        stats_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self._stats_text = tk.Text(stats_frame, height=6, width=50, font=("Consolas", 9))
        self._stats_text.pack(fill=tk.BOTH, expand=True)
        self._stats_text.config(state=tk.DISABLED)

        # ── Botones ──
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)

        ttk.Button(
            btn_frame, text="🔄 Refrescar Estado", command=self._refresh_status
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            btn_frame, text="🔍 Health Check Ollama", command=self._health_check_ollama
        ).pack(side=tk.LEFT)

    # ------------------------------------------------------------------
    # Lógica de actualización
    # ------------------------------------------------------------------

    def _get_pool(self):
        """Importa lazy el HybridInferencePool singleton."""
        if not self._pool_imported:
            try:
                from app.core.ollama_pool import HybridInferencePool
                self._pool = HybridInferencePool()
            except Exception as exc:
                print(f"[OLLAMA-PANEL] Error importando pool: {exc}")
                self._pool = None
            self._pool_imported = True
        return self._pool

    def _refresh_status(self):
        """Actualiza todos los indicadores de estado."""
        pool = self._get_pool()

        if pool is None:
            self._freellm_label.config(text="❌ Error de carga", foreground="#cc3333")
            self._openrouter_label.config(text="❌ Error de carga", foreground="#cc3333")
            self._ollama_label.config(text="❌ Error de carga", foreground="#cc3333")
            self._active_label.config(text="🔴 Pool no disponible", foreground="#cc3333")
            self._schedule_refresh()
            return

        try:
            # Capa 1: FreeLLMAPI
            f_avail = pool.is_freellm_available()
            self._freellm_label.config(
                text="✅ Disponible (Costo $0)" if f_avail else "⚠️ No configurado",
                foreground="#22c55e" if f_avail else "#999999",
            )

            # Capa 2: OpenRouter
            o_avail = pool.is_openrouter_available()
            self._openrouter_label.config(
                text="✅ Disponible" if o_avail else "⚠️ No configurado",
                foreground="#22c55e" if o_avail else "#999999",
            )

            # Capa 3: Ollama
            try:
                oll_avail = pool.is_ollama_available(force_check=True)
                self._ollama_label.config(
                    text="✅ Listo para usar" if oll_avail else "❌ No disponible",
                    foreground="#22c55e" if oll_avail else "#cc3333",
                )
            except Exception:
                self._ollama_label.config(text="❌ Error de verificación", foreground="#cc3333")

            # Capa activa
            active = pool.get_active_layer()
            labels = {
                "freellm": "🟢 FreeLLMAPI Proxy (Costo $0)",
                "openrouter": "🟡 OpenRouter Cloud",
                "ollama": "🔵 Ollama Local",
                "none": "🔴 Ninguna",
            }
            colors = {
                "freellm": "#22c55e",
                "openrouter": "#eab308",
                "ollama": "#3b82f6",
                "none": "#cc3333",
            }
            self._active_label.config(
                text=labels.get(active, "🔴 Desconocido"),
                foreground=colors.get(active, "#cc3333"),
            )

            # Estadísticas
            stats = pool.get_hybrid_stats()
            self._update_stats_text(stats)

        except Exception as exc:
            logger.warning("[OLLAMA-PANEL] Error refrescando estado: %s", exc)

        self._schedule_refresh()

    def _schedule_refresh(self):
        """Programa la próxima actualización automática (cada 10 segundos)."""
        if self._update_job:
            self.after_cancel(self._update_job)
        self._update_job = self.after(10000, self._refresh_status)

    def _update_stats_text(self, stats: dict):
        """Actualiza el widget de texto con estadísticas."""
        self._stats_text.config(state=tk.NORMAL)
        self._stats_text.delete(1.0, tk.END)

        by_layer = stats.get("by_layer", {})
        lines = [
            f"Total consultas:     {stats.get('total_queries', 0)}",
            f"FreeLLMAPI:          {by_layer.get('freellm', 0)}",
            f"OpenRouter:          {by_layer.get('openrouter', 0)}",
            f"Ollama:              {by_layer.get('ollama', 0)}",
            f"Fallos totales:      {by_layer.get('failed', 0)}",
            f"Última consulta:     {stats.get('last_query_time', 'N/A')}",
        ]
        self._stats_text.insert(1.0, "\n".join(lines))
        self._stats_text.config(state=tk.DISABLED)

    def _health_check_ollama(self):
        """Ejecuta un health-check forzado de Ollama."""
        pool = self._get_pool()
        if pool is None:
            self._ollama_label.config(text="❌ Pool no disponible", foreground="#cc3333")
            return

        self._ollama_label.config(text="⏳ Verificando...", foreground="#eab308")
        self.update_idletasks()

        try:
            avail = pool.is_ollama_available(force_check=True)
            self._ollama_label.config(
                text="✅ Listo para usar" if avail else "❌ No disponible",
                foreground="#22c55e" if avail else "#cc3333",
            )
        except Exception as exc:
            self._ollama_label.config(text=f"❌ Error: {str(exc)[:30]}", foreground="#cc3333")

    def destroy(self):
        """Limpia recursos al cerrar el panel."""
        if self._update_job:
            self.after_cancel(self._update_job)
        super().destroy()