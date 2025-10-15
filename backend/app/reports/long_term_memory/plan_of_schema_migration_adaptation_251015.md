# Schema Migration Adaptation Plan

**Date**: 2025-10-15
**Author**: Claude Code
**Purpose**: Clean migration 후 코드 적응 계획서

---

## 📋 Executive Summary

**10월 15일 Clean Migration 실행 결과:**
- ✅ 10개 테이블 삭제 (sessions, conversation_memories, entity_memories, user_preferences 등)
- ✅ 6개 테이블 생성 (chat_sessions, chat_messages, checkpoints 4개)
- ✅ Unified naming: 모든 테이블이 `session_id` 사용 (thread_id 제거)

**현재 상황:**
- ❌ `LongTermMemoryService` - conversation_memories, entity_memories, user_preferences 테이블 의존 (**삭제됨!**)
- ❌ `SessionManager` - sessions 테이블 의존 (**삭제됨!**)
- ✅ `chat_api.py` - memory_service 사용 중 (440-485 라인)
- ✅ `models/memory.py`, `models/session.py` - 삭제된 테이블 참조

**목표:**
1. 삭제된 테이블 의존성 제거
2. 새 스키마에 맞는 메모리 서비스 재설계
3. 최소한의 기능으로 대화 기록 저장/로드 구현

---

## 🔍 Current State Analysis

### 1. 삭제된 테이블과 영향받는 코드

#### **1-1. `sessions` 테이블 (HTTP/WebSocket)**

**삭제됨:**
```sql
-- 기존 스키마
CREATE TABLE sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id INTEGER,
    created_at TIMESTAMP,
    expires_at TIMESTAMP,
    last_activity TIMESTAMP,
    metadata JSONB
);
```

**영향받는 파일:**
| 파일 | 클래스/함수 | 의존도 | 상태 |
|------|------------|--------|------|
| `app/api/session_manager.py` | `SessionManager` 전체 | **높음** | ❌ 작동 불가 |
| `app/models/session.py` | `Session` 모델 | **높음** | ❌ 작동 불가 |
| `app/api/chat_api.py` | `get_session_manager()` 사용 | 중간 | ⚠️ 수정 필요 |

**SessionManager 사용처:**
```python
# chat_api.py
@router.post("/start")
async def start_session(session_mgr: SessionManager = Depends(get_session_manager)):
    session_id, expires_at = await session_mgr.create_session(...)  # ❌ sessions 테이블 없음

@router.websocket("/ws/{session_id}")
async def websocket_chat(..., session_mgr: SessionManager = Depends(get_session_manager)):
    if not await session_mgr.validate_session(session_id):  # ❌ sessions 테이블 없음
        ...
```

---

#### **1-2. `conversation_memories` 테이블**

**삭제됨:**
```sql
-- 기존 스키마
CREATE TABLE conversation_memories (
    id UUID PRIMARY KEY,
    user_id INTEGER NOT NULL,
    query TEXT NOT NULL,
    response_summary TEXT NOT NULL,
    relevance VARCHAR(20),
    session_id VARCHAR(100),  -- chat_sessions 참조
    intent_detected VARCHAR(100),
    entities_mentioned JSONB,
    created_at TIMESTAMP,
    conversation_metadata JSONB
);
```

**영향받는 파일:**
| 파일 | 클래스/함수 | 의존도 | 상태 |
|------|------------|--------|------|
| `app/service_agent/foundation/memory_service.py` | `LongTermMemoryService` | **높음** | ❌ 작동 불가 |
| `app/models/memory.py` | `ConversationMemory` 모델 | **높음** | ❌ 작동 불가 |
| `app/api/chat_api.py` | `/memory/history` 엔드포인트 | 중간 | ⚠️ 수정 필요 |

**LongTermMemoryService 주요 메서드:**
```python
# memory_service.py
async def load_recent_memories(user_id, limit=5):  # ❌ conversation_memories 없음
    query = select(ConversationMemory).where(...)

async def save_conversation(user_id, query, response_summary, ...):  # ❌ conversation_memories 없음
    new_memory = ConversationMemory(...)
    self.db.add(new_memory)
```

