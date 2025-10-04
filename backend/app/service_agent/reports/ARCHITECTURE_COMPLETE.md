# Service Agent Complete Architecture Report
## Team-Based Multi-Agent System - 완전한 아키텍처 분석 및 구현 가이드

### 작성일: 2025-01-02
### 버전: 2.0 (통합 완전판)
### 상태: Production Ready

---

## 📋 Executive Summary

service_agent는 **Team-based Multi-Agent 아키텍처**의 완전한 구현체로, 3개의 전문 팀(Search, Document, Analysis)이 **TeamBasedSupervisor의 조정 하에 협업**하여 부동산 관련 복합 작업을 수행합니다.

### 핵심 성과

- ✅ **팀 간 완벽한 소통**: Team Supervisor가 팀 간 데이터 전달 및 조정
- ✅ **Planning Agent 통합**: LLM 기반 의도 분석 및 실행 계획 수립
- ✅ **동적 Agent 관리**: Registry 패턴으로 런타임 Agent 제어
- ✅ **State Pollution 방지**: 팀별 독립 State + StateManager로 결과 병합
- ✅ **병렬/순차 실행**: 전략적 워크플로우 관리

---

## 🏗️ Part 1: Architecture Overview

### 1.1 시스템 구성도

```
┌─────────────────────────────────────────────────────────────┐
│                    TeamBasedSupervisor                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  initialize → planning → execute_teams → aggregate   │  │
│  │                     ↓                                 │  │
│  │              PlanningAgent                           │  │
│  │          (의도 분석 + 실행 계획)                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                   │
│  ┌─────────────┬────────────────┬──────────────┐          │
│  │ SearchTeam  │ DocumentTeam   │ AnalysisTeam │          │
│  └─────────────┴────────────────┴──────────────┘          │
└─────────────────────────────────────────────────────────────┘
        ↓              ↓               ↓
┌──────────────┐ ┌───────────────┐ ┌──────────────┐
│ SearchAgent  │ │ DocumentAgent │ │AnalysisAgent │
│              │ │ ReviewAgent   │ │              │
└──────────────┘ └───────────────┘ └──────────────┘
        ↓              ↓               ↓
┌──────────────────────────────────────────────────┐
│           AgentRegistry (Singleton)               │
│  - search_agent (team: search, priority: 10)     │
│  - analysis_agent (team: analysis, priority: 5)  │
│  - document_agent (team: document, priority: 3)  │
│  - review_agent (team: document, priority: 3)    │
└──────────────────────────────────────────────────┘
```

### 1.2 폴더 구조 (실제)

```
service_agent/
├── core/                          # 핵심 인프라
│   ├── agent_adapter.py           # Agent Registry 통합 어댑터
│   ├── agent_registry.py          # 중앙 Agent 레지스트리 (Singleton)
│   ├── separated_states.py        # 팀별 독립 State 정의
│   ├── config.py                  # ✅ 설정파일 (DB경로, Model설정, Timeout 등)
│   ├── context.py                 # Context 관리
│   └── __init__.py
│
├── teams/                         # 팀 Supervisor (3개 팀)
│   ├── search_team.py             # SearchTeamSupervisor
│   ├── document_team.py           # DocumentTeamSupervisor
│   ├── analysis_team.py           # AnalysisTeamSupervisor
│   └── __init__.py
│
├── planning/                      # 계획 수립
│   ├── planning_agent.py          # PlanningAgent
│   └── __init__.py
│
├── supervisor/                    # 메인 조정자
│   ├── team_supervisor.py         # TeamBasedSupervisor ← 핵심!
│   └── __init__.py
│
├── tools/                         # 검색 도구
│   ├── hybrid_legal_search.py     # 하이브리드 법률 검색 (ChromaDB + SQLite)
│   ├── market_data_tool.py        # 부동산 시세 검색
│   ├── loan_data_tool.py          # 대출 상품 검색
│   └── __init__.py
│
├── models/                        # 임베딩 모델 (현재 비어있음)
│   └── KURE_v1/                   # 한국 법률 임베딩 모델 (예정)
│
├── tests/                         # 테스트 파일
│   ├── test_hybrid_legal_search.py
│   └── test_search_team_legal.py
│
├── reports/                       # 아키텍처 문서
│   └── ARCHITECTURE_COMPLETE.md   # 본 문서
│
├── 테스트 스크립트들              # 다양한 테스트 파일들
│   ├── allinone_test_*.py         # 통합 테스트 (5/10/25/50/100 쿼리)
│   ├── hn_agent_*.py              # Agent 테스트
│   ├── test_*.py                  # 개별 테스트
│   └── run_legal_test.py          # 법률 검색 테스트
│
├── 테스트 데이터                  # 테스트용 JSON 파일들
│   ├── test_queries_*.json
│   └── allinone_test_queries.json
│
└── __init__.py
```

**주요 변경사항:**
- ❌ `guides/` 디렉토리는 **존재하지 않음** (기존 보고서의 오류)
- ✅ `core/config.py` - 시스템 설정 파일 (DB 경로, Model 경로, Timeout 설정 등)
- ✅ `tools/` - 실제 검색 도구들이 위치
- ✅ `models/` - 임베딩 모델 디렉토리 (현재는 빈 폴더)
- ✅ `tests/` - 별도 테스트 디렉토리 존재

---

## 🔄 Part 2: Execution Flow (상세)

### 2.1 전체 실행 흐름

```
User Query: "강남 아파트 시세 분석 및 투자 추천서 작성"
    ↓
[1] TeamBasedSupervisor.initialize_node()
    - 세션 초기화
    - 변수 설정 (active_teams=[], completed_teams=[], team_results={})
    ↓
[2] TeamBasedSupervisor.planning_node()
    - PlanningAgent.analyze_intent(query)
      → Intent: "종합분석"
      → Keywords: ["강남", "아파트", "시세", "분석", "투자", "추천서"]
      → Entities: {location: "강남", property_type: "아파트"}

    - PlanningAgent.create_execution_plan(intent)
      → Strategy: "sequential" (순차 실행)
      → Steps: [
          {agent: "search_agent", team: "search", priority: 10},
          {agent: "analysis_agent", team: "analysis", priority: 5, depends: ["search_agent"]},
          {agent: "document_agent", team: "document", priority: 3, depends: ["analysis_agent"]}
        ]

    - active_teams 결정: ["search", "analysis", "document"]
    ↓
[3] TeamBasedSupervisor.execute_teams_node()
    - shared_state 생성 (user_query, session_id, timestamp)
    - Strategy = "sequential" → _execute_teams_sequential()

    [3-1] SearchTeam 실행
        ↓ SearchTeamSupervisor.app.ainvoke(...)
        ↓ prepare → route → search → aggregate → finalize
        ↓ Result: {
            "legal_results": [...],
            "real_estate_results": [...],
            "aggregated_results": {...},
            "status": "completed"
          }
        ↓ StateManager.merge_team_results()
            → main_state["team_results"]["search"] = result
            → main_state["shared_context"]["search_results"] = result["aggregated_results"]

    [3-2] AnalysisTeam 실행 (SearchTeam 결과 사용)
        ↓ input_data = {
            "data_source": "search_team",
            "data": main_state["shared_context"]["search_results"],  ← 전달!
            "metadata": {}
          }
        ↓ AnalysisTeamSupervisor.app.ainvoke(...)
        ↓ prepare → preprocess → analyze → generate_insights → create_report
        ↓ Result: {
            "metrics": {...},
            "insights": [...],
            "report": {...},
            "status": "completed"
          }
        ↓ StateManager.merge_team_results()
            → main_state["shared_context"]["analysis_report"] = result["report"]

    [3-3] DocumentTeam 실행 (AnalysisTeam 결과 사용)
        ↓ document_data = {
            "analysis_report": main_state["shared_context"]["analysis_report"],  ← 전달!
            "search_results": main_state["shared_context"]["search_results"]      ← 전달!
          }
        ↓ DocumentTeamSupervisor.app.ainvoke(...)
        ↓ prepare → generate → review → finalize
        ↓ Result: {
            "final_document": "투자 추천서 내용...",
            "review_result": {...},
            "status": "completed"
          }
    ↓
[4] TeamBasedSupervisor.aggregate_results_node()
    - 모든 팀 결과 통합
    - final_result = {
        "search": {...},
        "analysis": {...},
        "document": {...},
        "summary": "..."
      }
    ↓
[5] TeamBasedSupervisor.generate_response_node()
    - 사용자 응답 생성
    - status = "completed"
    ↓
END → User Response
```

### 2.2 TeamBasedSupervisor 상세 워크플로우

#### 노드별 역할

**initialize_node**
```python
async def initialize_node(self, state: MainSupervisorState):
    state["start_time"] = datetime.now()
    state["status"] = "initialized"
    state["current_phase"] = "initialization"
    state["active_teams"] = []
    state["completed_teams"] = []
    state["failed_teams"] = []
    state["team_results"] = {}
    state["error_log"] = []
    return state
```

**planning_node**
```python
async def planning_node(self, state: MainSupervisorState):
    # 1. 의도 분석
    query = state.get("query", "")
    intent_result = await self.planning_agent.analyze_intent(query)
    # → IntentType, confidence, keywords, entities

    # 2. 실행 계획 생성
    execution_plan = await self.planning_agent.create_execution_plan(intent_result)
    # → ExecutionPlan with steps, strategy, parallel_groups

    # 3. Planning State 생성
    planning_state = PlanningState(
        raw_query=query,
        analyzed_intent={...},
        execution_steps=[...],
        execution_strategy=execution_plan.strategy.value,
        parallel_groups=execution_plan.parallel_groups
    )

    # 4. 활성화할 팀 결정
    active_teams = set()
    for step in planning_state["execution_steps"]:
        team = step.get("team")
        if team:
            active_teams.add(team)

    state["active_teams"] = list(active_teams)
    state["planning_state"] = planning_state

    return state
```

