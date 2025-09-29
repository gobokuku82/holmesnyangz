"""
Real Estate Chatbot Supervisor
Simplified single-file supervisor with LLM integration
Manages intent analysis, planning, and agent orchestration
"""

from typing import Dict, Any, Optional, List, Literal
from langgraph.graph import StateGraph, START, END
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

logger = logging.getLogger(__name__)


class LLMClient:
    """
    LLM Client for intent analysis and planning
    Supports OpenAI, Azure OpenAI, and Mock modes
    """

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "mock")
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the appropriate LLM client"""
        if self.provider == "openai" and self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized")
            except ImportError:
                logger.warning("OpenAI library not installed, using mock")
                self.provider = "mock"
        elif self.provider == "azure" and self.azure_endpoint:
            try:
                from openai import AzureOpenAI
                self.client = AzureOpenAI(
                    azure_endpoint=self.azure_endpoint,
                    api_key=self.api_key,
                    api_version="2024-02-01"
                )
                logger.info("Azure OpenAI client initialized")
            except ImportError:
                logger.warning("Azure OpenAI library not installed, using mock")
                self.provider = "mock"
        else:
            logger.info("Using mock LLM client")
            self.provider = "mock"

    async def analyze_intent(self, query: str) -> Dict[str, Any]:
        """
        Analyze user intent from query

        Args:
            query: User query string

        Returns:
            Intent analysis with entities and confidence
        """
        if self.provider == "mock":
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

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
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
        if self.provider == "mock":
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
    "collection_keywords": ["수집할 데이터 키워드"],
    "execution_order": "sequential" or "parallel",
    "reasoning": "계획 수립 이유"
}"""

            user_prompt = f"""사용자 질의: {query}
의도 분석: {json.dumps(intent, ensure_ascii=False)}"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"LLM plan creation failed: {e}")
            return self._mock_create_plan(query, intent)

    def _mock_analyze_intent(self, query: str) -> Dict[str, Any]:
        """Mock intent analysis"""
        query_lower = query.lower()

        # Determine intent type
        if any(word in query_lower for word in ["매물", "시세", "가격"]):
            intent_type = "search"
        elif any(word in query_lower for word in ["분석", "전망", "동향"]):
            intent_type = "analysis"
        elif any(word in query_lower for word in ["추천", "어떤", "좋은"]):
            intent_type = "recommendation"
        elif any(word in query_lower for word in ["법", "계약", "세금"]):
            intent_type = "legal"
        elif any(word in query_lower for word in ["대출", "금리", "융자"]):
            intent_type = "loan"
        else:
            intent_type = "general"

        # Extract entities
        entities = {}
        if "강남" in query_lower:
            entities["region"] = "강남구"
        elif "서초" in query_lower:
            entities["region"] = "서초구"

        if "아파트" in query_lower:
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
    Single-file implementation with LLM integration
    """

    def __init__(self):
        self.llm_client = LLMClient()
        self.workflow = None
        self._build_graph()

    def _build_graph(self):
        """Build the workflow graph"""
        self.workflow = StateGraph(RealEstateMainState)

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

        intent = await self.llm_client.analyze_intent(query)

        return {
            "intent": intent,
            "intent_type": intent.get("intent_type"),
            "intent_confidence": intent.get("confidence", 0.0),
            "status": "intent_analyzed",
            "execution_step": "planning"
        }

    async def create_plan_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create execution plan using LLM

        Args:
            state: Current state

        Returns:
            Updated state with execution plan
        """
        query = state["query"]
        intent = state["intent"]

        logger.info(f"Creating execution plan for intent: {intent.get('intent_type')}")

        plan = await self.llm_client.create_execution_plan(query, intent)

        return {
            "execution_plan": plan,
            "collection_keywords": plan.get("collection_keywords", []),
            "selected_agents": plan.get("agents", []),
            "status": "plan_created",
            "execution_step": "executing"
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
        collection_keywords = state.get("collection_keywords", [])

        logger.info(f"Executing agents: {selected_agents}")

        agent_results = {}
        shared_context = state.get("shared_context", {})

        for agent_name in selected_agents:
            if agent_name == "search_agent":
                # Import and execute search_agent
                try:
                    from subgraphs.search_agent import SearchAgent
                    search_agent = SearchAgent()

                    # Prepare input for search agent
                    search_input = {
                        "original_query": state["query"],
                        "collection_keywords": collection_keywords,
                        "shared_context": shared_context,
                        "chat_session_id": state["chat_session_id"]
                    }

                    # Execute search agent
                    result = await search_agent.execute(search_input)
                    agent_results[agent_name] = result

                    # Update shared context with collected data
                    if result.get("status") == "success":
                        shared_context.update(result.get("collected_data", {}))

                except Exception as e:
                    logger.error(f"Failed to execute {agent_name}: {e}")
                    agent_results[agent_name] = {
                        "status": "error",
                        "error": str(e)
                    }
            else:
                # Mock result for other agents
                agent_results[agent_name] = {
                    "status": "success",
                    "data": f"Mock result from {agent_name}"
                }

        return {
            "agent_results": agent_results,
            "shared_context": shared_context,
            "status": "agents_executed",
            "execution_step": "generating_response"
        }

    async def generate_response_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate final response

        Args:
            state: Current state

        Returns:
            Updated state with final response
        """
        agent_results = state.get("agent_results", {})
        intent = state.get("intent", {})

        logger.info("Generating final response")

        # Check if search_agent returned direct output
        search_result = agent_results.get("search_agent", {})
        if search_result.get("next_action") == "direct_output":
            response = {
                "type": "direct",
                "content": search_result.get("output_data", {}),
                "summary": search_result.get("search_summary", "")
            }
            response_type = "direct"
        else:
            # Generate response based on collected data
            collected_data = state.get("shared_context", {})

            response = {
                "type": "processed",
                "intent": intent.get("intent_type"),
                "data": collected_data,
                "summary": self._generate_summary(collected_data, intent),
                "agent_results": agent_results
            }
            response_type = "processed"

        return {
            "final_response": response,
            "response_type": response_type,
            "status": "completed",
            "execution_step": "done"
        }

    def _generate_summary(
        self,
        collected_data: Dict[str, Any],
        intent: Dict[str, Any]
    ) -> str:
        """Generate summary from collected data"""
        intent_type = intent.get("intent_type", "general")

        if not collected_data:
            return "요청하신 정보를 찾을 수 없습니다."

        summary_parts = []

        if intent_type == "search":
            summary_parts.append("부동산 검색 결과:")
            if "properties" in collected_data:
                summary_parts.append(f"- {len(collected_data['properties'])}개 매물 발견")
            if "price_info" in collected_data:
                summary_parts.append("- 시세 정보 확인")

        elif intent_type == "legal":
            summary_parts.append("법률 정보 검색 결과:")
            if "legal_info" in collected_data:
                summary_parts.append(f"- {len(collected_data.get('legal_info', []))}개 관련 법률")

        elif intent_type == "loan":
            summary_parts.append("대출 정보 검색 결과:")
            if "loan_products" in collected_data:
                summary_parts.append(f"- {len(collected_data.get('loan_products', []))}개 대출 상품")

        else:
            summary_parts.append("검색 결과가 준비되었습니다.")

        return "\n".join(summary_parts)

    async def process_query(self, query: str, session_id: str = None) -> Dict[str, Any]:
        """
        Process user query through the supervisor

        Args:
            query: User query
            session_id: Session ID

        Returns:
            Final response
        """
        # Prepare initial state
        initial_state = {
            "query": query,
            "chat_session_id": session_id or f"session_{datetime.now().timestamp()}",
            "status": "pending",
            "execution_step": "initializing",
            "errors": [],
            "agent_results": {},
            "shared_context": {}
        }

        try:
            # Run the workflow
            result = await self.app.ainvoke(initial_state)
            return result.get("final_response", {})

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "처리 중 오류가 발생했습니다."
            }


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        supervisor = RealEstateSupervisor()

        # Test queries
        test_queries = [
            "강남구 아파트 매매 시세 알려줘",
            "부동산 계약시 주의사항은?",
            "주택담보대출 금리 비교해줘"
        ]

        for query in test_queries:
            print(f"\n질의: {query}")
            print("-" * 50)
            result = await supervisor.process_query(query)
            print(f"응답: {json.dumps(result, ensure_ascii=False, indent=2)}")

    asyncio.run(main())