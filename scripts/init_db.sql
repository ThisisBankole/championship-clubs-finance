-- National League Financial Intelligence Platform
-- Database initialization script

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create database user (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nlf_user') THEN
        CREATE ROLE nlf_user WITH LOGIN PASSWORD 'nlf_password';
    END IF;
END
$$;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE national_league_finance TO nlf_user;
GRANT ALL ON SCHEMA public TO nlf_user;

-- Create initial tables will be handled by Alembic migrations
-- This script just ensures the database is ready

-- Log initialization
INSERT INTO information_schema.sql_features (feature_id, feature_name) 
VALUES ('NLF_INIT', 'National League Finance Database Initialized') 
ON CONFLICT DO NOTHING;
