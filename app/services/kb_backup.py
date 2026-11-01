"""
N3 - KB BACKUP (Nivel 3: Backup con Seguridad)
═══════════════════════════════════════════════
Backup Knowledge Base: SHA-256 checksum, inventory,
limpieza automática >30 días.
Cumple con: Pre-Flight Backup & DR (Agent-KB.md)
═══════════════════════════════════════════════
"""
import os, json, shutil, sqlite3, hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from app.services.elite_logger import logger
from app.config.path_manager import PathManager

BACKUP_DIR = PathManager.get_paths()['backups']
RETENTION_DAYS = 30

def _sha256_file(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""): h.update(chunk)
    return h.hexdigest()

def _load_inventory() -> List[Dict]:
    inv_file = BACKUP_DIR.parent / "backup_inventory.json"
    if inv_file.exists():
        try: return json.loads(inv_file.read_text())
        except: return []
    return []

def _save_inventory(inv: List[Dict]):
    (BACKUP_DIR.parent / "backup_inventory.json").write_text(
        json.dumps(inv, indent=2, ensure_ascii=False))

def _cleanup_old_backups():
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS); count = 0
    for f in BACKUP_DIR.glob("*.backup.*"):
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            f.unlink(); count += 1
    if count > 0: logger.info(f"Backup| Cleanup: {count} archivos >{RETENTION_DAYS}d")

