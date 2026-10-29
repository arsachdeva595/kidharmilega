"""
Buyer Finder — personal export-lead tool.

HSN code in, scored list of overseas buyers out, each backed by a customs
record. Run it with `python3 -m buyer_finder --help`; see buyer_finder/README.md.
"""

import os
from pathlib import Path

BASE_DIR     = Path(__file__).resolve().parent.parent
DATA_DIR     = Path(os.environ.get("BUYER_FINDER_DATA", BASE_DIR / "data" / "buyer_finder"))  # gitignored: leads stay local
DB_FILE      = DATA_DIR / "buyer_finder.db"
PROFILES_DIR = DATA_DIR / "profiles"
EXPORTS_DIR  = DATA_DIR / "exports"


def ensure_dirs():
    for d in (DATA_DIR, PROFILES_DIR, EXPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)