---

#### **1-3. `entity_memories` 테이블**

**삭제됨:**
```sql
-- 기존 스키마
CREATE TABLE entity_memories (
    id UUID PRIMARY KEY,
    user_id INTEGER NOT NULL,
    entity_type VARCHAR(50),
    entity_id VARCHAR(100),
    entity_name VARCHAR(200),
    mention_count INTEGER DEFAULT 1,
    first_mentioned_at TIMESTAMP,
    last_mentioned_at TIMESTAMP,
    entity_context JSONB
);
```

**영향받는 파일:**
| 파일 | 클래스/함수 | 의존도 | 상태 |
|------|------------|--------|------|
| `app/service_agent/foundation/memory_service.py` | `_update_entity_tracking()` | 중간 | ❌ 작동 불가 |
| `app/models/memory.py` | `EntityMemory` 모델 | 중간 | ❌ 작동 불가 |

---

#### **1-4. `user_preferences` 테이블**

**삭제됨:**
```sql
-- 기존 스키마
CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,
    preferences JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**영향받는 파일:**
| 파일 | 클래스/함수 | 의존도 | 상태 |
|------|------------|--------|------|
| `app/service_agent/foundation/memory_service.py` | `get_user_preferences()`, `update_user_preferences()` | 낮음 | ❌ 작동 불가 |
| `app/models/memory.py` | `UserPreference` 모델 | 낮음 | ❌ 작동 불가 |

---

### 2. 새 스키마 (Clean Migration 후)

#### **2-1. `chat_sessions` 테이블**

```sql
CREATE TABLE chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,  -- ✅ thread_id로도 사용
    user_id INTEGER NOT NULL DEFAULT 1,
    title VARCHAR(200) NOT NULL DEFAULT '새 대화',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**특징:**
- GPT-style 대화 스레드 관리
- `session_id` = LangGraph `thread_id` (통일!)
- `user_id` 기본값 1 (인증 미구현)

---

#### **2-2. `chat_messages` 테이블**

```sql
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**특징:**
- 메시지 히스토리 저장 (UI 표시용)
- `session_id`로 chat_sessions와 연결
- `role`: user, assistant, system

---

#### **2-3. Checkpoint Tables (4개)**

```sql
-- LangGraph 상태 저장용 (자동 생성)
CREATE TABLE checkpoints (session_id TEXT, ...);
CREATE TABLE checkpoint_blobs (session_id TEXT, ...);
CREATE TABLE checkpoint_writes (session_id TEXT, ...);
CREATE TABLE checkpoint_migrations (v INTEGER, ...);
```

**특징:**
- ✅ 모두 `session_id` 사용 (thread_id 제거!)
- LangGraph가 자동 관리
- 우리가 직접 조작할 필요 없음

---

## 🚨 Critical Issues

### Issue 1: SessionManager 완전 파괴

**문제:**
```python
# chat_api.py:69
@router.post("/start")
async def start_session(session_mgr: SessionManager = Depends(get_session_manager)):
    session_id, expires_at = await session_mgr.create_session(...)  # ❌ sessions 테이블 없음
```

**에러 예상:**
```
sqlalchemy.exc.ProgrammingError: (psycopg.errors.UndefinedTable)
relation "sessions" does not exist
```

**영향:**
- WebSocket 연결 불가
- 세션 생성/검증 불가
- 전체 채팅 기능 마비

---

### Issue 2: LongTermMemoryService 완전 파괴

**문제:**
```python
# memory_service.py:29
async def load_recent_memories(user_id, limit=5):
    query = select(ConversationMemory).where(...)  # ❌ conversation_memories 테이블 없음
```

**에러 예상:**
```
sqlalchemy.exc.ProgrammingError: (psycopg.errors.UndefinedTable)
relation "conversation_memories" does not exist
```

**영향:**
- 대화 기록 로드 불가
- `/memory/history` 엔드포인트 500 에러
- Long-term memory 기능 완전 상실

---

### Issue 3: Model 정의 불일치

**문제:**
```python
# models/memory.py:23
class ConversationMemory(Base):
    __tablename__ = "conversation_memories"  # ❌ 존재하지 않는 테이블

