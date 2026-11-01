"""
ConsoleView Mejorada — Terminal minimalista de logs en vivo + botón trigger + barra de progreso.

Mejoras sobre la versión original:
  1. LOGS COLOREADOS por nivel (SYSTEM, INFO, OK, WARNING, ERROR, CRITICAL, DEBUG)
  2. Timestamp automático en cada entrada
  3. Toggle Auto-Scroll (seguir o no el último log)
  4. Botón Limpiar consola
  5. Botón Sincronizar con máquina de estados (idle → running → done/error)
  6. Última sincronización visible
  7. Contador de líneas / badge de nivel activo
  8. Integración con sistema de temas (Dark/Light)
  9. Barra de progreso desacoplada vía ProgressBar component
 10. API write_log con nivel semántico: write_log("texto", level="INFO")
"""

import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import threading
import queue
import time
from datetime import datetime
from typing import Optional, Callable

from app.ui.components.progress_bar import ProgressBar


class ConsoleView(ttk.Frame):
    """Terminal de logs en vivo con controles y barra de progreso integrada.

    Args:
        parent: Widget padre ttk.
        start_sync_callback: Callable[[ConsoleView], None] — se dispara al pulsar sincronizar.
        theme: Instancia de BaseTheme (DarkTheme/LightTheme) para colores.
        title: Título del panel.
    """

    # Niveles de log con prioridad (menor = más importante)
    LOG_LEVELS = {
        "CRITICAL": 0,
        "ERROR": 1,
        "WARNING": 2,
        "OK": 3,
        "INFO": 4,
        "SYSTEM": 5,
        "DEBUG": 6,
    }

    def __init__(
        self,
        parent,
        start_sync_callback: Optional[Callable] = None,
        theme=None,
        title: str = "GEM OS • Monitor de Ingesta de Conocimiento",
    ):
        super().__init__(parent)
        self.start_sync_callback = start_sync_callback
        self.theme = theme
        self._title = title

        # Cola thread-safe para logs desde hilos secundarios
        self.log_queue: queue.Queue = queue.Queue()

        # Estado interno
        self._sync_state: str = "idle"       # idle | running | done | error
        self._auto_scroll: bool = True
        self._line_count: int = 0
        self._last_sync_time: Optional[str] = None
        self._last_sync_status: str = ""
        self._active_level: str = "INFO"
        self._min_priority: int = 4  # mostrar INFO y superiores por defecto

        # Construir UI
        self._setup_styles()
        self._create_widgets()

        # Bucle de procesamiento de cola
        self.after(100, self._process_log_queue)

    def _setup_styles(self):
        """Define la estética corporativa y limpia de la interfaz."""
        style = ttk.Style()
        style.configure("ConsoleButton.TButton", font=("Helvetica", 10, "bold"), padding=6)
        style.configure("ConsoleProgress.Horizontal.TProgressbar", thickness=15)

    def _create_widgets(self):
        """Construye las 4 secciones del panel de control general."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # ================================================================
        # 1. ENCABEZADO + TRIGGER MANUAL + CONTROLES
        # ================================================================
        top_frame = ttk.Frame(self, padding=10)
        top_frame.grid(row=0, column=0, sticky="ew")
        top_frame.columnconfigure(0, weight=1)

        self._title_label = ttk.Label(
            top_frame,
            text=self._title,
            font=("Helvetica", 12, "bold"),
        )
        self._title_label.grid(row=0, column=0, sticky="w")

        # --- Botones de control (fila derecha) ---
        btn_container = ttk.Frame(top_frame)
        btn_container.grid(row=0, column=1, sticky="e")

        # Toggle auto-scroll
        self.auto_scroll_btn = ttk.Button(
            btn_container,
            text="🔽 Auto-Scroll: ON",
            command=self._toggle_auto_scroll,
        )
        self.auto_scroll_btn.pack(side=tk.RIGHT, padx=2)

        # Botón limpiar consola
        self.clear_btn = ttk.Button(
            btn_container,
            text="🧹 Limpiar",
            command=self._clear_console,
        )
        self.clear_btn.pack(side=tk.RIGHT, padx=2)

        # Botón sincronizar (trigger manual)
        self.sync_button = ttk.Button(
            btn_container,
            text="🚀 Sincronizar",
            style="ConsoleButton.TButton",
            command=self._on_sync_pressed,
        )
        self.sync_button.pack(side=tk.RIGHT, padx=2)

        # ================================================================
        # 2. CONSOLA DE LOGS EN VIVO (terminal oscuro)
        # ================================================================
        middle_frame = ttk.Frame(self, padding=(10, 2, 10, 2))
        middle_frame.grid(row=1, column=0, sticky="nsew")
        middle_frame.columnconfigure(0, weight=1)
        middle_frame.rowconfigure(1, weight=1)

        # Info bar (última sync + contador)
        self.info_bar = ttk.Label(
            middle_frame,
            text="🟢 Listo — 0 líneas",
            font=("Helvetica", 8),
            foreground="#a0a0a0",
        )
        self.info_bar.grid(row=0, column=0, sticky="ew", pady=(0, 2))

        self.text_area = ScrolledText(
            middle_frame,
            wrap=tk.WORD,
            background="#1e1e1e",
            foreground="#4af626",
            insertbackground="white",
            font=("Consolas", 10),
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
        )
        self.text_area.grid(row=1, column=0, sticky="nsew")
        self.text_area.configure(state='disabled')

        # ================================================================
        # 3. BARRA DE PROGRESO MEJORADA (ProgressBar component)
        # ================================================================
        self.progress = ProgressBar(
            self,
            label_text="Progreso: 0%",
            determinate=True,
            theme=self.theme,
        )
        self.progress.grid(row=2, column=0, sticky="ew", pady=(4, 2))

        # ================================================================
        # 4. BARRA DE ESTADO FINAL (footer metadata)
        # ================================================================
        self._status_bar = ttk.Label(
            self,
            text="⚡ GEM OS • Dropshipping Intelligence Suite",
            font=("Helvetica", 7),
            foreground="#666666",
            anchor="w",
        )
        self._status_bar.grid(row=3, column=0, sticky="ew")

        # --- Log intro ---
        self.write_log("⎯" * 50, level="SYSTEM")
        self.write_log(f"🚀 {self._title} — Inicializado", level="SYSTEM")
        self.write_log(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", level="SYSTEM")
        self.write_log("⌨️  Listo para sincronizar. Presiona '🚀 Sincronizar' para comenzar.", level="SYSTEM")
        self.write_log("⎯" * 50, level="SYSTEM")

    # ------------------------------------------------------------------
    # API PÚBLICA
    # ------------------------------------------------------------------

    def write_log(self, text: str, level: str = "INFO") -> None:
        """Registra un mensaje en la consola con nivel semántico.

        Args:
            text: Contenido del mensaje.
            level: Nivel del log (CRITICAL, ERROR, WARNING, OK, INFO, SYSTEM, DEBUG).
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put((timestamp, level.upper(), text))

    def write_log_from_thread(self, text: str, level: str = "INFO") -> None:
        """Alias thread-safe de write_log."""
        self.write_log(text, level)

    def update_progress(self, value: float) -> None:
        """Actualiza el valor de la barra de progreso (0–100)."""
        self.progress.set_value(value)

    def set_progress_status(self, text: str) -> None:
        """Establece el texto de estado en la barra de progreso."""
        self.progress.set_status(text)

    def set_progress_eta(self, eta_text: str) -> None:
        """Establece el texto de ETA en la barra de progreso."""
        self.progress.set_eta(eta_text)

    def set_sync_state(self, state: str) -> None:
        """Cambia el estado visual del botón de sincronización.
        Estados: idle, running, done, error.
        """
        self._sync_state = state
        self._update_sync_button_ui()

    def get_sync_state(self) -> str:
        return self._sync_state

    # ------------------------------------------------------------------
    # MANEJO DE LOGS (procesamiento de cola + renderizado)
    # ------------------------------------------------------------------

    def _process_log_queue(self) -> None:
        """Vacía la cola de logs y los renderiza con color según nivel."""
        while not self.log_queue.empty():
            try:
                timestamp, level, msg = self.log_queue.get_nowait()

                # Filtro por prioridad mínima
                msg_priority = self.LOG_LEVELS.get(level, 4)
                if msg_priority > self._min_priority:
                    continue

                color = self._get_log_color(level)
                tag = level.upper().ljust(8)
                formatted = f"[{timestamp}] [{tag}] {msg}"

                self.text_area.configure(state='normal')
                self.text_area.insert(tk.END, formatted + "\n")
                self._apply_color_tag(level)
                self.text_area.configure(state='disabled')

                self._line_count += 1
                self._active_level = level

            except queue.Empty:
                break

        if self._auto_scroll:
            try:
                self.text_area.see(tk.END)
            except Exception:
                pass

        self._update_info_bar()
        self.after(100, self._process_log_queue)

    def _apply_color_tag(self, level: str) -> None:
        """Aplica color a la última línea insertada según nivel del log."""
        color = self._get_log_color(level)
        try:
            start = self.text_area.index("end-1 lines linestart")
            end = self.text_area.index("end-1 lines lineend")
            tag_name = f"clr_{level}_{self._line_count}"
            self.text_area.tag_config(tag_name, foreground=color)
            self.text_area.tag_add(tag_name, start, end)
        except Exception:
            pass

    def _get_log_color(self, level: str) -> str:
        """Retorna el color hex para un nivel de log, desde el tema o fallback."""
        if self.theme:
            return self.theme.get_log_color(level)
        palette = {
            "CRITICAL": "#d50000", "ERROR": "#ff1744",
            "WARNING": "#ffd54f", "OK": "#00c853",
            "INFO": "#4af626", "SYSTEM": "#8a8a8a", "DEBUG": "#6a1b9a",
        }
        return palette.get(level.upper(), "#4af626")

    def _update_info_bar(self) -> None:
        """Actualiza la barra de información (última sync, contador líneas)."""
        sync_info = ""
        if self._last_sync_time:
            icon = "✅" if self._last_sync_status == "done" else "❌"
            sync_info = f" | Última sync: {self._last_sync_time} {icon}"
        scroll_icon = "🔽" if self._auto_scroll else "🔒"
        self.info_bar["text"] = (
            f"{scroll_icon} Auto-Scroll: {'ON' if self._auto_scroll else 'OFF'} — "
            f"{self._line_count} líneas{sync_info}"
        )

    # ------------------------------------------------------------------
    # BOTÓN DE SINCRONIZACIÓN (trigger manual mejorado)
    # ------------------------------------------------------------------

    def _on_sync_pressed(self) -> None:
        """Maneja el clic del botón de sincronización."""
        if self._sync_state == "running":
            self.write_log("[SISTEMA] Ya hay una sincronización en curso.", level="WARNING")
            return
        if not self.start_sync_callback:
            self.write_log("[CRÍTICO] No hay callback configurado.", level="ERROR")
            return
        self.progress.reset()
        self.progress.set_status("Iniciando sincronización...")
        self.set_sync_state("running")
        self.sync_button.configure(state='disabled')
        self.write_log("⎯" * 50, level="SYSTEM")
        self.write_log(f"🚀 Sincronización iniciada — {datetime.now().strftime('%H:%M:%S')}", level="SYSTEM")
        self.write_log("⎯" * 50, level="SYSTEM")
        threading.Thread(target=self._execute_sync_task, daemon=True).start()

    def _execute_sync_task(self) -> None:
        """Ejecuta callback de sincronización en un hilo separado."""
        try:
            self.start_sync_callback(self)
            self._on_sync_success()
        except Exception as e:
            self._on_sync_error(e)

    def _on_sync_success(self) -> None:
        """Callback de finalización exitosa de la sincronización."""
        self._last_sync_time = datetime.now().strftime("%H:%M:%S")
        self._last_sync_status = "done"
        self.set_sync_state("done")
        self.progress.complete()
        self.write_log("⎯" * 50, level="SYSTEM")
        self.write_log("✅ Sincronización completada exitosamente.", level="OK")
        self.write_log(f"🕐 Finalizado: {self._last_sync_time}", level="SYSTEM")
        self.write_log("⎯" * 50, level="SYSTEM")
        self.after(0, lambda: self.sync_button.configure(state='normal'))

    def _on_sync_error(self, exc: Exception) -> None:
        """Callback de error en sincronización."""
        self._last_sync_time = datetime.now().strftime("%H:%M:%S")
        self._last_sync_status = "error"
        self.set_sync_state("error")
        self.write_log("⎯" * 50, level="SYSTEM")
        self.write_log(f"❌ Error: {str(exc)}", level="CRITICAL")
        self.write_log(f"🕐 Fallo: {self._last_sync_time}", level="SYSTEM")
        self.write_log("⎯" * 50, level="SYSTEM")
        self.progress.set_value(0)
        self.progress.set_status("⚠️ Error — reintenta")
        self.after(0, lambda: self.sync_button.configure(state='normal'))

    def _update_sync_button_ui(self) -> None:
        """Actualiza el texto del botón según el estado."""
        icons = {
            "idle": "🚀 Sincronizar",
            "running": "⏳ Sincronizando...",
            "done": "✅ Sincronizado",
            "error": "⚠️ Reintentar",
        }
        self.sync_button["text"] = icons.get(self._sync_state, "🚀 Sincronizar")

    # ------------------------------------------------------------------
    # CONTROLES DE CONSOLA
    # ------------------------------------------------------------------

    def _toggle_auto_scroll(self) -> None:
        """Activa/desactiva el auto-scroll de la consola."""
        self._auto_scroll = not self._auto_scroll
        self.auto_scroll_btn["text"] = f"🔽 Auto-Scroll: {'ON' if self._auto_scroll else 'OFF'}"
        self._update_info_bar()
        if self._auto_scroll:
            try:
                self.text_area.see(tk.END)
            except Exception:
                pass

    def _clear_console(self) -> None:
        """Limpia todo el contenido de la consola de logs."""
        self.text_area.configure(state='normal')
        self.text_area.delete("1.0", tk.END)
        self.text_area.configure(state='disabled')
        self._line_count = 0
        self._update_info_bar()
        self.write_log("🧹 Consola limpiada.", level="SYSTEM")

    def apply_theme(self, theme) -> None:
        """Aplica un tema visual (colores) a la consola y sus componentes."""
        self.theme = theme
        self.text_area.configure(
            background=theme.console_bg,
            foreground=theme.console_fg,
        )
        self.progress._theme = theme
        self._update_info_bar()
