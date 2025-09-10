# LangGraph 0.6 Context API 코딩 규칙 (RULES.md)

## 🎯 목적
이 문서는 LangGraph 0.6 Context API를 사용한 챗봇 개발 시 준수해야 할 코딩 규칙과 베스트 프랙티스를 정의합니다.

## 📋 일반 규칙

### 1. 버전 요구사항
- **필수**: LangGraph >= 0.6.0
- **권장**: Python >= 3.9 (dataclass와 타입 힌트 완전 지원)
- **금지**: config_schema 사용 (deprecated)

### 2. 임포트 규칙
```python
# ✅ 올바른 임포트 순서
# 1. 표준 라이브러리
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import uuid

# 2. 서드파티 라이브러리
from langchain_core.messages import AnyMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime, get_runtime

# 3. 로컬 모듈
from .context import ContextSchema
from .state import State
```

## 🏗️ Context API 구현 규칙

### RULE 1: Context 스키마 정의

#### 1.1 필수 사용 패턴
```python
# ✅ GOOD: dataclass 사용 (권장)
@dataclass
class ContextSchema:
    user_id: str  # 필수 필드
    model_provider: str = "anthropic"  # 기본값 있는 필드
    api_key: Optional[str] = None  # 선택적 필드

# ⚠️ ACCEPTABLE: TypedDict 사용
class ContextSchema(TypedDict, total=False):
    user_id: str
    model_provider: str

# ❌ BAD: 일반 dict 사용
context = {"user_id": "123"}  # 타입 안전성 없음
```

#### 1.2 Context 명명 규칙
- 클래스명은 `Context` 또는 `*Context` 형태 (예: `ChatbotContext`, `AgentContext`)
- 변수명은 `context` 사용
- 파일명은 `context.py` 또는 `{domain}_context.py`

#### 1.3 Context 설계 원칙
```python
@dataclass
class ContextSchema:
    # ✅ GOOD: 불변 데이터
    user_id: str
    api_endpoint: str
    max_retries: int = 3
    
    # ❌ BAD: 가변 데이터 (State에 포함되어야 함)
    # current_message: str  # State로 이동
    # conversation_history: List  # State로 이동
    # retry_count: int  # State로 이동
```

### RULE 2: State 정의

#### 2.1 State 구조
```python
# ✅ GOOD: 명확한 타입 힌트와 Annotated 사용
from typing import Annotated
from langgraph.graph import add_messages

class State(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    current_step: str
    metadata: Dict[str, Any]

# ❌ BAD: 타입 힌트 없음
class State(TypedDict):
    messages: list  # 구체적인 타입 명시 필요
    data: Any  # 너무 모호함
```

#### 2.2 State 명명 규칙
- 클래스명은 `State` 또는 `*State` 형태 (예: `ChatbotState`, `WorkflowState`)
- 변수명은 `state` 사용
- 파일명은 `state.py` 또는 `{domain}_state.py`

### RULE 3: 노드 함수 시그니처

#### 3.1 필수 시그니처 패턴
```python
# ✅ GOOD: Runtime 타입 파라미터 명시
def my_node(
    state: State, 
    runtime: Runtime[ContextSchema]
) -> Dict[str, Any]:
    user_id = runtime.context.user_id
    return {"result": "processed"}

# ❌ BAD: 이전 방식 (deprecated)
def old_node(state: State, config: RunnableConfig):
    user_id = config["configurable"]["user_id"]  # 금지
    return {"result": "processed"}

# ❌ BAD: 타입 힌트 없음
def bad_node(state, runtime):  # 타입 명시 필요
    pass
```

#### 3.2 Runtime 접근 패턴
```python
def node(state: State, runtime: Runtime[ContextSchema]) -> Dict[str, Any]:
    # ✅ GOOD: 명시적 속성 접근
    user_id = runtime.context.user_id
    model = runtime.context.model_provider
    
    # ✅ GOOD: None 체크
    if runtime.store:
        data = runtime.store.get(("key",))
    
    # ❌ BAD: 체크 없이 접근
    # data = runtime.store.get(("key",))  # store가 None일 수 있음
    
    # ❌ BAD: dict 스타일 접근
    # user_id = runtime.context["user_id"]  # 속성 접근 사용
```

