#!/usr/bin/env python3
"""
Test Suite - Verificar FASE 1, 3, 4
- FASE 1: YouTube Monitor + Transcript Cleaner
- FASE 3: Copywriting Engine (AIDA)
- FASE 4: TikTok Script Generator
"""

import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.connection import DatabaseConnection
from app.services.youtube_channel_monitor import YouTubeChannelMonitor
from app.services.copywriting_engine import CopywrightingEngine
from app.services.tiktok_script_generator import TikTokScriptGenerator
from app.services.financial_validator import FinancialValidator


def test_fase_1():
    """Test FASE 1: YouTube Monitor + Transcript Cleaner"""
    print("\n" + "="*60)
    print("TEST FASE 1: YouTube Monitor + Transcript Cleaner")
    print("="*60)
    
    try:
        db = DatabaseConnection()
        monitor = YouTubeChannelMonitor(db_manager=db)
        
        print("[1.1] Verificar canales cargados")
        estado = monitor.obtener_estado_monitor()
        print(f"  Canales activos: {estado['canales_activos']}")
        print(f"  Canales: {estado['canales']}")
        
        print("\n[1.2] Sincronizar canales (mock)")
        resultado = monitor.sincronizar_canales()
        print(f"  Canales procesados: {resultado['canales_procesados']}")
        print(f"  Videos descargados: {resultado['videos_descargados']}")
        print(f"  Transcripciones procesadas: {resultado['transcripciones_procesadas']}")
        print(f"  Tokens ahorrados: {resultado['tokens_ahorrados']}")
        
        print("\n[1.3] Obtener transcripciones limpias")
        transcripciones = monitor.obtener_transcripciones_limpias(limite=3)
        print(f"  Total recuperadas: {len(transcripciones)}")
        if transcripciones:
            print(f"  Última: {transcripciones[0]['titulo']} ({transcripciones[0]['tokens_limpios']} tokens limpios)")
        
        print("\n[OK] FASE 1 COMPLETADA")
        return True
    except Exception as e:
        print(f"[ERROR] FASE 1 fallo: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_fase_3():
    """Test FASE 3: Copywriting Engine (AIDA)"""
    print("\n" + "="*60)
    print("TEST FASE 3: Copywriting Engine (AIDA)")
    print("="*60)
    
    try:
        db = DatabaseConnection()
        engine = CopywrightingEngine(db_manager=db)
        
        print("[3.1] Validar prohibición de superlativos")
        texto_valido = "Este producto es bueno y funciona bien"
        texto_invalido = "Este producto es increible y alucinante"
        
        es_valido1, adjetivos1 = engine.validar_sin_superlativos(texto_valido)
        print(f"  Texto válido: {es_valido1} (adjetivos: {adjetivos1})")
        
        es_valido2, adjetivos2 = engine.validar_sin_superlativos(texto_invalido)
        print(f"  Texto inválido: {es_valido2} (adjetivos encontrados: {adjetivos2})")
        
        print("\n[3.2] Generar copy con AIDA")
        copy = engine.generar_copy_template(
            nombre_producto="Funda para Teléfono Premium",
            categoria="Accesorios",
            costo_origen=2.5,
            pvp=7.5,
            peso_kg=0.1
        )
        print(f"  Título: {copy['titulo']}")
        print(f"  Scores AIDA: A={copy['scores_aida']['attention']}, "
              f"I={copy['scores_aida']['interest']}, "
              f"D={copy['scores_aida']['decision']}, "
              f"A={copy['scores_aida']['action']}")
        print(f"  Sin superlativos: {copy['sin_superlativos']}")
        print(f"  Descripción (primeras 100 chars): {copy['descripcion'][:100]}...")
        
        print("\n[3.3] Guardar copy en BD")
        # Primero crear un producto de prueba (SKU único por ejecución)
        import time
        sku_unico = f"TEST-CP-{int(time.time())}"
        validator = FinancialValidator(db_manager=db)
        val = validator.validar_producto(sku_unico, 2.5, 0.1)
        id_producto = validator.guardar_validacion(val)
        print(f"  Producto creado con ID: {id_producto}")
        
        id_copy = engine.guardar_copy(id_producto, copy)
        print(f"  Copy guardado con ID: {id_copy}")
        
        print("\n[3.4] Reporte de copywriting")
        reporte = engine.obtener_reporte_copywriting()
        print(f"  Total copys: {reporte['total_copys']}")
        print(f"  Score promedio: {reporte['score_promedio']}")
        
        print("\n[OK] FASE 3 COMPLETADA")
        return True
    except Exception as e:
        print(f"[ERROR] FASE 3 fallo: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_fase_4():
    """Test FASE 4: TikTok Script Generator"""
    print("\n" + "="*60)
    print("TEST FASE 4: TikTok Script Generator")
    print("="*60)
    
    try:
        db = DatabaseConnection()
        generator = TikTokScriptGenerator(db_manager=db)
        
        print("[4.1] Generar guión individual con hook story-telling")
        guion = generator.generar_guion_completo(
            nombre_producto="Funda Premium",
            categoria="Accesorios",
            patron_hook='story-telling',
            duracion_segundos=60
        )
        print(f"  Hook: {guion['hook']}")
        print(f"  Duración estimada: {guion['duracion_segundos']} segundos")
        print(f"  CTA: {guion['cta']}")
        
        print("\n[4.2] Generar lote de 5 variantes")
        variantes = generator.generar_variantes_lote(
            nombre_producto="Funda Premium",
            categoria="Accesorios",
            cantidad=5
        )
        print(f"  Variantes generadas: {len(variantes)}")
        for i, v in enumerate(variantes, 1):
            print(f"    {i}. {v['patron_hook']} - {v['duracion_segundos']} seg")
        
        print("\n[4.3] Guardar guión en BD")
        # Crear producto de prueba propio (SKU único)
        import time
        validator = FinancialValidator(db_manager=db)
        sku_unico = f"TEST-TK-{int(time.time())}"
        val = validator.validar_producto(sku_unico, 3.0, 0.15)
        id_producto = validator.guardar_validacion(val)
        print(f"  Producto creado con ID: {id_producto}")
        id_guion = generator.guardar_guion(id_producto, guion)
        print(f"  Guión guardado con ID: {id_guion}")
        
        print("\n[4.4] Reporte de guiones")
        reporte = generator.obtener_reporte_guiones()
        print(f"  Total guiones: {reporte['total_guiones']}")
        print(f"  Duración promedio: {reporte['duracion_promedio_segundos']} segundos")
        
        print("\n[OK] FASE 4 COMPLETADA")
        return True
    except Exception as e:
        print(f"[ERROR] FASE 4 fallo: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecuta todos los tests."""
    print("\n" + "[TESTS] SUITE DE TESTS FASE 1, 3, 4")
    print("="*60)
    
    resultados = {
        'FASE 1 - YouTube Monitor': test_fase_1(),
        'FASE 3 - Copywriting AIDA': test_fase_3(),
        'FASE 4 - TikTok Scripts': test_fase_4(),
    }
    
    print("\n" + "="*60)
    print("RESUMEN DE TESTS")
    print("="*60)
    
    total_tests = len(resultados)
    tests_passed = sum(1 for v in resultados.values() if v)
    
    for test_name, passed in resultados.items():
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {test_name}")
    
    print(f"\nTotal: {tests_passed}/{total_tests} fases completadas")
    
    if tests_passed == total_tests:
        print("\n[OK] FASES 1, 3, 4 COMPLETADAS EXITOSAMENTE")
        return 0
    else:
        print("\n[ERROR] ALGUNAS FASES FALLARON")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
