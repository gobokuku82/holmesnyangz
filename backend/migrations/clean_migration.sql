-- ============================================================================
-- Clean Migration Script for HolmesNyangz
-- ============================================================================
-- Purpose: Drop old chat/memory/checkpoint tables and create new simplified schema
-- Date: 2025-10-15
-- Author: Claude Code
--
-- What this does:
-- 1. DROP old tables (chat, memory, checkpoint related ONLY)
-- 2. CREATE new simplified tables (6 tables)
-- 3. Unified naming: ALL tables use "session_id" (not "thread_id")
--
-- Tables to DROP (9 tables):
--   - sessions (HTTP/WebSocket) - no longer needed
--   - conversation_memories - replaced by chat_messages
--   - entity_memories - not needed for core functionality
--   - user_preferences - not needed (was for memory service)
--   - chat_sessions (old version)
--   - chat_messages (old version)
--   - checkpoints (old version with thread_id)
--   - checkpoint_blobs (old version with thread_id)
--   - checkpoint_writes (old version with thread_id)
--   - checkpoint_migrations (old version)
--
-- Tables to CREATE (6 tables):
--   Core (2):
--     - chat_sessions (new)
--     - chat_messages (new)
--   Checkpoint (4):
--     - checkpoints (session_id, NOT thread_id!)
--     - checkpoint_blobs (session_id, NOT thread_id!)
--     - checkpoint_writes (session_id, NOT thread_id!)
--     - checkpoint_migrations
--
-- ⚠️  WARNING: This will DELETE all chat history and checkpoints!
--
-- Usage:
--   PGPASSWORD=root1234 psql -h localhost -U postgres -d real_estate -f clean_migration.sql
-- ============================================================================

\echo ''
\echo '=========================================='
\echo 'Clean Migration Started'
\echo '=========================================='
\echo ''
\echo '⚠️  WARNING: This will delete all chat/memory/checkpoint data!'
\echo 'Press Ctrl+C within 3 seconds to cancel...'
\echo ''

-- Give user 3 seconds to cancel (just a warning, no actual sleep in SQL)

-- ============================================================================
-- STEP 1: Drop OLD chat/memory/checkpoint tables
-- ============================================================================

\echo ''
\echo '=========================================='
\echo 'STEP 1: Dropping old tables...'
\echo '=========================================='
\echo ''

-- Drop checkpoint tables (old version with thread_id)
\echo '[1/10] Dropping checkpoint_writes...'
DROP TABLE IF EXISTS checkpoint_writes CASCADE;

\echo '[2/10] Dropping checkpoint_blobs...'
DROP TABLE IF EXISTS checkpoint_blobs CASCADE;

\echo '[3/10] Dropping checkpoint_migrations...'
DROP TABLE IF EXISTS checkpoint_migrations CASCADE;

\echo '[4/10] Dropping checkpoints...'
DROP TABLE IF EXISTS checkpoints CASCADE;

-- Drop memory/session tables
\echo '[5/10] Dropping conversation_memories...'
DROP TABLE IF EXISTS conversation_memories CASCADE;

\echo '[6/10] Dropping entity_memories...'
DROP TABLE IF EXISTS entity_memories CASCADE;

\echo '[7/10] Dropping user_preferences...'
DROP TABLE IF EXISTS user_preferences CASCADE;

\echo '[8/10] Dropping sessions (HTTP/WebSocket)...'
DROP TABLE IF EXISTS sessions CASCADE;

-- Drop chat tables (will recreate)
\echo '[9/10] Dropping chat_messages...'
DROP TABLE IF EXISTS chat_messages CASCADE;

\echo '[10/10] Dropping chat_sessions...'
DROP TABLE IF EXISTS chat_sessions CASCADE;

\echo ''
\echo '✅ All old tables dropped successfully'
\echo ''

-- ============================================================================
-- STEP 2: Create NEW core tables (2 tables)
-- ============================================================================

\echo '=========================================='
\echo 'STEP 2: Creating new core tables...'
\echo '=========================================='
\echo ''

-- ----------------------------------------------------------------------------
-- 2-1. chat_sessions 테이블
-- ----------------------------------------------------------------------------

\echo '[1/2] Creating chat_sessions table...'

CREATE TABLE chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,  -- 임시 하드코딩 (인증 미구현)
    title VARCHAR(200) NOT NULL DEFAULT '새 대화',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    last_message TEXT,  -- 마지막 메시지 미리보기 (세션 목록 UI용)
    message_count INTEGER DEFAULT 0,  -- 세션 내 메시지 개수
    is_active BOOLEAN DEFAULT true,  -- 세션 활성 상태
    metadata JSONB  -- 추가 메타데이터 (향후 확장용)
);

-- Indexes
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_updated_at ON chat_sessions(updated_at DESC);
CREATE INDEX idx_chat_sessions_user_updated ON chat_sessions(user_id, updated_at DESC);

