"""
Analysis Agent Subgraph
=======================
LangGraph 0.6+ compatible agent for analyzing collected data
Processes data from SearchAgent or direct input to generate insights
"""

from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, START, END
import logging
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directories to path for imports
current_file = Path(__file__)
agents_dir = current_file.parent     # agents
service_dir = agents_dir.parent      # service
app_dir = service_dir.parent         # app
backend_dir = app_dir.parent         # backend

# Add paths to ensure imports work
if str(service_dir) not in sys.path:
    sys.path.insert(0, str(service_dir))
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Add app.service to path for absolute imports
sys.path.insert(0, str(backend_dir / "app" / "service"))

from core.states import AnalysisAgentState
from core.context import LLMContext, create_default_llm_context
from core.config import Config
from core.todo_types import (
    create_todo_dict, update_todo_status, find_todo, get_todo_summary
)
from tools.analysis_tools import analysis_tool_registry

logger = logging.getLogger(__name__)


class AnalysisAgentLLM:
    """
    LLM client for analysis agent decision making
    Handles analysis planning and insight generation
    """

    def __init__(self, context: LLMContext = None):
        self.context = context or create_default_llm_context()
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize LLM client"""
        api_key = self.context.api_key or Config.LLM_DEFAULTS.get("api_key")

        if self.context.provider == "openai":
            if not api_key:
                raise ValueError("OpenAI API key is required")
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=api_key,
                    organization=self.context.organization
                )
                logger.info("AnalysisAgent OpenAI client initialized")
            except ImportError:
                raise ImportError("OpenAI library not installed")
            except Exception as e:
                raise RuntimeError(f"Failed to initialize OpenAI client: {e}")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.context.provider}")

    def get_model(self, purpose: str = "analysis") -> str:
        """Get model name for specific purpose"""
        if self.context.model_overrides and purpose in self.context.model_overrides:
            return self.context.model_overrides[purpose]
        return Config.LLM_DEFAULTS["models"].get(purpose, "gpt-4o")

    def get_params(self) -> Dict[str, Any]:
        """Get LLM parameters with context overrides"""
        params = Config.LLM_DEFAULTS["default_params"].copy()

        if self.context.temperature is not None:
            params["temperature"] = self.context.temperature
        if self.context.max_tokens is not None:
            params["max_tokens"] = self.context.max_tokens
        if self.context.response_format is not None:
            params["response_format"] = self.context.response_format

        return params

    async def create_analysis_plan(
        self,
        query: str,
        analysis_type: str,
        data_summary: str
    ) -> Dict[str, Any]:
        """
        Create analysis plan based on query and data

        Args:
            query: Original user query
            analysis_type: Type of analysis requested
            data_summary: Summary of available data

        Returns:
            Analysis plan with methods and parameters
        """
        try:
            system_prompt = """당신은 부동산 데이터 분석 전문가입니다.
주어진 데이터와 분석 유형에 따라 최적의 분석 계획을 수립하세요.

사용 가능한 분석 도구:
- market_analyzer: 시장 현황 분석 (가격, 거래량, 수급)
- trend_analyzer: 시계열 트렌드 분석 (가격 변동, 패턴)
- comparative_analyzer: 지역/단지 비교 분석
- investment_evaluator: 투자 가치 평가 (ROI, 수익률)
- risk_assessor: 리스크 평가 (시장, 유동성, 규제)

JSON 형식으로 응답:
{
    "selected_methods": ["도구1", "도구2"],
    "analysis_sequence": "분석 순서 설명",
    "focus_areas": ["주요 분석 포인트"],
    "expected_insights": ["예상 인사이트"]
}"""

            user_prompt = f"""사용자 질의: {query}
