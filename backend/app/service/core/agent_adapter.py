"""
Agent Adapter - 기존 Agent들을 Registry 시스템에 통합
기존 코드를 최소한으로 수정하면서 새로운 아키텍처 적용
"""

import logging
from typing import Dict, Any, Optional, Type
from core.agent_registry import AgentRegistry, AgentCapabilities

logger = logging.getLogger(__name__)


class AgentAdapter:
    """
    기존 Agent들을 Registry와 통합하는 어댑터
    """

    @staticmethod
    def register_existing_agents():
        """
        모든 기존 Agent들을 Registry에 등록
        """
        logger.info("Registering existing agents to Registry...")

        # SearchAgent 등록
        try:
            from agents.search_agent import SearchAgent

            capabilities = AgentCapabilities(
                name="search_agent",
                description="법률, 부동산, 대출 정보를 검색하는 Agent",
                input_types=["query", "keywords"],
                output_types=["legal_search", "real_estate_search", "loan_search"],
                required_tools=[
                    "legal_search_tool",
                    "real_estate_search_tool",
                    "loan_search_tool"
                ],
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
            logger.info("SearchAgent registered successfully")

        except ImportError as e:
            logger.error(f"Failed to register SearchAgent: {e}")

        # AnalysisAgent 등록
        try:
            from agents.analysis_agent import AnalysisAgent

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
            logger.info("AnalysisAgent registered successfully")

        except ImportError as e:
            logger.error(f"Failed to register AnalysisAgent: {e}")

        # DocumentAgent 등록
        try:
            from agents.document_agent import DocumentAgent

            capabilities = AgentCapabilities(
                name="document_agent",
                description="부동산 관련 법률 문서를 생성하는 Agent",
                input_types=["document_type", "document_params"],
                output_types=["generated_document"],
                required_tools=["document_generation_tool"],
                team="document"
            )

            AgentRegistry.register(
                name="document_agent",
                agent_class=DocumentAgent,
                team="document",
                capabilities=capabilities,
                priority=3,
                enabled=True
            )
            logger.info("DocumentAgent registered successfully")

        except ImportError as e:
            logger.error(f"Failed to register DocumentAgent: {e}")

        # ReviewAgent 등록
        try:
            from agents.review_agent import ReviewAgent

            capabilities = AgentCapabilities(
                name="review_agent",
                description="계약서 및 문서를 검토하고 위험을 분석하는 Agent",
                input_types=["document_content", "review_type"],
                output_types=["risk_factors", "recommendations"],
                required_tools=["contract_review_tool"],
                team="document"
            )

            AgentRegistry.register(
                name="review_agent",
                agent_class=ReviewAgent,
                team="document",
                capabilities=capabilities,
                priority=3,
                enabled=True
            )
            logger.info("ReviewAgent registered successfully")

        except ImportError as e:
            logger.error(f"Failed to register ReviewAgent: {e}")

        logger.info(f"Registration complete. Registered agents: {AgentRegistry.list_agents()}")
        logger.info(f"Teams: {AgentRegistry.list_teams()}")

    @staticmethod
    async def execute_agent_dynamic(
        agent_name: str,
        input_data: Dict[str, Any],
        llm_context: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Registry를 통해 Agent를 동적으로 실행

        Args:
            agent_name: 실행할 Agent 이름
            input_data: 입력 데이터
            llm_context: LLM 컨텍스트

        Returns:
            실행 결과
        """
        # Registry에서 Agent 클래스 조회
        agent_class = AgentRegistry.get_agent_class(agent_name)
        if not agent_class:
            logger.error(f"Agent '{agent_name}' not found in registry")
            return {
                "status": "error",
                "error": f"Agent '{agent_name}' not found",
                "agent": agent_name
            }

        # Agent 메타데이터 조회
        metadata = AgentRegistry.get_agent(agent_name)
        if not metadata.enabled:
            logger.warning(f"Agent '{agent_name}' is disabled")
            return {
                "status": "skipped",
                "error": f"Agent '{agent_name}' is disabled",
                "agent": agent_name
            }

        try:
            # Agent 인스턴스 생성
            if agent_name in ["search_agent", "analysis_agent"]:
                # LLM context가 필요한 Agent들
                agent = agent_class(llm_context=llm_context)
            else:
                # LLM context가 필요 없는 Agent들
                agent = agent_class()

            # Agent 실행
            if hasattr(agent, 'app') and agent.app:
                # LangGraph 기반 Agent (SearchAgent, AnalysisAgent)
                result = await agent.app.ainvoke(input_data)
            elif hasattr(agent, 'execute'):
                # 일반 Agent (DocumentAgent, ReviewAgent)
                result = await agent.execute(input_data)
            else:
                # 동기 실행 Agent
                result = agent.run(input_data)

            logger.info(f"Agent '{agent_name}' executed successfully")
            return result

        except Exception as e:
            logger.error(f"Failed to execute agent '{agent_name}': {e}")
            return {
                "status": "error",
                "error": str(e),
                "agent": agent_name
            }

    @staticmethod
    def get_agents_for_intent(intent_type: str) -> list[str]:
        """
        의도 타입에 따라 실행할 Agent 목록 반환

        Args:
            intent_type: 의도 타입

        Returns:
            Agent 이름 목록
        """
        intent_agent_mapping = {
            "법률상담": ["search_agent"],
            "시세조회": ["search_agent", "analysis_agent"],
            "대출상담": ["search_agent", "analysis_agent"],
            "계약서작성": ["document_agent"],
            "계약서검토": ["review_agent"],
            "종합분석": ["search_agent", "analysis_agent"],
            "문서생성": ["document_agent"],
            "리스크분석": ["search_agent", "analysis_agent", "review_agent"]
        }

        agents = intent_agent_mapping.get(intent_type, ["search_agent"])

        # Registry에서 활성화된 Agent만 필터링
        enabled_agents = [
            agent for agent in agents
            if AgentRegistry.get_agent(agent) and AgentRegistry.get_agent(agent).enabled
        ]

        return enabled_agents

    @staticmethod
    def get_agent_dependencies(agent_name: str) -> Dict[str, Any]:
        """
        Agent의 의존성 정보 조회

        Args:
            agent_name: Agent 이름

        Returns:
            의존성 정보
        """
        dependencies = {
            "search_agent": {
                "requires": [],
                "provides": ["legal_search", "real_estate_search", "loan_search"]
            },
            "analysis_agent": {
                "requires": ["collected_data"],
                "provides": ["report", "insights"]
            },
            "document_agent": {
                "requires": ["document_type", "params"],
                "provides": ["generated_document"]
            },
            "review_agent": {
                "requires": ["document_content"],
                "provides": ["risk_analysis", "recommendations"]
            }
        }

        return dependencies.get(agent_name, {})


# 초기화 함수
def initialize_agent_system(auto_register: bool = True):
    """
    Agent 시스템 초기화

    Args:
        auto_register: 기존 Agent들을 자동으로 등록할지 여부
    """
    if auto_register:
        AgentAdapter.register_existing_agents()

    logger.info("Agent system initialized")
    return AgentRegistry()


# 사용 예시
if __name__ == "__main__":
    import asyncio

    async def test_dynamic_execution():
        # Agent 시스템 초기화
        initialize_agent_system()

        # 동적 Agent 실행 테스트
        test_input = {
            "query": "전세금 인상률 제한은?",
            "chat_session_id": "test_session",
            "original_query": "전세금 인상률 제한은?"
        }

        # Search Agent 실행
        result = await AgentAdapter.execute_agent_dynamic(
            "search_agent",
            test_input
        )
        print(f"Search result: {result.get('status')}")

        # 의도에 따른 Agent 목록 조회
        agents = AgentAdapter.get_agents_for_intent("법률상담")
        print(f"Agents for 법률상담: {agents}")

    # 테스트 실행
    asyncio.run(test_dynamic_execution())