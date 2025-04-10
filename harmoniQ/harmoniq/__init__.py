from pathlib import Path
import os

DEMANDE_PATH = Path(__file__).parent / "db" / "demande.db"

if os.environ.get("HARMONIQ_TESTING") == "True":
    DB_PATH = Path(__file__).parent / "db" / "test_db.sqlite"
else:
    DB_PATH = Path(__file__).parent / "db" / "db.sqlite"
