# Long-term Memory 구현 계획서 (최종)

**Version**: 1.0 Final
**Date**: 2025-10-14
**Location**: backend/app/reports/long_term_memory/
**Status**: Ready to Start

---

## 📋 Executive Summary

### 목표
사용자별 대화 기록을 영구 저장하고, 다음 대화 시 과거 맥락을 제공하여 개인화된 AI 응답 생성

### 완료된 작업
- ✅ **Task 1**: sessions.user_id 타입 수정 (String → Integer)

### 남은 작업
- 🔜 **Task 2**: Memory 모델 생성 (2시간)
- 🔜 **Task 3**: LongTermMemoryService 구현 (4-5시간)
- 🔜 **Task 4**: Workflow 통합 (3-4시간)
- 🔜 **Task 5**: Frontend UI (4-5시간)

**총 예상 시간**: 13-16시간 (약 2-3일)

---

## 🎯 Task 2: Memory 모델 생성

### 소요 시간
약 2시간 (코드 복사-붙여넣기)

### 생성할 파일
`backend/app/models/memory.py` (신규 생성)

### 모델 구조

#### 1. ConversationMemory (대화 기록)
```python
class ConversationMemory(Base):
    """대화 기록 영구 저장"""
    __tablename__ = "conversation_memories"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Key
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(100), nullable=True)

    # 대화 내용
    user_query = Column(Text, nullable=False)
    assistant_response_summary = Column(Text, nullable=True)
    conversation_summary = Column(Text, nullable=True)

    # 분류
    intent_type = Column(String(50), nullable=True, index=True)
    intent_confidence = Column(Float, nullable=True)

    # 실행 정보
    teams_used = Column(JSONB, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    entities_mentioned = Column(JSONB, nullable=True)

    # 타임스탬프
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="conversation_memories")

    # Indexes
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_user_intent', 'user_id', 'intent_type'),
    )
```

#### 2. UserPreference (사용자 선호도)
```python
class UserPreference(Base):
    """사용자 선호도 추적"""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # 선호도 데이터
    preferred_regions = Column(JSONB, nullable=True)
    preferred_property_types = Column(JSONB, nullable=True)
    price_range = Column(JSONB, nullable=True)
    area_range = Column(JSONB, nullable=True)
    search_history_summary = Column(JSONB, nullable=True)

    # 통계
    interaction_count = Column(Integer, default=0, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    last_updated = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="preferences")
```

#### 3. EntityMemory (엔티티 추적)
```python
class EntityMemory(Base):
    """엔티티 추적 (매물, 지역, 중개사)"""
    __tablename__ = "entity_memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 엔티티 정보
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(String(100), nullable=False, index=True)
    entity_name = Column(String(200), nullable=True)

    # 추적 정보
    last_mentioned = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    mention_count = Column(Integer, default=1, nullable=False)
    context_summary = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="entity_memories")

    __table_args__ = (
        Index('idx_user_entity', 'user_id', 'entity_type', 'entity_id'),
        Index('idx_user_last_mentioned', 'user_id', 'last_mentioned'),
    )
```

### 작업 순서

#### Step 1: memory.py 파일 생성
```bash
# 파일 위치
backend/app/models/memory.py
```

#### Step 2: Import 추가
```python
from sqlalchemy import (
    Column, Integer, String, Text, TIMESTAMP, ForeignKey, Index, Float
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.postgre_db import Base
import uuid
```

#### Step 3: 3개 모델 클래스 작성
- ConversationMemory
- UserPreference
- EntityMemory

#### Step 4: User 모델에 Relationship 추가

**파일**: `backend/app/models/users.py`

```python
class User(Base):
    # ... 기존 필드들 ...

    # Relationships (기존)
    profile = relationship("UserProfile", ...)
    chat_sessions = relationship("ChatSession", ...)

    # ✨ NEW: Long-term Memory relationships
    conversation_memories = relationship("ConversationMemory", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    entity_memories = relationship("EntityMemory", back_populates="user", cascade="all, delete-orphan")
```

#### Step 5: 테이블 생성
```bash
# 서버 시작 시 자동 생성
cd backend
uvicorn app.main:app --reload
```

#### Step 6: 확인
```bash
psql "postgresql://postgres:root1234@localhost:5432/real_estate" << EOF
\dt conversation_memories
\dt user_preferences
\dt entity_memories
\q
EOF
```

**예상 출력**:
```
conversation_memories | table | postgres
user_preferences      | table | postgres
entity_memories       | table | postgres
```

---

