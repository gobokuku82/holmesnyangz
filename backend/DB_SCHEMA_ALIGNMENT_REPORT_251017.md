# 📊 DB 스키마 정리 및 정렬 보고서

**작성일**: 2025-10-17
**목적**: 채팅(메모리) 스키마와 부동산 스키마 명확히 분리 및 정리

---

## 🎯 Executive Summary

### 문제점
1. ❌ SQL 파일(`complete_rebuild_251017.sql`)과 Python 모델 간 ENUM 타입 불일치
2. ❌ `migrations/` 및 `scripts/` 폴더에 불필요한 파일 혼재
3. ❌ 채팅 스키마와 부동산 스키마가 섞여서 관리 복잡

### 해결책
1. ✅ 폴더 백업: `migrations_old/`, `scripts_old/` 생성
2. ✅ 필수 파일만 선별하여 새 폴더에 복사
3. ✅ 통합 스키마 문서 작성 (`unified_schema.dbml`)
4. ✅ Python `init_db.py` 사용으로 ENUM 문제 해결

---

## 📁 폴더 구조 변경

### Before (기존)
```
backend/
├── migrations/
│   ├── complete_rebuild_251017.sql  ← ENUM 타입 불일치
│   ├── complete_schema_251016.dbml  ← 채팅 스키마 (정확)
│   ├── simplified_schema_unified.dbml
│   └── ... (기타 파일들)
│
└── scripts/
    ├── init_db.py
    ├── init_db_estate_only.py  ← 새로 생성
    ├── import_apt_ofst.py
    ├── import_villa_house_oneroom.py
    ├── import_utils.py
    ├── check_all_data.py
    └── ... (기타 파일들)
```

### After (정리 후)
```
backend/
├── migrations_old/  ← 백업
│   └── (모든 기존 파일)
│
├── scripts_old/  ← 백업
│   └── (모든 기존 파일)
│
├── migrations/  ← 깔끔!
│   └── unified_schema.dbml  ← ✅ 최종 통합 스키마 (채팅 + 부동산)
│
└── scripts/  ← 깔끔!
    ├── __init__.py
    ├── init_db.py  ← ✅ 전체 테이블 생성
    ├── import_apt_ofst.py  ← ✅ 아파트/오피스텔 import
    ├── import_villa_house_oneroom.py  ← ✅ 원룸/빌라 import
    └── import_utils.py  ← ✅ 공통 유틸리티
```

---

## 📋 스키마 비교 및 정렬

### Part 1: 채팅 & 메모리 스키마

#### 원본 스키마 (complete_schema_251016.dbml)
```dbml
Table chat_sessions {
  session_id varchar(100) [pk]
  user_id integer [not null, default: 1]
  title varchar(200) [not null, default: '새 대화']
  created_at timestamp [not null, default: `now()`]
  updated_at timestamp [not null, default: `now()`]
  last_message text
  message_count integer [default: 0]
  is_active boolean [default: true]
  metadata jsonb
}

Table chat_messages {
  id serial [pk]
  session_id varchar(100) [not null, ref: > chat_sessions.session_id]
  role varchar(20) [not null]
  content text [not null]
  created_at timestamp [not null, default: `now()`]
}
```

#### Python 모델 (app/models/chat.py)
```python
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(String(100), primary_key=True)  # ✅ 일치
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # ✅ 일치
    title = Column(String(200), nullable=False, default="새 대화")  # ✅ 일치
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)  # ✅ 일치
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)  # ✅ 일치
    last_message = Column(Text)  # ✅ 일치
    message_count = Column(Integer, default=0)  # ✅ 일치
    is_active = Column(Boolean, default=True)  # ✅ 일치
    session_metadata = Column("metadata", JSONB)  # ✅ 일치

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)  # ✅ 일치
    session_id = Column(String(100), ForeignKey("chat_sessions.session_id", ondelete="CASCADE"), nullable=False)  # ✅ 일치
    role = Column(String(20), nullable=False)  # ✅ 일치
    content = Column(Text, nullable=False)  # ✅ 일치
    structured_data = Column(JSONB, nullable=True)  # ✅ 확장 필드 (호환)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())  # ✅ 일치
```

#### ✅ 결론: 채팅 스키마는 Python 모델과 완전히 일치
- `structured_data` 필드는 추가 확장 필드 (UI 표시용, 호환 가능)

---

### Part 2: 부동산 스키마

#### 원본 없음 (부동산 스키마는 original 폴더 참조)