# models/session.py:13
class Session(Base):
    __tablename__ = "sessions"  # ❌ 존재하지 않는 테이블
```

**영향:**
- SQLAlchemy 메타데이터 오류
- Import 시 경고 발생 가능
- 다른 코드에 영향

---

## ✅ Solution Plan

### Phase 1: 긴급 수정 (필수)

#### **1-1. SessionManager 대체**

**옵션 A: 메모리 기반으로 전환 (추천)**

```python
# app/api/memory_session_manager.py (새 파일)

class InMemorySessionManager:
    """
    메모리 기반 세션 관리 (간단한 대안)

    WebSocket 연결 중에만 유효한 세션
    재시작 시 세션 소실 (현재는 문제 없음)
    """
    def __init__(self):
        self._sessions: Dict[str, Dict] = {}

    async def create_session(self, user_id=None, metadata=None):
        session_id = f"session-{uuid.uuid4()}"
        expires_at = datetime.now() + timedelta(hours=24)

        self._sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now(),
            "expires_at": expires_at,
            "metadata": metadata or {}
        }

        return session_id, expires_at

    async def validate_session(self, session_id: str) -> bool:
        if session_id not in self._sessions:
            return False

        session = self._sessions[session_id]
        if datetime.now() > session["expires_at"]:
            del self._sessions[session_id]
            return False

        return True

    # ... 기타 메서드 간소화
```

**장점:**
- 빠른 구현 (DB 없이)
- sessions 테이블 불필요
- 현재 요구사항 충족

**단점:**
- 재시작 시 세션 소실
- 나중에 인증 구현 시 다시 수정 필요

---

**옵션 B: chat_sessions 재사용 (장기 해결책)**

```python
# app/api/chat_session_manager.py (새 파일)

class ChatSessionManager:
    """
    chat_sessions 테이블을 세션 관리에도 사용

    GPT-style 대화 = 세션
    session_id 통일
    """
    async def create_session(self, user_id=1, metadata=None):
        session_id = f"chat_{uuid.uuid4()}"

        async with AsyncSessionLocal() as db:
            new_session = ChatSession(
                session_id=session_id,
                user_id=user_id,
                title="새 대화"
            )
            db.add(new_session)
            await db.commit()

        return session_id, datetime.now() + timedelta(hours=24)

    async def validate_session(self, session_id: str) -> bool:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ChatSession).where(ChatSession.session_id == session_id)
            )
            return result.scalar_one_or_none() is not None
```

**장점:**
- 스키마에 맞춤
- 영구 저장
- session_id 통일

**단점:**
- chat_sessions가 "대화 스레드"와 "HTTP 세션" 역할 동시 수행
- 개념적 혼란 가능

---

#### **1-2. LongTermMemoryService 대체**

**옵션 A: chat_messages 기반 메모리 서비스 (추천)**

```python
# app/service_agent/foundation/simple_memory_service.py (새 파일)