**execute_teams_node**
```python
async def execute_teams_node(self, state: MainSupervisorState):
    execution_strategy = state.get("execution_plan", {}).get("strategy", "sequential")
    active_teams = state.get("active_teams", [])

    # 공유 상태 생성
    shared_state = StateManager.create_shared_state(
        query=state["query"],
        session_id=state["session_id"]
    )

    # 팀별 실행
    if execution_strategy == "parallel" and len(active_teams) > 1:
        results = await self._execute_teams_parallel(active_teams, shared_state, state)
    else:
        results = await self._execute_teams_sequential(active_teams, shared_state, state)

    # 결과 저장
    for team_name, team_result in results.items():
        state = StateManager.merge_team_results(state, team_name, team_result)

    return state
```

**_execute_teams_sequential** (핵심!)
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
        if team_name in self.teams:
            try:
                # 팀 실행
                result = await self._execute_single_team(team_name, shared_state, main_state)
                results[team_name] = result

                # ✅ 팀 간 데이터 전달
                if team_name == "search" and "analysis" in teams:
                    # SearchTeam 결과를 AnalysisTeam에 전달
                    main_state["team_results"][team_name] = self._extract_team_data(result, team_name)

                # ✅ shared_context 업데이트
                if team_name == "search":
                    main_state["shared_context"]["search_results"] = result.get("aggregated_results")
                elif team_name == "analysis":
                    main_state["shared_context"]["analysis_report"] = result.get("report")

            except Exception as e:
                logger.error(f"Team '{team_name}' failed: {e}")
                results[team_name] = {"status": "failed", "error": str(e)}

    return results
```

**_execute_single_team**
```python
async def _execute_single_team(
    self,
    team_name: str,
    shared_state: SharedState,
    main_state: MainSupervisorState
) -> Any:
    """단일 팀 실행 - 이전 팀 결과 활용"""

    team = self.teams[team_name]

    # 팀별 Input 구성
    if team_name == "search":
        team_input = {
            "user_query": shared_state["user_query"],
            "session_id": shared_state["session_id"],
            "shared_context": shared_state
        }

    elif team_name == "analysis":
        # ✅ SearchTeam 결과 사용
        team_input = {
            "user_query": shared_state["user_query"],
            "input_data": {
                "data_source": "search_team",
                "data": main_state["shared_context"].get("search_results", {}),
                "metadata": {}
            },
            "shared_context": shared_state
        }

    elif team_name == "document":
        # ✅ AnalysisTeam + SearchTeam 결과 사용
        team_input = {
            "document_type": self._infer_document_type(main_state),
            "document_data": {
                "analysis_report": main_state["shared_context"].get("analysis_report"),
                "search_results": main_state["shared_context"].get("search_results")
            },
            "shared_context": shared_state
        }

    # 팀 LangGraph 실행
    result = await team.app.ainvoke(team_input)

    return result
```

---

## 🧩 Part 3: Core Components (상세)

### 3.1 AgentRegistry (Singleton Pattern)

#### 클래스 구조

```python
class AgentCapabilities:
    """Agent 능력 정의"""
    name: str                    # Agent 이름
    description: str             # 설명
    input_types: List[str]       # 처리 가능 입력 타입
    output_types: List[str]      # 생성 출력 타입
    required_tools: List[str]    # 필요 도구 목록
    team: str                    # 소속 팀

class AgentMetadata:
    """Agent 메타데이터"""
    agent_class: Type            # Agent 클래스 참조
    team: Optional[str]          # 팀 이름
    capabilities: AgentCapabilities
    priority: int                # 실행 우선순위 (높을수록 먼저)
    enabled: bool                # 활성화 여부

class AgentRegistry:
    """중앙 Agent 레지스트리 (Singleton)"""
    _instance = None
    _agents: Dict[str, AgentMetadata] = {}
    _teams: Dict[str, List[str]] = {}
    _initialization_hooks: List[Callable] = []
```

#### 주요 메서드

**register()**
```python
@classmethod
def register(
    cls,
    name: str,
    agent_class: Type,
    team: Optional[str] = None,
    capabilities: Optional[AgentCapabilities] = None,
    priority: int = 0,
    enabled: bool = True
) -> None:
    """Agent를 레지스트리에 등록"""

    metadata = AgentMetadata(
        agent_class=agent_class,
        team=team,
        capabilities=capabilities,
        priority=priority,
        enabled=enabled
    )

    cls._agents[name] = metadata

    # 팀별 분류
    if team:
        if team not in cls._teams:
            cls._teams[team] = []
        if name not in cls._teams[team]:
            cls._teams[team].append(name)
```

**get_agent() / get_agent_class()**
```python
@classmethod
def get_agent(cls, name: str) -> Optional[AgentMetadata]:
    """특정 Agent 메타데이터 조회"""
    return cls._agents.get(name)

@classmethod
def get_agent_class(cls, name: str) -> Optional[Type]:
    """Agent 클래스 조회"""
    metadata = cls._agents.get(name)
    return metadata.agent_class if metadata else None
```

**create_agent()**
```python
@classmethod
def create_agent(cls, name: str, **kwargs) -> Optional[Any]:
    """Agent 인스턴스 생성"""

    metadata = cls._agents.get(name)
    if not metadata or not metadata.enabled:
        return None

    try:
        agent_instance = metadata.agent_class(**kwargs)
        return agent_instance
    except Exception as e:
        logger.error(f"Failed to create agent '{name}': {e}")
        return None
```

**list_agents()**
```python
@classmethod
def list_agents(cls, team: Optional[str] = None, enabled_only: bool = True) -> List[str]:
    """Agent 목록 조회 (우선순위 순 정렬)"""

    if team:
        agent_names = cls._teams.get(team, [])
    else:
        agent_names = list(cls._agents.keys())

    if enabled_only:
        agent_names = [
            name for name in agent_names
            if cls._agents[name].enabled
        ]

    # 우선순위 순으로 정렬
    agent_names.sort(
        key=lambda name: cls._agents[name].priority,
        reverse=True
    )

    return agent_names
```

**find_agents_by_capability()**
```python
@classmethod
def find_agents_by_capability(
    cls,
    input_type: Optional[str] = None,
    output_type: Optional[str] = None,
    required_tool: Optional[str] = None
) -> List[str]:
    """능력 기준으로 Agent 검색"""

    matching_agents = []

    for name, metadata in cls._agents.items():
        if not metadata.enabled or not metadata.capabilities:
            continue

        capabilities = metadata.capabilities

        # 조건 검사
        if input_type and input_type not in capabilities.input_types:
            continue
        if output_type and output_type not in capabilities.output_types:
            continue
        if required_tool and required_tool not in capabilities.required_tools:
            continue

        matching_agents.append(name)

    return matching_agents
```

#### 사용 예시

```python
# 1. Agent 등록
capabilities = AgentCapabilities(
    name="search_agent",
    description="법률, 부동산, 대출 정보를 검색하는 Agent",
    input_types=["query", "keywords"],
    output_types=["legal_search", "real_estate_search", "loan_search"],
    required_tools=["legal_search_tool", "real_estate_search_tool"],
    team="search"
)

AgentRegistry.register(
    name="search_agent",
    agent_class=SearchAgent,
    team="search",
    capabilities=capabilities,
    priority=10,
    enabled=True
)

# 2. Agent 조회
metadata = AgentRegistry.get_agent("search_agent")
print(f"Team: {metadata.team}, Priority: {metadata.priority}")

# 3. Agent 인스턴스 생성
agent = AgentRegistry.create_agent("search_agent", llm_context=context)

# 4. 팀별 Agent 목록
search_agents = AgentRegistry.list_agents(team="search")
# → ["search_agent"]

# 5. 능력 기반 검색
agents = AgentRegistry.find_agents_by_capability(
    input_type="query",
    output_type="legal_search"
)
# → ["search_agent"]
```

### 3.2 AgentAdapter

#### 역할 및 주요 기능

**역할**: 기존 Agent들을 Registry 시스템에 통합하는 어댑터

#### register_existing_agents()

```python
@staticmethod
def register_existing_agents():
    """모든 기존 Agent들을 Registry에 등록"""

    # 1. SearchAgent 등록
    from app.service.agents.search_agent import SearchAgent

    capabilities = AgentCapabilities(
        name="search_agent",
        description="법률, 부동산, 대출 정보를 검색하는 Agent",
        input_types=["query", "keywords"],
        output_types=["legal_search", "real_estate_search", "loan_search"],
        required_tools=["legal_search_tool", "real_estate_search_tool", "loan_search_tool"],
        team="search"
    )

    AgentRegistry.register(
        name="search_agent",
        agent_class=SearchAgent,
        team="search",
        capabilities=capabilities,
        priority=10,
        enabled=True
    )

    # 2. AnalysisAgent 등록
    from app.service.agents.analysis_agent import AnalysisAgent

    capabilities = AgentCapabilities(
        name="analysis_agent",
        description="수집된 데이터를 분석하고 보고서를 생성하는 Agent",
        input_types=["collected_data", "analysis_type"],
        output_types=["report", "insights", "recommendations"],
        required_tools=["analysis_tools"],
        team="analysis"
    )

    AgentRegistry.register(
        name="analysis_agent",
        agent_class=AnalysisAgent,
        team="analysis",
        capabilities=capabilities,
        priority=5,
        enabled=True
    )

    # 3. DocumentAgent 등록
    # 4. ReviewAgent 등록
    # ... (동일한 패턴)
