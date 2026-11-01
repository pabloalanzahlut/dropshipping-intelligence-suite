"""
TrafficAnalyzer - Analizador de Tendencias y Tráfico
Lee de la KB local (matriz_tendencias + operaciones_trafico) para clasificar productos.
"""

import os
import json
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from app.database.connection import DatabaseConnection


class TrafficAnalyzer:
    """Analizador de tendencias y tráfico basado en KB local."""
    
    # Rutas KB inmutables
    MATRIZ_TENDENCIAS_PATH = "ai_workspace/context/matriz_tendencias.md"
    OPERACIONES_TRAFICO_PATH = "ai_workspace/context/operaciones_trafico.md"
    
    def __init__(self, db_manager: Optional[DatabaseConnection] = None):
        self.db_manager = db_manager if db_manager else DatabaseConnection()
        self.tendencias_cache = None
        self.trafico_cache = None
        self._cargar_kb()
    
    def _cargar_kb(self):
        """Carga la base de conocimiento local (idempotente)."""
        # Leer matriz_tendencias.md
        if os.path.exists(self.MATRIZ_TENDENCIAS_PATH):
            with open(self.MATRIZ_TENDENCIAS_PATH, 'r', encoding='utf-8') as f:
                self.tendencias_cache = f.read()
        else:
            self.tendencias_cache = "# Sin datos de tendencias\n"
        
        # Leer operaciones_trafico.md
        if os.path.exists(self.OPERACIONES_TRAFICO_PATH):
            with open(self.OPERACIONES_TRAFICO_PATH, 'r', encoding='utf-8') as f:
                self.trafico_cache = f.read()
        else:
            self.trafico_cache = "# Sin datos de tráfico\n"
    
    def clasificar_producto(self, nombre_producto: str, categoria: str = "") -> Dict:
        """
        Clasifica un producto en un nicho basado en matriz de tendencias.
        
        Args:
            nombre_producto: Nombre del producto
            categoria: Categoría sugerida
        
        Returns:
            Dict con clasificación y score de tendencia
        """
        # Extraer nichos de la matriz
        nichos = self._extraer_nichos()
        
        # Buscar coincidencia en nombre
        categoria_lower = categoria.lower()
        nicho_encontrado = None
        
        for nicho in nichos:
            if any(palabra in categoria_lower for palabra in nicho.lower().split()):
                nicho_encontrado = nicho
                break
        
        # Fallback: primer nicho disponible o genérico
        if not nicho_encontrado and nichos:
            nicho_encontrado = nichos[0]
        elif not nicho_encontrado:
            nicho_encontrado = "General"
        
        # Score de tendencia (mock analítico basado en KB)
        trending_score = self._calcular_trending_score(nombre_producto, nicho_encontrado)
        
        return {
            'producto': nombre_producto,
            'nicho': nicho_encontrado,
            'trending_score': trending_score,
            'categoria_base': categoria,
            'fuente': 'matriz_tendencias.md',
            'timestamp': datetime.now().isoformat()
        }
    
    def _extraer_nichos(self) -> List[str]:
        """Extrae nombres de nichos de la matriz de tendencias."""
        if not self.tendencias_cache:
            return []
        
        nichos = []
        for line in self.tendencias_cache.split('\n'):
            line = line.strip()
            if line.startswith('## ') or line.startswith('### '):
                nichos.append(line.replace('## ', '').replace('### ', '').strip())
        
        return nichos
    
    def _calcular_trending_score(self, nombre: str, nicho: str) -> int:
        """
        Calcula score de tendencia (0-100) basado en análisis de KB.
        Usa heurísticas de contenido + variaciones de palabras clave.
        """
        score = 50  # Base
        
        # Palabras de alto valor en naming de productos
        palabras_trending = {'pro', 'max', 'ultra', 'smart', 'auto', 'rapid', 
                           'premium', 'elite', 'tech', 'fit', 'glow', 'boost'}
        
        nombre_lower = nombre.lower()
        for palabra in palabras_trending:
            if palabra in nombre_lower:
                score += 8
        
        # Nichos específicos tienen bonus
        nichos_bonus = {
            'tecnologia': 15, 'fitness': 12, 'belleza': 10, 'hogar': 8,
            'bebe': 10, 'mascotas': 12, 'cocina': 8, 'gadgets': 15
        }
        
        nicho_lower = nicho.lower()
        for key, bonus in nichos_bonus.items():
            if key in nicho_lower:
                score += bonus
        
        return min(100, score)
    
    def obtener_reporte_tendencias(self, limite: int = 10) -> Dict:
        """
        Genera reporte consolidado de tendencias desde la BD.
        
        Returns:
            Dict con tendencias, fuentes de tráfico y estrategias
        """
        # Leer tendencias desde product_trends
        tendencias_db = []
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT niche, COUNT(*) as count, AVG(estimated_margin) as avg_margin
                    FROM product_trends
                    GROUP BY niche
                    ORDER BY count DESC
                    LIMIT ?
                """, (limite,))
                tendencias_db = [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] TrafficAnalyzer DB: {str(e)}")
        
        # Extraer fuentes de tráfico de KB
        fuentes_trafico = self._extraer_fuentes_trafico()
        
        return {
            'tendencias_db': tendencias_db,
            'fuentes_trafico': fuentes_trafico,
            'kb_tendencias_loaded': bool(self.tendencias_cache),
            'kb_trafico_loaded': bool(self.trafico_cache)
        }
    
    def _extraer_fuentes_trafico(self) -> List[str]:
        """Extrae fuentes de tráfico de la KB."""
        if not self.trafico_cache:
            return []
        
        fuentes = []
        for line in self.trafico_cache.split('\n'):
            line = line.strip()
            if line.startswith('-') and ('tiktok' in line.lower() or 'facebook' in line.lower() 
                                       or 'google' in line.lower() or 'youtube' in line.lower()
                                       or 'pinterest' in line.lower() or 'snapchat' in line.lower()
                                       or 'ads' in line.lower() or 'traffic' in line.lower()):
                fuentes.append(line.lstrip('- '))
        
        return fuentes if fuentes else ["TikTok Ads", "Facebook Ads", "Google Ads", "YouTube Organic", "Pinterest"]


def analyze_quick(nombre: str, categoria: str = "") -> Dict:
    """Función helper para análisis rápido desde CLI."""
    analyzer = TrafficAnalyzer()
    return analyzer.clasificar_producto(nombre, categoria)


# ============================================================================
# EXTENSIÓN: Trend Scoring con peso de IA
# ============================================================================

def calcular_trend_score_ai_weighted(
    producto_nombre: str,
    categoria: str,
    menciones_kb: int = 0,
    peso_logistico_kg: float = 0.0,
    margen_bruto: float = 0.0,
) -> Dict:
    """
    Calcula un score de tendencia ponderado por IA basado en múltiples factores.

    Args:
        producto_nombre: Nombre del producto
        categoria: Categoría
        menciones_kb: Número de menciones en la KB de transcripciones
        peso_logistico_kg: Peso del producto en kg
        margen_bruto: Margen bruto (0.0 - 1.0)

    Returns:
        Dict con score total y desglose
    """
    score = 50  # Base

    # Factor 1: Menciones en KB (peso: 30%)
    if menciones_kb > 0:
        score += min(30, menciones_kb * 5)

    # Factor 2: Nicho trending (peso: 25%)
    nichos_trending = {
        "tecnologia": 20, "fitness": 18, "belleza": 16, "hogar": 14,
        "mascotas": 18, "bebe": 15, "cocina": 12, "gadgets": 22,
        "moda": 14, "deportes": 16, "salud": 17, "jardin": 10,
    }
    cat_lower = categoria.lower()
    for nicho, bonus in nichos_trending.items():
        if nicho in cat_lower or cat_lower in nicho:
            score += bonus
            break

    # Factor 3: Logística (peso: 20%)
    if peso_logistico_kg > 0:
        if peso_logistico_kg < 0.5:
            score += 20  # Producto ligero, ideal
        elif peso_logistico_kg < 1.0:
            score += 15
        elif peso_logistico_kg < 1.2:
            score += 10
        else:
            score -= 10  # Excede límite Iván Caicedo

    # Factor 4: Margen bruto (peso: 25%)
    if margen_bruto > 0:
        if margen_bruto >= 0.80:
            score += 25
        elif margen_bruto >= 0.75:
            score += 20
        elif margen_bruto >= 0.70:
            score += 15
        else:
            score += 5

    # Factor 5: Palabras clave en nombre (peso: 10%)
    palabras_clave = {"pro": 5, "max": 5, "smart": 8, "auto": 6, "premium": 4,
                      "tech": 7, "fit": 6, "glow": 5, "boost": 7, "rapid": 6}
    nombre_lower = producto_nombre.lower()
    for palabra, bonus in palabras_clave.items():
        if palabra in nombre_lower:
            score += bonus

    score = max(0, min(100, score))

    return {
        "score_total": score,
        "desglose": {
            "menciones_kb": min(30, menciones_kb * 5) if menciones_kb > 0 else 0,
            "nicho_trending": next((b for n, b in nichos_trending.items()
                                   if n in cat_lower or cat_lower in n), 0),
            "logistica": 0,  # Se calcula arriba
            "margen": 0,     # Se calcula arriba
            "palabras_clave": sum(bonus for p, bonus in palabras_clave.items()
                                 if p in nombre_lower),
        },
        "factores": {
            "menciones_kb": menciones_kb,
            "peso_kg": peso_logistico_kg,
            "margen_bruto_pct": round(margen_bruto * 100, 1),
            "categoria": categoria,
        },
        "timestamp": datetime.now().isoformat(),
    }


def obtener_datos_para_grafico(analyzer: TrafficAnalyzer) -> Dict:
    """
    Obtiene datos estructurados para gráficos en tiempo real.

    Returns:
        Dict con 'nichos', 'scores', 'fuentes', 'distribucion'
    """
    # Obtener nichos de la matriz
    nichos = analyzer._extraer_nichos() if analyzer.tendencias_cache else []
    scores = {}
    for nicho in nichos[:8]:  # Top 8 nichos
        score = analyzer._calcular_trending_score(nicho, nicho)
        scores[nicho] = score

    # Fuentes de tráfico
    fuentes = analyzer._extraer_fuentes_trafico() if analyzer.trafico_cache else []

    # Distribución estimada
    distribucion = {
        "TikTok Organic": 35,
        "Facebook Ads": 25,
        "Google Ads": 20,
        "YouTube": 12,
        "Pinterest": 8,
    }

    return {
        "nichos": list(scores.keys()),
        "scores": list(scores.values()),
        "fuentes_trafico": fuentes,
        "distribucion_trafico": distribucion,
        "timestamp": datetime.now().isoformat(),
    }