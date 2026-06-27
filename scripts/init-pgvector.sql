-- Runs automatically on first init of the mem0-postgres container
-- (Postgres executes /docker-entrypoint-initdb.d/*.sql once, on an empty data dir).
-- Ensures the pgvector extension exists so the mem0 SDK can create vector columns.
CREATE EXTENSION IF NOT EXISTS vector;