```

#### execute_agent_dynamic()

```python
@staticmethod
async def execute_agent_dynamic(
    agent_name: str,
    input_data: Dict[str, Any],
    llm_context: Optional[Any] = None
) -> Dict[str, Any]:
    """Registry를 통해 Agent를 동적으로 실행"""

    # 1. Registry에서 Agent 클래스 조회
    agent_class = AgentRegistry.get_agent_class(agent_name)
    if not agent_class:
        return {"status": "error", "error": f"Agent '{agent_name}' not found"}

    # 2. Agent 활성화 여부 확인
    metadata = AgentRegistry.get_agent(agent_name)
    if not metadata.enabled:
        return {"status": "skipped", "error": f"Agent '{agent_name}' is disabled"}

    try:
        # 3. Agent 인스턴스 생성
        if agent_name in ["search_agent", "analysis_agent"]:
            agent = agent_class(llm_context=llm_context)
        else:
            agent = agent_class()

        # 4. Agent 실행
        if hasattr(agent, 'app') and agent.app:
            # LangGraph 기반 Agent
            result = await agent.app.ainvoke(input_data)
        elif hasattr(agent, 'execute'):
            # 일반 Agent
            result = await agent.execute(input_data)
        else:
            result = agent.run(input_data)

        return result

    except Exception as e:
        logger.error(f"Failed to execute agent '{agent_name}': {e}")
        return {"status": "error", "error": str(e), "agent": agent_name}
```

#### get_agents_for_intent()

```python
@staticmethod
def get_agents_for_intent(intent_type: str) -> list[str]:
    """의도 타입에 따라 실행할 Agent 목록 반환"""

    intent_agent_mapping = {
        "법률상담": ["search_agent"],
        "시세조회": ["search_agent", "analysis_agent"],
        "대출상담": ["search_agent", "analysis_agent"],
        "계약서작성": ["document_agent"],
        "계약서검토": ["review_agent"],
        "종합분석": ["search_agent", "analysis_agent"],
        "문서생성": ["document_agent"],
        "리스크분석": ["search_agent", "analysis_agent", "review_agent"],
        "전체분석": ["search_agent", "analysis_agent", "document_agent", "review_agent"]
    }

    agents = intent_agent_mapping.get(intent_type, ["search_agent"])

    # Registry에서 활성화된 Agent만 필터링
    enabled_agents = [
        agent for agent in agents
        if AgentRegistry.get_agent(agent) and AgentRegistry.get_agent(agent).enabled
    ]

    return enabled_agents
```

#### get_agent_dependencies()

```python
@staticmethod
def get_agent_dependencies(agent_name: str) -> Dict[str, Any]:
    """Agent의 의존성 정보 조회"""

    dependencies = {
        "search_agent": {
            "requires": [],
            "provides": ["legal_search", "real_estate_search", "loan_search"],
            "team": "search",
            "description": "정보 검색 Agent"
        },
        "analysis_agent": {
            "requires": ["collected_data"],
            "provides": ["report", "insights", "recommendations"],
            "team": "analysis",
            "description": "데이터 분석 Agent"
        },
        "document_agent": {
            "requires": ["document_type", "document_params"],
            "provides": ["generated_document"],
            "team": "document",
            "description": "문서 생성 Agent"
        },
        "review_agent": {
            "requires": ["document_content"],
            "provides": ["risk_analysis", "recommendations", "compliance_check"],
            "team": "document",
            "description": "문서 검토 Agent"
        }
    }

    return dependencies.get(agent_name, {})
```

### 3.3 SeparatedStates

#### State 계층 구조

```python
# 1. SharedState - 모든 팀이 공유하는 최소한의 상태
class SharedState(TypedDict):
    user_query: str
    session_id: str
    timestamp: str
    language: str
    status: Literal["pending", "processing", "completed", "error"]
    error_message: Optional[str]

# 2. SearchTeamState - 검색 팀 전용
class SearchTeamState(TypedDict):
    # Team identification
    team_name: str
    status: str

    # Shared context
    shared_context: Dict[str, Any]

    # Search specific
    keywords: Optional[SearchKeywords]
    search_scope: List[str]  # ["legal", "real_estate", "loan"]
    filters: Dict[str, Any]

    # Search results
    legal_results: List[Dict[str, Any]]
    real_estate_results: List[Dict[str, Any]]
    loan_results: List[Dict[str, Any]]
    aggregated_results: Dict[str, Any]

    # Metadata
    total_results: int
    search_time: float
    sources_used: List[str]
    search_progress: Dict[str, str]

    # Execution tracking
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    error: Optional[str]
    current_search: Optional[str]
    execution_strategy: Optional[str]

# 3. DocumentTeamState - 문서 팀 전용
class DocumentTeamState(TypedDict):
    team_name: str
    status: str
    shared_context: Dict[str, Any]

    # Document specific
    document_type: str
    template: Optional[DocumentTemplate]
    document_content: Optional[DocumentContent]
    generation_progress: Dict[str, str]

    # Review specific
    review_needed: bool
    review_result: Optional[ReviewResult]
    final_document: Optional[str]

    # Timing
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    generation_time: Optional[float]
    review_time: Optional[float]
    error: Optional[str]

# 4. AnalysisTeamState - 분석 팀 전용
class AnalysisTeamState(TypedDict):
    team_name: str
    status: str
    shared_context: Dict[str, Any]

    # Analysis specific
    analysis_type: str
    input_data: Optional[AnalysisInput]
    preprocessing_done: bool

    # Results
    metrics: Optional[AnalysisMetrics]
    insights: List[AnalysisInsight]
    report: Optional[AnalysisReport]
    recommendations: List[str]

    # Timing
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    analysis_time: Optional[float]
    error: Optional[str]

# 5. MainSupervisorState - 메인 Supervisor State
class MainSupervisorState(TypedDict):
    # Query
    query: str
    session_id: str

    # Planning
    planning_state: Optional[PlanningState]
    execution_plan: Dict[str, Any]

    # Team management
    active_teams: List[str]
    completed_teams: List[str]
    failed_teams: List[str]

    # Results
    team_results: Dict[str, Any]
    shared_context: Dict[str, Any]

    # Status
    status: str
    current_phase: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    error_log: List[str]
```

#### StateManager

```python
class StateManager:
    """State 관리 유틸리티"""

    @staticmethod
    def create_shared_state(query: str, session_id: str) -> SharedState:
        """공유 State 생성"""
        return SharedState(
            user_query=query,
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            language="ko",
            status="pending",
            error_message=None
        )

    @staticmethod
    def merge_team_results(
        main_state: MainSupervisorState,
        team_name: str,
        team_result: Dict[str, Any]
    ) -> MainSupervisorState:
        """팀 결과를 main_state에 병합"""

        # 1. 팀 결과 저장
        main_state["team_results"][team_name] = team_result

        # 2. 완료/실패 팀 목록 업데이트
        if team_result.get("status") == "completed":
            main_state["completed_teams"].append(team_name)
        elif team_result.get("status") == "failed":
            main_state["failed_teams"].append(team_name)

        # 3. 다음 팀을 위한 데이터 추출
        if team_name == "search":
            main_state["shared_context"]["search_results"] = team_result.get("aggregated_results")
        elif team_name == "analysis":
            main_state["shared_context"]["analysis_report"] = team_result.get("report")
            main_state["shared_context"]["insights"] = team_result.get("insights")
        elif team_name == "document":
            main_state["shared_context"]["final_document"] = team_result.get("final_document")

        return main_state
```

---

## 🎯 Part 4: Team Supervisors (상세)

### 4.1 SearchTeamSupervisor

#### 워크플로우

```
prepare → route → search → aggregate → finalize
            ↓ (skip)
          finalize
```

#### 노드 구현

**prepare_search_node**
```python
async def prepare_search_node(self, state: SearchTeamState) -> SearchTeamState:
    """검색 준비 - 키워드 추출 및 검색 범위 설정"""

    user_query = state.get("shared_context", {}).get("user_query", "")

    # 1. 키워드 추출 (간단한 패턴 매칭 또는 LLM)
    keywords = self._extract_keywords(user_query)

    state["keywords"] = SearchKeywords(
        legal=keywords.get("legal", []),
        real_estate=keywords.get("real_estate", []),
        loan=keywords.get("loan", []),
        general=keywords.get("general", [])
    )

    # 2. 검색 범위 결정
    state["search_scope"] = self._determine_search_scope(user_query, keywords)
    # → ["legal", "real_estate"] or ["loan"] 등

    # 3. 필터 설정
    state["filters"] = self._build_filters(user_query)

    state["status"] = "prepared"
    state["start_time"] = datetime.now()

    return state
```

**route_search_node & _route_decision**
```python
def _route_decision(self, state: SearchTeamState) -> str:
    """검색 실행 여부 결정"""

    if not state.get("search_scope"):
        return "skip"

    return "search"
