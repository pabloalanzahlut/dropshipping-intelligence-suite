"""
FinancialValidator - Motor de Validación Financiera

Fuente primaria: Adrián Sáenz. Solo se aplican reglas que sus contenidos dicen
explícitamente, cada una con su referencia. No se inventa ninguna.

Curso base (Q4Ykcwh5Osc):
- Mínimo 2x: PVP >= coste_landed * 2  → RECHAZAR si no cumple  (24:40)
- Objetivo 3x: PVP >= coste_landed * 3 → ADVERTIR si no cumple (24:40)
- Coste de origen $5-15                → ADVERTIR fuera de rango (17:50)
- ROAS mínimo 2                        → ADVERTIR (métrica de campaña) (09:40)

Guía productos ganadores (qgK3GfY5ZC4 11:30):
- El multiplicador se calcula sobre COSTE LANDED = producto + envío.
  Ficha real del vídeo: $5 producto + $2 envío = $7 landed → PVP $30.
  Calcular sobre el producto solo infla el multiplicador y aprueba
  productos que en realidad no llegan al mínimo.

P&L real de 30 días (rqMrq2MGdpw):
- Fees Shopify + cambio de divisa: 4,0% de la facturación (3.109 € / 77.748 €)
- Cancelaciones y devoluciones:   10,1% de la facturación (7.887 € / 77.748 €)
  Estos dos costes no aparecen en el curso base pero sí en su P&L real, y
  suman 14,1% que de otro modo se pierde sin quedar registrado.

El curso NO fija umbral de margen (%), NO fija límite de peso en kg.
Esos criterios NO se inventan ni se añaden.
"""

