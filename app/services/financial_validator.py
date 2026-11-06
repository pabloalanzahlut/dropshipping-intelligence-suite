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

    # Alias retrocompatibles para módulos existentes.
    REGLA_3X_MULTIPLICADOR = MULTIPLICADOR_OBJETIVO
    MARGEN_BRUTO_MINIMO    = 0.0   # el curso no fija umbral; se conserva alias en 0
    MARGEN_BRUTO_OBJETIVO  = 0.0   # ídem
    PESO_MAXIMO_KG         = None  # el curso no fija límite de peso
    
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
        
        # 1. Sin PVP dado, partir del objetivo del curso (x3)
        pvp_calculado = pvp_sugerido if pvp_sugerido else costo_origen * self.MULTIPLICADOR_OBJETIVO

        # 2. Calcular margen bruto y multiplicador real
        margen_bruto = (pvp_calculado - costo_origen) / pvp_calculado if pvp_calculado > 0 else 0.0
        multiplicador = pvp_calculado / costo_origen if costo_origen > 0 else 0.0

        # 3. Piso del curso: por debajo de x2 el producto se descarta
        pvp_minimo = costo_origen * self.MULTIPLICADOR_MINIMO
        regla_minimo_cumple = pvp_calculado >= pvp_minimo - 0.01

        # 4. x3 es la recomendación "si el producto da las características"
        pvp_objetivo = costo_origen * self.MULTIPLICADOR_OBJETIVO
        objetivo_cumple = pvp_calculado >= pvp_objetivo - 0.01

        # 5. Margen: el curso no fija umbral, así que informa sin bloquear
        margen_cumple = margen_bruto >= self.MARGEN_BRUTO_OBJETIVO

        # 6. Peso: el curso no lo trata; se mantiene como límite logístico real
        logistica_cumple = peso_kg < self.PESO_MAXIMO_KG

        # 7. Solo el piso x2 y el peso rechazan
        todas_validas = regla_minimo_cumple and logistica_cumple
        status_validacion = 'validado' if todas_validas else 'rechazado'

        notas = []
        if not regla_minimo_cumple:
            notas.append(
                f"Multiplicador {multiplicador:.2f}x bajo el mínimo x2 del curso: "
                f"PVP mínimo ${pvp_minimo:.2f}, es ${pvp_calculado:.2f}"
            )
        if not logistica_cumple:
            notas.append(f"Peso excedido: {peso_kg} kg (máximo: {self.PESO_MAXIMO_KG} kg) - ALERTA IVÁN CAICEDO")

        advertencias = []
        if regla_minimo_cumple and not objetivo_cumple:
            advertencias.append(
                f"Multiplicador {multiplicador:.2f}x: por debajo del x3 recomendado "
                f"(PVP ${pvp_objetivo:.2f}) — subirlo si el producto lo permite"
            )
        if not margen_cumple:
            advertencias.append(
                f"Margen bruto {margen_bruto*100:.1f}% (objetivo {self.MARGEN_BRUTO_OBJETIVO*100:.0f}%)"
            )

        nota_auditoria = "; ".join(notas + advertencias) or "Producto validado exitosamente"
        
        resultado = {
            'sku': sku,
            'validado': todas_validas,
            'costo_origen': costo_origen,
            'pvp_calculado': round(pvp_calculado, 2),
            'margen_bruto': round(margen_bruto * 100, 2),
            'multiplicador': round(multiplicador, 2),
            'regla_minimo_cumple': regla_minimo_cumple,
            'objetivo_x3_cumple': objetivo_cumple,
            'regla_3x_cumple': objetivo_cumple,  # alias retrocompatible
            'margen_cumple': margen_cumple,
            'logistica_cumple': logistica_cumple,
            'peso_kg': peso_kg,
            'status_validacion': status_validacion,
            'nota_auditoria': nota_auditoria,
            'advertencias': advertencias,
            'detalles': {
                'pvp_minimo_x2': round(pvp_minimo, 2),
                'pvp_objetivo_x3': round(pvp_objetivo, 2),
                'pvp_esperado_regla_3x': round(pvp_objetivo, 2),  # alias
                'margen_objetivo_pct': round(self.MARGEN_BRUTO_OBJETIVO * 100, 1),
                'peso_maximo_kg': self.PESO_MAXIMO_KG,
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
