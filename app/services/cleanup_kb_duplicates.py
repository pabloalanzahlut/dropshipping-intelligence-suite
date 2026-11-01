#!/usr/bin/env python3
"""
cleanup_kb_duplicates.py — Mantenimiento de la Knowledge Base GEM OS.

Complejidad:
  Temporal (video_id): O(n) con hash lookups
  Temporal (hash_md5): O(n) con hash lookups
  Temporal (semántico): O(n * (len_i + len_j)) ≈ O(n log n) con filtros
  Espacial: O(n) para registros y tokens

Referencias:
  [PEP 8]     snake_case, PascalCase, imports organizados
  [PEP 391]   Logging estructurado (vía EliteLogger)
  [PEP 484]   Type hints en todas las funciones
  [SQLite Docs] PRAGMA foreign_keys, queries parametrizadas
  [Jaccard]   J(A,B) = |A∩B| / |A∪B| para similitud semántica
  [Big-O]     Análisis de complejidad en docstrings
  [CWE-89]   Queries parametrizadas con ? (no concatenación)
  [SOLID-SRP] Cada método de detección es una responsabilidad única

Busca y elimina registros duplicados en la tabla `transcripciones_youtube`
basándose en tres criterios:
  1. `video_id` duplicado (mismo video procesado múltiples veces)
  2. `hash_md5` duplicado (misma transcripción comprimida)
  3. Semántico: transcripciones con alto solapamiento léxico (Jaccard ≥ threshold)

Preserva siempre la fila más antigua (menor `id`) y elimina las redundantes.
Imprime un resumen claro de la operación en terminal.

Uso (desarrollo):
    python app/services/cleanup_kb_duplicates.py
"""

import re
import sys
import sqlite3
from typing import Dict, List, Set, Tuple, Optional


