"""
Remove demo/test assets from the database safely.

Usage (dry run by default):
  python scripts/remove_test_assets.py

Actually delete matched assets (requires --confirm):
  python scripts/remove_test_assets.py --confirm

Options:
  --include-inventory  Also remove assets linked to inventory items (defaults to skip)
  --include-all        Ignore heuristics and delete ALL assets (dangerous; requires --confirm)

Heuristics for test/demo assets:
  - asset_code ILIKE 'TEST%%' OR 'DEMO%%' OR 'SAMPLE%%'
  - name ILIKE 'test%%' OR 'demo%%' OR 'sample%%'
  - notes ILIKE '%%test%%' OR '%%demo%%' OR '%%sample%%'
"""

from __future__ import annotations

import argparse
from typing import List

import sys
from pathlib import Path

# Ensure project root (containing 'app') is on sys.path when running as a script
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import SessionLocal
from app.models.asset_management import Asset, AssetMaintenance, AssetDepreciation, AssetImage
from sqlalchemy import or_, and_


def find_test_assets(session, include_all: bool = False, include_inventory: bool = False) -> List[Asset]:
    q = session.query(Asset)
    if not include_all:
        patterns = [
            Asset.asset_code.ilike('TEST%'),
            Asset.asset_code.ilike('DEMO%'),
            Asset.asset_code.ilike('SAMPLE%'),
            Asset.name.ilike('test%'),
            Asset.name.ilike('demo%'),
            Asset.name.ilike('sample%'),
            Asset.notes.ilike('%test%'),
            Asset.notes.ilike('%demo%'),
            Asset.notes.ilike('%sample%'),
        ]
        q = q.filter(or_(*patterns))
    if not include_inventory:
        q = q.filter(or_(Asset.inventory_item_id.is_(None), Asset.inventory_item_id == ''))
    return q.all()


def delete_assets(session, asset_ids: List[str]) -> int:
    if not asset_ids:
        return 0
    # Delete child records first to satisfy FK constraints
    session.query(AssetMaintenance).filter(AssetMaintenance.asset_id.in_(asset_ids)).delete(synchronize_session=False)
    session.query(AssetDepreciation).filter(AssetDepreciation.asset_id.in_(asset_ids)).delete(synchronize_session=False)
    session.query(AssetImage).filter(AssetImage.asset_id.in_(asset_ids)).delete(synchronize_session=False)
    # Delete assets
    deleted = session.query(Asset).filter(Asset.id.in_(asset_ids)).delete(synchronize_session=False)
    return deleted


def main():
    parser = argparse.ArgumentParser(description="Remove demo/test assets safely")
    parser.add_argument('--confirm', action='store_true', help='Actually delete matched assets')
    parser.add_argument('--include-inventory', action='store_true', help='Also delete assets linked to inventory items')
    parser.add_argument('--include-all', action='store_true', help='Delete ALL assets (requires --confirm)')
    args = parser.parse_args()

    db = SessionLocal()
    try:
        to_delete = find_test_assets(db, include_all=args.include_all, include_inventory=args.include_inventory)
        count = len(to_delete)
        print(f"Matched assets: {count}")
        for a in to_delete[:25]:
            print(f" - {a.id} | {a.asset_code} | {a.name} | {a.category}")
        if count > 25:
            print(f"... and {count - 25} more")

        if count == 0:
            print("No matching assets to delete.")
            return

        if not args.confirm:
            print("\nDry run only. Re-run with --confirm to delete.")
            return

        ids = [a.id for a in to_delete]
        deleted = delete_assets(db, ids)
        db.commit()
        print(f"Deleted {deleted} assets and their related records.")
    except Exception as e:
        db.rollback()
        print(f"Error during deletion: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    main()
