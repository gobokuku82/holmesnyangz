"""
Real Estate Chatbot Supervisor
Updated for LangGraph 0.6+ with Runtime and Context support
Manages intent analysis, planning, and agent orchestration
"""

from typing import Dict, Any, Optional, List, Literal
from langgraph.graph import StateGraph, START, END
from dataclasses import dataclass
import logging
import json
import os
from datetime import datetime
import sys
from pathlib import Path

# Add parent directories to path for imports
current_file = Path(__file__)
supervisor_dir = current_file.parent  # supervisor
service_dir = supervisor_dir.parent   # service
app_dir = service_dir.parent         # app
backend_dir = app_dir.parent         # backend

# Add multiple paths to ensure imports work
if str(service_dir) not in sys.path:
    sys.path.insert(0, str(service_dir))
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from core.states import RealEstateMainState
from core.context import LLMContext, create_default_llm_context
from core.config import Config

logger = logging.getLogger(__name__)


class LLMManager:
    """
    Centralized LLM Manager for all LLM operations
    Uses LLMContext for configuration (LangGraph 0.6+)
    """

    def __init__(self, context: LLMContext = None):
        self.context = context or create_default_llm_context()
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the appropriate LLM client"""
        # Check if forced to use mock
        if self.context.use_mock:
            logger.info("Using mock LLM (forced by context)")
            self.context.provider = "mock"
            return

        # Get API key from context or config
        api_key = self.context.api_key or Config.LLM_DEFAULTS.get("api_key")

        if self.context.provider == "openai" and api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=api_key,
                    organization=self.context.organization
                )
                logger.info("OpenAI client initialized successfully")
            except ImportError:
                logger.error("OpenAI library not installed. Install with: pip install openai")
                logger.warning("Falling back to mock mode")
                self.context.provider = "mock"
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {e}")
                logger.warning("Falling back to mock mode")
                self.context.provider = "mock"
        elif self.context.provider == "azure":
            # Azure OpenAI support can be added here
            logger.info("Azure OpenAI not yet implemented, using mock")
            self.context.provider = "mock"
        else:
            if self.context.provider == "openai" and not api_key:
                logger.warning("OPENAI_API_KEY not found")
            logger.info("Using mock LLM")
            self.context.provider = "mock"

    def get_model(self, purpose: str) -> str:
        """Get model name for specific purpose"""
        # Check context overrides first
        if self.context.model_overrides and purpose in self.context.model_overrides:
            return self.context.model_overrides[purpose]
        # Use defaults from config
        return Config.LLM_DEFAULTS["models"].get(purpose, "gpt-4o-mini")

    def get_params(self) -> Dict[str, Any]:
        """Get LLM parameters with context overrides"""
        params = Config.LLM_DEFAULTS["default_params"].copy()

        # Apply context overrides if present
        if self.context.temperature is not None:
            params["temperature"] = self.context.temperature
        if self.context.max_tokens is not None:
            params["max_tokens"] = self.context.max_tokens
        if self.context.response_format is not None:
            params["response_format"] = self.context.response_format

        return params

    async def analyze_intent(self, query: str) -> Dict[str, Any]:
        """
        Analyze user intent from query

        Args:
            query: User query string

        Returns:
            Intent analysis with entities and confidence
        """
        if self.context.provider == "mock":
            return self._mock_analyze_intent(query)

        try:
            system_prompt = """당신은 부동산 전문 챗봇의 의도 분석기입니다.
사용자 질의를 분석하여 의도와 핵심 정보를 추출하세요.

의도 타입:
- search: 매물/시세 검색
- analysis: 시장 분석
- recommendation: 추천 요청
- legal: 법률/규정 문의
- loan: 대출 상담
- general: 일반 질문

