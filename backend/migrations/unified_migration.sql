-- ============================================================================
-- Unified Migration Script for HolmesNyangz
-- ============================================================================
-- Purpose: Complete database setup for GPT-style multi-chat system
-- Date: 2025-10-14
-- Author: Claude Code
--
-- This script:
-- 1. Drops existing tables (cascade)
-- 2. Creates all required tables (9 tables)
-- 3. Creates triggers and functions
-- 4. Creates indexes
-- 5. Verifies the setup
--
-- Tables created:
-- - chat_messages
-- - chat_sessions
-- - checkpoints
-- - checkpoint_blobs
-- - checkpoint_migrations
-- - checkpoint_writes
-- - conversation_memories
-- - entity_memories
-- - sessions
--
-- Usage:
--   PGPASSWORD=root1234 psql -h localhost -U postgres -d real_estate -f unified_migration.sql
-- ============================================================================

\echo '=========================================='
\echo 'Starting Unified Migration...'
\echo '=========================================='
\echo ''

-- ============================================================================
-- STEP 1: Drop existing tables (CASCADE)
-- ============================================================================

\echo 'STEP 1: Dropping existing tables...'
\echo ''

-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS checkpoint_writes CASCADE;
DROP TABLE IF EXISTS checkpoint_blobs CASCADE;
DROP TABLE IF EXISTS checkpoint_migrations CASCADE;
DROP TABLE IF EXISTS checkpoints CASCADE;
DROP TABLE IF EXISTS chat_messages CASCADE;
DROP TABLE IF EXISTS conversation_memories CASCADE;
DROP TABLE IF EXISTS entity_memories CASCADE;
DROP TABLE IF EXISTS chat_sessions CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;

\echo 'All tables dropped successfully.'
\echo ''

-- ============================================================================
-- STEP 2: Create core tables
-- ============================================================================

\echo 'STEP 2: Creating core tables...'
\echo ''

-- ============================================================================
-- 2-1. sessions 테이블 (HTTP/WebSocket 세션 관리)
-- ============================================================================

\echo '  [2-1] Creating sessions table...'

CREATE TABLE sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    metadata JSONB
);

CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);

\echo '  ✓ sessions table created'

-- ============================================================================
-- 2-2. chat_sessions 테이블 (GPT-style 채팅 세션)
-- ============================================================================

\echo '  [2-2] Creating chat_sessions table...'

CREATE TABLE chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL DEFAULT '새 대화',
    last_message TEXT,
    message_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB
);

CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_updated_at ON chat_sessions(updated_at DESC);
CREATE INDEX idx_chat_sessions_user_updated ON chat_sessions(user_id, updated_at DESC);
CREATE INDEX idx_chat_sessions_is_active ON chat_sessions(is_active);

\echo '  ✓ chat_sessions table created'

-- ============================================================================
-- 2-3. chat_messages 테이블 (선택적 메시지 저장)
-- ============================================================================

\echo '  [2-3] Creating chat_messages table...'

CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    metadata JSONB
);

CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_session_created ON chat_messages(session_id, created_at DESC);

\echo '  ✓ chat_messages table created'

-- ============================================================================
-- 2-4. conversation_memories 테이블 (Long-term Memory)
-- ============================================================================

\echo '  [2-4] Creating conversation_memories table...'

CREATE TABLE conversation_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL,
    query TEXT NOT NULL,
    response_summary TEXT NOT NULL,
    relevance VARCHAR(20) NOT NULL CHECK (relevance IN ('RELEVANT', 'IRRELEVANT', 'UNCLEAR')),
    session_id VARCHAR(100),
    intent_detected VARCHAR(100),
    entities_mentioned JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    conversation_metadata JSONB
);

-- Foreign Key (nullable for backward compatibility)
ALTER TABLE conversation_memories
ADD CONSTRAINT fk_conv_mem_session
FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE;

CREATE INDEX idx_conv_mem_user_id ON conversation_memories(user_id);
CREATE INDEX idx_conv_mem_created_at ON conversation_memories(created_at DESC);
CREATE INDEX idx_conv_mem_relevance ON conversation_memories(relevance);
CREATE INDEX idx_conv_mem_session_id ON conversation_memories(session_id);
CREATE INDEX idx_conv_mem_session_created ON conversation_memories(session_id, created_at DESC);

\echo '  ✓ conversation_memories table created'

-- ============================================================================
-- 2-5. entity_memories 테이블 (Entity 추적)
-- ============================================================================

\echo '  [2-5] Creating entity_memories table...'

CREATE TABLE entity_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_name VARCHAR(200) NOT NULL,
    entity_value TEXT,
    context TEXT,
    first_mentioned TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    last_mentioned TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    mention_count INTEGER DEFAULT 1,
    importance_score FLOAT DEFAULT 0.5,
    metadata JSONB
);

CREATE INDEX idx_entity_mem_user_id ON entity_memories(user_id);
CREATE INDEX idx_entity_mem_type ON entity_memories(entity_type);
CREATE INDEX idx_entity_mem_name ON entity_memories(entity_name);
CREATE INDEX idx_entity_mem_last_mentioned ON entity_memories(last_mentioned DESC);

\echo '  ✓ entity_memories table created'

-- ============================================================================
-- STEP 3: Create LangGraph checkpoint tables
-- ============================================================================

\echo ''
\echo 'STEP 3: Creating LangGraph checkpoint tables...'
\echo ''

-- ============================================================================
-- 3-1. checkpoints 테이블
-- ============================================================================

\echo '  [3-1] Creating checkpoints table...'

