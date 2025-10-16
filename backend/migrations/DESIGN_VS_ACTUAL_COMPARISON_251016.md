# 설계 vs 실제 DB 구조 비교

**날짜**: 2025-10-16
**작성자**: Claude Code

---

## 📊 비교 대상

| 구분 | 문서 | 날짜 |
|------|------|------|
| **최종 설계** | `clean_migration.sql` | 2025-10-15 |
| **실제 DB** | PostgreSQL (real_estate) | 2025-10-16 현재 |

---

## ✅ chat_sessions 테이블 비교

### 설계 (clean_migration.sql)

```sql
CREATE TABLE chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    title VARCHAR(200) NOT NULL DEFAULT '새 대화',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
```

**컬럼 수**: 5개

---

### 실제 DB

```sql
CREATE TABLE chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    title VARCHAR(200) NOT NULL DEFAULT '새 대화',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

    -- 추가된 컬럼 4개
    last_message TEXT,
    message_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    metadata JSONB
);
```

**컬럼 수**: 9개

---

### ❌ 차이점: 4개 컬럼 추가됨

| 컬럼 | 설계 | 실제 | 차이 |
|------|------|------|------|
| session_id | ✅ | ✅ | 일치 |
| user_id | ✅ | ✅ | 일치 |
| title | ✅ | ✅ | 일치 |
| created_at | ✅ | ✅ | 일치 |
| updated_at | ✅ | ✅ | 일치 |
| **last_message** | ❌ 없음 | ✅ 있음 | **추가됨** |
| **message_count** | ❌ 없음 | ✅ 있음 | **추가됨** |
| **is_active** | ❌ 없음 | ✅ 있음 | **추가됨** |
| **metadata** | ❌ 없음 | ✅ 있음 | **추가됨** |

---

## ✅ chat_messages 테이블 비교

### 설계 (clean_migration.sql)

```sql
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
```

---

### 실제 DB

```sql
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
```

---

### ✅ 차이점: 없음 (완벽히 일치)

---

## ✅ Checkpoint 테이블 비교 (4개)

### checkpoints

| 항목 | 설계 | 실제 | 결과 |
|------|------|------|------|
| session_id | TEXT | TEXT | ✅ 일치 |
| checkpoint_ns | TEXT | TEXT | ✅ 일치 |
| checkpoint_id | TEXT | TEXT | ✅ 일치 |
| parent_checkpoint_id | TEXT | TEXT | ✅ 일치 |
| type | TEXT | TEXT | ✅ 일치 |
| checkpoint | JSONB | JSONB | ✅ 일치 |
| metadata | JSONB | JSONB | ✅ 일치 |

**결과**: ✅ 완벽히 일치

---

### checkpoint_blobs, checkpoint_writes, checkpoint_migrations

**결과**: ✅ 모두 설계와 일치

---

## 📋 전체 테이블 비교 (17개)

### 설계에 포함된 테이블 (6개)
```
✅ chat_sessions      (5개 컬럼 설계 → 9개 컬럼 실제)
✅ chat_messages      (일치)
✅ checkpoints        (일치)
✅ checkpoint_blobs   (일치)
✅ checkpoint_writes  (일치)
✅ checkpoint_migrations (일치)
```

---

### 설계에 없지만 실제 DB에 있는 테이블 (11개)

**인증/사용자** (5개):
```
users
user_profiles
local_auths
social_auths
user_favorites
```

**부동산 데이터** (6개):
```
regions
real_estates
transactions
real_estate_agents
nearby_facilities
trust_scores
```

---

## 🔍 차이 발생 원인 분석

### 1. chat_sessions에 4개 컬럼 추가된 이유

#### last_message (TEXT)
- **목적**: 세션 목록 UI에서 미리보기 표시
- **예시**: "임대차계약이 만료되면 자동으로..."
- **추가 시점**: 설계 이후 UI 요구사항 반영

#### message_count (INTEGER DEFAULT 0)
- **목적**: 세션별 메시지 개수 빠른 조회
- **장점**: `COUNT(*)` 쿼리 대신 캐시 값 사용
- **추가 시점**: 성능 최적화 차원

#### is_active (BOOLEAN DEFAULT true)
- **목적**: 세션 활성/아카이빙 상태 관리
- **사용 예**: 오래된 세션 숨기기, 삭제된 세션 표시
- **추가 시점**: 세션 관리 기능 확장