### RULE 4: 도구 내 Context 접근

#### 4.1 get_runtime 사용
```python
# ✅ GOOD: get_runtime으로 Context 접근
from langgraph.runtime import get_runtime

@tool
def my_tool(param: str) -> str:
    """도구 설명"""
    runtime = get_runtime(ContextSchema)
    user_id = runtime.context.user_id
    # 도구 로직
    return result

# ❌ BAD: Context를 파라미터로 전달
@tool
def bad_tool(param: str, context: ContextSchema) -> str:  # 금지
    pass
```

### RULE 5: 그래프 생성 및 컴파일

#### 5.1 그래프 빌더 패턴
```python
# ✅ GOOD: context_schema 사용
builder = StateGraph(
    state_schema=State,
    context_schema=ContextSchema  # 필수
)

# ❌ BAD: config_schema 사용 (deprecated)
builder = StateGraph(
    state_schema=State,
    config_schema=ConfigSchema  # 금지
)

# ❌ BAD: context_schema 누락
builder = StateGraph(State)  # Context 스키마 명시 필요
```

#### 5.2 노드 추가 규칙
```python
# ✅ GOOD: 명확한 노드명과 함수
builder.add_node("preprocess", preprocess_node)
builder.add_node("llm", llm_node)

# ❌ BAD: 람다 함수 직접 사용
builder.add_node("node", lambda s, r: {...})  # 별도 함수로 분리
```

### RULE 6: 그래프 실행

#### 6.1 invoke 패턴
```python
# ✅ GOOD: context 파라미터 사용
result = graph.invoke(
    input_state,
    context={"user_id": "123", "model_provider": "openai"},
    config={"configurable": {"thread_id": "thread_123"}}  # thread_id는 config에
)

# ❌ BAD: config에 context 데이터 전달
result = graph.invoke(
    input_state,
    config={"configurable": {"user_id": "123"}}  # context로 이동 필요
)
```

#### 6.2 스트리밍 패턴
```python
# ✅ GOOD: 스트림에도 context 전달
for chunk in graph.stream(
    input_state,
    context=context_data,
    stream_mode="values"
):
    process_chunk(chunk)

# ✅ GOOD: 비동기 스트리밍
async for chunk in graph.astream(
    input_state,
    context=context_data
):
    await process_chunk(chunk)
```

## 🎨 코드 스타일 규칙

### RULE 7: 명명 규칙

#### 7.1 변수 및 함수명
```python
# ✅ GOOD
user_id = runtime.context.user_id
def process_message(state: State, runtime: Runtime[ContextSchema]):
    pass

# ❌ BAD
userId = runtime.context.user_id  # camelCase 금지
def ProcessMessage(state, runtime):  # PascalCase는 클래스용
    pass
```

#### 7.2 상수
```python
# ✅ GOOD
DEFAULT_MODEL = "claude-3-5-haiku"
MAX_RETRIES = 3

# ❌ BAD
default_model = "claude-3-5-haiku"  # 대문자 사용
```

### RULE 8: 타입 힌트

#### 8.1 필수 타입 힌트
```python
# ✅ GOOD: 완전한 타입 힌트
def process(
    messages: List[AnyMessage],
    temperature: float = 0.7
) -> Dict[str, Any]:
    pass

# ❌ BAD: 타입 힌트 누락
def process(messages, temperature=0.7):
    pass
```

#### 8.2 Optional 사용
```python
# ✅ GOOD: Optional 명시
from typing import Optional

@dataclass
class Context:
    api_key: Optional[str] = None
    
# ⚠️ ACCEPTABLE: Union 사용 (Python 3.10+)
api_key: str | None = None

# ❌ BAD: 모호한 타입
api_key = None  # 타입 불명확
```

## 🔒 보안 규칙

### RULE 9: 민감 정보 처리

#### 9.1 API 키 관리
```python
# ✅ GOOD: 환경 변수 사용
import os

@dataclass
class SecureContext:
    user_id: str
    _api_key: Optional[str] = None
    
    @property
    def api_key(self) -> str:
        return self._api_key or os.getenv("API_KEY")

# ❌ BAD: 하드코딩
@dataclass
class InsecureContext:
    api_key: str = "sk-abc123..."  # 절대 금지
```

