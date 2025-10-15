# Database Schema Creation Guide

## 📋 개요

Python SQLAlchemy를 사용하여 데이터베이스 스키마를 코드로 관리합니다.

## 📦 생성된 파일

1. **`backend/app/models/unified_schema.py`** (520줄)
   - 9개 테이블의 SQLAlchemy 모델 정의
   - 관계(Relationships), 인덱스, 제약조건 포함

2. **`backend/create_schema.py`** (250줄)
   - 스키마 생성/삭제 스크립트
   - 트리거 생성 포함
   - 검증 기능

## 🚀 사용 방법

### 방법 1: Python 스크립트 (추천)

```bash
# 프로젝트 루트로 이동
cd /c/kdy/Projects/holmesnyangz/beta_v001

# 스키마 정보 확인
python backend/create_schema.py --info

# 테이블 생성 (기존 테이블 유지)
python backend/create_schema.py

# 테이블 재생성 (기존 삭제 후 생성)
python backend/create_schema.py --drop
```

### 방법 2: SQL 스크립트

```bash
# SQL 파일로 실행
PGPASSWORD=root1234 psql -h localhost -U postgres -d real_estate -f backend/migrations/unified_migration.sql
```

## 🔄 두 방법의 차이

### Python 스크립트 (create_schema.py)

**장점**:
- ✅ 코드로 스키마 관리 (버전 관리 용이)
- ✅ ORM 모델과 DB 스키마 자동 동기화
- ✅ 검증 기능 내장
- ✅ 프로그래밍 방식 제어

**단점**:
- ❌ Python 환경 필요
- ❌ SQL 직접 수정 불가

**사용 시나리오**:
- 개발 중 스키마 변경이 잦을 때
- CI/CD 파이프라인에서 자동화
- ORM 모델 기반 개발

### SQL 스크립트 (unified_migration.sql)

**장점**:
- ✅ Python 없이 실행 가능
- ✅ SQL 직접 확인/수정 가능
- ✅ 트리거 등 복잡한 로직 포함
- ✅ 빠른 실행

**단점**:
- ❌ 수동 유지보수 필요
- ❌ ORM 모델과 별도 관리

**사용 시나리오**:
- 프로덕션 배포
- 빠른 DB 재설정
- SQL 직접 제어 필요 시

## 📊 생성되는 테이블

### Core Tables (5개)

| 테이블 | 설명 | 주요 필드 |
|--------|------|----------|
| `sessions` | HTTP/WebSocket 세션 | session_id, user_id, expires_at |
| `chat_sessions` | GPT-style 채팅 세션 | session_id, user_id, title, message_count |
| `chat_messages` | 채팅 메시지 | id, session_id, role, content |
| `conversation_memories` | Long-term Memory | id, user_id, query, response_summary, session_id |
| `entity_memories` | Entity 추적 | id, user_id, entity_type, entity_name |

### LangGraph Checkpoint Tables (4개)

| 테이블 | 설명 |
|--------|------|
| `checkpoints` | LangGraph 체크포인트 |
| `checkpoint_blobs` | 체크포인트 바이너리 데이터 |
| `checkpoint_writes` | 체크포인트 쓰기 기록 |
| `checkpoint_migrations` | 마이그레이션 버전 |

## 🎯 Python 스크립트 상세

### 옵션

```bash
# 스키마 정보만 출력 (변경 없음)
python backend/create_schema.py --info

# 테이블 생성 (기존 유지)
python backend/create_schema.py

# 모든 테이블 삭제 후 재생성 (경고!)
python backend/create_schema.py --drop

# 트리거 생성 건너뛰기
python backend/create_schema.py --skip-triggers
```

### 실행 예시

```bash
$ python backend/create_schema.py

======================================================================
🏗️  Database Schema Creation
======================================================================
🔌 Connecting to: localhost:5432/real_estate
✓ Connected to PostgreSQL: PostgreSQL 14.0

📋 Existing tables: 9
  chat_messages, chat_sessions, checkpoint_blobs, checkpoint_migrations, checkpoint_writes ... (+4 more)

🏗️  Creating 9 tables...
✅ Created 9 tables: sessions, chat_sessions, chat_messages, conversation_memories, entity_memories, checkpoints, checkpoint_blobs, checkpoint_writes, checkpoint_migrations

📌 Creating triggers and functions...
  ✓ Triggers created successfully

🔍 Verifying schema...

📊 Database Status:
  Expected tables: 9
  Existing tables: 9

✅ All required tables exist!

📈 Table Row Counts:
  sessions                            0 rows
  chat_sessions                       0 rows
  chat_messages                       0 rows
  conversation_memories               0 rows
  entity_memories                     0 rows
  checkpoints                         0 rows
  checkpoint_blobs                    0 rows
  checkpoint_writes                   0 rows
  checkpoint_migrations               0 rows

======================================================================
✅ Schema creation completed successfully!
======================================================================
```

## 🔧 코드에서 사용하기

### 1. 모델 임포트

```python
from backend.app.models.unified_schema import (
    Session,
    ChatSession,
    ChatMessage,
    ConversationMemory,
    EntityMemory,
    Checkpoint,
    CheckpointBlob,
    CheckpointWrite,
    CheckpointMigration
)
```

### 2. 테이블 생성

```python
from sqlalchemy import create_engine
from backend.app.models.unified_schema import create_all_tables

engine = create_engine('postgresql+psycopg://postgres:root1234@localhost:5432/real_estate')
create_all_tables(engine)
```

### 3. 데이터 조회

