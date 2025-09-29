"""
Search Agent Subgraph
Updated for LangGraph 0.6+ with LLMContext support
Handles data collection and routing decisions
Uses LLM to determine next actions
"""

from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, START, END
import logging
import json
import os
import sys
from pathlib import Path

# Add parent directories to path for imports
current_file = Path(__file__)
subgraphs_dir = current_file.parent  # subgraphs
service_dir = subgraphs_dir.parent   # service
app_dir = service_dir.parent         # app
backend_dir = app_dir.parent         # backend

# Add multiple paths to ensure imports work
if str(service_dir) not in sys.path:
    sys.path.insert(0, str(service_dir))
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from core.states import SearchAgentState
from core.context import LLMContext, create_default_llm_context
from core.config import Config
from tools import tool_registry

logger = logging.getLogger(__name__)


class SearchAgentLLM:
    """
    LLM client for search agent decision making
    Updated for LangGraph 0.6+ with LLMContext support
    """

    def __init__(self, context: LLMContext = None):
        self.context = context or create_default_llm_context()
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize LLM client"""
        # Check if forced to use mock
        if self.context.use_mock:
            logger.info("SearchAgent using mock LLM (forced by context)")
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
                logger.info("SearchAgent OpenAI client initialized")
            except ImportError:
                logger.warning("OpenAI not available, using mock")
                self.context.provider = "mock"
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI for SearchAgent: {e}")
                self.context.provider = "mock"
        else:
            logger.info("SearchAgent using mock LLM")
            self.context.provider = "mock"

    def get_model(self, purpose: str = "search") -> str:
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

    async def create_search_plan(
        self,
        query: str,
        keywords: List[str]
    ) -> Dict[str, Any]:
        """
        Create search plan based on query and keywords

        Args:
            query: Original user query
            keywords: Collection keywords from supervisor

        Returns:
            Search plan with tools and parameters
        """
        if self.context.provider == "mock":
            return self._mock_search_plan(query, keywords)

        try:
            system_prompt = """당신은 부동산 정보 검색 전문가입니다.
주어진 키워드를 바탕으로 적절한 검색 도구를 선택하고 검색 계획을 수립하세요.

사용 가능한 도구:
- legal_search: 법률, 계약, 세금 정보
- regulation_search: 규정, 정책, 건축 규제
- loan_search: 대출, 금리, 금융 상품
- real_estate_search: 매물, 시세, 거래 정보

JSON 형식으로 응답:
{
    "selected_tools": ["도구1", "도구2"],
    "tool_parameters": {
        "도구1": {"param1": "value1"},
        "도구2": {"param2": "value2"}
    },
    "search_strategy": "검색 전략 설명"
}"""

            user_prompt = f"""사용자 질의: {query}
수집 키워드: {', '.join(keywords)}"""

            model = self.get_model("search")
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
            logger.error(f"LLM search plan failed: {e}")
            return self._mock_search_plan(query, keywords)

    async def decide_next_action(
        self,
        collected_data: Dict[str, Any],
        query: str
    ) -> Dict[str, Any]:
        """
        Decide next action based on collected data

        Args:
            collected_data: Data collected from tools
            query: Original query

        Returns:
            Decision on next action
        """
        if self.context.provider == "mock":
            return self._mock_next_action(collected_data)

        try:
            system_prompt = """수집된 데이터를 분석하고 다음 행동을 결정하세요.

가능한 행동:
- return_to_supervisor: 감독자에게 결과 반환
- pass_to_agent: 다른 에이전트에게 전달 (target_agent 지정)
- direct_output: 사용자에게 직접 출력

JSON 형식으로 응답:
{
    "next_action": "선택한 행동",
    "target_agent": "대상 에이전트 (pass_to_agent인 경우)",
    "reasoning": "결정 이유",
    "summary": "데이터 요약"
}"""

            user_prompt = f"""원본 질의: {query}
