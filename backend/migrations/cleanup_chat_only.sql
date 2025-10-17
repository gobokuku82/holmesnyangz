-- ============================================================================
-- Chat Data Only Cleanup Script
-- ============================================================================
-- 생성일: 2025-10-17
-- 목적: 채팅/세션 데이터만 삭제 (부동산 데이터 보존)
-- 주의: 채팅 히스토리와 체크포인트 데이터가 삭제됩니다!
-- ============================================================================

BEGIN;

\echo '=========================================='
\echo '🗑️  채팅 데이터 삭제 시작...'
\echo '=========================================='

-- ============================================================================
-- STEP 1: 현재 데이터 백업 (롤백용)
-- ============================================================================

\echo ''
\echo '📦 백업 테이블 생성 중...'

-- 채팅 데이터 백업
CREATE TABLE IF NOT EXISTS chat_sessions_backup AS
SELECT * FROM chat_sessions;

CREATE TABLE IF NOT EXISTS chat_messages_backup AS
SELECT * FROM chat_messages;

\echo '✅ 백업 완료'

-- ============================================================================
-- STEP 2: 체크포인트 데이터 삭제
-- ============================================================================

\echo ''
\echo '💾 체크포인트 데이터 삭제 중...'

DELETE FROM checkpoint_writes;
DELETE FROM checkpoint_blobs;
DELETE FROM checkpoints;

\echo '✅ 체크포인트 삭제 완료'

-- ============================================================================
-- STEP 3: 채팅 데이터 삭제
-- ============================================================================

\echo ''
\echo '💬 채팅 데이터 삭제 중...'

-- chat_messages 먼저 삭제 (FK 때문)
DELETE FROM chat_messages;

-- chat_sessions 삭제
DELETE FROM chat_sessions;

\echo '✅ 채팅 데이터 삭제 완료'

-- ============================================================================
-- STEP 4: 시퀀스 리셋
-- ============================================================================

\echo ''
\echo '🔄 시퀀스 리셋 중...'

-- chat_messages ID 시퀀스 리셋
ALTER SEQUENCE chat_messages_id_seq RESTART WITH 1;

\echo '✅ 시퀀스 리셋 완료'

-- ============================================================================
-- STEP 5: 검증
-- ============================================================================

\echo ''
\echo '=========================================='
\echo '✅ 삭제 완료 - 검증 결과:'
\echo '=========================================='

-- 삭제된 테이블 확인
\echo '💬 채팅 데이터:'
SELECT 'chat_sessions' as table_name, COUNT(*) as count FROM chat_sessions
UNION ALL SELECT 'chat_messages', COUNT(*) FROM chat_messages
UNION ALL SELECT 'checkpoints', COUNT(*) FROM checkpoints;

-- 보존된 테이블 확인
\echo ''
\echo '🏢 부동산 데이터 (보존됨):'
SELECT 'real_estates' as table_name, COUNT(*) as count FROM real_estates
UNION ALL SELECT 'transactions', COUNT(*) FROM transactions
UNION ALL SELECT 'regions', COUNT(*) FROM regions;

\echo ''
\echo '=========================================='
\echo '📝 다음 단계:'
\echo '=========================================='
\echo '1. 검증 결과 확인'
\echo '2. 문제 없으면: COMMIT; 입력'
\echo '3. 문제 있으면: ROLLBACK; 입력'
\echo ''
\echo '롤백 방법:'
\echo '  ROLLBACK;'
\echo '  INSERT INTO chat_sessions SELECT * FROM chat_sessions_backup;'
\echo '  INSERT INTO chat_messages SELECT * FROM chat_messages_backup;'
\echo '=========================================='

-- ============================================================================
-- 사용자 확인 대기 (자동 COMMIT 안 함)
-- ============================================================================

\echo ''
\echo '⏸️  트랜잭션 대기 중... COMMIT 또는 ROLLBACK을 입력하세요.'

-- COMMIT 또는 ROLLBACK은 사용자가 직접 실행
