# Unified Migration Script 사용 가이드

## 📋 개요

이 스크립트는 HolmesNyangz 프로젝트의 **모든 데이터베이스 테이블**을 한 번에 생성/재생성하는 통합 마이그레이션 스크립트입니다.

## 🗂️ 생성되는 테이블 (총 9개)

### Core Tables (5개)
1. **sessions** - HTTP/WebSocket 세션 관리
2. **chat_sessions** - GPT-style 채팅 세션
3. **chat_messages** - 채팅 메시지 저장
4. **conversation_memories** - Long-term Memory (대화 기록)
5. **entity_memories** - Entity 추적

### LangGraph Checkpoint Tables (4개)
6. **checkpoints** - LangGraph 체크포인트
7. **checkpoint_blobs** - 체크포인트 바이너리 데이터
8. **checkpoint_writes** - 체크포인트 쓰기 기록
9. **checkpoint_migrations** - 체크포인트 마이그레이션 버전

## 🚀 실행 방법

### Git Bash에서 실행

```bash
# 1. 프로젝트 루트로 이동
cd /c/kdy/Projects/holmesnyangz/beta_v001

# 2. 마이그레이션 실행
PGPASSWORD=root1234 psql -h localhost -U postgres -d real_estate -f backend/migrations/unified_migration.sql
```

### 한 줄 명령어

```bash
PGPASSWORD=root1234 psql -h localhost -U postgres -d real_estate -f backend/migrations/unified_migration.sql
```

## 📝 실행 단계 설명

스크립트는 다음 5단계로 진행됩니다:

### STEP 1: 기존 테이블 삭제 (DROP CASCADE)
```sql
DROP TABLE IF EXISTS checkpoint_writes CASCADE;
DROP TABLE IF EXISTS checkpoint_blobs CASCADE;
...
```
- 기존 테이블 모두 삭제
- CASCADE로 종속된 객체(FK, 인덱스 등)도 함께 삭제

### STEP 2: Core 테이블 생성
```sql
CREATE TABLE sessions (...);
CREATE TABLE chat_sessions (...);
CREATE TABLE conversation_memories (...);
...
```
- 9개 테이블 생성
- 인덱스 생성
- Foreign Key 설정

### STEP 3: LangGraph 체크포인트 테이블 생성
```sql
CREATE TABLE checkpoints (...);
CREATE TABLE checkpoint_writes (...);
...
```

### STEP 4: 트리거 및 함수 생성
```sql
CREATE FUNCTION update_chat_session_timestamp() ...
CREATE TRIGGER trigger_update_chat_session_timestamp ...
```
- `updated_at` 자동 갱신 트리거
- `message_count`, `last_message` 자동 갱신 트리거
- 제목 자동 생성 로직

### STEP 5: 검증 (Verification)
```sql
SELECT * FROM pg_tables WHERE schemaname = 'public';
SELECT COUNT(*) FROM chat_sessions;
...
```
- 테이블 목록 출력
- 각 테이블의 row count 확인
- 트리거 목록 출력
- Foreign Key 관계 출력

## ✅ 실행 결과 예시

```
==========================================
Starting Unified Migration...
==========================================

STEP 1: Dropping existing tables...

All tables dropped successfully.

STEP 2: Creating core tables...

  [2-1] Creating sessions table...
  ✓ sessions table created
  [2-2] Creating chat_sessions table...
  ✓ chat_sessions table created
  [2-3] Creating chat_messages table...
  ✓ chat_messages table created
  [2-4] Creating conversation_memories table...
  ✓ conversation_memories table created
  [2-5] Creating entity_memories table...
  ✓ entity_memories table created

STEP 3: Creating LangGraph checkpoint tables...

  [3-1] Creating checkpoints table...
  ✓ checkpoints table created
  [3-2] Creating checkpoint_blobs table...
  ✓ checkpoint_blobs table created
  [3-3] Creating checkpoint_writes table...
  ✓ checkpoint_writes table created
  [3-4] Creating checkpoint_migrations table...
  ✓ checkpoint_migrations table created

STEP 4: Creating triggers and functions...

  [4-1] Creating update_chat_session_timestamp trigger...
  ✓ update_chat_session_timestamp trigger created
  [4-2] Creating update_session_message_count trigger...
  ✓ update_session_message_count trigger created

STEP 5: Verifying migration...

==========================================
All Tables:
==========================================
 schemaname |       tablename        | tableowner
------------+------------------------+------------
 public     | chat_messages          | postgres
 public     | chat_sessions          | postgres
 public     | checkpoint_blobs       | postgres
 public     | checkpoint_migrations  | postgres
 public     | checkpoint_writes      | postgres
 public     | checkpoints            | postgres
 public     | conversation_memories  | postgres
 public     | entity_memories        | postgres
 public     | sessions               | postgres
(9 rows)

==========================================
Table Row Counts:
==========================================
       table_name        | row_count
-------------------------+-----------
 chat_messages           |         0
 chat_sessions           |         0
 checkpoint_blobs        |         0
 checkpoint_migrations   |         0
 checkpoint_writes       |         0
 checkpoints             |         0
 conversation_memories   |         0
 entity_memories         |         0
 sessions                |         0
(9 rows)

==========================================
Triggers:
==========================================
             trigger_name              | event_object_table | action_timing | event_manipulation
---------------------------------------+--------------------+---------------+--------------------
 trigger_update_chat_session_timestamp | chat_sessions      | BEFORE        | UPDATE
 trigger_update_session_message_count  | conversation_memories | AFTER      | INSERT
(2 rows)

==========================================
Foreign Keys:
==========================================
      table_name       |  column_name  | foreign_table_name | foreign_column_name
-----------------------+---------------+--------------------+---------------------
 chat_messages         | session_id    | chat_sessions      | session_id
 conversation_memories | session_id    | chat_sessions      | session_id
(2 rows)

==========================================
✅ Migration Complete!
==========================================

Summary:
  - 9 tables created
  - 2 triggers created
  - 2 functions created
  - Multiple indexes created
  - Foreign keys established
```

