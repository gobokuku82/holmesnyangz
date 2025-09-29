"""
Real Estate Supervisor - Production Version
실제 LLM (OpenAI)만 사용하는 프로덕션 버전
Mock 로직은 supervisor_mock.py에 분리됨
"""

import json
import logging
from typing import Dict, Any, Optional, List
from langgraph.graph import StateGraph
import sys
from pathlib import Path

# Add parent directories to path
current_dir = Path(__file__).parent
service_dir = current_dir.parent
app_dir = service_dir.parent
backend_dir = app_dir.parent

# Add paths in correct order - most specific first
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
    Production version - OpenAI only
    """

    def __init__(self, context: LLMContext = None):
        self.context = context or create_default_llm_context()
        self.client = None
        self._connection_error = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize OpenAI client"""
        # Get API key from context first, only fallback to config if context.api_key is None
        # Empty string means explicitly no API key
        if self.context.api_key == "":
            api_key = ""  # Explicitly empty
        else:
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
                self._connection_error = "OpenAI 라이브러리가 설치되지 않았습니다."
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {e}")
                self._connection_error = f"OpenAI 연결 실패: {str(e)}"
        elif self.context.provider == "azure":
            # Azure OpenAI support can be added here
            logger.info("Azure OpenAI not yet implemented")
            self._connection_error = "Azure OpenAI는 아직 지원되지 않습니다."
        else:
            if self.context.provider == "openai" and not api_key:
                logger.warning("OPENAI_API_KEY not found")
                self._connection_error = "API 키가 설정되지 않았습니다."
            else:
                self._connection_error = "LLM 공급자가 설정되지 않았습니다."

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
        # Check for connection errors
        if self._connection_error:
            return {
                "error": True,
                "intent": "error",
                "message": "시스템 연결 오류가 발생했습니다.",
                "details": self._connection_error,
                "suggestion": "잠시 후 다시 시도해주세요."
            }

        if not self.client:
            return {
                "error": True,
                "intent": "error",
                "message": "LLM 클라이언트가 초기화되지 않았습니다.",
                "details": "OpenAI 연결에 실패했습니다.",
                "suggestion": "시스템 관리자에게 문의하세요."
            }

        try:
            system_prompt = """당신은 부동산 전문 챗봇의 의도 분석기입니다.
사용자 질의를 분석하여 의도와 핵심 정보를 추출하세요.

의도 타입:
- search: 매물/시세 검색
- analysis: 시장 분석
- recommendation: 추천 요청
- legal: 법률/규정 관련
- loan: 대출 관련
- general: 일반 문의

JSON 형식으로 응답하세요:
{
    "intent_type": "의도 타입",
    "entities": {
        "region": "지역명",
        "property_type": "부동산 유형",
        "transaction_type": "거래 유형"
    },
    "keywords": ["핵심 키워드"],
    "confidence": 0.0-1.0
}"""

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
            # Return unclear intent instead of error
            return {
                "intent": "unclear",
                "message": "질문을 이해하지 못했습니다. 다음과 같은 형식으로 질문해주세요:",
                "examples": [
                    "강남구 아파트 시세 알려줘",
                    "서초구 30평대 전세 매물 찾아줘",
                    "부동산 계약시 주의사항은?",
                    "주택담보대출 금리 비교해줘"
                ],
                "original_query": query
            }

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
        # Check for connection errors
        if self._connection_error:
            return {
                "error": True,
                "message": "시스템 연결 오류로 실행 계획을 생성할 수 없습니다.",
                "details": self._connection_error,
                "agents": []
            }

        if not self.client:
            return {
                "error": True,
                "message": "LLM 클라이언트가 초기화되지 않았습니다.",
                "details": "OpenAI 연결에 실패했습니다.",
                "agents": []
            }

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
            # Return error instead of falling back
            return {
                "error": True,
                "message": "실행 계획 생성 중 오류가 발생했습니다.",
                "details": str(e),
                "agents": []
            }


