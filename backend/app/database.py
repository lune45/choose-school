from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_sqlite_migrations() -> None:
    # Lightweight migration to keep local SQLite schema compatible without Alembic.
    with engine.begin() as conn:
        cols = conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()
        names = {row[1] for row in cols}
        if "role" not in names:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN role VARCHAR(32) DEFAULT 'user'")
