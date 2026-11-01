"""
governance_panel.py — Panel de Control de Gobernanza GEM OS v2.0
Tab en la UI que muestra:
- Cumplimiento de reglas (status de las 4 metodologías)
- Memoria activa de agentes (bitácora visible)
- Violaciones de protocolo
- Score de cumplimiento
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from app.database.connection import DatabaseConnection
from app.services.validator_rules import RulesValidator
from app.services.memory_logger import MemoryLogger
from app.services.protocol_enforcer import ProtocolEnforcer


class GovernancePanel(ttk.Frame):
    """Panel de Control de Gobernanza — Auditoría de cumplimiento."""

    def __init__(self, parent, db_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.db_manager = db_manager if db_manager else DatabaseConnection()
        self.validator = RulesValidator(db_manager=self.db_manager)
        self.memory = MemoryLogger(db_manager=self.db_manager)
        self.enforcer = ProtocolEnforcer(validator=self.validator)
        self._build_ui()
        self._refrescar()

    # ─────────────── UI ───────────────

    def _build_ui(self):
        """Construye el layout del panel de gobernanza."""

        # ===== Fila Superior: Score de Cumplimiento =====
        score_frame = ttk.LabelFrame(self, text="Score de Cumplimiento General", padding=10)
        score_frame.pack(fill=tk.X, padx=10, pady=5)

        score_grid = ttk.Frame(score_frame)
        score_grid.pack(fill=tk.X, pady=4)

        # Tarjetas de métricas
        self._crear_tarjeta(score_grid, "Cumplimiento", "0%", 0, "#4CAF50")
        self._crear_tarjeta(score_grid, "Validaciones", "0", 1, "#2196F3")
        self._crear_tarjeta(score_grid, "Violaciones", "0", 2, "#FF9800")
        self._crear_tarjeta(score_grid, "Memoria Activa", "0", 3, "#E91E63")

        # ===== Fila Media: Estado de Metodologías =====
        rules_frame = ttk.LabelFrame(self, text="Estado de las 4 Metodologías", padding=10)
        rules_frame.pack(fill=tk.X, padx=10, pady=5)

        self.rules_text = tk.Text(rules_frame, height=8, wrap=tk.WORD, font=("Consolas", 9))
        self.rules_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ===== Fila Inferior: Logs de Memoria =====
        mem_frame = ttk.LabelFrame(self, text="Bitácora de Memoria Activa (últimas entradas)", padding=10)
        mem_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("Timestamp", "Agente", "Tipo", "Resumen")
        self.mem_tree = ttk.Treeview(mem_frame, columns=columns, height=10)
        self.mem_tree.heading("#0", text="#")
        self.mem_tree.column("#0", width=30)
        for col in columns:
            self.mem_tree.heading(col, text=col)
            self.mem_tree.column(col, width=130)

        scroll_mem = ttk.Scrollbar(mem_frame, orient=tk.VERTICAL, command=self.mem_tree.yview)
        self.mem_tree.configure(yscroll=scroll_mem.set)
        self.mem_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_mem.pack(side=tk.RIGHT, fill=tk.Y)

        # ===== Botones de Acción =====
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(btn_frame, text="🔄 Refrescar", command=self._refrescar).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔍 Verificar agent.md", command=self._check_agent_md).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🧹 Limpiar Memoria", command=self._clear_memory).pack(side=tk.LEFT, padx=5)

    # ─────────────── Helpers UI ───────────────

    def _crear_tarjeta(self, parent, label, value, col, color):
        """Crea una tarjeta KPI estilizada."""
        card = tk.Frame(parent, bg=color, highlightbackground=color, width=180, height=80)
        card.grid(row=0, column=col, padx=8, pady=5)
        card.pack_propagate(False)

        lbl = tk.Label(card, text=label, fg="white", bg=color, font=("Segoe UI", 9, "bold"))
        lbl.pack(pady=(4, 0))

        val_lbl = tk.Label(card, text=value, fg="white", bg=color, font=("Segoe UI", 18, "bold"))
        val_lbl.pack(pady=(0, 4))
        val_lbl._g_key = label

        if not hasattr(self, '_kpi_labels'):
            self._kpi_labels = {}
        self._kpi_labels[label] = val_lbl

    def _refrescar(self):
        """Refresca todos los datos del panel."""
        self._actualizar_score()
        self._actualizar_metodologias()
        self._actualizar_memoria()

    def _actualizar_score(self):
        """Actualiza las tarjetas KPI."""
        score = self.validator.compliance_score()
        mem_stats = self.memory.memory_stats()

        if hasattr(self, '_kpi_labels'):
            self._kpi_labels["Cumplimiento"].config(text=f"{score.get('compliance_score', 0)}%")
            col = {'GREEN': '#4CAF50', 'YELLOW': '#FF9800', 'RED': '#E91E63'}.get(score.get('status'), '#4CAF50')
            self._kpi_labels["Cumplimiento"].master.config(bg=col)
            self._kpi_labels["Cumplimiento"].config(bg=col)
            self._kpi_labels["Validaciones"].config(text=str(score.get('total_checks', 0)))
            self._kpi_labels["Violaciones"].config(text=str(score.get('violaciones_activas', 0)))
            self._kpi_labels["Memoria Activa"].config(text=str(mem_stats.get('total_entries', 0)))

    def _actualizar_metodologias(self):
        """Actualiza el estado de las 4 metodologias."""
        check = self.validator.pre_execution_check()
        resultados = check.get('resultados', {})
        items = {
            'agent_md_loaded': ('agent.md', '📄'),
            'no_invent_policy': ('No Inventar', '🚫'),
            'memory_available': ('Memoria', '💾'),
            'business_rules': ('Reglas Negocio', '📋')
        }
        lines = []
        for key, (label, icon) in items.items():
            r = resultados.get(key, {})
            st = '🟢' if r.get('status') else '🔴'
            lines.append(f"{st} {icon} {label}: {r.get('detail', 'N/A')}")
        score = self.validator.compliance_score()
        lines.append("")
        lines.append(f"Score: {score.get('compliance_score', 0)}% | "
                     f"Checks: {score.get('passed', 0)}/{score.get('total_checks', 0)} | "
                     f"Estado: {score.get('status', 'N/A')}")
        self.rules_text.delete(1.0, tk.END)
        self.rules_text.insert(1.0, '\n'.join(lines))
        self.rules_text.config(state=tk.DISABLED)

    def _actualizar_memoria(self):
        """Actualiza el treeview con memoria reciente."""
        entries = self.memory.get_all_memory(limit=50)
        for item in self.mem_tree.get_children():
            self.mem_tree.delete(item)
        for i, e in enumerate(entries, 1):
            ts = (e.get('timestamp') or '')[:19]
            self.mem_tree.insert("", "end", text=str(i),
                                 values=(ts, e.get('agent_name', '?'),
                                         e.get('event_type', '?').upper(),
                                         (e.get('summary') or '?')[:60]))

    def _check_agent_md(self):
        """Verifica integridad del agent.md."""
        integ = self.validator.check_agent_md_integrity()
        if integ.get('status') == 'PASS':
            messagebox.showinfo("agent.md OK",
                                f"✅ agent.md integro. Hash: {(integ.get('hash_actual') or '')[:16]}...")
        else:
            messagebox.showwarning("agent.md Modificado", integ.get('detail', 'Error'))

    def _clear_memory(self):
        """Limpia memoria de agentes."""
        if messagebox.askyesno("Limpiar", "Limpiar TODA la memoria?"):
            agents = set()
            for e in self.memory.get_all_memory(limit=1000):
                if e.get('agent_name'):
                    agents.add(e['agent_name'])
            for a in agents:
                self.memory.clear_agent_memory(a)
            messagebox.showinfo("OK", f"Memoria limpiada para {len(agents)} agente(s).")
            self._refrescar()