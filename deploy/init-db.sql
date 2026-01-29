-- FindableX Database Initialization Script
-- This runs automatically when PostgreSQL container starts for the first time

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create indexes for better performance (optional, tables created by SQLAlchemy)
-- These will be created if tables already exist

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE findablex TO findablex;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'FindableX database initialized successfully at %', NOW();
END $$;
