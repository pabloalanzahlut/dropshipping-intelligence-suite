
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from dotenv import load_dotenv

from app.ui.themes import DarkTheme, LightTheme
from app.ui.components import StatusIndicator, ConsoleView
from app.ui.components.navigation_v2 import Sidebar
from app.ui.components.dashboard_panel import DashboardPanel
from app.ui.components.financial_validator_panel_v2 import FinancialValidatorPanel
from app.ui.components.youtube_monitor_panel import YouTubeMonitorPanel
from app.ui.components.copywriting_panel import CopywritingPanel
from app.ui.components.tiktok_panel import TikTokPanel
from app.ui.components.governance_panel import GovernancePanel
from app.ui.components.ollama_panel import OllamaPanel
from app.ui.components.kb_agent_panel import KBAgentPanel
from app.database.connection import DatabaseConnection
from app.ui.themes.design_tokens import NEON_COLORS, DARK_BASE, TEXT_COLORS
from app.ui.themes.jack_styles import apply_jack_styles
from app.services.provider_monitor_engine import ProviderMonitorEngine

ERROR_COLOR = NEON_COLORS["pink"]


class GEMOSApplication:
    def __init__(self, root: tk.Tk, initial_theme: str = "dark"):
        self.root = root
        self.root.title("💎 GEM OS v3.0 • Premium Intelligence Suite")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # Configurar colores de ventana
        self.root.configure(bg=DARK_BASE['bg_primary'])
        
        # Aplicar estilos Jack premium
        apply_jack_styles(self.root)
        
        self._current_theme_name: str = initial_theme
        self._themes = {"dark": DarkTheme(), "light": LightTheme()}
        self._current_theme = self._themes[initial_theme]
        self._current_theme.apply()
        load_dotenv()
        self.console_view = None
        self._verify_environment()
        self.db_manager = DatabaseConnection()
        self._panels = []
        self._build_main_layout()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._log("💎 GEM OS v3.0 iniciado correctamente.")

    def _build_main_layout(self):
        """Sidebar premium + toolbar neon + contenedor de paneles."""
        # Main container con glassmorphism
        mc = tk.Frame(self.root, bg=DARK_BASE['bg_primary'])
        mc.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Sidebar premium
        self.sidebar = Sidebar(mc, items=[
            ("🏠", "Dashboard", lambda: self._show(0)),
            ("💎", "Validador", lambda: self._show(1)),
            ("▶️", "YouTube",   lambda: self._show(2)),
            ("✍️", "Copys",     lambda: self._show(3)),
            ("🎵", "TikTok",   lambda: self._show(4)),
            ("📋", "Gobernanza", lambda: self._show(5)),
            ("🔗", "Enrutador", lambda: self._show(6)),
            ("📥", "Ingesta",  lambda: self._show(7)),
            ("🤖", "Agente IA", lambda: self._show(8)),
        ])
        self.sidebar.grid(row=0, column=0, sticky="ns")
        
        # Content frame con padding
        cf = tk.Frame(mc, bg=DARK_BASE['bg_primary'])
        cf.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        mc.columnconfigure(1, weight=1)
        mc.rowconfigure(0, weight=1)
        self._content = cf
        
        # Toolbar premium con glassmorphism
        tb = tk.Frame(cf, bg=DARK_BASE['bg_secondary'], height=50)
        tb.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        
        # Tema selector (minimalista)
        self.theme_frame = tk.Frame(tb, bg=DARK_BASE['bg_secondary'])
        self.theme_frame.pack(side=tk.LEFT, padx=15, pady=8)
        
        self.theme_icon = tk.Label(self.theme_frame, text="🎨", font=("Segoe UI", 12),
                bg=DARK_BASE['bg_secondary'], fg=TEXT_COLORS['primary'])
        self.theme_icon.pack(side=tk.LEFT, padx=(0, 8))
        
        self._tv = tk.StringVar(value=self._current_theme_name)
        self.theme_radiobuttons = []
        for lb, val in [("🌙", "dark"), ("☀️", "light")]:
            rb = tk.Radiobutton(self.theme_frame, text=lb, variable=self._tv, value=val,
                              command=self._on_theme_changed,
                              bg=DARK_BASE['bg_secondary'], fg=TEXT_COLORS['secondary'],
                              selectcolor=DARK_BASE['bg_input'],
                              activebackground=DARK_BASE['bg_hover'],
                              font=("Segoe UI", 11))
            rb.pack(side=tk.LEFT, padx=2)
            self.theme_radiobuttons.append(rb)
        
        # Separador vertical
        tk.Frame(tb, bg=TEXT_COLORS['tertiary'], width=1).pack(side=tk.LEFT, fill=tk.Y, padx=15, pady=8)
        
        # Status indicators con neon
        indicators_frame = tk.Frame(tb, bg=DARK_BASE['bg_secondary'])
        indicators_frame.pack(side=tk.RIGHT, padx=15, pady=8)
        
        or_key = os.getenv("OPENROUTER_API_KEY", "")
        if or_key:
            self._api_st = StatusIndicator(indicators_frame, status="ok", text="API Key")
        else:
            self._api_st = StatusIndicator(indicators_frame, status="error", text="Sin API")
        self._api_st.pack(side=tk.RIGHT, padx=6)
        
        self._sync_st = StatusIndicator(indicators_frame, status="neutral", text="Inactivo")
        self._sync_st.pack(side=tk.RIGHT, padx=6)
        
        # Sync button (neon style)
        sync_btn_frame = tk.Frame(tb, bg=DARK_BASE['bg_secondary'])
        sync_btn_frame.pack(side=tk.RIGHT, padx=10)
        
        sync_btn = tk.Button(sync_btn_frame, text="🔄 Sincronizar",
                           command=self._on_global_sync,
                           bg=DARK_BASE['bg_input'], fg=NEON_COLORS['cyan'],
                           font=("Segoe UI", 9, "bold"),
                           relief=tk.FLAT, padx=15, pady=6,
                           cursor="hand2")
        sync_btn.pack()
        
        # Panel container
        pc = tk.Frame(cf, bg=DARK_BASE['bg_primary'])
        pc.grid(row=1, column=0, sticky="nsew", pady=(0, 0))
        cf.columnconfigure(0, weight=1)
        cf.rowconfigure(1, weight=1)
        pc.columnconfigure(0, weight=1)
        pc.rowconfigure(0, weight=1)
        self._pc = pc
        self._create_panels()
        self._show(0)

    def _create_panels(self):
        """Crea todos los paneles en frames apilables con lazy loading."""
        specs = [
            ("Dashboard", lambda: DashboardPanel(self._pc, db_manager=self.db_manager)),
            ("Validador", lambda: FinancialValidatorPanel(self._pc, db_manager=self.db_manager)),
            ("YouTube", lambda: YouTubeMonitorPanel(self._pc, db_manager=self.db_manager)),
            ("Copys", lambda: CopywritingPanel(self._pc, db_manager=self.db_manager)),
            ("TikTok", lambda: TikTokPanel(self._pc, db_manager=self.db_manager)),
            ("Gobernanza", lambda: GovernancePanel(self._pc, db_manager=self.db_manager)),
            ("Enrutador", lambda: OllamaPanel(self._pc, db_manager=self.db_manager)),
            ("Ingesta", self._build_console),
            ("Agente IA", lambda: KBAgentPanel(self._pc, db_manager=self.db_manager)),
        ]
        self._panel_factories = specs
        self._panel_loaded = [False] * len(specs)
        for i, (name, factory) in enumerate(specs):
            f = ttk.Frame(self._pc)
            # Todos los paneles comparten la celda (0,0): solo uno visible a la vez
            f.grid(row=0, column=0, sticky="nsew")
            f.grid_remove()  # Hide initially
            ttk.Label(f, text="Cargando...", foreground="#888").pack(pady=20)
            self._panels.append(f)
        self._panel_loaded[0] = True
        try:
            p = specs[0][1]()
            self._panels[0].panel_ref = p
            for w in self._panels[0].winfo_children():
                w.destroy()
            p.grid(row=0, column=0, sticky="nsew")
            self._panels[0].columnconfigure(0, weight=1)
            self._panels[0].rowconfigure(0, weight=1)
        except Exception as e:
            ttk.Label(self._panels[0], text=f"Error Dashboard: {e}", foreground=ERROR_COLOR).pack(pady=20)

    def _build_console(self):
        """Construye panel de consola de ingesta."""
        cv = ConsoleView(self._panels[7],
            start_sync_callback=lambda v: self.trigger_pipeline_ingestion(v),
            theme=self._current_theme,
            title="GEM OS • Monitor de Ingesta de Conocimiento")
        cv.pack(fill=tk.BOTH, expand=True)
        self.console_view = cv
        return cv

    def _show(self, idx: int):
        """Muestra panel idx con lazy loading."""
        for i, f in enumerate(self._panels):
            if i == idx:
                f.grid()  # Show via grid (was hidden with grid_remove)
                if not self._panel_loaded[i]:
                    self._panel_loaded[i] = True
                    self.root.after(50, lambda i=i: self._load_panel(i))
            else:
                f.grid_remove()  # Hide via grid (not remove completely)

    def _load_panel(self, idx: int):
        """Carga un panel bajo demanda."""
        if idx >= len(self._panel_factories):
            return
        name, factory = self._panel_factories[idx]
        frame = self._panels[idx]
        for w in frame.winfo_children():
            w.destroy()
        try:
            panel = factory()
            frame.panel_ref = panel
            panel.grid(row=0, column=0, sticky="nsew")
            frame.columnconfigure(0, weight=1)
            frame.rowconfigure(0, weight=1)
            self._log(f"Panel cargado: {name}")
        except Exception as e:
            ttk.Label(frame, text=f"Error {name}: {e}", foreground=ERROR_COLOR).pack(pady=20)
            self._log(f"Error cargando panel {name}: {e}")

    def _log(self, msg: str, level: str = "SYSTEM"):
        if self.console_view and hasattr(self.console_view, 'write_log'):
            self.console_view.write_log(msg, level=level)
        else:
            import sys
            try:
                sys.stdout.write(f"[{level}] {msg}\n")
                sys.stdout.flush()
            except:
                pass

    def _on_global_sync(self):
        self._sync_st.set_status("info", "Sincronizando...")
        if self.console_view:
            self.trigger_pipeline_ingestion(self.console_view)

    def _verify_environment(self):
        from app.services.openrouter_client import sanitize_api_key
        keys_status = []
        or_key = os.getenv("OPENROUTER_API_KEY", "")
        fl_key = os.getenv("FREELLM_API_KEY", "")
        anth_key = os.getenv("ANTHROPIC_API_KEY", "")
        if or_key:
            keys_status.append(f"OpenRouter: {sanitize_api_key(or_key)}")
        else:
            keys_status.append("OpenRouter: No configurada")
        if fl_key:
            keys_status.append(f"FreeLLMAPI: {sanitize_api_key(fl_key)}")
        else:
            keys_status.append("FreeLLMAPI: No configurada (opcional)")
        if anth_key:
            keys_status.append(f"Anthropic: {sanitize_api_key(anth_key)}")
        else:
            keys_status.append("Anthropic: No configurada (opcional)")
        budget = os.getenv("AI_MONTHLY_BUDGET_USD", "20.0")
        keys_status.append(f"Presupuesto mensual: ${budget} USD")
        if not or_key and not fl_key and not anth_key:
            messagebox.showwarning(
                "Sin APIs Configuradas",
                "No se detectaron API keys de IA.\n\n"
                "El software funcionara en modo offline con:\n"
                "* Templates locales de copywriting\n"
                "* Ollama local (si esta instalado)\n"
                "* Cache de KB existente\n\n"
                "Configura OPENROUTER_API_KEY en .env para funcionalidad completa."
            )
        else:
            status_msg = "\n".join(keys_status)
            self._log(f"🔑 APIs: {status_msg}")

    def _on_theme_changed(self) -> None:
        new_theme = self._tv.get()
        if new_theme == self._current_theme_name:
            return
        self._current_theme_name = new_theme
        self._current_theme = self._themes[new_theme]
        self._current_theme.apply()
        
        # Actualizar los colores de fondo de los frames principales
        self.root.configure(bg=self._current_theme.bg_primary)
        
        # Actualizar el toolbar y selector de tema
        if hasattr(self, 'theme_frame'):
            self.theme_frame.configure(bg=self._current_theme.bg_secondary)
        if hasattr(self, 'theme_icon'):
            self.theme_icon.configure(bg=self._current_theme.bg_secondary, 
                                     fg=self._current_theme.fg_primary)
        if hasattr(self, 'theme_radiobuttons'):
            for rb in self.theme_radiobuttons:
                rb.configure(bg=self._current_theme.bg_secondary,
                           fg=self._current_theme.fg_secondary,
                           selectcolor=self._current_theme.bg_tertiary,
                           activebackground=self._current_theme.accent)
        
        # Actualizar todos los frames y widgets recursivamente
        self._apply_theme_recursive(self.root)
        
        if self.console_view:
            self.console_view.apply_theme(self._current_theme)
            self._log(f"🎨 Tema cambiado a: {new_theme.upper()}")
    
    def _apply_theme_recursive(self, widget):
        """Aplica el tema recursivamente a todos los widgets."""
        try:
            # Actualizar el widget actual según su tipo
            if isinstance(widget, tk.Frame):
                # Solo actualizar frames que no tengan colores personalizados
                current_bg = widget.cget('bg')
                if current_bg in [DARK_BASE['bg_primary'], DARK_BASE['bg_secondary'], 
                                 DARK_BASE['bg_tertiary'], "#f9fafb", "#ffffff", "#fafafa"]:
                    widget.configure(bg=self._current_theme.bg_primary)
            elif isinstance(widget, tk.Label):
                # Solo actualizar labels que no tengan colores neon/personalizados
                current_fg = widget.cget('fg')
                if current_fg not in [NEON_COLORS.get('cyan', ''), NEON_COLORS.get('purple', '')]:
                    widget.configure(bg=self._current_theme.bg_primary, 
                                   fg=self._current_theme.fg_primary)
            elif isinstance(widget, tk.Button):
                # Mantener los colores personalizados de botones especiales
                pass
            
            # Recursivamente aplicar a los hijos
            for child in widget.winfo_children():
                self._apply_theme_recursive(child)
        except:
            pass

    def trigger_pipeline_ingestion(self, view_instance):
        view_instance.write_log("[ORQUESTADOR] Preparando entorno de sincronizacion...", level="SYSTEM")
        def worker_task():
            try:
                engine = ProviderMonitorEngine(db_manager=self.db_manager)
                engine.log_callback = lambda msg: view_instance.write_log(msg, level="INFO")
                engine.progress_callback = view_instance.update_progress
                view_instance.write_log("[ORQUESTADOR] Iniciando escaneo e ingesta masiva de canales favoritos...", level="INFO")
                engine.run_global_ingestion()
                view_instance.write_log("[SISTEMA] Sincronizacion Maestra finalizada con exito.", level="OK")
            except Exception as e:
                view_instance.write_log(f"[CRITICO - MAIN] Fallo en la cadena de ejecucion: {str(e)}", level="CRITICAL")
                import traceback
                view_instance.write_log(traceback.format_exc(), level="CRITICAL")
        threading.Thread(target=worker_task, daemon=True).start()

    def _on_close(self):
        self._log("GEM OS cerrando sesion...")
        self.root.destroy()

def main():
    """Entry point corporativo de la Suite."""
    # Arranque silencioso de Ollama (capa 3 del enrutador hibrido)
    try:
        from app.core.ollama_startup_engine import OllamaStartupEngine
        ollama_ok = OllamaStartupEngine.launch_local_ollama_silently()
        if ollama_ok:
            print("[OLLAMA] Capa local disponible.")
        else:
            print("[OLLAMA] No disponible. Se usara solo Cloud (FreeLLMAPI/OpenRouter).")
    except Exception as exc:
        print(f"[OLLAMA] Error en pre-flight: {exc}. Continuando sin capa local.")
    root = tk.Tk()
    app = GEMOSApplication(root, initial_theme="dark")
    root.mainloop()

if __name__ == "__main__":
    main()
