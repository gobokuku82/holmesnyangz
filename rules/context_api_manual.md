# LangGraph 0.6 Context API 구현 메뉴얼

## 📋 목차
1. [개요](#개요)
2. [설치 및 환경 설정](#설치-및-환경-설정)
3. [Context API 기본 구조](#context-api-기본-구조)
4. [단계별 구현 가이드](#단계별-구현-가이드)
5. [고급 패턴](#고급-패턴)
6. [마이그레이션 가이드](#마이그레이션-가이드)
7. [트러블슈팅](#트러블슈팅)

## 개요

LangGraph 0.6에서 도입된 Context API는 런타임 의존성을 관리하는 새로운 패러다임입니다. 이전의 `config['configurable']` 패턴을 대체하여 더 명확하고 타입 안전한 방식을 제공합니다.

### 주요 변경사항
- ❌ **이전**: `config['configurable']` 사용
- ✅ **현재**: `Context` 스키마와 `Runtime` 객체 사용

## 설치 및 환경 설정

### 필수 패키지 설치
```bash
pip install langgraph>=0.6.0
pip install langchain-core
pip install langchain-openai  # OpenAI 사용 시
pip install langchain-anthropic  # Anthropic 사용 시
```

### 버전 확인
```python
import langgraph
print(f"LangGraph version: {langgraph.__version__}")
# 0.6.0 이상이어야 함
```

## Context API 기본 구조

### 1. Context 스키마 정의

Context는 런타임에 필요한 정적 데이터를 정의합니다. `dataclass`, `TypedDict`, 또는 `Pydantic` 모델을 사용할 수 있습니다.

#### dataclass 사용 (권장)
```python
from dataclasses import dataclass
from typing import Optional, Literal

@dataclass
class ContextSchema:
    # 필수 필드
    user_id: str
    
    # 선택적 필드 (기본값 포함)
    model_provider: Literal["openai", "anthropic"] = "anthropic"
    model_name: str = "claude-3-5-haiku-latest"
    temperature: float = 0.7
    
    # 선택적 필드 (None 허용)
    system_message: Optional[str] = None
    db_connection: Optional[str] = None
    api_key: Optional[str] = None
```

#### TypedDict 사용
```python
from typing_extensions import TypedDict
from typing import Optional

class ContextSchema(TypedDict, total=False):
    user_id: str  # required=True로 지정 가능
    model_provider: str
    system_message: Optional[str]
```

#### Pydantic 모델 사용
```python
from pydantic import BaseModel, Field

class ContextSchema(BaseModel):
    user_id: str = Field(..., description="사용자 고유 ID")
    model_provider: str = Field(default="anthropic")
    temperature: float = Field(default=0.7, ge=0, le=2)
```

### 2. State 정의

State는 그래프 실행 중 변경되는 동적 데이터를 관리합니다.

```python
from typing import List, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages

class State(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    current_step: str
    result: Optional[str]
```

### 3. Runtime 객체 활용

Runtime 객체는 context와 기타 런타임 유틸리티에 접근하는 통합 인터페이스입니다.

```python
from langgraph.runtime import Runtime

def my_node(state: State, runtime: Runtime[ContextSchema]) -> State:
    # Context 접근
    user_id = runtime.context.user_id
    model_provider = runtime.context.model_provider
    
    # Store 접근 (메모리 관리)
    if runtime.store:
        user_data = runtime.store.get(("users", user_id))
    
    # Stream writer 접근 (커스텀 스트리밍)
    if runtime.stream_writer:
        runtime.stream_writer({"status": "processing"})
    
    return {"current_step": "completed"}
```

## 단계별 구현 가이드

### Step 1: 프로젝트 구조 설정

```
chatbot_project/
├── __init__.py
├── context.py      # Context 스키마 정의
├── state.py        # State 정의
├── nodes.py        # 노드 함수들
├── tools.py        # 도구 정의
├── graph.py        # 그래프 구성
└── main.py         # 실행 엔트리포인트
```

### Step 2: Context 스키마 정의 (context.py)

```python
from dataclasses import dataclass
from typing import Optional, List, Literal

@dataclass
class ChatbotContext:
    """챗봇 런타임 컨텍스트"""
    
    # 사용자 정보
    user_id: str
    user_name: str
    user_role: Literal["admin", "user", "guest"] = "user"
    
    # 모델 설정
    model_provider: Literal["openai", "anthropic", "google"] = "anthropic"
    model_name: str = "claude-3-5-haiku-latest"
    temperature: float = 0.7
    max_tokens: int = 4096
    
    # 시스템 설정
    system_message: Optional[str] = None
    available_tools: List[str] = None
    
    # 외부 리소스
    db_connection_string: Optional[str] = None
    api_endpoints: Optional[dict] = None
    
    def __post_init__(self):
        """초기화 후 처리"""
        if self.available_tools is None:
            self.available_tools = []
        if self.api_endpoints is None:
            self.api_endpoints = {}
```

### Step 3: State 정의 (state.py)

```python
from typing import List, Optional, Dict, Any, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages

class ChatbotState(TypedDict):
    """챗봇 상태 관리"""
    
    # 대화 관련
    messages: Annotated[List[AnyMessage], add_messages]
    
    # 워크플로우 관련
    current_node: str
    next_action: Optional[str]
    
    # 도구 실행 관련
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    
    # 결과 관련
    final_response: Optional[str]
    metadata: Dict[str, Any]
```

### Step 4: 노드 구현 (nodes.py)

```python
from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.chat_models import init_chat_model
from langgraph.runtime import Runtime
from .context import ChatbotContext
from .state import ChatbotState

# 모델 초기화 맵
MODELS = {
    "openai": {
        "gpt-4": "openai:gpt-4",
        "gpt-4-turbo": "openai:gpt-4-turbo-preview",
        "gpt-3.5-turbo": "openai:gpt-3.5-turbo"
    },
    "anthropic": {
        "claude-3-opus": "anthropic:claude-3-opus-latest",
        "claude-3-5-sonnet": "anthropic:claude-3-5-sonnet-latest",
        "claude-3-5-haiku": "anthropic:claude-3-5-haiku-latest"
    }
}

def preprocess_node(
    state: ChatbotState, 
    runtime: Runtime[ChatbotContext]
) -> Dict[str, Any]:
    """메시지 전처리 노드"""
    
    # Context에서 사용자 정보 가져오기
    user_name = runtime.context.user_name
    user_role = runtime.context.user_role
    
    # 시스템 메시지 추가
    messages = state["messages"].copy()
    
    if runtime.context.system_message:
        system_msg = runtime.context.system_message.format(
            user_name=user_name,
            user_role=user_role
        )
        messages.insert(0, SystemMessage(content=system_msg))
    
    return {
        "messages": messages,
        "current_node": "preprocess",
        "metadata": {
            "user_id": runtime.context.user_id,
            "timestamp": datetime.now().isoformat()
        }
    }

def llm_node(
    state: ChatbotState,
    runtime: Runtime[ChatbotContext]
) -> Dict[str, Any]:
    """LLM 호출 노드"""
    
    # Context에서 모델 설정 가져오기
    provider = runtime.context.model_provider
    model_name = runtime.context.model_name
    
    # 모델 초기화
    model_string = f"{provider}:{model_name}"
    model = init_chat_model(
        model_string,
        temperature=runtime.context.temperature,
        max_tokens=runtime.context.max_tokens
    )
    
    # 도구 바인딩 (필요한 경우)
    if runtime.context.available_tools:
        tools = load_tools(runtime.context.available_tools)
        model = model.bind_tools(tools)
    
    # 모델 호출
    response = model.invoke(state["messages"])
    
    # 스트림 라이터 사용 (옵션)
    if runtime.stream_writer:
        runtime.stream_writer({
            "type": "llm_response",
            "content": response.content
        })
    
    return {
        "messages": [response],
        "current_node": "llm",
        "final_response": response.content
    }

def memory_node(
    state: ChatbotState,
    runtime: Runtime[ChatbotContext]
) -> Dict[str, Any]:
    """메모리 저장 노드"""
    
    if not runtime.store:
        return {"current_node": "memory"}
    
    user_id = runtime.context.user_id
    
    # 대화 내역 저장
    conversation = {
        "messages": [msg.dict() for msg in state["messages"]],
        "timestamp": datetime.now().isoformat(),
        "metadata": state.get("metadata", {})
    }
    
    # Store에 저장
    runtime.store.put(
        ("conversations", user_id),
        str(uuid.uuid4()),
        conversation
    )
    
    # 사용자 통계 업데이트
    stats = runtime.store.get(("stats", user_id)) or {"count": 0}
    stats["count"] += 1
    stats["last_interaction"] = datetime.now().isoformat()
    runtime.store.put(("stats",), user_id, stats)
    
    return {"current_node": "memory"}
```

### Step 5: 도구 구현 (tools.py)

```python
from typing import Optional
from langchain_core.tools import tool
from langgraph.runtime import get_runtime
from .context import ChatbotContext

@tool
def get_user_preferences() -> dict:
    """사용자 선호도 조회"""
    runtime = get_runtime(ChatbotContext)
    user_id = runtime.context.user_id
    
    # Context에서 DB 연결 정보 사용
    if runtime.context.db_connection_string:
        # DB에서 조회 로직
        preferences = fetch_from_db(
            runtime.context.db_connection_string,
            user_id
        )
        return preferences
    
    return {"preferences": "default"}

@tool
def call_external_api(endpoint: str, params: dict) -> dict:
    """외부 API 호출"""
    runtime = get_runtime(ChatbotContext)
    
    # Context에서 API 엔드포인트 정보 가져오기
    api_config = runtime.context.api_endpoints.get(endpoint)
    if not api_config:
        return {"error": f"Unknown endpoint: {endpoint}"}
    
    # API 호출 로직
    response = make_api_call(api_config, params)
    return response

def load_tools(tool_names: List[str]):
    """도구 동적 로드"""
    available_tools = {
        "get_user_preferences": get_user_preferences,
        "call_external_api": call_external_api,
        # 추가 도구들...
    }
    
    return [available_tools[name] for name in tool_names if name in available_tools]
```

### Step 6: 그래프 구성 (graph.py)

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from .context import ChatbotContext
from .state import ChatbotState
from .nodes import preprocess_node, llm_node, memory_node

def create_chatbot_graph():
    """챗봇 그래프 생성"""
    
    # 그래프 빌더 생성
    builder = StateGraph(
        state_schema=ChatbotState,
        context_schema=ChatbotContext  # Context 스키마 등록
    )
    
    # 노드 추가
    builder.add_node("preprocess", preprocess_node)
    builder.add_node("llm", llm_node)
    builder.add_node("memory", memory_node)
    
    # 엣지 정의
    builder.add_edge(START, "preprocess")
    builder.add_edge("preprocess", "llm")
    builder.add_edge("llm", "memory")
    builder.add_edge("memory", END)
    
    # 조건부 엣지 (옵션)
    def should_continue(state: ChatbotState) -> str:
        if state.get("tool_calls"):
            return "tools"
        return "end"
    
    builder.add_conditional_edges(
        "llm",
        should_continue,
        {
            "tools": "tool_execution",
            "end": "memory"
        }
    )
    
    # 체크포인터와 스토어 설정
    checkpointer = MemorySaver()
    store = InMemoryStore()
    
    # 그래프 컴파일
    graph = builder.compile(
        checkpointer=checkpointer,
        store=store
    )
    
    return graph
```

### Step 7: 실행 (main.py)

```python
import asyncio
from typing import Optional
from .graph import create_chatbot_graph
from .context import ChatbotContext

class ChatbotApp:
    def __init__(self):
        self.graph = create_chatbot_graph()
    
    def create_context(
        self,
        user_id: str,
        user_name: str,
        **kwargs
    ) -> ChatbotContext:
        """사용자별 Context 생성"""
        return ChatbotContext(
            user_id=user_id,
            user_name=user_name,
            **kwargs
        )
    
    def chat(
        self,
        message: str,
        user_id: str,
        user_name: str,
        thread_id: Optional[str] = None,
        **context_kwargs
    ):
        """동기 채팅"""
        # Context 생성
        context = self.create_context(
            user_id=user_id,
            user_name=user_name,
            **context_kwargs
        )
        
        # 입력 준비
        input_state = {
            "messages": [{"role": "user", "content": message}]
        }
        
        # 설정 준비
        config = {
            "configurable": {
                "thread_id": thread_id or f"thread_{user_id}"
            }
        }
        
        # 그래프 실행
        result = self.graph.invoke(
            input_state,
            context=context,  # Context 전달
            config=config
        )
        
        return result["final_response"]
    
    async def achat(
        self,
        message: str,
        user_id: str,
        user_name: str,
        thread_id: Optional[str] = None,
        **context_kwargs
    ):
        """비동기 채팅"""
        context = self.create_context(
            user_id=user_id,
            user_name=user_name,
            **context_kwargs
        )
        
        input_state = {
            "messages": [{"role": "user", "content": message}]
        }
        
        config = {
            "configurable": {
                "thread_id": thread_id or f"thread_{user_id}"
            }
        }
        
        # 비동기 실행
        result = await self.graph.ainvoke(
            input_state,
            context=context,
            config=config
        )
        
        return result["final_response"]
    
    def stream_chat(
        self,
        message: str,
        user_id: str,
        user_name: str,
        **context_kwargs
    ):
        """스트리밍 채팅"""
        context = self.create_context(
            user_id=user_id,
            user_name=user_name,
            **context_kwargs
        )
        
        input_state = {
            "messages": [{"role": "user", "content": message}]
        }
        
        # 스트리밍 실행
        for chunk in self.graph.stream(
            input_state,
            context=context,
            stream_mode="values"
        ):
            yield chunk

# 사용 예제
if __name__ == "__main__":
    app = ChatbotApp()
    
    # 기본 사용
    response = app.chat(
        message="안녕하세요!",
        user_id="user123",
        user_name="홍길동"
    )
    print(response)
    
    # 커스텀 Context 설정
    response = app.chat(
        message="날씨 알려줘",
        user_id="user123",
        user_name="홍길동",
        model_provider="openai",
        model_name="gpt-4",
        temperature=0.5,
        available_tools=["get_weather", "get_news"],
        system_message="당신은 친절한 AI 비서입니다."
    )
    print(response)
    
    # 비동기 사용
    async def async_example():
        response = await app.achat(
            message="파이썬 코드 작성해줘",
            user_id="user456",
            user_name="김철수",
            model_provider="anthropic",
            model_name="claude-3-opus"
        )
        print(response)
    
    asyncio.run(async_example())
```

## 고급 패턴

### 1. 동적 모델 선택

```python
def dynamic_model_selection(
    state: State,
    runtime: Runtime[ContextSchema]
) -> Dict[str, Any]:
    """요청 복잡도에 따른 동적 모델 선택"""
    
    message_length = len(state["messages"][-1].content)
    
    # 복잡도에 따라 모델 선택
    if message_length < 100:
        model_name = "gpt-3.5-turbo"  # 간단한 질문
    elif message_length < 500:
        model_name = "gpt-4"  # 중간 복잡도
    else:
        model_name = "claude-3-opus"  # 복잡한 요청
    
    # Context 오버라이드 (직접 수정은 불가, 새 모델로 처리)
    model = init_chat_model(model_name)
    response = model.invoke(state["messages"])
    
    return {"messages": [response]}
```

### 2. 다중 Context 패턴

```python
@dataclass
class BaseContext:
    """기본 Context"""
    user_id: str
    timestamp: str

@dataclass
class ModelContext:
    """모델 관련 Context"""
    provider: str
    model_name: str
    temperature: float

@dataclass
class FullContext(BaseContext, ModelContext):
    """통합 Context"""
    pass

# 사용
def node_with_full_context(
    state: State,
    runtime: Runtime[FullContext]
) -> Dict[str, Any]:
    # 모든 Context 필드 접근 가능
    user_id = runtime.context.user_id
    model_name = runtime.context.model_name
    # ...
```

### 3. Context 검증

```python
from pydantic import BaseModel, validator

class ValidatedContext(BaseModel):
    """검증이 포함된 Context"""
    
    user_id: str
    api_key: str
    rate_limit: int
    
    @validator('user_id')
    def validate_user_id(cls, v):
        if not v or len(v) < 3:
            raise ValueError("Invalid user_id")
        return v
    
    @validator('rate_limit')
    def validate_rate_limit(cls, v):
        if v < 0 or v > 1000:
            raise ValueError("Rate limit must be between 0 and 1000")
        return v
```

### 4. Context 팩토리 패턴

```python
class ContextFactory:
    """Context 생성 팩토리"""
    
    @staticmethod
    def create_for_admin(user_id: str) -> ChatbotContext:
        return ChatbotContext(
            user_id=user_id,
            user_name="Admin",
            user_role="admin",
            model_provider="openai",
            model_name="gpt-4",
            temperature=0.3,
            available_tools=["admin_tools"]
        )
    
    @staticmethod
    def create_for_guest() -> ChatbotContext:
        return ChatbotContext(
            user_id="guest_" + str(uuid.uuid4()),
            user_name="Guest",
            user_role="guest",
            model_provider="openai",
            model_name="gpt-3.5-turbo",
            temperature=0.7,
            max_tokens=1000
        )
```

## 마이그레이션 가이드

### 이전 코드 (config 사용)

```python
# 이전 방식
def old_node(state: State, config: RunnableConfig):
    user_id = config.get("configurable", {}).get("user_id")
    model = config.get("configurable", {}).get("model", "gpt-3.5-turbo")
    # ...

# 그래프 생성
builder = StateGraph(State, config_schema=ConfigSchema)

# 실행
graph.invoke(
    input_state,
    config={"configurable": {"user_id": "123", "model": "gpt-4"}}
)
```

### 새로운 코드 (Context 사용)

```python
# 새로운 방식
@dataclass
class ContextSchema:
    user_id: str
    model: str = "gpt-3.5-turbo"

def new_node(state: State, runtime: Runtime[ContextSchema]):
    user_id = runtime.context.user_id
    model = runtime.context.model
    # ...

# 그래프 생성
builder = StateGraph(State, context_schema=ContextSchema)

# 실행
graph.invoke(
    input_state,
    context={"user_id": "123", "model": "gpt-4"}
)
```

### 마이그레이션 체크리스트

- [ ] `config_schema`를 `context_schema`로 변경
- [ ] 노드 시그니처를 `(state, config)`에서 `(state, runtime)`으로 변경
- [ ] `config["configurable"]` 접근을 `runtime.context`로 변경
- [ ] `graph.invoke()` 호출 시 `config` 대신 `context` 사용
- [ ] 도구에서 `get_config()`를 `get_runtime()`으로 변경

## 트러블슈팅

### 1. TypeError: Context 초기화 오류

**문제**: LangGraph API 서버 사용 시 HTTP 헤더가 Context에 병합되어 오류 발생

**해결**:
```python
@dataclass
class ContextSchema:
    user_id: str
    # 기타 필드...
    
    def __init__(self, user_id: str, **kwargs):
        """추가 kwargs 무시"""
        self.user_id = user_id
        # 명시적으로 필요한 필드만 설정
```

### 2. Context가 서브그래프로 전달되지 않음

**문제**: 메인 그래프의 Context가 서브그래프로 자동 전달되지 않음

**해결**:
```python
def parent_node(state: State, runtime: Runtime[ContextSchema]):
    # 서브그래프 호출 시 명시적으로 Context 전달
    subgraph_result = subgraph.invoke(
        state,
        context=runtime.context  # Context 명시적 전달
    )
    return subgraph_result
```

### 3. Runtime이 None으로 나타남

**문제**: 스트리밍 엔드포인트에서 runtime.context가 null

**해결**:
```python
# 스트리밍 시 Context 확인
def node(state: State, runtime: Runtime[ContextSchema]):
    if runtime and runtime.context:
        user_id = runtime.context.user_id
    else:
        # 기본값 사용
        user_id = "default_user"
```

### 4. 동적 도구 바인딩 실패

**문제**: Context의 available_tools가 제대로 바인딩되지 않음

**해결**:
```python
def llm_node(state: State, runtime: Runtime[ContextSchema]):
    # 도구를 먼저 로드하고 검증
    if runtime.context.available_tools:
        tools = []
        for tool_name in runtime.context.available_tools:
            tool = load_tool(tool_name)
            if tool:
                tools.append(tool)
        
        if tools:
            model = model.bind_tools(tools)
```

## 베스트 프랙티스

### 1. Context 설계 원칙
- 불변 데이터만 Context에 포함
- 자주 변경되는 데이터는 State 사용
- 민감한 정보는 암호화하거나 별도 관리

### 2. 타입 안전성
- 항상 타입 힌트 사용
- Runtime[ContextSchema] 형태로 명시
- Optional 필드는 명확히 표시

### 3. 성능 최적화
- Context 객체를 가볍게 유지
- 대용량 데이터는 참조만 저장
- 필요한 경우 lazy loading 패턴 사용

### 4. 테스트
```python
import pytest
from unittest.mock import Mock

def test_node_with_context():
    # Mock Runtime 생성
    mock_runtime = Mock()
    mock_runtime.context = ContextSchema(
        user_id="test_user",
        model_provider="openai"
    )
    
    # 노드 테스트
    result = my_node(test_state, mock_runtime)
    assert result["status"] == "success"
```

## 참고 자료

- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [Context API 가이드](https://langchain-ai.github.io/langgraph/agents/context/)
- [Runtime API 레퍼런스](https://langchain-ai.github.io/langgraph/reference/runtime/)
- [마이그레이션 가이드](https://langchain-ai.github.io/langgraph/migration/)

## 요약

LangGraph 0.6의 Context API는 다음과 같은 장점을 제공합니다:

1. **타입 안전성**: 명확한 스키마 정의와 타입 체킹
2. **의존성 주입**: 깔끔한 의존성 관리
3. **테스트 용이성**: Mock 객체를 통한 쉬운 테스트
4. **유지보수성**: 명확한 코드 구조와 문서화
5. **확장성**: 복잡한 엔터프라이즈 애플리케이션 지원

이 메뉴얼을 따라 구현하면 프로덕션 레벨의 견고한 챗봇을 구축할 수 있습니다.
