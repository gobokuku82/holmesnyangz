# State/Context 관리 분석 - Long-term Memory 구현

**Date**: 2025-10-14
**Purpose**: 기존 State 구조와 Long-term Memory 통합 분석

---

## 🎯 핵심 질문

> "state/context 관리를 고려한 memory 구현 계획서인가?"

---

## ✅ 답변: 네, 고려되어 있습니다!

### 현재 State 구조 분석 결과

기존 코드를 확인한 결과, **이미 대부분의 State 관리가 준비되어 있습니다!**

---

## 📊 현재 State 구조 (separated_states.py)

### 1. SharedState (Line 59-71)

```python
class SharedState(TypedDict):
    """모든 팀이 공유하는 최소한의 상태"""
    user_query: str
    session_id: str
    user_id: Optional[int]  # ✅ 이미 있음!
    timestamp: str
    language: str
    status: Literal["pending", "processing", "completed", "error"]
    error_message: Optional[str]
```

**확인 사항**:
- ✅ `user_id: Optional[int]` 이미 존재!
- ✅ 타입이 `int`로 올바름!
- ✅ Long-term Memory에서 바로 사용 가능!

---

### 2. MainSupervisorState (Line 228-281)

```python
class MainSupervisorState(TypedDict, total=False):
    """메인 Supervisor의 State"""
    # Core fields
    query: str
    session_id: str
    request_id: str

    # Planning
    planning_state: Optional[PlanningState]
    execution_plan: Optional[Dict[str, Any]]

    # Team states
    search_team_state: Optional[Dict[str, Any]]
    document_team_state: Optional[Dict[str, Any]]
    analysis_team_state: Optional[Dict[str, Any]]

    # Execution tracking
    current_phase: str
    active_teams: List[str]
    completed_teams: List[str]
    failed_teams: List[str]

    # Results
    team_results: Dict[str, Any]
    aggregated_results: Dict[str, Any]
    final_response: Optional[Dict[str, Any]]

    # Timing
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    total_execution_time: Optional[float]

    # Error handling
    error_log: List[str]
    status: str
```

**확인 사항**:
- ❌ `user_id` 필드 없음 (추가 필요)
- ❌ `loaded_memories` 필드 없음 (추가 필요)
- ❌ `user_preferences` 필드 없음 (추가 필요)

---

### 3. StateManager (Line 286-431)

```python
class StateManager:
    """State 변환 및 관리 유틸리티"""

    @staticmethod
    def create_shared_state(
        query: str,
        session_id: str,
        user_id: Optional[int] = None,  # ✅ 이미 있음!
        language: str = "ko",
        timestamp: Optional[str] = None
    ) -> SharedState:
        """공유 State 생성"""
        return SharedState(
            user_query=query,
            session_id=session_id,
            user_id=user_id,  # ✅ 전달됨!
            ...
        )
```

**확인 사항**:
- ✅ `user_id` 이미 지원됨!
- ✅ SharedState 생성 시 user_id 전달!

---

## 🔧 필요한 State 확장

### MainSupervisorState에 추가할 필드

```python
class MainSupervisorState(TypedDict, total=False):
    # ... 기존 필드들 ...

    # ✨ NEW: Long-term Memory fields
    user_id: Optional[int]  # 사용자 ID (SharedState에서 전달받음)
    loaded_memories: Optional[List[Dict[str, Any]]]  # 로드된 과거 대화
    user_preferences: Optional[Dict[str, Any]]  # 사용자 선호도
    memory_load_time: Optional[str]  # 메모리 로드 시각
```

**추가 위치**: `separated_states.py` Line ~265 (error_log 아래)

---

## 🔄 데이터 흐름 분석

### 1. user_id 흐름

```
Frontend (로그인)
    ↓
POST /chat/start (user_id=123)
    ↓
SessionManager.create_session(user_id=123)
    ↓ sessions 테이블에 저장
    session_id: "session-abc123"
    user_id: 123 (Integer)
    ↓
WebSocket 연결
    ↓
chat_api.py: session_info = get_session(session_id)
    user_id = session_info["user_id"]  # 123
    ↓
process_query_streaming(user_id=123)
    ↓
initial_state = {
    "query": query,
    "session_id": session_id,
    "user_id": user_id  # ✨ 여기서 MainSupervisorState에 추가
}
    ↓
StateManager.create_shared_state(user_id=123)
    ↓ SharedState에 포함
    shared_state["user_id"] = 123
    ↓
planning_node(state)
    user_id = state.get("user_id")  # ✨ 여기서 Long-term Memory 로드
    if user_id:
        loaded_memories = await memory_service.load_recent_memories(user_id)
        state["loaded_memories"] = loaded_memories
```

