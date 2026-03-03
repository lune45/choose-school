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

        analysis_cols = conn.exec_driver_sql("PRAGMA table_info(analysis_records)").fetchall()
        analysis_names = {row[1] for row in analysis_cols}
        if "status" not in analysis_names:
            conn.exec_driver_sql("ALTER TABLE analysis_records ADD COLUMN status VARCHAR(32) DEFAULT 'completed'")
        if "error_message" not in analysis_names:
            conn.exec_driver_sql("ALTER TABLE analysis_records ADD COLUMN error_message TEXT DEFAULT ''")
        if "result_json" not in analysis_names:
            conn.exec_driver_sql("ALTER TABLE analysis_records ADD COLUMN result_json JSON")
        if "raw_ai_response" not in analysis_names:
            conn.exec_driver_sql("ALTER TABLE analysis_records ADD COLUMN raw_ai_response TEXT DEFAULT ''")
