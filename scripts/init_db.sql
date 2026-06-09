-- PostgreSQL initialization script
-- Runs once when the container is first created.
-- The database and user are already created by POSTGRES_DB / POSTGRES_USER env vars.

-- Extensions (useful for UUID generation, full-text search)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- for LIKE index acceleration

-- Grant privileges (already done via env, but explicit is safer)
GRANT ALL PRIVILEGES ON DATABASE inspectai TO inspectai;
