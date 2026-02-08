"""HarmoniQ package: paths (DB, demande), used by db and scripts."""

import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
DEMANDE_PATH = _ROOT / "db" / "demande.db"
METEO_DATA_PATH = _ROOT / "db" / "meteo_data.csv"

if os.environ.get("HARMONIQ_TESTING") == "True":
    DB_PATH = _ROOT / "db" / "test_db.sqlite"
else:
    DB_PATH = _ROOT / "db" / "db.sqlite"
