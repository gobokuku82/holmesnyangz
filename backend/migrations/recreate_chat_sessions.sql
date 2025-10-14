-- ============================================================================
-- Migration: Recreate chat_sessions table (Clean Install)
-- Purpose: Drop and recreate chat_sessions with correct schema
-- Date: 2025-10-14
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. Drop existing chat_sessions table (if exists)
-- ============================================================================

-- Drop foreign key constraints first
DO $$
BEGIN
    -- Drop FK from conversation_memories if exists
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_conv_mem_session'
    ) THEN
        ALTER TABLE conversation_memories DROP CONSTRAINT fk_conv_mem_session;
        RAISE NOTICE 'Dropped FK constraint fk_conv_mem_session';
    END IF;
END $$;

-- Drop session_id column from conversation_memories
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversation_memories'
        AND column_name = 'session_id'
    ) THEN
        ALTER TABLE conversation_memories DROP COLUMN session_id;
        RAISE NOTICE 'Dropped session_id column from conversation_memories';
    END IF;
END $$;

-- Drop chat_sessions table
DROP TABLE IF EXISTS chat_sessions CASCADE;

-- ============================================================================
-- 2. Create chat_sessions table (NEW)
-- ============================================================================

CREATE TABLE chat_sessions (
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
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_updated_at ON chat_sessions(updated_at DESC);
CREATE INDEX idx_chat_sessions_user_updated ON chat_sessions(user_id, updated_at DESC);

-- Comments
COMMENT ON TABLE chat_sessions IS 'GPT-style chat sessions for multi-conversation management';
COMMENT ON COLUMN chat_sessions.session_id IS 'Unique session identifier (UUID format)';
COMMENT ON COLUMN chat_sessions.user_id IS 'User who owns this chat session';
COMMENT ON COLUMN chat_sessions.title IS 'Chat title (auto-generated from first message)';
COMMENT ON COLUMN chat_sessions.last_message IS 'Preview of last message';
COMMENT ON COLUMN chat_sessions.message_count IS 'Total number of messages in this session';

-- ============================================================================
-- 3. Add session_id to conversation_memories
-- ============================================================================

ALTER TABLE conversation_memories
ADD COLUMN session_id VARCHAR(100);

-- Add foreign key constraint
ALTER TABLE conversation_memories
ADD CONSTRAINT fk_conv_mem_session
FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE;

-- Create indexes
CREATE INDEX idx_conv_mem_session_id ON conversation_memories(session_id);
CREATE INDEX idx_conv_mem_session_created ON conversation_memories(session_id, created_at DESC);

COMMENT ON COLUMN conversation_memories.session_id IS 'Reference to chat session (for GPT-style multi-chat)';

-- ============================================================================
-- 4. Create triggers for auto-update
-- ============================================================================

-- Trigger to update chat_sessions.updated_at
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

-- Trigger to auto-update message_count and last_message
CREATE OR REPLACE FUNCTION update_session_message_count()
RETURNS TRIGGER AS $$
BEGIN
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
-- 5. Migrate existing conversation_memories
-- ============================================================================

DO $$
DECLARE
    v_user_id INTEGER;
    v_default_session_id VARCHAR(100);
    v_migrated_count INTEGER := 0;
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
        );

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

        v_migrated_count := v_migrated_count + 1;
        RAISE NOTICE 'Migrated memories for user % to session %', v_user_id, v_default_session_id;
    END LOOP;

    RAISE NOTICE 'Migration completed: % users processed', v_migrated_count;
END $$;

-- ============================================================================
-- 6. Verification
-- ============================================================================

-- Show results
SELECT
    '✅ chat_sessions' as table_name,
    COUNT(*) as total_rows,
    COUNT(DISTINCT user_id) as unique_users
FROM chat_sessions
UNION ALL
SELECT
    '✅ conversation_memories with session',
    COUNT(*),
    COUNT(DISTINCT session_id)
FROM conversation_memories
WHERE session_id IS NOT NULL
UNION ALL
SELECT
    '⚠️ conversation_memories without session',
    COUNT(*),
    0
FROM conversation_memories
WHERE session_id IS NULL;

-- Show sample data
SELECT
    session_id,
    user_id,
    title,
    message_count,
    TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as created,
    TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI:SS') as updated
FROM chat_sessions
ORDER BY updated_at DESC
LIMIT 5;

COMMIT;

-- ============================================================================
-- SUCCESS!
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Migration completed successfully!';
    RAISE NOTICE '   - chat_sessions table created';
    RAISE NOTICE '   - conversation_memories.session_id added';
    RAISE NOTICE '   - Foreign key constraints established';
    RAISE NOTICE '   - Triggers configured';
    RAISE NOTICE '   - Existing data migrated';
END $$;