```python
from sqlalchemy.orm import Session
from backend.app.models.unified_schema import ChatSession

with Session(engine) as session:
    # 모든 채팅 세션 조회
    chat_sessions = session.query(ChatSession).all()

    # 특정 사용자의 활성 세션
    user_sessions = session.query(ChatSession)\
        .filter(ChatSession.user_id == 1)\
        .filter(ChatSession.is_active == True)\
        .order_by(ChatSession.updated_at.desc())\
        .all()
```

### 4. 데이터 삽입

```python
from backend.app.models.unified_schema import ChatSession, ConversationMemory

with Session(engine) as session:
    # 새 채팅 세션 생성
    new_session = ChatSession(
        session_id='session-test-123',
        user_id=1,
        title='테스트 대화'
    )
    session.add(new_session)
    session.commit()

    # 대화 기록 추가
    memory = ConversationMemory(
        user_id=1,
        query='테스트 질문',
        response_summary='테스트 응답',
        relevance='RELEVANT',
        session_id='session-test-123'
    )
    session.add(memory)
    session.commit()
```

## 🔄 기존 모델 파일 마이그레이션

### 현재 파일 구조
```
backend/app/models/
├── __init__.py
├── chat.py           (기존)
├── memory.py         (기존)
├── session.py        (기존)
├── real_estate.py
├── trust.py
├── users.py
└── unified_schema.py (신규)
```

### 통합 방법 (선택사항)

#### 옵션 1: 점진적 마이그레이션 (추천)
```python
# backend/app/models/__init__.py
from .unified_schema import (
    Session,
    ChatSession,
    ChatMessage,
    ConversationMemory,
    EntityMemory,
    # ... 나머지
)

# 기존 모델은 deprecated 처리
from .chat import ChatSession as OldChatSession  # deprecated
from .memory import ConversationMemory as OldConversationMemory  # deprecated
```

#### 옵션 2: 완전 교체
```bash
# 1. 기존 파일 백업
mv backend/app/models/chat.py backend/app/models/chat.py.backup
mv backend/app/models/memory.py backend/app/models/memory.py.backup
mv backend/app/models/session.py backend/app/models/session.py.backup

# 2. __init__.py 업데이트
# unified_schema에서 모든 모델 임포트하도록 수정
```

#### 옵션 3: 병행 사용 (현재 상태 유지)
```python
# 기존 코드는 기존 모델 사용
from backend.app.models.chat import ChatSession

# 새로운 코드는 unified_schema 사용
from backend.app.models.unified_schema import ChatSession
```

## 📚 모델 상세 문서

### ChatSession

```python
class ChatSession(Base):
    """GPT-style 채팅 세션"""
    session_id: str          # Primary Key
    user_id: int             # 사용자 ID
    title: str               # 세션 제목 (자동 생성)
    last_message: str        # 마지막 메시지 미리보기
    message_count: int       # 메시지 수 (트리거로 자동 증가)
    created_at: datetime     # 생성 시각
    updated_at: datetime     # 마지막 업데이트 (트리거로 자동 갱신)
    is_active: bool          # 활성 상태
    session_metadata: dict   # 메타데이터 (JSONB)

    # Relationships
    chat_messages: List[ChatMessage]
    conversation_memories: List[ConversationMemory]
```

### ConversationMemory

```python
class ConversationMemory(Base):
    """Long-term Memory (대화 기록)"""
    id: UUID                    # Primary Key
    user_id: int                # 사용자 ID
    query: str                  # 사용자 질문
    response_summary: str       # AI 응답 요약
    relevance: str              # 'RELEVANT', 'IRRELEVANT', 'UNCLEAR'
    session_id: str             # ChatSession FK (nullable)
    intent_detected: str        # 감지된 의도
    entities_mentioned: dict    # 언급된 엔티티 (JSONB)
    created_at: datetime        # 생성 시각
    conversation_metadata: dict # 메타데이터 (JSONB)

    # Relationships
    chat_session: ChatSession
```

## 🐛 트러블슈팅

### 오류 1: "relation already exists"
```bash
# 기존 테이블 삭제 후 재생성
python backend/create_schema.py --drop
```

### 오류 2: "connection refused"
```bash
# PostgreSQL 서비스 시작 확인
pg_ctl status

# Windows
net start postgresql-x64-14
```

### 오류 3: "ModuleNotFoundError"
```bash
# Python 경로 확인
cd /c/kdy/Projects/holmesnyangz/beta_v001
python backend/create_schema.py

# 가상환경 활성화 (있는 경우)
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 오류 4: "column does not exist"
```bash
# 기존 테이블 구조가 다른 경우
# 1. 백업
PGPASSWORD=root1234 pg_dump -h localhost -U postgres real_estate > backup.sql

# 2. 재생성
python backend/create_schema.py --drop
```

## ✅ 체크리스트

### 스키마 생성 전
- [ ] PostgreSQL 실행 중인지 확인
- [ ] 데이터베이스 백업 (중요한 경우)
- [ ] Python 환경 확인

### 스키마 생성 후
- [ ] 9개 테이블 모두 생성되었는지 확인
- [ ] 트리거 2개 생성되었는지 확인
- [ ] Foreign Key 관계 확인
- [ ] 테스트 데이터 삽입 성공하는지 확인

## 🎓 참고 자료

- SQLAlchemy 문서: https://docs.sqlalchemy.org/
- PostgreSQL 문서: https://www.postgresql.org/docs/
- 프로젝트 보고서: `backend/app/reports/long_term_memory/GPT_STYLE_MULTI_CHAT_IMPLEMENTATION_REPORT_251014.md`

---

**Created**: 2025-10-14
**Author**: Claude Code
