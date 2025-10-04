# 홈즈냥즈 AI 시스템 완전 흐름 분석 보고서
## 사용자 질문 → LLM Tool 결정 → 팀 협업 → 최종 출력

**작성일**: 2025-10-03
**버전**: 1.0 (Complete Flow Analysis)
**대상**: 개발자 및 아키텍처 이해를 위한 상세 가이드

---

## 📋 목차

1. [개요](#1-개요)
2. [전체 시스템 흐름도](#2-전체-시스템-흐름도)
3. [Phase별 상세 분석](#3-phase별-상세-분석)
4. [LLM 역할 및 호출 시점](#4-llm-역할-및-호출-시점)
5. [Tool 결정 메커니즘](#5-tool-결정-메커니즘)
6. [팀 간 협업 프로토콜](#6-팀-간-협업-프로토콜)
7. [데이터 흐름 추적](#7-데이터-흐름-추적)
8. [실제 실행 예제](#8-실제-실행-예제)
9. [성능 최적화 포인트](#9-성능-최적화-포인트)
10. [결론](#10-결론)

---

## 1. 개요

### 1.1 시스템 핵심 컨셉

홈즈냥즈 AI는 **LLM 기반 의도 분석 → 동적 Tool 선택 → 팀 기반 협업 → 통합 응답 생성**의 4단계 파이프라인으로 작동합니다.

```
사용자 질문
    ↓
[LLM] Intent 분석 (PlanningAgent)
    ↓
[시스템] Tool/Agent 선택 (AgentRegistry + Adapter)
    ↓
[팀] 순차/병렬 실행 (TeamBasedSupervisor)
    ↓
[LLM] 최종 응답 생성 (Response Generator)
    ↓
사용자에게 답변
```

### 1.2 핵심 구성 요소

| 구성 요소 | 역할 | LLM 사용 여부 |
|----------|------|--------------|
| **PlanningAgent** | 의도 분석 및 실행 계획 | ✅ LLM 사용 (GPT-4o-mini) |
| **AgentRegistry** | Agent 등록/관리/검색 | ❌ 규칙 기반 |
| **AgentAdapter** | Agent 동적 실행 | ❌ 규칙 기반 |
| **TeamBasedSupervisor** | 팀 조정 및 데이터 전달 | ❌ 오케스트레이션 |
| **SearchExecutor** | 법률/시장/대출 검색 | ❌ Tool 호출만 |
| **AnalysisExecutor** | 데이터 분석 | ⚠️ 선택적 LLM |
| **DocumentExecutor** | 문서 생성/검토 | ✅ LLM 사용 |
| **Response Generator** | 최종 답변 생성 | ✅ LLM 사용 (GPT-4o-mini) |

---

## 2. 전체 시스템 흐름도

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         사용자                                │
│                           ↓                                   │
│                   "강남구 아파트 시세 알려주세요"               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   TeamBasedSupervisor                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  [1] initialize → [2] planning → [3] execute_teams     │ │
│  │       ↓              ↓                ↓                 │ │
│  │    State 준비   Planning Agent    팀 실행              │ │
│  │                  (LLM 호출)       (순차/병렬)          │ │
│  │       ↓              ↓                ↓                 │ │
│  │  [4] aggregate ← [5] generate_response                 │ │
│  │       ↓                   ↓                             │ │
│  │   결과 통합          최종 응답 (LLM 호출)               │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    PlanningAgent                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  [LLM 호출 #1] Intent 분석                             │ │
│  │  ─────────────────────────────────────────────         │ │
│  │  Input:  사용자 질문                                   │ │
│  │  Model:  GPT-4o-mini                                   │ │
│  │  Output: {                                             │ │
│  │    "intent": "MARKET_INQUIRY",                        │ │
│  │    "confidence": 0.90,                                │ │
│  │    "keywords": ["강남구", "아파트", "시세"],           │ │
│  │    "entities": {                                      │ │
│  │      "location": "강남구",                            │ │
│  │      "property_type": "아파트"                        │ │
│  │    },                                                 │ │
│  │    "reasoning": "..."                                 │ │
│  │  }                                                    │ │
│  │                                                        │ │
│  │  [규칙 기반] 실행 계획 수립                            │ │
│  │  ─────────────────────────────────────────────         │ │
│  │  Intent → Agent 매핑 (AgentAdapter)                   │ │
│  │  MARKET_INQUIRY → ["search_team"]                     │ │
│  │                                                        │ │
│  │  실행 전략 결정:                                        │ │
│  │  - 의존성 있음 → SEQUENTIAL                           │ │
│  │  - 의존성 없음 → PARALLEL                             │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Team Execution Layer                         │
│                                                               │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │ SearchExecutor   │   │ AnalysisExecutor │   │ DocumentExecutor │   │
│  │              │   │              │   │              │   │
│  │ [Tool 호출]  │→  │ [데이터 분석] │→  │ [LLM 호출]  │   │
│  │ Legal DB     │   │ 패턴 인식    │   │ 문서 생성    │   │
│  │ Market DB    │   │ 트렌드 분석  │   │ 문서 검토    │   │
│  │ Loan DB      │   │              │   │              │   │
│  └──────────────┘   └──────────────┘   └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Response Generation                          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  [LLM 호출 #2] 최종 답변 생성                          │ │
│  │  ─────────────────────────────────────────────         │ │
│  │  Input:  {                                             │ │
│  │    "query": "강남구 아파트 시세 알려주세요",           │ │
│  │    "search_results": [...],                           │ │
│  │    "analysis_report": {...}                           │ │
│  │  }                                                    │ │
│  │  Model:  GPT-4o-mini                                   │ │
│  │  Output: "강남구 아파트 시세는..."                     │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↓
                     사용자에게 답변 전달
```

### 2.2 LLM 호출 시점

시스템 전체에서 **2~3회의 LLM 호출**이 발생합니다:

1. **PlanningAgent** (Intent 분석) - 필수
2. **Response Generator** (답변 생성) - 필수
3. **DocumentExecutor** (문서 생성) - 선택적 (Intent에 따라)

---

## 3. Phase별 상세 분석

### Phase 1: 초기화 (initialize_node)

**역할**: 시스템 상태 준비 및 초기화

```python
async def initialize_node(self, state: MainSupervisorState):
    """
    시스템 초기화
    - LLM 사용 없음
    - 단순 상태 설정
    """
    state["start_time"] = datetime.now()
    state["status"] = "initialized"
    state["current_phase"] = "initialization"
    state["active_teams"] = []
    state["completed_teams"] = []
    state["failed_teams"] = []
    state["team_results"] = {}
    state["shared_context"] = {}
    state["error_log"] = []

    return state
```

**출력**:
```json
{
  "query": "강남구 아파트 시세 알려주세요",
  "session_id": "session_20251003_001",
  "status": "initialized",
  "start_time": "2025-10-03T10:30:00",
  "active_teams": [],
  "team_results": {},
  "shared_context": {}
}
```

---

### Phase 2: Intent 분석 및 실행 계획 (planning_node)

**역할**: LLM을 사용하여 사용자 의도 파악 및 실행 계획 수립

#### Step 2-1: LLM Intent 분석

**LLM 호출 #1** - Intent Analysis

```python
async def _analyze_with_llm(self, query: str, context: Optional[Dict]) -> IntentResult:
    """
    LLM을 사용한 의도 분석
    """
    system_prompt = """당신은 부동산 AI 시스템의 의도 분석 전문가입니다.

## 분류 카테고리:
1. LEGAL_CONSULT (법률상담)
2. MARKET_INQUIRY (시세조회)
3. LOAN_CONSULT (대출상담)
4. CONTRACT_CREATION (계약서작성)
5. CONTRACT_REVIEW (계약서검토)
6. COMPREHENSIVE (종합분석)
7. RISK_ANALYSIS (리스크분석)
8. UNCLEAR (불분명)
9. IRRELEVANT (무관)

## 응답 형식 (JSON):
{
    "intent": "카테고리명",
    "confidence": 0.0~1.0,
    "keywords": ["키워드", "목록"],
    "entities": {
        "location": "지역명",
        "price": "가격",
        "contract_type": "계약유형"
    },
    "reasoning": "분류 이유"
}
"""

    response = self.llm_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"분석할 질문: {query}"}
        ],
        temperature=0.1,
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)
    return IntentResult(...)
```

**입력**:
```
질문: "강남구 아파트 시세 알려주세요"
```

**LLM 응답**:
```json
{
  "intent": "MARKET_INQUIRY",
  "confidence": 0.90,
  "keywords": ["강남구", "아파트", "시세"],
  "entities": {
    "location": "강남구",
    "property_type": "아파트",
    "contract_type": null
  },
  "reasoning": "사용자가 '강남구 아파트 시세'에 대한 정보를 요청하고 있으며, 가격과 시세에 대한 명확한 질문이 포함되어 있어 MARKET_INQUIRY로 분류했습니다."
}
```

#### Step 2-2: Agent 선택 (규칙 기반)

**AgentAdapter를 통한 Agent 매핑**

```python
def get_agents_for_intent(intent_type: str) -> List[str]:
    """
    의도 타입에 따라 실행할 Agent 목록 반환
    - LLM 사용 없음
    - 미리 정의된 매핑 규칙 사용
    """
    intent_agent_mapping = {
        "LEGAL_CONSULT": ["search_team"],
        "MARKET_INQUIRY": ["search_team"],  # ← 선택됨
        "LOAN_CONSULT": ["search_team"],
        "CONTRACT_CREATION": ["document_team"],
        "CONTRACT_REVIEW": ["document_team", "review_team"],
        "COMPREHENSIVE": ["search_team", "analysis_team"],
        "RISK_ANALYSIS": ["search_team", "analysis_team", "document_team"]
    }

    agents = intent_agent_mapping.get(intent_type, ["search_team"])

    # AgentRegistry에서 활성화된 Agent만 필터링
    enabled_agents = [
        agent for agent in agents
        if AgentRegistry.get_agent(agent) and
           AgentRegistry.get_agent(agent).enabled
    ]

    return enabled_agents
```

**선택된 Agent**:
```python
["search_team"]  # MARKET_INQUIRY → SearchExecutor만 실행
```

#### Step 2-3: 실행 전략 결정

```python
def _determine_strategy(self, steps: List[ExecutionStep]) -> ExecutionStrategy:
    """
    실행 전략 결정
    - LLM 사용 없음
    - 의존성 기반 규칙
    """
    # 의존성 확인
    has_dependencies = any(step.dependencies for step in steps)

    if has_dependencies:
        return ExecutionStrategy.SEQUENTIAL  # 순차 실행
    elif len(steps) > 1:
        return ExecutionStrategy.PARALLEL    # 병렬 실행
    else:
        return ExecutionStrategy.SEQUENTIAL  # 단일 실행
```

**결과**:
- **전략**: SEQUENTIAL (단일 팀이므로)
- **active_teams**: ["search"]

**Planning 결과**:
```python
{
    "planning_state": {
        "analyzed_intent": {
            "intent_type": "MARKET_INQUIRY",
            "confidence": 0.90,
            "keywords": ["강남구", "아파트", "시세"],
            "entities": {"location": "강남구", "property_type": "아파트"}
        },
        "execution_steps": [
            {
                "agent_name": "search_agent",
                "team": "search",
                "priority": 10,
                "dependencies": []
            }
        ],
        "execution_strategy": "sequential"
    },
    "active_teams": ["search"]
}
```

---

### Phase 3: 팀 실행 (execute_teams_node)

**역할**: 선택된 팀들을 순차/병렬로 실행하고 결과 수집

#### Step 3-1: SharedState 생성

```python
async def execute_teams_node(self, state: MainSupervisorState):
    """
    팀 실행 노드
    - LLM 사용 없음
    - 팀 간 조정만 수행
    """
    # 공유 상태 생성
    shared_state = StateManager.create_shared_state(
        query=state["query"],
        session_id=state["session_id"]
    )
    # {
    #   "user_query": "강남구 아파트 시세 알려주세요",
    #   "session_id": "session_20251003_001",
    #   "timestamp": "2025-10-03T10:30:05",
    #   "language": "ko",
    #   "status": "processing"
    # }

    # 전략에 따라 팀 실행
    if execution_strategy == "parallel":
        results = await self._execute_teams_parallel(...)
    else:
        results = await self._execute_teams_sequential(...)

    return state
```

#### Step 3-2: SearchExecutor 실행

**SearchExecutor 서브그래프 워크플로우**

```
prepare → route → search → aggregate → finalize
```

##### 3-2-1: prepare_search_node

```python
async def prepare_search_node(self, state: SearchExecutorState):
    """
    검색 준비
    - LLM 사용 없음
    - 키워드 추출 및 검색 범위 설정
    """
    user_query = state["shared_context"]["user_query"]
    # "강남구 아파트 시세 알려주세요"

    # 키워드 추출 (패턴 매칭)
    keywords = self._extract_keywords(user_query)
    # {
    #   "legal": [],
    #   "real_estate": ["강남구", "아파트", "시세"],
    #   "loan": [],
    #   "general": ["알려주세요"]
    # }

    state["keywords"] = SearchKeywords(**keywords)

    # 검색 범위 결정 (규칙 기반)
    state["search_scope"] = self._determine_search_scope(user_query, keywords)
    # ["real_estate"]  ← 부동산 DB만 검색

    state["status"] = "prepared"
    return state
```

##### 3-2-2: route_search_node

```python
def _route_decision(self, state: SearchExecutorState) -> str:
    """
    검색 실행 여부 결정
    - LLM 사용 없음
    """
    if not state.get("search_scope"):
        return "skip"  # 검색 범위 없으면 건너뛰기

    return "search"  # 검색 실행
```

##### 3-2-3: execute_search_node

**Tool 호출 (LLM 사용 없음)**

```python
async def execute_search_node(self, state: SearchExecutorState):
    """
    실제 검색 수행
    - LLM 사용 없음
    - DB Tool 직접 호출
    """
    search_scope = state.get("search_scope", [])  # ["real_estate"]

    # 부동산 DB 검색 (Tool 호출)
    if "real_estate" in search_scope:
        real_estate_results = await self.market_data_tool.search(
            location=state["keywords"]["real_estate"][0],  # "강남구"
            property_type="아파트",
            limit=10
        )
        state["real_estate_results"] = real_estate_results
        # [
        #   {"address": "강남구 역삼동", "price": 1200000000, "area": 85, ...},
        #   {"address": "강남구 삼성동", "price": 1500000000, "area": 102, ...},
        #   ...
        # ]

    # 법률 DB 검색 (검색 범위에 없으면 건너뛰기)
    if "legal" in search_scope:
        legal_results = await self.legal_search_tool.search(...)
        state["legal_results"] = legal_results

    # 대출 DB 검색 (검색 범위에 없으면 건너뛰기)
    if "loan" in search_scope:
        loan_results = await self.loan_data_tool.search(...)
        state["loan_results"] = loan_results

    state["current_search"] = "completed"
    return state
```

##### 3-2-4: aggregate_results_node

```python
async def aggregate_results_node(self, state: SearchExecutorState):
    """
    결과 통합
    - LLM 사용 없음
    """
    aggregated = {
        "legal": state.get("legal_results", []),
        "real_estate": state.get("real_estate_results", []),
        "loan": state.get("loan_results", []),
        "total_count": (
            len(state.get("legal_results", [])) +
            len(state.get("real_estate_results", [])) +
            len(state.get("loan_results", []))
        ),
        "search_scope": state.get("search_scope", []),
        "keywords": state.get("keywords")
    }

    state["aggregated_results"] = aggregated
    state["total_results"] = aggregated["total_count"]  # 10

    return state
```

##### 3-2-5: finalize_node

```python
async def finalize_node(self, state: SearchExecutorState):
    """
    최종 정리
    - LLM 사용 없음
    """
    state["status"] = "completed"
    state["end_time"] = datetime.now()
    state["search_time"] = (
        state["end_time"] - state["start_time"]
    ).total_seconds()  # 1.2초

    return state
```

**SearchExecutor 최종 결과**:
```python
{
    "team_name": "search",
    "status": "completed",
    "search_scope": ["real_estate"],
    "legal_results": [],
    "real_estate_results": [
        {"address": "강남구 역삼동", "price": 1200000000, "area": 85, "type": "아파트"},
        {"address": "강남구 삼성동", "price": 1500000000, "area": 102, "type": "아파트"},
        {"address": "강남구 대치동", "price": 1800000000, "area": 120, "type": "아파트"},
        # ... 총 10개
    ],
    "loan_results": [],
    "aggregated_results": {
        "real_estate": [...],
        "total_count": 10
    },
    "search_time": 1.2
}
```

#### Step 3-3: 결과 병합 (StateManager)

```python
# TeamBasedSupervisor.execute_teams_node()에서 호출
main_state = StateManager.merge_team_results(
    main_state,
    "search",
    search_result
)
```

**StateManager.merge_team_results()**

```python
@staticmethod
def merge_team_results(
    main_state: MainSupervisorState,
    team_name: str,
    team_result: Dict[str, Any]
) -> MainSupervisorState:
    """
    팀 결과를 main_state에 병합
    - LLM 사용 없음
    """
    # 1. 팀 결과 저장
    main_state["team_results"][team_name] = team_result

    # 2. 완료 팀 목록 업데이트
    if team_result.get("status") == "completed":
        main_state["completed_teams"].append(team_name)

    # 3. 다음 팀을 위한 데이터 추출
    if team_name == "search":
        main_state["shared_context"]["search_results"] = \
            team_result.get("aggregated_results")

    return main_state
```

**병합 후 main_state**:
```python
{
    "query": "강남구 아파트 시세 알려주세요",
    "completed_teams": ["search"],
    "team_results": {
        "search": {
            "status": "completed",
            "aggregated_results": {...},
            "search_time": 1.2
        }
    },
    "shared_context": {
        "search_results": {
            "real_estate": [...],
            "total_count": 10
        }
    }
}
```

---

### Phase 4: 결과 통합 (aggregate_results_node)

**역할**: 모든 팀 결과를 하나로 통합

```python
async def aggregate_results_node(self, state: MainSupervisorState):
    """
    결과 통합
    - LLM 사용 없음
    - 단순 데이터 병합
    """
    aggregated = {}

    for team_name, team_result in state["team_results"].items():
        if team_result.get("status") == "completed":
            aggregated[team_name] = {
                "summary": self._create_team_summary(team_result),
                "data": team_result
            }

    state["aggregated_results"] = aggregated

    return state
```

**통합 결과**:
```python
{
    "aggregated_results": {
        "search": {
            "summary": "부동산 DB에서 10건의 강남구 아파트 검색 완료",
            "data": {
                "real_estate": [...],
                "total_count": 10
            }
        }
    }
}
```

---

### Phase 5: 최종 응답 생성 (generate_response_node)

**역할**: LLM을 사용하여 사용자 친화적인 최종 답변 생성

**LLM 호출 #2** - Response Generation

```python
async def generate_response_node(self, state: MainSupervisorState):
    """
    최종 응답 생성
    - LLM 사용 (GPT-4o-mini)
    """
    query = state.get("query")
    aggregated_results = state.get("aggregated_results", {})

    # 검색 결과 추출
    search_data = aggregated_results.get("search", {}).get("data", {})
    real_estate_results = search_data.get("real_estate", [])

    # LLM 프롬프트 구성
    prompt = f"""사용자 질문: {query}

검색 결과:
{json.dumps(real_estate_results, ensure_ascii=False, indent=2)}

위 검색 결과를 바탕으로 사용자의 질문에 자연스럽고 정확하게 답변해주세요.

답변 가이드:
1. 검색된 매물 개수 언급
2. 평균 가격 계산 및 제시
3. 주요 지역 및 가격 범위 설명
4. 추가 정보가 필요하면 제안
"""

    response = await self.llm_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "당신은 부동산 정보를 제공하는 AI 어시스턴트입니다."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    answer = response.choices[0].message.content

    state["final_response"] = {
        "answer": answer,
        "data_sources": ["search_team"],
        "confidence": 0.90
    }

    state["status"] = "completed"
    state["current_phase"] = "response_generation"

    return state
```

**LLM 입력**:
```
사용자 질문: 강남구 아파트 시세 알려주세요

검색 결과:
[
  {"address": "강남구 역삼동", "price": 1200000000, "area": 85, "type": "아파트"},
  {"address": "강남구 삼성동", "price": 1500000000, "area": 102, "type": "아파트"},
  {"address": "강남구 대치동", "price": 1800000000, "area": 120, "type": "아파트"},
  ...
]
```

**LLM 출력 (최종 답변)**:
```
강남구 아파트 시세를 알려드리겠습니다.

현재 강남구에서 거래되고 있는 아파트 10건을 검색한 결과:

**평균 시세: 약 15억원**

**지역별 시세:**
- 역삼동: 12억~13억원 (소형 평형)
- 삼성동: 14억~16억원 (중형 평형)
- 대치동: 17억~19억원 (대형 평형)

**주요 특징:**
- 평균 전용면적: 85~120㎡
- 가격 범위: 12억~18억원
- 학군 지역(대치동)이 가장 높은 시세 형성

더 자세한 정보나 특정 평형, 단지에 대해 궁금하신 점이 있으시면 말씀해주세요.
```

**최종 상태**:
```python
{
    "query": "강남구 아파트 시세 알려주세요",
    "status": "completed",
    "current_phase": "response_generation",
    "completed_teams": ["search"],
    "team_results": {...},
    "aggregated_results": {...},
    "final_response": {
        "answer": "강남구 아파트 시세를 알려드리겠습니다...",
        "data_sources": ["search_team"],
        "confidence": 0.90
    },
    "start_time": "2025-10-03T10:30:00",
    "end_time": "2025-10-03T10:30:15",
    "total_execution_time": 15.0
}
```

---

## 4. LLM 역할 및 호출 시점

### 4.1 LLM 호출 요약

| 호출 시점 | 모델 | 역할 | 필수 여부 |
|----------|------|------|----------|
| **#1 Planning** | GPT-4o-mini | Intent 분석 | ✅ 필수 |
| **#2 Response Generation** | GPT-4o-mini | 최종 답변 생성 | ✅ 필수 |
| **#3 Document Generation** | GPT-4 | 문서 작성 | ⚠️ Intent에 따라 |
| **#4 Document Review** | GPT-4 | 문서 검토 | ⚠️ Intent에 따라 |

### 4.2 각 LLM 호출 상세

#### LLM 호출 #1: Intent 분석 (PlanningAgent)

**위치**: `PlanningAgent._analyze_with_llm()`

**입력**:
- 시스템 프롬프트: Intent 분류 가이드
- 사용자 프롬프트: 사용자 질문

**파라미터**:
```python
{
    "model": "gpt-4o-mini",
    "temperature": 0.1,  # 일관된 분류 위해 낮은 온도
    "response_format": {"type": "json_object"}  # JSON 강제
}
```

**출력**:
```json
{
  "intent": "MARKET_INQUIRY",
  "confidence": 0.90,
  "keywords": [...],
  "entities": {...},
  "reasoning": "..."
}
```

**처리 시간**: 평균 3-5초

---

#### LLM 호출 #2: 최종 답변 생성

**위치**: `TeamBasedSupervisor.generate_response_node()`

**입력**:
- 시스템 프롬프트: AI 어시스턴트 역할 정의
- 사용자 프롬프트: 질문 + 검색 결과

**파라미터**:
```python
{
    "model": "gpt-4o-mini",
    "temperature": 0.7,  # 자연스러운 답변 위해 적절한 온도
}
```

**출력**: 자연어 답변 (string)

**처리 시간**: 평균 6-10초

---

#### LLM 호출 #3: 문서 생성 (선택적)

**위치**: `DocumentExecutor` → `DocumentAgent`

**조건**: Intent가 `CONTRACT_CREATION` 또는 `COMPREHENSIVE`일 때

**입력**:
- 템플릿
- 검색 결과
- 분석 데이터

**파라미터**:
```python
{
    "model": "gpt-4",
    "temperature": 0.3,  # 정확한 문서 작성
}
```

**출력**: 구조화된 문서 (markdown/text)

**처리 시간**: 평균 15-20초

---

## 5. Tool 결정 메커니즘

### 5.1 Tool 선택 프로세스

```
사용자 질문
    ↓
[LLM] Intent 분석 → Intent Type 결정
    ↓
[규칙] Intent → Agent 매핑 (AgentAdapter)
    ↓
[규칙] Agent → Tool 매핑 (Agent 내부)
    ↓
[실행] Tool 호출
```

### 5.2 Intent → Agent 매핑 (AgentAdapter)

```python
intent_agent_mapping = {
    "LEGAL_CONSULT": ["search_team"],
    "MARKET_INQUIRY": ["search_team"],
    "LOAN_CONSULT": ["search_team"],
    "CONTRACT_CREATION": ["document_team"],
    "CONTRACT_REVIEW": ["document_team", "review_agent"],
    "COMPREHENSIVE": ["search_team", "analysis_team"],
    "RISK_ANALYSIS": ["search_team", "analysis_team", "review_agent"]
}
```

### 5.3 Agent → Tool 매핑 (SearchExecutor 예시)

```python
# SearchExecutor 내부
search_scope_tool_mapping = {
    "legal": "legal_search_tool",      # Legal DB
    "real_estate": "market_data_tool",  # Market DB
    "loan": "loan_data_tool"            # Loan DB
}

# 검색 범위에 따라 Tool 선택
if "real_estate" in search_scope:
    results = market_data_tool.search(...)
if "legal" in search_scope:
    results = legal_search_tool.search(...)
if "loan" in search_scope:
    results = loan_data_tool.search(...)
```

### 5.4 Tool 선택 예시

| 질문 | Intent | Agent | Tool |
|------|--------|-------|------|
| "전세금 인상 가능한가요?" | LEGAL_CONSULT | search_team | legal_search_tool |
| "강남구 아파트 시세는?" | MARKET_INQUIRY | search_team | market_data_tool |
| "대출 금리 알려주세요" | LOAN_CONSULT | search_team | loan_data_tool |
| "계약서 작성해주세요" | CONTRACT_CREATION | document_team | document_generator (LLM) |
| "강남 아파트 분석" | COMPREHENSIVE | search_team + analysis_team | market_data_tool + analysis_tools |

---

## 6. 팀 간 협업 프로토콜

### 6.1 데이터 전달 메커니즘

**핵심**: `shared_context`를 통한 명시적 데이터 전달

```
SearchExecutor
    ↓
    결과: aggregated_results
    ↓
StateManager.merge_team_results()
    ↓
    main_state["shared_context"]["search_results"] = aggregated_results
    ↓
AnalysisExecutor
    ↓
    입력: shared_context["search_results"]
    ↓
    결과: analysis_report
    ↓
StateManager.merge_team_results()
    ↓
    main_state["shared_context"]["analysis_report"] = analysis_report
    ↓
DocumentExecutor
    ↓
    입력: shared_context["search_results"] + shared_context["analysis_report"]
```

### 6.2 순차 실행 (Sequential)

```python
async def _execute_teams_sequential(
    self,
    teams: List[str],
    shared_state: SharedState,
    main_state: MainSupervisorState
) -> Dict[str, Any]:
    """순차 실행 with 팀 간 데이터 전달"""

    results = {}

    for team_name in teams:
        # 1. 이전 팀 결과를 현재 팀 입력으로 구성
        team_input = self._prepare_team_input(
            team_name,
            shared_state,
            main_state
        )

        # 2. 팀 실행
        result = await self.teams[team_name].app.ainvoke(team_input)
        results[team_name] = result

        # 3. 결과를 main_state에 병합
        main_state = StateManager.merge_team_results(
            main_state,
            team_name,
            result
        )

    return results
```

### 6.3 병렬 실행 (Parallel)

```python
async def _execute_teams_parallel(
    self,
    teams: List[str],
    shared_state: SharedState,
    main_state: MainSupervisorState
) -> Dict[str, Any]:
    """병렬 실행 - 독립적인 팀들만"""

    # 동시 실행 (asyncio.gather)
    tasks = []
    for team_name in teams:
        team_input = self._prepare_team_input(team_name, shared_state, main_state)
        task = self.teams[team_name].app.ainvoke(team_input)
        tasks.append((team_name, task))

    # 모든 팀 실행 완료 대기
    results = {}
    completed = await asyncio.gather(*[task for _, task in tasks])

    for (team_name, _), result in zip(tasks, completed):
        results[team_name] = result
        main_state = StateManager.merge_team_results(main_state, team_name, result)

    return results
```

---

## 7. 데이터 흐름 추적

### 7.1 복합 쿼리 예시: "강남 아파트 시세 분석 후 투자 추천서 작성"

#### Intent 분석
```json
{
  "intent": "COMPREHENSIVE",
  "confidence": 0.92,
  "keywords": ["강남", "아파트", "시세", "분석", "투자", "추천서"]
}
```

#### Agent 선택
```python
["search_team", "analysis_team", "document_team"]
```

#### 데이터 흐름

**Step 1: SearchExecutor**

입력:
```python
{
    "user_query": "강남 아파트 시세 분석 후 투자 추천서 작성",
    "session_id": "session_001"
}
```

출력:
```python
{
    "aggregated_results": {
        "real_estate": [
            {"address": "강남구 역삼동", "price": 1200000000, ...},
            {"address": "강남구 삼성동", "price": 1500000000", ...},
            ...
        ],
        "total_count": 10
    }
}
```

병합 후:
```python
main_state["shared_context"]["search_results"] = {
    "real_estate": [...],
    "total_count": 10
}
```

---

**Step 2: AnalysisExecutor** (SearchExecutor 결과 사용)

입력:
```python
{
    "input_data": {
        "data_source": "search_team",
        "data": main_state["shared_context"]["search_results"]  # ← 전달
    }
}
```

처리:
```python
# 데이터 분석
- 평균 가격 계산: 15억
- 가격 범위: 12억~18억
- 트렌드: 상승
- 투자 점수: 0.75
```

출력:
```python
{
    "report": {
        "title": "강남 아파트 종합 분석 보고서",
        "metrics": {
            "avg_price": 1500000000,
            "price_trend": "상승",
            "investment_score": 0.75
        },
        "insights": [
            "강남 아파트 가격 상승 추세",
            "투자 적기로 판단"
        ]
    }
}
```

병합 후:
```python
main_state["shared_context"]["analysis_report"] = {
    "title": "...",
    "metrics": {...},
    "insights": [...]
}
```

---

**Step 3: DocumentExecutor** (SearchExecutor + AnalysisExecutor 결과 사용)

입력:
```python
{
    "document_type": "investment_recommendation",
    "document_data": {
        "search_results": main_state["shared_context"]["search_results"],    # ← 전달
        "analysis_report": main_state["shared_context"]["analysis_report"]  # ← 전달
    }
}
```

처리 (LLM 호출):
```python
# LLM 프롬프트
"""
다음 정보를 바탕으로 투자 추천서를 작성해주세요:

검색 결과:
- 강남구 아파트 10건
- 평균 가격: 15억원
- 가격 범위: 12억~18억원

분석 결과:
- 가격 추세: 상승
- 투자 점수: 0.75
- 주요 인사이트: 투자 적기

추천서 구성:
1. 투자 개요
2. 시장 분석
3. 추천 사항
4. 법적 검토사항
"""
```

출력:
```markdown
# 강남 아파트 투자 추천서

## 투자 개요
- 지역: 강남구
- 물건: 아파트
- 평균 가격: 15억원

## 시장 분석
- 가격 추세: 상승
- 투자 점수: 0.75 (높음)
- 리스크: 낮음

## 추천 사항
1. 85㎡ 이하 중소형 평형 투자 권장
2. 역삼동/삼성동 지역 우선 고려
3. 향후 6개월 내 매수 타이밍

## 법적 검토사항
- 주택임대차보호법 준수
- 부동산 거래 규정 확인
```

---

### 7.2 데이터 변환 추적

```
사용자 질문 (string)
    ↓ [LLM] PlanningAgent
Intent + Entities (dict)
    ↓ [규칙] AgentAdapter
Agent 목록 (list)
    ↓ [실행] SearchExecutor
DB 검색 결과 (list[dict])
    ↓ [규칙] StateManager
shared_context["search_results"] (dict)
    ↓ [실행] AnalysisExecutor
분석 보고서 (dict)
    ↓ [규칙] StateManager
shared_context["analysis_report"] (dict)
    ↓ [실행] DocumentExecutor + LLM
최종 문서 (markdown string)
    ↓ [LLM] Response Generator
사용자 친화적 답변 (string)
    ↓
사용자에게 전달
```

---

## 8. 실제 실행 예제

### 예제 1: 법률 상담

**입력**: "전세금 5% 인상이 가능한가요?"

**흐름**:
1. **Planning** (LLM #1)
   - Intent: `LEGAL_CONSULT`
   - Confidence: 0.90
   - Keywords: ["전세금", "인상", "5%"]

2. **Agent 선택**
   - Selected: `["search_team"]`
   - Strategy: `SEQUENTIAL`

3. **SearchExecutor 실행**
   - Scope: `["legal"]`
   - Tool: `legal_search_tool`
   - Results: 법률 조항 10건 검색

4. **Response Generation** (LLM #2)
   - Input: 법률 조항 + 질문
   - Output: "전세금 5% 인상은 주택임대차보호법 제7조에 따라..."

**LLM 호출**: 2회 (Planning + Response)
**처리 시간**: 약 10초

---

### 예제 2: 복합 분석

**입력**: "강남 아파트 시세 분석 후 투자 추천서 작성"

**흐름**:
1. **Planning** (LLM #1)
   - Intent: `COMPREHENSIVE`
   - Agents: `["search_team", "analysis_team", "document_team"]`

2. **SearchExecutor** (Tool 호출)
   - Market DB 검색: 10건

3. **AnalysisExecutor** (데이터 분석)
   - 평균 가격, 트렌드 계산

4. **DocumentExecutor** (LLM #3)
   - 투자 추천서 생성

5. **Response Generation** (LLM #4)
   - 최종 답변 생성

**LLM 호출**: 3회 (Planning + Document + Response)
**처리 시간**: 약 30초

---

## 9. 성능 최적화 포인트

### 9.1 병렬 실행

**최적화 대상**: 독립적인 검색들

```python
# 병렬 가능
async def execute_search_parallel(self, state):
    tasks = []
    if "legal" in search_scope:
        tasks.append(legal_search_tool.search(...))
    if "real_estate" in search_scope:
        tasks.append(market_data_tool.search(...))
    if "loan" in search_scope:
        tasks.append(loan_data_tool.search(...))

    results = await asyncio.gather(*tasks)
    # 3개 검색을 동시 실행 → 1/3 시간 단축
```

**효과**: 검색 시간 1/N (N = 병렬 작업 수)

---

### 9.2 LLM 호출 최소화

**전략 1: 캐싱**
```python
# Intent 분석 결과 캐싱 (동일 질문)
intent_cache = {}

if query in intent_cache:
    return intent_cache[query]  # LLM 호출 생략

result = await llm_analyze_intent(query)
intent_cache[query] = result
```

**전략 2: Batch 처리**
```python
# 여러 질문을 한 번의 LLM 호출로 처리
queries = ["질문1", "질문2", "질문3"]
results = await llm_batch_analyze(queries)
```

---

### 9.3 DB 쿼리 최적화

```python
# 인덱싱
CREATE INDEX idx_location ON properties(location);
CREATE INDEX idx_price ON properties(price);

# 결과 제한
market_data_tool.search(location="강남구", limit=10)  # 필요한 만큼만
```

---

## 10. 결론

### 10.1 시스템 특징 요약

| 특징 | 설명 | 장점 |
|------|------|------|
| **LLM 기반 Intent 분석** | 사용자 의도를 정확히 파악 | 유연한 질문 처리 |
| **규칙 기반 Agent 매핑** | Intent → Agent → Tool | 예측 가능성 |
| **팀 기반 협업** | 팀 간 명시적 데이터 전달 | 확장 용이 |
| **순차/병렬 실행** | 의존성 기반 전략 선택 | 성능 최적화 |
| **LLM 최종 응답 생성** | 자연스러운 답변 | 사용자 만족도 향상 |

### 10.2 LLM 사용 효율성

- **최소 호출**: 2회 (Planning + Response)
- **최대 호출**: 4회 (Planning + Document Gen + Document Review + Response)
- **평균 처리 시간**: 10-30초

### 10.3 확장 가능성

**새로운 Intent 추가**:
```python
# 1. Intent 정의
class IntentType(Enum):
    NEW_INTENT = "새로운의도"

# 2. Agent 매핑
intent_agent_mapping["NEW_INTENT"] = ["new_team"]

# 3. 끝! (자동으로 작동)
```

**새로운 Tool 추가**:
```python
# 1. Tool 클래스 작성
class NewTool:
    def search(self, ...):
        pass

# 2. SearchExecutor에 등록
self.new_tool = NewTool()

# 3. 검색 범위에 추가
if "new_scope" in search_scope:
    results = self.new_tool.search(...)
```

---

## 부록: 주요 코드 위치

| 컴포넌트 | 파일 경로 |
|----------|----------|
| **TeamBasedSupervisor** | `supervisor/team_supervisor.py` |
| **PlanningAgent** | `cognitive_agents/planning_agent.py` |
| **AgentRegistry** | `foundation/agent_registry.py` |
| **AgentAdapter** | `foundation/agent_adapter.py` |
| **SearchExecutor** | `execution_agents/search_team.py` |
| **AnalysisExecutor** | `execution_agents/analysis_team.py` |
| **DocumentExecutor** | `execution_agents/document_team.py` |
| **StateManager** | `foundation/separated_states.py` |

---

**문서 버전**: 1.0
**최종 수정일**: 2025-10-03
**작성자**: System Analysis Team
**상태**: COMPLETE ✅