## 🎯 Task 3: LongTermMemoryService 구현

### 소요 시간
약 4-5시간

### 생성할 파일
`backend/app/services/long_term_memory_service.py` (신규 생성)

### 핵심 메서드

#### 1. 메모리 로드 (Planning Node에서 사용)
```python
async def load_recent_memories(
    self,
    user_id: int,
    limit: int = 5,
    intent_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """최근 대화 기록 로드"""
    # conversation_memories 테이블에서 조회
    # ORDER BY created_at DESC
    # LIMIT 5
```

#### 2. 선호도 조회
```python
async def get_user_preferences(
    self,
    user_id: int
) -> Optional[Dict[str, Any]]:
    """사용자 선호도 조회"""
    # user_preferences 테이블에서 조회
```

#### 3. 대화 저장 (Response Node에서 사용)
```python
async def save_conversation(
    self,
    user_id: int,
    session_id: str,
    user_query: str,
    assistant_response_summary: Optional[str],
    conversation_summary: Optional[str],
    intent_type: Optional[str],
    intent_confidence: Optional[float],
    teams_used: Optional[List[str]],
    entities_mentioned: Optional[Dict[str, Any]],
    execution_time_ms: Optional[int]
) -> bool:
    """대화 기록 저장"""
    # conversation_memories에 INSERT
    # entity_memories 업데이트
```

#### 4. 선호도 업데이트
```python
async def update_user_preferences(
    self,
    user_id: int,
    regions: Optional[List[str]] = None,
    property_types: Optional[List[str]] = None,
    price_range: Optional[Dict[str, int]] = None,
    area_range: Optional[Dict[str, int]] = None
) -> bool:
    """사용자 선호도 업데이트 (점진적 학습)"""
    # user_preferences UPSERT
```

---

## 🎯 Task 4: Workflow 통합

### 소요 시간
약 3-4시간

### 수정할 파일

#### 1. chat_api.py (user_id 추출)

**위치**: `backend/app/api/chat_api.py`

**수정 지점**: `websocket_chat()` 함수

```python
# ✨ NEW: user_id 추출
session_info = await session_mgr.get_session(session_id)
user_id = session_info.get("user_id") if session_info else None

# Query 처리
asyncio.create_task(
    _process_query_async(
        supervisor=supervisor,
        query=query,
        session_id=session_id,
        user_id=user_id,  # ✨ NEW
        ...
    )
)
```

#### 2. team_supervisor.py (planning_node)

**위치**: `backend/app/service_agent/supervisor/team_supervisor.py`

**수정 지점**: `planning_node()` 함수

```python
async def planning_node(self, state: MainSupervisorState):
    """계획 수립 노드"""

    user_id = state.get("user_id")

    # ✨ NEW: Long-term Memory 로드
    if user_id:
        from app.services.long_term_memory_service import LongTermMemoryService

        memory_service = LongTermMemoryService()

        # 최근 대화 로드
        loaded_memories = await memory_service.load_recent_memories(
            user_id=user_id,
            limit=5
        )

        # 선호도 로드
        user_preferences = await memory_service.get_user_preferences(user_id)

        # State에 저장
        state["loaded_memories"] = loaded_memories
        state["user_preferences"] = user_preferences

        # Progress callback
        await self._send_progress("memory_loaded", {
            "user_id": user_id,
            "memory_count": len(loaded_memories)
        })

    # 기존 planning 로직 계속...
```

#### 3. team_supervisor.py (response_node)

**수정 지점**: 대화 완료 후 저장

```python
# ✨ NEW: Long-term Memory 저장
user_id = state.get("user_id")
if user_id:
    await memory_service.save_conversation(
        user_id=user_id,
        session_id=state.get("session_id"),
        user_query=state.get("query"),
        assistant_response_summary=self._summarize_response(state),
        intent_type=intent_info.get("intent_type"),
        teams_used=state.get("completed_teams", []),
        entities_mentioned=self._extract_entities(state),
        execution_time_ms=execution_time_ms
    )
```

#### 4. separated_states.py (MainSupervisorState 확장)

```python
class MainSupervisorState(TypedDict, total=False):
    # ... 기존 필드들 ...

    # ✨ NEW: Long-term Memory fields
    user_id: Optional[int]
    loaded_memories: Optional[List[Dict[str, Any]]]
    user_preferences: Optional[Dict[str, Any]]
    memory_load_time: Optional[str]
```

---

## 🎯 Task 5: Frontend UI

### 소요 시간
약 4-5시간

