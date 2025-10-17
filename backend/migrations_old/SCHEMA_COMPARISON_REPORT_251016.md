# DB Schema 비교 리포트

**날짜**: 2025-10-16
**작성자**: Claude Code
**목적**: 기존 DBML vs 실제 PostgreSQL 스키마 비교

---

## 📊 요약

| 항목 | 기존 DBML | 실제 DB | 차이 |
|------|-----------|---------|------|
| **테이블 수** | 6개 | 17개 | +11개 |
| **chat_sessions 필드** | 5개 | 9개 | +4개 |
| **chat_messages 필드** | 5개 | 5개 | ✅ 일치 |
| **Foreign Keys** | 1개 | 14개 | +13개 |

---

## 🔍 상세 비교

### 1. 테이블 수 차이

#### 기존 DBML (6개 테이블)
```
✅ chat_sessions
✅ chat_messages
✅ checkpoints
✅ checkpoint_blobs
✅ checkpoint_writes
✅ checkpoint_migrations
```

#### 실제 DB (17개 테이블) - 11개 추가!
```
✅ chat_sessions
✅ chat_messages
✅ checkpoints
✅ checkpoint_blobs
✅ checkpoint_writes
✅ checkpoint_migrations

➕ users (사용자)
➕ user_profiles (사용자 프로필)
➕ user_favorites (찜 목록)
➕ local_auths (로컬 인증)
➕ social_auths (소셜 인증)
➕ regions (지역)
➕ real_estates (부동산 매물)
➕ transactions (거래)
➕ real_estate_agents (중개사)
➕ nearby_facilities (주변 시설)
➕ trust_scores (신뢰도)
```

**이유**: 기존 DBML은 **채팅 기능만** 포함, 실제 DB는 **부동산 시스템 전체** 포함

---

### 2. chat_sessions 테이블 필드 차이

#### 기존 DBML (5개 필드)
```sql
session_id    VARCHAR(100)    PK
user_id       INTEGER         NOT NULL DEFAULT 1
title         VARCHAR(200)    NOT NULL DEFAULT '새 대화'
created_at    TIMESTAMP       NOT NULL DEFAULT now()
updated_at    TIMESTAMP       NOT NULL DEFAULT now()
```

#### 실제 DB (9개 필드) - 4개 추가!
```sql
session_id    VARCHAR(100)    PK
user_id       INTEGER         NOT NULL DEFAULT 1
title         VARCHAR(200)    NOT NULL DEFAULT '새 대화'
created_at    TIMESTAMP       NOT NULL DEFAULT now()
updated_at    TIMESTAMP       NOT NULL DEFAULT now()

➕ last_message  TEXT          -- 마지막 메시지 미리보기
➕ message_count INTEGER       DEFAULT 0
➕ is_active     BOOLEAN       DEFAULT true
➕ metadata      JSONB         -- 추가 메타데이터
```

**추가된 이유**:
- `last_message`: UI에서 세션 목록 표시 시 미리보기 필요
- `message_count`: 세션별 메시지 개수 빠른 조회
- `is_active`: 세션 활성/비활성 상태 관리
- `metadata`: 향후 확장을 위한 유연한 데이터 저장

---

### 3. chat_messages 테이블 ✅ 일치

#### 기존 DBML
```sql
id            SERIAL          PK
session_id    VARCHAR(100)    NOT NULL → chat_sessions.session_id
role          VARCHAR(20)     NOT NULL CHECK (user|assistant|system)
content       TEXT            NOT NULL
created_at    TIMESTAMP       NOT NULL DEFAULT now()
```

#### 실제 DB
```sql
id            SERIAL          PK
session_id    VARCHAR(100)    NOT NULL → chat_sessions.session_id
role          VARCHAR(20)     NOT NULL CHECK (user|assistant|system)
content       TEXT            NOT NULL
created_at    TIMESTAMP       NOT NULL DEFAULT now()
```

**✅ 완벽히 일치!**

**참고**:
- 이전에는 모델에서 `sender_type` / `UUID` 사용 → **오늘 수정 완료**
- 현재 모델과 DB 스키마 일치 확인됨

---

### 4. Checkpoint 테이블 ✅ 일치

**checkpoints, checkpoint_blobs, checkpoint_writes, checkpoint_migrations**:
- 기존 DBML과 실제 DB 완벽히 일치
- 모두 `session_id` 사용 (✅ 통합 명명 규칙)

---

## 🆕 새로 추가된 테이블 상세

### 인증 & 사용자 관리 (5개)

#### users
- 사용자 기본 정보 (인증 통합 테이블)
- `email`, `type`, `is_active`
- ENUM `usertype`: individual, agent, admin

#### user_profiles
- 사용자 프로필 정보
- `nickname`, `phone`
- 1:1 관계 → users.id

#### local_auths
- 로컬 인증 (아이디/비밀번호)
- `username`, `hashed_password`
- 1:1 관계 → users.id

#### social_auths
- 소셜 인증 (카카오, 네이버, 구글)
- `provider`, `provider_user_id`
- 1:N 관계 → users.id

#### user_favorites
- 사용자 찜 목록
- `user_id`, `real_estate_id`
- N:M 브리지 테이블

---

### 부동산 데이터 (6개)