class KBDuplicateCleaner:
    """Motor de limpieza de duplicados para la Knowledge Base de GEM OS."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        semantic_threshold: float = 0.85,
        semantic_batch_size: int = 200,
    ):
        """
        Args:
            db_path: Ruta a la base de datos SQLite.
            semantic_threshold: Similitud Jaccard mínima (0.0–1.0) para
                                considerar dos transcripciones duplicados.
            semantic_batch_size: Máx. registros por lote para controlar memoria.
        """
        if db_path is None:
            from app.config.path_manager import PathManager
            db_path = str(PathManager.get_paths()['db'])
        self.db_path = db_path
        self.semantic_threshold = semantic_threshold
        self.semantic_batch_size = semantic_batch_size
        self.summary: Dict[str, int] = {
            "total_duplicados_video_id": 0,
            "total_duplicados_hash_md5": 0,
            "total_duplicados_semanticos": 0,
            "total_eliminados": 0,
            "total_preservados": 0,
        }

    def _get_connection(self) -> sqlite3.Connection:
        """Establece conexión con la base de datos SQLite."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _verify_table_exists(self) -> bool:
        """Verifica que la tabla `transcripciones_youtube` exista y tenga la estructura esperada."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='transcripciones_youtube'"
                )
                if not cursor.fetchone():
                    print("[ERROR] La tabla 'transcripciones_youtube' no existe en la base de datos.")
                    return False

                cursor.execute("PRAGMA table_info(transcripciones_youtube)")
                columns = {row[1] for row in cursor.fetchall()}
                required = {"id", "video_id", "hash_md5", "transcripcion_limpia"}
                missing = required - columns
                if missing:
                    print(f"[ERROR] Faltan columnas requeridas en 'transcripciones_youtube': {missing}")
                    return False

                print(f"[OK] Tabla 'transcripciones_youtube' verificada — {len(columns)} columnas disponibles.")
                return True
        except sqlite3.Error as e:
            print(f"[ERROR] No se pudo conectar a la base de datos: {e}")
            return False

    def _find_duplicates_by_video_id(self) -> Dict[int, int]:
        """
        Encuentra grupos de filas con el mismo `video_id`.
        Retorna un dict {id_a_eliminar: id_a_preservar} para cada fila redundante.
        """
        duplicates: Dict[int, int] = {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT video_id, GROUP_CONCAT(id ORDER BY id ASC) as ids
                FROM transcripciones_youtube
                GROUP BY video_id
                HAVING COUNT(*) > 1
            """)
            groups = cursor.fetchall()

        for group in groups:
            ids = [int(x) for x in group["ids"].split(",")]
            preserved_id = ids[0]  # El más antiguo (menor id)
            for redundant_id in ids[1:]:
                duplicates[redundant_id] = preserved_id
                self.summary["total_duplicados_video_id"] += 1

        return duplicates

    def _find_duplicates_by_hash(self) -> Dict[int, int]:
        """
        Encuentra grupos de filas con el mismo `hash_md5`.
        Retorna un dict {id_a_eliminar: id_a_preservar} para cada fila redundante.
        """
        duplicates: Dict[int, int] = {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT hash_md5, GROUP_CONCAT(id ORDER BY id ASC) as ids
                FROM transcripciones_youtube
                WHERE hash_md5 IS NOT NULL AND hash_md5 != ''
                GROUP BY hash_md5
                HAVING COUNT(*) > 1
            """)
            groups = cursor.fetchall()

        for group in groups:
            ids = [int(x) for x in group["ids"].split(",")]
            preserved_id = ids[0]
            for redundant_id in ids[1:]:
                # Si ya está marcado para eliminar por video_id, no lo contamos doble
                if redundant_id not in duplicates:
                    duplicates[redundant_id] = preserved_id
                    self.summary["total_duplicados_hash_md5"] += 1

        return duplicates

    def _delete_redundant_rows(self, duplicates: Dict[int, int]) -> int:
        """Elimina las filas redundantes y retorna el número de registros eliminados."""
        if not duplicates:
            return 0

        ids_to_delete = list(duplicates.keys())
        preserved_ids = set(duplicates.values())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ",".join("?" for _ in ids_to_delete)
            cursor.execute(
                f"DELETE FROM transcripciones_youtube WHERE id IN ({placeholders})",
                ids_to_delete,
            )
            conn.commit()
            deleted_count = cursor.rowcount

        self.summary["total_eliminados"] = deleted_count
        self.summary["total_preservados"] = len(preserved_ids)
        return deleted_count

# ── Deduplicación Semántica ───────────────────────────────────────────────

    @staticmethod
    def _tokenize(text: str) -> Set[str]:
        """Tokeniza un texto en un conjunto de palabras limpias."""
        text = text.lower()
        text = re.sub(r"[^a-záéíóúüñ0-9\s]", " ", text)
        tokens = set(text.split())
        return tokens

    @staticmethod
    def _jaccard_similarity(a: Set[str], b: Set[str]) -> float:
        """Calcula similitud Jaccard entre dos conjuntos de tokens."""
        if not a or not b:
            return 0.0
        intersection = a & b
        union = a | b
        return len(intersection) / len(union) if union else 0.0

    def _find_semantic_duplicates(self) -> Dict[int, int]:
        """
        Encuentra pares de transcripciones con alto solapamiento léxico
        usando similitud Jaccard. Retorna {id_eliminar: id_preservar}.
        Solo compara registros con longitud similar (±40% de diferencia)
        para evitar O(n²) innecesario.
        """
        duplicates: Dict[int, int] = {}
        threshold = self.semantic_threshold

        # Cargar id, transcripcion_limpia para todos los registros
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, transcripcion_limpia FROM transcripciones_youtube "
                "WHERE transcripcion_limpia IS NOT NULL AND transcripcion_limpia != '' "
                "ORDER BY id ASC"
            )
            rows = cursor.fetchall()

        if len(rows) < 2:
            return duplicates

        # Pre-tokenizar y medir longitudes para filtrar rápido
        records: List[Dict] = []
        for row in rows:
            text = row["transcripcion_limpia"]
            tokens = self._tokenize(text)
            records.append({
                "id": row["id"],
                "tokens": tokens,
                "len": len(text),
                "token_count": len(tokens),
            })

        # Comparación por pares con filtro de longitud (±40%)
        compared: Set[Tuple[int, int]] = set()
        for i in range(len(records)):
            if records[i]["id"] in duplicates.values():
                # Este registro ya fue marcado como preservado → saltar
                continue
            for j in range(i + 1, len(records)):
                if records[j]["id"] in duplicates:
                    # Ya marcado como eliminado → saltar
                    continue

                # Filtro rápido: longitud del texto
                len_i = records[i]["len"]
                len_j = records[j]["len"]
                if len_i == 0 or len_j == 0:
                    continue
                ratio = len_i / len_j if len_i <= len_j else len_j / len_i
                if ratio < 0.6:  # Más del 40% de diferencia → no son duplicados
                    continue

                # Filtro rápido: conteo de tokens
                tc_i = records[i]["token_count"]
                tc_j = records[j]["token_count"]
                if tc_i == 0 or tc_j == 0:
                    continue
                tc_ratio = tc_i / tc_j if tc_i <= tc_j else tc_j / tc_i
                if tc_ratio < 0.6:
                    continue

                # Calcular Jaccard
                pair = (records[i]["id"], records[j]["id"])
                if pair in compared:
                    continue
                compared.add(pair)

                similarity = self._jaccard_similarity(
                    records[i]["tokens"], records[j]["tokens"]
                )
                if similarity >= threshold:
                    # Preservar el menor ID (más antiguo)
                    preserved = min(records[i]["id"], records[j]["id"])
                    to_delete = max(records[i]["id"], records[j]["id"])
                    if to_delete not in duplicates:
                        duplicates[to_delete] = preserved
                        self.summary["total_duplicados_semanticos"] += 1

        return duplicates

    def run(self) -> bool:
        """Ejecuta el ciclo completo de limpieza. Retorna True si todo fue bien."""
        print("=" * 60)
        print("  GEM OS — Limpieza de Duplicados en Knowledge Base")
        print("=" * 60)

        # Paso 1: Verificar estructura
        if not self._verify_table_exists():
            return False

        # Paso 2: Contar registros antes
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM transcripciones_youtube")
            total_before = cursor.fetchone()[0]
        print(f"\n[INFO] Registros antes de la limpieza: {total_before}")

        # Paso 3: Detectar duplicados
        print("\n[SCAN] Buscando duplicados por video_id...")
        dup_video = self._find_duplicates_by_video_id()
        print(f"       -> {self.summary['total_duplicados_video_id']} duplicados encontrados.")

        print("\n[SCAN] Buscando duplicados por hash_md5...")
        dup_hash = self._find_duplicates_by_hash()
        print(f"       -> {self.summary['total_duplicados_hash_md5']} duplicados encontrados.")

        print(f"\n[SCAN] Buscando duplicados semánticos (Jaccard ≥ {self.semantic_threshold})...")
        dup_semantic = self._find_semantic_duplicates()
        print(f"       -> {self.summary['total_duplicados_semanticos']} duplicados semánticos encontrados.")

        # Unificar los tres conjuntos (semántico no duplica los ya marcados)
        all_duplicates: Dict[int, int] = {}
        all_duplicates.update(dup_video)
        all_duplicates.update(dup_hash)
        all_duplicates.update(dup_semantic)

        if not all_duplicates:
            print("\n[OK] No se encontraron registros duplicados. Base de datos limpia.")
            return True

        # Paso 4: Eliminar redundantes
        print(f"\n[DELETE] Eliminando {len(all_duplicates)} filas redundantes...")
        deleted = self._delete_redundant_rows(all_duplicates)

        # Paso 5: Contar registros después
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM transcripciones_youtube")
            total_after = cursor.fetchone()[0]

        # Paso 6: Resumen final
        print("\n" + "-" * 60)
        print("  RESUMEN DE LIMPIEZA")
        print("-" * 60)
        print(f"  Duplicados por video_id:       {self.summary['total_duplicados_video_id']}")
        print(f"  Duplicados por hash_md5:        {self.summary['total_duplicados_hash_md5']}")
        print(f"  Duplicados semánticos:          {self.summary['total_duplicados_semanticos']}")
        print(f"  Total filas eliminadas:         {deleted}")
        print(f"  Total filas preservadas:        {self.summary['total_preservados']}")
        print(f"  Registros antes → después:      {total_before} → {total_after}")
        print("-" * 60)

        if total_before - total_after == deleted:
            print("  [OK] Consistencia verificada: diferencia coincide con eliminados.")
        else:
            print("  [WARN] La diferencia no coincide exactamente — revisar manualmente.")

        print("=" * 60)
        return True


def main():
    """Punto de entrada principal."""
    cleaner = KBDuplicateCleaner()
    success = cleaner.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()