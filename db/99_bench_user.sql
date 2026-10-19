-- Read-only role used by WrenAI, DB-GPT and the harness (runs after chinook.sql)
\c chinook;
CREATE ROLE bench LOGIN PASSWORD 'bench';
GRANT CONNECT ON DATABASE chinook TO bench;
GRANT USAGE ON SCHEMA public TO bench;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO bench;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO bench;
ALTER ROLE bench SET statement_timeout = '30s';
