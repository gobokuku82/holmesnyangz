"""
Real Estate Supervisor - Mock Version
테스트 전용 Mock Supervisor
실제 LLM을 사용하지 않고 미리 정의된 응답을 반환
"""

import logging
from typing import Dict, Any, Optional, List
from langgraph.graph import StateGraph
import sys
from pathlib import Path

# Add parent directories to path
current_dir = Path(__file__).parent
service_dir = current_dir.parent
backend_dir = service_dir.parent.parent

if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from core.states import RealEstateMainState
from core.context import LLMContext, create_default_llm_context

logger = logging.getLogger(__name__)


class MockLLMManager:
    """
    Mock LLM Manager for testing
    미리 정의된 응답을 반환하는 테스트용 Manager
    """

    def __init__(self):
        logger.info("MockLLMManager initialized for testing")

    async def analyze_intent(self, query: str) -> Dict[str, Any]:
        """Mock intent analysis"""
        query_lower = query.lower()

        # Determine intent type
        if any(word in query_lower for word in ["매물", "시세", "가격", "찾아"]):
            intent_type = "search"
        elif any(word in query_lower for word in ["법", "계약", "세금"]):
            intent_type = "legal"
        elif any(word in query_lower for word in ["대출", "금리", "융자"]):
            intent_type = "loan"
        elif any(word in query_lower for word in ["분석", "동향", "전망"]):
            intent_type = "analysis"
        elif any(word in query_lower for word in ["추천", "어떤", "좋은"]):
            intent_type = "recommendation"
        else:
            intent_type = "general"

        # Extract entities
        entities = {}
        regions = ["강남구", "서초구", "송파구", "용산구"]
        for region in regions:
            if region in query:
                entities["region"] = region
                break

        if "아파트" in query:
            entities["property_type"] = "아파트"

        if "매매" in query_lower:
            entities["transaction_type"] = "매매"
        elif "전세" in query_lower:
            entities["transaction_type"] = "전세"

        return {
            "intent_type": intent_type,
            "entities": entities,
            "confidence": 0.85,
            "keywords": [word for word in query.split() if len(word) > 1]
        }

    async def create_execution_plan(
        self,
        query: str,
        intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock execution plan creation"""
        intent_type = intent.get("intent_type", "general")

        # Determine agents and keywords based on intent
        if intent_type == "search":
            agents = ["search_agent"]
            keywords = ["매물", "시세", "가격", "거래"]
        elif intent_type == "legal":
            agents = ["search_agent"]
            keywords = ["법률", "계약", "세금", "규정"]
        elif intent_type == "loan":
            agents = ["search_agent"]
            keywords = ["대출", "금리", "LTV", "DTI"]
        elif intent_type == "analysis":
            agents = ["search_agent", "analysis_agent"]
            keywords = ["시장", "동향", "통계", "전망"]
        else:
            agents = ["search_agent"]
            keywords = ["부동산", "정보", "일반"]

        # Add region-specific keywords if present
        if "region" in intent.get("entities", {}):
            keywords.append(intent["entities"]["region"])

        return {
            "agents": agents,
            "collection_keywords": keywords,
            "execution_order": "sequential" if len(agents) > 1 else "parallel",
            "reasoning": f"{intent_type} 의도에 따른 계획 수립"
        }


class RealEstateSupervisorMock:
    """
    Mock Supervisor for Real Estate Chatbot
    테스트 전용 - 실제 LLM 사용하지 않음
    """

    def __init__(self):
        logger.info("RealEstateSupervisorMock initialized for testing")
        self.llm_manager = MockLLMManager()
        self.workflow = None
        self._build_graph()

    def _build_graph(self):
        """Build the workflow graph"""
        self.workflow = StateGraph(state_schema=RealEstateMainState)

        # Add nodes
        self.workflow.add_node("analyze_intent", self.analyze_intent_node)
        self.workflow.add_node("create_plan", self.create_plan_node)
        self.workflow.add_node("execute_agents", self.execute_agents_node)
        self.workflow.add_node("generate_response", self.generate_response_node)

        # Add edges
        self.workflow.set_entry_point("analyze_intent")
        self.workflow.add_edge("analyze_intent", "create_plan")
        self.workflow.add_edge("create_plan", "execute_agents")
        self.workflow.add_edge("execute_agents", "generate_response")

        logger.info("Mock Supervisor workflow graph built successfully")

    async def analyze_intent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user intent using mock"""
        query = state["query"]
        logger.info(f"[MOCK] Analyzing intent for query: {query}")

        intent = await self.llm_manager.analyze_intent(query)

        return {
            "intent": intent,
            "intent_type": intent.get("intent_type", "general"),
            "intent_confidence": intent.get("confidence", 0.0)
        }

    async def create_plan_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create execution plan using mock"""
        query = state["query"]
        intent = state["intent"]

        logger.info(f"[MOCK] Creating execution plan for intent: {intent.get('intent_type')}")

        plan = await self.llm_manager.create_execution_plan(query, intent)

        return {
            "execution_plan": plan,
            "collection_keywords": plan.get("collection_keywords", []),
            "selected_agents": plan.get("agents", [])
        }

    async def execute_agents_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agents (mock version uses mock search agent)"""
        selected_agents = state.get("selected_agents", [])
        logger.info(f"[MOCK] Executing agents: {selected_agents}")

        agent_results = {}

        for agent_name in selected_agents:
            if agent_name == "search_agent":
                # Use mock search agent
                from subgraphs.search_agent import SearchAgent

                # Create mock LLM context for search agent
                mock_context = create_default_llm_context()
                mock_context.use_mock = True

                agent = SearchAgent(llm_context=mock_context)
                input_data = {
                    "original_query": state["query"],
                    "collection_keywords": state.get("collection_keywords", []),
                    "shared_context": state.get("shared_context", {}),
                    "chat_session_id": state.get("chat_session_id", "")
                }

                # SearchAgent uses app.ainvoke instead of run
                result = await agent.app.ainvoke(input_data)
                agent_results[agent_name] = result
            else:
                # Mock result for other agents
                agent_results[agent_name] = {
                    "status": "completed",
                    "data": f"Mock result for {agent_name}"
                }

        return {
            "agent_results": agent_results,
            "status": "agents_executed"
        }

    async def generate_response_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock response"""
        logger.info("[MOCK] Generating mock response")

        agent_results = state.get("agent_results", {})
        search_result = agent_results.get("search_agent", {})

        # Check if search agent returned direct output
        if search_result.get("direct_output"):
            return {
                "final_response": search_result["direct_output"],
                "response_type": "direct"
            }

        # Generate mock summary
        mock_summary = f"[MOCK] {len(agent_results)}개의 에이전트 실행 완료"

        # Collect all data
        all_data = {}
        for agent_name, result in agent_results.items():
            if result.get("status") == "success":
                all_data[agent_name] = result.get("data", {})

        final_response = {
            "type": "processed",
            "data": all_data,
            "summary": mock_summary
        }

        return {
            "final_response": final_response,
            "response_type": "processed"
        }

    async def process_query(
        self,
        query: str,
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        Process user query using mock workflow

        Args:
            query: User query
            session_id: Session ID

        Returns:
            Complete state with mock response
        """
        logger.info(f"[MOCK] Processing query: {query}")

        # Initialize state
        initial_state = {
            "query": query,
            "chat_session_id": session_id or "mock_session",
            "shared_context": {},
            "messages": []
        }

        # Compile and run workflow
        app = self.workflow.compile()
        final_state = await app.ainvoke(initial_state)

        logger.info("[MOCK] Query processing completed")
        return final_state