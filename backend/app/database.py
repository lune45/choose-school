import json
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
        if "concerns_json" not in analysis_names:
            conn.exec_driver_sql("ALTER TABLE analysis_records ADD COLUMN concerns_json JSON DEFAULT '[]'")
        if "weights_json" not in analysis_names:
            conn.exec_driver_sql("ALTER TABLE analysis_records ADD COLUMN weights_json JSON DEFAULT '{}'")

        conn.exec_driver_sql(
            """
            UPDATE analysis_records
            SET concerns_json = CASE
                WHEN concerns_json IS NULL OR TRIM(CAST(concerns_json AS TEXT)) = '' THEN selected_dimensions
                ELSE concerns_json
            END
            """
        )
        conn.exec_driver_sql(
            """
            UPDATE analysis_records
            SET weights_json = CASE
                WHEN weights_json IS NULL OR TRIM(CAST(weights_json AS TEXT)) = '' OR TRIM(CAST(weights_json AS TEXT)) = '{}'
                THEN weights
                ELSE weights_json
            END
            """
        )

        school_cols = conn.exec_driver_sql("PRAGMA table_info(school_programs)").fetchall()
        school_names = {row[1] for row in school_cols}
        if "qs_rank" not in school_names:
            conn.exec_driver_sql("ALTER TABLE school_programs ADD COLUMN qs_rank FLOAT DEFAULT 0")
        if "usnews_rank" not in school_names:
            conn.exec_driver_sql("ALTER TABLE school_programs ADD COLUMN usnews_rank FLOAT DEFAULT 0")
        if "times_rank" not in school_names:
            conn.exec_driver_sql("ALTER TABLE school_programs ADD COLUMN times_rank FLOAT DEFAULT 0")
        if "program_duration_months" not in school_names:
            conn.exec_driver_sql("ALTER TABLE school_programs ADD COLUMN program_duration_months FLOAT DEFAULT 0")
        if "course_list_json" not in school_names:
            conn.exec_driver_sql("ALTER TABLE school_programs ADD COLUMN course_list_json JSON DEFAULT '[]'")
        if "query_output_json" not in school_names:
            conn.exec_driver_sql("ALTER TABLE school_programs ADD COLUMN query_output_json JSON DEFAULT '{}'")

        # Backfill ranking columns from legacy ranking_score when empty.
        conn.exec_driver_sql(
            """
            UPDATE school_programs
            SET qs_rank = CASE
                WHEN IFNULL(qs_rank, 0) > 0 THEN qs_rank
                WHEN IFNULL(ranking_score, 0) > 0 THEN MAX(1, ROUND(101 - ranking_score, 1))
                ELSE 0 END
            """
        )
        conn.exec_driver_sql(
            """
            UPDATE school_programs
            SET usnews_rank = CASE
                WHEN IFNULL(usnews_rank, 0) > 0 THEN usnews_rank
                WHEN IFNULL(qs_rank, 0) > 0 THEN qs_rank
                ELSE 0 END
            """
        )
        conn.exec_driver_sql(
            """
            UPDATE school_programs
            SET times_rank = CASE
                WHEN IFNULL(times_rank, 0) > 0 THEN times_rank
                WHEN IFNULL(qs_rank, 0) > 0 THEN qs_rank
                ELSE 0 END
            """
        )

        # Backfill v2 query_output_json for all programs.
        try:
            from .services.query_schema import compose_query_output

            rows = conn.exec_driver_sql(
                """
                SELECT id, country, school_name, program_name, major_track, degree,
                       qs_rank, usnews_rank, times_rank, program_duration_months, course_list_json,
                       tuition_usd, living_cost_usd, ranking_score, median_salary_usd,
                       safety_score, course_difficulty, employment_support, visa_support,
                       alumni_network, immigration_friendly, domestic_recognition, notes, query_output_json
                FROM school_programs
                """
            ).fetchall()

            for row in rows:
                row_map = dict(row._mapping)
                raw_query = row_map.get("query_output_json")
                if isinstance(raw_query, str):
                    try:
                        raw_query = json.loads(raw_query)
                    except Exception:
                        raw_query = {}
                if not isinstance(raw_query, dict):
                    raw_query = {}

                program_data = {k: v for k, v in row_map.items() if k not in {"id", "query_output_json"}}
                merged = compose_query_output(program_data, raw_query)
                conn.exec_driver_sql(
                    "UPDATE school_programs SET query_output_json = ? WHERE id = ?",
                    (json.dumps(merged, ensure_ascii=False), row_map["id"]),
                )
        except Exception:
            # Keep startup resilient even if backfill fails unexpectedly.
            pass