JSON 형식으로 응답하세요."""

            user_prompt = f"사용자 질의: {query}"

            model = self.get_model("intent")
            params = self.get_params()

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                **params
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"LLM intent analysis failed: {e}")
            return self._mock_analyze_intent(query)

    async def create_execution_plan(
        self,
        query: str,
        intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create execution plan based on intent

        Args:
            query: User query
            intent: Analyzed intent

        Returns:
            Execution plan with agents and keywords
        """
        if self.context.provider == "mock":
            return self._mock_create_plan(query, intent)

        try:
            system_prompt = """당신은 부동산 챗봇의 실행 계획 수립 전문가입니다.
사용자 의도에 따라 필요한 에이전트와 수집할 데이터를 결정하세요.

사용 가능한 에이전트:
- search_agent: 데이터 검색 및 수집 (법률, 규정, 대출, 부동산 정보)
- analysis_agent: 데이터 분석 및 인사이트 도출
- recommendation_agent: 맞춤 추천 제공

JSON 형식으로 응답하세요:
{
    "agents": ["선택된 에이전트 목록"],
    "collection_keywords": ["수집할 키워드"],
    "execution_order": "sequential 또는 parallel",
    "reasoning": "계획 수립 근거"
}"""

            user_prompt = f"""사용자 질의: {query}
분석된 의도: {json.dumps(intent, ensure_ascii=False)}"""

            model = self.get_model("planning")
            params = self.get_params()

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                **params
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"LLM planning failed: {e}")
            return self._mock_create_plan(query, intent)

    def _mock_analyze_intent(self, query: str) -> Dict[str, Any]:
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

    def _mock_create_plan(
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


class RealEstateSupervisor:
    """
    Main Supervisor for Real Estate Chatbot
    Updated for LangGraph 0.6+ with Runtime and Context support
    """

    def __init__(self, llm_context: LLMContext = None):
        self.llm_context = llm_context or create_default_llm_context()
        self.llm_manager = LLMManager(self.llm_context)
        self.workflow = None
        self._build_graph()

    def _build_graph(self):
        """Build the workflow graph with context_schema"""
        # Create StateGraph with context_schema for LangGraph 0.6+
        self.workflow = StateGraph(
            state_schema=RealEstateMainState,
            # context_schema=LLMContext  # This would be used with Runtime
        )

        # Add nodes
        self.workflow.add_node("analyze_intent", self.analyze_intent_node)
        self.workflow.add_node("create_plan", self.create_plan_node)
        self.workflow.add_node("execute_agents", self.execute_agents_node)
        self.workflow.add_node("generate_response", self.generate_response_node)

        # Add edges
        self.workflow.add_edge(START, "analyze_intent")
        self.workflow.add_edge("analyze_intent", "create_plan")
        self.workflow.add_edge("create_plan", "execute_agents")
        self.workflow.add_edge("execute_agents", "generate_response")
        self.workflow.add_edge("generate_response", END)

        # Compile the graph
        self.app = self.workflow.compile()
        logger.info("Supervisor workflow graph built successfully")

    async def analyze_intent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze user intent using LLM

        Args:
            state: Current state

        Returns:
            Updated state with intent analysis
        """
        query = state["query"]
        logger.info(f"Analyzing intent for query: {query}")

        intent = await self.llm_manager.analyze_intent(query)

        return {
            "intent": intent,
            "intent_type": intent.get("intent_type", "general"),
            "intent_confidence": intent.get("confidence", 0.0)
        }

    async def create_plan_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create execution plan based on intent

        Args:
            state: Current state

        Returns:
            Updated state with execution plan
        """
        query = state["query"]
        intent = state["intent"]

        logger.info(f"Creating execution plan for intent: {intent.get('intent_type')}")

        plan = await self.llm_manager.create_execution_plan(query, intent)

        return {
            "execution_plan": plan,
            "collection_keywords": plan.get("collection_keywords", []),
            "selected_agents": plan.get("agents", [])
        }

    async def execute_agents_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute selected agents

        Args:
            state: Current state

        Returns:
            Updated state with agent results
        """
        selected_agents = state.get("selected_agents", [])
        logger.info(f"Executing agents: {selected_agents}")

        agent_results = {}

        for agent_name in selected_agents:
            if agent_name == "search_agent":
                # Import and execute search agent
                from subgraphs.search_agent import SearchAgent

                agent = SearchAgent(llm_context=self.llm_context)
                input_data = {
                    "original_query": state["query"],
                    "collection_keywords": state.get("collection_keywords", []),
                    "shared_context": state.get("shared_context", {}),
                    "chat_session_id": state.get("chat_session_id", "")
                }

                result = await agent.execute(input_data)
                agent_results[agent_name] = result

                # Update shared context
                if "shared_context" in result:
                    state["shared_context"] = result["shared_context"]
            else:
                # Placeholder for other agents
                agent_results[agent_name] = {
                    "status": "not_implemented",
                    "message": f"{agent_name} not yet implemented"
                }

        return {
            "agent_results": agent_results,
            "status": "agents_executed"
        }

    async def generate_response_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate final response based on agent results

        Args:
            state: Current state

        Returns:
            Updated state with final response
        """
        logger.info("Generating final response")

        agent_results = state.get("agent_results", {})

        # Check if search_agent returned direct output
        search_result = agent_results.get("search_agent", {})
        if search_result.get("next_action") == "direct_output":
            final_response = {
                "type": "direct",
                "content": search_result.get("output_data", {}),
                "summary": search_result.get("search_summary", "")
            }
        else:
            # Generate response based on collected data
            final_response = {
                "type": "processed",
                "data": search_result.get("collected_data", {}),
                "summary": "데이터 처리 완료"
            }

        return {
            "final_response": final_response,
            "response_type": final_response["type"],
            "response_metadata": {
                "timestamp": datetime.now().isoformat(),
                "intent_type": state.get("intent_type"),
                "agents_used": list(agent_results.keys()),
                "keywords": state.get("collection_keywords", [])
            },
            "status": "completed",
            "execution_step": "done"
        }

    async def process_query(
        self,
        query: str,
        session_id: str = None,
        llm_context: LLMContext = None
    ) -> Dict[str, Any]:
        """
        Process user query through the supervisor workflow

        Args:
            query: User query
            session_id: Session ID
            llm_context: Optional LLM context override

        Returns:
            Complete state with results
        """
        # Update LLM context if provided
        if llm_context:
            self.llm_context = llm_context
            self.llm_manager = LLMManager(llm_context)

        # Prepare initial state
        initial_state = {
            # Session identifiers
            "chat_session_id": session_id or f"session_{datetime.now().timestamp()}",
            "chat_thread_id": None,
            "db_session_id": None,
            "db_user_id": None,

            # Query and intent
            "query": query,
            "intent": None,
            "intent_confidence": 0.0,
            "intent_type": None,

            # Planning
            "execution_plan": None,
            "collection_keywords": [],
            "selected_agents": [],

            # Results
            "agent_results": {},
            "shared_context": {},

            # Control
            "current_agent": None,
            "agent_sequence": None,
            "status": "pending",
            "execution_step": "starting",
            "errors": [],

            # Response
            "final_response": None,
            "response_type": None,
            "response_metadata": None
        }

        try:
            # Run the workflow
            result = await self.app.ainvoke(initial_state)
            return result  # Return complete state

        except Exception as e:
            logger.error(f"Supervisor execution failed: {e}")
            return {
                **initial_state,
                "status": "error",
                "errors": [str(e)],
                "final_response": {
                    "type": "error",
                    "message": "처리 중 오류가 발생했습니다.",
                    "error": str(e)
                }
            }


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Create LLM context
        llm_context = LLMContext(
            provider="openai",  # or "mock" for testing
            api_key=os.getenv("OPENAI_API_KEY"),
            model_overrides={"intent": "gpt-4o-mini"},
            temperature=0.3
        )

        # Create supervisor with context
        supervisor = RealEstateSupervisor(llm_context)

        # Test query
        query = "강남구 아파트 매매 시세 알려줘"
        result = await supervisor.process_query(query, "test_session")

        print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")

    asyncio.run(main())