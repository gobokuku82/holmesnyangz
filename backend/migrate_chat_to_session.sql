-- ============================================================================
-- Session ID 마이그레이션 스크립트
-- chat-{uuid} → session-{uuid} 형식 변환
-- ============================================================================
-- 실행 전 주의사항:
-- 1. 반드시 백업 먼저 수행!
-- 2. 트랜잭션 내에서 실행
-- 3. 테스트 환경에서 먼저 검증
-- ============================================================================

BEGIN;

-- 1. 백업 테이블 생성 (롤백용)
CREATE TABLE IF NOT EXISTS chat_sessions_backup AS
SELECT * FROM chat_sessions WHERE session_id LIKE 'chat-%';

CREATE TABLE IF NOT EXISTS chat_messages_backup AS
SELECT * FROM chat_messages WHERE session_id LIKE 'chat-%';

-- 2. 임시 매핑 테이블 생성
CREATE TEMPORARY TABLE session_id_mapping (
    old_session_id VARCHAR(100),
    new_session_id VARCHAR(100)
);

-- 3. chat-{uuid} → session-{uuid} 매핑 생성
INSERT INTO session_id_mapping (old_session_id, new_session_id)
SELECT
    session_id as old_session_id,
    'session-' || SUBSTRING(session_id FROM 6) as new_session_id  -- 'chat-' 제거 후 'session-' 추가
FROM chat_sessions
WHERE session_id LIKE 'chat-%';

-- 4. chat_messages 테이블 업데이트 (FK 때문에 먼저 수행)
UPDATE chat_messages cm
SET session_id = m.new_session_id
FROM session_id_mapping m
WHERE cm.session_id = m.old_session_id;

-- 5. checkpoints 테이블 업데이트
UPDATE checkpoints cp
SET session_id = m.new_session_id
FROM session_id_mapping m
WHERE cp.session_id = m.old_session_id;

-- 6. checkpoint_writes 테이블 업데이트
UPDATE checkpoint_writes cw
SET session_id = m.new_session_id
FROM session_id_mapping m
WHERE cw.session_id = m.old_session_id;

-- 7. checkpoint_blobs 테이블 업데이트
UPDATE checkpoint_blobs cb
SET session_id = m.new_session_id
FROM session_id_mapping m
WHERE cb.session_id = m.old_session_id;

-- 8. chat_sessions 테이블 업데이트 (PK이므로 마지막)
UPDATE chat_sessions cs
SET session_id = m.new_session_id
FROM session_id_mapping m
WHERE cs.session_id = m.old_session_id;

-- 9. 검증: 변환된 세션 확인
SELECT
    'After Migration' as status,
    COUNT(*) as total_sessions,
    SUM(CASE WHEN session_id LIKE 'session-%' THEN 1 ELSE 0 END) as standard_format,
    SUM(CASE WHEN session_id LIKE 'chat-%' THEN 1 ELSE 0 END) as old_format
FROM chat_sessions;

-- 10. 변환 결과 상세 확인
SELECT
    m.old_session_id,
    m.new_session_id,
    cs.title,
    COUNT(cm.id) as message_count
FROM session_id_mapping m
LEFT JOIN chat_sessions cs ON cs.session_id = m.new_session_id
LEFT JOIN chat_messages cm ON cm.session_id = m.new_session_id
GROUP BY m.old_session_id, m.new_session_id, cs.title
ORDER BY cs.created_at DESC;

-- ============================================================================
-- 커밋 또는 롤백 선택
-- ============================================================================

-- 성공 시:
-- COMMIT;

-- 실패 시 또는 테스트 시:
-- ROLLBACK;

-- ============================================================================
-- 롤백 스크립트 (문제 발생 시 사용)
-- ============================================================================

/*
BEGIN;

-- chat_sessions 복원
DELETE FROM chat_sessions WHERE session_id LIKE 'session-%'
    AND session_id IN (
        SELECT 'session-' || SUBSTRING(session_id FROM 6)
        FROM chat_sessions_backup
    );

INSERT INTO chat_sessions
SELECT * FROM chat_sessions_backup;

-- chat_messages 복원
DELETE FROM chat_messages WHERE session_id LIKE 'session-%'
    AND session_id IN (
        SELECT 'session-' || SUBSTRING(session_id FROM 6)
        FROM chat_messages_backup
    );

INSERT INTO chat_messages
SELECT * FROM chat_messages_backup;

-- 백업 테이블 삭제
DROP TABLE IF EXISTS chat_sessions_backup;
DROP TABLE IF EXISTS chat_messages_backup;

COMMIT;
*/
