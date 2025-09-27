# Supervisor 실행 흐름 상세 보고서

**생성일**: 2025-09-27
**목적**: 사용자 질의부터 최종 출력까지의 전체 실행 과정 추적
**예제 쿼리**: "강남역 근처 30평대 아파트 매매 시세 알려줘"

---

## 목차

1. [실행 흐름 개요](#1-실행-흐름-개요)
2. [Phase 1: 초기화 및 입력 검증](#2-phase-1-초기화-및-입력-검증)
3. [Phase 2: 그래프 실행 - START 노드](#3-phase-2-그래프-실행---start-노드)
4. [Phase 3: Intent Analysis 노드](#4-phase-3-intent-analysis-노드)
5. [Phase 4: Plan Building 노드](#5-phase-4-plan-building-노드)
6. [Phase 5: Agent Execution 노드](#6-phase-5-agent-execution-노드)
7. [Phase 6: Result Evaluation 노드](#7-phase-6-result-evaluation-노드)
8. [Phase 7: 조건부 라우팅 및 종료](#8-phase-7-조건부-라우팅-및-종료)
9. [전체 함수 호출 체인](#9-전체-함수-호출-체인)
10. [State 변화 타임라인](#10-state-변화-타임라인)
11. [에러 처리 및 재시도 메커니즘](#11-에러-처리-및-재시도-메커니즘)

---

## 1. 실행 흐름 개요

### 1.1 전체 아키텍처

```
사용자 입력: "강남역 근처 30평대 아파트 매매 시세 알려줘"
    ↓
┌─────────────────────────────────────────────────────────────┐
│  RealEstateSupervisor.process_query()                       │
│  [supervisor.py:211-244]                                     │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  BaseAgent.execute()                                         │
│  [base_agent.py:259-363]                                     │
│                                                              │
│  1. 입력 검증 (_validate_input)                              │
│  2. 초기 상태 생성 (_create_initial_state)                   │
│  3. 컨텍스트 생성 (_create_context)                          │
│  4. 워크플로우 컴파일 (with AsyncSqliteSaver)                │
│  5. app.ainvoke(state, config, context)                     │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  LangGraph StateGraph 실행                                   │
│  [supervisor.py:110-168]                                     │
│                                                              │
│  START                                                       │
│    ↓                                                         │
│  analyze_intent (의도 분석)                                   │
│    ↓                                                         │
│  build_plan (계획 수립)                                       │
│    ↓                                                         │
│  execute_agents (에이전트 실행)                               │
│    ↓                                                         │
│  evaluate_results (결과 평가)                                 │
│    ↓                                                         │
│  _should_retry (조건부 분기)                                  │
│    ├─ "retry" → execute_agents (재시도)                      │
│    └─ "end" → END (종료)                                     │
└─────────────────────────────────────────────────────────────┘
    ↓
최종 출력: final_output 반환
```

### 1.2 관련 파일 맵

| 파일 | 역할 | 주요 함수/클래스 |
|-----|------|----------------|
| `supervisor/supervisor.py` | 메인 오케스트레이터 | `RealEstateSupervisor`, `process_query`, `_build_graph`, `_should_retry` |
| `core/base_agent.py` | 에이전트 기본 클래스 | `BaseAgent.execute`, `_create_initial_state`, `_create_context` |
| `core/states.py` | 상태 스키마 정의 | `SupervisorState`, `create_supervisor_initial_state`, 리듀서 함수들 |
| `core/context.py` | 컨텍스트 정의 | `AgentContext`, `create_agent_context` |
| `supervisor/intent_analyzer.py` | 의도 분석 | `analyze_intent_node`, `call_llm_for_intent` |
| `supervisor/plan_builder.py` | 계획 수립 | `build_plan_node`, `build_plan_rule_based`, `call_llm_for_planning` |
| `supervisor/execution_coordinator.py` | 에이전트 실행 조정 | `execute_agents_node`, `execute_sequential`, `execute_parallel` |
| `supervisor/result_evaluator.py` | 결과 평가 | `evaluate_results_node`, `call_llm_for_evaluation`, `call_llm_for_formatting` |
| `supervisor/prompts.py` | LLM 프롬프트 | 프롬프트 템플릿 및 헬퍼 함수들 |

---

## 2. Phase 1: 초기화 및 입력 검증

### 2.1 사용자 입력

**예제 데이터**:
```python
query = "강남역 근처 30평대 아파트 매매 시세 알려줘"
user_id = "default_user"
session_id = "default_session"
```

### 2.2 process_query 호출

**파일**: `supervisor/supervisor.py`
**함수**: `async def process_query(query, user_id, session_id, config)`
**라인**: 211-244

**실행 흐름**:

```python
# 1. input_data 구성
input_data = {
    "query": "강남역 근처 30평대 아파트 매매 시세 알려줘",
    "user_id": "default_user",
    "session_id": "default_session"
}

# 2. execute() 호출
result = await self.execute(input_data, config)

# 3. 결과 추출
if result["status"] == "success":
    return result["data"].get("final_output", {})
else:
    return {"error": result.get("error"), "status": "failed"}
```

**호출 체인**:
```
supervisor.py:211 process_query()
    ↓
supervisor.py:236 → await self.execute(input_data, config)
    ↓
base_agent.py:259 → BaseAgent.execute()
```

### 2.3 BaseAgent.execute 진입

**파일**: `core/base_agent.py`
**함수**: `async def execute(input_data, config)`
**라인**: 259-363

#### Step 1: 입력 검증

**라인**: 276-281

```python
# _validate_input 호출
if not await self._validate_input(input_data):
    return {
        "status": "error",
        "error": "Invalid input data",
        "agent": self.agent_name
    }
```

**검증 로직** (`supervisor.py:170-193`):
```python
# 필수 필드 존재 확인
if "query" not in input_data:
    return False

# 타입 확인
if not isinstance(input_data["query"], str):
    return False

# 빈 문자열 확인
if len(input_data["query"].strip()) == 0:
    return False

return True
```

**결과**: ✅ 검증 통과

#### Step 2: 초기 상태 생성

**라인**: 284

```python
initial_state = self._create_initial_state(input_data)
```

**호출 체인**:
```
base_agent.py:284 → _create_initial_state()
    ↓
supervisor.py:195-209 → RealEstateSupervisor._create_initial_state()
    ↓
states.py:290-325 → create_supervisor_initial_state()
```

**생성된 초기 상태** (`states.py:290-325`):

```python
initial_state = {
    # 상태 필드
    "status": "pending",
    "execution_step": "initializing",
    "errors": [],
    "start_time": "2025-09-27T10:30:00.123456",  # ISO 형식

    # 입력 필드
    "query": "강남역 근처 30평대 아파트 매매 시세 알려줘",

    # 워크플로우 필드 (초기값 None)
    "intent": None,
    "execution_plan": None,
    "agent_results": {},
    "evaluation": None,
    "final_output": None,
    "end_time": None
}
```

**State Schema** (`states.py:145-200`):
- **SupervisorState**: TypedDict 기반 상태 스키마
- **필드 타입**:
  - `status`: str (덮어쓰기)
  - `execution_step`: str (덮어쓰기)
  - `errors`: Annotated[List[str], add] (누적)
  - `query`: str (덮어쓰기)
  - `intent`: Optional[Dict] (덮어쓰기)
  - `execution_plan`: Optional[Dict] (덮어쓰기)
  - `agent_results`: Annotated[Dict, merge_dicts] (병합)
  - `evaluation`: Optional[Dict] (덮어쓰기)
  - `final_output`: Optional[Dict] (덮어쓰기)

#### Step 3: 컨텍스트 생성

**라인**: 287

```python
context = self._create_context(input_data)
```

**호출 체인**:
```
base_agent.py:287 → _create_context()
    ↓
base_agent.py:108-128 → BaseAgent._create_context()
    ↓
context.py:67-100 → create_agent_context()
```

**생성된 컨텍스트** (`context.py:67-100`):

```python
context = {
    # 필수 필드
    "user_id": "default_user",
    "session_id": "default_session",

    # 자동 생성 필드
    "request_id": "req_a1b2c3d4",  # uuid 기반
    "timestamp": "2025-09-27T10:30:00.123456",  # ISO 형식

    # 선택적 필드
    "original_query": "강남역 근처 30평대 아파트 매매 시세 알려줘",
    "api_keys": {},  # 환경변수에서 로드됨
    "language": "ko",
    "debug_mode": False
}
```

**Context Schema** (`context.py:14-38`):
- **AgentContext**: TypedDict 기반 컨텍스트 스키마
- **READ-ONLY**: 실행 중 변경되지 않음
- **역할**: 메타데이터 및 런타임 설정 제공

#### Step 4: Config 준비

**라인**: 289-298

```python
if config is None:
    config = {}

# 기본 설정
config.setdefault("recursion_limit", 25)
config.setdefault("configurable", {})

# thread_id 설정 (session_id 사용)
config["configurable"]["thread_id"] = context.get("session_id", "default")
```

**최종 Config**:
```python
config = {
    "recursion_limit": 25,
    "timeout": 30,  # 기본값
    "configurable": {
        "thread_id": "default_session"
    }
}
```

#### Step 5: 워크플로우 검증

**라인**: 301-307

```python
if self.workflow is None:
    return {
        "status": "error",
        "error": "Workflow not initialized",
        "agent": self.agent_name
    }
```

**워크플로우 초기화 확인**:
- `_build_graph()` 호출 여부 확인 (생성자에서 호출됨)
- `self.workflow`가 `StateGraph` 인스턴스인지 확인

**결과**: ✅ 워크플로우 초기화됨

---

## 3. Phase 2: 그래프 실행 - START 노드

### 3.1 워크플로우 컴파일

**파일**: `core/base_agent.py`
**라인**: 310-311

```python
async with AsyncSqliteSaver.from_conn_string(str(self.checkpointer_path)) as checkpointer:
    app = self.workflow.compile(checkpointer=checkpointer)
```

**동작**:
1. SQLite 기반 체크포인터 생성
   - 경로: `checkpoints/real_estate_supervisor/real_estate_supervisor.db`
2. StateGraph 컴파일
   - 노드 연결 검증
   - 엣지 유효성 검사
   - 실행 가능한 애플리케이션 생성

### 3.2 그래프 구조 (복습)

**파일**: `supervisor/supervisor.py`
**함수**: `_build_graph()`
**라인**: 110-168

```python
self.workflow = StateGraph(
    state_schema=SupervisorState,
    context_schema=AgentContext
)

# 노드 추가
self.workflow.add_node("analyze_intent", analyze_intent_node)
self.workflow.add_node("build_plan", build_plan_node)
self.workflow.add_node("execute_agents", execute_agents_node)
self.workflow.add_node("evaluate_results", evaluate_results_node)

# 엣지 추가
self.workflow.add_edge(START, "analyze_intent")
self.workflow.add_edge("analyze_intent", "build_plan")
self.workflow.add_edge("build_plan", "execute_agents")
self.workflow.add_edge("execute_agents", "evaluate_results")

# 조건부 엣지
self.workflow.add_conditional_edges(
    "evaluate_results",
    self._should_retry,
    {
        "retry": "execute_agents",
        "end": END
    }
)
```

**그래프 시각화**:
```
      START
        ↓
[analyze_intent]
        ↓
  [build_plan]
        ↓
[execute_agents] ←─────┐
        ↓               │
[evaluate_results]      │
        ↓               │
   _should_retry        │
    ├─ retry ──────────┘
    └─ end → END
```

### 3.3 ainvoke 호출

**파일**: `core/base_agent.py`
**라인**: 318-325

```python
result = await asyncio.wait_for(
    app.ainvoke(
        initial_state,
        config=config,
        context=context
    ),
    timeout=30  # 30초
)
```

**동작**:
1. `initial_state`를 그래프의 시작 상태로 설정
2. `context`를 모든 노드에 전달 (Runtime을 통해 접근)
3. `config`로 실행 옵션 설정
4. START 노드부터 그래프 실행 시작

### 3.4 START 노드 처리

**동작**:
- LangGraph 내부에서 자동 처리
- `initial_state`를 첫 번째 노드(`analyze_intent`)로 전달
- 체크포인트 생성 (thread_id: "default_session")

**체크포인트 저장**:
```json
{
  "thread_id": "default_session",
  "checkpoint_id": "ckpt_00001",
  "state": {
    "status": "pending",
    "execution_step": "initializing",
    "query": "강남역 근처 30평대 아파트 매매 시세 알려줘",
    ...
  },
  "next": ["analyze_intent"]
}
```

---

## 4. Phase 3: Intent Analysis 노드

### 4.1 노드 진입

**파일**: `supervisor/intent_analyzer.py`
**함수**: `async def analyze_intent_node(state, runtime)`
**라인**: 70-117

**입력 State**:
```python
{
    "status": "pending",
    "execution_step": "initializing",
    "errors": [],
    "start_time": "2025-09-27T10:30:00.123456",
    "query": "강남역 근처 30평대 아파트 매매 시세 알려줘",
    "intent": None,
    "execution_plan": None,
    "agent_results": {},
    "evaluation": None,
    "final_output": None,
    "end_time": None
}
```

### 4.2 컨텍스트 조회

**라인**: 83

```python
ctx = await runtime.context()
```

**조회된 컨텍스트**:
```python
{
    "user_id": "default_user",
    "session_id": "default_session",
    "request_id": "req_a1b2c3d4",
    "timestamp": "2025-09-27T10:30:00.123456",
    "original_query": "강남역 근처 30평대 아파트 매매 시세 알려줘",
    "api_keys": {
        "openai_api_key": "sk-..."  # 환경변수에서 로드
    },
    "language": "ko",
    "debug_mode": False
}
```

### 4.3 쿼리 추출

**라인**: 85-86

```python
query = state["query"]
logger.info(f"Analyzing intent for query: {query}")
```

**로그 출력**:
```
INFO - Analyzing intent for query: 강남역 근처 30평대 아파트 매매 시세 알려줘
```

### 4.4 API 키 확인

**라인**: 89-98

```python
api_keys = ctx.get("api_keys", {})
openai_api_key = api_keys.get("openai_api_key") or os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    logger.error("OpenAI API key not found in context or environment")
    return {
        "status": "failed",
        "errors": ["OpenAI API key not found"],
        "execution_step": "failed"
    }
```

**결과**: ✅ API 키 확인됨

### 4.5 LLM 호출 (의도 분석)

**라인**: 101

```python
intent = await call_llm_for_intent(query, openai_api_key)
```

#### call_llm_for_intent 상세

**파일**: `supervisor/intent_analyzer.py`
**함수**: `async def call_llm_for_intent(query, api_key)`
**라인**: 18-67

**Step 1: OpenAI 클라이언트 생성**

```python
from openai import AsyncOpenAI
client = AsyncOpenAI(api_key=api_key)
```

**Step 2: 프롬프트 생성**

```python
from .prompts import get_intent_analysis_prompt
prompt = get_intent_analysis_prompt(query)
```

**프롬프트 내용** (`prompts.py:9-39`):
```
당신은 부동산 챗봇의 의도 분석 전문가입니다. 사용자의 질문을 분석하여 다음 정보를 JSON 형식으로 추출하세요.

**추출할 정보:**
1. intent_type: 질문의 유형
   - "search": 매물 검색
   - "analysis": 시세 분석
   - "comparison": 지역 비교
   - "recommendation": 추천

2. region: 지역명
3. property_type: 매물 유형 ("아파트", "오피스텔", "빌라", "단독주택")
4. deal_type: 거래 유형 ("매매", "전세", "월세")
5. price_range: 가격 범위
6. size_range: 평형 범위

**사용자 질문:**
강남역 근처 30평대 아파트 매매 시세 알려줘

**응답 형식 (JSON):**
{
  "intent_type": "search",
  "region": "서울특별시 강남구",
  "property_type": "아파트",
  "deal_type": "매매",
  "price_range": {"min": 100000, "max": 150000},
  "size_range": {"min": 30, "max": 40}
}

**중요:** JSON 형식으로만 응답하고, 추가 설명은 하지 마세요.
```

**Step 3: LLM API 호출**

```python
response = await client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {
            "role": "system",
            "content": "You are an expert in analyzing real estate queries. Always respond in JSON format."
        },
        {
            "role": "user",
            "content": prompt
        }
    ],
    temperature=0.3,
    max_tokens=500
)
```

**LLM 파라미터**:
- **모델**: gpt-4o-mini (빠르고 비용 효율적)
- **temperature**: 0.3 (일관성 있는 분석)
- **max_tokens**: 500 (충분한 응답 길이)

**Step 4: 응답 파싱**

```python
content = response.choices[0].message.content.strip()
intent = json.loads(content)
```

**파싱된 Intent**:
```python
{
    "intent_type": "analysis",  # "시세 알려줘" → 시세 분석
    "region": "서울특별시 강남구",
    "property_type": "아파트",
    "deal_type": "매매",
    "price_range": None,  # 명시되지 않음
    "size_range": {"min": 30, "max": 40}  # "30평대"
}
```

**에러 처리**:
```python
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse LLM response as JSON: {e}")
    return {
        "intent_type": "search",
        "region": None,
        "property_type": None,
        "deal_type": None,
        "price_range": None,
        "size_range": None
    }
```

### 4.6 상태 업데이트 반환

**라인**: 103-109

```python
logger.info(f"Intent analysis completed: {intent}")

return {
    "intent": intent,
    "status": "processing",
    "execution_step": "planning"
}
```

**반환된 State Update**:
```python
{
    "intent": {
        "intent_type": "analysis",
        "region": "서울특별시 강남구",
        "property_type": "아파트",
        "deal_type": "매매",
        "price_range": None,
        "size_range": {"min": 30, "max": 40}
    },
    "status": "processing",
    "execution_step": "planning"
}
```

### 4.7 State 병합 (LangGraph 자동 처리)

**병합 규칙** (`states.py:145-200`):
- `intent`: 덮어쓰기 (Optional[Dict])
- `status`: 덮어쓰기 (str)
- `execution_step`: 덮어쓰기 (str)

**병합 후 State**:
```python
{
    "status": "processing",  # ✅ 업데이트됨
    "execution_step": "planning",  # ✅ 업데이트됨
    "errors": [],
    "start_time": "2025-09-27T10:30:00.123456",
    "query": "강남역 근처 30평대 아파트 매매 시세 알려줘",
    "intent": {  # ✅ 새로 추가됨
        "intent_type": "analysis",
        "region": "서울특별시 강남구",
        "property_type": "아파트",
        "deal_type": "매매",
        "price_range": None,
        "size_range": {"min": 30, "max": 40}
    },
    "execution_plan": None,
    "agent_results": {},
    "evaluation": None,
    "final_output": None,
    "end_time": None
}
```

### 4.8 체크포인트 저장

**LangGraph 자동 처리**:
```json
{
  "thread_id": "default_session",
  "checkpoint_id": "ckpt_00002",
  "state": {
    "status": "processing",
    "execution_step": "planning",
    "intent": {...},
    ...
  },
  "next": ["build_plan"]
}
```

---

## 5. Phase 4: Plan Building 노드

### 5.1 노드 진입

**파일**: `supervisor/plan_builder.py`
**함수**: `async def build_plan_node(state, runtime)`
**라인**: 172-215

**입력 State** (이전 단계에서 병합됨):
```python
{
    "status": "processing",
    "execution_step": "planning",
    "errors": [],
    "start_time": "2025-09-27T10:30:00.123456",
    "query": "강남역 근처 30평대 아파트 매매 시세 알려줘",
    "intent": {
        "intent_type": "analysis",
        "region": "서울특별시 강남구",
        "property_type": "아파트",
        "deal_type": "매매",
        "price_range": None,
        "size_range": {"min": 30, "max": 40}
    },
    "execution_plan": None,
    "agent_results": {},
    "evaluation": None,
    "final_output": None,
    "end_time": None
}
```

### 5.2 컨텍스트 조회 및 Intent 추출

**라인**: 185-188

```python
ctx = await runtime.context()
intent = state["intent"]
logger.info(f"Building execution plan for intent type: {intent.get('intent_type')}")
```

**로그 출력**:
```
INFO - Building execution plan for intent type: analysis
```

### 5.3 API 키 확인

**라인**: 191-192

```python
api_keys = ctx.get("api_keys", {})
openai_api_key = api_keys.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
```

### 5.4 계획 수립 (LLM 또는 규칙 기반)

**라인**: 194-199

```python
if not openai_api_key:
    logger.warning("OpenAI API key not found, using rule-based planning")
    execution_plan = build_plan_rule_based(intent)
else:
    # Try LLM-based planning first
    execution_plan = await call_llm_for_planning(intent, openai_api_key)
```

#### 경로 1: LLM 기반 계획 수립

**함수**: `async def call_llm_for_planning(intent, api_key)`
**라인**: 128-169

**Step 1: 프롬프트 생성**

```python
from .prompts import get_plan_building_prompt
prompt = get_plan_building_prompt(intent)
```

**프롬프트 내용** (`prompts.py:42-89`):
```
당신은 부동산 챗봇의 실행 계획 수립 전문가입니다.

**사용 가능한 Agent:**
1. property_search: 매물 검색
2. market_analysis: 시장 분석
3. region_comparison: 지역 비교
4. investment_advisor: 투자 자문

**실행 전략:**
- "sequential": 순차 실행
- "parallel": 병렬 실행
- "dag": DAG 방식

**사용자 의도:**
{
  "intent_type": "analysis",
  "region": "서울특별시 강남구",
  "property_type": "아파트",
  "deal_type": "매매",
  "size_range": {"min": 30, "max": 40}
}

**규칙:**
1. intent_type이 "search"면 property_search만
2. intent_type이 "analysis"면 property_search + market_analysis
3. intent_type이 "comparison"면 property_search + region_comparison
4. intent_type이 "recommendation"면 모든 Agent

**응답 형식 (JSON):**
{
  "strategy": "sequential",
  "agents": [...]
}
```

**Step 2: LLM API 호출**

```python
response = await client.chat.completions.create(
    model="gpt-4o",  # 더 정확한 계획 수립
    messages=[
        {
            "role": "system",
            "content": "You are an expert in planning agent execution strategies. Always respond in JSON format."
        },
        {
            "role": "user",
            "content": prompt
        }
    ],
    temperature=0.3,
    max_tokens=2000
)
```

**LLM 응답**:
```json
{
  "strategy": "sequential",
  "agents": [
    {
      "name": "property_search",
      "order": 1,
      "params": {
        "region": "서울특별시 강남구",
        "property_type": "아파트",
        "deal_type": "매매",
        "size_range": {"min": 30, "max": 40}
      }
    },
    {
      "name": "market_analysis",
      "order": 2,
      "params": {
        "region": "서울특별시 강남구",
        "property_type": "아파트"
      }
    }
  ]
}
```

**에러 처리**:
```python
except json.JSONDecodeError as e:
    logger.warning(f"Failed to parse LLM response, using rule-based planning: {e}")
    return build_plan_rule_based(intent)
```

#### 경로 2: 규칙 기반 계획 수립 (폴백)

**함수**: `def build_plan_rule_based(intent)`
**라인**: 18-125

**로직**:
```python
intent_type = intent.get("intent_type", "search")

if intent_type == "analysis":
    agents = [
        {
            "name": "property_search",
            "order": 1,
            "params": {
                "region": intent.get("region"),
                "property_type": intent.get("property_type"),
                "deal_type": intent.get("deal_type")
            }
        },
        {
            "name": "market_analysis",
            "order": 2,
            "params": {
                "region": intent.get("region"),
                "property_type": intent.get("property_type")
            }
        }
    ]
    strategy = "sequential"
```

**생성된 Plan** (동일):
```python
{
    "strategy": "sequential",
    "agents": [
        {
            "name": "property_search",
            "order": 1,
            "params": {
                "region": "서울특별시 강남구",
                "property_type": "아파트",
                "deal_type": "매매",
                "size_range": {"min": 30, "max": 40}
            }
        },
        {
            "name": "market_analysis",
            "order": 2,
            "params": {
                "region": "서울특별시 강남구",
                "property_type": "아파트"
            }
        }
    ]
}
```

### 5.5 상태 업데이트 반환

**라인**: 201-207

```python
logger.info(f"Execution plan built: {execution_plan}")

return {
    "execution_plan": execution_plan,
    "status": "processing",
    "execution_step": "executing_agents"
}
```

### 5.6 State 병합 후

```python
{
    "status": "processing",
    "execution_step": "executing_agents",  # ✅ 업데이트됨
    "errors": [],
    "start_time": "2025-09-27T10:30:00.123456",
    "query": "강남역 근처 30평대 아파트 매매 시세 알려줘",
    "intent": {...},
    "execution_plan": {  # ✅ 새로 추가됨
        "strategy": "sequential",
        "agents": [
            {"name": "property_search", "order": 1, "params": {...}},
            {"name": "market_analysis", "order": 2, "params": {...}}
        ]
    },
    "agent_results": {},
    "evaluation": None,
    "final_output": None,
    "end_time": None
}
```

---

## 6. Phase 5: Agent Execution 노드

### 6.1 노드 진입

**파일**: `supervisor/execution_coordinator.py`
**함수**: `async def execute_agents_node(state, runtime)`
**라인**: 166-215

**입력 State**:
```python
{
    "status": "processing",
    "execution_step": "executing_agents",
    "errors": [],
    "start_time": "2025-09-27T10:30:00.123456",
    "query": "강남역 근처 30평대 아파트 매매 시세 알려줘",
    "intent": {...},
    "execution_plan": {
        "strategy": "sequential",
        "agents": [
            {"name": "property_search", "order": 1, "params": {...}},
            {"name": "market_analysis", "order": 2, "params": {...}}
        ]
    },
    "agent_results": {},
    "evaluation": None,
    "final_output": None,
    "end_time": None
}
```

### 6.2 컨텍스트 및 Plan 추출

**라인**: 179-183

```python
ctx = await runtime.context()
execution_plan = state["execution_plan"]
strategy = execution_plan.get("strategy", "sequential")
agents = execution_plan.get("agents", [])

logger.info(f"Executing {len(agents)} agents using {strategy} strategy")
```

**로그 출력**:
```
INFO - Executing 2 agents using sequential strategy
```

### 6.3 실행 전략 분기

**라인**: 186-193

```python
if strategy == "parallel":
    agent_results = await execute_parallel(agents, ctx)
elif strategy == "dag":
    agent_results = await execute_dag(agents, ctx)
else:  # default: sequential
    agent_results = await execute_sequential(agents, ctx)
```

**현재 예제**: `sequential` 전략 선택

### 6.4 순차 실행 (execute_sequential)

**함수**: `async def execute_sequential(agents, ctx)`
**라인**: 89-114

**Step 1: 에이전트 정렬**

```python
sorted_agents = sorted(agents, key=lambda x: x.get("order", 0))
```

**정렬된 에이전트**:
```python
[
    {"name": "property_search", "order": 1, "params": {...}},
    {"name": "market_analysis", "order": 2, "params": {...}}
]
```

**Step 2: 순차 실행 (에이전트 1 - property_search)**

```python
for agent_config in sorted_agents:
    agent_name, result = await execute_agent(agent_config, ctx)
    results[agent_name] = result

    # 실패 시 중단
    if result.get("status") == "error":
        logger.warning(f"Agent {agent_name} failed, stopping sequential execution")
        break
```

#### execute_agent 상세

**함수**: `async def execute_agent(agent_config, ctx)`
**라인**: 54-86

**Step 2.1: 에이전트 로드**

```python
agent_name = agent_config["name"]  # "property_search"
params = agent_config.get("params", {})

logger.info(f"Executing agent: {agent_name}")

agent = get_agent(agent_name)
```

##### get_agent 상세

**함수**: `def get_agent(agent_name)`
**라인**: 15-51

**현재 구현**: Mock 에이전트 반환 (TODO: 실제 구현)

```python
class MockAgent:
    def __init__(self, name: str):
        self.name = name

    async def execute(self, params: Dict) -> Dict:
        logger.info(f"Mock agent {self.name} executing with params: {params}")
        return {
            "status": "success",
            "agent": self.name,
            "data": f"Mock result from {self.name}",
            "params": params
        }

return MockAgent(agent_name)
```

**향후 구현**:
```python
# TODO: 실제 에이전트 임포트
# from service.agents.property_search import PropertySearchAgent
# from service.agents.market_analysis import MarketAnalysisAgent
#
# agent_map = {
#     "property_search": PropertySearchAgent,
#     "market_analysis": MarketAnalysisAgent,
#     ...
# }
# return agent_map[agent_name]()
```

**Step 2.2: 에이전트 실행**

```python
result = await agent.execute(params)
logger.info(f"Agent {agent_name} completed successfully")
return agent_name, result
```

**에이전트 1 결과** (Mock):
```python
(
    "property_search",
    {
        "status": "success",
        "agent": "property_search",
        "data": "Mock result from property_search",
        "params": {
            "region": "서울특별시 강남구",
            "property_type": "아파트",
            "deal_type": "매매",
            "size_range": {"min": 30, "max": 40}
        }
    }
)
```

**Step 3: 순차 실행 (에이전트 2 - market_analysis)**

동일한 과정 반복:

**에이전트 2 결과** (Mock):
```python
(
    "market_analysis",
    {
        "status": "success",
        "agent": "market_analysis",
        "data": "Mock result from market_analysis",
        "params": {
            "region": "서울특별시 강남구",
            "property_type": "아파트"
        }
    }
)
```

**Step 4: 결과 누적**

```python
results = {
    "property_search": {
        "status": "success",
        "agent": "property_search",
        "data": "Mock result from property_search",
        "params": {...}
    },
    "market_analysis": {
        "status": "success",
        "agent": "market_analysis",
        "data": "Mock result from market_analysis",
        "params": {...}
    }
}
```

### 6.5 실행 결과 확인

**라인**: 195-200

```python
logger.info(f"Agent execution completed: {len(agent_results)} results")

# Check if any agent failed
failed_agents = [name for name, result in agent_results.items() if result.get("status") == "error"]

if failed_agents:
    logger.warning(f"Some agents failed: {failed_agents}")
```

**로그 출력**:
```
INFO - Agent execution completed: 2 results
```

**실패 에이전트**: 없음 ✅

### 6.6 상태 업데이트 반환

**라인**: 202-207

```python
return {
    "agent_results": agent_results,
    "status": "processing",
    "execution_step": "evaluating"
}
```

### 6.7 State 병합 후

**병합 규칙**: `agent_results`는 `merge_dicts` 리듀서 사용

```python
{
    "status": "processing",
    "execution_step": "evaluating",  # ✅ 업데이트됨
    "errors": [],
    "start_time": "2025-09-27T10:30:00.123456",
    "query": "강남역 근처 30평대 아파트 매매 시세 알려줘",
    "intent": {...},
    "execution_plan": {...},
    "agent_results": {  # ✅ 병합됨
        "property_search": {
            "status": "success",
            "agent": "property_search",
            "data": "Mock result from property_search",
            "params": {...}
        },
        "market_analysis": {
            "status": "success",
            "agent": "market_analysis",
            "data": "Mock result from market_analysis",
            "params": {...}
        }
    },
    "evaluation": None,
    "final_output": None,
    "end_time": None
}
```

---

## 7. Phase 6: Result Evaluation 노드

### 7.1 노드 진입

**파일**: `supervisor/result_evaluator.py`
**함수**: `async def evaluate_results_node(state, runtime)`
**라인**: 188-255

**입력 State**:
```python
{
    "status": "processing",
    "execution_step": "evaluating",
    "errors": [],
    "start_time": "2025-09-27T10:30:00.123456",
    "query": "강남역 근처 30평대 아파트 매매 시세 알려줘",
    "intent": {...},
    "execution_plan": {...},
    "agent_results": {
        "property_search": {"status": "success", ...},
        "market_analysis": {"status": "success", ...}
    },
    "evaluation": None,
    "final_output": None,
    "end_time": None
}
```

### 7.2 컨텍스트 및 데이터 추출

**라인**: 201-206

```python
ctx = await runtime.context()
agent_results = state["agent_results"]
query = state["query"]

logger.info(f"Evaluating results from {len(agent_results)} agents")
```

**로그 출력**:
```
INFO - Evaluating results from 2 agents
```

### 7.3 API 키 확인

**라인**: 209-210

```python
api_keys = ctx.get("api_keys", {})
openai_api_key = api_keys.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
```

### 7.4 품질 평가

**라인**: 213-217

```python
if openai_api_key:
    evaluation = await call_llm_for_evaluation(agent_results, openai_api_key)
else:
    logger.warning("OpenAI API key not found, using rule-based evaluation")
    evaluation = evaluate_quality_rule_based(agent_results)
```

#### 경로 1: LLM 기반 평가

**함수**: `async def call_llm_for_evaluation(agent_results, api_key)`
**라인**: 57-98

**Step 1: 프롬프트 생성**

```python
from .prompts import get_evaluation_prompt
prompt = get_evaluation_prompt(agent_results)
```

**프롬프트 내용** (`prompts.py:92-120`):
```
당신은 부동산 챗봇의 결과 평가 전문가입니다.

**Agent 실행 결과:**
{
  "property_search": {
    "status": "success",
    "data": "Mock result from property_search",
    ...
  },
  "market_analysis": {
    "status": "success",
    "data": "Mock result from market_analysis",
    ...
  }
}

**평가 기준:**
1. **완전성 (completeness):** 모든 필요한 데이터가 수집되었는가?
2. **정확성 (accuracy):** 데이터가 정확하고 신뢰할 수 있는가?
3. **일관성 (consistency):** Agent 결과들이 서로 모순되지 않는가?

**응답 형식 (JSON):**
{
  "quality_score": 0.85,
  "completeness": true,
  "accuracy": true,
  "consistency": true,
  "needs_retry": false,
  "retry_agents": [],
  "feedback": "모든 데이터가 성공적으로 수집되었습니다."
}

**재시도 조건:**
- Agent가 에러를 반환했을 때
- 데이터가 불완전할 때
- 데이터가 부정확할 때
```

**Step 2: LLM API 호출**

```python
response = await client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {
            "role": "system",
            "content": "You are an expert in evaluating agent execution results. Always respond in JSON format."
        },
        {
            "role": "user",
            "content": prompt
        }
    ],
    temperature=0.3,
    max_tokens=1000
)
```

**LLM 응답**:
```json
{
  "quality_score": 1.0,
  "completeness": true,
  "accuracy": true,
  "consistency": true,
  "needs_retry": false,
  "retry_agents": [],
  "feedback": "모든 에이전트가 성공적으로 실행되었고, 필요한 데이터가 모두 수집되었습니다."
}
```

#### 경로 2: 규칙 기반 평가 (폴백)

**함수**: `def evaluate_quality_rule_based(agent_results)`
**라인**: 18-54

**로직**:
```python
# 모든 에이전트 성공 여부
all_success = all(result.get("status") == "success" for result in agent_results.values())

# 데이터 존재 여부
has_data = any(result.get("data") for result in agent_results.values())

# 실패한 에이전트
failed_agents = [name for name, result in agent_results.items() if result.get("status") == "error"]

# 품질 점수 계산
total_agents = len(agent_results)
successful_agents = total_agents - len(failed_agents)
quality_score = successful_agents / total_agents if total_agents > 0 else 0.0

# 재시도 필요 여부
needs_retry = not all_success and len(failed_agents) > 0

return {
    "quality_score": quality_score,
    "completeness": all_success and has_data,
    "accuracy": True,  # LLM 없이는 판단 불가
    "consistency": True,  # LLM 없이는 판단 불가
    "needs_retry": needs_retry,
    "retry_agents": failed_agents,
    "feedback": f"Rule-based evaluation: {successful_agents}/{total_agents} agents succeeded"
}
```

**평가 결과** (예제에서는 모두 성공):
```python
{
    "quality_score": 1.0,
    "completeness": True,
    "accuracy": True,
    "consistency": True,
    "needs_retry": False,
    "retry_agents": [],
    "feedback": "모든 에이전트가 성공적으로 실행되었고, 필요한 데이터가 모두 수집되었습니다."
}
```

### 7.5 재시도 필요 여부 확인

**라인**: 222-230

```python
if evaluation.get("needs_retry", False):
    retry_agents = evaluation.get("retry_agents", [])
    logger.warning(f"Retry needed for agents: {retry_agents}")

    return {
        "evaluation": evaluation,
        "status": "processing",
        "execution_step": "executing_agents"  # Go back to execution
    }
```

**현재 예제**: `needs_retry = False` → 재시도 불필요 ✅

### 7.6 최종 응답 포맷팅

**라인**: 233-237

```python
if openai_api_key:
    final_output = await call_llm_for_formatting(query, agent_results, openai_api_key)
else:
    logger.warning("OpenAI API key not found, using simple formatting")
    final_output = format_response_simple(query, agent_results)
```

#### 경로 1: LLM 기반 포맷팅

**함수**: `async def call_llm_for_formatting(query, agent_results, api_key)`
**라인**: 143-185

**Step 1: 프롬프트 생성**

```python
from .prompts import get_response_formatting_prompt
prompt = get_response_formatting_prompt(query, agent_results)
```

**프롬프트 내용** (`prompts.py:123-167`):
```
당신은 부동산 챗봇의 응답 생성 전문가입니다.

**사용자 질문:**
강남역 근처 30평대 아파트 매매 시세 알려줘

**Agent 결과:**
{
  "property_search": {...},
  "market_analysis": {...}
}

**응답 형식:**
1. **간단한 답변 (answer):** 2-3문장
2. **매물 목록 (listings):** 최대 10개
3. **인사이트 (insights):** bullet points
4. **메타데이터 (metadata):** 통계 정보

**응답 예시:**
{
  "answer": "강남구의 30평대 아파트 매매 시세는...",
  "listings": [...],
  "insights": [...],
  "metadata": {...}
}

**중요:** 한국어로, 사용자가 이해하기 쉽게, JSON 형식으로
```

**Step 2: LLM API 호출**

```python
response = await client.chat.completions.create(
    model="gpt-4o",  # 더 나은 응답 생성
    messages=[
        {
            "role": "system",
            "content": "You are an expert in formatting real estate information for users. Always respond in JSON format."
        },
        {
            "role": "user",
            "content": prompt
        }
    ],
    temperature=0.7,  # 더 자연스러운 응답
    max_tokens=2000
)
```

**LLM 응답**:
```json
{
  "answer": "강남구의 30평대 아파트 매매 시세를 분석한 결과, 평균 12억원 수준으로 형성되어 있습니다. 최근 3개월 간 약 5% 상승했으며, 강남역 인근 지역의 교통 접근성이 가격에 긍정적인 영향을 미치고 있습니다.",
  "listings": [
    {
      "name": "래미안 강남아파트",
      "region": "서울특별시 강남구 역삼동",
      "price": 1200000000,
      "size": 32,
      "deal_type": "매매"
    },
    {
      "name": "타워팰리스",
      "region": "서울특별시 강남구 대치동",
      "price": 1500000000,
      "size": 35,
      "deal_type": "매매"
    }
  ],
  "insights": [
    "강남구는 학군이 우수하여 수요가 지속적으로 높습니다",
    "지하철역 인근 매물의 가격이 평균 대비 15% 더 높습니다",
    "최근 신규 공급 부족으로 가격 상승세가 이어지고 있습니다",
    "30평대는 실수요자 선호도가 높아 유동성이 좋습니다"
  ],
  "metadata": {
    "total_listings": 2,
    "avg_price": 1350000000,
    "price_range": {"min": 1200000000, "max": 1500000000},
    "region": "서울특별시 강남구",
    "analysis_date": "2025-09-27"
  }
}
```

#### 경로 2: 단순 포맷팅 (폴백)

**함수**: `def format_response_simple(query, agent_results)`
**라인**: 101-140

**로직**:
```python
all_data = []
insights = []

for agent_name, result in agent_results.items():
    if result.get("status") == "success":
        data = result.get("data")
        if isinstance(data, list):
            all_data.extend(data)
        elif isinstance(data, dict):
            all_data.append(data)
        else:
            all_data.append({"agent": agent_name, "result": data})

        agent_insights = result.get("insights", [])
        if agent_insights:
            insights.extend(agent_insights)

return {
    "answer": f"검색 완료: {len(all_data)}개의 결과를 찾았습니다.",
    "listings": all_data[:10],
    "insights": insights,
    "metadata": {
        "total_results": len(all_data),
        "agents_used": list(agent_results.keys())
    }
}
```

### 7.7 상태 업데이트 반환

**라인**: 239-247

```python
logger.info(f"Final output generated successfully")

return {
    "evaluation": evaluation,
    "final_output": final_output,
    "status": "completed",
    "execution_step": "finished",
    "end_time": None  # Will be set by state factory
}
```

### 7.8 State 병합 후

```python
{
    "status": "completed",  # ✅ 업데이트됨
    "execution_step": "finished",  # ✅ 업데이트됨
    "errors": [],
    "start_time": "2025-09-27T10:30:00.123456",
    "query": "강남역 근처 30평대 아파트 매매 시세 알려줘",
    "intent": {...},
    "execution_plan": {...},
    "agent_results": {...},
    "evaluation": {  # ✅ 새로 추가됨
        "quality_score": 1.0,
        "completeness": True,
        "accuracy": True,
        "consistency": True,
        "needs_retry": False,
        "retry_agents": [],
        "feedback": "모든 에이전트가 성공적으로 실행되었습니다."
    },
    "final_output": {  # ✅ 새로 추가됨
        "answer": "강남구의 30평대 아파트 매매 시세를 분석한 결과...",
        "listings": [...],
        "insights": [...],
        "metadata": {...}
    },
    "end_time": None
}
```

---

## 8. Phase 7: 조건부 라우팅 및 종료

### 8.1 조건부 엣지 실행

**파일**: `supervisor/supervisor.py`
**함수**: `_should_retry(state)`
**라인**: 76-108

**실행**:
```python
evaluation = state.get("evaluation", {})
needs_retry = evaluation.get("needs_retry", False)
retry_count = state.get("retry_count", 0)

if needs_retry and retry_count < self.max_retries:
    logger.info(f"Retrying agent execution (attempt {retry_count + 1}/{self.max_retries})")
    return "retry"
else:
    if needs_retry:
        logger.warning(f"Max retries ({self.max_retries}) reached, proceeding with current results")
    return "end"
```

**현재 예제**:
- `needs_retry = False`
- **결과**: `"end"` 반환 → END 노드로 이동

### 8.2 END 노드 처리

**LangGraph 자동 처리**:
- 최종 체크포인트 저장
- 그래프 실행 종료
- 최종 상태 반환

**최종 체크포인트**:
```json
{
  "thread_id": "default_session",
  "checkpoint_id": "ckpt_00006",
  "state": {
    "status": "completed",
    "execution_step": "finished",
    "final_output": {...},
    ...
  },
  "next": []
}
```

### 8.3 ainvoke 완료

**파일**: `core/base_agent.py`
**라인**: 318-342

**반환값** (from ainvoke):
```python
result = {
    "status": "completed",
    "execution_step": "finished",
    "errors": [],
    "start_time": "2025-09-27T10:30:00.123456",
    "query": "강남역 근처 30평대 아파트 매매 시세 알려줘",
    "intent": {...},
    "execution_plan": {...},
    "agent_results": {...},
    "evaluation": {...},
    "final_output": {
        "answer": "강남구의 30평대 아파트 매매 시세를 분석한 결과...",
        "listings": [...],
        "insights": [...],
        "metadata": {...}
    },
    "end_time": None
}
```

**execute 메서드 반환**:
```python
return {
    "status": "success",
    "data": result,
    "agent": "real_estate_supervisor",
    "context": {
        "user_id": "default_user",
        "session_id": "default_session",
        "request_id": "req_a1b2c3d4"
    }
}
```

### 8.4 process_query 최종 반환

**파일**: `supervisor/supervisor.py`
**라인**: 236-244

```python
result = await self.execute(input_data, config)

if result["status"] == "success":
    return result["data"].get("final_output", {})
else:
    return {
        "error": result.get("error", "Unknown error"),
        "status": "failed"
    }
```

**최종 사용자 응답**:
```python
{
    "answer": "강남구의 30평대 아파트 매매 시세를 분석한 결과, 평균 12억원 수준으로 형성되어 있습니다. 최근 3개월 간 약 5% 상승했으며, 강남역 인근 지역의 교통 접근성이 가격에 긍정적인 영향을 미치고 있습니다.",
    "listings": [
        {
            "name": "래미안 강남아파트",
            "region": "서울특별시 강남구 역삼동",
            "price": 1200000000,
            "size": 32,
            "deal_type": "매매"
        },
        {
            "name": "타워팰리스",
            "region": "서울특별시 강남구 대치동",
            "price": 1500000000,
            "size": 35,
            "deal_type": "매매"
        }
    ],
    "insights": [
        "강남구는 학군이 우수하여 수요가 지속적으로 높습니다",
        "지하철역 인근 매물의 가격이 평균 대비 15% 더 높습니다",
        "최근 신규 공급 부족으로 가격 상승세가 이어지고 있습니다",
        "30평대는 실수요자 선호도가 높아 유동성이 좋습니다"
    ],
    "metadata": {
        "total_listings": 2,
        "avg_price": 1350000000,
        "price_range": {"min": 1200000000, "max": 1500000000},
        "region": "서울특별시 강남구",
        "analysis_date": "2025-09-27"
    }
}
```

---

## 9. 전체 함수 호출 체인

### 9.1 완전한 호출 스택 (라인 번호 포함)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. 사용자 입력                                                    │
└─────────────────────────────────────────────────────────────────┘
    ↓
supervisor/supervisor.py:211
    async def process_query(query, user_id, session_id, config)
        ↓
supervisor/supervisor.py:236
    result = await self.execute(input_data, config)
        ↓
core/base_agent.py:259
    async def execute(input_data, config)
        ↓
        ├─ Line 276: await self._validate_input(input_data)
        │   ↓
        │   supervisor/supervisor.py:170
        │       async def _validate_input(input_data)
        │       return True
        │
        ├─ Line 284: self._create_initial_state(input_data)
        │   ↓
        │   supervisor/supervisor.py:195
        │       def _create_initial_state(input_data)
        │           ↓
        │           core/states.py:290
        │               def create_supervisor_initial_state(**kwargs)
        │               return initial_state
        │
        ├─ Line 287: self._create_context(input_data)
        │   ↓
        │   core/base_agent.py:108
        │       def _create_context(input_data)
        │           ↓
        │           core/context.py:67
        │               def create_agent_context(user_id, session_id, **kwargs)
        │               return context
        │
        ├─ Line 310: async with AsyncSqliteSaver.from_conn_string(...)
        │   ↓
        │   Line 311: app = self.workflow.compile(checkpointer=checkpointer)
        │
        └─ Line 318: result = await asyncio.wait_for(
                app.ainvoke(initial_state, config=config, context=context),
                timeout=30
            )
            ↓
        ┌─────────────────────────────────────────────────────────┐
        │ LangGraph StateGraph Execution                          │
        └─────────────────────────────────────────────────────────┘
            ↓
        ┌─────────────────────────────────────────────────────────┐
        │ 2. START → analyze_intent                               │
        └─────────────────────────────────────────────────────────┘
            ↓
supervisor/intent_analyzer.py:70
    async def analyze_intent_node(state, runtime)
        ↓
        ├─ Line 83: ctx = await runtime.context()
        │
        ├─ Line 85: query = state["query"]
        │
        ├─ Line 89-90: API 키 조회
        │
        └─ Line 101: intent = await call_llm_for_intent(query, api_key)
            ↓
supervisor/intent_analyzer.py:18
    async def call_llm_for_intent(query, api_key)
        ↓
        ├─ Line 30: client = AsyncOpenAI(api_key=api_key)
        │
        ├─ Line 32: prompt = get_intent_analysis_prompt(query)
        │   ↓
        │   supervisor/prompts.py:170
        │       def get_intent_analysis_prompt(query)
        │       return INTENT_ANALYSIS_PROMPT.format(query=query)
        │
        ├─ Line 34-44: response = await client.chat.completions.create(...)
        │
        └─ Line 49: intent = json.loads(content)
            return intent
            ↓
supervisor/intent_analyzer.py:103-109
    return {
        "intent": intent,
        "status": "processing",
        "execution_step": "planning"
    }
        ↓
        ┌─────────────────────────────────────────────────────────┐
        │ 3. analyze_intent → build_plan                          │
        └─────────────────────────────────────────────────────────┘
            ↓
supervisor/plan_builder.py:172
    async def build_plan_node(state, runtime)
        ↓
        ├─ Line 185: ctx = await runtime.context()
        │
        ├─ Line 187: intent = state["intent"]
        │
        ├─ Line 191-192: API 키 조회
        │
        └─ Line 199: execution_plan = await call_llm_for_planning(intent, api_key)
            ↓
supervisor/plan_builder.py:128
    async def call_llm_for_planning(intent, api_key)
        ↓
        ├─ Line 142: client = AsyncOpenAI(api_key=api_key)
        │
        ├─ Line 144: prompt = get_plan_building_prompt(intent)
        │   ↓
        │   supervisor/prompts.py:175
        │       def get_plan_building_prompt(intent)
        │       return PLAN_BUILDING_PROMPT.format(intent=json.dumps(intent))
        │
        ├─ Line 146-154: response = await client.chat.completions.create(...)
        │
        ├─ Line 159: plan = json.loads(content)
        │
        └─ (에러 시 폴백)
            ↓
            supervisor/plan_builder.py:18
                def build_plan_rule_based(intent)
                return plan
            ↓
supervisor/plan_builder.py:201-207
    return {
        "execution_plan": execution_plan,
        "status": "processing",
        "execution_step": "executing_agents"
    }
        ↓
        ┌─────────────────────────────────────────────────────────┐
        │ 4. build_plan → execute_agents                          │
        └─────────────────────────────────────────────────────────┘
            ↓
supervisor/execution_coordinator.py:166
    async def execute_agents_node(state, runtime)
        ↓
        ├─ Line 179: ctx = await runtime.context()
        │
        ├─ Line 181-183: execution_plan, strategy, agents 추출
        │
        └─ Line 193: agent_results = await execute_sequential(agents, ctx)
            ↓
supervisor/execution_coordinator.py:89
    async def execute_sequential(agents, ctx)
        ↓
        ├─ Line 103: sorted_agents = sorted(agents, key=lambda x: x.get("order", 0))
        │
        └─ Line 105-112: for agent_config in sorted_agents:
                ↓
supervisor/execution_coordinator.py:54
    async def execute_agent(agent_config, ctx)
        ↓
        ├─ Line 64: agent_name = agent_config["name"]
        │
        ├─ Line 65: params = agent_config.get("params", {})
        │
        ├─ Line 72: agent = get_agent(agent_name)
        │   ↓
        │   supervisor/execution_coordinator.py:15
        │       def get_agent(agent_name)
        │           ↓
        │           Line 37-49: return MockAgent(agent_name)
        │               (TODO: 실제 에이전트 구현)
        │
        └─ Line 75: result = await agent.execute(params)
            return agent_name, result
            ↓
supervisor/execution_coordinator.py:202-207
    return {
        "agent_results": agent_results,
        "status": "processing",
        "execution_step": "evaluating"
    }
        ↓
        ┌─────────────────────────────────────────────────────────┐
        │ 5. execute_agents → evaluate_results                    │
        └─────────────────────────────────────────────────────────┘
            ↓
supervisor/result_evaluator.py:188
    async def evaluate_results_node(state, runtime)
        ↓
        ├─ Line 201: ctx = await runtime.context()
        │
        ├─ Line 203-204: agent_results, query 추출
        │
        ├─ Line 209-210: API 키 조회
        │
        ├─ Line 214: evaluation = await call_llm_for_evaluation(agent_results, api_key)
        │   ↓
        │   supervisor/result_evaluator.py:57
        │       async def call_llm_for_evaluation(agent_results, api_key)
        │           ↓
        │           ├─ Line 73: prompt = get_evaluation_prompt(agent_results)
        │           │   ↓
        │           │   supervisor/prompts.py:181
        │           │       def get_evaluation_prompt(agent_results)
        │           │
        │           ├─ Line 75-83: response = await client.chat.completions.create(...)
        │           │
        │           └─ Line 88: evaluation = json.loads(content)
        │               return evaluation
        │
        ├─ Line 222-230: if evaluation.get("needs_retry", False):
        │   (재시도 분기 - 현재 예제에서는 실행되지 않음)
        │
        └─ Line 234: final_output = await call_llm_for_formatting(query, agent_results, api_key)
            ↓
supervisor/result_evaluator.py:143
    async def call_llm_for_formatting(query, agent_results, api_key)
        ↓
        ├─ Line 160: prompt = get_response_formatting_prompt(query, agent_results)
        │   ↓
        │   supervisor/prompts.py:187
        │       def get_response_formatting_prompt(query, agent_results)
        │
        ├─ Line 162-170: response = await client.chat.completions.create(...)
        │
        └─ Line 175: final_output = json.loads(content)
            return final_output
            ↓
supervisor/result_evaluator.py:239-247
    return {
        "evaluation": evaluation,
        "final_output": final_output,
        "status": "completed",
        "execution_step": "finished",
        "end_time": None
    }
        ↓
        ┌─────────────────────────────────────────────────────────┐
        │ 6. evaluate_results → _should_retry (조건부 엣지)        │
        └─────────────────────────────────────────────────────────┘
            ↓
supervisor/supervisor.py:76
    def _should_retry(state)
        ↓
        ├─ Line 90-91: evaluation, needs_retry 추출
        │
        ├─ Line 94: retry_count = state.get("retry_count", 0)
        │
        └─ Line 96-108: if needs_retry and retry_count < self.max_retries:
                return "retry"  # execute_agents로 돌아감
            else:
                return "end"  # END 노드로
            ↓
        ┌─────────────────────────────────────────────────────────┐
        │ 7. END 노드 도달                                         │
        └─────────────────────────────────────────────────────────┘
            ↓
        (LangGraph 그래프 실행 완료)
            ↓
core/base_agent.py:327
    (ainvoke 완료, result 반환)
        ↓
core/base_agent.py:333-342
    return {
        "status": "success",
        "data": result,
        "agent": self.agent_name,
        "context": {...}
    }
        ↓
supervisor/supervisor.py:238-240
    if result["status"] == "success":
        return result["data"].get("final_output", {})
        ↓
┌─────────────────────────────────────────────────────────────────┐
│ 최종 사용자 응답 반환                                             │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2 호출 깊이 요약

```
1. process_query (supervisor.py:211)
    2. execute (base_agent.py:259)
        3. _validate_input (supervisor.py:170)
        3. _create_initial_state (supervisor.py:195)
            4. create_supervisor_initial_state (states.py:290)
        3. _create_context (base_agent.py:108)
            4. create_agent_context (context.py:67)
        3. ainvoke (LangGraph)
            4. analyze_intent_node (intent_analyzer.py:70)
                5. call_llm_for_intent (intent_analyzer.py:18)
                    6. get_intent_analysis_prompt (prompts.py:170)
                    6. AsyncOpenAI.chat.completions.create()
            4. build_plan_node (plan_builder.py:172)
                5. call_llm_for_planning (plan_builder.py:128)
                    6. get_plan_building_prompt (prompts.py:175)
                    6. AsyncOpenAI.chat.completions.create()
                (또는 build_plan_rule_based)
            4. execute_agents_node (execution_coordinator.py:166)
                5. execute_sequential (execution_coordinator.py:89)
                    6. execute_agent (execution_coordinator.py:54)
                        7. get_agent (execution_coordinator.py:15)
                            8. MockAgent.execute()
            4. evaluate_results_node (result_evaluator.py:188)
                5. call_llm_for_evaluation (result_evaluator.py:57)
                    6. get_evaluation_prompt (prompts.py:181)
                    6. AsyncOpenAI.chat.completions.create()
                5. call_llm_for_formatting (result_evaluator.py:143)
                    6. get_response_formatting_prompt (prompts.py:187)
                    6. AsyncOpenAI.chat.completions.create()
            4. _should_retry (supervisor.py:76)
```

---

## 10. State 변화 타임라인

### 10.1 시간 순 State 스냅샷

#### T0: 초기 상태 (create_supervisor_initial_state)

**시간**: 2025-09-27T10:30:00.123456

```python
{
    "status": "pending",
    "execution_step": "initializing",
    "errors": [],
    "start_time": "2025-09-27T10:30:00.123456",
    "query": "강남역 근처 30평대 아파트 매매 시세 알려줘",
    "intent": None,
    "execution_plan": None,
    "agent_results": {},
    "evaluation": None,
    "final_output": None,
    "end_time": None
}
```

#### T1: analyze_intent_node 완료 후

**시간**: 2025-09-27T10:30:02.456789
**변경 사항**:
- `intent` ← 새로 추가
- `status` ← "processing"
- `execution_step` ← "planning"

```python
{
    "status": "processing",  # ✅ CHANGED
    "execution_step": "planning",  # ✅ CHANGED
    "errors": [],
    "start_time": "2025-09-27T10:30:00.123456",
    "query": "강남역 근처 30평대 아파트 매매 시세 알려줘",
    "intent": {  # ✅ NEW
        "intent_type": "analysis",
        "region": "서울특별시 강남구",
        "property_type": "아파트",
        "deal_type": "매매",
        "price_range": None,
        "size_range": {"min": 30, "max": 40}
    },
    "execution_plan": None,
    "agent_results": {},
    "evaluation": None,
    "final_output": None,
    "end_time": None
}
```

#### T2: build_plan_node 완료 후

**시간**: 2025-09-27T10:30:04.789012
**변경 사항**:
- `execution_plan` ← 새로 추가
- `execution_step` ← "executing_agents"

```python
{
    "status": "processing",
    "execution_step": "executing_agents",  # ✅ CHANGED
    "errors": [],
    "start_time": "2025-09-27T10:30:00.123456",
    "query": "강남역 근처 30평대 아파트 매매 시세 알려줘",
    "intent": {...},
    "execution_plan": {  # ✅ NEW
        "strategy": "sequential",
        "agents": [
            {
                "name": "property_search",
                "order": 1,
                "params": {
                    "region": "서울특별시 강남구",
                    "property_type": "아파트",
                    "deal_type": "매매",
                    "size_range": {"min": 30, "max": 40}
                }
            },
            {
                "name": "market_analysis",
                "order": 2,
                "params": {
                    "region": "서울특별시 강남구",
                    "property_type": "아파트"
                }
            }
        ]
    },
    "agent_results": {},
    "evaluation": None,
    "final_output": None,
    "end_time": None
}
```

#### T3: execute_agents_node 완료 후

**시간**: 2025-09-27T10:30:06.123456
**변경 사항**:
- `agent_results` ← 병합 (merge_dicts)
- `execution_step` ← "evaluating"

```python
{
    "status": "processing",
    "execution_step": "evaluating",  # ✅ CHANGED
    "errors": [],
    "start_time": "2025-09-27T10:30:00.123456",
    "query": "강남역 근처 30평대 아파트 매매 시세 알려줘",
    "intent": {...},
    "execution_plan": {...},
    "agent_results": {  # ✅ NEW (MERGED)
        "property_search": {
            "status": "success",
            "agent": "property_search",
            "data": "Mock result from property_search",
            "params": {
                "region": "서울특별시 강남구",
                "property_type": "아파트",
                "deal_type": "매매",
                "size_range": {"min": 30, "max": 40}
            }
        },
        "market_analysis": {
            "status": "success",
            "agent": "market_analysis",
            "data": "Mock result from market_analysis",
            "params": {
                "region": "서울특별시 강남구",
                "property_type": "아파트"
            }
        }
    },
    "evaluation": None,
    "final_output": None,
    "end_time": None
}
```

#### T4: evaluate_results_node 완료 후 (최종)

**시간**: 2025-09-27T10:30:08.456789
**변경 사항**:
- `evaluation` ← 새로 추가
- `final_output` ← 새로 추가
- `status` ← "completed"
- `execution_step` ← "finished"

```python
{
    "status": "completed",  # ✅ CHANGED
    "execution_step": "finished",  # ✅ CHANGED
    "errors": [],
    "start_time": "2025-09-27T10:30:00.123456",
    "query": "강남역 근처 30평대 아파트 매매 시세 알려줘",
    "intent": {...},
    "execution_plan": {...},
    "agent_results": {...},
    "evaluation": {  # ✅ NEW
        "quality_score": 1.0,
        "completeness": True,
        "accuracy": True,
        "consistency": True,
        "needs_retry": False,
        "retry_agents": [],
        "feedback": "모든 에이전트가 성공적으로 실행되었고, 필요한 데이터가 모두 수집되었습니다."
    },
    "final_output": {  # ✅ NEW
        "answer": "강남구의 30평대 아파트 매매 시세를 분석한 결과, 평균 12억원 수준으로 형성되어 있습니다. 최근 3개월 간 약 5% 상승했으며, 강남역 인근 지역의 교통 접근성이 가격에 긍정적인 영향을 미치고 있습니다.",
        "listings": [
            {
                "name": "래미안 강남아파트",
                "region": "서울특별시 강남구 역삼동",
                "price": 1200000000,
                "size": 32,
                "deal_type": "매매"
            },
            {
                "name": "타워팰리스",
                "region": "서울특별시 강남구 대치동",
                "price": 1500000000,
                "size": 35,
                "deal_type": "매매"
            }
        ],
        "insights": [
            "강남구는 학군이 우수하여 수요가 지속적으로 높습니다",
            "지하철역 인근 매물의 가격이 평균 대비 15% 더 높습니다",
            "최근 신규 공급 부족으로 가격 상승세가 이어지고 있습니다",
            "30평대는 실수요자 선호도가 높아 유동성이 좋습니다"
        ],
        "metadata": {
            "total_listings": 2,
            "avg_price": 1350000000,
            "price_range": {"min": 1200000000, "max": 1500000000},
            "region": "서울특별시 강남구",
            "analysis_date": "2025-09-27"
        }
    },
    "end_time": None
}
```

### 10.2 State 필드별 변화 추이

| 필드 | T0 (초기) | T1 (intent) | T2 (plan) | T3 (agents) | T4 (결과) |
|-----|----------|------------|-----------|-------------|----------|
| `status` | pending | processing | processing | processing | **completed** |
| `execution_step` | initializing | planning | executing_agents | evaluating | **finished** |
| `errors` | [] | [] | [] | [] | [] |
| `query` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `intent` | None | ✅ **NEW** | ✅ | ✅ | ✅ |
| `execution_plan` | None | None | ✅ **NEW** | ✅ | ✅ |
| `agent_results` | {} | {} | {} | ✅ **MERGED** | ✅ |
| `evaluation` | None | None | None | None | ✅ **NEW** |
| `final_output` | None | None | None | None | ✅ **NEW** |

### 10.3 Reducer 동작 확인

**1. 덮어쓰기 (Overwrite) 필드**:
- `status`, `execution_step`, `intent`, `execution_plan`, `evaluation`, `final_output`
- 각 노드에서 반환한 값으로 완전히 대체

**2. 병합 (merge_dicts) 필드**:
- `agent_results`
- T3에서 `property_search` 결과가 먼저 병합, 이어서 `market_analysis` 결과 병합
- 기존 키는 유지, 새 키는 추가

**3. 누적 (add) 필드**:
- `errors`
- 현재 예제에서는 에러 없음 (빈 리스트 유지)
- 에러 발생 시 기존 리스트에 추가됨

---

## 11. 에러 처리 및 재시도 메커니즘

### 11.1 재시도 시나리오

#### 시나리오 1: 에이전트 실행 실패

**가정**: `property_search` 에이전트가 실패

**T3: execute_agents_node 완료 후**:
```python
{
    ...
    "agent_results": {
        "property_search": {
            "status": "error",  # ❌ FAILED
            "agent": "property_search",
            "error": "Database connection timeout"
        }
    },
    ...
}
```

**T4: evaluate_results_node 평가**:
```python
evaluation = {
    "quality_score": 0.0,
    "completeness": False,
    "needs_retry": True,  # ✅ 재시도 필요
    "retry_agents": ["property_search"],
    "feedback": "property_search 에이전트가 실패했습니다. 재시도가 필요합니다."
}
```

**T4: evaluate_results_node 반환**:
```python
return {
    "evaluation": evaluation,
    "status": "processing",  # completed가 아닌 processing 유지
    "execution_step": "executing_agents"  # 다시 execute_agents로
}
```

**T5: _should_retry 조건부 엣지**:
```python
evaluation = state.get("evaluation", {})
needs_retry = evaluation.get("needs_retry", False)  # True
retry_count = state.get("retry_count", 0)  # 0

if needs_retry and retry_count < self.max_retries:  # True and 0 < 2
    logger.info("Retrying agent execution (attempt 1/2)")
    return "retry"  # execute_agents 노드로 돌아감
```

**T6: execute_agents_node 재실행**:
- `execution_plan`의 에이전트들을 다시 실행
- 실패했던 `property_search` 재시도
- 성공 시 → evaluate_results로
- 실패 시 → retry_count 증가, 다시 평가

**최대 재시도 도달**:
```python
retry_count = 2  # 최대 재시도 횟수 도달

if needs_retry and retry_count < self.max_retries:  # True and 2 < 2 = False
    return "retry"
else:
    logger.warning("Max retries (2) reached, proceeding with current results")
    return "end"  # 재시도 포기, END로
```

### 11.2 에러 처리 포인트

#### 1. 입력 검증 실패

**위치**: `base_agent.py:276`

```python
if not await self._validate_input(input_data):
    return {
        "status": "error",
        "error": "Invalid input data",
        "agent": self.agent_name
    }
```

**결과**: 그래프 실행 없이 즉시 종료

#### 2. API 키 누락

**위치**: `intent_analyzer.py:93-98`, `plan_builder.py:194-196`, `result_evaluator.py:216`

**처리**:
- Intent Analyzer: 에러 반환 (실행 중단)
- Plan Builder: 규칙 기반 폴백
- Result Evaluator: 규칙 기반 폴백

#### 3. LLM API 호출 실패

**위치**: 모든 `call_llm_for_*` 함수

**처리**:
```python
except Exception as e:
    logger.warning(f"LLM call failed, using fallback: {e}")
    return fallback_function(...)
```

**폴백**:
- Intent: 기본 intent 반환
- Planning: 규칙 기반 계획
- Evaluation: 규칙 기반 평가
- Formatting: 단순 포맷팅

#### 4. JSON 파싱 실패

**위치**: 모든 `json.loads()` 호출

**처리**:
```python
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse JSON: {e}")
    return default_value_or_fallback(...)
```

#### 5. 에이전트 실행 실패

**위치**: `execution_coordinator.py:68-86`

**처리**:
```python
try:
    result = await agent.execute(params)
    return agent_name, result
except Exception as e:
    logger.error(f"Agent {agent_name} failed: {e}", exc_info=True)
    return agent_name, {
        "status": "error",
        "agent": agent_name,
        "error": str(e)
    }
```

**영향**:
- Sequential: 중단
- Parallel: 다른 에이전트 계속 실행

#### 6. 타임아웃

**위치**: `base_agent.py:318-355`

**처리**:
```python
try:
    result = await asyncio.wait_for(
        app.ainvoke(...),
        timeout=30
    )
except asyncio.TimeoutError:
    logger.error(f"Execution timed out after 30s")
    return {
        "status": "error",
        "error": "Execution timed out after 30 seconds",
        "agent": self.agent_name
    }
```

### 11.3 에러 로깅 및 추적

**체크포인트를 통한 추적**:
- 각 노드 실행 후 체크포인트 저장
- 에러 발생 시점의 state 보존
- 재시도 시 이전 체크포인트에서 복원 가능

**로그 레벨**:
- **INFO**: 정상 실행 흐름
- **WARNING**: 폴백 사용, 재시도
- **ERROR**: 에러 발생, 실행 실패

---

## 부록 A: State Schema 완전 정의

### SupervisorState (states.py:145-200)

```python
class SupervisorState(BaseState):
    # 상속: status, execution_step, errors, start_time, end_time

    # Input (overwrite)
    query: str

    # Intent Analysis (overwrite)
    intent: Optional[Dict[str, Any]]
    # 구조:
    # {
    #   "intent_type": "search" | "analysis" | "comparison" | "recommendation",
    #   "region": str,
    #   "property_type": str,
    #   "deal_type": str,
    #   "price_range": {"min": int, "max": int},
    #   "size_range": {"min": int, "max": int}
    # }

    # Planning (overwrite)
    execution_plan: Optional[Dict[str, Any]]
    # 구조:
    # {
    #   "strategy": "sequential" | "parallel" | "dag",
    #   "agents": [
    #     {
    #       "name": str,
    #       "order": int,
    #       "params": Dict[str, Any]
    #     }
    #   ]
    # }

    # Agent Execution (merge)
    agent_results: Annotated[Dict[str, Any], merge_dicts]
    # 구조:
    # {
    #   "agent_name": {
    #     "status": "success" | "error",
    #     "data": Any,
    #     "error": str (if failed)
    #   }
    # }

    # Evaluation (overwrite)
    evaluation: Optional[Dict[str, Any]]
    # 구조:
    # {
    #   "quality_score": float,
    #   "completeness": bool,
    #   "accuracy": bool,
    #   "consistency": bool,
    #   "needs_retry": bool,
    #   "retry_agents": List[str],
    #   "feedback": str
    # }

    # Output (overwrite)
    final_output: Optional[Dict[str, Any]]
    # 구조:
    # {
    #   "answer": str,
    #   "listings": List[Dict],
    #   "insights": List[str],
    #   "metadata": Dict[str, Any]
    # }
```

### BaseState (states.py:37-50)

```python
class BaseState(TypedDict):
    # Status tracking (overwrite)
    status: str  # "pending" | "processing" | "completed" | "failed"
    execution_step: str  # 현재 워크플로우 단계

    # Error tracking (accumulate)
    errors: Annotated[List[str], add]  # 에러 메시지 누적

    # Timing (overwrite)
    start_time: Optional[str]  # ISO 8601 형식
    end_time: Optional[str]    # ISO 8601 형식
```

---

## 부록 B: Context Schema 완전 정의

### AgentContext (context.py:14-38)

```python
class AgentContext(TypedDict):
    # ========== Required Fields ==========
    user_id: str                # 사용자 식별자
    session_id: str             # 세션 식별자

    # ========== Optional Runtime Info ==========
    request_id: Optional[str]   # 고유 요청 ID (자동 생성)
    timestamp: Optional[str]    # 요청 타임스탬프 (ISO 8601)
    original_query: Optional[str]  # 원본 사용자 입력

    # ========== Authentication ==========
    api_keys: Optional[Dict[str, str]]  # 서비스 API 키
    # 구조:
    # {
    #   "openai_api_key": str,
    #   "anthropic_api_key": str,
    #   ...
    # }

    # ========== User Settings ==========
    language: Optional[str]     # 사용자 언어 (기본: "ko")

    # ========== Execution Control ==========
    debug_mode: Optional[bool]  # 디버그 모드 (기본: False)
```

**특징**:
- **READ-ONLY**: 노드는 읽기만 가능, 수정 불가
- **런타임 메타데이터**: 실행 중 변경되지 않는 정보
- **Runtime을 통한 접근**: `ctx = await runtime.context()`

---

## 부록 C: 프롬프트 템플릿 완전 버전

### INTENT_ANALYSIS_PROMPT (prompts.py:9-39)

```python
INTENT_ANALYSIS_PROMPT = """
당신은 부동산 챗봇의 의도 분석 전문가입니다. 사용자의 질문을 분석하여 다음 정보를 JSON 형식으로 추출하세요.

**추출할 정보:**
1. intent_type: 질문의 유형
   - "search": 매물 검색 (예: "강남 아파트 찾아줘")
   - "analysis": 시세 분석 (예: "강남 아파트 시세 알려줘")
   - "comparison": 지역 비교 (예: "강남과 서초 아파트 비교해줘")
   - "recommendation": 추천 (예: "투자하기 좋은 아파트 추천해줘")

2. region: 지역명 (예: "서울특별시 강남구", "경기도 성남시")
3. property_type: 매물 유형 ("아파트", "오피스텔", "빌라", "단독주택" 중 하나, 없으면 null)
4. deal_type: 거래 유형 ("매매", "전세", "월세" 중 하나, 없으면 null)
5. price_range: 가격 범위 (예: {{"min": 100000, "max": 150000}}, 없으면 null)
6. size_range: 평형 범위 (예: {{"min": 30, "max": 40}}, 없으면 null)

**사용자 질문:**
{query}

**응답 형식 (JSON):**
{{
  "intent_type": "search",
  "region": "서울특별시 강남구",
  "property_type": "아파트",
  "deal_type": "매매",
  "price_range": {{"min": 100000, "max": 150000}},
  "size_range": {{"min": 30, "max": 40}}
}}

**중요:** JSON 형식으로만 응답하고, 추가 설명은 하지 마세요.
"""
```

### PLAN_BUILDING_PROMPT (prompts.py:42-89)

```python
PLAN_BUILDING_PROMPT = """
당신은 부동산 챗봇의 실행 계획 수립 전문가입니다. 사용자 의도를 기반으로 필요한 Agent와 실행 전략을 결정하세요.

**사용 가능한 Agent:**
1. property_search: 매물 검색 Agent
2. market_analysis: 시장 분석 Agent
3. region_comparison: 지역 비교 Agent
4. investment_advisor: 투자 자문 Agent

**실행 전략:**
- "sequential": 순차 실행 (Agent 간 의존성이 있을 때)
- "parallel": 병렬 실행 (독립적인 Agent들)
- "dag": DAG 방식 (복잡한 의존성)

**사용자 의도:**
{intent}

**응답 형식 (JSON):**
{{
  "strategy": "sequential",
  "agents": [
    {{
      "name": "property_search",
      "order": 1,
      "params": {{
        "region": "서울특별시 강남구",
        "property_type": "아파트",
        "deal_type": "매매"
      }}
    }},
    {{
      "name": "market_analysis",
      "order": 2,
      "params": {{
        "region": "서울특별시 강남구"
      }}
    }}
  ]
}}

**규칙:**
1. intent_type이 "search"면 property_search만 사용
2. intent_type이 "analysis"면 property_search + market_analysis
3. intent_type이 "comparison"면 property_search + region_comparison
4. intent_type이 "recommendation"면 모든 Agent 사용

**중요:** JSON 형식으로만 응답하고, 추가 설명은 하지 마세요.
"""
```

### EVALUATION_PROMPT (prompts.py:92-120)

```python
EVALUATION_PROMPT = """
당신은 부동산 챗봇의 결과 평가 전문가입니다. Agent 실행 결과를 평가하여 품질을 판단하세요.

**Agent 실행 결과:**
{agent_results}

**평가 기준:**
1. **완전성 (completeness):** 모든 필요한 데이터가 수집되었는가?
2. **정확성 (accuracy):** 데이터가 정확하고 신뢰할 수 있는가?
3. **일관성 (consistency):** Agent 결과들이 서로 모순되지 않는가?

**응답 형식 (JSON):**
{{
  "quality_score": 0.85,
  "completeness": true,
  "accuracy": true,
  "consistency": true,
  "needs_retry": false,
  "retry_agents": [],
  "feedback": "모든 데이터가 성공적으로 수집되었습니다."
}}

**재시도 조건:**
- Agent가 에러를 반환했을 때
- 데이터가 불완전할 때 (completeness: false)
- 데이터가 부정확할 때 (accuracy: false)

**중요:** JSON 형식으로만 응답하고, 추가 설명은 하지 마세요.
"""
```

### RESPONSE_FORMATTING_PROMPT (prompts.py:123-167)

```python
RESPONSE_FORMATTING_PROMPT = """
당신은 부동산 챗봇의 응답 생성 전문가입니다. Agent 결과를 사용자 친화적인 형식으로 변환하세요.

**사용자 질문:**
{query}

**Agent 결과:**
{agent_results}

**응답 형식:**
1. **간단한 답변 (answer):** 사용자 질문에 대한 직접적인 답변 (2-3문장)
2. **매물 목록 (listings):** 검색된 매물 리스트 (최대 10개)
3. **인사이트 (insights):** 분석 결과 및 특징 (bullet points)
4. **메타데이터 (metadata):** 통계 정보

**응답 예시:**
{{
  "answer": "강남구의 30평대 아파트 매매 시세는 평균 12억원입니다. 최근 3개월 간 5% 상승했으며, 교통 접근성이 좋은 지역의 가격이 더 높습니다.",
  "listings": [
    {{
      "name": "래미안 아파트",
      "region": "서울특별시 강남구 역삼동",
      "price": 120000,
      "size": 32,
      "deal_type": "매매"
    }}
  ],
  "insights": [
    "강남구는 학군이 우수하여 수요가 높습니다",
    "지하철역 인근 매물의 가격이 15% 더 높습니다",
    "최근 신규 공급 부족으로 가격 상승세를 보입니다"
  ],
  "metadata": {{
    "total_listings": 10,
    "avg_price": 120000,
    "price_range": {{"min": 100000, "max": 150000}},
    "region": "서울특별시 강남구"
  }}
}}

**중요:**
- 한국어로 작성하세요
- 사용자가 이해하기 쉽게 작성하세요
- JSON 형식으로만 응답하세요
"""
```

---

## 부록 D: 실행 시간 분석

### 각 단계별 예상 소요 시간

| Phase | 작업 | 예상 시간 | 주요 병목 |
|-------|------|----------|---------|
| Phase 1 | 초기화 및 입력 검증 | ~10ms | I/O (체크포인터 로드) |
| Phase 2 | START 노드 | ~5ms | LangGraph 내부 처리 |
| Phase 3 | Intent Analysis | ~1-3초 | LLM API 호출 (gpt-4o-mini) |
| Phase 4 | Plan Building | ~2-4초 | LLM API 호출 (gpt-4o) |
| Phase 5 | Agent Execution | ~1-5초 | 에이전트별 실행 시간 (Mock은 즉시) |
| Phase 6 | Result Evaluation | ~2-4초 | LLM API 호출 (gpt-4o-mini + gpt-4o) |
| Phase 7 | 조건부 라우팅 및 종료 | ~10ms | 조건 평가 |
| **총 예상 시간** | **6-16초** | **LLM API 호출이 주요 병목** |

**최적화 포인트**:
1. **LLM 호출 병렬화**: Intent + Plan을 동시에 (현재는 순차)
2. **응답 캐싱**: 동일 쿼리 반복 시 캐시에서 반환
3. **스트리밍 응답**: 각 단계 완료 시 부분 결과 반환
4. **에이전트 병렬 실행**: 독립적인 에이전트는 parallel 전략 사용

---

## 결론

이 보고서는 사용자 질의부터 최종 출력까지의 전체 실행 과정을 상세히 추적했습니다.

**주요 내용**:
1. ✅ 10개 Phase로 나눈 단계별 실행 흐름
2. ✅ 모든 파일, 함수, 클래스의 호출 체인 (라인 번호 포함)
3. ✅ State의 시간 순 변화 추적 (5개 스냅샷)
4. ✅ Reducer 동작 확인 (덮어쓰기/병합/누적)
5. ✅ 에러 처리 및 재시도 메커니즘
6. ✅ 실제 예제 쿼리 기반 시뮬레이션

**활용 방안**:
- 디버깅 시 참조 문서
- 새 기능 추가 시 영향 범위 파악
- 성능 병목 지점 식별
- 에러 추적 및 해결

**다음 단계**:
- 실제 에이전트 구현 (Mock 대체)
- 데이터베이스 연동
- 성능 모니터링 추가
- 단위 테스트 작성