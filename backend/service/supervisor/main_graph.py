# backend/service/supervisor.py
"""
Simplified Real Estate Supervisor
단순화된 부동산 챗봇 Supervisor - LangGraph 0.6.7
한 파일에 모든 워크플로우를 통합한 버전

Workflow: 의도 분석 → 계획 수립 → 실행 → 평가
"""

from typing import Dict, Any, Type, Optional, Literal
from langgraph.graph import StateGraph, START, END
import logging
import json
import asyncio
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from service.core.base_agent import BaseAgent
from service.core.states import SupervisorState, create_supervisor_initial_state
from service.core.context import AgentContext, create_agent_context
from service.utils.agent_registry import AgentRegistry

logger = logging.getLogger(__name__)


# ============ PROMPTS (프롬프트 템플릿) ============

INTENT_PROMPT = """
사용자 질문: {query}

위 질문을 분석하여 다음 JSON 형식으로 응답하세요:
{{
  "intent_type": "search/analysis/comparison/recommendation 중 하나",
  "entities": {{
    "region": "지역명",
    "property_type": "아파트/오피스텔/빌라",
    "deal_type": "매매/전세/월세",
    "price_range": {{"min": 0, "max": 0}},
    "size_range": {{"min": 0, "max": 0}}
  }}
}}
"""

PLAN_PROMPT = """
의도: {intent}

필요한 agent를 선택하고 실행 순서를 정하세요.
사용 가능한 agents: property_search, market_analysis, region_comparison, investment_advisor

JSON 응답:
{{
  "strategy": "sequential/parallel",
  "agents": [
    {{"name": "agent_name", "order": 1, "params": {{}}}}
  ]
}}
"""

EVALUATION_PROMPT = """
실행 결과: {results}

결과를 평가하고 JSON으로 응답:
{{
  "quality_score": 0.0-1.0,
  "needs_retry": true/false,
  "final_answer": "사용자에게 전달할 최종 답변"
}}
"""


# ============ NODE FUNCTIONS (노드 함수들) ============

async def analyze_intent_node(state: Dict[str, Any], runtime: Optional[Any] = None) -> Dict[str, Any]:
    """
    Step 1: 사용자 의도 분석
    사용자의 질문을 분석하여 의도와 엔티티를 추출
    """
    try:
        query = state.get("query", "")
        logger.info(f"[Step 1] 의도 분석 시작: {query[:50]}...")
        
        # 간단한 규칙 기반 의도 분석 (LLM 대체 가능)
        intent = {
            "intent_type": "search",  # 기본값
            "entities": {
                "region": None,
                "property_type": "아파트",
                "deal_type": "매매"
            }
        }
        
        # 키워드 기반 의도 파악
        if "분석" in query or "시세" in query:
            intent["intent_type"] = "analysis"
        elif "비교" in query:
            intent["intent_type"] = "comparison"
        elif "추천" in query or "투자" in query:
            intent["intent_type"] = "recommendation"
        
        # 지역 추출 (간단한 예시)
        regions = ["강남", "서초", "송파", "강북", "마포"]
        for region in regions:
            if region in query:
                intent["entities"]["region"] = f"서울특별시 {region}구"
                break
        
        # 거래 유형 추출
        if "전세" in query:
            intent["entities"]["deal_type"] = "전세"
        elif "월세" in query:
            intent["entities"]["deal_type"] = "월세"
        
        # 평수 추출 (간단한 정규식 사용 가능)
        if "30평" in query:
            intent["entities"]["size_range"] = {"min": 28, "max": 32}
        elif "40평" in query:
            intent["entities"]["size_range"] = {"min": 38, "max": 42}
        
        logger.info(f"[Step 1] 의도 분석 완료: {intent['intent_type']}")
        
        return {
            "intent": intent,
            "status": "processing",
            "execution_step": "planning"
        }
        
    except Exception as e:
        logger.error(f"[Step 1] 의도 분석 실패: {e}")
        return {
            "status": "failed",
            "errors": [f"Intent analysis failed: {str(e)}"]
        }


