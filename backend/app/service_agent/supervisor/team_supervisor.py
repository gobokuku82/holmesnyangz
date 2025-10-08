"""
Team-based Supervisor - 팀 기반 서브그래프를 조정하는 메인 Supervisor
SearchTeam, DocumentTeam, AnalysisTeam을 오케스트레이션
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
from langgraph.graph import StateGraph, START, END

import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.foundation.separated_states import (
    MainSupervisorState,
    SharedState,
    StateManager,
    PlanningState
)
from app.service_agent.foundation.context import LLMContext, create_default_llm_context
from app.service_agent.cognitive_agents.planning_agent import PlanningAgent, IntentType, ExecutionStrategy
from app.service_agent.execution_agents import SearchExecutor, DocumentExecutor, AnalysisExecutor
from app.service_agent.foundation.agent_registry import AgentRegistry
from app.service_agent.foundation.agent_adapter import initialize_agent_system

logger = logging.getLogger(__name__)


class TeamBasedSupervisor:
    """
    팀 기반 Supervisor
    각 팀을 독립적으로 관리하고 조정
    """

    def __init__(self, llm_context: LLMContext = None):
        """
        초기화

        Args:
            llm_context: LLM 컨텍스트
        """
        self.llm_context = llm_context or create_default_llm_context()

        # Agent 시스템 초기화
        initialize_agent_system(auto_register=True)

        # Checkpointer placeholder - will be initialized later
        self.checkpointer = None

        # Planning Agent
        self.planning_agent = PlanningAgent(llm_context=llm_context)

        # 팀 초기화
        self.teams = {
            "search": SearchExecutor(llm_context=llm_context),
            "document": DocumentExecutor(llm_context=llm_context),
            "analysis": AnalysisExecutor(llm_context=llm_context)
        }

        # 워크플로우 구성
        self.app = None
        self._build_graph()

        logger.info("TeamBasedSupervisor initialized with 3 teams")

    def _get_llm_client(self):
        """LLM 클라이언트 가져오기"""
        try:
            from openai import OpenAI
            if self.llm_context.api_key:
                return OpenAI(api_key=self.llm_context.api_key)
        except:
            pass
        return None

    def _build_graph(self):
        """워크플로우 그래프 구성"""
        workflow = StateGraph(MainSupervisorState)

        # 노드 추가
        workflow.add_node("initialize", self.initialize_node)
        workflow.add_node("planning", self.planning_node)
        workflow.add_node("execute_teams", self.execute_teams_node)
        workflow.add_node("aggregate", self.aggregate_results_node)
        workflow.add_node("generate_response", self.generate_response_node)

        # 엣지 구성
        workflow.add_edge(START, "initialize")
        workflow.add_edge("initialize", "planning")

        # 계획 후 라우팅
        workflow.add_conditional_edges(
            "planning",
            self._route_after_planning,
            {
                "execute": "execute_teams",
                "respond": "generate_response"
            }
        )

        workflow.add_edge("execute_teams", "aggregate")
        workflow.add_edge("aggregate", "generate_response")
        workflow.add_edge("generate_response", END)

        self.app = workflow.compile()
        logger.info("Team-based workflow graph built successfully")

    def _route_after_planning(self, state: MainSupervisorState) -> str:
        """계획 후 라우팅"""
        planning_state = state.get("planning_state")
        if planning_state and planning_state.get("execution_steps"):
            logger.info(f"[TeamSupervisor] Routing to execute - {len(planning_state['execution_steps'])} steps found")
            return "execute"
        logger.info("[TeamSupervisor] No execution steps found, routing to respond")
        return "respond"

    async def initialize_node(self, state: MainSupervisorState) -> MainSupervisorState:
        """
        초기화 노드
        """
        logger.info("[TeamSupervisor] Initializing")

        state["start_time"] = datetime.now()
        state["status"] = "initialized"
        state["current_phase"] = "initialization"
        state["active_teams"] = []
        state["completed_teams"] = []
        state["failed_teams"] = []
        state["team_results"] = {}
        state["error_log"] = []

        return state

    async def planning_node(self, state: MainSupervisorState) -> MainSupervisorState:
        """
        계획 수립 노드
        PlanningAgent를 사용하여 의도 분석 및 실행 계획 생성
        """
        logger.info("[TeamSupervisor] Planning phase")

        state["current_phase"] = "planning"

        # 의도 분석
        query = state.get("query", "")
        intent_result = await self.planning_agent.analyze_intent(query)

        # 실행 계획 생성
        execution_plan = await self.planning_agent.create_execution_plan(intent_result)

        # Planning State 생성
        planning_state = PlanningState(
            raw_query=query,
            analyzed_intent={
                "intent_type": intent_result.intent_type.value,
                "confidence": intent_result.confidence,
                "keywords": intent_result.keywords,
                "entities": intent_result.entities
            },
            intent_confidence=intent_result.confidence,
            available_agents=AgentRegistry.list_agents(enabled_only=True),
            available_teams=list(self.teams.keys()),
            execution_steps=[
                {
                    "step_id": f"step_{i}",
                    "agent_name": step.agent_name,
                    "team": self._get_team_for_agent(step.agent_name),
                    "priority": step.priority,
                    "dependencies": step.dependencies,
                    "estimated_time": step.timeout,
                    "required": not step.optional
                }
                for i, step in enumerate(execution_plan.steps)
            ],
            execution_strategy=execution_plan.strategy.value,
            parallel_groups=execution_plan.parallel_groups,
            plan_validated=True,
            validation_errors=[],
            estimated_total_time=execution_plan.estimated_time
        )

        state["planning_state"] = planning_state
        state["execution_plan"] = {
            "intent": intent_result.intent_type.value,
            "strategy": execution_plan.strategy.value,
            "steps": planning_state["execution_steps"]
        }

        # 활성화할 팀 결정
        active_teams = set()
        for step in planning_state["execution_steps"]:
            team = step.get("team")
            if team:
                active_teams.add(team)

        state["active_teams"] = list(active_teams)

        logger.info(f"[TeamSupervisor] Plan created: {len(planning_state['execution_steps'])} steps, {len(active_teams)} teams")

        # 디버그: execution_steps 내용 로깅
        for step in planning_state["execution_steps"]:
            logger.debug(f"  Step: agent={step.get('agent_name')}, team={step.get('team')}, priority={step.get('priority')}")

        if not planning_state["execution_steps"]:
            logger.warning("[TeamSupervisor] WARNING: No execution steps created in planning phase!")

        return state

    def _get_team_for_agent(self, agent_name: str) -> str:
        """Agent가 속한 팀 찾기"""
        # 팀 이름 매핑 (agent_selection.txt에서 사용하는 이름들)
        team_name_mapping = {
            "search_team": "search",
            "analysis_team": "analysis",
            "document_team": "document"
        }

        # 이미 팀 이름인 경우 바로 매핑
        if agent_name in team_name_mapping:
            return team_name_mapping[agent_name]

        # Agent 이름인 경우 기존 로직 사용
        from app.service_agent.foundation.agent_adapter import AgentAdapter
        dependencies = AgentAdapter.get_agent_dependencies(agent_name)
        return dependencies.get("team", "search")

    async def execute_teams_node(self, state: MainSupervisorState) -> MainSupervisorState:
        """
        팀 실행 노드
        계획에 따라 팀들을 실행
        """
        logger.info("[TeamSupervisor] Executing teams")

        state["current_phase"] = "executing"

        execution_strategy = state.get("execution_plan", {}).get("strategy", "sequential")
        active_teams = state.get("active_teams", [])

        # 공유 상태 생성
        shared_state = StateManager.create_shared_state(
            query=state["query"],
            session_id=state["session_id"]
        )

        # 팀별 실행
        if execution_strategy == "parallel" and len(active_teams) > 1:
            # 병렬 실행
            results = await self._execute_teams_parallel(active_teams, shared_state, state)
        else:
            # 순차 실행
            results = await self._execute_teams_sequential(active_teams, shared_state, state)

        # 결과 저장
        for team_name, team_result in results.items():
            state = StateManager.merge_team_results(state, team_name, team_result)

        return state

    async def _execute_teams_parallel(
        self,
        teams: List[str],
        shared_state: SharedState,
        main_state: MainSupervisorState
    ) -> Dict[str, Any]:
        """팀 병렬 실행"""
        logger.info(f"[TeamSupervisor] Executing {len(teams)} teams in parallel")

        tasks = []
        for team_name in teams:
            if team_name in self.teams:
                task = self._execute_single_team(team_name, shared_state, main_state)
                tasks.append((team_name, task))

        results = {}
        for team_name, task in tasks:
            try:
                result = await task
                results[team_name] = result
                logger.info(f"[TeamSupervisor] Team '{team_name}' completed")
            except Exception as e:
                logger.error(f"[TeamSupervisor] Team '{team_name}' failed: {e}")
                results[team_name] = {"status": "failed", "error": str(e)}

        return results

    async def _execute_teams_sequential(
        self,
        teams: List[str],
        shared_state: SharedState,
        main_state: MainSupervisorState
    ) -> Dict[str, Any]:
        """팀 순차 실행"""
        logger.info(f"[TeamSupervisor] Executing {len(teams)} teams sequentially")

        results = {}
        for team_name in teams:
            if team_name in self.teams:
                try:
                    result = await self._execute_single_team(team_name, shared_state, main_state)
                    results[team_name] = result
                    logger.info(f"[TeamSupervisor] Team '{team_name}' completed")

                    # 데이터 전달 (다음 팀을 위해)
                    if team_name == "search" and "analysis" in teams:
                        # SearchTeam 결과를 AnalysisTeam에 전달
                        main_state["team_results"][team_name] = self._extract_team_data(result, team_name)

                except Exception as e:
                    logger.error(f"[TeamSupervisor] Team '{team_name}' failed: {e}")
                    results[team_name] = {"status": "failed", "error": str(e)}

        return results

    async def _execute_single_team(
        self,
        team_name: str,
        shared_state: SharedState,
        main_state: MainSupervisorState
    ) -> Any:
        """단일 팀 실행"""
        team = self.teams[team_name]

        if team_name == "search":
            return await team.execute(shared_state)

        elif team_name == "document":
            # 문서 타입 추출
            doc_type = self._extract_document_type(main_state)
            return await team.execute(
                shared_state,
                document_type=doc_type
            )

        elif team_name == "analysis":
            # 이전 팀 결과 전달
            input_data = main_state.get("team_results", {})
            return await team.execute(
                shared_state,
                analysis_type="comprehensive",
                input_data=input_data
            )

        return {"status": "skipped"}

    def _extract_document_type(self, state: MainSupervisorState) -> str:
        """문서 타입 추출"""
        intent = state.get("planning_state", {}).get("analyzed_intent", {})
        intent_type = intent.get("intent_type", "")

        if "계약서" in intent_type or "작성" in intent_type:
            return "lease_contract"
        elif "매매" in intent_type:
            return "sales_contract"
        else:
            return "lease_contract"

    def _extract_team_data(self, team_state: Any, team_name: str) -> Dict:
        """팀 결과에서 데이터 추출"""
        if team_name == "search":
            return {
                "legal_search": team_state.get("legal_results", []),
                "real_estate_search": team_state.get("real_estate_results", []),
                "loan_search": team_state.get("loan_results", [])
            }
        elif team_name == "document":
            return {
                "document": team_state.get("final_document", ""),
                "review": team_state.get("review_result", {})
            }
        elif team_name == "analysis":
            return {
                "report": team_state.get("report", {}),
                "insights": team_state.get("insights", [])
            }
        return {}

    async def aggregate_results_node(self, state: MainSupervisorState) -> MainSupervisorState:
        """
        결과 집계 노드
        """
        logger.info("[TeamSupervisor] Aggregating results")

        state["current_phase"] = "aggregation"

        # 팀 결과 집계
        aggregated = {}
        for team_name, team_data in state.get("team_results", {}).items():
            if team_data:
                aggregated[team_name] = {
                    "status": "success",
                    "data": team_data
                }

        state["aggregated_results"] = aggregated

        # 실행 통계
        total_teams = len(state.get("active_teams", []))
        completed_teams = len(state.get("completed_teams", []))
        failed_teams = len(state.get("failed_teams", []))

        logger.info(f"[TeamSupervisor] Aggregation complete: {completed_teams}/{total_teams} succeeded")
        return state

    async def generate_response_node(self, state: MainSupervisorState) -> MainSupervisorState:
        """
        응답 생성 노드
        """
        logger.info("[TeamSupervisor] Generating response")

        state["current_phase"] = "response_generation"

        # LLM을 사용한 자연어 응답 생성
        if self.planning_agent.llm_service:
            response = await self._generate_llm_response(state)
        else:
            response = self._generate_simple_response(state)

        state["final_response"] = response
        state["status"] = "completed"

        # 실행 시간 계산
        if state.get("start_time"):
            state["end_time"] = datetime.now()
            state["total_execution_time"] = (state["end_time"] - state["start_time"]).total_seconds()

        logger.info("[TeamSupervisor] Response generation complete")
        return state

    def _safe_json_dumps(self, obj: Any) -> str:
        """Safely convert object to JSON string, handling datetime objects"""
        from datetime import datetime

        def json_serial(obj):
            """JSON serializer for objects not serializable by default json code"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        return json.dumps(obj, default=json_serial, ensure_ascii=False, indent=2)

    async def _generate_llm_response(self, state: MainSupervisorState) -> Dict:
        """LLM을 사용한 응답 생성"""
        query = state.get("query", "")
        aggregated = state.get("aggregated_results", {})
        intent_info = state.get("planning_state", {}).get("analyzed_intent", {})

        system_prompt = """당신은 부동산 전문 AI 상담사입니다.
사용자의 질문에 대해 여러 팀이 수집한 정보를 종합하여 명확하고 실용적인 답변을 제공하세요.

## 답변 작성 가이드:

### 1. 구조화된 답변
- **직접 답변**: 질문에 대한 핵심 답을 먼저 제시
- **근거 제시**: 수집된 데이터를 바탕으로 근거 설명
- **추가 정보**: 관련된 유용한 정보 제공
- **실행 가능한 조언**: 구체적인 다음 단계 제안

### 2. 정보 활용
- SearchTeam: 법률 조항, 시세 정보, 대출 상품
- AnalysisTeam: 데이터 분석, 인사이트, 추천사항
- DocumentTeam: 생성/검토된 문서

### 3. 답변 원칙
- 전문적이되 이해하기 쉬운 언어 사용
- 구체적인 숫자와 사실 인용
- 법률 조항 언급 시 정확한 출처 명시
- 불확실한 부분은 솔직하게 인정
- 추가 질문이나 확인이 필요한 경우 안내

### 4. 답변 형식 (JSON)
{
    "answer": "핵심 답변 (2-3문장, 질문에 직접 답하는 내용)",
    "details": {
        "legal_basis": "법적 근거 (해당되는 경우)",
        "data_analysis": "데이터 분석 결과 (해당되는 경우)",
        "considerations": "고려사항 (리스트)"
    },
    "recommendations": [
        "추천사항1: 구체적인 행동 지침",
        "추천사항2: 주의할 점"
    ],
    "sources": [
        "참고한 법률이나 데이터 출처"
    ],
    "confidence": 0.0~1.0,
    "additional_info": "추가로 도움이 될 만한 정보"
}

### 예시:

**질문**: "전세금 5% 인상이 가능한가요?"

**답변**:
{
    "answer": "네, 전세금 5% 인상은 일반적으로 가능합니다. 주택임대차보호법에 따르면 임대인은 약정한 차임이나 보증금이 임차주택에 관한 조세, 공과금, 그 밖의 부담의 증가나 경제 사정의 변동으로 인해 상당하지 않게 된 경우 증액을 청구할 수 있습니다.",
    "details": {
        "legal_basis": "주택임대차보호법 제7조(차임 등의 증감청구권)에 따라 임대인은 차임 증액을 청구할 수 있으나, 청구 당시 차임 또는 보증금의 20분의 1(5%)을 초과하지 못합니다.",
        "data_analysis": "현재 시장 상황과 계약 조건에 따라 다를 수 있습니다.",
        "considerations": [
            "5%는 법적 상한선입니다",
            "계약 갱신 시에만 적용됩니다",
            "임차인의 동의가 필요합니다"
        ]
    },
    "recommendations": [
        "계약서의 특약사항을 확인하세요",
        "주변 시세와 비교하여 적정성을 판단하세요",
        "증액에 동의하기 전에 협상을 시도해보세요"
    ],
    "sources": [
        "주택임대차보호법 제7조",
        "주택임대차보호법 제7조의2"
    ],
    "confidence": 0.95,
    "additional_info": "임대차계약이 종료되고 갱신되는 시점에만 증액 청구가 가능하며, 증액된 차임은 청구 당시를 기준으로 산정됩니다."
}"""

        user_prompt = f"""## 사용자 질문:
{query}

## 의도 분석:
- 유형: {intent_info.get('intent_type', '알 수 없음')}
- 신뢰도: {intent_info.get('confidence', 0):.0%}
- 핵심 키워드: {', '.join(intent_info.get('keywords', []))}

## 수집된 정보:
{self._safe_json_dumps(aggregated)[:4000]}

위 정보를 바탕으로 구조화된 답변을 JSON 형식으로 작성하세요."""

        try:
            # LLMService를 통한 응답 생성
            answer = await self.planning_agent.llm_service.complete_async(
                prompt_name="response_synthesis",
                variables={
                    "query": query,
                    "analysis_result": self._safe_json_dumps(aggregated)[:4000]
                },
                temperature=0.3,
                max_tokens=1000
            )

            return {
                "type": "answer",
                "answer": answer,
                "teams_used": list(aggregated.keys()),
                "data": aggregated
            }

        except Exception as e:
            logger.error(f"LLM response generation failed: {e}")
            return self._generate_simple_response(state)

    def _generate_simple_response(self, state: MainSupervisorState) -> Dict:
        """간단한 응답 생성"""
        aggregated = state.get("aggregated_results", {})

        summary_parts = []
        for team_name, team_data in aggregated.items():
            if team_data.get("status") == "success":
                summary_parts.append(f"{team_name} 팀 완료")

        return {
            "type": "summary",
            "summary": ", ".join(summary_parts) if summary_parts else "처리 완료",
            "teams_used": list(aggregated.keys()),
            "data": aggregated
        }

    async def process_query(
        self,
        query: str,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """
        쿼리 처리 메인 메서드

        Args:
            query: 사용자 쿼리
            session_id: 세션 ID

        Returns:
            처리 결과
        """
        logger.info(f"[TeamSupervisor] Processing query: {query[:100]}...")

        # 초기 상태 생성
        initial_state = MainSupervisorState(
            query=query,
            session_id=session_id,
            request_id=f"req_{datetime.now().timestamp()}",
            planning_state=None,
            execution_plan=None,
            search_team_state=None,
            document_team_state=None,
            analysis_team_state=None,
            current_phase="",
            active_teams=[],
            completed_teams=[],
            failed_teams=[],
            team_results={},
            aggregated_results={},
            final_response=None,
            start_time=datetime.now(),
            end_time=None,
            total_execution_time=None,
            error_log=[],
            status="initialized"
        )

        # 워크플로우 실행
        try:
            final_state = await self.app.ainvoke(initial_state)
            return final_state
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "final_response": {
                    "type": "error",
                    "message": "처리 중 오류가 발생했습니다.",
                    "error": str(e)
                }
            }


# 테스트 코드
if __name__ == "__main__":
    async def test_team_supervisor():
        # TeamBasedSupervisor 초기화
        supervisor = TeamBasedSupervisor()

        # 테스트 쿼리
        test_queries = [
            "전세금 5% 인상 가능한가요?",
            "강남구 아파트 시세와 투자 분석해주세요",
            "임대차계약서 작성하고 검토해주세요"
        ]

        for query in test_queries:
            print(f"\n{'='*80}")
            print(f"Query: {query}")
            print("-"*80)

            result = await supervisor.process_query(query, "test_team_supervisor")

            print(f"Status: {result.get('status')}")
            print(f"Phase: {result.get('current_phase')}")
            print(f"Teams used: {result.get('active_teams', [])}")

            if result.get("final_response"):
                response = result["final_response"]
                print(f"\nResponse type: {response.get('type')}")
                if response.get("answer"):
                    print(f"Answer: {response.get('answer', '')[:200]}...")
                elif response.get("summary"):
                    print(f"Summary: {response.get('summary')}")

            if result.get("total_execution_time"):
                print(f"\nExecution time: {result['total_execution_time']:.2f}s")

    import asyncio
    asyncio.run(test_team_supervisor())