-- Run as a database administrator in Neon SQL Editor.
-- Replace role name and password. Use a newly rotated password.
CREATE ROLE nl2sql_reader LOGIN PASSWORD 'REPLACE_WITH_A_NEW_STRONG_PASSWORD';

GRANT CONNECT ON DATABASE neondb TO nl2sql_reader;
GRANT USAGE ON SCHEMA public TO nl2sql_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO nl2sql_reader;

-- Ensure future tables in public are readable by this role.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON TABLES TO nl2sql_reader;

-- Set conservative server-side defaults.
ALTER ROLE nl2sql_reader SET default_transaction_read_only = on;
ALTER ROLE nl2sql_reader SET statement_timeout = '10s';

-- Optional: prevent temp objects if not required.
-- REVOKE TEMPORARY ON DATABASE neondb FROM nl2sql_reader;
