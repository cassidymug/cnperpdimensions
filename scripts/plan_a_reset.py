#!/usr/bin/env python3
"""Plan A Reset Framework.
Backs up selected tables then wipes & reseeds.
Usage:
  python scripts/plan_a_reset.py --all
  python scripts/plan_a_reset.py --what accounts units roles_permissions --force
"""
import argparse, json, datetime
from pathlib import Path
from sqlalchemy.sql import text
from app.core.database import get_db
from sqlalchemy.orm import Session
from scripts.seeds import registry  # seed registry
# force import seed modules
import scripts.seeds.seed_roles_permissions  # noqa
import scripts.seeds.seed_units  # noqa
import scripts.seeds.seed_accounts  # noqa
import scripts.seeds.seed_demo_users  # noqa

BACKUP_MAP = {
    "accounts":"accounting_codes",
    "units":"unit_of_measure",
    "roles_permissions":"roles,permissions,role_permissions",
    "demo_users":"users"
}

WIPE_SQL = {
    "accounts":["DELETE FROM accounting_codes"],
    "units":["DELETE FROM unit_of_measure"],
    "roles_permissions":["DELETE FROM role_permissions","DELETE FROM permissions","DELETE FROM roles"],
    "demo_users":["DELETE FROM users"],
}

REFERENCES_BLOCK = {
    "accounts":[("journal_entries","account_code_id"),("accounting_entries","account_code_id")],
}

def has_references(db: Session, item: str) -> bool:
    refs = REFERENCES_BLOCK.get(item, [])
    for table, col in refs:
        try:
            cnt = db.execute(text(f"SELECT 1 FROM {table} WHERE {col} IS NOT NULL LIMIT 1")).fetchone()
            if cnt: return True
        except Exception:
            continue
    return False

def backup_table(db: Session, table: str, out_dir: Path):
    ts = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"{table}_{ts}.json"
    rows = db.execute(text(f"SELECT * FROM {table}")).mappings().all()
    path.write_text(json.dumps([dict(r) for r in rows], indent=2))
    print(f"[backup] {table} -> {path}")

def backup_items(db: Session, items, out_dir: Path):
    out_dir.mkdir(exist_ok=True)
    for item in items:
        tables = BACKUP_MAP.get(item)
        if not tables: continue
        for t in tables.split(","):
            backup_table(db, t.strip(), out_dir)

def wipe_items(db: Session, items):
    for item in items:
        stmts = WIPE_SQL.get(item, [])
        for s in stmts:
            db.execute(text(s))
    db.commit()
    print(f"[wipe] Completed: {', '.join(items)}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--what", nargs="*", help="Specific seeds to reset")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    items = registry.list_seeders() if args.all else (args.what or [])
    if not items:
        print("No items specified. Use --all or --what")
        return

    db = next(get_db())
    try:
        for item in items:
            if not args.force and has_references(db, item):
                print(f"[abort] References detected for {item}; use --force to override.")
                return
        backup_items(db, items, Path("backups"))
        wipe_items(db, items)
        registry.run_selected(db, items)
        print("[done] Plan A reset complete.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
