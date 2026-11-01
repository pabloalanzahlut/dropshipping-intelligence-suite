#!/usr/bin/env python3
"""
CLI Test - Pruebas rápidas de FASE 0 (Fundacional)
Valida:
1. FinancialValidator (Regla 3x + 70% margen + peso)
2. TranscriptCleaner (limpieza ultra)
3. Conexion a BD
"""

import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.connection import DatabaseConnection
from app.services.financial_validator import FinancialValidator
from app.services.transcript_cleaner import TranscriptCleaner


def test_database():
    """Test 1: Verifica conexión a BD y creación de tablas."""
    print("\n" + "="*60)
    print("TEST 1: Database Connection")
    print("="*60)
    
    try:
        db = DatabaseConnection()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Verificar tablas críticas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [t[0] for t in tables]
        
        print(f"✓ Conexión establecida")
        print(f"✓ Tablas encontradas: {len(table_names)}")
        
        required_tables = ['transcripciones_youtube', 'productos_validados']
        for table in required_tables:
            if table in table_names:
                print(f"  ✓ Tabla '{table}' existe")
            else:
                print(f"  ✗ Tabla '{table}' NO ENCONTRADA")
        
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_financial_validator():
    """Test 2: Valida FinancialValidator con casos de prueba."""
    print("\n" + "="*60)
    print("TEST 2: Financial Validator")
    print("="*60)
    
    try:
        validator = FinancialValidator()
        
        # Caso de prueba 1: Producto válido
        print("\n[CASO 1] Producto válido (Regla 3x, margen 70%, peso < 1.2kg)")
        resultado1 = validator.validar_producto(
            sku="TEST-001",
            costo_origen=10.0,  # Costo: $10
            peso_kg=0.8          # Peso: 800g
        )
        print(f"  SKU: {resultado1['sku']}")
        print(f"  Costo Origen: ${resultado1['costo_origen']}")
        print(f"  PVP Calculado: ${resultado1['pvp_calculado']} (esperado: $30.00 por Regla 3x)")
        print(f"  Margen Bruto: {resultado1['margen_bruto']}%")
        print(f"  Regla 3x Cumple: {'✓' if resultado1['regla_3x_cumple'] else '✗'}")
        print(f"  Margen Cumple: {'✓' if resultado1['margen_cumple'] else '✗'}")
        print(f"  Logística Cumple: {'✓' if resultado1['logistica_cumple'] else '✗'}")
        print(f"  Status: {resultado1['status_validacion']}")
        print(f"  Nota: {resultado1['nota_auditoria']}")
        
        # Caso de prueba 2: Producto rechazado por peso
        print("\n[CASO 2] Producto rechazado (peso > 1.2kg - ALERTA IVÁN CAICEDO)")
        resultado2 = validator.validar_producto(
            sku="TEST-002",
            costo_origen=15.0,
            peso_kg=1.5  # Sobrepeso
        )
        print(f"  SKU: {resultado2['sku']}")
        print(f"  Peso: {resultado2['peso_kg']} kg (máximo: {FinancialValidator.PESO_MAXIMO_KG} kg)")
        print(f"  Status: {resultado2['status_validacion']}")
        print(f"  Nota: {resultado2['nota_auditoria']}")
        
        # Caso de prueba 3: Producto rechazado por margen bajo
        print("\n[CASO 3] Producto rechazado (margen bruto < 70%)")
        resultado3 = validator.validar_producto(
            sku="TEST-003",
            costo_origen=10.0,
            pvp_sugerido=15.0,  # PVP bajo
            peso_kg=0.5
        )
        print(f"  SKU: {resultado3['sku']}")
        print(f"  Costo Origen: ${resultado3['costo_origen']}")
        print(f"  PVP Sugerido: ${resultado3['pvp_calculado']}")
        print(f"  Margen Bruto: {resultado3['margen_bruto']}% (mínimo: 70%)")
        print(f"  Status: {resultado3['status_validacion']}")
        print(f"  Nota: {resultado3['nota_auditoria']}")
        
        # Guardar una validación
        print("\n[GUARDANDO] Validación 1 en base de datos")
        db = DatabaseConnection()
        id_guardado = validator.guardar_validacion(resultado1)
        print(f"  ✓ Producto guardado con ID: {id_guardado}")
        
        # Reporte
        reporte = validator.obtener_reporte_validaciones()
        print(f"\n[REPORTE] Total validaciones: {reporte['total']}")
        print(f"  Validados: {reporte['validados']}")
        print(f"  Rechazados: {reporte['rechazados']}")
        print(f"  Tasa éxito: {reporte['tasa_exito']}%")
        
        return True
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_transcript_cleaner():
    """Test 3: Valida TranscriptCleaner con texto de ejemplo."""
    print("\n" + "="*60)
    print("TEST 3: Transcript Cleaner (Ultra-Limpieza)")
    print("="*60)
    
    try:
        cleaner = TranscriptCleaner()
        
        # Texto de prueba con ruido típico de YouTube
        texto_raw = """
00:00:15.234 --> 00:00:20.000
Ehh, bueno, mira entonces, umm ok, hoy vamos a hablar de dropshipping. 
Bueno bueno bueno, entiendes, entonces el primer paso es validar los productos.

[Música de fondo]

00:00:25.000 --> 00:00:30.500
Ehh, la regla 3x, verdad, umm, significa que si el producto cuesta $10, 
entonces entonces entonces el precio debe ser de $30.

[Pausa de 10 segundos]



Mira, además, el margen debe ser mayor al 70%. Sabes, ok, eso es crítico.
Ehh, también importante es validar el peso, umm, debe ser menor a 1.2 kilogramos.
        """
        
        print("[ENTRADA]")
        print(f"  Caracteres: {len(texto_raw)}")
        tokens_orig = cleaner.count_tokens_estimate(texto_raw)
        print(f"  Tokens estimados: {tokens_orig}")
        
        # Ejecutar limpieza
        print("\n[LIMPIEZA EN CURSO...]")
        resultado = cleaner.clean(texto_raw, log_stats=True)
        
        print(f"\n[RESULTADO]")
        print(f"  Pasos ejecutados: {', '.join(resultado['pasos_ejecutados'])}")
        print(f"  UTF-8 válido: {'✓' if resultado['es_valido'] else '✗'}")
        print(f"  Tokens original: {resultado['tokens_original']}")
        print(f"  Tokens limpio: {resultado['tokens_limpio']}")
        print(f"  Reducción: {resultado['reduccion_pct']}%")
        
        print(f"\n[TEXTO LIMPIO]")
        print("---")
        print(resultado['text_limpio'][:300] + "...")
        print("---")
        
        # Stats
        stats = cleaner.get_cleaning_stats()
        print(f"\n[ESTADÍSTICAS GLOBALES]")
        print(f"  Total limpiezas: {stats['total_limpiezas']}")
        print(f"  Promedio reducción: {stats['promedio_reduccion_pct']}%")
        print(f"  Ahorro total de tokens: {stats['ahorro_total_tokens']}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecuta todos los tests."""
    print("\n" + "[TESTS] SUITE DE TESTS FASE 0: FUNDACIONAL")
    print("="*60)
    
    resultados = {
        'Database': test_database(),
        'FinancialValidator': test_financial_validator(),
        'TranscriptCleaner': test_transcript_cleaner(),
    }
    
    print("\n" + "="*60)
    print("RESUMEN DE TESTS")
    print("="*60)
    
    total_tests = len(resultados)
    tests_passed = sum(1 for v in resultados.values() if v)
    
    for test_name, passed in resultados.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name}: {status}")
    
    print(f"\nTotal: {tests_passed}/{total_tests} tests pasaron")
    
    if tests_passed == total_tests:
        print("\n[OK] FASE 0 COMPLETADA EXITOSAMENTE")
        return 0
    else:
        print("\n[ERROR] ALGUNOS TESTS FALLARON")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