```

**execute_search_node**
```python
async def execute_search_node(self, state: SearchTeamState) -> SearchTeamState:
    """Agent 동적 실행 - 실제 검색 수행"""

    state["current_search"] = "executing"

    # AgentAdapter를 통한 동적 실행
    input_data = {
        "query": state.get("shared_context", {}).get("user_query"),
        "keywords": state.get("keywords"),
        "search_scope": state.get("search_scope"),
        "filters": state.get("filters")
    }

    result = await AgentAdapter.execute_agent_dynamic(
        "search_agent",
        input_data,
        self.llm_context
    )

    # 결과 분해
    state["legal_results"] = result.get("legal_results", [])
    state["real_estate_results"] = result.get("real_estate_results", [])
    state["loan_results"] = result.get("loan_results", [])

    state["current_search"] = "completed"

    return state
```

**aggregate_results_node**
```python
async def aggregate_results_node(self, state: SearchTeamState) -> SearchTeamState:
    """결과 통합"""

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
    state["total_results"] = aggregated["total_count"]
    state["sources_used"] = state.get("search_scope", [])

    return state
```

**finalize_node**
```python
async def finalize_node(self, state: SearchTeamState) -> SearchTeamState:
    """최종 정리"""

    state["status"] = "completed"
    state["end_time"] = datetime.now()

    if state.get("start_time"):
        state["search_time"] = (state["end_time"] - state["start_time"]).total_seconds()

    return state
```

### 4.2 DocumentTeamSupervisor

#### 워크플로우

```
prepare → generate → review_decision → review → finalize
                            ↓ (skip)
                          finalize
```

#### 노드 구현

**prepare_document_node**
```python
async def prepare_document_node(self, state: DocumentTeamState) -> DocumentTeamState:
    """문서 생성 준비"""

    document_type = state.get("document_type", "lease_contract")

    # 템플릿 로드
    template = self.templates.get(document_type)
    if not template:
        state["error"] = f"Template not found: {document_type}"
        state["status"] = "failed"
        return state

    state["template"] = template
    state["status"] = "prepared"
    state["start_time"] = datetime.now()

    return state
```

**generate_document_node**
```python
async def generate_document_node(self, state: DocumentTeamState) -> DocumentTeamState:
    """문서 생성"""

    input_data = {
        "template": state.get("template"),
        "document_data": state.get("document_data", {}),
        "shared_context": state.get("shared_context")
    }

    result = await AgentAdapter.execute_agent_dynamic(
        "document_agent",
        input_data,
        self.llm_context
    )

    state["document_content"] = result.get("document_content")
    state["generation_progress"]["generate"] = "completed"

    return state
```

**review_document_node**
```python
async def review_document_node(self, state: DocumentTeamState) -> DocumentTeamState:
    """문서 검토"""

    if not state.get("review_needed", True):
        return state

    input_data = {
        "document_content": state.get("document_content"),
        "document_type": state.get("document_type"),
        "shared_context": state.get("shared_context")
    }

    result = await AgentAdapter.execute_agent_dynamic(
        "review_agent",
        input_data,
        self.llm_context
    )

    state["review_result"] = ReviewResult(
        reviewed=True,
        risk_level=result.get("risk_level", "low"),
        risks=result.get("risks", []),
        recommendations=result.get("recommendations", []),
        compliance_check=result.get("compliance_check", {})
    )

    state["generation_progress"]["review"] = "completed"

    return state
```

**finalize_document_node**
```python
async def finalize_document_node(self, state: DocumentTeamState) -> DocumentTeamState:
    """최종 문서 완성"""

    # 검토 결과 반영
    document_content = state.get("document_content")
    review_result = state.get("review_result")

    if review_result and review_result.get("recommendations"):
        # 권장사항을 문서에 추가
        final_doc = self._apply_review_recommendations(
            document_content,
            review_result
        )
    else:
        final_doc = document_content

    state["final_document"] = final_doc
    state["status"] = "completed"
    state["end_time"] = datetime.now()

    if state.get("start_time"):
        state["generation_time"] = (state["end_time"] - state["start_time"]).total_seconds()

    return state
```

### 4.3 AnalysisTeamSupervisor

#### 워크플로우

```
prepare → preprocess → analyze → generate_insights → create_report → finalize
```

#### 노드 구현

**prepare_analysis_node**
```python
async def prepare_analysis_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
    """분석 준비"""

    # 분석 타입 결정
    user_query = state.get("shared_context", {}).get("user_query", "")
    analysis_type = self._infer_analysis_type(user_query)
    # → "comprehensive", "market", "risk", "comparison"

    state["analysis_type"] = analysis_type
    state["status"] = "prepared"
    state["start_time"] = datetime.now()

    return state
```

**preprocess_data_node**
```python
async def preprocess_data_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
    """데이터 전처리"""

    input_data = state.get("input_data")

    if not input_data:
        state["preprocessing_done"] = False
        return state

    # 데이터 정제, 변환, 정규화
    preprocessed = self._preprocess(input_data)

    state["input_data"] = preprocessed
    state["preprocessing_done"] = True

    return state
```

**analyze_data_node**
```python
async def analyze_data_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
    """데이터 분석"""

    analysis_type = state.get("analysis_type")
    input_data = state.get("input_data")

    # 분석 메서드 선택
    analysis_method = self.analysis_methods.get(analysis_type, self._comprehensive_analysis)

    # Agent 실행 또는 직접 분석
    result = await AgentAdapter.execute_agent_dynamic(
        "analysis_agent",
        {
            "analysis_type": analysis_type,
            "data": input_data,
            "shared_context": state.get("shared_context")
        },
        self.llm_context
    )

    # Metrics 추출
    state["metrics"] = AnalysisMetrics(
        avg_price=result.get("avg_price"),
        max_price=result.get("max_price"),
        min_price=result.get("min_price"),
        price_trend=result.get("price_trend"),
        risk_score=result.get("risk_score"),
        investment_score=result.get("investment_score")
    )

    return state
```

**generate_insights_node**
```python
async def generate_insights_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
    """인사이트 생성"""

    metrics = state.get("metrics")
    input_data = state.get("input_data")

    # 패턴 인식, 이상 탐지, 트렌드 분석
    insights = []

    # 예시: 가격 트렌드 인사이트
    if metrics and metrics.get("price_trend"):
        insights.append(AnalysisInsight(
            insight_type="trend",
            content=f"가격이 {metrics['price_trend']} 추세입니다.",
            confidence=0.85,
            supporting_data={"metrics": metrics}
        ))

    state["insights"] = insights

    return state
```

**create_report_node**
```python
async def create_report_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
    """보고서 생성"""

    metrics = state.get("metrics")
    insights = state.get("insights", [])

    report = AnalysisReport(
        title=f"{state.get('analysis_type')} 분석 보고서",
        summary=self._create_summary(metrics, insights),
        sections=[
            {"title": "시장 개요", "content": "..."},
            {"title": "주요 지표", "content": metrics},
            {"title": "인사이트", "content": insights}
        ],
        metrics=metrics,
        insights=insights,
        recommendations=self._generate_recommendations(metrics, insights)
    )

    state["report"] = report
    state["recommendations"] = report["recommendations"]

    return state
```

**finalize_node**
```python
async def finalize_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
    """최종 정리"""

    state["status"] = "completed"
    state["end_time"] = datetime.now()

    if state.get("start_time"):
        state["analysis_time"] = (state["end_time"] - state["start_time"]).total_seconds()

    return state
```

---

## 🚀 Part 5: Planning Agent (상세)

### 5.1 PlanningAgent 구조

```python
class PlanningAgent:
    """의도 분석 및 실행 계획 수립"""

    def __init__(self, llm_client):
        self.llm = llm_client

    async def analyze_intent(self, query: str) -> IntentResult:
        """LLM 기반 의도 분석"""

        prompt = f"""
        사용자 쿼리: {query}

        다음 중 하나의 의도로 분류하세요:
        - 법률상담: 법률 정보 검색
        - 시세조회: 부동산 시세 확인
        - 대출상담: 대출 관련 정보
        - 계약서작성: 계약서 생성
        - 계약서검토: 계약서 검토
        - 종합분석: 검색 + 분석
        - 리스크분석: 검색 + 분석 + 검토
        - 전체분석: 모든 Agent 활용

        JSON 형식으로 반환:
        {{
            "intent_type": "...",
            "confidence": 0.0-1.0,
            "keywords": ["..."],
            "entities": {{"key": "value"}}
        }}
        """

        response = await self.llm.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        return IntentResult(
            intent_type=IntentType(result["intent_type"]),
            confidence=result["confidence"],
            keywords=result["keywords"],
            entities=result["entities"]
        )

    async def create_execution_plan(self, intent_result: IntentResult) -> ExecutionPlan:
        """실행 계획 생성"""

        intent_type = intent_result.intent_type

        # 의도별 Agent 매핑
        agents = AgentAdapter.get_agents_for_intent(intent_type.value)

        # ExecutionStep 생성
        steps = []
        for i, agent_name in enumerate(agents):
            deps = AgentAdapter.get_agent_dependencies(agent_name)

            step = ExecutionStep(
                step_id=f"step_{i}",
                agent_name=agent_name,
                team=deps.get("team"),
                priority=10 - i,  # 순서대로 우선순위
                dependencies=deps.get("requires", []),
                timeout=30,
                optional=False
            )
            steps.append(step)

        # 전략 결정
        strategy = self._determine_strategy(steps)

        # 병렬 그룹 생성
        parallel_groups = self._create_parallel_groups(steps) if strategy == ExecutionStrategy.PARALLEL else []

        return ExecutionPlan(
            steps=steps,
            strategy=strategy,
            parallel_groups=parallel_groups,
            estimated_time=sum(step.timeout for step in steps)
        )

    def _determine_strategy(self, steps: List[ExecutionStep]) -> ExecutionStrategy:
        """실행 전략 결정"""

        # 의존성 확인
        has_dependencies = any(step.dependencies for step in steps)

        if has_dependencies:
            return ExecutionStrategy.SEQUENTIAL
        elif len(steps) > 1:
            return ExecutionStrategy.PARALLEL
        else:
            return ExecutionStrategy.SEQUENTIAL