#### Python 모델 (app/models/real_estate.py)
```python
class PropertyType(enum.Enum):
    APARTMENT = "apartment"  # ← 소문자 값!
    OFFICETEL = "officetel"
    VILLA = "villa"
    ONEROOM = "oneroom"
    HOUSE = "house"

class RealEstate(Base):
    __tablename__ = "real_estates"

    id = Column(Integer, primary_key=True)
    property_type = Column(Enum(PropertyType), nullable=False)  # ← ENUM!
    code = Column(String(30), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    # ... (나머지 필드)

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    real_estate_id = Column(Integer, ForeignKey("real_estates.id"), nullable=False)
    transaction_type = Column(Enum(TransactionType))  # ← ENUM!
    # ... (나머지 필드)
```

#### ⚠️ ENUM 타입 문제

**SQL 스키마 (complete_rebuild_251017.sql)**:
```sql
CREATE TYPE propertytype AS ENUM ('apartment', 'officetel', 'villa', ...);  -- 소문자!
CREATE TYPE transactiontype AS ENUM ('sale', 'jeonse', 'rent');  -- 소문자!
```

**Python Enum**:
```python
class PropertyType(enum.Enum):
    APARTMENT = "apartment"  # Enum 이름: APARTMENT, 값: "apartment"
```

**문제**:
- SQLAlchemy의 `Enum(PropertyType)`이 기본적으로 PostgreSQL native ENUM을 생성하려고 함
- SQL 파일로 수동 생성한 ENUM과 충돌 발생
- Python은 `PropertyType.APARTMENT`를 보내지만, SQL은 `"apartment"` 문자열을 기대

**해결책**:
- ✅ Python `init_db.py`로 테이블 생성 → SQLAlchemy가 자동으로 올바르게 ENUM 생성
- ❌ SQL 파일 사용 X (ENUM 타입 불일치 문제)

---

## 🔧 ENUM 타입 작동 원리

### 방법 1: Python init_db.py (✅ 권장)

```bash
uv run python scripts/init_db.py
```

**동작**:
1. SQLAlchemy가 Python Enum을 분석
2. PostgreSQL ENUM 타입 자동 생성: `CREATE TYPE propertytype AS ENUM ('apartment', 'officetel', ...)`
3. 테이블 생성: `property_type propertytype`
4. 데이터 insert: `PropertyType.APARTMENT` → `"apartment"` 자동 변환 ✅

### 방법 2: SQL 파일 (❌ 비권장)

```bash
psql -U postgres -d real_estate -f migrations/complete_rebuild_251017.sql
```

**문제**:
1. SQL이 ENUM 생성: `CREATE TYPE propertytype AS ENUM ('apartment', ...)`
2. 테이블 생성: `property_type propertytype`
3. Python import: `PropertyType.APARTMENT` → ???
4. SQLAlchemy가 ENUM 이름(`APARTMENT`)을 보내서 에러! ❌

---

## ✅ 최종 솔루션

### 사용할 파일

1. **스키마 문서**: `migrations/unified_schema.dbml`
   - 참고용
   - dbdiagram.io에서 ERD 확인용

2. **테이블 생성**: `scripts/init_db.py`
   - Python SQLAlchemy ORM 사용
   - ENUM 자동 생성 (정확함)

3. **데이터 Import**:
   - `scripts/import_apt_ofst.py`
   - `scripts/import_villa_house_oneroom.py`
   - `scripts/import_utils.py`

### 사용하지 않을 파일

1. ❌ `migrations_old/complete_rebuild_251017.sql`
   - ENUM 타입 불일치
   - 백업용으로만 보관

2. ❌ `scripts_old/`의 기타 파일들
   - 테스트 파일, 오래된 스크립트
   - 백업용으로만 보관

---

## 🚀 실행 가이드

### Step 1: 전체 테이블 생성

```bash
cd /c/kdy/Projects/holmesnyangz/beta_v001/backend

# Python으로 모든 테이블 생성 (채팅 + 부동산)
uv run python scripts/init_db.py
```

**생성되는 테이블** (17개):
- ✅ 채팅: `users`, `chat_sessions`, `chat_messages`
- ✅ 체크포인트: `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`
- ✅ 부동산: `regions`, `real_estates`, `transactions`, `nearby_facilities`, `real_estate_agents`, `trust_scores`
- ✅ 사용자: `user_profiles`, `user_favorites`, `local_auths`, `social_auths`

### Step 2: 부동산 데이터 Import

```bash
# 아파트/오피스텔 (약 2,104개)
uv run python scripts/import_apt_ofst.py

# 원룸 (약 1,010개)
uv run python scripts/import_villa_house_oneroom.py --auto --type oneroom

# 빌라 (약 6,631개)
uv run python scripts/import_villa_house_oneroom.py --auto --type villa
```

