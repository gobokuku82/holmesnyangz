-- ============================================================================
-- Add structured_data column to chat_messages
-- ============================================================================
-- Purpose: Store structured answer data (sections, metadata) for rich UI display
-- Date: 2025-10-16
-- Author: Claude Code
--
-- What this does:
-- 1. Add structured_data JSONB column to chat_messages table
-- 2. This allows storing structured answers (법률상담, 데이터 분석 등)
-- 3. F5 새로고침 시 원본 메시지와 똑같이 표시 가능
--
-- Usage:
--   cd backend/migrations
--   PGPASSWORD=root1234 psql -h localhost -U postgres -d real_estate -f add_structured_data_251016.sql
-- ============================================================================

\echo ''
\echo '=========================================='
\echo 'Adding structured_data column'
\echo '=========================================='
\echo ''

-- Add structured_data column
ALTER TABLE chat_messages
ADD COLUMN IF NOT EXISTS structured_data JSONB;

-- Add comment
COMMENT ON COLUMN chat_messages.structured_data IS 'Structured answer data (sections, metadata) for rich UI display';

\echo '✅ Column added successfully'
\echo ''

-- Verification
\echo '--- Verify Column ---'
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name = 'chat_messages'
    AND column_name = 'structured_data';

\echo ''
\echo '=========================================='
\echo '✅ Migration Complete!'
\echo '=========================================='
\echo ''