#### 9.2 로깅 규칙
```python
# ✅ GOOD: 민감 정보 제외
import logging

def log_context(runtime: Runtime[ContextSchema]):
    logging.info(f"Processing for user: {runtime.context.user_id}")
    # api_key는 로깅하지 않음

# ❌ BAD: 전체 Context 로깅
logging.info(f"Context: {runtime.context}")  # 민감 정보 노출 위험
```

## ⚡ 성능 규칙

### RULE 10: Context 최적화

#### 10.1 Context 크기
```python
# ✅ GOOD: 필요한 정보만 포함
@dataclass
class OptimizedContext:
    user_id: str
    model_name: str
    
# ❌ BAD: 과도한 데이터
@dataclass
class BloatedContext:
    user_id: str
    entire_user_profile: dict  # 너무 큼
    all_conversation_history: list  # State로 이동
```

#### 10.2 Lazy Loading
```python
# ✅ GOOD: 필요시 로드
@dataclass
class LazyContext:
    user_id: str
    _user_profile: Optional[dict] = None
    
    @property
    def user_profile(self) -> dict:
        if self._user_profile is None:
            self._user_profile = load_profile(self.user_id)
        return self._user_profile
```

## 🧪 테스트 규칙

### RULE 11: 단위 테스트

#### 11.1 Mock Runtime
```python
# ✅ GOOD: Mock 사용
import pytest
from unittest.mock import Mock

def test_node():
    # Mock Runtime 생성
    mock_runtime = Mock()
    mock_runtime.context = ContextSchema(
        user_id="test_user",
        model_provider="test_model"
    )
    mock_runtime.store = None
    
    # 테스트 실행
    state = {"messages": []}
    result = my_node(state, mock_runtime)
    
    # 검증
    assert "result" in result
    assert mock_runtime.context.user_id == "test_user"
```

#### 11.2 Context 검증
```python
# ✅ GOOD: Context 유효성 테스트
def test_context_validation():
    with pytest.raises(TypeError):
        # 필수 필드 누락
        context = ContextSchema()  # user_id 필수
    
    # 정상 케이스
    context = ContextSchema(user_id="123")
    assert context.user_id == "123"
    assert context.model_provider == "anthropic"  # 기본값
```

## 🚨 에러 처리 규칙

### RULE 12: 예외 처리

#### 12.1 Runtime 체크
```python
# ✅ GOOD: None 체크와 예외 처리
def safe_node(state: State, runtime: Runtime[ContextSchema]) -> Dict[str, Any]:
    try:
        if not runtime or not runtime.context:
            raise ValueError("Runtime or context is missing")
        
        user_id = runtime.context.user_id
        
        if runtime.store:
            data = runtime.store.get(("key",))
        else:
            data = get_default_data()
            
        return {"status": "success", "data": data}
        
    except Exception as e:
        logging.error(f"Error in node: {e}")
        return {"status": "error", "error": str(e)}

# ❌ BAD: 체크 없이 접근
def unsafe_node(state: State, runtime: Runtime[ContextSchema]):
    data = runtime.store.get(("key",))  # store가 None일 수 있음
    return {"data": data}
```

#### 12.2 Context 기본값
```python
# ✅ GOOD: 기본값 처리
def node_with_defaults(state: State, runtime: Runtime[ContextSchema]):
    model = getattr(runtime.context, 'model_provider', 'gpt-3.5-turbo')
    temperature = getattr(runtime.context, 'temperature', 0.7)
    
    # 또는
    model = runtime.context.model_provider if runtime.context else 'gpt-3.5-turbo'
```

## 📝 문서화 규칙

### RULE 13: Docstring

#### 13.1 노드 문서화
```python
# ✅ GOOD: 완전한 문서화
def process_node(
    state: State,
    runtime: Runtime[ContextSchema]
) -> Dict[str, Any]:
    """
    메시지를 처리하고 응답을 생성합니다.
    
    Args:
        state: 현재 그래프 상태
        runtime: 런타임 컨텍스트와 유틸리티
        
    Returns:
        Dict[str, Any]: 업데이트할 상태 필드
        
    Raises:
        ValueError: Context가 유효하지 않은 경우
    """
    pass

# ❌ BAD: 문서화 없음
def process_node(state, runtime):
    pass
```