### 생성할 파일

#### 1. ConversationHistory.tsx
```typescript
// 과거 대화 목록 표시
// GET /api/v1/memory/conversations?user_id={user_id}
```

#### 2. MemoryLoadedIndicator.tsx
```typescript
// 메모리 로드 상태 표시
// "📚 5 past conversations loaded"
```

#### 3. memory_api.py (Backend)
```python
# GET /api/v1/memory/conversations
# GET /api/v1/memory/preferences
# GET /api/v1/memory/statistics
```

#### 4. WebSocket Handler 수정
```typescript
case 'memory_loaded':
  console.log(`📚 Loaded ${data.memory_count} memories`);
  setMemoryLoadedState(data);
  break;
```

---

## 📊 구현 순서 및 시간 배분

| Task | 내용 | 소요 시간 | 상태 |
|------|------|-----------|------|
| Task 1 | sessions.user_id 타입 수정 | 30분 | ✅ 완료 |
| Task 2 | Memory 모델 생성 | 2시간 | 🔜 다음 |
| Task 3 | LongTermMemoryService | 4-5시간 | ⏳ 대기 |
| Task 4 | Workflow 통합 | 3-4시간 | ⏳ 대기 |
| Task 5 | Frontend UI | 4-5시간 | ⏳ 대기 |

**총 소요 시간**: 13-16시간 (2-3일)

---

## 🗂️ 파일 구조

```
backend/
├── app/
│   ├── models/
│   │   ├── memory.py                          # ✨ Task 2 (신규)
│   │   ├── users.py                           # 수정 (relationship 추가)
│   │   └── session.py                         # ✅ 완료 (user_id 타입 수정)
│   │
│   ├── services/
│   │   └── long_term_memory_service.py        # ✨ Task 3 (신규)
│   │
│   ├── api/
│   │   ├── chat_api.py                        # 수정 (user_id 추출)
│   │   └── memory_api.py                      # ✨ Task 5 (신규)
│   │
│   └── service_agent/
│       ├── foundation/
│       │   └── separated_states.py            # 수정 (State 확장)
│       │
│       └── supervisor/
│           └── team_supervisor.py             # 수정 (Memory 로드/저장)
│
└── reports/
    └── long_term_memory/
        └── IMPLEMENTATION_PLAN.md             # 📄 현재 문서
```

---

## 📋 체크리스트

### Task 1: sessions.user_id 타입 수정
- [x] models/session.py Line 26 수정
- [x] create_sessions_table.sql Line 8 수정
- [x] PostgreSQL 테이블 재생성
- [x] user_id → integer 확인

### Task 2: Memory 모델 생성
- [ ] memory.py 파일 생성
- [ ] ConversationMemory 모델 작성
- [ ] UserPreference 모델 작성
- [ ] EntityMemory 모델 작성
- [ ] User 모델에 relationship 추가
- [ ] 테이블 생성 확인 (\dt)

### Task 3: LongTermMemoryService
- [ ] long_term_memory_service.py 생성
- [ ] load_recent_memories() 구현
- [ ] get_user_preferences() 구현
- [ ] save_conversation() 구현
- [ ] update_user_preferences() 구현
- [ ] _update_entity_tracking() 구현

### Task 4: Workflow 통합
- [ ] chat_api.py user_id 추출
- [ ] _process_query_async user_id 전달
- [ ] planning_node Memory 로드
- [ ] response_node Memory 저장
- [ ] MainSupervisorState 확장

### Task 5: Frontend UI
- [ ] ConversationHistory.tsx 생성
- [ ] MemoryLoadedIndicator.tsx 생성
- [ ] memory_api.py 생성
- [ ] WebSocket handler 수정
- [ ] API endpoints 추가

---

## 🚀 시작 준비

### 현재 상태
- ✅ Task 1 완료
- ✅ 모든 코드 준비됨
- ✅ PostgreSQL 설정 완료
- ✅ 타입 불일치 해결

### 다음 작업
**Task 2: Memory 모델 생성 시작**

**파일**: `backend/app/models/memory.py`

**방법**:
1. 파일 생성
2. 코드 복사-붙여넣기
3. User 모델 relationship 추가
4. 서버 재시작
5. 테이블 생성 확인

**예상 시간**: 2시간

---

## 📚 참고 문서

이 폴더의 다른 문서들:
- 세션 vs 메모리 관계 설명
- 타입 불일치 해결 가이드
- 단계별 구현 가이드

---

**준비 완료! 시작합니다!** 🚀

---

**Document End**
