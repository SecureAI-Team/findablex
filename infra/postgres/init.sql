-- Initial PostgreSQL setup
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS app;

-- Grant privileges
GRANT ALL PRIVILEGES ON SCHEMA app TO findablex;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA app TO findablex;

-- Set default search path
ALTER DATABASE findablex SET search_path TO app, public;