#### 13.2 Context 문서화
```python
# ✅ GOOD: 필드 설명
@dataclass
class DocumentedContext:
    """챗봇 런타임 컨텍스트
    
    Attributes:
        user_id: 사용자 고유 식별자
        model_provider: LLM 제공자 (openai, anthropic 등)
        temperature: 생성 온도 (0.0-2.0)
    """
    user_id: str
    model_provider: Literal["openai", "anthropic"] = "anthropic"
    temperature: float = 0.7
```

## 🔄 마이그레이션 규칙

### RULE 14: 레거시 코드 처리

#### 14.1 점진적 마이그레이션
```python
# ✅ GOOD: 호환성 레이어
def migrate_config_to_context(config: dict) -> ContextSchema:
    """레거시 config를 Context로 변환"""
    configurable = config.get("configurable", {})
    return ContextSchema(
        user_id=configurable.get("user_id", "default"),
        model_provider=configurable.get("model", "anthropic")
    )

# 전환 기간 동안 사용
def transitional_node(state: State, runtime: Runtime[ContextSchema] = None, config: dict = None):
    if runtime and runtime.context:
        context = runtime.context
    elif config:
        context = migrate_config_to_context(config)
    else:
        raise ValueError("Neither runtime nor config provided")
```

#### 14.2 Deprecation 경고
```python
# ✅ GOOD: 명확한 경고
import warnings

def deprecated_function():
    warnings.warn(
        "This function is deprecated. Use new_function with Context API instead.",
        DeprecationWarning,
        stacklevel=2
    )
    # 레거시 로직
```

## ✅ 체크리스트

### 프로젝트 시작 시
- [ ] LangGraph 0.6.0 이상 설치 확인
- [ ] Python 3.9 이상 확인
- [ ] Context 스키마 정의
- [ ] State 스키마 정의
- [ ] 프로젝트 구조 설정

### 노드 구현 시
- [ ] 올바른 시그니처 사용 (state, runtime)
- [ ] Runtime 타입 파라미터 명시
- [ ] 반환 타입 명시
- [ ] 에러 처리 구현
- [ ] 문서화 작성

### 그래프 생성 시
- [ ] context_schema 파라미터 사용
- [ ] config_schema 사용하지 않음
- [ ] 노드 명확히 명명
- [ ] 엣지 올바르게 연결

### 실행 시
- [ ] context 파라미터로 데이터 전달
- [ ] thread_id는 config에 유지
- [ ] 스트리밍 시에도 context 전달

### 테스트 시
- [ ] Mock Runtime 사용
- [ ] Context 유효성 검증
- [ ] 에러 케이스 테스트
- [ ] 통합 테스트 실행

## 🚫 금지 사항

1. **절대 사용 금지**:
   - `config_schema` 파라미터
   - `config["configurable"]` 패턴
   - 타입 힌트 없는 함수
   - Context에 가변 데이터 포함
   - API 키 하드코딩

2. **권장하지 않음**:
   - 람다 함수를 노드로 직접 사용
   - Context 크기 과도하게 증가
   - 전체 Context 로깅
   - 동기/비동기 혼용

## 📚 참고 자료

- [LangGraph 0.6 릴리즈 노트](https://github.com/langchain-ai/langgraph/releases/tag/0.6.0)
- [Context API 공식 문서](https://langchain-ai.github.io/langgraph/agents/context/)
- [Runtime API 레퍼런스](https://langchain-ai.github.io/langgraph/reference/runtime/)
- [마이그레이션 가이드](https://langchain-ai.github.io/langgraph/migration/)

---

**버전**: 1.0.0  
**최종 수정**: 2025-01-10  
**작성자**: LangGraph 0.6 Context API 구현 팀

이 규칙은 LangGraph 0.6 이상 버전을 대상으로 하며, 향후 버전 업데이트에 따라 수정될 수 있습니다.