def backup_database(db_path=None, backup_name=None) -> Optional[Dict]:
    if db_path is None:
        db_path = str(BACKUP_DIR / "dropshipping_suite.db")
        if not Path(db_path).exists():
            db_path = str(PathManager.get_paths()['db'])
    src = Path(db_path)
    if not src.exists():
        return logger.warning(f"Backup| DB no encontrada: {db_path}") or None
    name = backup_name or "dropshipping_suite"
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"{name}.backup.{ts}.db"
    try:
        conn = sqlite3.connect(str(src))
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
        shutil.copy2(str(src), str(dest))
    except Exception as e:
        return logger.error(f"Backup| Error copiando DB: {e}") or None
    # Verify SQLite
    try:
        conn = sqlite3.connect(str(dest))
        conn.execute("SELECT COUNT(*) FROM sqlite_master")
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Backup| Backup corrupto: {e}")
        dest.unlink()
        return None
    cs = _sha256_file(str(dest))
    mb = dest.stat().st_size / (1024 * 1024)
    result = {
        "name": name,
        "source": str(src.resolve()),
        "dest": str(dest.resolve()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checksum_sha256": cs,
        "size_mb": round(mb, 2),
        "status": "OK",
    }
    inv = _load_inventory()
    inv.append(result)
    _save_inventory(inv)
    _cleanup_old_backups()
    logger.success(f"Backup| DB -> {dest.name} ({mb:.1f}MB SHA256:{cs[:12]}...)")
    return result

def backup_directory(source_dir, backup_name=None) -> Optional[Dict]:
    src = Path(source_dir)
    if not src.exists() or not src.is_dir():
        return logger.warning(f"Backup| Directorio no encontrado: {source_dir}") or None
    name = backup_name or src.name; BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"{name}.backup.{ts}.zip"
    try:
        shutil.make_archive(str(dest.with_suffix("")), "zip", root_dir=str(src.parent), base_dir=src.name)
        actual = Path(str(dest.with_suffix("")) + ".zip") if not dest.exists() else dest
    except OSError as e: return logger.error(f"Backup| Error comprimiendo: {e}") or None
    cs = _sha256_file(str(actual)); mb = actual.stat().st_size/(1024*1024)
    result = {"name":name,"source":str(src.resolve()),"dest":str(actual.resolve()),
              "timestamp":datetime.now(timezone.utc).isoformat(),"checksum_sha256":cs,"size_mb":round(mb,2),"status":"OK"}
    inv = _load_inventory(); inv.append(result); _save_inventory(inv)
    _cleanup_old_backups()
    logger.success(f"Backup| Dir -> {actual.name} ({mb:.1f}MB SHA256:{cs[:12]}...)")
    return result

def verify_backup(backup_path: str) -> bool:
    path = Path(backup_path)
    if not path.exists(): return logger.warning(f"Backup| Verify: no encontrado: {backup_path}") or False
    inv = _load_inventory()
    found = [i for i in inv if i.get("dest") == str(path.resolve())]
    if found:
        exp = found[-1].get("checksum_sha256",""); act = _sha256_file(str(path))
        if exp and exp != act:
            logger.error(f"Backup| Verify: CHECKSUM MISMATCH! {exp[:16]}... != {act[:16]}..."); return False
    if path.suffix == ".db":
        try:
            conn = sqlite3.connect(str(path)); cur = conn.cursor()
            cur.execute("PRAGMA integrity_check"); ok = cur.fetchone()[0]; conn.close()
            if ok != "ok": logger.error(f"Backup| Verify: SQLite FAIL: {ok}"); return False
            logger.success(f"Backup| Verify: SQLite integro")
        except sqlite3.Error as e: logger.error(f"Backup| Verify: SQLite error: {e}"); return False
    logger.success(f"Backup| Verify: {path.name} -> INTEGRO"); return True

def list_backups() -> List[Dict]: return _load_inventory()

def run_backup(db_path=None, workspace="ai_workspace") -> Dict:
    logger.info("Backup| Iniciando backup completo...")
    results = {"timestamp":datetime.now(timezone.utc).isoformat(),"items":[]}
    if db_path is None:
        db_path = str(PathManager.get_paths()['db'])
    db = backup_database(db_path); ws = backup_directory(workspace,"ai_workspace")
    if db: results["items"].append(db)
    if ws: results["items"].append(ws)
    results["status"] = "OK" if results["items"] else "FAIL"
    logger.success(f"Backup| Completo: {len(results['items'])} items"); return results


def backup_json_file(file_path: Optional[str] = None, backup_name: Optional[str] = None) -> Optional[Dict]:
    """
    Realiza backup de un único archivo JSON (p. ej. youtube_channels.json o
    queue_state.json) con checksum SHA-256 e inventario. (FASE 6D)

    Args:
        file_path: Ruta absoluta al archivo. Si es None, no se ejecuta.
        backup_name: Nombre lógico para el backup (por defecto el nombre base).

    Returns:
        Dict con metadatos del backup, o None si no existe / falla.
    """
    if file_path is None:
        return logger.warning("Backup| JSON: file_path requerido") or None
    src = Path(file_path)
    if not src.exists():
        return logger.warning(f"Backup| JSON no encontrado: {file_path}") or None
    try:
        # Validar que sea JSON parseable antes de respaldar
        json.loads(src.read_text(encoding="utf-8"))
    except Exception as e:
        return logger.error(f"Backup| JSON inválido: {file_path} -> {e}") or None
    name = backup_name or src.stem
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"{name}.backup.{ts}.json"
    try:
        shutil.copy2(str(src), str(dest))
    except OSError as e:
        return logger.error(f"Backup| Error copiando JSON: {e}") or None
    cs = _sha256_file(str(dest))
    mb = dest.stat().st_size / (1024 * 1024)
    result = {
        "name": name,
        "source": str(src.resolve()),
        "dest": str(dest.resolve()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checksum_sha256": cs,
        "size_mb": round(mb, 2),
        "status": "OK",
    }
    inv = _load_inventory(); inv.append(result); _save_inventory(inv)
    _cleanup_old_backups()
    logger.success(f"Backup| JSON -> {dest.name} ({mb:.1f}MB SHA256:{cs[:12]}...)")
    return result


def run_config_backup() -> Dict:
    """
    Backup completo de configuración runtime (FASE 6D):
      - dropshipping_suite.db
      - youtube_channels.json
      - queue_state.json
    Retorna Dict con el detalle de cada ítem respaldado.
    """
    logger.info("Backup| Iniciando backup de configuración...")
    paths = PathManager.get_paths()
    results = {"timestamp": datetime.now(timezone.utc).isoformat(), "items": []}
    candidates = [
        ("dropshipping_suite", str(paths['db']), "db"),
        ("youtube_channels", str(paths['config']), "json"),
        ("queue_state", str(paths['queue']), "json"),
    ]
    for name, path, kind in candidates:
        if kind == "db":
            item = backup_database(path, backup_name=name)
        else:
            item = backup_json_file(path, backup_name=name)
        if item:
            results["items"].append(item)
    results["status"] = "OK" if results["items"] else "FAIL"
    logger.success(f"Backup| Config completo: {len(results['items'])} items")
    return results