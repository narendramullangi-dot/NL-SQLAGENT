from sqlalchemy import inspect
from sqlalchemy.engine import Engine

def load_schema(engine: Engine, schema_name: str = "public") -> dict:
    """Read metadata only: tables, columns, primary keys and foreign keys."""
    inspector = inspect(engine)
    tables = []
    for table_name in sorted(inspector.get_table_names(schema=schema_name)):
        cols = inspector.get_columns(table_name, schema=schema_name)
        pk = inspector.get_pk_constraint(table_name, schema=schema_name) or {}
        fks = inspector.get_foreign_keys(table_name, schema=schema_name) or []
        tables.append({
            "name": table_name,
            "columns": [
                {
                    "name": c["name"],
                    "type": str(c["type"]),
                    "nullable": bool(c.get("nullable", True)),
                } for c in cols
            ],
            "primary_key": pk.get("constrained_columns", []) or [],
            "foreign_keys": [
                {
                    "columns": fk.get("constrained_columns", []) or [],
                    "referred_schema": fk.get("referred_schema") or schema_name,
                    "referred_table": fk.get("referred_table"),
                    "referred_columns": fk.get("referred_columns", []) or [],
                } for fk in fks
            ],
        })
    return {"schema": schema_name, "tables": tables}

def schema_to_prompt_context(schema: dict) -> str:
    lines = [f"PostgreSQL schema: {schema['schema']}"]
    if not schema["tables"]:
        lines.append("No tables were found.")
    for table in schema["tables"]:
        lines.append(f"\nTABLE {schema['schema']}.{table['name']}")
        for col in table["columns"]:
            nullability = "NULL" if col["nullable"] else "NOT NULL"
            lines.append(f"  - {col['name']} {col['type']} {nullability}")
        lines.append("  PRIMARY KEY: " + (", ".join(table["primary_key"]) or "none"))
        for fk in table["foreign_keys"]:
            lines.append(
                f"  FOREIGN KEY ({', '.join(fk['columns'])}) REFERENCES "
                f"{fk['referred_schema']}.{fk['referred_table']} "
                f"({', '.join(fk['referred_columns'])})"
            )
    return "\n".join(lines)