CREATE TABLE checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE INDEX idx_checkpoints_thread_id ON checkpoints(thread_id);

\echo '  ✓ checkpoints table created'

-- ============================================================================
-- 3-2. checkpoint_blobs 테이블
-- ============================================================================

\echo '  [3-2] Creating checkpoint_blobs table...'

CREATE TABLE checkpoint_blobs (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL,
    version TEXT NOT NULL,
    type TEXT NOT NULL,
    blob BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);

\echo '  ✓ checkpoint_blobs table created'

-- ============================================================================
-- 3-3. checkpoint_writes 테이블
-- ============================================================================

\echo '  [3-3] Creating checkpoint_writes table...'

CREATE TABLE checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    blob BYTEA NOT NULL,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

CREATE INDEX idx_checkpoint_writes_thread_id ON checkpoint_writes(thread_id);

\echo '  ✓ checkpoint_writes table created'

-- ============================================================================
-- 3-4. checkpoint_migrations 테이블
-- ============================================================================

\echo '  [3-4] Creating checkpoint_migrations table...'

CREATE TABLE checkpoint_migrations (
    v INTEGER PRIMARY KEY
);

\echo '  ✓ checkpoint_migrations table created'

-- ============================================================================
-- STEP 4: Create triggers and functions
-- ============================================================================

\echo ''
\echo 'STEP 4: Creating triggers and functions...'
\echo ''

-- ============================================================================
-- 4-1. updated_at 자동 갱신 트리거
-- ============================================================================

\echo '  [4-1] Creating update_chat_session_timestamp trigger...'

CREATE OR REPLACE FUNCTION update_chat_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_chat_session_timestamp
    BEFORE UPDATE ON chat_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_chat_session_timestamp();

\echo '  ✓ update_chat_session_timestamp trigger created'

-- ============================================================================
-- 4-2. message_count, last_message 자동 갱신 트리거
-- ============================================================================

\echo '  [4-2] Creating update_session_message_count trigger...'

CREATE OR REPLACE FUNCTION update_session_message_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.session_id IS NOT NULL THEN
        -- chat_sessions 테이블 업데이트
        UPDATE chat_sessions
        SET
            message_count = message_count + 1,
            last_message = LEFT(NEW.query, 100),
            updated_at = NOW()
        WHERE session_id = NEW.session_id;

        -- 제목이 "새 대화"인 경우 첫 질문으로 자동 변경
        UPDATE chat_sessions
        SET title = LEFT(NEW.query, 30) || CASE WHEN LENGTH(NEW.query) > 30 THEN '...' ELSE '' END
        WHERE session_id = NEW.session_id AND title = '새 대화';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_session_message_count
    AFTER INSERT ON conversation_memories
    FOR EACH ROW
    EXECUTE FUNCTION update_session_message_count();

\echo '  ✓ update_session_message_count trigger created'

-- ============================================================================
-- STEP 5: Verification
-- ============================================================================

\echo ''
\echo 'STEP 5: Verifying migration...'
\echo ''

-- List all tables
\echo '=========================================='
\echo 'All Tables:'
\echo '=========================================='

SELECT
    schemaname,
    tablename,
    tableowner
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

\echo ''
\echo '=========================================='
\echo 'Table Row Counts:'
\echo '=========================================='

SELECT
    'chat_sessions' AS table_name,
    COUNT(*) AS row_count
FROM chat_sessions
UNION ALL
SELECT
    'chat_messages' AS table_name,
    COUNT(*) AS row_count
FROM chat_messages
UNION ALL
SELECT
    'conversation_memories' AS table_name,
    COUNT(*) AS row_count
FROM conversation_memories
UNION ALL
SELECT
    'entity_memories' AS table_name,
    COUNT(*) AS row_count
FROM entity_memories
UNION ALL
SELECT
    'sessions' AS table_name,
    COUNT(*) AS row_count
FROM sessions
UNION ALL
SELECT
    'checkpoints' AS table_name,
    COUNT(*) AS row_count
FROM checkpoints
UNION ALL
SELECT
    'checkpoint_blobs' AS table_name,
    COUNT(*) AS row_count
FROM checkpoint_blobs
UNION ALL
SELECT
    'checkpoint_writes' AS table_name,
    COUNT(*) AS row_count
FROM checkpoint_writes
UNION ALL
SELECT
    'checkpoint_migrations' AS table_name,
    COUNT(*) AS row_count
FROM checkpoint_migrations
ORDER BY table_name;

\echo ''
\echo '=========================================='
\echo 'Triggers:'
\echo '=========================================='

SELECT
    trigger_name,
    event_object_table,
    action_timing,
    event_manipulation
FROM information_schema.triggers
WHERE trigger_schema = 'public'
ORDER BY event_object_table, trigger_name;

\echo ''
\echo '=========================================='
\echo 'Foreign Keys:'
\echo '=========================================='

SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema = 'public'
ORDER BY tc.table_name, kcu.column_name;

\echo ''
\echo '=========================================='
\echo '✅ Migration Complete!'
\echo '=========================================='
\echo ''
\echo 'Summary:'
\echo '  - 9 tables created'
\echo '  - 2 triggers created'
\echo '  - 2 functions created'
\echo '  - Multiple indexes created'
\echo '  - Foreign keys established'
\echo ''
\echo 'Next steps:'
\echo '  1. Verify table structures: \\d+ chat_sessions'
\echo '  2. Check triggers: \\dft'
\echo '  3. Test insert: INSERT INTO chat_sessions ...'
\echo ''
