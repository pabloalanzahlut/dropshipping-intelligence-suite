#!/usr/bin/env python3
"""Inicializacion en Frio de GEM OS - Base de Datos SQLite"""

import sys
import io

if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from app.database.connection import DatabaseConnection

def init_database():
    """Inicializa la base de datos con esquema operacional."""
    print("[INIT] Inicializando base de datos GEM OS...")
    print("-" * 60)
    
    try:
        db = DatabaseConnection()
        print("[OK] Conexion a BD establecida")
        print("[DB] Ruta: app/database/dropshipping_suite.db")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"\n[TABLES] Esquema creado: {len(tables)} tablas")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"  [OK] {table[0]:25s} ({count} registros)")
        
        print(f"\n[COLUMNS] Validacion de columnas criticas:")
        
        cursor.execute("PRAGMA table_info(operations_traffic)")
        columns = cursor.fetchall()
        col_names = [col[1] for col in columns]
        
        if 'weight_kg' in col_names:
            print(f"  [OK] weight_kg en operations_traffic (REAL)")
        else:
            print(f"  [FAIL] weight_kg NO ENCONTRADO")
            return False
        
        cursor.execute("PRAGMA table_info(product_trends)")
        columns = cursor.fetchall()
        col_names = [col[1] for col in columns]
        
        if 'estimated_margin' in col_names:
            print(f"  [OK] estimated_margin en product_trends (REAL)")
        else:
            print(f"  [FAIL] estimated_margin NO ENCONTRADO")
            return False
        
        cursor.execute("PRAGMA table_info(conversion_formulas)")
        columns = cursor.fetchall()
        col_names = [col[1] for col in columns]
        
        if 'framework_name' in col_names:
            print(f"  [OK] framework_name en conversion_formulas (TEXT)")
        else:
            print(f"  [FAIL] framework_name NO ENCONTRADO")
            return False
        
        conn.close()
        print(f"\n[SUCCESS] Base de datos inicializada")
        print("-" * 60)
        return True
        
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