async def build_plan_node(state: Dict[str, Any], runtime: Optional[Any] = None) -> Dict[str, Any]:
    """
    Step 2: 계획 수립
    의도에 따라 실행할 agent와 순서를 결정
    """
    try:
        intent = state.get("intent", {})
        intent_type = intent.get("intent_type", "search")
        
        logger.info(f"[Step 2] 계획 수립 시작: intent_type={intent_type}")
        
        # 의도별 agent 선택 (규칙 기반)
        agents = []
        
        if intent_type == "search":
            agents = [
                {"name": "property_search", "order": 1, "params": intent.get("entities", {})}
            ]
        elif intent_type == "analysis":
            agents = [
                {"name": "property_search", "order": 1, "params": intent.get("entities", {})},
                {"name": "market_analysis", "order": 2, "params": {"region": intent.get("entities", {}).get("region")}}
            ]
        elif intent_type == "comparison":
            agents = [
                {"name": "property_search", "order": 1, "params": intent.get("entities", {})},
                {"name": "region_comparison", "order": 2, "params": {"region": intent.get("entities", {}).get("region")}}
            ]
        elif intent_type == "recommendation":
            agents = [
                {"name": "property_search", "order": 1, "params": intent.get("entities", {})},
                {"name": "market_analysis", "order": 2, "params": {"region": intent.get("entities", {}).get("region")}},
                {"name": "investment_advisor", "order": 3, "params": intent.get("entities", {})}
            ]
        
        execution_plan = {
            "strategy": "sequential",  # 순차 실행
            "agents": agents
        }
        
        logger.info(f"[Step 2] 계획 수립 완료: {len(agents)}개 agent 실행 예정")
        
        return {
            "execution_plan": execution_plan,
            "status": "processing",
            "execution_step": "executing"
        }
        
    except Exception as e:
        logger.error(f"[Step 2] 계획 수립 실패: {e}")
        return {
            "status": "failed",
            "errors": [f"Planning failed: {str(e)}"]
        }


async def execute_plan_node(state: Dict[str, Any], runtime: Optional[Any] = None) -> Dict[str, Any]:
    """
    Step 3: 계획 실행
    수립된 계획에 따라 agent들을 실행
    """
    try:
        execution_plan = state.get("execution_plan", {})
        agents = execution_plan.get("agents", [])
        
        logger.info(f"[Step 3] 실행 시작: {len(agents)}개 agent")
        
        # Context 준비
        context = {
            "user_id": "default_user",
            "session_id": state.get("chat_session_id", "default"),
            "query": state.get("query", "")
        }
        
        # Agent 실행 (순차적)
        agent_results = {}
        for agent_config in agents:
            agent_name = agent_config["name"]
            params = agent_config.get("params", {})
            
            logger.info(f"[Step 3] Agent 실행: {agent_name}")
            
            # AgentRegistry에서 agent 가져오기 (MockAgent 사용)
            agent = AgentRegistry.get_agent(agent_name)
            
            # Agent 실행
            try:
                result = await agent.execute({
                    **params,
                    "context": context
                })
                agent_results[agent_name] = result
                logger.info(f"[Step 3] Agent {agent_name} 성공")
            except Exception as e:
                logger.error(f"[Step 3] Agent {agent_name} 실패: {e}")
                agent_results[agent_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # 재시도가 필요한 agent 확인
        failed_agents = [
            name for name, result in agent_results.items()
            if result.get("status") == "error"
        ]
        
        logger.info(f"[Step 3] 실행 완료: 성공={len(agent_results)-len(failed_agents)}, 실패={len(failed_agents)}")
        
        return {
            "agent_results": agent_results,
            "failed_agents": failed_agents,
            "status": "processing",
            "execution_step": "evaluating"
        }
        
    except Exception as e:
        logger.error(f"[Step 3] 실행 실패: {e}")
        return {
            "status": "failed",
            "errors": [f"Execution failed: {str(e)}"]
        }


async def evaluate_results_node(state: Dict[str, Any], runtime: Optional[Any] = None) -> Dict[str, Any]:
    """
    Step 4: 결과 평가
    실행 결과를 평가하고 최종 응답 생성
    """
    try:
        agent_results = state.get("agent_results", {})
        failed_agents = state.get("failed_agents", [])
        query = state.get("query", "")
        
        logger.info(f"[Step 4] 평가 시작: {len(agent_results)}개 결과")
        
        # 품질 점수 계산
        total_agents = len(agent_results)
        successful_agents = total_agents - len(failed_agents)
        quality_score = successful_agents / total_agents if total_agents > 0 else 0.0
        
        # 재시도 필요 여부 판단
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 2)
        needs_retry = len(failed_agents) > 0 and retry_count < max_retries
        
        # 최종 응답 생성
        final_answer = self._generate_final_answer(query, agent_results)
        
        logger.info(f"[Step 4] 평가 완료: quality_score={quality_score:.2f}, needs_retry={needs_retry}")
        
        evaluation = {
            "quality_score": quality_score,
            "needs_retry": needs_retry,
            "retry_agents": failed_agents if needs_retry else []
        }
        
        final_output = {
            "answer": final_answer,
            "data": agent_results,
            "metadata": {
                "quality_score": quality_score,
                "agents_used": list(agent_results.keys()),
                "execution_time": datetime.now().isoformat()
            }
        }
        
        return {
            "evaluation": evaluation,
            "final_output": final_output,
            "retry_needed": needs_retry,
            "status": "completed" if not needs_retry else "processing",
            "execution_step": "finished" if not needs_retry else "retrying"
        }
        
    except Exception as e:
        logger.error(f"[Step 4] 평가 실패: {e}")
        return {
            "status": "failed",
            "errors": [f"Evaluation failed: {str(e)}"]
        }


