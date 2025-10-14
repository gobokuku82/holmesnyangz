-- ============================================================================
-- Long-term Memory 데이터 확인용 SQL 쿼리
-- ============================================================================
-- 실행 방법:
-- psql "postgresql://postgres:root1234@localhost:5432/real_estate" -f backend/migrations/check_memory_data.sql
-- ============================================================================

\echo ''
\echo '=========================================='
\echo '1. 전체 통계 확인'
\echo '=========================================='

-- 1-1. 대화 기록 통계
\echo ''
\echo '[대화 기록 통계]'
SELECT
    COUNT(*) as "총 대화 기록 수",
    COUNT(DISTINCT user_id) as "사용자 수",
    COUNT(CASE WHEN relevance = 'RELEVANT' THEN 1 END) as "RELEVANT 대화",
    COUNT(CASE WHEN relevance = 'IRRELEVANT' THEN 1 END) as "IRRELEVANT 대화",
    MIN(created_at) as "첫 대화 시간",
    MAX(created_at) as "마지막 대화 시간"
FROM conversation_memories;

-- 1-2. 사용자별 대화 개수
\echo ''
\echo '[사용자별 대화 개수]'
SELECT
    user_id as "사용자 ID",
    COUNT(*) as "대화 개수",
    COUNT(CASE WHEN relevance = 'RELEVANT' THEN 1 END) as "RELEVANT",
    COUNT(CASE WHEN relevance = 'IRRELEVANT' THEN 1 END) as "IRRELEVANT"
FROM conversation_memories
GROUP BY user_id
ORDER BY COUNT(*) DESC;

-- 1-3. 엔티티 통계
\echo ''
\echo '[엔티티 추적 통계]'
SELECT
    COUNT(*) as "총 엔티티 수",
    COUNT(DISTINCT user_id) as "엔티티를 언급한 사용자 수",
    COUNT(CASE WHEN entity_type = 'properties' THEN 1 END) as "매물 엔티티",
    COUNT(CASE WHEN entity_type = 'regions' THEN 1 END) as "지역 엔티티",
    COUNT(CASE WHEN entity_type = 'agents' THEN 1 END) as "중개사 엔티티"
FROM entity_memories;

-- 1-4. 선호도 데이터 통계
\echo ''
\echo '[사용자 선호도 통계]'
SELECT
    COUNT(*) as "선호도 레코드 수",
    COUNT(DISTINCT user_id) as "선호도를 가진 사용자 수"
FROM user_preferences;


\echo ''
\echo '=========================================='
\echo '2. 최근 대화 기록 (최신 10개)'
\echo '=========================================='

SELECT
    LEFT(id::TEXT, 8) as "ID (앞 8자)",
    user_id as "사용자",
    LEFT(query, 50) as "쿼리 (50자)",
    LEFT(response_summary, 50) as "응답 요약 (50자)",
    relevance as "관련성",
    intent_detected as "의도",
    TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as "생성 시간"
FROM conversation_memories
ORDER BY created_at DESC
LIMIT 10;


\echo ''
\echo '=========================================='
\echo '3. 사용자 선호도 확인'
\echo '=========================================='

SELECT
    user_id as "사용자 ID",
    preferences as "선호도 (JSONB)",
    TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as "생성 시간",
    TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI:SS') as "수정 시간"
FROM user_preferences
ORDER BY updated_at DESC;


\echo ''
\echo '=========================================='
\echo '4. 엔티티 추적 확인 (최신 10개)'
\echo '=========================================='

SELECT
    LEFT(id::TEXT, 8) as "ID",
    user_id as "사용자",
    entity_type as "타입",
    entity_id as "엔티티 ID",
    entity_name as "이름",
    mention_count as "언급 횟수",
    TO_CHAR(last_mentioned_at, 'YYYY-MM-DD HH24:MI:SS') as "마지막 언급"
FROM entity_memories
ORDER BY last_mentioned_at DESC
LIMIT 10;


\echo ''
\echo '=========================================='
\echo '5. 특정 사용자 상세 확인'
\echo '=========================================='
\echo '※ user_id=1로 필터링 (필요시 쿼리 수정)'
\echo ''

-- 5-1. 해당 사용자의 모든 대화
\echo '[사용자 1의 모든 대화]'
SELECT
    TO_CHAR(created_at, 'MM-DD HH24:MI') as "시간",
    relevance as "관련성",
    LEFT(query, 60) as "쿼리",
    LEFT(response_summary, 60) as "응답",
    intent_detected as "의도"
FROM conversation_memories
WHERE user_id = 1
ORDER BY created_at DESC;

-- 5-2. 해당 사용자의 선호도
\echo ''
\echo '[사용자 1의 선호도]'
SELECT
    preferences
FROM user_preferences
WHERE user_id = 1;

-- 5-3. 해당 사용자의 엔티티
\echo ''
\echo '[사용자 1의 엔티티]'
SELECT
    entity_type as "타입",
    entity_name as "이름",
    mention_count as "언급",
    TO_CHAR(last_mentioned_at, 'MM-DD HH24:MI') as "마지막"
FROM entity_memories
WHERE user_id = 1
ORDER BY last_mentioned_at DESC;


\echo ''
\echo '=========================================='
\echo '6. 데이터 품질 검증'
\echo '=========================================='

-- 6-1. user_id가 NULL인 레코드 (있으면 안 됨)
\echo ''
\echo '[user_id가 NULL인 대화 (있으면 문제)]'
SELECT COUNT(*) as "NULL user_id 개수"
FROM conversation_memories
WHERE user_id IS NULL;

-- 6-2. relevance 값 검증
\echo ''
\echo '[relevance 값 분포]'
SELECT
    relevance,
    COUNT(*) as "개수"
FROM conversation_memories
GROUP BY relevance
ORDER BY COUNT(*) DESC;

-- 6-3. 최근 1시간 내 데이터 (테스트 직후 확인용)
\echo ''
\echo '[최근 1시간 내 생성된 대화]'
SELECT
    COUNT(*) as "개수",
    COUNT(DISTINCT user_id) as "사용자 수"
FROM conversation_memories
WHERE created_at > NOW() - INTERVAL '1 hour';


\echo ''
\echo '=========================================='
\echo '완료!'
\echo '=========================================='
\echo ''
