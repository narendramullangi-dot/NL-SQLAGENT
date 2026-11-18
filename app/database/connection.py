
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.config import DATABASE_URL, DB_CONNECT_TIMEOUT


def build_engine() -> Engine:
    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
        pool_recycle=300,
        connect_args={
            "connect_timeout": DB_CONNECT_TIMEOUT,
            "application_name": "nl2sql_streamlit_agent",
        },
    )


engine = build_engine()


def check_database_connection() -> dict:
    try:
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT current_database() AS database_name,
                       current_user AS database_user,
                       current_schema() AS current_schema,
                       version() AS postgres_version
            """)).mappings().one()

        return {"ok": True, **dict(row)}

    except SQLAlchemyError as exc:
        cause = exc.__cause__ or exc
        return {
            "ok": False,
            "error": str(cause).splitlines()[0]
        }


def close_engine():
    engine.dispose()