def _generate_final_answer(query: str, agent_results: Dict[str, Any]) -> str:
    """최종 답변 생성 (helper function)"""
    
    # 결과에서 주요 정보 추출
    property_data = agent_results.get("property_search", {}).get("data", [])
    market_insights = agent_results.get("market_analysis", {}).get("insights", [])
    recommendations = agent_results.get("investment_advisor", {}).get("recommendations", [])
    
    # 간단한 답변 템플릿
    answer_parts = []
    
    if property_data:
        answer_parts.append(f"검색 결과 {len(property_data)}개의 매물을 찾았습니다.")
        if property_data and isinstance(property_data, list) and len(property_data) > 0:
            first_property = property_data[0]
            answer_parts.append(
                f"대표 매물: {first_property.get('name', '알 수 없음')} - "
                f"{first_property.get('region', '')} - "
                f"{first_property.get('price', 0):,}만원"
            )
    
    if market_insights:
        answer_parts.append("시장 분석 결과:")
        for insight in market_insights[:2]:  # 처음 2개만
            answer_parts.append(f"• {insight}")
    
    if recommendations:
        answer_parts.append("투자 추천:")
        for rec in recommendations[:2]:  # 처음 2개만
            answer_parts.append(f"• {rec}")
    
    if not answer_parts:
        return "죄송합니다. 요청하신 정보를 찾을 수 없습니다."
    
    return "\n".join(answer_parts)


# ============ MAIN SUPERVISOR CLASS ============

