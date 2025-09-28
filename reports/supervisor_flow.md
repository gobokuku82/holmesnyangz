● 🔍 사용자 질의 → 출력까지 전체 코드 연결점 분석

  📌 시작점: 사용자가 호출하는 함수

  # 사용자 코드 (예상)
  from supervisor import RealEstateSupervisor

  supervisor = RealEstateSupervisor()
  result = await supervisor.process_query(
      query="강남역 근처 30평대 아파트 매매 시세",
      user_id="user123",
      session_id="session456"
  )

  ---
  🎯 전체 실행 흐름 (코드 연결점)

  ┌─────────────────────────────────────────────────────────────┐
  │ 1️⃣ RealEstateSupervisor.__init__()                         │
  │    📍 supervisor/supervisor.py:39-48                       │
  │    ↓ 상속: BaseAgent.__init__()                             │
  │    📍 core/base_agent.py:31-53                             │
  │    └─ self._build_graph() 호출                              │
  │       📍 supervisor/supervisor.py:59-130                   │
  └─────────────────────────────────────────────────────────────┘
            ↓
  ┌─────────────────────────────────────────────────────────────┐
  │ 2️⃣ supervisor.process_query()                               │
  │    📍 supervisor/supervisor.py:173-206                       │
  │    ↓                                                         │
  │    input_data = {"query": ..., "user_id": ..., ...}        │
  │    ↓                                                         │
  │    result = await self.execute(input_data, config)          │
  └─────────────────────────────────────────────────────────────┘
            ↓
  ┌─────────────────────────────────────────────────────────────┐
  │ 3️⃣ BaseAgent.execute()                                      │
  │    📍 core/base_agent.py:259-260 (메서드 시작)              │
  │                                                              │
  │    ┌──────────────────────────────────────────────┐        │
  │    │ 3-A. 입력 검증                                 │        │
  │    │ 📍 base_agent.py:276                           │        │
  │    │ if not await self._validate_input(input_data) │        │
  │    │    ↓ 호출                                      │        │
  │    │ 📍 supervisor.py:132-155                       │        │
  │    │    (_validate_input 오버라이드)               │        │
  │    └──────────────────────────────────────────────┘        │
  │          ↓                                                   │
  │    ┌──────────────────────────────────────────────┐        │
  │    │ 3-B. 초기 State 생성                          │        │
  │    │ 📍 base_agent.py:284                           │        │
  │    │ initial_state = self._create_initial_state()  │        │
  │    │    ↓ 호출                                      │        │
  │    │ 📍 supervisor.py:157-171                       │        │
  │    │    (_create_initial_state 오버라이드)         │        │
  │    │    ↓ 내부 호출                                 │        │
  │    │ 📍 core/states.py:290-325                      │        │
  │    │    (create_supervisor_initial_state)          │        │
  │    └──────────────────────────────────────────────┘        │
  │          ↓                                                   │
  │    ┌──────────────────────────────────────────────┐        │
  │    │ 3-C. Context 생성                              │        │
  │    │ 📍 base_agent.py:287                           │        │
  │    │ context = self._create_context(input_data)    │        │
  │    │    ↓ 호출 (BaseAgent 기본 구현)               │        │
  │    │ 📍 base_agent.py:105-125                       │        │
  │    │    ↓ 내부 호출                                 │        │
  │    │ 📍 core/context.py:74-111                      │        │
  │    │    (create_agent_context)                     │        │
  │    └──────────────────────────────────────────────┘        │
  │          ↓                                                   │
  │    ┌──────────────────────────────────────────────┐        │
  │    │ 3-D. Config 준비                               │        │
  │    │ 📍 base_agent.py:290-298                       │        │
  │    │ config["configurable"]["thread_id"] = ...     │        │
  │    └──────────────────────────────────────────────┘        │
  │          ↓                                                   │
  │    ┌──────────────────────────────────────────────┐        │
  │    │ 3-E. Workflow 컴파일 & 실행                    │        │
  │    │ 📍 base_agent.py:310-324                       │        │
  │    │ app = self.workflow.compile(checkpointer)     │        │
  │    │ result = await app.ainvoke(                   │        │
  │    │     initial_state,                            │        │
  │    │     config=config,                            │        │
  │    │     context=context                           │        │
  │    │ )                                             │        │
  │    └──────────────────────────────────────────────┘        │
  └─────────────────────────────────────────────────────────────┘
            ↓
  ┌─────────────────────────────────────────────────────────────┐
  │ 4️⃣ LangGraph StateGraph 실행                                │
  │    (app.ainvoke 내부 - LangGraph 프레임워크)                │
  │                                                              │
  │    ┌──────────────────────────────────────────────┐        │
  │    │ 4-A. 시작점: analyze_intent                    │        │
  │    │ 📍 supervisor.py:128 (set_entry_point)         │        │
  │    │ 📍 supervisor.py:84 (add_node)                 │        │
  │    │    ↓ 노드 함수 실행                            │        │
  │    │ 📍 supervisor/intent_analyzer.py:70-115        │        │
  │    │    async def analyze_intent_node(state, runtime)│       │
  │    │    ↓                                           │        │
  │    │    ctx = await runtime.context()  ← Context 접근│       │
  │    │    query = state["query"]         ← State 읽기 │       │
  │    │    ↓ LLM 호출                                  │        │
  │    │ 📍 intent_analyzer.py:17-67                    │        │
  │    │    await call_llm_for_intent(query, api_key)  │        │
  │    │    ↓ 프롬프트 가져오기                         │        │
  │    │ 📍 supervisor/prompts.py:11-42                 │        │
  │    │    INTENT_ANALYSIS_PROMPT                     │        │
  │    │    ↓                                           │        │
  │    │    return {"intent": {...}, "execution_step": "planning"}│
  │    └──────────────────────────────────────────────┘        │
  │          ↓ (State 업데이트 후 다음 노드로)                  │
  │    ┌──────────────────────────────────────────────┐        │
  │    │ 4-B. 다음: build_plan                          │        │
  │    │ 📍 supervisor.py:85 (add_node)                 │        │
  │    │ 📍 supervisor.py:90 (add_edge)                 │        │
  │    │    ↓ 노드 함수 실행                            │        │
  │    │ 📍 supervisor/plan_builder.py:170-193          │        │
  │    │    async def build_plan_node(state, runtime)  │        │
  │    │    ↓                                           │        │
  │    │    intent = state["intent"]       ← 이전 노드 결과│      │
  │    │    ↓ 규칙 기반 계획 생성                       │        │
  │    │ 📍 plan_builder.py:17-117                      │        │
  │    │    build_plan_rule_based(intent)              │        │
  │    │    ↓                                           │        │
  │    │    return {"execution_plan": {...}, ...}      │        │
  │    └──────────────────────────────────────────────┘        │
  │          ↓                                                   │
  │    ┌──────────────────────────────────────────────┐        │
  │    │ 4-C. 다음: execute_agents                      │        │
  │    │ 📍 supervisor.py:86 (add_node)                 │        │
  │    │ 📍 supervisor.py:91 (add_edge)                 │        │
  │    │    ↓ 노드 함수 실행                            │        │
  │    │ 📍 supervisor/execution_coordinator.py:145-182 │        │
  │    │    async def execute_agents_node(state, runtime)│       │
  │    │    ↓                                           │        │
  │    │    plan = state["execution_plan"]             │        │
  │    │    ↓ 전략별 실행                               │        │
  │    │ 📍 execution_coordinator.py:87-112 (sequential)│        │
  │    │    await execute_sequential(agents, ctx)      │        │
  │    │    ↓ Agent별 실행                              │        │
  │    │ 📍 execution_coordinator.py:54-79              │        │
  │    │    await execute_agent(agent_config, ctx)     │        │
  │    │    ↓ Mock Agent 사용 (현재)                    │        │
  │    │ 📍 execution_coordinator.py:17-51              │        │
  │    │    get_agent(agent_name)                      │        │
  │    │    ↓                                           │        │
  │    │    return {"agent_results": {...}, ...}       │        │
  │    └──────────────────────────────────────────────┘        │
  │          ↓                                                   │
  │    ┌──────────────────────────────────────────────┐        │
  │    │ 4-D. 다음: evaluate_results                    │        │
  │    │ 📍 supervisor.py:87 (add_node)                 │        │
  │    │ 📍 supervisor.py:92 (add_edge)                 │        │
  │    │    ↓ 노드 함수 실행                            │        │
  │    │ 📍 supervisor/result_evaluator.py:148-197      │        │
  │    │    async def evaluate_results_node(state, runtime)│     │
  │    │    ↓                                           │        │
  │    │    agent_results = state["agent_results"]     │        │
  │    │    ↓ 품질 평가                                 │        │
  │    │ 📍 result_evaluator.py:17-58 (rule_based)     │        │
  │    │    evaluate_quality_rule_based(agent_results) │        │
  │    │    ↓ 응답 포맷팅                               │        │
  │    │ 📍 result_evaluator.py:86-115 (simple)         │        │
  │    │    format_response_simple(query, agent_results)│       │
  │    │    ↓                                           │        │
  │    │    return {"evaluation": {...}, "final_output": {...}}│ │
  │    └──────────────────────────────────────────────┘        │
  │          ↓                                                   │
  │    ┌──────────────────────────────────────────────┐        │
  │    │ 4-E. 조건부 분기: should_retry                 │        │
  │    │ 📍 supervisor.py:95-116 (함수 정의)            │        │
  │    │ 📍 supervisor.py:118-125 (add_conditional_edges)│       │
  │    │    ↓                                           │        │
  │    │    if needs_retry and retry_count < 2:        │        │
  │    │        return "retry"  → execute_agents 재실행 │        │
  │    │    else:                                       │        │
  │    │        return "end"    → END                   │        │
  │    └──────────────────────────────────────────────┘        │
  │          ↓ (재시도 없으면)                                  │
  │    📍 supervisor.py:123 (END)                               │
  └─────────────────────────────────────────────────────────────┘
            ↓
  ┌─────────────────────────────────────────────────────────────┐
  │ 5️⃣ BaseAgent.execute() 결과 반환                            │
  │    📍 base_agent.py:327-339                                  │
  │    ↓                                                         │
  │    return {                                                  │
  │        "status": "success",                                  │
  │        "data": result,  ← 최종 State (final_output 포함)     │
  │        "agent": "real_estate_supervisor",                    │
  │        "context": {...}                                      │
  │    }                                                         │
  └─────────────────────────────────────────────────────────────┘
            ↓
  ┌─────────────────────────────────────────────────────────────┐
  │ 6️⃣ process_query() 최종 응답 추출                           │
  │    📍 supervisor.py:198-206                                  │
  │    ↓                                                         │
  │    if result["status"] == "success":                         │
  │        return result["data"]["final_output"]                 │
  │    else:                                                     │
  │        return {"error": ..., "status": "failed"}             │
  └─────────────────────────────────────────────────────────────┘
            ↓
  ┌─────────────────────────────────────────────────────────────┐
  │ 7️⃣ 사용자에게 최종 응답                                      │
  │    {                                                         │
  │        "answer": "강남구 아파트 매매 시세는...",              │
  │        "listings": [...],                                    │
  │        "insights": [...],                                    │
  │        "metadata": {...}                                     │
  │    }                                                         │
  └─────────────────────────────────────────────────────────────┘

  ---
  🔑 핵심 상속 & 호출 관계

  1. 클래스 상속 구조

  BaseAgent (추상 클래스)
  📍 core/base_agent.py:24-325
      ├─ __init__()
      ├─ execute()              ← 핵심 실행 메서드
      ├─ _validate_input()      ← 추상 메서드
      ├─ _build_graph()         ← 추상 메서드
      ├─ _get_state_schema()    ← 추상 메서드
      └─ _create_initial_state()

           ↓ 상속

  RealEstateSupervisor (구체 클래스)
  📍 supervisor/supervisor.py:30-207
      ├─ __init__()             → super().__init__() 호출
      ├─ _validate_input()      → 오버라이드 (query 검증)
      ├─ _build_graph()         → 오버라이드 (StateGraph 구성)
      ├─ _get_state_schema()    → 오버라이드 (SupervisorState 반환)
      ├─ _create_initial_state()→ 오버라이드 (create_supervisor_initial_state 호출)     
      └─ process_query()        → 편의 메서드 (execute 래핑)

  2. State 관리 흐름

  SupervisorState (TypedDict)
  📍 core/states.py:145-199
      ├─ query: str
      ├─ intent: Optional[Dict]
      ├─ execution_plan: Optional[Dict]
      ├─ agent_results: Annotated[Dict, merge_dicts]
      ├─ evaluation: Optional[Dict]
      └─ final_output: Optional[Dict]

           ↓ 초기화

  create_supervisor_initial_state()
  📍 core/states.py:290-325
      └─ 모든 필드를 기본값으로 초기화

           ↓ 각 노드에서 업데이트

  analyze_intent_node       → state["intent"] 업데이트
  build_plan_node           → state["execution_plan"] 업데이트
  execute_agents_node       → state["agent_results"] 업데이트
  evaluate_results_node     → state["evaluation"], state["final_output"] 업데이트       

  3. Context 관리 흐름

  AgentContext (TypedDict)
  📍 core/context.py:14-37
      ├─ user_id: str (필수)
      ├─ session_id: str (필수)
      ├─ request_id: Optional[str]
      ├─ api_keys: Optional[Dict]
      └─ debug_mode: Optional[bool]

           ↓ 생성

  create_agent_context(user_id, session_id, **kwargs)
  📍 core/context.py:74-111
      └─ Context 딕셔너리 생성

           ↓ 전달

  BaseAgent._create_context()
  📍 core/base_agent.py:105-125
      └─ input_data에서 Context 추출

           ↓ LangGraph에 전달

  app.ainvoke(state, config, context=context)
  📍 base_agent.py:319-323

           ↓ 노드에서 접근

  async def node(state, runtime):
      ctx = await runtime.context()  ← READ-ONLY로 접근
      api_key = ctx.get("api_keys", {}).get("openai_api_key")

  ---
  💡 가장 먼저 실행되는 것들

  1️⃣ 최초 진입점

  # 사용자 코드
  supervisor = RealEstateSupervisor()
  호출 순서:
  1. RealEstateSupervisor.__init__() (supervisor.py:39)
  2. super().__init__() → BaseAgent.__init__() (base_agent.py:31)
  3. self._build_graph() → RealEstateSupervisor._build_graph() (supervisor.py:59)       

  2️⃣ 최초 상속받는 클래스

  class RealEstateSupervisor(BaseAgent):
      ...
  - 부모 클래스: BaseAgent (core/base_agent.py:24)
  - 상속 받는 메서드:
    - execute() - 핵심 실행 로직
    - _create_context() - Context 생성
    - _wrap_node_with_runtime() - Runtime 주입
    - get_state() - 상태 조회
    - update_state() - 상태 업데이트

  3️⃣ 최초 실행되는 메서드

  result = await supervisor.process_query("강남역 아파트")
  호출 순서:
  1. process_query() (supervisor.py:173)
  2. self.execute() → BaseAgent.execute() (base_agent.py:259)
  3. self._validate_input() → RealEstateSupervisor._validate_input()
  (supervisor.py:132)
  4. self._create_initial_state() → RealEstateSupervisor._create_initial_state()        
  (supervisor.py:157)
  5. self._create_context() → BaseAgent._create_context() (base_agent.py:105)
  6. app.ainvoke() → LangGraph 실행

  ---
  📊 State 업데이트 추적

  # 초기 State (base_agent.py:284)
  initial_state = {
      "status": "pending",
      "query": "강남역 아파트",
      "intent": None,
      ...
  }

  # → analyze_intent_node 실행 후 (intent_analyzer.py:100-106)
  state = {
      "status": "processing",
      "query": "강남역 아파트",
      "intent": {"intent_type": "search", ...},  ← 추가
      "execution_step": "planning",  ← 업데이트
      ...
  }

  # → build_plan_node 실행 후 (plan_builder.py:187-191)
  state = {
      ...
      "execution_plan": {"strategy": "sequential", ...},  ← 추가
      "execution_step": "executing_agents",  ← 업데이트
  }

  # → execute_agents_node 실행 후 (execution_coordinator.py:175-179)
  state = {
      ...
      "agent_results": {  ← merge_dicts로 병합
          "property_search": {...},
          "market_analysis": {...}
      },
      "execution_step": "evaluating",
  }

  # → evaluate_results_node 실행 후 (result_evaluator.py:189-195)
  state = {
      ...
      "evaluation": {...},  ← 추가
      "final_output": {...},  ← 추가
      "status": "completed",
      "execution_step": "finished"
  }

  ---
  이것이 사용자 질의 → 출력까지의 완전한 코드 연결점입니다!