#### regions
- 지역 정보 (법정동 기준)
- `code` (법정동코드), `name`

#### real_estates
- 부동산 매물 정보
- 30개 필드 (면적, 가격, 위치, 태그 등)
- ENUM `propertytype`: apartment, officetel, villa, single_house, commercial
- FK: region_id → regions.id

#### transactions
- 거래 정보 (매매, 전세, 월세)
- 가격, 보증금, 월세, 거래일
- ENUM `transactiontype`: sale, jeonse, monthly_rent, short_term_rent
- FK: real_estate_id → real_estates.id, region_id → regions.id

#### real_estate_agents
- 부동산 중개사 정보
- `name`, `address`, `phone`
- FK: real_estate_id → real_estates.id

#### nearby_facilities
- 주변 시설 정보 (학교, 병원, 지하철)
- `facility_type`, `name`, `distance`
- FK: real_estate_id → real_estates.id

#### trust_scores
- 부동산 신뢰도 점수
- `score` (0.00-1.00), `data_quality`, `transaction_activity`, `price_stability`
- 1:1 관계 → real_estates.id

---

## 🔗 Foreign Key 관계도

### 사용자 중심
```
users (1)
  ├─ user_profiles (1:1)
  ├─ local_auths (1:1)
  ├─ social_auths (1:N)
  └─ user_favorites (1:N)
```

### 부동산 중심
```
regions (1)
  ├─ real_estates (1:N)
  └─ transactions (1:N)

real_estates (1)
  ├─ transactions (1:N)
  ├─ real_estate_agents (1:N)
  ├─ nearby_facilities (1:N)
  ├─ trust_scores (1:1)
  └─ user_favorites (1:N)
```

### 채팅 중심
```
chat_sessions (1)
  ├─ chat_messages (1:N, CASCADE DELETE)
  ├─ checkpoints (1:N, implicit)
  ├─ checkpoint_blobs (1:N, implicit)
  └─ checkpoint_writes (1:N, implicit)
```

---

## ✅ 검증 결과

### 오늘 수정한 내용 확인

#### ✅ ChatMessage 모델 수정 완료
- `id`: UUID → Integer (SERIAL) ✅
- `sender_type` → `role` ✅
- DB 스키마와 완벽히 일치 ✅

#### ✅ 저장 로직 추가 완료
- `_save_message_to_db()` 헬퍼 함수 ✅
- 사용자 메시지 저장 ✅
- AI 응답 저장 ✅

---

## 📝 DBML 파일 생성 완료

### 생성된 파일

#### 1. simplified_schema_unified.dbml (기존)
- **용도**: 채팅 기능만 포함 (6개 테이블)
- **상태**: 일부 필드 누락 (chat_sessions에 4개 필드 부족)

#### 2. complete_schema_251016.dbml (신규) ✅
- **용도**: 전체 시스템 스키마 (17개 테이블)
- **상태**: 실제 DB 완벽 반영
- **위치**: `backend/migrations/complete_schema_251016.dbml`

---

## 🎯 다음 단계

### 1. DBML 다이어그램 확인
1. https://dbdiagram.io/d 접속
2. `complete_schema_251016.dbml` 전체 복사
3. 에디터에 붙여넣기
4. ERD 자동 생성 확인

### 2. 테스트 진행
1. 백엔드 재시작
2. 메시지 전송
3. DB 조회:
   ```sql
   SELECT * FROM chat_messages ORDER BY created_at DESC LIMIT 10;
   ```

### 3. Frontend 연동 (향후)
- 메시지 로드: `GET /api/v1/chat/sessions/{session_id}/messages`
- 세션 목록: `GET /api/v1/chat/sessions`

---

## 📌 주요 발견 사항

### session_id 통합 사용 ✅
- 모든 채팅/체크포인트 테이블이 동일한 `session_id` 사용
- "session-{uuid}" 형식
- Backend에서 생성 (`POST /api/v1/chat/start`)
- `thread_id` 용어 사용 안함 (혼동 방지)

### chat_session_id 미사용 ⚠️
- Frontend에서 생성하지만 Backend에서 사용 안함
- 로깅만 하고 DB 저장 안함
- 향후 제거 예정 (계획서 참조: `Fix_Plan_Chat_Message_Persistence_251016.md`)

### ENUM 타입 사용
- `usertype`, `propertytype`, `transactiontype`
- PostgreSQL ENUM으로 정의됨
- DBML에서는 문자열로 표시

---

## 🔧 기술적 세부사항

### Triggers
- `chat_sessions.updated_at` 자동 갱신 트리거
- 함수: `update_chat_session_timestamp()`

### Indexes
**chat_sessions**:
- `session_id` (PK)
- `user_id`
- `updated_at DESC`
- `(user_id, updated_at DESC)` (복합)

**chat_messages**:
- `id` (PK)
- `session_id`
- `(session_id, created_at DESC)` (복합)

**transactions**:
- `article_no` (UNIQUE)
- `transaction_date`
- `(real_estate_id, transaction_date)` (복합)
- `(transaction_date, transaction_type)` (복합)

### Constraints
**chat_messages**:
- `role` CHECK: 'user', 'assistant', 'system'만 허용
- `session_id` FK: CASCADE DELETE

---

**문서 끝**
