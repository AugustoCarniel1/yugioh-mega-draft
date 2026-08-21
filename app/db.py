from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import DATABASE_URL, ensure_local_dirs
from app.models import Base


ensure_local_dirs()
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _run_player_migrations() -> None:
    with engine.begin() as connection:
        columns = connection.exec_driver_sql("PRAGMA table_info(player)").fetchall()
        column_names = {column[1] for column in columns}
        if "boss_pick_pending" not in column_names:
            connection.exec_driver_sql("ALTER TABLE player ADD COLUMN boss_pick_pending BOOLEAN DEFAULT 0")
        if "pending_year_pick_year" not in column_names:
            connection.exec_driver_sql("ALTER TABLE player ADD COLUMN pending_year_pick_year INTEGER")
        if "year_pick_claims" not in column_names:
            connection.exec_driver_sql("ALTER TABLE player ADD COLUMN year_pick_claims JSON DEFAULT '{}'")
        connection.exec_driver_sql(
            "UPDATE player SET boss_pick_pending = 0 WHERE boss_pick_pending IS NULL"
        )
        connection.exec_driver_sql(
            "UPDATE player SET year_pick_claims = '{}' WHERE year_pick_claims IS NULL OR TRIM(year_pick_claims) = ''"
        )
        if "active_deck_id" not in column_names:
            connection.exec_driver_sql("ALTER TABLE player ADD COLUMN active_deck_id INTEGER")


def _run_saved_deck_migrations() -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS saveddeck (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                name VARCHAR NOT NULL DEFAULT 'Deck Principal',
                created_at DATETIME,
                FOREIGN KEY(player_id) REFERENCES player (id)
            )
            """
        )
        connection.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_saveddeck_player_name ON saveddeck (player_id, name)"
        )
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_saveddeck_player_id ON saveddeck (player_id)")

        deck_columns = connection.exec_driver_sql("PRAGMA table_info(deckcard)").fetchall()
        deck_column_names = {column[1] for column in deck_columns}
        if "saved_deck_id" not in deck_column_names:
            connection.exec_driver_sql("ALTER TABLE deckcard ADD COLUMN saved_deck_id INTEGER")
            connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_deckcard_saved_deck_id ON deckcard (saved_deck_id)")

        player_ids = [row[0] for row in connection.exec_driver_sql("SELECT id FROM player").fetchall()]
        for player_id in player_ids:
            deck_id = connection.exec_driver_sql(
                "SELECT id FROM saveddeck WHERE player_id = ? ORDER BY id LIMIT 1",
                (player_id,),
            ).scalar()
            if deck_id is None:
                connection.exec_driver_sql(
                    "INSERT INTO saveddeck (player_id, name, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                    (player_id, "Deck Principal"),
                )
                deck_id = connection.exec_driver_sql("SELECT last_insert_rowid()").scalar()
            connection.exec_driver_sql(
                "UPDATE deckcard SET saved_deck_id = ? WHERE player_id = ? AND saved_deck_id IS NULL",
                (deck_id, player_id),
            )
            connection.exec_driver_sql(
                "UPDATE player SET active_deck_id = ? WHERE id = ? AND (active_deck_id IS NULL OR TRIM(CAST(active_deck_id AS TEXT)) = '')",
                (deck_id, player_id),
            )

        index_rows = connection.exec_driver_sql("PRAGMA index_list(deckcard)").fetchall()
        has_legacy_unique = any(row[1] == "sqlite_autoindex_deckcard_1" or row[1] == "uq_deck_player_card_zone" for row in index_rows)
        if has_legacy_unique:
            connection.exec_driver_sql(
                """
                CREATE TABLE IF NOT EXISTS deckcard_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER NOT NULL,
                    saved_deck_id INTEGER,
                    card_id INTEGER NOT NULL,
                    zone VARCHAR NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY(player_id) REFERENCES player (id),
                    FOREIGN KEY(saved_deck_id) REFERENCES saveddeck (id),
                    FOREIGN KEY(card_id) REFERENCES card (id),
                    CONSTRAINT uq_deck_saveddeck_card_zone UNIQUE (saved_deck_id, card_id, zone)
                )
                """
            )
            connection.exec_driver_sql(
                """
                INSERT INTO deckcard_new (id, player_id, saved_deck_id, card_id, zone, quantity)
                SELECT id, player_id, saved_deck_id, card_id, zone, quantity
                FROM deckcard
                """
            )
            connection.exec_driver_sql("DROP TABLE deckcard")
            connection.exec_driver_sql("ALTER TABLE deckcard_new RENAME TO deckcard")
            connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_deckcard_player_id ON deckcard (player_id)")
            connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_deckcard_saved_deck_id ON deckcard (saved_deck_id)")
            connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_deckcard_card_id ON deckcard (card_id)")
            connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_deckcard_zone ON deckcard (zone)")


def _run_card_catalog_migrations() -> None:
    with engine.begin() as connection:
        card_columns = {
            column[1] for column in connection.exec_driver_sql("PRAGMA table_info(card)").fetchall()
        }
        for column_name, column_type in {
            "frame_type": "VARCHAR",
            "attribute": "VARCHAR",
            "atk": "INTEGER",
            "defense": "INTEGER",
            "level": "INTEGER",
            "linkval": "INTEGER",
            "scale": "INTEGER",
        }.items():
            if column_name not in card_columns:
                connection.exec_driver_sql(f"ALTER TABLE card ADD COLUMN {column_name} {column_type}")

        collection_columns = {
            column[1]
            for column in connection.exec_driver_sql("PRAGMA table_info(collectionprogress)").fetchall()
        }
        if "cards_synced_at" not in collection_columns:
            connection.exec_driver_sql("ALTER TABLE collectionprogress ADD COLUMN cards_synced_at DATETIME")
        if "cards_sync_error" not in collection_columns:
            connection.exec_driver_sql("ALTER TABLE collectionprogress ADD COLUMN cards_sync_error VARCHAR")


def init_db() -> None:
    Base.metadata.create_all(engine)
    _run_player_migrations()
    _run_saved_deck_migrations()
    _run_card_catalog_migrations()


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
