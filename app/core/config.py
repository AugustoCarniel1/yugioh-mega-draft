from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "app" / "static"
IMAGE_CACHE_DIR = STATIC_DIR / "images"
DB_PATH = DATA_DIR / "yugioh_mega_draft.db"
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"
YGOPRODECK_BASE_URL = "https://db.ygoprodeck.com/api/v7"


def ensure_local_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