import hashlib
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from app.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class FinancialValidator:
    """Validador financiero con auditoría completa de productos."""

    # Reglas del curso Adrián Sáenz (Q4Ykcwh5Osc) — solo lo que el curso dice.
    MULTIPLICADOR_MINIMO  = 2.0   # 24:40 — rechaza si no cumple
    MULTIPLICADOR_OBJETIVO = 3.0  # 24:40 — advierte si no cumple
    COSTE_MIN = 5.0               # 17:50 — advierte fuera de rango
    COSTE_MAX = 15.0              # 17:50

    # Costes operativos reales del P&L de 30 días (rqMrq2MGdpw).
    # Se descuentan del PVP para obtener el margen neto real por unidad.
    FEES_SHOPIFY_DIVISA_PCT = 0.040   # 4,0% — pasarela + cambio de divisa
    CANCELACIONES_PCT       = 0.101   # 10,1% — cancelaciones y devoluciones

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
        pvp_sugerido: Optional[float] = None,
        costo_envio: float = 0.0,
        moneda_costo: str = "USD",
        moneda_pvp: str = "USD"
    ) -> Dict:
        """
        Valida un producto contra las reglas de negocio inmutables.

        El multiplicador se calcula sobre el coste LANDED (producto + envío),
        no sobre el coste de producto solo (qgK3GfY5ZC4 11:30).

        Si el coste y el PVP vienen en divisas distintas, convierte al tipo
        del día: un tipo fijo falsea el multiplicador (KXKzgeHOr7A hack 3).

        Args:
            sku: SKU del producto
            costo_origen: Costo del producto en el proveedor
            peso_kg: Peso neto del producto
            pvp_sugerido: PVP sugerido (opcional; si no se proporciona, se calcula)
            costo_envio: Coste de envío del proveedor al cliente
            moneda_costo: Divisa de costo_origen y costo_envio (AliExpress/CJ suelen ser USD)
            moneda_pvp: Divisa del PVP (tienda europea suele ser EUR)

        Returns:
            Dict con la validación completa, el desglose de costes operativos
            y el margen neto real por unidad.
        """

        # 1. Coste landed: el multiplicador se mide contra esto, no contra el producto solo
        costo_landed = costo_origen + costo_envio

        # 2. Divisas distintas: convertir el coste a la divisa del PVP al tipo del día
        fx_estimado = False
        fx_rate = 1.0
        if moneda_costo.upper() != moneda_pvp.upper():
            from app.services.fx_rates import get_rate, is_rate_live
            fx_rate = get_rate(moneda_costo, moneda_pvp)
            costo_landed = costo_landed * fx_rate
            fx_estimado = not is_rate_live(moneda_costo, moneda_pvp)

        # 3. Sin PVP dado, usar el objetivo del curso (x3) sobre el landed
        pvp_calculado = pvp_sugerido if pvp_sugerido else costo_landed * self.MULTIPLICADOR_OBJETIVO

        # 3. Multiplicador y margen bruto sobre coste landed
        multiplicador = pvp_calculado / costo_landed if costo_landed > 0 else 0.0
        margen_bruto  = (pvp_calculado - costo_landed) / pvp_calculado if pvp_calculado > 0 else 0.0

        # 4. Costes operativos del P&L real (rqMrq2MGdpw) — se descuentan del PVP
        coste_fees          = pvp_calculado * self.FEES_SHOPIFY_DIVISA_PCT
        coste_cancelaciones = pvp_calculado * self.CANCELACIONES_PCT
        margen_neto_unidad  = pvp_calculado - costo_landed - coste_fees - coste_cancelaciones
        margen_neto_pct     = margen_neto_unidad / pvp_calculado if pvp_calculado > 0 else 0.0

        # 5. Regla del curso: solo x2 rechaza (24:40)
        pvp_minimo   = costo_landed * self.MULTIPLICADOR_MINIMO
        pvp_objetivo = costo_landed * self.MULTIPLICADOR_OBJETIVO
        regla_minimo_cumple = pvp_calculado >= pvp_minimo - 0.01
        objetivo_cumple     = pvp_calculado >= pvp_objetivo - 0.01

        # 6. Solo el piso x2 rechaza — el curso no impone otra condición de rechazo
        status_validacion = 'validado' if regla_minimo_cumple else 'rechazado'

        notas = []
        if not regla_minimo_cumple:
            notas.append(
                f"Multiplicador {multiplicador:.2f}x sobre coste landed ${costo_landed:.2f} "
                f"por debajo del mínimo x2 del curso (Q4Ykcwh5Osc 24:40) — "
                f"PVP mínimo ${pvp_minimo:.2f}, actual ${pvp_calculado:.2f}"
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
        if costo_envio == 0.0:
            advertencias.append(
                "Coste de envío no informado: el multiplicador se ha calculado solo "
                "sobre el producto y puede estar inflado (qgK3GfY5ZC4 11:30)"
            )
        if fx_estimado:
            advertencias.append(
                f"Tipo de cambio {moneda_costo}/{moneda_pvp} estimado ({fx_rate}): "
                f"Frankfurter no respondió. Validación marcada como no definitiva"
            )
        if margen_neto_unidad <= 0:
            advertencias.append(
                f"Margen neto NEGATIVO (${margen_neto_unidad:.2f}/unidad) tras descontar "
                f"fees {self.FEES_SHOPIFY_DIVISA_PCT:.1%} y cancelaciones "
                f"{self.CANCELACIONES_PCT:.1%} del P&L real (rqMrq2MGdpw)"
            )

        nota_auditoria = "; ".join(notas + advertencias) or "Producto validado exitosamente"

        resultado = {
            'sku': sku,
            'validado': regla_minimo_cumple,
            'costo_origen': costo_origen,
            'costo_envio': costo_envio,
            'costo_landed': round(costo_landed, 2),
            'pvp_calculado': round(pvp_calculado, 2),
            'margen_bruto': round(margen_bruto * 100, 2),
            'margen_neto_unidad': round(margen_neto_unidad, 2),
            'margen_neto_pct': round(margen_neto_pct * 100, 2),
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
                'coste_fees_shopify_divisa': round(coste_fees, 2),
                'coste_cancelaciones': round(coste_cancelaciones, 2),
                'fx_rate': fx_rate,
                'fx_estimado': fx_estimado,
                'moneda_costo': moneda_costo,
                'moneda_pvp': moneda_pvp,
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
                pvp_sugerido=producto.get('pvp'),
                costo_envio=producto.get('costo_envio', 0.0)
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