```

### 5.2 데이터 타입

```python
class IntentType(Enum):
    법률상담 = "법률상담"
    시세조회 = "시세조회"
    대출상담 = "대출상담"
    계약서작성 = "계약서작성"
    계약서검토 = "계약서검토"
    종합분석 = "종합분석"
    리스크분석 = "리스크분석"
    전체분석 = "전체분석"

@dataclass
class IntentResult:
    intent_type: IntentType
    confidence: float
    keywords: List[str]
    entities: Dict[str, Any]

class ExecutionStrategy(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    DAG = "dag"

@dataclass
class ExecutionStep:
    step_id: str
    agent_name: str
    team: str
    priority: int
    dependencies: List[str]
    timeout: int
    optional: bool

@dataclass
class ExecutionPlan:
    steps: List[ExecutionStep]
    strategy: ExecutionStrategy
    parallel_groups: List[List[str]]
    estimated_time: float
```

---

## 📊 Part 6: 실제 실행 시나리오 (완전한 예시)

### 시나리오: "강남 아파트 시세 분석 후 투자 추천서 작성"

#### 1단계: 초기화 및 Planning

```python
# 사용자 입력
user_query = "강남 아파트 시세 분석 후 투자 추천서 작성"
session_id = "session_20250102_001"

# TeamBasedSupervisor 실행
supervisor = TeamBasedSupervisor(llm_context)

# [initialize_node]
state = {
    "query": user_query,
    "session_id": session_id,
    "start_time": datetime.now(),
    "status": "initialized",
    "active_teams": [],
    "completed_teams": [],
    "failed_teams": [],
    "team_results": {},
    "shared_context": {},
    "error_log": []
}

# [planning_node]
# 1. 의도 분석
intent_result = await planning_agent.analyze_intent(user_query)
# → IntentResult(
#     intent_type=IntentType.전체분석,
#     confidence=0.92,
#     keywords=["강남", "아파트", "시세", "분석", "투자", "추천서"],
#     entities={"location": "강남", "property_type": "아파트"}
#   )

# 2. 실행 계획 생성
execution_plan = await planning_agent.create_execution_plan(intent_result)
# → ExecutionPlan(
#     steps=[
#         ExecutionStep(step_id="step_0", agent_name="search_agent", team="search", priority=10, dependencies=[], timeout=30),
#         ExecutionStep(step_id="step_1", agent_name="analysis_agent", team="analysis", priority=9, dependencies=["search_agent"], timeout=30),
#         ExecutionStep(step_id="step_2", agent_name="document_agent", team="document", priority=8, dependencies=["analysis_agent"], timeout=30)
#     ],
#     strategy=ExecutionStrategy.SEQUENTIAL,
#     parallel_groups=[],
#     estimated_time=90.0
#   )

# 3. active_teams 결정
state["active_teams"] = ["search", "analysis", "document"]
state["execution_plan"] = execution_plan
```

#### 2단계: SearchTeam 실행

```python
# [execute_teams_node] → _execute_teams_sequential()
# [SearchTeam 실행]

# shared_state 생성
shared_state = {
    "user_query": "강남 아파트 시세 분석 후 투자 추천서 작성",
    "session_id": "session_20250102_001",
    "timestamp": "2025-01-02T10:30:00",
    "language": "ko",
    "status": "processing"
}

# SearchTeamSupervisor.app.ainvoke()
search_input = {
    "user_query": shared_state["user_query"],
    "session_id": shared_state["session_id"],
    "shared_context": shared_state
}

# SearchTeam 내부 실행
# → prepare_search_node()
search_state = {
    "team_name": "search",
    "shared_context": shared_state,
    "keywords": {
        "legal": ["임대차", "계약"],
        "real_estate": ["강남", "아파트", "시세"],
        "loan": [],
        "general": ["투자", "추천"]
    },
    "search_scope": ["real_estate", "legal"],
    "status": "prepared"
}

# → execute_search_node()
# AgentAdapter.execute_agent_dynamic("search_agent", ...)
search_agent_result = {
    "legal_results": [
        {"title": "주택임대차보호법", "content": "...", "relevance": 0.85},
        {"title": "부동산 거래 규정", "content": "...", "relevance": 0.78}
    ],
    "real_estate_results": [
        {"address": "강남구 역삼동", "price": 12억, "area": 85, "type": "아파트"},
        {"address": "강남구 삼성동", "price": 15억, "area": 102, "type": "아파트"},
        {"address": "강남구 대치동", "price": 18억, "area": 120, "type": "아파트"}
    ],
    "loan_results": []
}

search_state["legal_results"] = search_agent_result["legal_results"]
search_state["real_estate_results"] = search_agent_result["real_estate_results"]

# → aggregate_results_node()
search_state["aggregated_results"] = {
    "legal": search_state["legal_results"],
    "real_estate": search_state["real_estate_results"],
    "total_count": 5,
    "search_scope": ["real_estate", "legal"]
}

# → finalize_node()
search_state["status"] = "completed"
search_state["search_time"] = 6.5

# SearchTeam 결과 반환
search_result = search_state

# StateManager.merge_team_results()
main_state["team_results"]["search"] = search_result
main_state["shared_context"]["search_results"] = search_result["aggregated_results"]
main_state["completed_teams"].append("search")
```

#### 3단계: AnalysisTeam 실행 (SearchTeam 결과 사용)

```python
# [AnalysisTeam 실행]

# input_data 구성 (SearchTeam 결과 활용)
analysis_input = {
    "user_query": shared_state["user_query"],
    "input_data": {
        "data_source": "search_team",
        "data": main_state["shared_context"]["search_results"],  # ← SearchTeam 결과
        "metadata": {"location": "강남", "property_type": "아파트"}
    },
    "shared_context": shared_state
}

# AnalysisTeamSupervisor.app.ainvoke()
# → prepare_analysis_node()
analysis_state = {
    "team_name": "analysis",
    "shared_context": shared_state,
    "analysis_type": "comprehensive",
    "input_data": analysis_input["input_data"],
    "status": "prepared"
}

# → analyze_data_node()
# AgentAdapter.execute_agent_dynamic("analysis_agent", ...)
analysis_agent_result = {
    "avg_price": 15억,
    "max_price": 18억,
    "min_price": 12억,
    "price_trend": "상승",
    "risk_score": 0.35,
    "investment_score": 0.75
}

analysis_state["metrics"] = analysis_agent_result

# → generate_insights_node()
analysis_state["insights"] = [
    {
        "insight_type": "trend",
        "content": "강남 아파트 가격이 상승 추세입니다.",
        "confidence": 0.85,
        "supporting_data": {"metrics": analysis_agent_result}
    },
    {
        "insight_type": "opportunity",
        "content": "현재 투자 적기로 판단됩니다 (투자점수: 0.75).",
        "confidence": 0.78,
        "supporting_data": {"investment_score": 0.75}
    }
]

# → create_report_node()
analysis_state["report"] = {
    "title": "강남 아파트 종합 분석 보고서",
    "summary": "강남 아파트는 평균 15억원으로, 상승 추세를 보이고 있습니다.",
    "sections": [
        {"title": "시장 개요", "content": "..."},
        {"title": "주요 지표", "content": analysis_state["metrics"]},
        {"title": "인사이트", "content": analysis_state["insights"]}
    ],
    "metrics": analysis_state["metrics"],
    "insights": analysis_state["insights"],
    "recommendations": [
        "85㎡ 이하 중소형 평형 투자 권장",
        "역삼동/삼성동 지역 우선 고려",
        "향후 6개월 내 매수 타이밍"
    ]
}

# → finalize_node()
analysis_state["status"] = "completed"
analysis_state["analysis_time"] = 8.3

# AnalysisTeam 결과 반환
analysis_result = analysis_state

# StateManager.merge_team_results()
main_state["team_results"]["analysis"] = analysis_result
main_state["shared_context"]["analysis_report"] = analysis_result["report"]
main_state["shared_context"]["insights"] = analysis_result["insights"]
main_state["completed_teams"].append("analysis")
```

#### 4단계: DocumentTeam 실행 (AnalysisTeam + SearchTeam 결과 사용)

```python
# [DocumentTeam 실행]

# document_data 구성 (이전 팀 결과 활용)
document_input = {
    "document_type": "investment_recommendation",
    "document_data": {
        "analysis_report": main_state["shared_context"]["analysis_report"],  # ← AnalysisTeam
        "search_results": main_state["shared_context"]["search_results"],     # ← SearchTeam
        "property_info": {
            "location": "강남",
            "type": "아파트",
            "avg_price": 15억
        }
    },
    "shared_context": shared_state
}

# DocumentTeamSupervisor.app.ainvoke()
# → prepare_document_node()
document_state = {
    "team_name": "document",
    "shared_context": shared_state,
    "document_type": "investment_recommendation",
    "template": {
        "template_id": "invest_001",
        "template_name": "투자 추천서",
        "required_fields": ["property_info", "analysis_summary", "recommendations"]
    },
    "document_data": document_input["document_data"],
    "status": "prepared"
}

# → generate_document_node()
# AgentAdapter.execute_agent_dynamic("document_agent", ...)
document_state["document_content"] = {
    "title": "강남 아파트 투자 추천서",
    "content": """
    [투자 개요]
    - 지역: 강남구
    - 물건: 아파트
    - 평균 가격: 15억원

    [시장 분석]
    - 가격 추세: 상승
    - 투자 점수: 0.75 (높음)
    - 리스크 점수: 0.35 (낮음)

    [추천 사항]
    1. 85㎡ 이하 중소형 평형 투자 권장
    2. 역삼동/삼성동 지역 우선 고려
    3. 향후 6개월 내 매수 타이밍

    [법적 검토사항]
    - 주택임대차보호법 준수
    - 부동산 거래 규정 확인
    """,
    "metadata": {"created_at": "2025-01-02", "version": "1.0"}
}

# → review_document_node()
# AgentAdapter.execute_agent_dynamic("review_agent", ...)
document_state["review_result"] = {
    "reviewed": True,
    "risk_level": "low",
    "risks": [
        {"type": "legal", "description": "계약서 상세 조항 검토 필요", "severity": "low"}
    ],
    "recommendations": [
        "전문가 법률 자문 권장",
        "재무 상담 병행 추천"
    ],
    "compliance_check": {
        "legal_compliance": True,
        "financial_disclosure": True
    }
}

# → finalize_document_node()
document_state["final_document"] = f"""
{document_state["document_content"]["content"]}

[전문가 검토]
- 위험도: 낮음
- 법적 준수: 통과
- 추가 권장사항: {document_state["review_result"]["recommendations"]}
"""

document_state["status"] = "completed"
document_state["generation_time"] = 12.1

# DocumentTeam 결과 반환
document_result = document_state

# StateManager.merge_team_results()
main_state["team_results"]["document"] = document_result
main_state["shared_context"]["final_document"] = document_result["final_document"]
main_state["completed_teams"].append("document")
```

#### 5단계: 결과 통합 및 응답 생성

```python
# [aggregate_results_node]
main_state["aggregated_result"] = {
    "search_summary": {
        "total_properties": 3,
        "avg_price": 15억,
        "locations": ["역삼동", "삼성동", "대치동"]
    },
    "analysis_summary": {
        "trend": "상승",
        "investment_score": 0.75,
        "risk_score": 0.35,
        "key_insights": [
            "가격 상승 추세",
            "투자 적기"
        ]
    },
    "document_summary": {
        "document_type": "투자 추천서",
        "status": "완료",
        "reviewed": True
    }
}

# [generate_response_node]
final_response = {
    "status": "success",
    "query": "강남 아파트 시세 분석 후 투자 추천서 작성",
    "result": {
        "search_results": main_state["team_results"]["search"]["aggregated_results"],
        "analysis_report": main_state["team_results"]["analysis"]["report"],
        "final_document": main_state["team_results"]["document"]["final_document"]
    },
    "summary": """
    강남 아파트 시세 분석 및 투자 추천서가 완성되었습니다.

    주요 결과:
    - 평균 시세: 15억원
    - 투자 점수: 0.75 (높음)
    - 추천: 85㎡ 이하 중소형 평형, 역삼/삼성동 지역
    - 추천서: 법적 검토 완료
    """,
    "completed_teams": ["search", "analysis", "document"],
    "total_execution_time": 26.9,
    "session_id": "session_20250102_001"
}

# 사용자에게 반환
return final_response
```

---

## 💡 Part 7: 핵심 통찰 및 아키텍처 강점

### 7.1 팀 간 데이터 흐름의 완벽한 구현

**핵심 메커니즘**:
1. **SharedState**: 기본 정보 공유 (query, session_id)
2. **shared_context**: 팀 간 데이터 전달 채널
3. **StateManager**: 팀 결과 자동 병합
4. **_execute_single_team()**: 이전 팀 결과를 다음 팀 input으로 구성

**데이터 전달 예시**:
```
SearchTeam.aggregated_results
    ↓ (StateManager.merge_team_results)
main_state["shared_context"]["search_results"]
    ↓ (_execute_single_team)
AnalysisTeam.input_data["data"]
    ↓
AnalysisTeam.report
    ↓ (StateManager.merge_team_results)
main_state["shared_context"]["analysis_report"]
    ↓ (_execute_single_team)
DocumentTeam.document_data["analysis_report"]
```

### 7.2 Planning Agent의 역할

**1. 의도 분석**
- LLM 기반 정확한 의도 파악
- confidence score로 신뢰도 측정
- keywords, entities 추출

**2. 실행 계획 수립**
- 의도별 최적 Agent 조합 선택
- 의존성 기반 실행 순서 결정
- 병렬/순차 전략 자동 선택

**3. 동적 실행 제어**
- AgentRegistry와 연동
- 활성화된 Agent만 선택
- 실패 시 대체 전략 가능

### 7.3 AgentRegistry의 위력

**1. 동적 Agent 관리**
```python
# 런타임에 Agent 추가/제거
AgentRegistry.register("new_agent", NewAgent, ...)
AgentRegistry.set_enabled("old_agent", False)
```

**2. 능력 기반 검색**
```python
# 특정 기능이 필요한 Agent 자동 검색
agents = AgentRegistry.find_agents_by_capability(
    output_type="legal_search"
)
```

**3. 팀별 관리**
```python
# 팀별 Agent 목록 (우선순위 순)
search_agents = AgentRegistry.list_agents(team="search")
```

### 7.4 State Pollution 방지

**문제**: 모든 팀이 하나의 State를 공유하면 간섭 발생

**해결책**:
- 각 팀은 독립적인 State 사용 (SearchTeamState, DocumentTeamState, AnalysisTeamState)
- 공유 필요한 정보만 shared_context에 명시적 전달
- StateManager가 결과 병합 책임

**효과**:
- 팀 간 간섭 없음
- 각 팀은 독립적으로 개발/테스트 가능
- State 구조 변경이 다른 팀에 영향 없음

---

## 🛠️ Part 8: 기술 스택 및 구현 세부사항

### 8.1 사용 기술

**Core**:
- **LangGraph 0.6**: StateGraph, START, END
- **LangChain**: LLM 통합
- **OpenAI GPT-4**: Planning, Analysis
- **Python 3.10+**: AsyncIO, TypedDict

**Pattern**:
- **Singleton**: AgentRegistry
- **Factory**: Agent 생성
- **Adapter**: 기존 Agent 통합
- **Strategy**: 실행 전략 (parallel/sequential)

### 8.2 LangGraph 0.6 활용

**StateGraph**
```python
workflow = StateGraph(SearchTeamState)
workflow.add_node("prepare", self.prepare_node)
workflow.add_node("search", self.search_node)
workflow.add_edge("prepare", "search")
workflow.add_conditional_edges(
    "search",
    self._route_decision,
    {"continue": "aggregate", "skip": END}
)
app = workflow.compile()
```

**비동기 실행**
```python
result = await team.app.ainvoke(input_data)
```

**병렬 실행**
```python
tasks = [team.app.ainvoke(data) for team in teams]
results = await asyncio.gather(*tasks)
```

### 8.3 에러 처리

**팀 레벨**
```python
try:
    result = await self._execute_single_team(team_name, ...)
    results[team_name] = result
except Exception as e:
    logger.error(f"Team '{team_name}' failed: {e}")
    results[team_name] = {"status": "failed", "error": str(e)}
    main_state["failed_teams"].append(team_name)
```

**부분 실패 허용**
- 하나의 팀이 실패해도 다른 팀은 계속 실행
- failed_teams 목록에 기록
- 사용 가능한 결과만으로 응답 생성

---

## 📈 Part 9: 성능 및 확장성

### 9.1 성능 특징

**병렬 실행**:
- 독립적인 팀은 동시 실행 (예: 법률 검색 + 부동산 검색)
- asyncio.gather로 구현

**선택적 실행**:
- 필요한 팀만 활성화
- 리소스 효율적 사용

**캐싱** (향후):
- 검색 결과 캐싱
- 분석 결과 재사용

### 9.2 확장성

**새 Agent 추가**:
```python
# 1. Agent 클래스 작성
class NewAgent:
    pass

# 2. Registry 등록
AgentRegistry.register(
    name="new_agent",
    agent_class=NewAgent,
    team="new_team",
    capabilities=...,
    priority=5
)

# 3. 의도 매핑 추가
intent_agent_mapping["새로운의도"] = ["new_agent"]
```

**새 팀 추가**:
```python
# 1. TeamState 정의
class NewTeamState(TypedDict):
    team_name: str
    # ...

# 2. TeamSupervisor 작성
class NewTeamSupervisor:
    def _build_subgraph(self):
        workflow = StateGraph(NewTeamState)
        # ...

# 3. TeamBasedSupervisor에 등록
self.teams["new_team"] = NewTeamSupervisor(llm_context)
```

---

## 🚀 Part 10: 고도화 계획

### 10.1 LangGraph 0.6 최신 기능 통합

**Context API**
```python
from langgraph.context import Context

@dataclass
class ServiceContext(Context):
    llm_model: str
    user_id: str
    session_id: str

async def node(self, state, *, ctx: ServiceContext):
    llm = ChatOpenAI(model=ctx.llm_model)
    # ...
```

**Checkpointer**
```python
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver("checkpoints.db")
app = workflow.compile(checkpointer=checkpointer)

# 중단된 지점에서 재개
result = await app.ainvoke(
    state,
    config={"thread_id": session_id, "checkpoint_id": last_checkpoint}
)
```

**Interrupt/Command**
```python
from langgraph.types import interrupt

async def confirm_node(self, state):
    user_response = interrupt({
        "type": "confirmation",
        "message": "실행하시겠습니까?",
        "options": ["yes", "no"]
    })

    if user_response["action"] == "yes":
        return state
    else:
        state["status"] = "cancelled"
        return state
```

### 10.2 고급 Planning

**DAG 실행**
```python
import networkx as nx

def execute_dag(self, plan):
    # 1. DAG 생성
    dag = nx.DiGraph()
    for step in plan.steps:
        dag.add_node(step.agent_name)
        for dep in step.dependencies:
            dag.add_edge(dep, step.agent_name)

    # 2. 위상 정렬 기반 레벨별 실행
    for level in nx.topological_generations(dag):
        # 같은 레벨 = 병렬 실행
        await asyncio.gather(*[execute(node) for node in level])
```

**적응형 실행**
```python
async def execute_adaptive(self, plan):
    """실행 중 계획 조정"""

    results = {}
    remaining = plan.steps.copy()

    while remaining:
        # 실행 가능한 Agent
        executable = [s for s in remaining if all(d in results for d in s.dependencies)]

        # 병렬 실행
        step_results = await asyncio.gather(*[execute(s) for s in executable])

        # 실패 시 대체 Agent 추가
        for step, result in zip(executable, step_results):
            if result["status"] == "failed":
                alternative = find_alternative(step)
                if alternative:
                    remaining.append(alternative)
```

### 10.3 Streaming

```python
async def stream_execution(self, query, session_id):
    """실시간 실행 스트리밍"""

    stream = self.app.astream(
        {"query": query, "session_id": session_id},
        config={"thread_id": session_id}
    )

    async for event in stream:
        if event.get("planning"):
            yield {"type": "plan", "data": event["planning"]}
        elif event.get("team_started"):
            yield {"type": "team_start", "team": event["team_started"]}
        elif event.get("team_completed"):
            yield {"type": "team_complete", "result": event["result"]}
```

---

## 📝 Part 11: 현재 시스템 문제점 및 개선 방향

### 11.1 현재 달성된 것

✅ **완벽한 팀 간 소통 아키텍처**
- TeamBasedSupervisor가 팀 간 데이터 전달 및 조정
- StateManager로 자동 결과 병합
- shared_context를 통한 명시적 데이터 전달

✅ **Planning Agent 통합**
- LLM 기반 의도 분석
- 동적 실행 계획 수립
- 병렬/순차 전략 자동 선택

✅ **동적 Agent 관리**
- AgentRegistry (Singleton)
- 능력 기반 Agent 검색
- 런타임 Agent 제어

✅ **State Pollution 방지**
- 팀별 독립 State
- 최소 공유 (SharedState)
- StateManager 책임 분리

✅ **확장 가능한 구조**
- 새 Agent/팀 추가 용이
- 모듈화된 설계
- 명확한 책임 분리

### 11.2 발견된 주요 문제점

#### 🔴 **문제점 1: 실제 구현과 문서의 불일치**

**현상:**
- 보고서에 `guides/` 디렉토리가 있다고 기술되어 있으나 **실제로 존재하지 않음**
- `core/config.py`가 "고도화를 위한 참고자료"로 잘못 분류됨

**영향:**
- 신규 개발자가 코드베이스를 이해하는데 혼란
- 문서의 신뢰도 저하

**해결:**
- ✅ 본 보고서에서 폴더 구조 수정 완료
- 실제 구현과 100% 일치하도록 업데이트

---

#### 🟡 **문제점 2: models/ 디렉토리가 비어있음**

**현상:**
- `core/config.py`에서 `LEGAL_PATHS["embedding_model"]`이 `models/KURE_v1`을 참조
- 하지만 `models/` 디렉토리가 **비어있음**

**영향:**
- 법률 검색 임베딩 기능 사용 불가
- 하이브리드 검색의 벡터 검색 기능 미작동 가능성

**현재 상황:**
```python
# config.py:48
"embedding_model": BASE_DIR / "app" / "service_agent" / "models" / "KURE_v1"
```

**해결 방안:**
1. **단기:** 임베딩 모델 파일 누락 경고 로그 추가
2. **중기:** KURE_v1 모델 다운로드 및 배치
3. **장기:** 모델 자동 다운로드 스크립트 작성

---

#### 🟡 **문제점 3: Agent 구현체 누락**

**현상:**
- `AgentRegistry`에 등록되어야 할 실제 Agent 클래스들(`SearchAgent`, `AnalysisAgent`, `DocumentAgent`, `ReviewAgent`)의 구현체가 `service_agent/` 디렉토리에 **없음**
- `teams/` 내의 Supervisor들은 `AgentAdapter.execute_agent_dynamic()`을 호출하지만 실제 Agent는 다른 경로에 존재할 가능성

**영향:**
- Agent 실행 시 "Agent not found" 에러 발생 가능
- 팀 Supervisor가 제대로 작동하지 않을 수 있음

**예상 위치:**
- `backend/app/service/agents/` 경로에 실제 구현체가 있을 가능성
- Import 경로 불일치 문제

**해결 방안:**
1. 실제 Agent 구현체 위치 확인
2. `AgentAdapter.register_existing_agents()` 메서드에서 올바른 경로로 import
3. 또는 Agent 구현체를 `service_agent/agents/`로 이동

---

#### 🟡 **문제점 4: 중복된 PlanningAgent**

**현상:**
- `planning/planning_agent.py` 파일 존재
- 보고서에는 `guides/agents/planning_agent.py`도 언급
- 하나는 실제 구현, 하나는 참고자료일 가능성

**영향:**
- 어떤 것이 실제로 사용되는지 불명확
- 코드 중복 가능성

**해결 방안:**
- `planning/planning_agent.py`가 실제 사용되는 버전임을 확인
- 중복 파일이 있다면 제거 또는 명확히 구분

---

#### 🟡 **문제점 5: Import 경로 혼란**

**현상:**
```python
# search_team.py:19
from app.service.core.separated_states import SearchTeamState
# → app.service.core (X)

# planning_agent.py:19
from app.service_agent.core.agent_registry import AgentRegistry
# → app.service_agent.core (O)
```

**영향:**
- Import 에러 발생 가능성
- `app.service` vs `app.service_agent` 혼용

**해결 방안:**
1. 모든 파일에서 일관되게 `app.service_agent`로 통일
2. `search_team.py:19` 수정 필요

---

#### 🔴 **문제점 6: LangGraph 0.6 최신 기능 미활용**

**현상:**
- Context API 미사용
- Checkpointer 설정되어 있지 않음 (config에는 enable_checkpointing=True 있으나 실제 미구현)
- Interrupt/Command 없음

**영향:**
- 장시간 실행 작업 중단 시 처음부터 재시작
- 사용자 확인 단계 없음
- 실행 이력 추적 불가

**해결 방안:**
- Part 10의 고도화 계획 참조
- LangGraph 0.6 기능 단계적 도입

---

#### 🟠 **문제점 7: 에러 처리 및 로깅 부족**

**현상:**
- 팀 실패 시 로그만 남기고 계속 진행
- 부분 실패 시 사용자에게 어떤 팀이 실패했는지 명확히 전달 안됨
- 메트릭 수집 없음

**영향:**
- 디버깅 어려움
- 프로덕션 환경에서 문제 추적 불가

**해결 방안:**
1. 구조화된 로깅 도입 (structlog)
2. 메트릭 수집 (Prometheus + Grafana)
3. 분산 추적 (OpenTelemetry)

---

### 11.3 개선 필요 사항 (우선순위별)

#### 🔴 **P0 (긴급) - 즉시 수정 필요**

1. **Import 경로 통일**
   - `search_team.py` import 수정
   - 모든 파일에서 `app.service_agent` 사용

2. **Agent 구현체 위치 확인 및 수정**
   - 실제 Agent 파일 찾기
   - `AgentAdapter` import 경로 수정

3. **임베딩 모델 누락 처리**
   - 모델 없을 때 fallback 로직 추가
   - 에러 대신 경고 로그

---

#### 🟡 **P1 (높음) - 1-2주 내 개선**

1. **Checkpointer 실제 구현**
   ```python
   from langgraph.checkpoint.sqlite import SqliteSaver

   checkpointer = SqliteSaver(Config.get_checkpoint_path("supervisor", session_id))
   app = workflow.compile(checkpointer=checkpointer)
   ```

2. **에러 처리 강화**
   - 팀별 재시도 로직
   - 사용자 친화적 에러 메시지
   - 부분 실패 시 결과 포맷

3. **테스트 코드 정리**
   - 테스트 파일들을 `tests/` 디렉토리로 이동
   - 중복 제거

---

#### 🟢 **P2 (중간) - 1개월 내 개선**

1. **LangGraph 0.6 Context API**
   ```python
   @dataclass
   class ServiceContext(Context):
       llm_model: str
       user_id: str
       session_id: str
   ```

2. **모니터링 및 관찰성**
   - 구조화된 로깅
   - 메트릭 수집
   - 대시보드 구축

3. **DAG 실행 엔진**
   - 복잡한 의존성 처리
   - 동적 병렬화

---

#### 🔵 **P3 (낮음) - 장기 개선**

1. **Streaming 지원**
   - 실시간 실행 상태 스트리밍
   - 프론트엔드 연동

2. **적응형 Planning**
   - 실행 중 계획 조정
   - 실패 시 대체 전략

3. **캐싱 전략**
   - 검색 결과 캐싱
   - 분석 결과 재사용

### 11.3 단계별 고도화 로드맵

**Phase 1 (1개월): LangGraph 0.6 통합**
- Context API 적용
- Checkpointer 구현
- Interrupt/Command 추가
- 상태 복구 기능

**Phase 2 (1개월): Planning 고도화**
- DAG 실행 구현
- 적응형 실행 전략
- LLM 기반 동적 Agent 매핑
- 의존성 자동 해결

**Phase 3 (1개월): 관찰성 및 성능**
- Streaming 구현
- 메트릭 수집
- 분산 추적
- 캐싱 전략

**Phase 4 (1개월): 프로덕션 준비**
- 통합 테스트
- 성능 최적화
- 문서 완성
- 배포 자동화

### 11.4 결론

service_agent는 **잘 설계된 Team-based Multi-Agent 아키텍처**를 갖추고 있습니다. TeamBasedSupervisor를 통한 팀 간 소통, Planning Agent의 의도 분석, AgentRegistry의 동적 Agent 관리, 그리고 SeparatedStates를 통한 State 격리까지 핵심 설계가 완료되었습니다.

**그러나 다음과 같은 개선이 필요합니다:**

1. **즉시 수정 (P0)**
   - Import 경로 통일 (`app.service` → `app.service_agent`)
   - Agent 구현체 위치 확인 및 연결
   - 임베딩 모델 누락 처리

2. **단기 개선 (P1)**
   - Checkpointer 실제 구현
   - 에러 처리 강화
   - 테스트 코드 정리

3. **중장기 개선 (P2-P3)**
   - LangGraph 0.6 최신 기능 통합
   - 모니터링 및 관찰성 구축
   - DAG 실행, Streaming, 캐싱 등 고급 기능

이러한 개선을 단계적으로 수행하여 **Production-Ready Enterprise Multi-Agent System**으로 발전시킬 수 있습니다.

---

## 📊 Part 12: 시스템 흐름도 (Mermaid)

### 12.1 전체 아키텍처 흐름도

```mermaid
graph TB
    User[사용자 쿼리] --> Supervisor[TeamBasedSupervisor]

    Supervisor --> Init[1. initialize_node<br/>세션 초기화]
    Init --> Planning[2. planning_node<br/>PlanningAgent]

    Planning --> IntentAnalysis{의도 분석<br/>LLM/패턴}
    IntentAnalysis --> ExecPlan[실행 계획 생성<br/>Agent 선택<br/>전략 결정]

    ExecPlan --> Execute[3. execute_teams_node]

    Execute --> Strategy{실행 전략}
    Strategy -->|Sequential| SeqExec[순차 실행]
    Strategy -->|Parallel| ParExec[병렬 실행]

    SeqExec --> SearchTeam[SearchTeam]
    SeqExec --> AnalysisTeam[AnalysisTeam]
    SeqExec --> DocumentTeam[DocumentTeam]

    ParExec --> SearchTeam
    ParExec --> AnalysisTeam
    ParExec --> DocumentTeam

    SearchTeam --> SearchResult[검색 결과]
    AnalysisTeam --> AnalysisResult[분석 결과]
    DocumentTeam --> DocumentResult[문서 결과]

    SearchResult --> Merge[StateManager<br/>결과 병합]
    AnalysisResult --> Merge
    DocumentResult --> Merge

    Merge --> Aggregate[4. aggregate_results_node<br/>통합 결과 생성]
    Aggregate --> Response[5. generate_response_node<br/>사용자 응답]

    Response --> User

    style Supervisor fill:#e1f5ff
    style Planning fill:#fff4e1
    style SearchTeam fill:#e8f5e9
    style AnalysisTeam fill:#fce4ec
    style DocumentTeam fill:#f3e5f5
    style Merge fill:#fff9c4
```

### 12.2 SearchTeam 내부 흐름도

```mermaid
graph LR
    Start([START]) --> Prepare[prepare_search_node<br/>키워드 추출<br/>검색 범위 설정]

    Prepare --> Route[route_search_node<br/>병렬/순차 결정]

    Route --> Decision{검색 범위<br/>확인}
    Decision -->|있음| Search[execute_search_node]
    Decision -->|없음| Finalize

    Search --> Legal[법률 검색<br/>LegalSearchTool<br/>ChromaDB+SQLite]
    Search --> RealEstate[부동산 검색<br/>MarketDataTool]
    Search --> Loan[대출 검색<br/>LoanDataTool]

    Legal --> Aggregate[aggregate_results_node<br/>결과 통합]
    RealEstate --> Aggregate
    Loan --> Aggregate

    Aggregate --> Finalize[finalize_node<br/>상태 정리]
    Finalize --> End([END])

    style Prepare fill:#e8f5e9
    style Search fill:#c8e6c9
    style Legal fill:#a5d6a7
    style RealEstate fill:#81c784
    style Loan fill:#66bb6a
    style Aggregate fill:#fff9c4
```

### 12.3 데이터 흐름도

```mermaid
sequenceDiagram
    participant User as 사용자
    participant Sup as TeamBasedSupervisor
    participant Plan as PlanningAgent
    participant Search as SearchTeam
    participant Analysis as AnalysisTeam
    participant Document as DocumentTeam
    participant State as StateManager

    User->>Sup: 쿼리 요청
    Sup->>Sup: initialize_node()
    Sup->>Plan: analyze_intent(query)
    Plan-->>Sup: IntentResult

    Sup->>Plan: create_execution_plan(intent)
    Plan-->>Sup: ExecutionPlan

    Sup->>Sup: execute_teams_node()

    Note over Sup,Search: 순차 실행 시작

    Sup->>Search: execute(shared_state)
    Search->>Search: 법률/부동산/대출 검색
    Search-->>Sup: SearchTeamState

    Sup->>State: merge_team_results("search", result)
    State-->>Sup: shared_context 업데이트

    Sup->>Analysis: execute(shared_state + search_results)
    Analysis->>Analysis: 데이터 분석
    Analysis-->>Sup: AnalysisTeamState

    Sup->>State: merge_team_results("analysis", result)
    State-->>Sup: shared_context 업데이트

    Sup->>Document: execute(shared_state + analysis_report)
    Document->>Document: 문서 생성 + 검토
    Document-->>Sup: DocumentTeamState

    Sup->>State: merge_team_results("document", result)

    Sup->>Sup: aggregate_results_node()
    Sup->>Sup: generate_response_node()
    Sup-->>User: 최종 응답
```

### 12.4 Agent Registry 패턴

```mermaid
classDiagram
    class AgentRegistry {
        -_instance: AgentRegistry
        -_agents: Dict~str, AgentMetadata~
        -_teams: Dict~str, List~str~~
        +register(name, agent_class, team, capabilities)
        +get_agent(name) AgentMetadata
        +create_agent(name, kwargs) Agent
        +list_agents(team, enabled_only) List~str~
        +find_agents_by_capability() List~str~
    }

    class AgentMetadata {
        +agent_class: Type
        +team: str
        +capabilities: AgentCapabilities
        +priority: int
        +enabled: bool
    }

    class AgentCapabilities {
        +name: str
        +description: str
        +input_types: List~str~
        +output_types: List~str~
        +required_tools: List~str~
        +team: str
    }

    class AgentAdapter {
        +register_existing_agents()
        +execute_agent_dynamic(name, input)
        +get_agents_for_intent(intent) List~str~
        +get_agent_dependencies(name) Dict
    }

    class SearchAgent {
        +execute()
    }

    class AnalysisAgent {
        +execute()
    }

    class DocumentAgent {
        +execute()
    }

    AgentRegistry "1" --> "*" AgentMetadata : manages
    AgentMetadata "1" --> "1" AgentCapabilities : has
    AgentAdapter ..> AgentRegistry : uses
    AgentAdapter ..> SearchAgent : creates
    AgentAdapter ..> AnalysisAgent : creates
    AgentAdapter ..> DocumentAgent : creates
```

### 12.5 State 분리 아키텍처

```mermaid
graph TB
    MainState[MainSupervisorState<br/>전체 상태 관리] --> SharedContext[shared_context<br/>팀 간 데이터 전달]

    MainState --> TeamResults[team_results<br/>팀별 실행 결과]

    SharedContext --> SearchState[SearchTeamState<br/>검색 팀 독립 상태]
    SharedContext --> AnalysisState[AnalysisTeamState<br/>분석 팀 독립 상태]
    SharedContext --> DocumentState[DocumentTeamState<br/>문서 팀 독립 상태]

    TeamResults --> SearchResult[search: {...}]
    TeamResults --> AnalysisResult[analysis: {...}]
    TeamResults --> DocumentResult[document: {...}]

    SearchState --> SearchData[legal_results<br/>real_estate_results<br/>loan_results<br/>aggregated_results]

    AnalysisState --> AnalysisData[metrics<br/>insights<br/>report<br/>recommendations]

    DocumentState --> DocumentData[document_content<br/>review_result<br/>final_document]

    style MainState fill:#e1f5ff
    style SharedContext fill:#fff4e1
    style SearchState fill:#e8f5e9
    style AnalysisState fill:#fce4ec
    style DocumentState fill:#f3e5f5
```

---

**문서 버전**: 3.0 (완전 개정판 - 실제 구조 반영)
**최종 수정일**: 2025-10-04
**작성자**: Claude Code Analysis
**다음 리뷰**: 2025-11-04
**상태**: ⚠️ NEEDS IMPROVEMENT (P0 이슈 해결 필요)