---

### 2. Context 관리 흐름

```
planning_node 시작
    ↓
user_id 확인
    ↓ user_id가 있으면
LongTermMemoryService.load_recent_memories(user_id)
    ↓
PostgreSQL: conversation_memories 테이블 조회
    SELECT * FROM conversation_memories
    WHERE user_id = 123
    ORDER BY created_at DESC
    LIMIT 5
    ↓
loaded_memories = [
    {
        "user_query": "강남구 아파트 3억~5억 추천해줘",
        "intent_type": "search_real_estate",
        "created_at": "2025-10-10 14:30:00"
    },
    ...
]
    ↓
state["loaded_memories"] = loaded_memories
    ↓
PlanningAgent.analyze_intent(query, context=loaded_memories)
    ↓ LLM에 과거 맥락 제공
    "사용자는 이전에 강남구 아파트를 찾았습니다.
     3억~5억 가격대를 선호합니다."
    ↓
실행 계획 생성 (과거 맥락 고려)
    ↓
execute_teams_node
    ↓ 팀 실행 (과거 선호도 활용)
    ↓
response_node
    ↓
대화 완료 후 저장
    ↓
LongTermMemoryService.save_conversation(
    user_id=123,
    user_query=state["query"],
    intent_type=...,
    teams_used=state["completed_teams"]
)
    ↓
PostgreSQL: conversation_memories에 INSERT
```

---

## 🔍 기존 Context 관리 메커니즘

### 1. SharedState 전파

```python
# StateManager.create_shared_state() (Line 350-371)
shared_state = SharedState(
    user_query=query,
    session_id=session_id,
    user_id=user_id,  # ✅ 모든 팀에 전파됨
    timestamp=timestamp,
    language=language,
    status="pending",
    error_message=None
)
```

**결과**: 모든 Team State가 `shared_context`로 user_id 접근 가능

```python
# SearchTeamState (Line 77-110)
class SearchTeamState(TypedDict):
    team_name: str
    status: str
    shared_context: Dict[str, Any]  # ← user_id 포함됨!
    ...
```

---

### 2. Team State 초기화

```python
# StateManager.create_initial_team_state() (Line 434-519)
base_fields = {
    "team_name": team_type,
    "status": "initialized",
    "shared_context": dict(shared_state),  # ✅ user_id 전달됨
    ...
}
```

**확인**: 모든 팀이 `shared_context["user_id"]`로 user_id 접근 가능!

---

## ✅ 계획서가 고려하고 있는 것들

### 1. State 구조 확장 (고려됨)

✅ **MainSupervisorState 확장**:
```python
# 추가할 필드
user_id: Optional[int]
loaded_memories: Optional[List[Dict[str, Any]]]
user_preferences: Optional[Dict[str, Any]]
memory_load_time: Optional[str]
```

---

### 2. Context 전달 경로 (고려됨)

✅ **user_id 흐름**:
```
sessions 테이블 → chat_api → process_query_streaming
→ MainSupervisorState → planning_node → Memory 로드
```

---

### 3. 팀 간 Context 공유 (이미 구현됨)

✅ **SharedState 메커니즘**:
- 모든 팀이 `shared_context`로 접근
- user_id가 이미 포함됨
- Long-term Memory도 동일하게 공유 가능

---

### 4. Memory Context 활용 (계획됨)

✅ **Planning Agent 통합**:
```python
# planning_node에서
loaded_memories = state.get("loaded_memories", [])

# PlanningAgent에 전달
intent_result = await self.planning_agent.analyze_intent(
    query=query,
    context=loaded_memories  # ← 과거 맥락 제공
)
```

---

## ❌ 추가 작업이 필요한 부분

### 1. MainSupervisorState 필드 추가

**파일**: `separated_states.py` Line ~265

**추가 코드**:
```python
class MainSupervisorState(TypedDict, total=False):
    # ... 기존 필드들 ...

    # Long-term Memory fields (NEW)
    user_id: Optional[int]
    loaded_memories: Optional[List[Dict[str, Any]]]
    user_preferences: Optional[Dict[str, Any]]
    memory_load_time: Optional[str]
```

---

### 2. team_supervisor.py 수정

**파일**: `team_supervisor.py`