수집된 데이터 개수: {len(collected_data)}
데이터 카테고리: {list(collected_data.keys())}"""

            model = self.get_model("search")
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
            logger.error(f"LLM next action decision failed: {e}")
            return self._mock_next_action(collected_data)

    def _mock_search_plan(self, query: str, keywords: List[str]) -> Dict[str, Any]:
        """Mock search plan creation"""
        selected_tools = []
        tool_parameters = {}

        # Analyze keywords to select tools
        keywords_str = " ".join(keywords).lower()

        if any(word in keywords_str for word in ["법", "계약", "세금"]):
            selected_tools.append("legal_search")
            tool_parameters["legal_search"] = {"query": query}

        if any(word in keywords_str for word in ["규정", "정책", "규제"]):
            selected_tools.append("regulation_search")
            tool_parameters["regulation_search"] = {"query": query}

        if any(word in keywords_str for word in ["대출", "금리", "융자"]):
            selected_tools.append("loan_search")
            tool_parameters["loan_search"] = {"query": query}

        if any(word in keywords_str for word in ["매물", "시세", "가격", "거래"]):
            selected_tools.append("real_estate_search")
            tool_parameters["real_estate_search"] = {"query": query}

        # Default to real_estate_search if no tools selected
        if not selected_tools:
            selected_tools = ["real_estate_search"]
            tool_parameters["real_estate_search"] = {"query": query}

        return {
            "selected_tools": selected_tools,
            "tool_parameters": tool_parameters,
            "search_strategy": f"{len(selected_tools)}개 도구를 사용한 통합 검색"
        }

    def _mock_next_action(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock next action decision"""
        if not collected_data:
            return {
                "next_action": "return_to_supervisor",
                "reasoning": "데이터 수집 실패",
                "summary": "검색 결과 없음"
            }

        data_count = sum(len(v) if isinstance(v, list) else 1 for v in collected_data.values())

        if data_count > 10:
            # Large amount of data - needs analysis
            return {
                "next_action": "pass_to_agent",
                "target_agent": "analysis_agent",
                "reasoning": "대량의 데이터 분석 필요",
                "summary": f"{data_count}개의 결과 수집 완료"
            }
        else:
            # Small amount of data - direct output
            return {
                "next_action": "direct_output",
                "reasoning": "간단한 결과로 직접 응답 가능",
                "summary": f"{data_count}개의 관련 정보 발견"
            }


