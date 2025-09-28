# CORE 모듈 상세 문서

**작성일**: 2025-09-27
**버전**: LangGraph 0.6.7 기준
**프로젝트**: beta_v003

---

## 📋 목차

1. [개요](#개요)
2. [디렉토리 구조](#디렉토리-구조)
3. [모듈별 상세 분석](#모듈별-상세-분석)
   - [__init__.py](#1-__init__py)
   - [base_agent.py](#2-base_agentpy)
   - [checkpointer.py](#3-checkpointerpy)
   - [config.py](#4-configpy)
   - [context.py](#5-contextpy)
   - [states.py](#6-statespy)
4. [핵심 개념](#핵심-개념)
5. [LangGraph 0.6.7 챗봇 개발 가이드](#langgraph-067-챗봇-개발-가이드)
6. [주의사항](#주의사항)

---

## 개요

`backend/service/core/` 모듈은 LangGraph 0.6.x Context API 기반 에이전트 시스템의 핵심 컴포넌트를 제공합니다.

### 주요 기능
- ✅ LangGraph Context API 완전 지원
- ✅ State와 Context 명확한 분리
- ✅ AsyncSqliteSaver 기반 체크포인팅
- ✅ 재사용 가능한 BaseAgent 추상 클래스
- ✅ 다양한 State 정의 (Sales, DataCollection, Analysis, Document)
- ✅ 시스템 전역 설정 관리

### 현재 상태
- ⚠️ `BaseAgent` 클래스: 임시 비활성화 (__init__.py 라인 22, 45)
- ⚠️ `get_checkpointer` 함수: 임시 비활성화 (__init__.py 라인 24, 46)

---

## 디렉토리 구조

```
backend/service/core/
├── __init__.py           # 모듈 공개 API 정의
├── base_agent.py         # BaseAgent 추상 클래스 (325줄)
├── checkpointer.py       # 체크포인트 유틸리티 (94줄)
├── config.py             # 시스템 전역 설정 (140줄)
├── context.py            # LangGraph Context 정의 (206줄)
└── states.py             # LangGraph State 정의 (267줄)
```

**총 라인 수**: 1,032줄

---

## 모듈별 상세 분석

## 1. __init__.py

### 역할
core 모듈의 공개 API를 정의하고 필요한 컴포넌트를 익스포트합니다.

### 익스포트 항목

#### States (상태 정의)
```python
from .states import (
    BaseState,              # 기본 상태
    SalesState,             # 영업 분석 상태
    DataCollectionState,    # 데이터 수집 상태
    AnalysisState,          # 분석 상태
    create_sales_initial_state,  # SalesState 초기화 함수
    merge_state_updates,    # 상태 업데이트 병합 함수
    get_state_summary       # 상태 요약 함수
)
```

#### Contexts (컨텍스트 정의)
```python
from .context import (
    AgentContext,           # 에이전트 컨텍스트
    SubgraphContext,        # 서브그래프 컨텍스트
    create_agent_context,   # AgentContext 생성 함수
    create_subgraph_context,  # SubgraphContext 생성 함수
    merge_with_config_defaults,  # Config 기본값 병합
    extract_api_keys_from_env   # 환경변수에서 API 키 추출
)
```

#### Config (설정)
```python
from .config import Config  # 시스템 전역 설정 클래스
```

#### 비활성화된 컴포넌트
```python
# from .base_agent import BaseAgent  # 라인 22 - 임시 비활성화
# from .checkpointer import get_checkpointer  # 라인 24 - 임시 비활성화
```

---

## 2. base_agent.py

### 개요
LangGraph 0.6.x Context API를 완전히 지원하는 에이전트 추상 클래스입니다.

### 클래스: `BaseAgent`

#### 초기화
```python
def __init__(self, agent_name: str, checkpoint_dir: Optional[str] = None)
```

**파라미터**:
- `agent_name` (str): 에이전트 이름
- `checkpoint_dir` (Optional[str]): 체크포인트 저장 디렉토리
  - 기본값: `checkpoints/{agent_name}`

**자동 생성 속성**:
- `self.agent_name`: 에이전트 이름
- `self.logger`: `logging.getLogger(f"agent.{agent_name}")`
- `self.checkpoint_dir`: Path 객체로 변환된 체크포인트 디렉토리
- `self.checkpointer_path`: `{checkpoint_dir}/{agent_name}.db`
- `self.workflow`: StateGraph 인스턴스 (None으로 시작)

**실행 로직**:
1. 체크포인트 디렉토리 생성 (라인 44)
2. `_build_graph()` 호출하여 워크플로우 초기화 (라인 51)

---

### 추상 메서드 (반드시 구현)

#### 1. `_get_state_schema() -> Type`
**라인**: 56-63
**목적**: 에이전트가 사용할 State TypedDict 반환

```python
@abstractmethod
def _get_state_schema(self) -> Type:
    """
    Get the state schema for this agent

    Returns:
        State schema type (TypedDict)
    """
    pass
```

**구현 예시**:
```python
def _get_state_schema(self) -> Type:
    return SalesState
```

---

#### 2. `_build_graph()`
**라인**: 65-71
**목적**: LangGraph StateGraph 생성 및 노드/엣지 정의

```python
@abstractmethod
def _build_graph(self):
    """
    Build the LangGraph workflow with context_schema
    Must call StateGraph with both state_schema and context_schema
    """
    pass
```

**구현 예시**:
```python
def _build_graph(self):
    from langgraph.graph import StateGraph
    from .context import AgentContext

    self.workflow = StateGraph(
        state_schema=self._get_state_schema(),
        context_schema=AgentContext
    )

    # 노드 추가
    self.workflow.add_node("node1", self.node1_func)
    self.workflow.add_node("node2", self.node2_func)

    # 엣지 추가
    self.workflow.add_edge("node1", "node2")
    self.workflow.set_entry_point("node1")
    self.workflow.set_finish_point("node2")
```

**중요**: 반드시 `context_schema=AgentContext` 지정 필요

---

#### 3. `_validate_input(input_data: Dict[str, Any]) -> bool`
**라인**: 73-84
**목적**: 실행 전 입력 데이터 검증

```python
@abstractmethod
async def _validate_input(self, input_data: Dict[str, Any]) -> bool:
    """
    Validate input data before processing

    Args:
        input_data: Input data to validate

    Returns:
        True if valid, False otherwise
    """
    pass
```

**구현 예시**:
```python
async def _validate_input(self, input_data: Dict[str, Any]) -> bool:
    if "query" not in input_data:
        self.logger.error("Missing required field: query")
        return False

    if not isinstance(input_data["query"], str):
        self.logger.error("Query must be a string")
        return False

    return True
```

---

### 주요 메서드

#### `_create_initial_state(input_data: Dict[str, Any]) -> Dict[str, Any]`
**라인**: 86-103
**목적**: 워크플로우 초기 상태 생성

```python
def _create_initial_state(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create initial state from input data
    Only includes workflow-specific fields (not context fields)

    Args:
        input_data: Input data from user

    Returns:
        Initial state dictionary with workflow fields only
    """
    return {
        "status": "pending",
        "execution_step": "starting",
        **{k: v for k, v in input_data.items()
           if k not in ["user_id", "session_id", "metadata",
                        "original_query", "intent_result"]}
    }
```

**핵심 포인트**:
- Context 필드 제외 (`user_id`, `session_id`, `metadata` 등)
- 기본 필드 설정: `status: "pending"`, `execution_step: "starting"`
- 서브클래스에서 오버라이드하여 커스텀 필드 추가 가능

---

#### `_create_context(input_data: Dict[str, Any]) -> AgentContext`
**라인**: 105-125
**목적**: 실행 컨텍스트 생성

```python
def _create_context(self, input_data: Dict[str, Any]) -> AgentContext:
    """
    Create context from input data
    Context contains metadata that doesn't change during execution

    Args:
        input_data: Input data containing context information

    Returns:
        AgentContext instance
    """
    return create_agent_context(
        user_id=input_data.get("user_id", "default"),
        session_id=input_data.get("session_id", "default"),
        context_type="agent",
        agent_name=self.agent_name,
        original_query=input_data.get("original_query", ""),
        intent_result=input_data.get("intent_result", {}),
        metadata=input_data.get("metadata", {}),
        request_id=input_data.get("request_id")
    )
```

**핵심 포인트**:
- `user_id`, `session_id` 필수 (기본값: "default")
- `request_id` 미제공 시 자동 생성
- Context는 실행 중 READ-ONLY

---

#### `_wrap_node_with_runtime(node_func: Callable) -> Callable`
**라인**: 127-154
**목적**: 노드 함수에 Runtime 파라미터 자동 주입

```python
def _wrap_node_with_runtime(self, node_func: Callable) -> Callable:
    """
    Wrap a node function to properly handle Runtime parameter
    This ensures nodes receive Runtime even if not explicitly passed

    Args:
        node_func: Original node function

    Returns:
        Wrapped function that handles Runtime
    """
    async def wrapped(state: Dict[str, Any],
                      runtime: Optional[Runtime] = None) -> Dict[str, Any]:
        import inspect
        sig = inspect.signature(node_func)

        if "runtime" in sig.parameters:
            if runtime is None:
                self.logger.warning(
                    f"Runtime not provided to {node_func.__name__}, using default"
                )
                return await node_func(state, runtime)
            return await node_func(state, runtime)
        else:
            self.logger.warning(
                f"Node {node_func.__name__} doesn't use Runtime - consider updating"
            )
            return await node_func(state)

    return wrapped
```

**사용 시나리오**:
- Runtime 미지원 레거시 노드와 호환성 유지
- Runtime 파라미터 자동 검사 및 주입

---

#### `execute(input_data: Dict[str, Any], config: Optional[Dict]) -> Dict[str, Any]`
**라인**: 156-260
**목적**: 에이전트 워크플로우 실행

```python
async def execute(
    self,
    input_data: Dict[str, Any],
    config: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Execute the agent workflow with Context API

    Args:
        input_data: Input data for the agent
        config: Optional configuration for execution

    Returns:
        Dict containing execution results
    """
```

**실행 흐름**:

1. **입력 검증** (라인 172-178)
   ```python
   if not await self._validate_input(input_data):
       return {
           "status": "error",
           "error": "Invalid input data",
           "agent": self.agent_name
       }
   ```

2. **초기 상태 생성** (라인 181)
   ```python
   initial_state = self._create_initial_state(input_data)
   ```

3. **컨텍스트 생성** (라인 184)
   ```python
   context = self._create_context(input_data)
   ```

4. **Config 준비** (라인 187-195)
   ```python
   if config is None:
       config = {}

   config.setdefault("recursion_limit", 25)
   config.setdefault("configurable", {})
   config["configurable"]["thread_id"] = context.get("session_id", "default")
   ```

5. **워크플로우 컴파일** (라인 198-208)
   ```python
   if self.workflow is None:
       self.logger.error("Workflow not initialized")
       return {"status": "error", ...}

   async with AsyncSqliteSaver.from_conn_string(
       str(self.checkpointer_path)
   ) as checkpointer:
       app = self.workflow.compile(checkpointer=checkpointer)
   ```

6. **실행 (타임아웃 적용)** (라인 211-222)
   ```python
   timeout = config.get("timeout", 30)

   result = await asyncio.wait_for(
       app.ainvoke(
           initial_state,
           config=config,
           context=context
       ),
       timeout=timeout
   )
   ```

7. **결과 반환** (라인 230-239)
   ```python
   return {
       "status": "success",
       "data": result,
       "agent": self.agent_name,
       "context": {
           "user_id": context.get("user_id", "unknown"),
           "session_id": context.get("session_id", "unknown"),
           "request_id": context.get("request_id", "unknown")
       }
   }
   ```

8. **타임아웃 에러 처리** (라인 241-252)
   ```python
   except asyncio.TimeoutError:
       self.logger.error(f"Execution timed out after {timeout}s")
       return {
           "status": "error",
           "error": f"Execution timed out after {timeout} seconds",
           "agent": self.agent_name
       }
   ```

**반환 형식**:
- **성공 시**:
  ```python
  {
      "status": "success",
      "data": {...},  # 최종 상태
      "agent": "agent_name",
      "context": {
          "user_id": "...",
          "session_id": "...",
          "request_id": "..."
      }
  }
  ```
- **실패 시**:
  ```python
  {
      "status": "error",
      "error": "error message",
      "agent": "agent_name"
  }
  ```

---

#### `get_state(thread_id: str) -> Optional[Dict[str, Any]]`
**라인**: 262-280
**목적**: 특정 스레드의 현재 상태 조회

```python
async def get_state(self, thread_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the current state for a thread

    Args:
        thread_id: Thread ID to get state for

    Returns:
        Current state or None
    """
    try:
        async with AsyncSqliteSaver.from_conn_string(
            str(self.checkpointer_path)
        ) as checkpointer:
            app = self.workflow.compile(checkpointer=checkpointer)
            config = {"configurable": {"thread_id": thread_id}}
            state = await app.aget_state(config)
            return state.values if state else None
    except Exception as e:
        self.logger.error(f"Failed to get state: {e}")
        return None
```

**사용 예시**:
```python
current_state = await agent.get_state("session_123")
if current_state:
    print(f"Status: {current_state['status']}")
```

---

#### `update_state(thread_id: str, state_update: Dict, context: Optional[AgentContext]) -> bool`
**라인**: 282-311
**목적**: 특정 스레드의 상태 부분 업데이트

```python
async def update_state(
    self,
    thread_id: str,
    state_update: Dict[str, Any],
    context: Optional[AgentContext] = None
) -> bool:
    """
    Update the state for a thread

    Args:
        thread_id: Thread ID to update
        state_update: State updates to apply (partial update)
        context: Optional context for the update

    Returns:
        True if successful, False otherwise
    """
    try:
        async with AsyncSqliteSaver.from_conn_string(
            str(self.checkpointer_path)
        ) as checkpointer:
            app = self.workflow.compile(checkpointer=checkpointer)
            config = {"configurable": {"thread_id": thread_id}}

            await app.aupdate_state(config, state_update)

            self.logger.info(
                f"State updated for thread {thread_id}: {list(state_update.keys())}"
            )
            return True
    except Exception as e:
        self.logger.error(f"Failed to update state: {e}")
        return False
```

**사용 예시**:
```python
success = await agent.update_state(
    "session_123",
    {"status": "processing", "execution_step": "data_collection"}
)
```

---

#### `create_partial_update(**kwargs) -> Dict[str, Any]`
**라인**: 314-325
**목적**: 노드에서 상태 부분 업데이트 생성

```python
@staticmethod
def create_partial_update(**kwargs) -> Dict[str, Any]:
    """
    Helper to create partial state updates for nodes

    Usage in node:
        return self.create_partial_update(
            field1=new_value1,
            field2=new_value2
        )
    """
    return kwargs
```

**사용 예시 (노드 내부)**:
```python
async def process_node(state: Dict, runtime: Runtime) -> Dict:
    # 처리 로직
    result = do_something(state["query"])

    # 부분 업데이트 반환
    return BaseAgent.create_partial_update(
        status="completed",
        result=result,
        execution_step="finished"
    )
```

---

### Context API 핵심 패턴

#### 1. State와 Context 분리
```python
# State: 워크플로우 중 변경되는 데이터
initial_state = {
    "status": "pending",
    "query": "Show me sales data",
    "sql_result": []
}

# Context: 실행 내내 불변인 메타데이터
context = {
    "user_id": "user123",
    "session_id": "session456",
    "request_id": "req_abc123",
    "debug_mode": False
}
```

#### 2. 노드 시그니처
```python
async def my_node(state: Dict[str, Any], runtime: Runtime) -> Dict[str, Any]:
    # Context 접근
    ctx = await runtime.context()
    user_id = ctx["user_id"]

    # State 읽기 및 업데이트
    query = state["query"]
    result = process_query(query)

    # 부분 업데이트 반환
    return {"sql_result": [result], "status": "completed"}
```

#### 3. ainvoke 호출
```python
result = await app.ainvoke(
    initial_state,      # State (변경 가능)
    config=config,      # 실행 설정
    context=context     # Context (READ-ONLY)
)
```

---

## 3. checkpointer.py

### 개요
LangGraph 체크포인트 관리를 위한 유틸리티 함수를 제공합니다.

---

### 함수: `get_checkpointer`
**라인**: 15-47

```python
def get_checkpointer(
    checkpoint_path: str,
    async_mode: bool = True
) -> Optional[AsyncSqliteSaver]:
    """
    Get a checkpointer instance

    Args:
        checkpoint_path: Path to the checkpoint database
        async_mode: Whether to use async checkpointer

    Returns:
        Checkpointer instance or None if failed
    """
    try:
        checkpoint_path = Path(checkpoint_path)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        if async_mode:
            checkpointer = AsyncSqliteSaver.from_conn_string(
                str(checkpoint_path)
            )
            logger.info(f"AsyncSqliteSaver initialized at {checkpoint_path}")
        else:
            checkpointer = SqliteSaver.from_conn_string(str(checkpoint_path))
            logger.info(f"SqliteSaver initialized at {checkpoint_path}")

        return checkpointer

    except Exception as e:
        logger.error(f"Failed to initialize checkpointer: {e}")
        return None
```

**사용 예시**:
```python
checkpointer = get_checkpointer("checkpoints/sales_agent/session_123.db")
if checkpointer:
    app = workflow.compile(checkpointer=checkpointer)
```

**주의사항**:
- 현재 `__init__.py`에서 비활성화됨 (라인 24, 46)
- BaseAgent는 직접 AsyncSqliteSaver를 사용 (base_agent.py 라인 207)

---

### 함수: `cleanup_old_checkpoints`
**라인**: 50-94

```python
async def cleanup_old_checkpoints(
    checkpoint_dir: Path,
    keep_last: int = 5
) -> int:
    """
    Clean up old checkpoint files

    Args:
        checkpoint_dir: Directory containing checkpoints
        keep_last: Number of recent checkpoints to keep

    Returns:
        Number of files cleaned up
    """
    try:
        if not checkpoint_dir.exists():
            return 0

        # 수정 시간 기준으로 정렬
        checkpoint_files = sorted(
            checkpoint_dir.glob("*.db"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        # 최신 파일만 유지
        files_to_remove = checkpoint_files[keep_last:]
        removed_count = 0

        for file_path in files_to_remove:
            try:
                file_path.unlink()
                removed_count += 1
                logger.debug(f"Removed old checkpoint: {file_path}")
            except Exception as e:
                logger.error(f"Failed to remove {file_path}: {e}")

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old checkpoint files")

        return removed_count

    except Exception as e:
        logger.error(f"Failed to cleanup checkpoints: {e}")
        return 0
```

**사용 예시**:
```python
from pathlib import Path

checkpoint_dir = Path("checkpoints/sales_agent")
removed = await cleanup_old_checkpoints(checkpoint_dir, keep_last=10)
print(f"Removed {removed} old checkpoints")
```

---

## 4. config.py

### 개요
시스템 전역 정적 설정을 관리하는 클래스입니다.

---

### 클래스: `Config`

#### 경로 설정
**라인**: 22-30

```python
BASE_DIR = Path(__file__).parent.parent.parent.parent  # 프로젝트 루트
DB_DIR = BASE_DIR / "database" / "storage"
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
LOG_DIR = BASE_DIR / "logs"

# 디렉토리 자동 생성
for directory in [CHECKPOINT_DIR, LOG_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
```

**경로 구조**:
```
beta_v003/                      (BASE_DIR)
├── database/
│   └── storage/                (DB_DIR)
├── checkpoints/                (CHECKPOINT_DIR)
└── logs/                       (LOG_DIR)
```

---

#### 데이터베이스 경로
**라인**: 32-39

```python
DATABASES = {
    "hr_info": DB_DIR / "hr_information" / "hr_data.db",
    "hr_rules": DB_DIR / "hr_rules" / "chromadb",
    "sales_performance": DB_DIR / "sales_performance" / "sales_performance_db.db",
    "sales_targets": DB_DIR / "sales_performance" / "sales_target_db.db",
    "clients": DB_DIR / "sales_performance" / "clients_db.db",
}
```

**데이터베이스 목록**:
| 키 | 경로 | 용도 |
|---|---|---|
| `hr_info` | `hr_information/hr_data.db` | 인사 정보 |
| `hr_rules` | `hr_rules/chromadb` | 인사 규정 (Vector DB) |
| `sales_performance` | `sales_performance/sales_performance_db.db` | 영업 실적 |
| `sales_targets` | `sales_performance/sales_target_db.db` | 영업 목표 |
| `clients` | `sales_performance/clients_db.db` | 고객 정보 |

---

#### 모델 설정
**라인**: 41-50

```python
DEFAULT_MODELS = {
    "intent": "gpt-4o-mini",      # 빠른 인텐트 분석
    "planning": "gpt-4o",          # 정확한 계획 수립
}

DEFAULT_MODEL_PARAMS = {
    "intent": {"temperature": 0.3, "max_tokens": 500},
    "planning": {"temperature": 0.3, "max_tokens": 2000},
}
```

**모델 용도**:
- **intent**: 사용자 의도 분류 (빠른 응답 필요)
- **planning**: 실행 계획 수립 (정확도 우선)

---

#### 타임아웃 설정
**라인**: 52-56

```python
TIMEOUTS = {
    "agent": 30,           # 개별 에이전트 타임아웃 (초)
    "llm": 20,             # LLM 호출 타임아웃
}
```

---

#### 시스템 제한
**라인**: 58-64

```python
LIMITS = {
    "max_recursion": 25,           # 최대 재귀 깊이
    "max_retries": 3,              # 최대 재시도 횟수
    "max_message_length": 10000,   # 메시지 최대 길이
    "max_sql_results": 1000,       # SQL 결과 최대 행 수
}
```

---

#### 실행 설정
**라인**: 66-69

```python
EXECUTION = {
    "enable_checkpointing": True,  # 체크포인팅 활성화
}
```

---

#### 로깅 설정
**라인**: 71-79

```python
LOGGING = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "file_rotation": "daily",      # 일일 로테이션
    "max_log_size": "100MB",       # 최대 로그 파일 크기
    "backup_count": 7              # 백업 파일 수
}
```

---

#### 기능 플래그
**라인**: 81-84

```python
FEATURES = {
    "enable_llm_planning": True,  # LLM 기반 계획 수립 활성화
}
```

---

### 헬퍼 메서드

#### `get_database_path(db_name: str) -> Path`
**라인**: 88-91

```python
@classmethod
def get_database_path(cls, db_name: str) -> Path:
    """Get database path by name"""
    return cls.DATABASES.get(db_name, cls.DB_DIR / f"{db_name}.db")
```

**사용 예시**:
```python
sales_db = Config.get_database_path("sales_performance")
# 반환: Path("database/storage/sales_performance/sales_performance_db.db")
```

---

#### `get_checkpoint_path(agent_name: str, session_id: str) -> Path`
**라인**: 93-98

```python
@classmethod
def get_checkpoint_path(cls, agent_name: str, session_id: str) -> Path:
    """Get checkpoint database path for an agent session"""
    checkpoint_dir = cls.CHECKPOINT_DIR / agent_name
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    return checkpoint_dir / f"{session_id}.db"
```

**사용 예시**:
```python
checkpoint_path = Config.get_checkpoint_path("sales_agent", "session_123")
# 반환: Path("checkpoints/sales_agent/session_123.db")
```

---

#### `get_model_config(model_type: str) -> Dict[str, Any]`
**라인**: 100-106

```python
@classmethod
def get_model_config(cls, model_type: str) -> Dict[str, Any]:
    """Get model configuration by type"""
    return {
        "model": cls.DEFAULT_MODELS.get(model_type, "gpt-4o-mini"),
        **cls.DEFAULT_MODEL_PARAMS.get(model_type, {})
    }
```

**사용 예시**:
```python
config = Config.get_model_config("planning")
# 반환: {"model": "gpt-4o", "temperature": 0.3, "max_tokens": 2000}
```

---

#### `validate() -> bool`
**라인**: 108-129

```python
@classmethod
def validate(cls) -> bool:
    """Validate configuration"""
    issues = []

    # 데이터베이스 디렉토리 확인
    for name, path in cls.DATABASES.items():
        if not path.parent.exists():
            issues.append(f"Database directory missing: {path.parent}")

    # 필수 디렉토리 확인
    for directory in [cls.CHECKPOINT_DIR, cls.LOG_DIR]:
        if not directory.exists():
            issues.append(f"Required directory missing: {directory}")

    if issues:
        print("Configuration issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return False

    return True
```

**사용 예시**:
```python
if not Config.validate():
    print("Configuration validation failed!")
    sys.exit(1)
```

---

#### `to_dict() -> Dict[str, Any]`
**라인**: 131-140

```python
@classmethod
def to_dict(cls) -> Dict[str, Any]:
    """Export configuration as dictionary"""
    return {
        "databases": {k: str(v) for k, v in cls.DATABASES.items()},
        "models": cls.DEFAULT_MODELS,
        "timeouts": cls.TIMEOUTS,
        "limits": cls.LIMITS,
        "features": cls.FEATURES
    }
```

**사용 예시**:
```python
import json

config_dict = Config.to_dict()
print(json.dumps(config_dict, indent=2))
```

---

## 5. context.py

### 개요
LangGraph 0.6.x Context API를 위한 컨텍스트 정의 및 헬퍼 함수를 제공합니다.

---

### TypedDict: `AgentContext`
**라인**: 15-45

```python
class AgentContext(TypedDict):
    """
    Runtime context for agents
    Contains metadata and configuration passed at execution time
    This is READ-ONLY during execution
    """
```

#### 필드 구성

**필수 필드**:
```python
user_id: str                # 사용자 식별자
session_id: str             # 세션 식별자
```

**런타임 정보 (선택)**:
```python
request_id: Optional[str]       # 요청 고유 ID
timestamp: Optional[str]        # 요청 타임스탬프 (ISO 8601)
original_query: Optional[str]   # 원본 사용자 입력
```

**인증 (선택)**:
```python
api_keys: Optional[Dict[str, str]]  # 서비스 API 키
```

**사용자 설정 (선택)**:
```python
language: Optional[str]     # 사용자 언어 (ko, en, 등)
```

**런타임 설정 (선택)**:
```python
timeout_overrides: Optional[Dict[str, int]]  # 타임아웃 오버라이드
```

**실행 제어 (선택)**:
```python
debug_mode: Optional[bool]      # 디버그 로깅 활성화
dry_run: Optional[bool]         # 시뮬레이션 모드
strict_mode: Optional[bool]     # 엄격한 에러 처리
max_retries: Optional[int]      # 재시도 횟수 오버라이드
```

---

### TypedDict: `SubgraphContext`
**라인**: 47-70

```python
class SubgraphContext(TypedDict):
    """
    Context for subgraphs (filtered subset of AgentContext)
    Used when invoking DataCollectionSubgraph, AnalysisSubgraph, etc.
    """
```

#### 필드 구성

**부모로부터 상속 (필수)**:
```python
user_id: str
session_id: str
```

**부모로부터 상속 (선택)**:
```python
request_id: Optional[str]
language: Optional[str]
debug_mode: Optional[bool]
```

**서브그래프 식별**:
```python
parent_agent: str           # 부모 에이전트 이름
subgraph_name: str         # 현재 서브그래프 이름
```

**서브그래프 파라미터**:
```python
suggested_tools: Optional[List[str]]    # 도구 힌트
analysis_depth: Optional[str]           # shallow, normal, deep
db_paths: Optional[Dict[str, str]]     # 데이터베이스 경로
```

---

### 함수: `create_agent_context`
**라인**: 74-111

```python
def create_agent_context(
    user_id: str,
    session_id: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Create AgentContext with required fields and optional values

    Args:
        user_id: User identifier
        session_id: Session identifier
        **kwargs: Optional context fields

    Returns:
        Context dictionary ready for LangGraph
    """
```

**자동 생성 필드**:
- `request_id`: 미제공 시 `f"req_{uuid.uuid4().hex[:8]}"` 생성
- `timestamp`: 미제공 시 `datetime.now().isoformat()` 생성

**기본값**:
- `language`: "ko"
- `debug_mode`: False
- `strict_mode`: True

**사용 예시**:
```python
context = create_agent_context(
    user_id="user123",
    session_id="session456",
    original_query="Show me sales data",
    debug_mode=True,
    api_keys={"openai_api_key": "sk-..."}
)
```

**반환 예시**:
```python
{
    "user_id": "user123",
    "session_id": "session456",
    "request_id": "req_a1b2c3d4",
    "timestamp": "2025-09-27T10:30:00.123456",
    "original_query": "Show me sales data",
    "api_keys": {"openai_api_key": "sk-..."},
    "language": "ko",
    "debug_mode": True,
    "strict_mode": True
}
```

---

### 함수: `merge_with_config_defaults`
**라인**: 114-140

```python
def merge_with_config_defaults(
    context: Dict[str, Any],
    config: Any
) -> Dict[str, Any]:
    """
    Merge context with config defaults
    Context values take precedence

    Args:
        context: Runtime context
        config: Config instance

    Returns:
        Merged context with defaults
    """
```

**동작**:
1. Context에 `timeout_overrides`가 없으면 빈 딕셔너리 생성
2. Config에서 `agent`, `llm` 타임아웃 가져와 추가 (기본 30초)

**사용 예시**:
```python
from .config import Config

context = create_agent_context("user123", "session456")
context = merge_with_config_defaults(context, Config)

# context["timeout_overrides"] 추가됨:
# {"agent": 30, "llm": 20}
```

---

### 함수: `create_subgraph_context`
**라인**: 143-182

```python
def create_subgraph_context(
    parent_context: Dict[str, Any],
    parent_agent: str,
    subgraph_name: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Create context for subgraphs (filtered subset of parent context)

    Args:
        parent_context: Parent agent's context
        parent_agent: Parent agent name
        subgraph_name: Subgraph name
        **kwargs: Additional subgraph-specific parameters

    Returns:
        Filtered context for subgraph
    """
```

**필터링 규칙**:
- 부모 Context에서 필요한 필드만 추출 (`user_id`, `session_id`, `request_id`, `language`, `debug_mode`)
- 서브그래프 식별 정보 추가
- 서브그래프별 파라미터 추가 (`suggested_tools`, `analysis_depth`, `db_paths`)

**사용 예시**:
```python
parent_ctx = create_agent_context("user123", "session456", debug_mode=True)

subgraph_ctx = create_subgraph_context(
    parent_context=parent_ctx,
    parent_agent="sales_agent",
    subgraph_name="data_collection",
    suggested_tools=["sql_query", "aggregate"],
    analysis_depth="deep",
    db_paths={
        "sales_performance": "database/storage/sales_performance/sales_performance_db.db"
    }
)
```

**반환 예시**:
```python
{
    "user_id": "user123",
    "session_id": "session456",
    "request_id": "req_a1b2c3d4",
    "language": "ko",
    "debug_mode": True,
    "parent_agent": "sales_agent",
    "subgraph_name": "data_collection",
    "suggested_tools": ["sql_query", "aggregate"],
    "analysis_depth": "deep",
    "db_paths": {
        "sales_performance": "..."
    }
}
```

---

### 함수: `extract_api_keys_from_env`
**라인**: 185-206

```python
def extract_api_keys_from_env() -> Dict[str, str]:
    """
    Extract API keys from environment variables

    Returns:
        Dictionary of API keys
    """
```

**지원 키**:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

**동작**:
1. 환경 변수에서 API 키 패턴 검색
2. 키를 소문자로 변환하여 반환 (`openai_api_key`)

**사용 예시**:
```python
api_keys = extract_api_keys_from_env()
# 반환: {"openai_api_key": "sk-...", "anthropic_api_key": "..."}

context = create_agent_context(
    user_id="user123",
    session_id="session456",
    api_keys=api_keys
)
```

---

## 6. states.py

### 개요
LangGraph 워크플로우에서 사용하는 State 정의 및 리듀서 함수를 제공합니다.

---

### 리듀서 함수

#### `merge_dicts(a: Dict, b: Dict) -> Dict`
**라인**: 14-20

```python
def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Merge dictionaries, b overwrites a"""
    if not a:
        return b or {}
    if not b:
        return a
    return {**a, **b}
```

**사용**:
```python
aggregated_data: Annotated[Dict[str, Any], merge_dicts]
```

**동작**:
```python
a = {"x": 1, "y": 2}
b = {"y": 3, "z": 4}
result = merge_dicts(a, b)
# 결과: {"x": 1, "y": 3, "z": 4}
```

---

#### `append_unique(a: List, b: List) -> List`
**라인**: 23-33

```python
def append_unique(a: List[Any], b: List[Any]) -> List[Any]:
    """Append only unique items to list"""
    if not a:
        a = []
    if not b:
        return a
    result = a.copy()
    for item in b:
        if item not in result:
            result.append(item)
    return result
```

**사용**:
```python
insights: Annotated[List[str], append_unique]
```

**동작**:
```python
a = ["insight1", "insight2"]
b = ["insight2", "insight3"]
result = append_unique(a, b)
# 결과: ["insight1", "insight2", "insight3"]
```

---

### TypedDict: `BaseState`
**라인**: 38-51

```python
class BaseState(TypedDict):
    """Base state for all workflows"""
```

**필드**:
```python
# 상태 추적 (덮어쓰기)
status: str                # pending, processing, completed, failed
execution_step: str        # 현재 워크플로우 단계

# 에러 추적 (누적)
errors: Annotated[List[str], add]  # 에러 메시지

# 타이밍 (덮어쓰기)
start_time: Optional[str]
end_time: Optional[str]
```

**모든 State의 기본 필드**

---

### TypedDict: `DataCollectionState`
**라인**: 55-74

```python
class DataCollectionState(TypedDict):
    """State for data collection subgraph"""
```

**입력**:
```python
query_params: Dict[str, Any]    # 데이터 수집 파라미터
target_databases: List[str]     # 쿼리할 데이터베이스
```

**수집 결과 (누적)**:
```python
performance_data: Annotated[List[Dict[str, Any]], add]
target_data: Annotated[List[Dict[str, Any]], add]
client_data: Annotated[List[Dict[str, Any]], add]
```

**집계 데이터 (병합)**:
```python
aggregated_performance: Annotated[Dict[str, Any], merge_dicts]
aggregated_target: Annotated[Dict[str, Any], merge_dicts]
aggregated_client: Annotated[Dict[str, Any], merge_dicts]
```

**상태**:
```python
collection_status: str
errors: Annotated[List[str], add]
```

---

### TypedDict: `AnalysisState`
**라인**: 76-99

```python
class AnalysisState(TypedDict):
    """State for analysis subgraph"""
```

**입력 데이터 (데이터 수집에서)**:
```python
performance_data: List[Dict[str, Any]]
target_data: List[Dict[str, Any]]
client_data: List[Dict[str, Any]]
```

**분석 파라미터**:
```python
analysis_type: str          # basic, trend, comparative, comprehensive
analysis_params: Dict[str, Any]
```

**분석 결과 (병합)**:
```python
basic_metrics: Annotated[Dict[str, Any], merge_dicts]
trend_analysis: Annotated[Dict[str, Any], merge_dicts]
comparative_analysis: Annotated[Dict[str, Any], merge_dicts]
insights: Annotated[List[str], append_unique]
```

**최종 보고서**:
```python
analysis_report: Optional[Dict[str, Any]]
```

**상태**:
```python
analysis_status: str
errors: Annotated[List[str], add]
```

---

### TypedDict: `SalesState` (BaseState 상속)
**라인**: 103-142

```python
class SalesState(BaseState):
    """
    Sales Analytics Agent State
    Workflow data that changes during execution
    """
```

#### 필드 구성

**입력 (덮어쓰기)**:
```python
query: str                      # 사용자 쿼리
employee_name: Optional[str]    # 직원 이름
period: Optional[str]           # daily, weekly, monthly, yearly
metrics_type: Optional[str]     # performance, revenue, targets
```

**계획 (덮어쓰기)**:
```python
execution_plan: Optional[Dict[str, Any]]  # LLM 생성 실행 계획
```

**쿼리 처리 (덮어쓰기)**:
```python
parsed_query: Dict[str, Any]    # 파싱된 쿼리 구성 요소
generated_sql: Optional[str]    # 생성된 SQL 쿼리
```

**데이터 수집 (누적)**:
```python
sql_result: Annotated[List[Dict[str, Any]], add]  # SQL 쿼리 결과
```

**서브그래프 결과 (덮어쓰기)**:
```python
data_collection_result: Optional[Dict[str, Any]]  # DataCollectionSubgraph 결과
analysis_result: Optional[Dict[str, Any]]         # AnalysisSubgraph 결과
```

**집계 (병합)**:
```python
collected_data: Annotated[Dict[str, Any], merge_dicts]      # 서브그래프 데이터
execution_results: Annotated[Dict[str, Any], merge_dicts]   # 실행 결과
aggregated_data: Annotated[Dict[str, Any], merge_dicts]     # 집계 메트릭
statistics: Annotated[Dict[str, float], merge_dicts]        # 통계 요약
```

**분석 (중복 제거 누적)**:
```python
insights: Annotated[List[str], append_unique]           # 고유 인사이트
recommendations: Annotated[List[str], append_unique]    # 액션 추천
```

**출력 (덮어쓰기)**:
```python
formatted_result: Optional[str]         # 사람이 읽을 수 있는 결과
final_report: Optional[Dict[str, Any]]  # 완전한 보고서
```

---

### TypedDict: `DocumentState` (BaseState 상속)
**라인**: 144-172

```python
class DocumentState(BaseState):
    """
    State for document generation workflows
    """
```

#### 필드 구성

**문서 관련 필드**:
```python
doc_type: str               # sales_report, product_seminar_application 등
doc_format: str             # markdown, html, text, word
title: str                  # 문서 제목
input_data: Dict[str, Any]  # 입력 데이터
template_id: str            # 템플릿 식별자
sections: List[Dict[str, Any]]  # 문서 섹션
content: str                # 원시 콘텐츠
formatted_content: str      # 포맷된 콘텐츠
document_metadata: Dict[str, Any]  # 문서 메타데이터
final_document: Dict[str, Any]     # 최종 문서
```

**인터랙티브 처리 필드**:
```python
user_query: Optional[str]                   # 원본 사용자 쿼리
query_analysis: Optional[Dict[str, Any]]    # LLM 분석 결과
template_analysis: Optional[Dict[str, Any]] # 템플릿 필드 분석
required_fields: Optional[List[Dict[str, Any]]]  # 필수 필드 정의
missing_fields: Optional[List[Dict[str, Any]]]   # 누락된 필드
collected_data: Annotated[Dict[str, Any], merge_dicts]  # 인터랙티브 수집 데이터
interaction_mode: Optional[str]             # interactive, batch, auto
interaction_history: Annotated[List[Dict[str, Any]], add]  # 인터랙션 히스토리
needs_user_input: bool                      # 사용자 입력 필요 플래그
current_prompt: Optional[str]               # 현재 프롬프트
user_response: Optional[str]                # 최신 사용자 응답
```

---

### 함수: `create_sales_initial_state`
**라인**: 176-227

```python
def create_sales_initial_state(**kwargs) -> Dict[str, Any]:
    """
    Create initial SalesState with defaults

    Args:
        **kwargs: Initial field values

    Returns:
        Initial state dictionary
    """
```

**기본값**:
```python
{
    # 상태
    "status": "pending",
    "execution_step": "initializing",
    "errors": [],
    "start_time": datetime.now().isoformat(),

    # 입력
    "query": kwargs.get("query", ""),
    "employee_name": kwargs.get("employee_name"),
    "period": kwargs.get("period", "monthly"),
    "metrics_type": kwargs.get("metrics_type", "performance"),

    # 계획
    "execution_plan": None,

    # 쿼리 처리
    "parsed_query": {},
    "generated_sql": None,

    # 데이터 수집
    "sql_result": [],

    # 서브그래프 결과
    "data_collection_result": None,
    "analysis_result": None,

    # 집계
    "collected_data": {},
    "execution_results": {},
    "aggregated_data": {},
    "statistics": {},

    # 분석
    "insights": [],
    "recommendations": [],

    # 출력
    "formatted_result": None,
    "final_report": None,
    "end_time": None
}
```

**사용 예시**:
```python
initial_state = create_sales_initial_state(
    query="Show me monthly sales for John",
    employee_name="John",
    period="monthly"
)
```

---

### 함수: `merge_state_updates`
**라인**: 230-245

```python
def merge_state_updates(*updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge multiple state updates

    Args:
        *updates: State update dictionaries

    Returns:
        Merged state update
    """
```

**사용 예시**:
```python
update1 = {"status": "processing", "execution_step": "data_collection"}
update2 = {"sql_result": [{"row": 1}]}
update3 = {"insights": ["High performance"]}

merged = merge_state_updates(update1, update2, update3)
# 결과: {"status": "processing", "execution_step": "data_collection",
#        "sql_result": [{"row": 1}], "insights": ["High performance"]}
```

---

### 함수: `get_state_summary`
**라인**: 248-267

```python
def get_state_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get summary of current state

    Args:
        state: Current state

    Returns:
        Summary dictionary
    """
```

**반환 예시**:
```python
{
    "status": "completed",
    "step": "formatting_results",
    "errors_count": 0,
    "has_results": True,
    "data_collected": True,
    "insights_count": 5,
    "start_time": "2025-09-27T10:00:00",
    "end_time": "2025-09-27T10:00:30"
}
```

**사용 예시**:
```python
summary = get_state_summary(current_state)
print(f"Status: {summary['status']}, Step: {summary['step']}")
```

---

## 핵심 개념

### 1. State vs Context

| 항목 | State | Context |
|------|-------|---------|
| **정의** | 워크플로우 중 변경되는 데이터 | 실행 내내 불변인 메타데이터 |
| **변경 가능** | ✅ 노드에서 수정 가능 | ❌ READ-ONLY |
| **전달 방식** | `ainvoke(state, ...)` | `ainvoke(..., context=ctx)` |
| **예시** | `sql_result`, `insights`, `status` | `user_id`, `session_id`, `request_id` |
| **용도** | 워크플로우 진행 상황 추적 | 사용자/세션 식별, 설정 전달 |

**코드 예시**:
```python
# State: 워크플로우 데이터
state = {
    "status": "pending",
    "query": "Show me sales",
    "sql_result": [],
    "insights": []
}

# Context: 메타데이터
context = {
    "user_id": "user123",
    "session_id": "session456",
    "request_id": "req_abc",
    "debug_mode": False
}

# 실행
result = await app.ainvoke(state, config=config, context=context)
```

---

### 2. Reducer 패턴

LangGraph는 `Annotated[Type, reducer]`를 사용하여 State 필드 업데이트 방식을 정의합니다.

#### 내장 Reducer: `add`
```python
from operator import add

errors: Annotated[List[str], add]
```

**동작**:
```python
# 노드 1
return {"errors": ["Error A"]}

# 노드 2
return {"errors": ["Error B"]}

# 최종 state["errors"] = ["Error A", "Error B"]
```

---

#### 커스텀 Reducer: `merge_dicts`
```python
aggregated_data: Annotated[Dict[str, Any], merge_dicts]
```

**동작**:
```python
# 노드 1
return {"aggregated_data": {"x": 1, "y": 2}}

# 노드 2
return {"aggregated_data": {"y": 3, "z": 4}}

# 최종 state["aggregated_data"] = {"x": 1, "y": 3, "z": 4}
```

---

#### 커스텀 Reducer: `append_unique`
```python
insights: Annotated[List[str], append_unique]
```

**동작**:
```python
# 노드 1
return {"insights": ["Insight A", "Insight B"]}

# 노드 2
return {"insights": ["Insight B", "Insight C"]}

# 최종 state["insights"] = ["Insight A", "Insight B", "Insight C"]
```

---

### 3. LangGraph 0.6.x 워크플로우 패턴

#### A. StateGraph 생성
```python
from langgraph.graph import StateGraph
from .states import SalesState
from .context import AgentContext

workflow = StateGraph(
    state_schema=SalesState,
    context_schema=AgentContext
)
```

---

#### B. 노드 정의
```python
from langgraph.runtime import Runtime

async def data_collection_node(
    state: Dict[str, Any],
    runtime: Runtime
) -> Dict[str, Any]:
    # Context 접근 (READ-ONLY)
    ctx = await runtime.context()
    user_id = ctx["user_id"]
    debug_mode = ctx.get("debug_mode", False)

    if debug_mode:
        logger.debug(f"Processing for user: {user_id}")

    # State 읽기
    query = state["query"]

    # 데이터 수집 로직
    result = await fetch_data(query)

    # 부분 업데이트 반환
    return {
        "sql_result": [result],
        "status": "data_collected",
        "execution_step": "analysis"
    }
```

---

#### C. 노드 및 엣지 추가
```python
workflow.add_node("parse_query", parse_query_node)
workflow.add_node("data_collection", data_collection_node)
workflow.add_node("analysis", analysis_node)
workflow.add_node("format_result", format_result_node)

workflow.add_edge("parse_query", "data_collection")
workflow.add_edge("data_collection", "analysis")
workflow.add_edge("analysis", "format_result")

workflow.set_entry_point("parse_query")
workflow.set_finish_point("format_result")
```

---

#### D. 조건부 엣지
```python
def should_retry(state: Dict[str, Any]) -> str:
    if state.get("errors"):
        return "retry"
    return "continue"

workflow.add_conditional_edges(
    "data_collection",
    should_retry,
    {
        "retry": "parse_query",
        "continue": "analysis"
    }
)
```

---

#### E. 실행
```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# 체크포인터 생성
async with AsyncSqliteSaver.from_conn_string("checkpoints/agent.db") as checkpointer:
    # 컴파일
    app = workflow.compile(checkpointer=checkpointer)

    # 초기 상태
    initial_state = create_sales_initial_state(
        query="Show me monthly sales",
        period="monthly"
    )

    # 컨텍스트
    context = create_agent_context(
        user_id="user123",
        session_id="session456",
        debug_mode=True
    )

    # 실행
    config = {
        "recursion_limit": 25,
        "configurable": {"thread_id": "session456"}
    }

    result = await app.ainvoke(
        initial_state,
        config=config,
        context=context
    )

    print(result["final_report"])
```

---

### 4. 서브그래프 호출

```python
from langgraph.graph import StateGraph

# 서브그래프 정의
data_collection_subgraph = StateGraph(
    state_schema=DataCollectionState,
    context_schema=SubgraphContext
)
# ... 노드 추가 ...
data_collection_app = data_collection_subgraph.compile()

# 메인 에이전트 노드에서 서브그래프 호출
async def invoke_data_collection(
    state: Dict[str, Any],
    runtime: Runtime
) -> Dict[str, Any]:
    # 부모 Context 가져오기
    parent_ctx = await runtime.context()

    # 서브그래프 Context 생성
    subgraph_ctx = create_subgraph_context(
        parent_context=parent_ctx,
        parent_agent="sales_agent",
        subgraph_name="data_collection",
        suggested_tools=["sql_query"],
        db_paths={"sales_performance": "..."}
    )

    # 서브그래프 State 준비
    subgraph_state = {
        "query_params": state["parsed_query"],
        "target_databases": ["sales_performance"],
        "collection_status": "pending",
        "errors": []
    }

    # 서브그래프 실행
    config = {"configurable": {"thread_id": parent_ctx["session_id"]}}
    result = await data_collection_app.ainvoke(
        subgraph_state,
        config=config,
        context=subgraph_ctx
    )

    # 결과를 메인 State로 병합
    return {
        "data_collection_result": result,
        "collected_data": result["aggregated_performance"],
        "execution_step": "analysis"
    }
```

---

## LangGraph 0.6.7 챗봇 개발 가이드

### 필요한 수정/추가 사항

#### 1. `states.py`에 `ChatbotState` 추가

```python
class ChatbotState(BaseState):
    """
    Chatbot State
    대화형 에이전트를 위한 상태 정의
    """

    # 대화 관련
    messages: Annotated[List[Dict[str, str]], add]  # 대화 히스토리
    current_message: Optional[str]  # 현재 사용자 메시지
    current_intent: Optional[str]   # 현재 인텐트

    # 컨텍스트 변수
    context_variables: Annotated[Dict[str, Any], merge_dicts]  # 대화 컨텍스트

    # 액션 처리
    action_type: Optional[str]      # query_data, generate_document, etc.
    action_params: Optional[Dict[str, Any]]  # 액션 파라미터
    action_result: Optional[Dict[str, Any]]  # 액션 실행 결과

    # 응답 생성
    response: Optional[str]         # 최종 응답
    response_metadata: Annotated[Dict[str, Any], merge_dicts]  # 응답 메타데이터
```

---

#### 2. `context.py`에 채팅 관련 필드 추가

```python
class AgentContext(TypedDict):
    # ... 기존 필드 ...

    # 채팅 관련 추가
    conversation_history: Optional[List[Dict[str, str]]]  # 이전 대화 히스토리
    user_preferences: Optional[Dict[str, Any]]            # 사용자 선호도
    active_session_data: Optional[Dict[str, Any]]         # 활성 세션 데이터
```

---

#### 3. `config.py`에 채팅 설정 추가

```python
# 모델 설정에 추가
DEFAULT_MODELS = {
    "intent": "gpt-4o-mini",
    "planning": "gpt-4o",
    "chatbot": "gpt-4o",           # 추가
}

DEFAULT_MODEL_PARAMS = {
    "intent": {"temperature": 0.3, "max_tokens": 500},
    "planning": {"temperature": 0.3, "max_tokens": 2000},
    "chatbot": {"temperature": 0.7, "max_tokens": 1500},  # 추가
}

# 타임아웃에 추가
TIMEOUTS = {
    "agent": 30,
    "llm": 20,
    "chatbot": 60,  # 추가 - 대화형 처리는 더 긴 타임아웃
}

# 채팅 전용 설정 추가
CHATBOT = {
    "max_conversation_history": 20,     # 최대 대화 히스토리
    "context_window": 10,               # 컨텍스트 윈도우
    "enable_memory": True,              # 메모리 활성화
    "enable_streaming": False,          # 스트리밍 응답
}
```

---

#### 4. 새 파일: `chatbot_agent.py`

```python
"""
Chatbot Agent Implementation
LangGraph 0.6.x 기반 대화형 에이전트
"""

from typing import Dict, Any, Type
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
import logging

from .base_agent import BaseAgent
from .states import ChatbotState
from .context import AgentContext
from .config import Config


logger = logging.getLogger(__name__)


class ChatbotAgent(BaseAgent):
    """
    대화형 에이전트
    사용자 메시지 → 인텐트 분류 → 액션 실행 → 응답 생성
    """

    def __init__(self, agent_name: str = "chatbot", checkpoint_dir: str = None):
        super().__init__(agent_name, checkpoint_dir)

    def _get_state_schema(self) -> Type:
        """ChatbotState 사용"""
        return ChatbotState

    def _build_graph(self):
        """채팅 워크플로우 구성"""
        self.workflow = StateGraph(
            state_schema=ChatbotState,
            context_schema=AgentContext
        )

        # 노드 추가
        self.workflow.add_node("classify_intent", self.classify_intent_node)
        self.workflow.add_node("execute_action", self.execute_action_node)
        self.workflow.add_node("generate_response", self.generate_response_node)

        # 엣지 정의
        self.workflow.add_edge("classify_intent", "execute_action")
        self.workflow.add_edge("execute_action", "generate_response")

        # 시작/종료점
        self.workflow.set_entry_point("classify_intent")
        self.workflow.set_finish_point("generate_response")

    async def _validate_input(self, input_data: Dict[str, Any]) -> bool:
        """입력 검증"""
        if "current_message" not in input_data:
            self.logger.error("Missing required field: current_message")
            return False
        return True

    # ===== 노드 구현 =====

    async def classify_intent_node(
        self,
        state: Dict[str, Any],
        runtime: Runtime
    ) -> Dict[str, Any]:
        """인텐트 분류 노드"""
        ctx = await runtime.context()

        message = state["current_message"]
        self.logger.info(f"Classifying intent for: {message}")

        # LLM을 사용한 인텐트 분류
        intent_config = Config.get_model_config("intent")

        # TODO: 실제 LLM 호출
        # intent = await classify_intent_with_llm(message, intent_config)

        # 예시 결과
        intent = "query_sales_data"
        action_params = {
            "query": message,
            "period": "monthly"
        }

        return {
            "current_intent": intent,
            "action_type": intent,
            "action_params": action_params,
            "execution_step": "executing_action"
        }

    async def execute_action_node(
        self,
        state: Dict[str, Any],
        runtime: Runtime
    ) -> Dict[str, Any]:
        """액션 실행 노드"""
        ctx = await runtime.context()

        action_type = state["action_type"]
        action_params = state["action_params"]

        self.logger.info(f"Executing action: {action_type}")

        # 액션 타입별 처리
        if action_type == "query_sales_data":
            result = await self._query_sales_data(action_params, ctx)
        elif action_type == "generate_document":
            result = await self._generate_document(action_params, ctx)
        else:
            result = {"error": f"Unknown action type: {action_type}"}

        return {
            "action_result": result,
            "execution_step": "generating_response"
        }

    async def generate_response_node(
        self,
        state: Dict[str, Any],
        runtime: Runtime
    ) -> Dict[str, Any]:
        """응답 생성 노드"""
        ctx = await runtime.context()

        action_result = state["action_result"]
        current_message = state["current_message"]

        self.logger.info("Generating response")

        # LLM을 사용한 응답 생성
        chatbot_config = Config.get_model_config("chatbot")

        # TODO: 실제 LLM 호출
        # response = await generate_response_with_llm(
        #     current_message, action_result, chatbot_config
        # )

        # 예시 응답
        response = f"Based on your query, here are the results: {action_result}"

        # 대화 히스토리에 추가
        new_messages = [
            {"role": "user", "content": current_message},
            {"role": "assistant", "content": response}
        ]

        return {
            "messages": new_messages,
            "response": response,
            "status": "completed",
            "execution_step": "finished"
        }

    # ===== 헬퍼 메서드 =====

    async def _query_sales_data(
        self,
        params: Dict[str, Any],
        ctx: Dict[str, Any]
    ) -> Dict[str, Any]:
        """영업 데이터 쿼리"""
        # TODO: SalesAgent 호출 또는 직접 DB 쿼리
        return {"data": "Sample sales data"}

    async def _generate_document(
        self,
        params: Dict[str, Any],
        ctx: Dict[str, Any]
    ) -> Dict[str, Any]:
        """문서 생성"""
        # TODO: DocumentAgent 호출
        return {"document": "Sample document"}
```

---

#### 5. 사용 예시

```python
import asyncio
from core.chatbot_agent import ChatbotAgent
from core.context import create_agent_context

async def main():
    # 에이전트 생성
    chatbot = ChatbotAgent()

    # 입력 데이터
    input_data = {
        "current_message": "Show me monthly sales for John",
        "user_id": "user123",
        "session_id": "session456"
    }

    # 실행
    result = await chatbot.execute(input_data)

    if result["status"] == "success":
        response = result["data"]["response"]
        print(f"Chatbot: {response}")
    else:
        print(f"Error: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 채팅 히스토리 관리

```python
async def get_conversation_history(session_id: str) -> List[Dict[str, str]]:
    """세션의 대화 히스토리 조회"""
    agent = ChatbotAgent()
    state = await agent.get_state(session_id)

    if state:
        return state.get("messages", [])
    return []

async def continue_conversation(
    session_id: str,
    new_message: str
) -> str:
    """기존 세션에서 대화 계속"""
    agent = ChatbotAgent()

    # 기존 히스토리 가져오기
    history = await get_conversation_history(session_id)

    # 입력 데이터
    input_data = {
        "current_message": new_message,
        "messages": history,  # 기존 히스토리 포함
        "user_id": "user123",
        "session_id": session_id
    }

    # 실행
    result = await agent.execute(input_data)

    if result["status"] == "success":
        return result["data"]["response"]
    else:
        return f"Error: {result['error']}"
```

---

## 주의사항

### 1. BaseAgent 비활성화
- **위치**: `__init__.py` 라인 22, 45
- **이유**: 현재 임시 비활성화 상태
- **영향**: `from core import BaseAgent` 사용 불가
- **해결**: `from core.base_agent import BaseAgent` 직접 임포트

---

### 2. Context는 READ-ONLY
```python
# ❌ 잘못된 사용
async def node(state: Dict, runtime: Runtime) -> Dict:
    ctx = await runtime.context()
    ctx["user_id"] = "new_user"  # 에러 발생 (READ-ONLY)

# ✅ 올바른 사용
async def node(state: Dict, runtime: Runtime) -> Dict:
    ctx = await runtime.context()
    user_id = ctx["user_id"]  # 읽기만 가능
```

---

### 3. State 부분 업데이트
노드는 **변경된 필드만** 반환해야 합니다.

```python
# ❌ 잘못된 사용 (전체 State 반환)
async def node(state: Dict, runtime: Runtime) -> Dict:
    return state  # 모든 필드 반환

# ✅ 올바른 사용 (부분 업데이트)
async def node(state: Dict, runtime: Runtime) -> Dict:
    return {
        "status": "processing",
        "sql_result": [{"row": 1}]
    }
```

---

### 4. 체크포인터는 async context manager 사용
```python
# ✅ 올바른 사용
async with AsyncSqliteSaver.from_conn_string(path) as checkpointer:
    app = workflow.compile(checkpointer=checkpointer)
    result = await app.ainvoke(state, config, context=context)

# ❌ 잘못된 사용 (context manager 없음)
checkpointer = AsyncSqliteSaver.from_conn_string(path)
app = workflow.compile(checkpointer=checkpointer)
# 리소스 누수 발생 가능
```

---

### 5. thread_id는 session_id 사용
```python
# BaseAgent.execute()에서 자동 설정 (라인 195)
config["configurable"]["thread_id"] = context.get("session_id", "default")
```

---

### 6. Reducer 동작 이해
```python
# add: 리스트 추가
errors: Annotated[List[str], add]
# 노드1: {"errors": ["A"]} → state["errors"] = ["A"]
# 노드2: {"errors": ["B"]} → state["errors"] = ["A", "B"]

# merge_dicts: 딕셔너리 병합 (덮어쓰기)
data: Annotated[Dict, merge_dicts]
# 노드1: {"data": {"x": 1, "y": 2}}
# 노드2: {"data": {"y": 3, "z": 4}}
# 최종: {"x": 1, "y": 3, "z": 4}

# append_unique: 중복 제거 추가
insights: Annotated[List[str], append_unique]
# 노드1: {"insights": ["A", "B"]}
# 노드2: {"insights": ["B", "C"]}
# 최종: ["A", "B", "C"]
```

---

### 7. 서브그래프 호출 시 Context 필터링
```python
# SubgraphContext는 AgentContext의 필터링된 서브셋
subgraph_ctx = create_subgraph_context(
    parent_context=parent_ctx,
    parent_agent="sales_agent",
    subgraph_name="data_collection"
)

# 포함되는 필드:
# - user_id, session_id, request_id, language, debug_mode
# - parent_agent, subgraph_name
# - suggested_tools, analysis_depth, db_paths

# 제외되는 필드:
# - api_keys, timeout_overrides, dry_run, strict_mode, max_retries
```

---

### 8. 타임아웃 처리
```python
# Config에서 기본값 설정
TIMEOUTS = {
    "agent": 30,
    "llm": 20,
}

# execute()에서 타임아웃 적용
timeout = config.get("timeout", 30)
result = await asyncio.wait_for(
    app.ainvoke(state, config, context=context),
    timeout=timeout
)
```

---

## 부록: 파일 상세 정보

### 라인 수 요약
| 파일 | 라인 수 | 주요 내용 |
|------|--------|----------|
| `__init__.py` | 47 | 모듈 익스포트 |
| `base_agent.py` | 325 | BaseAgent 추상 클래스 |
| `checkpointer.py` | 94 | 체크포인트 유틸리티 |
| `config.py` | 140 | 시스템 설정 |
| `context.py` | 206 | Context 정의 |
| `states.py` | 267 | State 정의 |
| **합계** | **1,079** | |

---

### 의존성
```python
# 외부 라이브러리
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.sqlite import SqliteSaver

# 표준 라이브러리
from typing import TypedDict, Dict, Any, List, Optional, Annotated, Type, Callable
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from operator import add
import logging
import asyncio
import uuid
import os

# 환경 변수
from dotenv import load_dotenv
```

---

### 환경 변수
```bash
# .env 파일
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=...
```

---

## 문서 정보

**작성자**: AI Assistant
**작성일**: 2025-09-27
**버전**: 1.0
**LangGraph 버전**: 0.6.7
**프로젝트 경로**: `C:\kdy\Projects\holmesnyangz\beta_v003\backend\service\core\`

---

**끝**