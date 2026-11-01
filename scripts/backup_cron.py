"""
backup_cron.py — Backup automático programable (FASE 6D)
=====================================================================
Backups periódicos de:
  - dropshipping_suite.db
  - youtube_channels.json
  - queue_state.json

Puede ejecutarse manualmente o registrarse en el Programador de Tareas
de Windows (equivalente a cron) mediante el comando:

    python scripts/backup_cron.py                 # backup + verificación
    python scripts/backup_cron.py --no-verify      # solo backup
    python scripts/backup_cron.py --prune 45       # retención personalizada (días)

Registro en Windows Task Scheduler (cron):
    schtasks /Create /TN "GEM_OS_Backup" /TR "python C:\\ruta\\scripts\\backup_cron.py"
             /SC DAILY /ST 03:00 /F
"""

import argparse
import json
import sys
from datetime import datetime, timezone

from app.config.path_manager import PathManager
from app.services.kb_backup import (
    run_config_backup,
    verify_backup,
    list_backups,
)


def _prune_inventory(keep_days: int) -> int:
    """Elimina entradas de inventario y archivos backup más antiguos que keep_days."""
    from pathlib import Path
    from datetime import timedelta
    import os

    backup_dir = PathManager.get_paths()['backups']
    cutoff = datetime.now() - timedelta(days=keep_days)
    removed = 0
    for f in backup_dir.glob("*.backup.*"):
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            f.unlink(missing_ok=True)
            removed += 1
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup automático GEM OS (FASE 6D)")
    parser.add_argument("--no-verify", action="store_true",
                        help="Omitir verificación de checksum post-backup")
    parser.add_argument("--prune", type=int, default=30,
                        help="Retención en días (por defecto 30)")
    args = parser.parse_args()

    print("=" * 62)
    print("  GEM OS — BACKUP AUTOMÁTICO (FASE 6D)")
    print("=" * 62)

    # 1. Ejecutar backup de configuración runtime
    result = run_config_backup()
    status = result.get("status", "FAIL")
    print(f"\n[BACKUP] Estado: {status} | ítems: {len(result.get('items', []))}")
    for item in result.get("items", []):
        print(f"  - {item.get('name')}: {item.get('dest')} "
              f"({item.get('size_mb')}MB SHA256:{item.get('checksum_sha256', '')[:12]}...)")

    # 2. Verificar checksums (opcional)
    if not args.no_verify:
        print("\n[VERIFY] Verificando integridad de backups...")
        ok = 0
        for item in result.get("items", []):
            if verify_backup(item.get("dest", "")):
                ok += 1
        print(f"[VERIFY] {ok}/{len(result.get('items', []))} verificados correctamente")
        if ok < len(result.get("items", [])):
            print("[VERIFY] ⚠️  Se detectaron inconsistencias. Revise el inventario.")
    else:
        print("\n[VERIFY] Omitido (--no-verify)")

    # 3. Poda de backups antiguos
    pruned = _prune_inventory(args.prune)
    if pruned:
        print(f"[PRUNE] {pruned} archivo(s) antiguo(s) eliminados (> {args.prune} días)")

    # 4. Resumen final
    inv = list_backups()
    print(f"\n[INVENTORY] {len(inv)} respaldo(s) registrado(s). "
          f"Último: {inv[-1].get('timestamp', 'N/A') if inv else 'N/A'}")
    print("=" * 62)

    return 0 if status == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
