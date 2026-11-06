"""
FinancialValidator - Motor de Validación Financiera
Implementa las reglas del curso de Adrián Sáenz (Q4Ykcwh5Osc):
- Mínimo 2x: PVP >= costo_origen * 2  → RECHAZAR si no cumple  (24:40)
- Objetivo 3x: PVP >= costo_origen * 3 → ADVERTIR si no cumple  (24:40)
- Coste de origen $5-15               → ADVERTIR fuera de rango (17:50)
- ROAS mínimo 2                       → ADVERTIR (métrica de campaña) (09:40)

El curso NO fija umbral de margen (%), NO fija límite de peso en kg.
Esos criterios NO se inventan ni se añaden.
"""

import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from app.database.connection import DatabaseConnection


class FinancialValidator:
    """Validador financiero con auditoría completa de productos."""
    
    # Reglas del curso Adrián Sáenz (Q4Ykcwh5Osc) — solo lo que el curso dice.
    MULTIPLICADOR_MINIMO  = 2.0   # 24:40 — rechaza si no cumple
    MULTIPLICADOR_OBJETIVO = 3.0  # 24:40 — advierte si no cumple
    COSTE_MIN = 5.0               # 17:50 — advierte fuera de rango
    COSTE_MAX = 15.0              # 17:50

    # Alias retrocompatibles (no cambian la lógica; evitan romper código existente).
    REGLA_3X_MULTIPLICADOR = MULTIPLICADOR_OBJETIVO
    MARGEN_BRUTO_MINIMO    = 0.0  # el curso no fija umbral de margen
    MARGEN_BRUTO_OBJETIVO  = 0.0  # ídem
    
    def __init__(self, db_manager: Optional[DatabaseConnection] = None):
        """
        Args:
            db_manager: Gestor de conexión a BD. Si no se proporciona, crea uno nuevo.
        """
        self.db_manager = db_manager if db_manager else DatabaseConnection()
        self.validaciones_log = []
    
    def validar_producto(
        self,
        sku: str,
        costo_origen: float,
        peso_kg: float = 0.0,
        pvp_sugerido: Optional[float] = None
    ) -> Dict:
        """
        Valida un producto contra las reglas de negocio inmutables.
        
        Args:
            sku: SKU del producto
            costo_origen: Costo de origen en USD
            peso_kg: Peso neto del producto
            pvp_sugerido: PVP sugerido (opcional; si no se proporciona, se calcula)
        
        Returns:
            Dict con validación completa:
            {
                'sku': str,
                'validado': bool,
                'costo_origen': float,
                'pvp_calculado': float,
                'margen_bruto': float,
                'regla_3x_cumple': bool,
                'margen_cumple': bool,
                'logistica_cumple': bool,
                'peso_kg': float,
                'status_validacion': str,
                'nota_auditoria': str,
                'detalles': dict
            }
        """
        
        # 1. Sin PVP dado, usar el objetivo del curso (x3)
        pvp_calculado = pvp_sugerido if pvp_sugerido else costo_origen * self.MULTIPLICADOR_OBJETIVO

        # 2. Multiplicador y margen informativo
        multiplicador  = pvp_calculado / costo_origen if costo_origen > 0 else 0.0
        margen_bruto   = (pvp_calculado - costo_origen) / pvp_calculado if pvp_calculado > 0 else 0.0

        # 3. Regla del curso: solo x2 rechaza (24:40)
        pvp_minimo      = costo_origen * self.MULTIPLICADOR_MINIMO
        pvp_objetivo    = costo_origen * self.MULTIPLICADOR_OBJETIVO
        regla_minimo_cumple = pvp_calculado >= pvp_minimo - 0.01
        objetivo_cumple     = pvp_calculado >= pvp_objetivo - 0.01

        # 4. Solo el piso x2 rechaza — el curso no impone otra condición de rechazo
        status_validacion = 'validado' if regla_minimo_cumple else 'rechazado'

        notas = []
        if not regla_minimo_cumple:
            notas.append(
                f"Multiplicador {multiplicador:.2f}x por debajo del mínimo x2 del curso "
                f"(Q4Ykcwh5Osc 24:40) — PVP mínimo ${pvp_minimo:.2f}, actual ${pvp_calculado:.2f}"
            )

        advertencias = []
        if regla_minimo_cumple and not objetivo_cumple:
            advertencias.append(
                f"Multiplicador {multiplicador:.2f}x: el curso recomienda x3 "
                f"(${pvp_objetivo:.2f}) si el producto lo permite"
            )
        if not (self.COSTE_MIN <= costo_origen <= self.COSTE_MAX):
            advertencias.append(
                f"Coste ${costo_origen:.2f} fuera del rango $5–15 que filtra el curso "
                f"(Q4Ykcwh5Osc 17:50)"
            )

        nota_auditoria = "; ".join(notas + advertencias) or "Producto validado exitosamente"

        resultado = {
            'sku': sku,
            'validado': regla_minimo_cumple,
            'costo_origen': costo_origen,
            'pvp_calculado': round(pvp_calculado, 2),
            'margen_bruto': round(margen_bruto * 100, 2),
            'multiplicador': round(multiplicador, 2),
            'regla_minimo_cumple': regla_minimo_cumple,
            'objetivo_x3_cumple': objetivo_cumple,
            'regla_3x_cumple': objetivo_cumple,
            'peso_kg': peso_kg,
            'logistica_cumple': True,   # alias retrocompatible; el curso no rechaza por peso
            'margen_cumple': True,      # alias retrocompatible; el curso no fija umbral de margen
            'status_validacion': status_validacion,
            'nota_auditoria': nota_auditoria,
            'advertencias': advertencias,
            'detalles': {
                'pvp_minimo_x2': round(pvp_minimo, 2),
                'pvp_objetivo_x3': round(pvp_objetivo, 2),
                'pvp_esperado_regla_3x': round(pvp_objetivo, 2),
                'fecha_validacion': datetime.now().isoformat()
            }
        }
        
        self.validaciones_log.append(resultado)
        return resultado
    
    def guardar_validacion(self, validacion: Dict) -> int:
        """
        Guarda la validación en BD para auditoría.
        
        Returns:
            ID del producto guardado, o -1 si falla
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO productos_validados 
                    (sku, costo_origen, pvp, margen_bruto, status_validacion, validado_regla_3x, peso_kg, nota_auditoria)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    validacion['sku'],
                    validacion['costo_origen'],
                    validacion['pvp_calculado'],
                    validacion['margen_bruto'],
                    validacion['status_validacion'],
                    validacion['regla_3x_cumple'],
                    validacion['peso_kg'],
                    validacion['nota_auditoria']
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"[ERROR] FinancialValidator.guardar_validacion: {str(e)}")
            return -1
    
    def validar_lote(self, productos: List[Dict]) -> Tuple[List[Dict], int, int]:
        """
        Valida múltiples productos en lote.
        
        Args:
            productos: Lista de dicts con sku, costo_origen, peso_kg
        
        Returns:
            (lista_validaciones, validados_count, rechazados_count)
        """
        validaciones = []
        validados = 0
        rechazados = 0
        
        for producto in productos:
            validacion = self.validar_producto(
                sku=producto.get('sku'),
                costo_origen=producto.get('costo_origen'),
                peso_kg=producto.get('peso_kg', 0.0),
                pvp_sugerido=producto.get('pvp')
            )
            validaciones.append(validacion)
            
            if validacion['validado']:
                validados += 1
            else:
                rechazados += 1
        
        return validaciones, validados, rechazados
    
    def obtener_reporte_validaciones(self) -> Dict:
        """
        Genera un reporte consolidado de validaciones ejecutadas.
        
        Returns:
            Dict con estadísticas consolidadas
        """
        if not self.validaciones_log:
            return {
                'total': 0,
                'validados': 0,
                'rechazados': 0,
                'tasa_exito': 0.0
            }
        
        total = len(self.validaciones_log)
        validados = sum(1 for v in self.validaciones_log if v['validado'])
        rechazados = total - validados
        
        return {
            'total': total,
            'validados': validados,
            'rechazados': rechazados,
            'tasa_exito': round((validados / total) * 100, 2) if total > 0 else 0.0,
            'validaciones': self.validaciones_log
        }


def hash_contenido(contenido: str) -> str:
    """Genera hash MD5 de un contenido (para deduplicación)."""
    return hashlib.md5(contenido.encode()).hexdigest()