class RealEstateSupervisor:
    """
    Main Supervisor for Real Estate Chatbot
    Production version - OpenAI only
    """

    def __init__(self, llm_context: LLMContext = None):
        self.llm_context = llm_context or create_default_llm_context()
        self.llm_manager = LLMManager(self.llm_context)
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

        # Check for errors or unclear intent
        if intent.get("error"):
            return {
                "intent": intent,
                "intent_type": "error",
                "final_response": {
                    "type": "error",
                    "message": intent.get("message"),
                    "details": intent.get("details"),
                    "suggestion": intent.get("suggestion", "다시 시도해주세요.")
                }
            }

        if intent.get("intent") == "unclear":
            return {
                "intent": intent,
                "intent_type": "unclear",
                "final_response": {
                    "type": "help",
                    "message": intent.get("message"),
                    "examples": intent.get("examples", []),
                    "original_query": query
                }
            }

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
        # Skip if we already have an error or unclear intent
        if state.get("intent_type") in ["error", "unclear"]:
            return state

        query = state["query"]
        intent = state["intent"]

        logger.info(f"Creating execution plan for intent: {intent.get('intent_type')}")

        plan = await self.llm_manager.create_execution_plan(query, intent)

        # Check for plan creation errors
        if plan.get("error"):
            return {
                "execution_plan": plan,
                "final_response": {
                    "type": "error",
                    "message": plan.get("message"),
                    "details": plan.get("details")
                },
                "selected_agents": []
            }

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
        # Skip if we have an error or unclear intent
        if state.get("intent_type") in ["error", "unclear"]:
            return state

        # Skip if we already have a final response (from error handling)
        if state.get("final_response"):
            return state

        selected_agents = state.get("selected_agents", [])
        logger.info(f"Executing agents: {selected_agents}")

        agent_results = {}

        for agent_name in selected_agents:
            if agent_name == "search_agent":
                # Import and execute search agent
                from agents.search_agent import SearchAgent

                agent = SearchAgent(llm_context=self.llm_context)
                input_data = {
                    "original_query": state["query"],
                    "collection_keywords": state.get("collection_keywords", []),
                    "shared_context": state.get("shared_context", {}),
                    "chat_session_id": state.get("chat_session_id", "")
                }

                # SearchAgent uses app.ainvoke instead of run
                result = await agent.app.ainvoke(input_data)
                agent_results[agent_name] = result

            elif agent_name == "analysis_agent":
                # Analysis agent can be implemented here
                logger.info(f"Analysis agent not yet implemented")
                agent_results[agent_name] = {
                    "status": "not_implemented",
                    "message": "Analysis agent coming soon"
                }

            else:
                logger.warning(f"Unknown agent: {agent_name}")

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
        # Skip if we already have a final response (from error/unclear handling)
        if state.get("final_response"):
            return state

        logger.info("Generating final response")

        agent_results = state.get("agent_results", {})

        # Check if search_agent returned direct output
        search_result = agent_results.get("search_agent", {})
        if search_result.get("direct_output"):
            return {
                "final_response": search_result["direct_output"],
                "response_type": "direct"
            }

        # Process all agent results
        all_data = {}
        for agent_name, result in agent_results.items():
            if result.get("status") == "success":
                all_data[agent_name] = result.get("data", {})

        # Create summary
        summary = "데이터 수집 완료"
        if all_data:
            summary = f"{len(all_data)}개의 에이전트에서 데이터 수집 완료"

        final_response = {
            "type": "processed",
            "data": all_data,
            "summary": summary
        }

        return {
            "final_response": final_response,
            "response_type": "processed"
        }

    async def process_query(
        self,
        query: str,
        session_id: str = None,
        llm_context: LLMContext = None
    ) -> Dict[str, Any]:
        """
        Process user query through the workflow

        Args:
            query: User query
            session_id: Session ID
            llm_context: Optional LLM context override

        Returns:
            Complete state with final response
        """
        logger.info(f"Processing query: {query}")

        # Use override context if provided
        if llm_context:
            self.llm_context = llm_context
            self.llm_manager = LLMManager(llm_context)

        # Initialize state
        initial_state = {
            "query": query,
            "chat_session_id": session_id or "default_session",
            "shared_context": {},
            "messages": []
        }

        # Compile and run workflow
        app = self.workflow.compile()
        final_state = await app.ainvoke(initial_state)

        logger.info("Query processing completed")
        return final_state


# For backwards compatibility
def create_supervisor(llm_context: LLMContext = None) -> RealEstateSupervisor:
    """
    Factory function to create supervisor

    Args:
        llm_context: Optional LLM context

    Returns:
        Configured RealEstateSupervisor instance
    """
    return RealEstateSupervisor(llm_context=llm_context)


if __name__ == "__main__":
    import asyncio

    async def test_supervisor():
        # Example usage
        supervisor = RealEstateSupervisor()
        result = await supervisor.process_query(
            query="강남구 아파트 시세 알려줘",
            session_id="test_session"
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    asyncio.run(test_supervisor())