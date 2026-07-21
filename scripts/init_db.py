import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import DB_PATH, ensure_local_dirs


def init_db_with_sqlite() -> None:
    import sqlite3

    ensure_local_dirs()
    with sqlite3.connect(DB_PATH) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS player (
                id INTEGER NOT NULL PRIMARY KEY,
                name VARCHAR NOT NULL UNIQUE,
                gold REAL NOT NULL DEFAULT 0,
                current_collection_index INTEGER NOT NULL DEFAULT -1,
                created_at DATETIME NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_player_name ON player (name);

            CREATE TABLE IF NOT EXISTS card (
                id INTEGER NOT NULL PRIMARY KEY,
                name VARCHAR NOT NULL,
                type VARCHAR,
                desc VARCHAR,
                race VARCHAR,
                archetype VARCHAR,
                card_images JSON,
                card_sets JSON,
                cached_image_path VARCHAR,
                updated_at DATETIME NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_card_name ON card (name);

            CREATE TABLE IF NOT EXISTS inventoryitem (
                id INTEGER NOT NULL PRIMARY KEY,
                player_id INTEGER NOT NULL,
                card_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                rarity VARCHAR NOT NULL DEFAULT 'Common',
                source VARCHAR NOT NULL DEFAULT 'starter_deck',
                FOREIGN KEY(player_id) REFERENCES player (id),
                FOREIGN KEY(card_id) REFERENCES card (id)
            );
            CREATE INDEX IF NOT EXISTS ix_inventoryitem_player_id ON inventoryitem (player_id);
            CREATE INDEX IF NOT EXISTS ix_inventoryitem_card_id ON inventoryitem (card_id);

            CREATE TABLE IF NOT EXISTS cardrestriction (
                id INTEGER NOT NULL PRIMARY KEY,
                player_id INTEGER NOT NULL,
                card_id INTEGER NOT NULL,
                status VARCHAR NOT NULL DEFAULT 'limited',
                created_at DATETIME NOT NULL,
                FOREIGN KEY(player_id) REFERENCES player (id),
                FOREIGN KEY(card_id) REFERENCES card (id),
                UNIQUE(player_id, card_id)
            );
            CREATE INDEX IF NOT EXISTS ix_cardrestriction_player_id ON cardrestriction (player_id);
            CREATE INDEX IF NOT EXISTS ix_cardrestriction_card_id ON cardrestriction (card_id);
            CREATE INDEX IF NOT EXISTS ix_cardrestriction_status ON cardrestriction (status);

            CREATE TABLE IF NOT EXISTS collectionprogress (
                id INTEGER NOT NULL PRIMARY KEY,
                set_name VARCHAR NOT NULL UNIQUE,
                set_code VARCHAR,
                tcg_date VARCHAR,
                card_count INTEGER,
                position INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_collectionprogress_set_name ON collectionprogress (set_name);
            CREATE INDEX IF NOT EXISTS ix_collectionprogress_tcg_date ON collectionprogress (tcg_date);
            CREATE INDEX IF NOT EXISTS ix_collectionprogress_position ON collectionprogress (position);
            """
        )
        gold_info = connection.execute("PRAGMA table_info(player)").fetchall()
        gold_column = next((column for column in gold_info if column[1] == "gold"), None)
        if gold_column and str(gold_column[2]).upper() != "REAL":
            connection.executescript(
                """
                ALTER TABLE player RENAME TO player_old;
                CREATE TABLE player (
                    id INTEGER NOT NULL PRIMARY KEY,
                    name VARCHAR NOT NULL UNIQUE,
                    gold REAL NOT NULL DEFAULT 0,
                    current_collection_index INTEGER NOT NULL DEFAULT -1,
                    created_at DATETIME NOT NULL
                );
                INSERT INTO player (id, name, gold, current_collection_index, created_at)
                SELECT id, name, gold, current_collection_index, created_at FROM player_old;
                DROP TABLE player_old;
                CREATE INDEX IF NOT EXISTS ix_player_name ON player (name);
                """
            )


try:
    from app.db import init_db
except ModuleNotFoundError:
    init_db = init_db_with_sqlite


if __name__ == "__main__":
    init_db()
    print("Banco SQLite inicializado em data/yugioh_mega_draft.db")
