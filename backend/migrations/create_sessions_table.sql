-- Migration: Create sessions table for SessionManager
-- Date: 2025-10-14
-- Description: Migrate SessionManager from SQLite to PostgreSQL

-- Create sessions table
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INTEGER,
    metadata TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    request_count INTEGER NOT NULL DEFAULT 0
);

-- Create index on expires_at for efficient cleanup
CREATE INDEX IF NOT EXISTS idx_expires_at ON sessions(expires_at);

-- Create index on session_id (already primary key, but explicit for documentation)
CREATE INDEX IF NOT EXISTS idx_session_id ON sessions(session_id);