분석 유형: {analysis_type}
데이터 요약: {data_summary}"""

            model = self.get_model("analysis")
            params = self.get_params()
            params["temperature"] = 0.3

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
            logger.error(f"LLM analysis plan failed: {e}")
            # Fallback to default plan
            return {
                "selected_methods": ["market_analyzer", "trend_analyzer"],
                "analysis_sequence": "기본 시장 분석 후 트렌드 분석",
                "focus_areas": ["시장 현황", "가격 동향"],
                "expected_insights": ["시장 상황 파악"]
            }

    async def extract_insights(
        self,
        analysis_results: Dict[str, Any],
        query: str
    ) -> Dict[str, Any]:
        """
        Extract insights from analysis results

        Args:
            analysis_results: Results from analysis tools
            query: Original query

        Returns:
            Insights and recommendations
        """
        try:
            system_prompt = """분석 결과를 바탕으로 핵심 인사이트와 추천사항을 도출하세요.

JSON 형식으로 응답:
{
    "key_insights": ["핵심 인사이트 1", "핵심 인사이트 2"],
    "recommendations": ["추천사항 1", "추천사항 2"],
    "risk_factors": ["리스크 요인 1", "리스크 요인 2"],
    "opportunities": ["기회 요인 1", "기회 요인 2"],
    "summary": "종합 요약"
}"""

            user_prompt = f"""원본 질의: {query}