-- Comments
COMMENT ON TABLE chat_sessions IS 'Chat sessions (conversation threads)';
COMMENT ON COLUMN chat_sessions.session_id IS 'Session ID (unified across all tables, including checkpoints)';
COMMENT ON COLUMN chat_sessions.user_id IS 'User ID (default: 1, authentication not implemented)';
COMMENT ON COLUMN chat_sessions.title IS 'Session title (auto-generated from first message)';
COMMENT ON COLUMN chat_sessions.created_at IS 'Session created timestamp';
COMMENT ON COLUMN chat_sessions.updated_at IS 'Session last updated timestamp (auto-updated by trigger)';
COMMENT ON COLUMN chat_sessions.last_message IS 'Last message preview for session list UI';
COMMENT ON COLUMN chat_sessions.message_count IS 'Number of messages in this session';
COMMENT ON COLUMN chat_sessions.is_active IS 'Session active status (for archiving)';
COMMENT ON COLUMN chat_sessions.metadata IS 'Additional metadata (JSONB for future extension)';

\echo '  ✓ chat_sessions created'

-- ----------------------------------------------------------------------------
-- 2-2. chat_messages 테이블
-- ----------------------------------------------------------------------------

\echo '[2/2] Creating chat_messages table...'

CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Indexes
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_session_created ON chat_messages(session_id, created_at DESC);

-- Comments
COMMENT ON TABLE chat_messages IS 'Chat message history for UI display';
COMMENT ON COLUMN chat_messages.id IS 'Message unique ID (auto-increment)';
COMMENT ON COLUMN chat_messages.session_id IS 'References chat_sessions.session_id (CASCADE delete)';
COMMENT ON COLUMN chat_messages.role IS 'Message role: user, assistant, or system';
COMMENT ON COLUMN chat_messages.content IS 'Message content (full text)';
COMMENT ON COLUMN chat_messages.created_at IS 'Message created timestamp';

\echo '  ✓ chat_messages created'
\echo ''
\echo '✅ Core tables created successfully'
\echo ''

-- ============================================================================
-- STEP 3: Create NEW LangGraph checkpoint tables (4 tables)
-- ============================================================================

\echo '=========================================='
\echo 'STEP 3: Creating LangGraph checkpoint tables...'
\echo '=========================================='
\echo ''

-- ----------------------------------------------------------------------------
-- 3-1. checkpoints 테이블 (session_id 사용!)
-- ----------------------------------------------------------------------------

\echo '[1/4] Creating checkpoints table...'

CREATE TABLE checkpoints (
    session_id TEXT NOT NULL,  -- ✅ thread_id → session_id 변경!
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (session_id, checkpoint_ns, checkpoint_id)
);

-- Index
CREATE INDEX idx_checkpoints_session_id ON checkpoints(session_id);

-- Comments
COMMENT ON TABLE checkpoints IS 'LangGraph state snapshots for pause/resume';
COMMENT ON COLUMN checkpoints.session_id IS 'Session ID (same value as chat_sessions.session_id)';
COMMENT ON COLUMN checkpoints.checkpoint_ns IS 'Checkpoint namespace (default: empty string)';
COMMENT ON COLUMN checkpoints.checkpoint_id IS 'Checkpoint unique ID (LangGraph generated)';
COMMENT ON COLUMN checkpoints.parent_checkpoint_id IS 'Parent checkpoint ID (for version history)';
COMMENT ON COLUMN checkpoints.checkpoint IS 'LangGraph state snapshot (JSONB format)';
COMMENT ON COLUMN checkpoints.metadata IS 'Checkpoint metadata (JSONB format)';

\echo '  ✓ checkpoints created (using session_id!)'

-- ----------------------------------------------------------------------------
-- 3-2. checkpoint_blobs 테이블 (session_id 사용!)
-- ----------------------------------------------------------------------------

\echo '[2/4] Creating checkpoint_blobs table...'

CREATE TABLE checkpoint_blobs (
    session_id TEXT NOT NULL,  -- ✅ thread_id → session_id 변경!
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL,
    version TEXT NOT NULL,
    type TEXT NOT NULL,
    blob BYTEA,
    PRIMARY KEY (session_id, checkpoint_ns, channel, version)
);

-- Comments
COMMENT ON TABLE checkpoint_blobs IS 'LangGraph binary data storage';
COMMENT ON COLUMN checkpoint_blobs.session_id IS 'Session ID (same value as chat_sessions.session_id)';
COMMENT ON COLUMN checkpoint_blobs.channel IS 'Channel name (e.g., messages, documents)';
COMMENT ON COLUMN checkpoint_blobs.version IS 'Blob version';
COMMENT ON COLUMN checkpoint_blobs.blob IS 'Binary data (BYTEA format)';

\echo '  ✓ checkpoint_blobs created (using session_id!)'

-- ----------------------------------------------------------------------------
-- 3-3. checkpoint_writes 테이블 (session_id 사용!)
-- ----------------------------------------------------------------------------

\echo '[3/4] Creating checkpoint_writes table...'