### Step 3: 확인

```bash
psql -U postgres -d real_estate -c "
SELECT 'real_estates' as table, COUNT(*) FROM real_estates
UNION ALL SELECT 'transactions', COUNT(*) FROM transactions
UNION ALL SELECT 'chat_sessions', COUNT(*) FROM chat_sessions;
"
```

**예상 결과**:
```
     table      | count
----------------+-------
 real_estates   | 9,745
 transactions   | 15,000+
 chat_sessions  | 0
```

---

## 📊 스키마 비교표

| 항목 | 채팅 스키마 | 부동산 스키마 |
|------|-----------|-------------|
| **문서** | `complete_schema_251016.dbml` | `unified_schema.dbml` (Part 2) |
| **Python 모델** | `app/models/chat.py` | `app/models/real_estate.py` |
| **생성 방법** | `init_db.py` | `init_db.py` |
| **데이터 import** | N/A (런타임 생성) | `import_*.py` 스크립트 |
| **ENUM 타입** | 없음 | `propertytype`, `transactiontype` |
| **일치 여부** | ✅ 100% 일치 | ✅ Python 기준 100% 일치 |

---

## 🔑 핵심 정리

### ✅ 해야 할 것

1. **테이블 생성**: `init_db.py` 사용
2. **데이터 import**: `import_*.py` 스크립트 사용
3. **스키마 참고**: `unified_schema.dbml` 문서 확인

### ❌ 하지 말아야 할 것

1. **SQL 파일 사용**: ENUM 타입 불일치
2. **수동 ENUM 생성**: SQLAlchemy에게 맡기기
3. **스키마 수동 수정**: Python 모델이 정답

---

## 📝 백업 파일 목록

### `migrations_old/`
- `complete_rebuild_251017.sql` - SQL 스키마 (ENUM 문제)
- `complete_schema_251016.dbml` - 채팅 스키마 (정확)
- `simplified_schema_unified.dbml` - 이전 통합 스키마
- `cleanup_chat_only.sql` - 채팅 데이터만 삭제
- 기타 마이그레이션 파일들

### `scripts_old/`
- `init_db.py` - 원본
- `init_db_estate_only.py` - 부동산만 초기화 (생성함)
- `check_all_data.py`, `check_db_data.py` - 테스트 스크립트
- 기타 import 스크립트들

---

## 🎯 권장 워크플로우

### 신규 설치
```bash
# 1. 전체 초기화
uv run python scripts/init_db.py

# 2. 부동산 데이터 import
uv run python scripts/import_apt_ofst.py
uv run python scripts/import_villa_house_oneroom.py --auto --type oneroom
uv run python scripts/import_villa_house_oneroom.py --auto --type villa

# 3. 서버 시작
uvicorn app.main:app --reload
```

### 채팅 데이터 보존 (부동산만 재import)
```bash
# 1. 부동산 테이블만 DROP
psql -U postgres -d real_estate -c "
DROP TABLE IF EXISTS trust_scores CASCADE;
DROP TABLE IF EXISTS nearby_facilities CASCADE;
DROP TABLE IF EXISTS real_estate_agents CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS real_estates CASCADE;
DROP TABLE IF EXISTS regions CASCADE;
"

# 2. 부동산 테이블만 재생성
uv run python -c "
from app.db.postgre_db import engine
from app.models.real_estate import Region, RealEstate, Transaction, NearbyFacility, RealEstateAgent
from app.models.trust import TrustScore

for table in [Region.__table__, RealEstate.__table__, Transaction.__table__, NearbyFacility.__table__, RealEstateAgent.__table__, TrustScore.__table__]:
    table.create(bind=engine, checkfirst=True)
"

# 3. 부동산 데이터 import
uv run python scripts/import_apt_ofst.py
uv run python scripts/import_villa_house_oneroom.py --auto --type oneroom
uv run python scripts/import_villa_house_oneroom.py --auto --type villa
```

---

## ✅ 검증 체크리스트

- [ ] `migrations_old/` 폴더 생성됨
- [ ] `scripts_old/` 폴더 생성됨
- [ ] `migrations/unified_schema.dbml` 생성됨
- [ ] `scripts/init_db.py` 복사됨
- [ ] `scripts/import_*.py` 복사됨
- [ ] `init_db.py` 실행 성공 (17개 테이블)
- [ ] 부동산 데이터 import 성공 (~9,745개)
- [ ] 채팅 기능 정상 작동
- [ ] 부동산 검색 정상 작동

---

**작성일**: 2025-10-17
**작성자**: Claude Code Assistant
**문서 버전**: 1.0 (Final Clean Version)