class SimpleMemoryService:
    """
    chat_messages 테이블 기반 간단한 메모리 서비스

    conversation_memories 대체
    """
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def load_recent_messages(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        최근 메시지 로드 (chat_messages 기반)

        Args:
            session_id: chat_session_id
            limit: 로드할 메시지 수

        Returns:
            List[Dict]: 메시지 리스트
        """
        query = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        messages = result.scalars().all()

        return [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat()
            }
            for msg in reversed(messages)  # 시간순 정렬
        ]

    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> bool:
        """
        메시지 저장

        Args:
            session_id: chat_session_id
            role: 'user' | 'assistant' | 'system'
            content: 메시지 내용

        Returns:
            성공 여부
        """
        try:
            new_message = ChatMessage(
                session_id=session_id,
                role=role,
                content=content
            )

            self.db.add(new_message)
            await self.db.commit()

            logger.info(f"Saved message for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            await self.db.rollback()
            return False

    async def get_conversation_history(
        self,
        session_id: str
    ) -> List[Dict[str, str]]:
        """
        대화 히스토리 조회 (LLM 프롬프트용)

        Returns:
            [{"role": "user", "content": "..."}, ...]
        """
        messages = await self.load_recent_messages(session_id, limit=50)

        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]
```

**장점:**
- 새 스키마에 완벽히 호환
- 간단하고 명확
- conversation_memories 기능 대부분 커버

**단점:**
- intent_detected, entities_mentioned 등 메타데이터 저장 불가
- relevance 필터링 불가

---

**옵션 B: 나중에 필요하면 conversation_memories 재추가**

```sql
-- 향후 필요 시 테이블 재생성
CREATE TABLE conversation_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(100) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    summary TEXT NOT NULL,  -- 대화 요약
    intent VARCHAR(100),
    entities JSONB,
    relevance VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**특징:**
- chat_messages: 원본 메시지 (UI용)
- conversation_summaries: 요약 + 메타데이터 (검색/분석용)
- 선택적 구현 (지금은 불필요)

---

### Phase 2: 모델 정리

#### **2-1. 삭제할 파일/코드**

```bash
# 삭제 또는 주석 처리
backend/app/models/memory.py         # ConversationMemory, EntityMemory, UserPreference
backend/app/models/session.py        # Session (HTTP)
backend/app/api/session_manager.py   # SessionManager (PostgreSQL 기반)
backend/app/service_agent/foundation/memory_service.py  # LongTermMemoryService
```

---

#### **2-2. 유지할 파일**

```bash
# 유지
backend/app/models/chat.py           # ChatSession, ChatMessage (새 스키마)
backend/app/models/users.py          # User (변경 없음)
backend/app/api/chat_api.py          # 수정 필요
```

---

### Phase 3: API 엔드포인트 수정

#### **3-1. `/memory/history` 수정**

**Before:**
```python
# chat_api.py:440
@router.get("/memory/history")
async def get_memory_history(limit: int = 10):
    memory_service = LongTermMemoryService(db_session)
    memories = await memory_service.load_recent_memories(user_id=1, limit=limit)
    # ❌ conversation_memories 테이블 없음
```

**After:**
```python
# chat_api.py
@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, limit: int = 50):
    """
    특정 세션의 메시지 히스토리 조회

    Args:
        session_id: chat_session_id
        limit: 조회할 메시지 수

    Returns:
        메시지 리스트
    """
    async for db in get_async_db():
        memory_service = SimpleMemoryService(db)

        messages = await memory_service.load_recent_messages(
            session_id=session_id,
            limit=limit
        )

        return {
            "session_id": session_id,
            "count": len(messages),
            "messages": messages
        }
```

---

#### **3-2. 세션 생성/검증 수정**

**Before:**
```python
# chat_api.py:67
@router.post("/start")
async def start_session(session_mgr: SessionManager = Depends(get_session_manager)):
    session_id, expires_at = await session_mgr.create_session(...)
    # ❌ sessions 테이블 없음
```

**After (Option A - 메모리 기반):**
```python
@router.post("/start")
async def start_session():
    """
    새 채팅 세션 시작

    Returns:
        session_id와 생성 정보
    """
    session_id = f"chat_{uuid.uuid4()}"

    async for db in get_async_db():
        new_session = ChatSession(
            session_id=session_id,
            user_id=1,  # 임시 하드코딩
            title="새 대화"
        )
        db.add(new_session)
        await db.commit()

        return {
            "session_id": session_id,
            "created_at": datetime.now().isoformat()
        }
```

**After (Option B - 메모리 세션 관리자):**
```python
from app.api.memory_session_manager import get_in_memory_session_manager

@router.post("/start")
async def start_session(
    session_mgr: InMemorySessionManager = Depends(get_in_memory_session_manager)
):
    session_id, expires_at = await session_mgr.create_session(user_id=1)
    return {"session_id": session_id, "expires_at": expires_at.isoformat()}
```

---

## 📋 Implementation Checklist

### Phase 1: 긴급 수정 (Day 1-2)

- [ ] **1-1. 새 파일 생성**
  - [ ] `app/api/memory_session_manager.py` (InMemorySessionManager)
  - [ ] `app/service_agent/foundation/simple_memory_service.py` (SimpleMemoryService)

- [ ] **1-2. chat_api.py 수정**
  - [ ] SessionManager → InMemorySessionManager 교체
  - [ ] LongTermMemoryService → SimpleMemoryService 교체
  - [ ] `/memory/history` → `/sessions/{id}/messages`로 변경
  - [ ] `_process_query_async`에서 메시지 저장 추가

- [ ] **1-3. 테스트**
  - [ ] `/start` 엔드포인트 동작 확인
  - [ ] WebSocket 연결 테스트
  - [ ] 메시지 저장/로드 확인

---

### Phase 2: 코드 정리 (Day 3-4)

- [ ] **2-1. 파일 이동/삭제**
  - [ ] `models/memory.py` → `old/` 이동
  - [ ] `models/session.py` → `old/` 이동
  - [ ] `api/session_manager.py` → `old/` 이동
  - [ ] `service_agent/foundation/memory_service.py` → `old/` 이동

- [ ] **2-2. Import 정리**
  - [ ] 삭제된 모델 import 제거
  - [ ] 새 서비스 import 추가

- [ ] **2-3. 문서 업데이트**
  - [ ] API 문서 업데이트
  - [ ] README 수정

---

### Phase 3: 선택적 개선 (Day 5+)

- [ ] **3-1. 메시지 요약 기능 (선택)**
  - [ ] LLM으로 대화 요약 생성
  - [ ] chat_sessions.metadata에 요약 저장

- [ ] **3-2. conversation_summaries 테이블 재추가 (필요 시)**
  - [ ] 마이그레이션 스크립트 작성
  - [ ] 요약 저장 로직 구현

- [ ] **3-3. 인증 시스템 연동 (장기)**
  - [ ] user_id 하드코딩 제거
  - [ ] 실제 로그인 세션 연동

---

## 🎯 Expected Outcome

### Before (Migration 전)

```
✅ sessions 테이블 존재
✅ conversation_memories 존재
✅ SessionManager 작동
✅ LongTermMemoryService 작동
```

### After (수정 완료 후)

```
✅ chat_sessions + chat_messages 사용
✅ InMemorySessionManager 작동
✅ SimpleMemoryService 작동
✅ 메시지 저장/로드 가능
✅ 대화 이어가기 가능
```

---

## 🚨 Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| API 호환성 깨짐 | 높음 | 높음 | 점진적 마이그레이션, 테스트 강화 |
| 기존 대화 기록 소실 | 중간 | 중간 | 백업 확인 (이미 clean migration 실행됨) |
| 성능 저하 | 낮음 | 낮음 | chat_messages에 인덱스 존재 |
| 메모리 세션 소실 | 중간 | 낮음 | 재시작 시 재연결 (WebSocket 특성상 정상) |

---

## 📝 Notes

1. **user_id=1 하드코딩**
   - 현재 인증 미구현
   - 모든 사용자가 user_id=1로 저장됨
   - 추후 인증 구현 시 수정 필요

2. **LongGraph checkpoint 영향 없음**
   - checkpoint 테이블은 LangGraph가 자동 관리
   - session_id로 통일되어 문제 없음

3. **향후 확장성**
   - conversation_summaries 테이블 추가 가능
   - entity_memories 재추가 가능
   - 현재는 최소 구성으로 충분

---

## 🔗 Related Documents

- [Clean Migration README](../../../migrations/CLEAN_MIGRATION_README.md)
- [Simplified Schema](../../../migrations/simplified_schema_unified.dbml)
- [Schema Simplification Summary](../../../migrations/SCHEMA_SIMPLIFICATION_SUMMARY.md)

---

**Last Updated**: 2025-10-15
**Status**: Planning Phase
**Next Action**: Phase 1 긴급 수정 시작
