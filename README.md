# Production NL2SQL Agent

Stack: Python, Streamlit, LangGraph, Gemini API (`google-genai`), SQLGlot,
SQLAlchemy 2.x, Psycopg 3, PostgreSQL / Neon.

## Features
- Dynamic PostgreSQL schema discovery (tables, columns, PKs, FKs).
- Gemini natural-language-to-PostgreSQL SQL generation.
- LangGraph workflow with validation and bounded correction retries.
- SQLGlot AST checks: SELECT-only, one statement, approved schema/table allowlist,
  blocked risky functions, no SELECT INTO / row locking.
- Read-only PostgreSQL transaction, statement timeout and result row cap.
- Streamlit results, generated SQL, CSV export and local query history.
- Unit tests for basic SQL validation.

## Security first
The Neon owner URL/password was pasted into a chat. Treat it as exposed and rotate
that password before using this application. Create a dedicated restricted role.
Never put secrets in Python source, Git, screenshots, or logs.

Run `scripts/create_readonly_role.sql` in Neon SQL Editor as an administrator
after replacing the placeholder password. Check the role has access only to the
approved schema and tables. The script grants SELECT on all tables in `public`;
narrow those grants if any table/column is sensitive. PostgreSQL column-level
grants or curated views are recommended for sensitive data.

## Setup (Windows PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` with the NEW restricted role connection string and Gemini API key.
Keep Neon TLS parameters such as `sslmode=require` and `channel_binding=require`.
URL-encode special characters in the username/password.

Test:
```powershell
python -m scripts.check_db
```

Run:
```powershell
streamlit run streamlit_app.py
```

Tests:
```powershell
pytest -q
```

Docker:
```bash
docker build -t nl2sql-agent .
docker run --env-file .env -p 8501:8501 nl2sql-agent
```

## Expected database tables
The example business data shared for this project describes three logical entities:
- employees
- claims
- claim_items

The application does NOT create or assume these tables. It discovers the actual
tables in `DB_SCHEMA`. Create/import the tables into Neon first if they are not
already there. Confirm their real names, keys and columns in the Streamlit schema
discovery output.

Business semantics in the Gemini prompt:
- Claim-level totals are sourced from claims.total_amount.
- Expense-category/vendor/policy analysis is sourced from claim_items.amount.
- Joining claims to multiple claim_items can multiply claim rows; aggregate at
  the correct grain to avoid double counting.
- Employee references may not all have matching employee rows.

## Architecture
Question -> schema discovery -> Gemini generation -> SQLGlot validation ->
read-only PostgreSQL execution -> Streamlit results.

## Production hardening still required before exposing publicly
This is a production-oriented starter, not a security certification. Before
internet-facing deployment add:
- Authentication and per-user authorization.
- Row-level security / tenant isolation if applicable.
- Column masking and curated views for PII or confidential fields.
- Rate limiting and abuse controls.
- Centralized secrets management and secret rotation.
- Persistent audit logs with retention controls.
- Evaluation dataset and regression tests against expected SQL/results.
- Human approval for any future write capability (currently writes are blocked).
- Network restrictions, TLS, monitoring, backups and deployment health checks.

SQL parsing is defense-in-depth, not a substitute for PostgreSQL permissions.