## 🔍 실행 후 확인 방법

### 1. psql로 접속
```bash
PGPASSWORD=root1234 psql -h localhost -U postgres -d real_estate
```

### 2. 테이블 목록 확인
```sql
\dt
```

### 3. 특정 테이블 구조 확인
```sql
\d+ chat_sessions
\d+ conversation_memories
```

### 4. 트리거 확인
```sql
\dft
```

### 5. 테스트 데이터 삽입
```sql
-- chat_sessions 삽입
INSERT INTO chat_sessions (session_id, user_id, title)
VALUES ('session-test-123', 1, '새 대화');

-- conversation_memories 삽입 (트리거 테스트)
INSERT INTO conversation_memories (user_id, query, response_summary, relevance, session_id)
VALUES (1, '테스트 질문입니다', '테스트 응답입니다', 'RELEVANT', 'session-test-123');

-- chat_sessions 확인 (message_count가 1로 증가했는지 확인)
SELECT * FROM chat_sessions WHERE session_id = 'session-test-123';
```

## ⚠️ 주의사항

### 1. 데이터 손실
- **기존 데이터가 모두 삭제됩니다!**
- 실행 전 반드시 백업하세요
- 개발 환경에서만 사용하세요

### 2. 백업 방법
```bash
# 전체 데이터베이스 백업
PGPASSWORD=root1234 pg_dump -h localhost -U postgres real_estate > backup_$(date +%Y%m%d_%H%M%S).sql

# 특정 테이블만 백업
PGPASSWORD=root1234 pg_dump -h localhost -U postgres -t conversation_memories real_estate > backup_conversations.sql
```

### 3. 복원 방법
```bash
# 백업 파일에서 복원
PGPASSWORD=root1234 psql -h localhost -U postgres -d real_estate < backup_20251014_123456.sql
```

## 🔄 재실행 시

스크립트는 멱등성(idempotent)을 가지므로 여러 번 실행해도 안전합니다:
- `DROP TABLE IF EXISTS` 사용
- `CREATE OR REPLACE FUNCTION` 사용

## 🆚 기존 마이그레이션 파일과의 차이

### 기존 방식 (여러 파일)
```
backend/migrations/
  ├── create_sessions_table.sql
  ├── create_memory_tables.sql
  ├── add_chat_sessions_and_update_memories.sql
  └── recreate_chat_sessions.sql
```
❌ 각 파일을 순서대로 실행해야 함
❌ 의존성 관리 필요
❌ 에러 발생 시 롤백 어려움

### 새로운 방식 (통합 파일)
```
backend/migrations/
  └── unified_migration.sql
```
✅ 한 번에 실행 가능
✅ 자동으로 순서 관리
✅ 롤백 쉬움 (전체 재실행)

## 📦 추가 도구

### 빠른 재설정 스크립트 만들기

```bash
# backend/migrations/reset_db.sh
#!/bin/bash
echo "🔄 Resetting database..."
PGPASSWORD=root1234 psql -h localhost -U postgres -d real_estate -f unified_migration.sql
echo "✅ Database reset complete!"
```

실행 권한 부여 및 실행:
```bash
chmod +x backend/migrations/reset_db.sh
./backend/migrations/reset_db.sh
```

## 🐛 문제 해결

### 오류 1: "database does not exist"
```bash
# 데이터베이스 생성
PGPASSWORD=root1234 psql -h localhost -U postgres -c "CREATE DATABASE real_estate;"
```

### 오류 2: "connection refused"
```bash
# PostgreSQL 서비스 시작 (Windows)
net start postgresql-x64-14

# 또는 확인
pg_ctl status
```

### 오류 3: "permission denied"
```bash
# postgres 사용자로 실행 확인
PGPASSWORD=root1234 psql -h localhost -U postgres -d real_estate -c "SELECT current_user;"
```

## 📚 관련 문서

- 전체 구현 보고서: `backend/app/reports/long_term_memory/GPT_STYLE_MULTI_CHAT_IMPLEMENTATION_REPORT_251014.md`
- 기존 마이그레이션 가이드: `backend/migrations/HOW_TO_RUN_MIGRATION.md`

## ✨ 다음 단계

1. **마이그레이션 실행**
   ```bash
   PGPASSWORD=root1234 psql -h localhost -U postgres -d real_estate -f backend/migrations/unified_migration.sql
   ```

2. **백엔드 재시작**
   ```bash
   cd backend
   python main.py
   ```

3. **프론트엔드 재시작**
   ```bash
   cd frontend
   npm run dev
   ```

4. **테스트**
   - 새 채팅 생성
   - 메시지 전송
   - PostgreSQL에서 데이터 확인

---

**Created**: 2025-10-14
**Author**: Claude Code
**Version**: 1.0
