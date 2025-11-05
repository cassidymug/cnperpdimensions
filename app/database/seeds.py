"""Unified seeding entrypoint.

This module is imported by scripts like `seed_postgresql.py` and
`reseed_postgresql.py`. It delegates to either the "clean" minimal
seed set (clean_seeds) or the comprehensive IFRS-style seed set
(`seed_all`).

Selection logic:
  * If environment variable CNPERP_SEED_MODE is set to 'clean', use clean_seeds
  * Otherwise default to comprehensive seed_all

Both target modules expose a `seed_database()` function.
"""

from os import getenv

def seed_database():  # pragma: no cover - thin delegation
	mode = getenv("CNPERP_SEED_MODE", "all").lower()
	if mode == "clean":
		from .clean_seeds import seed_database as _seed
		print("🧪 Using CLEAN seed mode (minimal dataset)")
	else:
		from .seed_all import seed_database as _seed
		print("📚 Using FULL seed mode (comprehensive chart + demo data)")
	return _seed()

__all__ = ["seed_database"]
