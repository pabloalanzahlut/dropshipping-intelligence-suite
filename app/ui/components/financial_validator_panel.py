"""
FinancialValidatorPanel - UI para Validación de Productos
Permite importar productos, validarlos y exportar reportes.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import csv
import json
from datetime import datetime

from app.services.financial_validator import FinancialValidator


class FinancialValidatorPanel(ttk.Frame):
    """Panel UI para validación financiera de productos."""
    
    def __init__(self, parent, db_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.db_manager = db_manager
        self.validator = FinancialValidator(db_manager=db_manager)
        self.validaciones_actuales = []
        
        self._build_ui()
    
    def _build_ui(self):
        """Construye la interfaz gráfica."""
        
        # ====== Sección Superior: Importar Productos ======
        import_frame = ttk.LabelFrame(self, text="Importar Productos", padding=10)
        import_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(import_frame, text="Cargar CSV", command=self._importar_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(import_frame, text="Cargar JSON", command=self._importar_json).pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(import_frame, text="Listo para importar", foreground="blue")
        self.status_label.pack(side=tk.LEFT, padx=10, expand=True, fill=tk.X)
        
        # ====== Sección Media: Tabla de Validaciones ======
        tabla_frame = ttk.LabelFrame(self, text="Validaciones", padding=10)
        tabla_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ("SKU", "Costo", "PVP", "Margen %", "Regla 3x", "Peso kg", "Status")
        self.validaciones_tree = ttk.Treeview(tabla_frame, columns=columns, height=12)
        self.validaciones_tree.heading("#0", text="ID")
        self.validaciones_tree.column("#0", width=30)
        
        col_widths = [80, 60, 60, 70, 70, 60, 80]
        for col, width in zip(columns, col_widths):
            self.validaciones_tree.heading(col, text=col)
            self.validaciones_tree.column(col, width=width)
        
        scrollbar = ttk.Scrollbar(tabla_frame, orient=tk.VERTICAL, command=self.validaciones_tree.yview)
        self.validaciones_tree.configure(yscroll=scrollbar.set)
        
        self.validaciones_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # ====== Sección Inferior: Exportar Resultados ======
        export_frame = ttk.LabelFrame(self, text="Exportar Resultados", padding=10)
        export_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(export_frame, text="Exportar CSV", command=self._exportar_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="Exportar JSON", command=self._exportar_json).pack(side=tk.LEFT, padx=5)
        
        # Estadísticas
        self.stats_label = ttk.Label(export_frame, text="Stats: 0 validados, 0 rechazados")
        self.stats_label.pack(side=tk.LEFT, padx=10, expand=True, fill=tk.X)
    
    def _importar_csv(self):
        """Carga productos desde archivo CSV."""
        filepath = filedialog.askopenfilename(
            title="Seleccionar CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            self.status_label.config(text="Cargando CSV...", foreground="orange")
            self.update()
            
            productos = []
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    productos.append({
                        'sku': row.get('sku', row.get('SKU', '')),
                        'costo_origen': float(row.get('costo_origen', row.get('costo', 0))),
                        'peso_kg': float(row.get('peso_kg', row.get('peso', 0))),
                        'pvp': float(row.get('pvp', row.get('pvp', 0))) if row.get('pvp') or row.get('pvp') else None
                    })
            
            self._procesar_productos(productos)
            
        except Exception as e:
            messagebox.showerror("Error al Cargar CSV", str(e))
            self.status_label.config(text="Error cargando CSV", foreground="red")
    
    def _importar_json(self):
        """Carga productos desde archivo JSON."""
        filepath = filedialog.askopenfilename(
            title="Seleccionar JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            self.status_label.config(text="Cargando JSON...", foreground="orange")
            self.update()
            
            with open(filepath, 'r', encoding='utf-8') as f:
                productos = json.load(f)
            
            if not isinstance(productos, list):
                productos = [productos]
            
            self._procesar_productos(productos)
            
        except Exception as e:
            messagebox.showerror("Error al Cargar JSON", str(e))
            self.status_label.config(text="Error cargando JSON", foreground="red")
    
    def _procesar_productos(self, productos):
        """Valida batch de productos en thread separado."""
        self.status_label.config(text="Validando productos...", foreground="orange")
        
        def worker():
            validaciones, validados, rechazados = self.validator.validar_lote(productos)
            self.validaciones_actuales = validaciones
            
            # Actualizar UI en main thread
            self.after(0, lambda: self._actualizar_tabla(validaciones, validados, rechazados))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _actualizar_tabla(self, validaciones, validados, rechazados):
        """Actualiza tabla de validaciones."""
        # Limpiar tabla
        for item in self.validaciones_tree.get_children():
            self.validaciones_tree.delete(item)
        
        # Insertar filas
        for i, val in enumerate(validaciones, 1):
            status_icon = "[OK]" if val['validado'] else "[X]"
            self.validaciones_tree.insert("", "end", text=str(i),
                                         values=(
                                             val['sku'],
                                             f"${val['costo_origen']:.2f}",
                                             f"${val['pvp_calculado']:.2f}",
                                             f"{val['margen_bruto']:.1f}%",
                                             "Si" if val['regla_3x_cumple'] else "No",
                                             f"{val['peso_kg']} kg",
                                             status_icon
                                         ))
        
        # Actualizar estadísticas
        self.stats_label.config(
            text=f"Stats: {validados} validados, {rechazados} rechazados " +
                 f"(Tasa: {round(validados*100/(validados+rechazados), 1)}%)"
        )
        
        self.status_label.config(text="Validación completada", foreground="green")
        
        messagebox.showinfo("Validación Completada", 
                          f"Procesados {validados + rechazados} productos\n"
                          f"Validados: {validados}\nRechazados: {rechazados}")
    
    def _exportar_csv(self):
        """Exporta validaciones a CSV."""
        if not self.validaciones_actuales:
            messagebox.showwarning("Sin datos", "No hay validaciones para exportar")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['sku', 'costo_origen', 'pvp_calculado', 'margen_bruto', 
                            'regla_3x_cumple', 'peso_kg', 'status_validacion', 'nota_auditoria']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for val in self.validaciones_actuales:
                    writer.writerow({
                        'sku': val['sku'],
                        'costo_origen': val['costo_origen'],
                        'pvp_calculado': val['pvp_calculado'],
                        'margen_bruto': val['margen_bruto'],
                        'regla_3x_cumple': val['regla_3x_cumple'],
                        'peso_kg': val['peso_kg'],
                        'status_validacion': val['status_validacion'],
                        'nota_auditoria': val['nota_auditoria']
                    })
            
            messagebox.showinfo("Éxito", f"Exportado a {filepath}")
        except Exception as e:
            messagebox.showerror("Error al Exportar", str(e))
    
    def _exportar_json(self):
        """Exporta validaciones a JSON."""
        if not self.validaciones_actuales:
            messagebox.showwarning("Sin datos", "No hay validaciones para exportar")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            export_data = {
                'fecha_exportacion': datetime.now().isoformat(),
                'total_productos': len(self.validaciones_actuales),
                'productos': self.validaciones_actuales
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("Éxito", f"Exportado a {filepath}")
        except Exception as e:
            messagebox.showerror("Error al Exportar", str(e))