#### metadata (JSONB)
- **목적**: 향후 확장을 위한 유연한 데이터 저장
- **예시**: `{"theme": "dark", "language": "ko", "tags": ["중요"]}`
- **추가 시점**: 확장성 고려

---

### 2. 11개 부동산 테이블이 설계에 없는 이유

**clean_migration.sql의 목적**:
> "Drop old chat/memory/checkpoint tables and create new simplified schema"

→ **채팅 관련 테이블만** 재생성하는 마이그레이션

**부동산 테이블은**:
- 이미 존재하던 기존 테이블
- 이번 마이그레이션 대상이 아님
- 삭제/재생성 불필요

---

## 📌 결론

### ✅ 정상 상태

1. **chat_messages**: 설계와 100% 일치 ✅
2. **checkpoints 관련 4개**: 설계와 100% 일치 ✅
3. **부동산 11개 테이블**: 기존 테이블 정상 유지 ✅

---

### ⚠️ 설계와 다른 부분

**chat_sessions에 4개 컬럼 추가됨**:
- `last_message`, `message_count`, `is_active`, `metadata`

**영향도**:
- ✅ 기능 동작에 문제 없음 (추가 컬럼은 NULL/기본값 허용)
- ✅ 기존 코드와 호환됨
- ⚠️ 설계 문서 업데이트 필요

---

## 🎯 권장 조치

### 옵션 1: 설계 문서 업데이트 (권장)
`clean_migration.sql`에 4개 컬럼 추가
```sql
CREATE TABLE chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    title VARCHAR(200) NOT NULL DEFAULT '새 대화',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    last_message TEXT,                    -- 추가
    message_count INTEGER DEFAULT 0,      -- 추가
    is_active BOOLEAN DEFAULT true,       -- 추가
    metadata JSONB                        -- 추가
);
```

---

### 옵션 2: DB를 설계에 맞추기 (비권장)
4개 컬럼 삭제
```sql
ALTER TABLE chat_sessions
DROP COLUMN last_message,
DROP COLUMN message_count,
DROP COLUMN is_active,
DROP COLUMN metadata;
```

**비권장 이유**:
- 향후 기능 구현 시 다시 추가 필요
- 이미 추가된 컬럼이 해롭지 않음
- 마이그레이션 리스크

---

## 📝 설계 문서 업데이트 필요 사항

### 1. clean_migration.sql 업데이트
- chat_sessions 테이블 생성 부분에 4개 컬럼 추가
- 주석으로 용도 설명

### 2. DBML 파일 확인
- `complete_schema_251016.dbml`: ✅ 이미 반영됨
- `simplified_schema_unified.dbml`: ⚠️ 업데이트 필요

### 3. API 문서 업데이트
- `GET /sessions` 응답에 `last_message`, `message_count` 추가
- Pydantic 모델 확인

---

## 🔧 코드 영향도 분석

### Backend Models

#### ✅ ChatSession 모델 (이미 반영됨)
```python
# backend/app/models/chat.py
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(String(100), primary_key=True)
    user_id = Column(Integer, ...)
    title = Column(String(200), ...)
    created_at = Column(TIMESTAMP, ...)
    updated_at = Column(TIMESTAMP, ...)
    last_message = Column(Text)           # ✅ 있음
    message_count = Column(Integer, ...)  # ✅ 있음
    is_active = Column(Boolean, ...)      # ✅ 있음
    metadata = Column(JSONB)              # ✅ 있음 (session_metadata로 매핑)
```

**결과**: ✅ 모델이 실제 DB와 일치

---

### API Responses

#### ChatSessionResponse
```python
# backend/app/schemas/chat.py (추정)
class ChatSessionResponse(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    last_message: Optional[str] = None        # 확인 필요
    message_count: int = 0                    # 확인 필요
```

---

## 🔄 마이그레이션 히스토리 정리

### Phase 1: 초기 설계 (2025-10-15)
- 채팅 6개 테이블 설계
- `chat_sessions` 5개 컬럼

### Phase 2: 기능 확장 (날짜 미상)
- `chat_sessions`에 4개 컬럼 추가
- 세션 목록 UI 지원

### Phase 3: 현재 (2025-10-16)
- 설계와 실제 차이 발견
- 비교 문서 작성

---

**문서 끝**

**권장**: 옵션 1 (설계 문서 업데이트)을 선택하여 `clean_migration.sql`을 실제 DB에 맞게 수정