CREATE TABLE checkpoint_writes (
    session_id TEXT NOT NULL,  -- ✅ thread_id → session_id 변경!
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    blob BYTEA NOT NULL,
    PRIMARY KEY (session_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

-- Index
CREATE INDEX idx_checkpoint_writes_session_id ON checkpoint_writes(session_id);

-- Comments
COMMENT ON TABLE checkpoint_writes IS 'LangGraph incremental state updates';
COMMENT ON COLUMN checkpoint_writes.session_id IS 'Session ID (same value as chat_sessions.session_id)';
COMMENT ON COLUMN checkpoint_writes.task_id IS 'Task ID (for parallel execution)';
COMMENT ON COLUMN checkpoint_writes.idx IS 'Write index (sequence number)';
COMMENT ON COLUMN checkpoint_writes.channel IS 'Channel name';
COMMENT ON COLUMN checkpoint_writes.blob IS 'Update data (BYTEA format)';

\echo '  ✓ checkpoint_writes created (using session_id!)'

-- ----------------------------------------------------------------------------
-- 3-4. checkpoint_migrations 테이블
-- ----------------------------------------------------------------------------

\echo '[4/4] Creating checkpoint_migrations table...'

CREATE TABLE checkpoint_migrations (
    v INTEGER PRIMARY KEY
);

-- Comments
COMMENT ON TABLE checkpoint_migrations IS 'LangGraph schema version tracking';
COMMENT ON COLUMN checkpoint_migrations.v IS 'Migration version number';

\echo '  ✓ checkpoint_migrations created'
\echo ''
\echo '✅ Checkpoint tables created successfully'
\echo ''

-- ============================================================================
-- STEP 4: Create triggers
-- ============================================================================

\echo '=========================================='
\echo 'STEP 4: Creating triggers...'
\echo '=========================================='
\echo ''

-- ----------------------------------------------------------------------------
-- 4-1. updated_at 자동 갱신 트리거
-- ----------------------------------------------------------------------------

\echo '[1/1] Creating auto-update trigger for chat_sessions.updated_at...'

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

COMMENT ON FUNCTION update_chat_session_timestamp() IS 'Auto-update chat_sessions.updated_at on row update';

\echo '  ✓ Trigger created'
\echo ''
\echo '✅ Triggers created successfully'
\echo ''

-- ============================================================================
-- STEP 5: Verification
-- ============================================================================

\echo '=========================================='
\echo 'STEP 5: Verification'
\echo '=========================================='
\echo ''

-- List all tables
\echo '--- All Tables in Database ---'
SELECT
    schemaname,
    tablename,
    tableowner
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

\echo ''
\echo '--- Chat/Checkpoint Tables Only ---'
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) AS column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
    AND table_name IN ('chat_sessions', 'chat_messages', 'checkpoints', 'checkpoint_blobs', 'checkpoint_writes', 'checkpoint_migrations')
ORDER BY table_name;

\echo ''
\echo '--- Verify Unified Naming (session_id columns) ---'
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name IN ('chat_sessions', 'chat_messages', 'checkpoints', 'checkpoint_blobs', 'checkpoint_writes')
    AND column_name LIKE '%session%'
ORDER BY table_name, ordinal_position;

\echo ''
\echo '--- Foreign Keys ---'
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    rc.delete_rule
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
JOIN information_schema.referential_constraints AS rc
    ON tc.constraint_name = rc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema = 'public'
    AND tc.table_name IN ('chat_messages', 'checkpoints')
ORDER BY tc.table_name, kcu.column_name;

\echo ''
\echo '--- Triggers ---'
SELECT
    trigger_name,
    event_object_table,
    action_timing,
    event_manipulation
FROM information_schema.triggers
WHERE trigger_schema = 'public'
    AND event_object_table IN ('chat_sessions', 'chat_messages')
ORDER BY event_object_table, trigger_name;

\echo ''
\echo '--- Row Counts (should all be 0) ---'
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
\echo '✅ Clean Migration Complete!'
\echo '=========================================='
\echo ''
\echo 'Summary:'
\echo '  ✅ Dropped 10 old tables'
\echo '  ✅ Created 6 new tables'
\echo '  ✅ Unified naming: ALL tables use session_id'
\echo '  ✅ Created 1 trigger for auto-update'
\echo ''
\echo 'Tables created:'
\echo '  Core (2):'
\echo '    - chat_sessions (session_id)'
\echo '    - chat_messages (session_id → chat_sessions)'
\echo '  Checkpoint (4):'
\echo '    - checkpoints (session_id)'
\echo '    - checkpoint_blobs (session_id)'
\echo '    - checkpoint_writes (session_id)'
\echo '    - checkpoint_migrations'
\echo ''
\echo 'Next steps:'
\echo '  1. Verify: SELECT * FROM chat_sessions;'
\echo '  2. Test: INSERT INTO chat_sessions (session_id) VALUES (''test_123'');'
\echo '  3. Check: SELECT * FROM checkpoints WHERE session_id = ''test_123'';'
\echo ''
