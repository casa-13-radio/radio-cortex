-- Radio Cortex - PostgreSQL Initialization Script
-- This runs automatically when the container is first created

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set timezone
SET timezone = 'UTC';

-- Create database if not exists (handled by Docker, but included for reference)
-- This script runs after the database is created by Docker

COMMENT ON EXTENSION vector IS 'Vector similarity search for embeddings';
COMMENT ON EXTENSION pg_trgm IS 'Trigram matching for full-text search';