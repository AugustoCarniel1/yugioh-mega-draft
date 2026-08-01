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


def init_db() -> None:
    Base.metadata.create_all(engine)
    _run_player_migrations()


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
