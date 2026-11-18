from app.database.connection import check_database_connection, engine
from app.database.schema_loader import load_schema, schema_to_prompt_context
from app.config import DB_SCHEMA

result = check_database_connection()
if not result["ok"]:
    print("Connection failed:", result["error"])
    raise SystemExit(1)

print("Connected to database:", result["database_name"])
print("Database role:", result["database_user"])
print("Current schema:", result["current_schema"])
schema = load_schema(engine, DB_SCHEMA)
print(f"\nTables found in {DB_SCHEMA}: {len(schema['tables'])}")
for table in schema["tables"]:
    print(f"- {table['name']} ({len(table['columns'])} columns)")
print("\nSchema context:\n")
print(schema_to_prompt_context(schema))