class SimplifiedRealEstateSupervisor(BaseAgent):
    """
    단순화된 부동산 챗봇 Supervisor
    
    Workflow:
    1. 의도 분석 (Analyze Intent)
    2. 계획 수립 (Build Plan)  
    3. 실행 (Execute)
    4. 평가 (Evaluate)
    """
    
    def __init__(
        self,
        agent_name: str = "simplified_supervisor",
        checkpoint_dir: Optional[str] = None,
        max_retries: int = 2
    ):
        """Initialize simplified supervisor"""
        self.max_retries = max_retries
        super().__init__(agent_name, checkpoint_dir)
        logger.info(f"SimplifiedRealEstateSupervisor 초기화 완료 (max_retries={max_retries})")
    
    def _get_state_schema(self) -> Type:
        """State schema 반환"""
        return SupervisorState
    
    def _build_graph(self) -> None:
        """
        LangGraph 워크플로우 구성
        
        Graph:
            START → 의도분석 → 계획수립 → 실행 → 평가 → END
                                            ↑         ↓
                                            └─────────┘ (retry)
        """
        self.workflow = StateGraph(
            state_schema=SupervisorState,
            context_schema=AgentContext
        )
        
        # 노드 추가
        self.workflow.add_node("analyze_intent", analyze_intent_node)
        self.workflow.add_node("build_plan", build_plan_node)
        self.workflow.add_node("execute_plan", execute_plan_node)
        self.workflow.add_node("evaluate_results", evaluate_results_node)
        
        # 엣지 추가
        self.workflow.add_edge(START, "analyze_intent")
        self.workflow.add_edge("analyze_intent", "build_plan")
        self.workflow.add_edge("build_plan", "execute_plan")
        self.workflow.add_edge("execute_plan", "evaluate_results")
        
        # 조건부 엣지 (재시도 로직)
        self.workflow.add_conditional_edges(
            "evaluate_results",
            self._should_retry,
            {
                "retry": "execute_plan",
                "end": END
            }
        )
        
        logger.info("워크플로우 그래프 구성 완료")
    
    def _should_retry(self, state: Dict[str, Any]) -> Literal["retry", "end"]:
        """재시도 여부 결정"""
        needs_retry = state.get("retry_needed", False)
        retry_count = state.get("retry_count", 0)
        
        if needs_retry and retry_count < self.max_retries:
            logger.info(f"재시도 필요 (attempt {retry_count + 1}/{self.max_retries})")
            # 재시도 카운트 증가는 execute_plan_node에서 처리
            return "retry"
        else:
            if needs_retry:
                logger.warning(f"최대 재시도 횟수 도달 ({self.max_retries})")
            return "end"
    
    async def _validate_input(self, input_data: Dict[str, Any]) -> bool:
        """입력 검증"""
        if "query" not in input_data:
            logger.error("query 필드가 없습니다")
            return False
        
        query = input_data["query"]
        if not isinstance(query, str) or len(query.strip()) == 0:
            logger.error("query가 비어있거나 유효하지 않습니다")
            return False
        
        return True
    
    def _create_initial_state(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """초기 state 생성"""
        return create_supervisor_initial_state(
            chat_session_id=input_data.get("chat_session_id", "default_session"),
            query=input_data.get("query", ""),
            max_retries=self.max_retries
        )
    
    async def ask(self, query: str, session_id: str = None) -> Dict[str, Any]:
        """
        간편 실행 메서드
        
        Args:
            query: 사용자 질문
            session_id: 세션 ID (선택)
        
        Returns:
            최종 응답
        """
        input_data = {
            "query": query,
            "chat_session_id": session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        result = await self.execute(input_data)
        
        if result["status"] == "success":
            return result["data"].get("final_output", {})
        else:
            return {
                "error": result.get("error", "Unknown error"),
                "status": "failed"
            }


# ============ TESTING ============

async def test_supervisor():
    """Supervisor 테스트"""
    supervisor = SimplifiedRealEstateSupervisor()
    
    test_queries = [
        "강남역 근처 30평대 아파트 매매 시세 알려줘",
        "서초구와 강남구 아파트 가격 비교해줘",
        "투자하기 좋은 지역 추천해줘"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"질문: {query}")
        print(f"{'='*60}")
        
        result = await supervisor.ask(query)
        
        print("\n[최종 응답]")
        if "error" in result:
            print(f"❌ 오류: {result['error']}")
        else:
            print(f"✅ 답변:\n{result.get('answer', 'No answer')}")
            print(f"\n📊 메타데이터:")
            print(f"  - 사용된 agents: {result.get('metadata', {}).get('agents_used', [])}")
            print(f"  - 품질 점수: {result.get('metadata', {}).get('quality_score', 0):.2f}")


if __name__ == "__main__":
    import asyncio
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 테스트 실행
    asyncio.run(test_supervisor())