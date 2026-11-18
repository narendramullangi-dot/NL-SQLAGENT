from app.sql.validator import validate_and_normalize_sql

SCHEMA = {
    "schema": "public",
    "tables": [
        {"name": "employees", "columns": [], "primary_key": ["employee_id"], "foreign_keys": []},
        {"name": "claims", "columns": [], "primary_key": ["claim_id"], "foreign_keys": []},
    ],
}

def test_select_is_allowed_and_limited():
    result = validate_and_normalize_sql(
        "SELECT employee_id FROM public.employees",
        SCHEMA, "public", 100
    )
    assert result.valid
    assert "LIMIT 100" in result.sql.upper()

def test_delete_is_rejected():
    result = validate_and_normalize_sql(
        "DELETE FROM public.employees",
        SCHEMA, "public", 100
    )
    assert not result.valid

def test_unknown_table_is_rejected():
    result = validate_and_normalize_sql(
        "SELECT * FROM public.payroll",
        SCHEMA, "public", 100
    )
    assert not result.valid

def test_multiple_statements_are_rejected():
    result = validate_and_normalize_sql(
        "SELECT * FROM public.employees; DROP TABLE public.employees",
        SCHEMA, "public", 100
    )
    assert not result.valid
