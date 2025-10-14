# Chat Sessions Migration 실행 가이드

## 마이그레이션 파일
- **파일명**: `recreate_chat_sessions.sql`
- **목적**: GPT 스타일 멀티 채팅 시스템 구현을 위한 데이터베이스 스키마 재생성

## 실행 방법

### Windows 환경
```bash
psql "postgresql://postgres:root1234@localhost:5432/real_estate" -f backend/migrations/recreate_chat_sessions.sql
```

### 또는 psql 대화형 모드에서
```bash
# PostgreSQL 접속
psql -U postgres -d real_estate

# 마이그레이션 실행
\i backend/migrations/recreate_chat_sessions.sql
```

## 마이그레이션 내용

### 1. 기존 구조 삭제 (Clean Install)
- `chat_sessions` 테이블 완전 삭제 (CASCADE)
- `conversation_memories.session_id` 컬럼 삭제
- 관련 Foreign Key 제약조건 삭제

### 2. chat_sessions 테이블 생성
```sql
CREATE TABLE chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(200) DEFAULT '새 대화',
    last_message TEXT,
    message_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB
);
```

### 3. conversation_memories 테이블 수정
- `session_id` 컬럼 추가
- Foreign Key 제약조건 추가 (chat_sessions 참조)
- 인덱스 생성 (성능 최적화)

### 4. 자동 업데이트 트리거 생성
- `updated_at` 자동 갱신 트리거
- `message_count`, `last_message` 자동 갱신 트리거

### 5. 기존 데이터 마이그레이션
- 기존 `conversation_memories` 데이터를 위한 default session 생성
- 세션 제목: "이전 대화 (마이그레이션)"
- 모든 기존 대화를 해당 세션에 연결

## 성공 확인

마이그레이션 성공 시 다음 메시지들이 표시됩니다:
```
NOTICE: Dropped FK constraint fk_conv_mem_session
NOTICE: Dropped session_id column from conversation_memories
NOTICE: Migrated memories for user 1 to session session-migrated-1-...
NOTICE: Migration completed: 1 users processed
NOTICE: ✅ Migration completed successfully!
```

그리고 테이블 요약 정보가 출력됩니다:
```
         table_name              | total_rows | unique_users
---------------------------------+------------+-------------
 ✅ chat_sessions                |          1 |           1
 ✅ conversation_memories with session |    2 |           1
 ⚠️ conversation_memories without session | 0 |           0
```

## 오류 발생 시

### 오류: 테이블이 존재하지 않음
- 정상입니다. 마이그레이션이 IF EXISTS로 안전하게 처리됩니다.

### 오류: Foreign Key 위반
- users 테이블에 user_id=1인 사용자가 있는지 확인하세요.
- 없다면 먼저 생성:
  ```sql
  INSERT INTO users (id, email, type, is_active)
  VALUES (1, 'test@test.com', 'USER', true);
  ```

### ROLLBACK 발생
- 전체 마이그레이션이 취소됩니다 (트랜잭션 보호).
- 오류 메시지를 확인하고 문제를 해결한 후 다시 실행하세요.

## 다음 단계

마이그레이션 성공 후:
1. ✅ Backend SQLAlchemy 모델 업데이트 (`models/chat_session.py` 생성)
2. ✅ Session 관리 API 엔드포인트 구현
3. ✅ Frontend Session 목록 UI 구현
4. ✅ "새 채팅" 버튼 추가
5. ✅ Session 전환 기능 구현
