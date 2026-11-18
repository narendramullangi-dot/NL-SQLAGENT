from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.config import DB_MAX_ROWS, DB_STATEMENT_TIMEOUT_MS
from app.database.connection import engine

def execute_read_only(sql: str) -> dict:
    """
    Execute one validated query inside a read-only transaction.
    A restricted PostgreSQL role is still mandatory; application checks are defense-in-depth.
    """
    try:
        with engine.connect() as conn:
            with conn.begin():
                conn.exec_driver_sql("SET TRANSACTION READ ONLY")
                conn.execute(
                    text("SELECT set_config('statement_timeout', :timeout, true)"),
                    {"timeout": f"{DB_STATEMENT_TIMEOUT_MS}ms"},
                )
                result = conn.execute(text(sql))
                columns = list(result.keys())
                rows = result.fetchmany(DB_MAX_ROWS + 1)
                truncated = len(rows) > DB_MAX_ROWS
                rows = rows[:DB_MAX_ROWS]
                data = [dict(row._mapping) for row in rows]
                # Convert common non-JSON-native database values.
                for row in data:
                    for key, value in list(row.items()):
                        if hasattr(value, "isoformat"):
                            row[key] = value.isoformat()
                        elif isinstance(value, (bytes, bytearray, memoryview)):
                            row[key] = f"<binary data: {len(value)} bytes>"
                return {
                    "ok": True,
                    "columns": columns,
                    "data": data,
                    "row_count": len(data),
                    "truncated": truncated,
                }
    except SQLAlchemyError as exc:
        cause = exc.__cause__ or exc
        return {"ok": False, "error": str(cause).splitlines()[0][:500]}
