-- 간단한 데이터 현황 확인
\echo '=========================================='
\echo '📊 테이블 목록'
\echo '=========================================='
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;

\echo ''
\echo '=========================================='
\echo '📈 데이터 개수'
\echo '=========================================='

-- 부동산 데이터
\echo '🏢 부동산 관련:'
SELECT 'regions' as table_name, COUNT(*) as count FROM regions
UNION ALL SELECT 'real_estates', COUNT(*) FROM real_estates
UNION ALL SELECT 'transactions', COUNT(*) FROM transactions;

-- 채팅 데이터
\echo ''
\echo '💬 채팅 관련:'
SELECT 'chat_sessions' as table_name, COUNT(*) as count FROM chat_sessions
UNION ALL SELECT 'chat_messages', COUNT(*) FROM chat_messages;

-- Session ID 형식
\echo ''
\echo '🔑 Session ID 형식:'
SELECT
    CASE
        WHEN session_id LIKE 'session-%' THEN '✅ session-{uuid}'
        WHEN session_id LIKE 'chat-%' THEN '❌ chat-{uuid}'
        ELSE '⚠️ 기타'
    END AS format_type,
    COUNT(*) as count
FROM chat_sessions
GROUP BY format_type;
