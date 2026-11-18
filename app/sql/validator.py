from dataclasses import dataclass
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

FORBIDDEN_FUNCTIONS = {
    "pg_read_file", "pg_read_binary_file", "pg_ls_dir", "pg_sleep",
    "pg_terminate_backend", "pg_cancel_backend", "lo_import", "lo_export",
    "dblink", "dblink_exec", "set_config", "pg_advisory_lock",
}

@dataclass
class ValidationResult:
    valid: bool
    sql: str | None = None
    error: str | None = None

def _allowed_table_names(schema_metadata: dict) -> set[str]:
    return {t["name"].lower() for t in schema_metadata.get("tables", [])}

def validate_and_normalize_sql(sql: str, schema_metadata: dict,
                               schema_name: str, max_rows: int) -> ValidationResult:
    if not sql or not sql.strip():
        return ValidationResult(False, error="The model returned an empty SQL query.")

    try:
        parsed = sqlglot.parse(sql, read="postgres")
    except ParseError as exc:
        return ValidationResult(False, error=f"SQL parse error: {str(exc)[:300]}")

    # Reject multiple statements, including trailing second statements.
    statements = [s for s in parsed if s is not None]
    if len(statements) != 1:
        return ValidationResult(False, error="Only one SQL statement is allowed.")

    tree = statements[0]
    # Allow SELECT, UNION/INTERSECT/EXCEPT (all SELECT-based); reject all DML/DDL.
    if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        return ValidationResult(False, error="Only SELECT queries are permitted.")

    # Reject SELECT INTO and locking reads.
    if tree.find(exp.Into) is not None:
        return ValidationResult(False, error="SELECT INTO is not permitted.")
    if tree.find(exp.Lock) is not None:
        return ValidationResult(False, error="Locking clauses are not permitted.")

    for func in tree.find_all(exp.Func):
        func_name = (getattr(func, "name", "") or func.sql_name()).lower()
        if func_name in FORBIDDEN_FUNCTIONS:
            return ValidationResult(False, error=f"Function {func_name} is not permitted.")

    allowed = _allowed_table_names(schema_metadata)
    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        table_name = (table.name or "").lower()
        table_schema = (table.db or schema_name).lower()
        if table_name in cte_names:
            continue
        if table_schema != schema_name.lower():
            return ValidationResult(False, error=f"Access to schema '{table_schema}' is not permitted.")
        if table_name not in allowed:
            return ValidationResult(False, error=f"Table '{table_name}' is not in the approved schema allowlist.")

    # Enforce a root-level cap, including UNION/INTERSECT/EXCEPT queries.
    limit_node = tree.args.get("limit")
    if limit_node is None:
        tree = tree.limit(max_rows)
    else:
        try:
            requested = int(limit_node.expression.this)
        except Exception:
            return ValidationResult(False, error="LIMIT must be a positive integer literal.")
        if requested <= 0:
            return ValidationResult(False, error="LIMIT must be greater than zero.")
        if requested > max_rows:
            tree = tree.limit(max_rows)

    normalized = tree.sql(dialect="postgres")
    return ValidationResult(True, sql=normalized)