분석 결과: {json.dumps(analysis_results, ensure_ascii=False, indent=2)}"""

            model = self.get_model("analysis")
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
            logger.error(f"LLM insight extraction failed: {e}")
            return {
                "key_insights": ["분석이 완료되었습니다"],
                "recommendations": [],
                "risk_factors": [],
                "opportunities": [],
                "summary": "데이터 분석 완료"
            }

    async def decide_next_action(
        self,
        analysis_complete: bool,
        has_insights: bool
    ) -> Dict[str, Any]:
        """
        Decide next action after analysis

        Args:
            analysis_complete: Whether analysis is complete
            has_insights: Whether insights were generated

        Returns:
            Next action decision
        """
        try:
            if analysis_complete and has_insights:
                return {
                    "next_action": "return_to_supervisor",
                    "reasoning": "분석 완료 및 인사이트 도출 완료"
                }
            elif analysis_complete and not has_insights:
                return {
                    "next_action": "direct_output",
                    "reasoning": "분석은 완료했으나 특별한 인사이트 없음"
                }
            else:
                return {
                    "next_action": "return_to_supervisor",
                    "reasoning": "추가 데이터 필요"
                }

        except Exception as e:
            logger.error(f"Next action decision failed: {e}")
            return {
                "next_action": "return_to_supervisor",
                "reasoning": "기본 처리"
            }


class AnalysisAgent:
    """
    Analysis Agent for data analysis and insight generation
    LangGraph 0.6+ compatible
    """

    def __init__(self, llm_context: LLMContext = None):
        self.llm_context = llm_context or create_default_llm_context()
        self.llm_client = AnalysisAgentLLM(self.llm_context)
        self.workflow = None
        self._build_graph()

    def _build_graph(self):
        """Build the analysis agent workflow"""
        self.workflow = StateGraph(AnalysisAgentState)

        # Add nodes
        self.workflow.add_node("understand_request", self.understand_request_node)
        self.workflow.add_node("prepare_data", self.prepare_data_node)
        self.workflow.add_node("create_analysis_plan", self.create_analysis_plan_node)
        self.workflow.add_node("execute_analysis", self.execute_analysis_node)
        self.workflow.add_node("synthesize_results", self.synthesize_results_node)
        self.workflow.add_node("generate_report", self.generate_report_node)
        self.workflow.add_node("decide_routing", self.decide_routing_node)

        # Add edges
        self.workflow.add_edge(START, "understand_request")
        self.workflow.add_edge("understand_request", "prepare_data")
        self.workflow.add_edge("prepare_data", "create_analysis_plan")
        self.workflow.add_edge("create_analysis_plan", "execute_analysis")
        self.workflow.add_edge("execute_analysis", "synthesize_results")
        self.workflow.add_edge("synthesize_results", "generate_report")
        self.workflow.add_edge("generate_report", "decide_routing")
        self.workflow.add_edge("decide_routing", END)

        # Compile the graph
        self.app = self.workflow.compile()
        logger.info("Analysis Agent workflow built successfully")

    async def understand_request_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Understand the analysis request

        Args:
            state: Current state

        Returns:
            Updated state
        """
        query = state["original_query"]
        analysis_type = state.get("analysis_type", "comprehensive")
        todos = state.get("todos", [])
        parent_todo_id = state.get("parent_todo_id")

        logger.info(f"Understanding analysis request: {analysis_type}")
        logger.debug(f"[NODE] understand_request - Query: {query[:50]}...")

        # Update TODO if exists
        if parent_todo_id:
            parent_todo = find_todo(todos, todo_id=parent_todo_id)
            if parent_todo:
                # Add subtodos for analysis workflow
                todo_counter = state.get("todo_counter", 0)
                subtodos = [
                    create_todo_dict(f"ana_sub_{todo_counter}", "agent", "Understand request", "completed"),
                    create_todo_dict(f"ana_sub_{todo_counter + 1}", "agent", "Prepare data", "pending"),
                    create_todo_dict(f"ana_sub_{todo_counter + 2}", "agent", "Create analysis plan", "pending"),
                    create_todo_dict(f"ana_sub_{todo_counter + 3}", "agent", "Execute analysis", "pending"),
                    create_todo_dict(f"ana_sub_{todo_counter + 4}", "agent", "Synthesize results", "pending"),
                    create_todo_dict(f"ana_sub_{todo_counter + 5}", "agent", "Generate report", "pending")
                ]
                parent_todo["subtodos"] = subtodos
                state["todo_counter"] = todo_counter + 6
                logger.debug(f"[TODO] Added {len(subtodos)} subtodos for analysis")

        return {
            "status": "analyzing",
            "execution_step": "understanding_request",
            "current_task": "Understanding analysis requirements",
            "todos": todos
        }

    async def prepare_data_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare and validate input data

        Args:
            state: Current state

        Returns:
            Updated state with prepared data
        """
        input_data = state.get("input_data", {})
        todos = state.get("todos", [])
        parent_todo_id = state.get("parent_todo_id")

        logger.info("Preparing data for analysis")
        logger.debug(f"[NODE] prepare_data - Data sources: {list(input_data.keys())}")

        # Update TODO status
        if parent_todo_id:
            parent_todo = find_todo(todos, todo_id=parent_todo_id)
            if parent_todo and "subtodos" in parent_todo:
                for subtodo in parent_todo["subtodos"]:
                    if "Prepare data" in subtodo.get("task", ""):
                        todos = update_todo_status(todos, subtodo["id"], "in_progress")
                        break

        # Validate and prepare data
        prepared_data = {}
        data_count = 0

        for source, data in input_data.items():
            if isinstance(data, list):
                prepared_data[source] = data
                data_count += len(data)
            elif isinstance(data, dict):
                prepared_data[source] = [data]
                data_count += 1

        # Calculate data metrics
        data_metrics = {
            "total_records": data_count,
            "data_sources": len(prepared_data),
            "has_sufficient_data": data_count > 0
        }

        # Create data summary
        data_summary = f"{data_count}개 데이터, {len(prepared_data)}개 소스"

        # Update TODO status
        if parent_todo_id:
            parent_todo = find_todo(todos, todo_id=parent_todo_id)
            if parent_todo and "subtodos" in parent_todo:
                for subtodo in parent_todo["subtodos"]:
                    if "Prepare data" in subtodo.get("task", ""):
                        todos = update_todo_status(todos, subtodo["id"], "completed")
                        break

        return {
            "prepared_data": prepared_data,
            "data_validation": {"status": "valid", "issues": []},
            "data_metrics": data_metrics,
            "execution_step": "data_prepared",
            "current_task": "Creating analysis plan",
            "todos": todos,
            "analysis_summary": data_summary  # For LLM use
        }

    async def create_analysis_plan_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create analysis plan using LLM

        Args:
            state: Current state

        Returns:
            Updated state with analysis plan
        """
        query = state["original_query"]
        analysis_type = state.get("analysis_type", "comprehensive")
        data_summary = state.get("analysis_summary", "데이터 준비 완료")
        todos = state.get("todos", [])
        parent_todo_id = state.get("parent_todo_id")

        logger.info(f"Creating analysis plan for {analysis_type}")

        # Update TODO status
        if parent_todo_id:
            parent_todo = find_todo(todos, todo_id=parent_todo_id)
            if parent_todo and "subtodos" in parent_todo:
                for subtodo in parent_todo["subtodos"]:
                    if "Create analysis plan" in subtodo.get("task", ""):
                        todos = update_todo_status(todos, subtodo["id"], "in_progress")
                        break

        # Create analysis plan using LLM
        plan = await self.llm_client.create_analysis_plan(query, analysis_type, data_summary)

        logger.debug(f"[LLM] Analysis plan created - methods: {plan.get('selected_methods')}")

        # Update TODO status
        if parent_todo_id:
            parent_todo = find_todo(todos, todo_id=parent_todo_id)
            if parent_todo and "subtodos" in parent_todo:
                for subtodo in parent_todo["subtodos"]:
                    if "Create analysis plan" in subtodo.get("task", ""):
                        todos = update_todo_status(todos, subtodo["id"], "completed")
                        break

        return {
            "analysis_plan": plan,
            "selected_methods": plan.get("selected_methods", ["market_analyzer"]),
            "analysis_parameters": {
                "focus_areas": plan.get("focus_areas", []),
                "depth": "comprehensive" if analysis_type == "comprehensive" else "basic"
            },
            "execution_step": "plan_created",
            "current_task": "Executing analysis",
            "todos": todos
        }

    async def execute_analysis_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute selected analysis methods

        Args:
            state: Current state

        Returns:
            Updated state with analysis results
        """
        selected_methods = state.get("selected_methods", ["market_analyzer"])
        prepared_data = state.get("prepared_data", {})
        analysis_parameters = state.get("analysis_parameters", {})
        todos = state.get("todos", [])
        parent_todo_id = state.get("parent_todo_id")

        logger.info(f"Executing analysis methods: {selected_methods}")
        logger.debug(f"[NODE] execute_analysis - Methods: {selected_methods}")

        # Update TODO status
        if parent_todo_id:
            parent_todo = find_todo(todos, todo_id=parent_todo_id)
            if parent_todo and "subtodos" in parent_todo:
                for subtodo in parent_todo["subtodos"]:
                    if "Execute analysis" in subtodo.get("task", ""):
                        todos = update_todo_status(todos, subtodo["id"], "in_progress")
                        break

        # Execute each analysis method
        analysis_results = {}
        tool_usage = {}

        for method_name in selected_methods:
            tool = analysis_tool_registry.get(method_name)
            if tool:
                try:
                    result = await tool.execute(prepared_data, analysis_parameters)
                    analysis_results[method_name] = result
                    tool_usage[method_name] = 1
                    logger.info(f"Analysis method {method_name} completed")
                except Exception as e:
                    logger.error(f"Analysis method {method_name} failed: {e}")
                    analysis_results[method_name] = {
                        "status": "error",
                        "error": str(e)
                    }
            else:
                logger.warning(f"Analysis method {method_name} not found")

        # Store results by type
        result_mapping = {
            "market_analyzer": "market_analysis",
            "trend_analyzer": "trend_analysis",
            "comparative_analyzer": "comparative_analysis",
            "investment_evaluator": "investment_analysis",
            "risk_assessor": "risk_analysis"
        }

        state_updates = {}
        for method, result in analysis_results.items():
            if method in result_mapping:
                state_updates[result_mapping[method]] = result

        # Update TODO status
        if parent_todo_id:
            parent_todo = find_todo(todos, todo_id=parent_todo_id)
            if parent_todo and "subtodos" in parent_todo:
                for subtodo in parent_todo["subtodos"]:
                    if "Execute analysis" in subtodo.get("task", ""):
                        todos = update_todo_status(todos, subtodo["id"], "completed")
                        break

        return {
            **state_updates,
            "tool_usage": tool_usage,
            "execution_step": "analysis_executed",
            "current_task": "Synthesizing results",
            "todos": todos
        }

    async def synthesize_results_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesize analysis results and extract insights

        Args:
            state: Current state

        Returns:
            Updated state with insights
        """
        query = state["original_query"]
        todos = state.get("todos", [])
        parent_todo_id = state.get("parent_todo_id")

        logger.info("Synthesizing analysis results")

        # Update TODO status
        if parent_todo_id:
            parent_todo = find_todo(todos, todo_id=parent_todo_id)
            if parent_todo and "subtodos" in parent_todo:
                for subtodo in parent_todo["subtodos"]:
                    if "Synthesize results" in subtodo.get("task", ""):
                        todos = update_todo_status(todos, subtodo["id"], "in_progress")
                        break

        # Collect all analysis results
        analysis_results = {}
        for key in ["market_analysis", "trend_analysis", "comparative_analysis",
                   "investment_analysis", "risk_analysis"]:
            if key in state and state[key]:
                analysis_results[key] = state[key]

        # Extract insights using LLM
        if analysis_results:
            insights_data = await self.llm_client.extract_insights(analysis_results, query)

            insights = insights_data.get("key_insights", [])
            recommendations = insights_data.get("recommendations", [])
            risk_factors = insights_data.get("risk_factors", [])
            opportunities = insights_data.get("opportunities", [])
            summary = insights_data.get("summary", "분석 완료")
        else:
            insights = ["분석 데이터가 없습니다"]
            recommendations = []
            risk_factors = []
            opportunities = []
            summary = "분석할 데이터가 부족합니다"

        logger.debug(f"[SYNTHESIS] Generated {len(insights)} insights, {len(recommendations)} recommendations")

        # Calculate confidence scores
        confidence_scores = {
            "overall": 0.75,  # Default confidence
            "data_quality": 0.8 if len(analysis_results) > 2 else 0.5,
            "insight_quality": 0.9 if len(insights) > 3 else 0.6
        }

        # Update TODO status
        if parent_todo_id:
            parent_todo = find_todo(todos, todo_id=parent_todo_id)
            if parent_todo and "subtodos" in parent_todo:
                for subtodo in parent_todo["subtodos"]:
                    if "Synthesize results" in subtodo.get("task", ""):
                        todos = update_todo_status(todos, subtodo["id"], "completed")
                        break

        return {
            "insights": insights,
            "recommendations": recommendations,
            "risk_factors": risk_factors,
            "opportunities": opportunities,
            "analysis_summary": summary,
            "confidence_scores": confidence_scores,
            "execution_step": "synthesis_complete",
            "current_task": "Generating report",
            "todos": todos
        }

    async def generate_report_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate final analysis report

        Args:
            state: Current state

        Returns:
            Updated state with final report
        """
        todos = state.get("todos", [])
        parent_todo_id = state.get("parent_todo_id")

        logger.info("Generating final analysis report")

        # Update TODO status
        if parent_todo_id:
            parent_todo = find_todo(todos, todo_id=parent_todo_id)
            if parent_todo and "subtodos" in parent_todo:
                for subtodo in parent_todo["subtodos"]:
                    if "Generate report" in subtodo.get("task", ""):
                        todos = update_todo_status(todos, subtodo["id"], "in_progress")
                        break

        # Compile final report
        final_report = {
            "summary": state.get("analysis_summary", "분석 완료"),
            "analysis_type": state.get("analysis_type", "comprehensive"),
            "key_findings": {
                "insights": state.get("insights", []),
                "recommendations": state.get("recommendations", []),
                "risks": state.get("risk_factors", []),
                "opportunities": state.get("opportunities", [])
            },
            "detailed_analysis": {},
            "metrics": {},
            "confidence": state.get("confidence_scores", {}),
            "timestamp": datetime.now().isoformat()
        }

        # Add detailed analysis results
        for analysis_type in ["market_analysis", "trend_analysis", "comparative_analysis",
                             "investment_analysis", "risk_analysis"]:
            if analysis_type in state and state[analysis_type]:
                result = state[analysis_type]
                if result.get("status") == "success":
                    final_report["detailed_analysis"][analysis_type] = result.get("analysis", {})
                    if "metrics" in result:
                        final_report["metrics"][analysis_type] = result["metrics"]

        # Extract key metrics for visualization
        key_metrics = {}
        if "market_analysis" in state and state["market_analysis"]:
            market_data = state["market_analysis"]
            if "metrics" in market_data:
                key_metrics["average_price"] = market_data["metrics"].get("average_price", "N/A")
                key_metrics["market_heat_index"] = market_data["metrics"].get("market_heat_index", 50)

        if "trend_analysis" in state and state["trend_analysis"]:
            trend_data = state["trend_analysis"]
            if "trends" in trend_data:
                key_metrics["price_change"] = trend_data["trends"].get("price_change", "N/A")

        # Update TODO status
        if parent_todo_id:
            parent_todo = find_todo(todos, todo_id=parent_todo_id)
            if parent_todo and "subtodos" in parent_todo:
                for subtodo in parent_todo["subtodos"]:
                    if "Generate report" in subtodo.get("task", ""):
                        todos = update_todo_status(todos, subtodo["id"], "completed")
                        break

        return {
            "final_report": final_report,
            "key_metrics": key_metrics,
            "visualization_data": {
                "charts_available": ["price_trend", "market_comparison", "risk_matrix"],
                "data_points": len(state.get("prepared_data", {}))
            },
            "status": "completed",
            "execution_step": "report_generated",
            "current_task": "Deciding routing",
            "todos": todos
        }

    async def decide_routing_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decide how to route the results

        Args:
            state: Current state

        Returns:
            Updated state with routing decision
        """
        logger.info("Deciding routing for analysis results")

        # Check if analysis was successful
        has_report = state.get("final_report") is not None
        has_insights = len(state.get("insights", [])) > 0

        # Decide next action
        decision = await self.llm_client.decide_next_action(has_report, has_insights)

        logger.debug(f"[ROUTING] Decision: {decision.get('next_action')} - {decision.get('reasoning')}")

        return {
            "next_action": decision.get("next_action", "return_to_supervisor"),
            "routing_reason": decision.get("reasoning", "Analysis complete"),
            "status": "completed"
        }


# For backwards compatibility
def create_analysis_agent(llm_context: LLMContext = None) -> AnalysisAgent:
    """
    Factory function to create analysis agent

    Args:
        llm_context: Optional LLM context

    Returns:
        Configured AnalysisAgent instance
    """
    return AnalysisAgent(llm_context=llm_context)


if __name__ == "__main__":
    import asyncio

    async def test_analysis_agent():
        # Example usage
        agent = AnalysisAgent()

        # Sample input data
        input_data = {
            "original_query": "강남구 아파트 시장 분석해줘",
            "analysis_type": "comprehensive",
            "input_data": {
                "real_estate_search": [
                    {"title": "래미안 강남", "price": "25억", "region": "강남구"},
                    {"title": "아크로리버뷰", "price": "30억", "region": "강남구"}
                ],
                "loan_search": [
                    {"product": "주택담보대출", "rate": "3.5%"}
                ]
            },
            "shared_context": {},
            "chat_session_id": "test_session"
        }

        result = await agent.app.ainvoke(input_data)
        print(json.dumps(result.get("final_report", {}), ensure_ascii=False, indent=2))

    asyncio.run(test_analysis_agent())