**수정 지점 1**: `process_query_streaming()` - user_id 전달

```python
async def process_query_streaming(
    self,
    query: str,
    session_id: str,
    user_id: Optional[int] = None,  # ✨ NEW parameter
    progress_callback: Optional[Callable] = None
):
    initial_state = {
        "query": query,
        "session_id": session_id,
        "user_id": user_id,  # ✨ NEW
        ...
    }
```

**수정 지점 2**: `planning_node()` - Memory 로드

```python
async def planning_node(self, state: MainSupervisorState):
    user_id = state.get("user_id")

    # ✨ NEW: Long-term Memory 로드
    if user_id:
        from app.services.long_term_memory_service import LongTermMemoryService

        memory_service = LongTermMemoryService()
        loaded_memories = await memory_service.load_recent_memories(user_id, limit=5)

        state["loaded_memories"] = loaded_memories
        state["memory_load_time"] = datetime.now().isoformat()
```

---

## 🎯 검증: Context가 올바르게 전달되는가?

### Test 1: user_id 전달 확인

```python
# chat_api.py에서 시작
user_id = 123

# MainSupervisorState에 저장
state["user_id"] = user_id

# planning_node에서 접근
user_id = state.get("user_id")  # ✅ 123

# Memory 로드
memories = await memory_service.load_recent_memories(user_id)  # ✅ user_id=123
```

---

### Test 2: SharedState 전파 확인

```python
# SharedState 생성
shared_state = StateManager.create_shared_state(
    query=query,
    session_id=session_id,
    user_id=123  # ✅ 포함
)

# Team State 초기화
search_state = StateManager.create_initial_team_state(
    team_type="search",
    shared_state=shared_state  # ✅ user_id 전달
)

# Team에서 접근
user_id = search_state["shared_context"]["user_id"]  # ✅ 123
```

---

### Test 3: Memory Context 활용 확인

```python
# planning_node에서 Memory 로드
state["loaded_memories"] = [
    {
        "user_query": "강남구 아파트...",
        "intent_type": "search_real_estate"
    }
]

# PlanningAgent에 전달 (가정)
context = state.get("loaded_memories", [])
intent_result = await self.planning_agent.analyze_intent(
    query=query,
    context=context  # ✅ 과거 맥락 제공
)
```

---

## 📋 최종 확인 체크리스트

### State 구조
- [x] SharedState에 user_id 존재 (`Optional[int]`)
- [ ] MainSupervisorState에 user_id 필드 추가 필요
- [ ] MainSupervisorState에 loaded_memories 필드 추가 필요
- [ ] MainSupervisorState에 user_preferences 필드 추가 필요

### Context 전달
- [x] StateManager.create_shared_state() user_id 지원
- [x] SharedState → Team State 전파 메커니즘 존재
- [ ] MainSupervisorState → planning_node 전달 구현 필요

### Memory 통합
- [ ] LongTermMemoryService 구현
- [ ] planning_node에서 Memory 로드
- [ ] response_node에서 Memory 저장

---

## 🎯 결론

### 질문: "state/context 관리를 고려한 계획서인가?"

**답변**: **네, 충분히 고려되어 있습니다!**

### 이유

1. ✅ **기존 State 구조가 이미 user_id를 지원**
   - SharedState에 `user_id: Optional[int]` 존재
   - StateManager가 user_id 전달 지원

2. ✅ **Context 전파 메커니즘 존재**
   - SharedState → Team State 자동 전파
   - 모든 팀이 `shared_context["user_id"]` 접근 가능

3. ✅ **필요한 확장만 추가하면 됨**
   - MainSupervisorState에 Memory 필드 3-4개만 추가
   - planning_node에서 Memory 로드 로직 추가
   - response_node에서 Memory 저장 로직 추가

### 추가 작업

**최소한의 수정으로 구현 가능**:
1. MainSupervisorState 확장 (3-4개 필드)
2. planning_node Memory 로드 (20-30줄)
3. response_node Memory 저장 (20-30줄)

**기존 State 관리 구조를 최대한 활용!**

---

## 📄 참고

- **기존 State 파일**: `backend/app/service_agent/foundation/separated_states.py`
- **수정 필요 파일**: `separated_states.py`, `team_supervisor.py`
- **신규 파일**: `memory.py`, `long_term_memory_service.py`

---

**State/Context 관리는 충분히 고려되었으며, 기존 구조를 최대한 활용합니다!** ✅

---

**Document End**