class SearchAgent:
    """
    Search Agent for data collection
    Updated for LangGraph 0.6+ with LLMContext support
    """

    def __init__(self, llm_context: LLMContext = None):
        self.llm_context = llm_context or create_default_llm_context()
        self.llm_client = SearchAgentLLM(self.llm_context)
        self.workflow = None
        self._build_graph()

    def _build_graph(self):
        """Build the search agent workflow"""
        self.workflow = StateGraph(SearchAgentState)

        # Add nodes
        self.workflow.add_node("create_search_plan", self.create_search_plan_node)
        self.workflow.add_node("execute_tools", self.execute_tools_node)
        self.workflow.add_node("process_results", self.process_results_node)
        self.workflow.add_node("decide_next_action", self.decide_next_action_node)

        # Add edges
        self.workflow.add_edge(START, "create_search_plan")
        self.workflow.add_edge("create_search_plan", "execute_tools")
        self.workflow.add_edge("execute_tools", "process_results")
        self.workflow.add_edge("process_results", "decide_next_action")
        self.workflow.add_edge("decide_next_action", END)

        # Compile the graph
        self.app = self.workflow.compile()
        logger.info("Search Agent workflow built successfully")

    async def create_search_plan_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create search plan using LLM

        Args:
            state: Current state

        Returns:
            Updated state with search plan
        """
        query = state["original_query"]
        keywords = state["collection_keywords"]

        logger.info(f"Creating search plan for keywords: {keywords}")

        plan = await self.llm_client.create_search_plan(query, keywords)

        return {
            "search_plan": plan,
            "selected_tools": plan.get("selected_tools", []),
            "tool_parameters": plan.get("tool_parameters", {}),
            "status": "searching",
            "execution_step": "executing_tools"
        }

    async def execute_tools_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute selected tools

        Args:
            state: Current state

        Returns:
            Updated state with tool results
        """
        selected_tools = state.get("selected_tools", [])
        tool_parameters = state.get("tool_parameters", {})

        logger.info(f"Executing tools: {selected_tools}")

        tool_results = {}
        successful_tools = []
        failed_tools = []

        for tool_name in selected_tools:
            tool = tool_registry.get(tool_name)

            if tool:
                try:
                    params = tool_parameters.get(tool_name, {})
                    query = params.get("query", state["original_query"])

                    # Execute tool with mock data
                    result = await tool.execute(query, params)

                    tool_results[tool_name] = result
                    successful_tools.append(tool_name)

                    logger.info(f"Tool {tool_name} executed successfully")

                except Exception as e:
                    logger.error(f"Tool {tool_name} failed: {e}")
                    failed_tools.append(tool_name)
                    tool_results[tool_name] = {
                        "status": "error",
                        "error": str(e)
                    }
            else:
                logger.warning(f"Tool {tool_name} not found")
                failed_tools.append(tool_name)

        return {
            "tool_results": tool_results,
            "successful_tools": successful_tools,
            "failed_tools": failed_tools,
            "status": "processing",
            "execution_step": "processing_results"
        }

    async def process_results_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and aggregate tool results

        Args:
            state: Current state

        Returns:
            Updated state with processed results
        """
        tool_results = state.get("tool_results", {})

        logger.info("Processing tool results")

        collected_data = {}
        total_count = 0

        for tool_name, result in tool_results.items():
            if result.get("status") == "success":
                data = result.get("data", [])
                collected_data[tool_name] = data
                total_count += len(data) if isinstance(data, list) else 1

        # Generate summary
        summary_parts = []
        for tool_name, data in collected_data.items():
            if isinstance(data, list):
                summary_parts.append(f"{tool_name}: {len(data)}개 결과")
            else:
                summary_parts.append(f"{tool_name}: 데이터 수집 완료")

        data_summary = "\n".join(summary_parts) if summary_parts else "데이터 수집 실패"

        # Calculate quality score
        quality_score = len(collected_data) / len(tool_results) if tool_results else 0.0

        return {
            "collected_data": collected_data,
            "data_summary": data_summary,
            "data_quality_score": quality_score,
            "status": "processed",
            "execution_step": "deciding_next_action"
        }

    async def decide_next_action_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decide next action using LLM

        Args:
            state: Current state

        Returns:
            Updated state with routing decision
        """
        collected_data = state.get("collected_data", {})
        query = state["original_query"]

        logger.info("Deciding next action")

        decision = await self.llm_client.decide_next_action(collected_data, query)

        # Prepare output based on decision
        if decision["next_action"] == "direct_output":
            output_data = {
                "type": "search_results",
                "data": collected_data,
                "summary": state.get("data_summary", ""),
                "total_results": sum(
                    len(v) if isinstance(v, list) else 1
                    for v in collected_data.values()
                )
            }
        else:
            output_data = None

        # Update shared context
        shared_context = state.get("shared_context", {})
        shared_context.update(collected_data)

        return {
            "next_action": decision.get("next_action", "return_to_supervisor"),
            "target_agent": decision.get("target_agent"),
            "routing_reason": decision.get("reasoning", ""),
            "search_summary": decision.get("summary", state.get("data_summary", "")),
            "output_data": output_data,
            "shared_context": shared_context,
            "status": "completed",
            "execution_step": "done"
        }

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute search agent

        Args:
            input_data: Input from supervisor

        Returns:
            Search results and routing decision
        """
        # Prepare initial state
        initial_state = {
            "original_query": input_data.get("original_query", ""),
            "collection_keywords": input_data.get("collection_keywords", []),
            "shared_context": input_data.get("shared_context", {}),
            "chat_session_id": input_data.get("chat_session_id", ""),
            "status": "pending",
            "execution_step": "initializing",
            "errors": [],
            "tool_results": {},
            "successful_tools": [],
            "failed_tools": []
        }

        try:
            # Run the workflow
            result = await self.app.ainvoke(initial_state)

            return {
                "status": "success",
                "next_action": result.get("next_action"),
                "target_agent": result.get("target_agent"),
                "collected_data": result.get("collected_data", {}),
                "output_data": result.get("output_data"),
                "search_summary": result.get("search_summary", ""),
                "shared_context": result.get("shared_context", {})
            }

        except Exception as e:
            logger.error(f"Search agent execution failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "collected_data": {},
                "search_summary": "검색 실패"
            }


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Create LLM context
        llm_context = LLMContext(
            provider="openai",  # or "mock" for testing
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.3
        )

        # Create search agent with context
        search_agent = SearchAgent(llm_context)

        # Test input
        test_input = {
            "original_query": "강남구 아파트 매매 시세와 대출 정보 알려줘",
            "collection_keywords": ["매물", "시세", "대출", "금리"],
            "shared_context": {},
            "chat_session_id": "test_session"
        }

        print("Testing Search Agent")
        print("-" * 50)
        result = await search_agent.execute(test_input)
        print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")

    asyncio.run(main())