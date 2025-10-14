-- ============================================================================
-- Migration: Add chat_sessions table and update conversation_memories
-- Purpose: Enable GPT-style multi-chat management
-- Date: 2025-10-14
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. Create chat_sessions table
-- ============================================================================

CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL DEFAULT '새 대화',
    last_message TEXT,
    message_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_updated ON chat_sessions(user_id, updated_at DESC);

-- Comment
COMMENT ON TABLE chat_sessions IS 'GPT-style chat sessions for multi-conversation management';
COMMENT ON COLUMN chat_sessions.session_id IS 'Unique session identifier (UUID format)';
COMMENT ON COLUMN chat_sessions.user_id IS 'User who owns this chat session';
COMMENT ON COLUMN chat_sessions.title IS 'Chat title (auto-generated from first message)';
COMMENT ON COLUMN chat_sessions.last_message IS 'Preview of last message';
COMMENT ON COLUMN chat_sessions.message_count IS 'Total number of messages in this session';
COMMENT ON COLUMN chat_sessions.is_active IS 'Whether the session is still active';

-- ============================================================================
-- 2. Add session_id to conversation_memories
-- ============================================================================

-- Add column if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversation_memories'
        AND column_name = 'session_id'
    ) THEN
        ALTER TABLE conversation_memories
        ADD COLUMN session_id VARCHAR(100);
    END IF;
END $$;

-- Add foreign key constraint
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_conv_mem_session'
    ) THEN
        ALTER TABLE conversation_memories
        ADD CONSTRAINT fk_conv_mem_session
        FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE;
    END IF;
END $$;

-- Create index for session_id
CREATE INDEX IF NOT EXISTS idx_conv_mem_session_id ON conversation_memories(session_id);
CREATE INDEX IF NOT EXISTS idx_conv_mem_session_created ON conversation_memories(session_id, created_at DESC);

-- Comment
COMMENT ON COLUMN conversation_memories.session_id IS 'Reference to chat session (for GPT-style multi-chat)';

-- ============================================================================
-- 3. Create trigger to update chat_sessions.updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_chat_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_chat_session_timestamp ON chat_sessions;

CREATE TRIGGER trigger_update_chat_session_timestamp
    BEFORE UPDATE ON chat_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_chat_session_timestamp();

-- ============================================================================
-- 4. Create function to auto-update message_count
-- ============================================================================

CREATE OR REPLACE FUNCTION update_session_message_count()
RETURNS TRIGGER AS $$
BEGIN
    -- Increment message count when new memory is added
    IF TG_OP = 'INSERT' AND NEW.session_id IS NOT NULL THEN
        UPDATE chat_sessions
        SET
            message_count = message_count + 1,
            last_message = LEFT(NEW.query, 100),
            updated_at = NOW()
        WHERE session_id = NEW.session_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_session_message_count ON conversation_memories;

CREATE TRIGGER trigger_update_session_message_count
    AFTER INSERT ON conversation_memories
    FOR EACH ROW
    EXECUTE FUNCTION update_session_message_count();

-- ============================================================================
-- 5. Migrate existing conversation_memories (if any)
-- ============================================================================

-- Create a default session for existing memories without session_id
DO $$
DECLARE
    v_user_id INTEGER;
    v_default_session_id VARCHAR(100);
BEGIN
    -- For each user with memories but no session_id
    FOR v_user_id IN
        SELECT DISTINCT user_id
        FROM conversation_memories
        WHERE session_id IS NULL
    LOOP
        -- Create a default session
        v_default_session_id := 'session-migrated-' || v_user_id || '-' || EXTRACT(EPOCH FROM NOW())::BIGINT;

        INSERT INTO chat_sessions (session_id, user_id, title, created_at, updated_at)
        VALUES (
            v_default_session_id,
            v_user_id,
            '이전 대화 (마이그레이션)',
            (SELECT MIN(created_at) FROM conversation_memories WHERE user_id = v_user_id),
            NOW()
        )
        ON CONFLICT (session_id) DO NOTHING;

        -- Link existing memories to this session
        UPDATE conversation_memories
        SET session_id = v_default_session_id
        WHERE user_id = v_user_id AND session_id IS NULL;

        -- Update message count
        UPDATE chat_sessions
        SET message_count = (
            SELECT COUNT(*)
            FROM conversation_memories
            WHERE session_id = v_default_session_id
        )
        WHERE session_id = v_default_session_id;

        RAISE NOTICE 'Migrated memories for user % to session %', v_user_id, v_default_session_id;
    END LOOP;
END $$;

-- ============================================================================
-- 6. Verification queries
-- ============================================================================

-- Check chat_sessions table
SELECT
    COUNT(*) as total_sessions,
    COUNT(DISTINCT user_id) as total_users
FROM chat_sessions;

-- Check conversation_memories with session_id
SELECT
    COUNT(*) as total_memories,
    COUNT(DISTINCT session_id) as sessions_with_memories,
    COUNT(*) FILTER (WHERE session_id IS NULL) as memories_without_session
FROM conversation_memories;

-- Show sample sessions
SELECT
    session_id,
    user_id,
    title,
    message_count,
    created_at,
    updated_at
FROM chat_sessions
ORDER BY updated_at DESC
LIMIT 5;

COMMIT;

-- ============================================================================
-- SUCCESS!
-- ============================================================================
-- To verify the migration:
--   SELECT * FROM chat_sessions;
--   SELECT session_id, query FROM conversation_memories LIMIT 10;
-- ============================================================================
