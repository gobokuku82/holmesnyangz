-- ============================================================================
-- 기존 세션 데이터 확인 스크립트
-- ============================================================================

-- 1. chat_sessions 테이블의 모든 session_id 형식 확인
SELECT
    session_id,
    title,
    created_at,
    message_count,
    CASE
        WHEN session_id LIKE 'session-%' THEN '✅ 표준 (session-)'
        WHEN session_id LIKE 'chat-%' THEN '❌ 비표준 (chat-)'
        ELSE '⚠️ 알 수 없는 형식'
    END AS format_type
FROM chat_sessions
ORDER BY created_at DESC;

-- 2. session_id 형식별 개수 통계
SELECT
    CASE
        WHEN session_id LIKE 'session-%' THEN '✅ session-{uuid}'
        WHEN session_id LIKE 'chat-%' THEN '❌ chat-{uuid}'
        ELSE '⚠️ 기타'
    END AS format_type,
    COUNT(*) as count,
    MIN(created_at) as first_created,
    MAX(created_at) as last_created
FROM chat_sessions
GROUP BY
    CASE
        WHEN session_id LIKE 'session-%' THEN '✅ session-{uuid}'
        WHEN session_id LIKE 'chat-%' THEN '❌ chat-{uuid}'
        ELSE '⚠️ 기타'
    END
ORDER BY count DESC;

-- 3. 비표준 형식(chat-) 세션의 메시지 확인
SELECT
    cs.session_id,
    cs.title,
    COUNT(cm.id) as message_count,
    cs.created_at
FROM chat_sessions cs
LEFT JOIN chat_messages cm ON cs.session_id = cm.session_id
WHERE cs.session_id LIKE 'chat-%'
GROUP BY cs.session_id, cs.title, cs.created_at
ORDER BY cs.created_at DESC;

-- 4. checkpoints 테이블의 session_id 형식 확인
SELECT
    CASE
        WHEN session_id LIKE 'session-%' THEN '✅ session-{uuid}'
        WHEN session_id LIKE 'chat-%' THEN '❌ chat-{uuid}'
        ELSE '⚠️ 기타'
    END AS format_type,
    COUNT(*) as checkpoint_count
FROM checkpoints
GROUP BY
    CASE
        WHEN session_id LIKE 'session-%' THEN '✅ session-{uuid}'
        WHEN session_id LIKE 'chat-%' THEN '❌ chat-{uuid}'
        ELSE '⚠️ 기타'
    END
ORDER BY checkpoint_count DESC;

-- 5. 전체 요약
SELECT
    'chat_sessions' as table_name,
    COUNT(*) as total_count,
    SUM(CASE WHEN session_id LIKE 'session-%' THEN 1 ELSE 0 END) as standard_count,
    SUM(CASE WHEN session_id LIKE 'chat-%' THEN 1 ELSE 0 END) as non_standard_count
FROM chat_sessions
UNION ALL
SELECT
    'chat_messages' as table_name,
    COUNT(DISTINCT session_id) as total_count,
    SUM(CASE WHEN session_id LIKE 'session-%' THEN 1 ELSE 0 END) as standard_count,
    SUM(CASE WHEN session_id LIKE 'chat-%' THEN 1 ELSE 0 END) as non_standard_count
FROM chat_messages
UNION ALL
SELECT
    'checkpoints' as table_name,
    COUNT(DISTINCT session_id) as total_count,
    SUM(CASE WHEN session_id LIKE 'session-%' THEN 1 ELSE 0 END) as standard_count,
    SUM(CASE WHEN session_id LIKE 'chat-%' THEN 1 ELSE 0 END) as non_standard_count
FROM checkpoints;
