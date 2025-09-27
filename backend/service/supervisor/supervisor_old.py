"""
Real Estate Supervisor
Main orchestrator for the real estate chatbot system
Manages: Intent Analysis → Planning → Execution → Evaluation
"""

from typing import Dict, Any, Type, Optional
from langgraph.graph import StateGraph, END
from langgraph.runtime import Runtime
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.base_agent import BaseAgent
from core.states import SupervisorState
from core.context import AgentContext

from .intent_analyzer import analyze_intent_node
from .plan_builder import build_plan_node
from .execution_coordinator import execute_agents_node
from .result_evaluator import evaluate_results_node


logger = logging.getLogger(__name__)


class RealEstateSupervisor(BaseAgent):
    """
    Main Supervisor for Real Estate Chatbot
    Orchestrates the entire workflow from user query to final response

    Workflow:
        User Query → Intent Analysis → Plan Building → Agent Execution → Result Evaluation → Final Output
    """

    def __init__(self, agent_name: str = "real_estate_supervisor", checkpoint_dir: Optional[str] = None):
        """
        Initialize Real Estate Supervisor

        Args:
            agent_name: Name of the supervisor (default: "real_estate_supervisor")
            checkpoint_dir: Directory for checkpoints
        """
        super().__init__(agent_name, checkpoint_dir)
        logger.info("RealEstateSupervisor initialized")

    def _get_state_schema(self) -> Type:
        """
        Get the state schema for this supervisor

        Returns:
            SupervisorState type
        """
        return SupervisorState

    def _build_graph(self):
        """
        Build the LangGraph workflow for supervisor

        Graph Structure:
            START
              ↓
            analyze_intent (의도 분석)
              ↓
            build_plan (계획 수립)
              ↓
            execute_agents (Agent 실행)
              ↓
            evaluate_results (결과 평가)
              ↓
            Should Retry? ← (재시도 필요 시 execute_agents로)
              ↓ No
            END
        """
        self.workflow = StateGraph(
            state_schema=SupervisorState,
            context_schema=AgentContext
        )

        # Add nodes
        self.workflow.add_node("analyze_intent", analyze_intent_node)
        self.workflow.add_node("build_plan", build_plan_node)
        self.workflow.add_node("execute_agents", execute_agents_node)
        self.workflow.add_node("evaluate_results", evaluate_results_node)

        # Add sequential edges
        self.workflow.add_edge("analyze_intent", "build_plan")
        self.workflow.add_edge("build_plan", "execute_agents")
        self.workflow.add_edge("execute_agents", "evaluate_results")

        # Add conditional edge for retry logic
        def should_retry(state: Dict[str, Any]) -> str:
            """
            Determine if agent execution should be retried

            Args:
                state: Current state

            Returns:
                "retry" if retry is needed, "end" otherwise
            """
            evaluation = state.get("evaluation", {})
            needs_retry = evaluation.get("needs_retry", False)

            # Limit retry attempts
            retry_count = state.get("retry_count", 0)
            max_retries = 2

            if needs_retry and retry_count < max_retries:
                logger.info(f"Retrying agent execution (attempt {retry_count + 1}/{max_retries})")
                return "retry"
            else:
                return "end"

        self.workflow.add_conditional_edges(
            "evaluate_results",
            should_retry,
            {
                "retry": "execute_agents",
                "end": END
            }
        )

        # Set entry point
        self.workflow.set_entry_point("analyze_intent")

        logger.info("Supervisor workflow graph built successfully")

    async def _validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data before processing

        Args:
            input_data: Input data to validate

        Returns:
            True if valid, False otherwise
        """
        # Check required field
        if "query" not in input_data:
            self.logger.error("Missing required field: query")
            return False

        if not isinstance(input_data["query"], str):
            self.logger.error("Query must be a string")
            return False

        if len(input_data["query"].strip()) == 0:
            self.logger.error("Query cannot be empty")
            return False

        return True

    def _create_initial_state(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create initial state from input data

        Args:
            input_data: Input data from user

        Returns:
            Initial state dictionary
        """
        from core.states import create_supervisor_initial_state

        return create_supervisor_initial_state(
            query=input_data.get("query", "")
        )

    async def process_query(
        self,
        query: str,
        user_id: str = "default_user",
        session_id: str = "default_session",
        config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        High-level method to process user query

        Args:
            query: User query string
            user_id: User identifier
            session_id: Session identifier
            config: Optional execution config

        Returns:
            Final output dictionary
        """
        input_data = {
            "query": query,
            "user_id": user_id,
            "session_id": session_id
        }

        result = await self.execute(input_data, config)

        if result["status"] == "success":
            return result["data"].get("final_output", {})
        else:
            return {
                "error": result.get("error", "Unknown error"),
                "status": "failed"
            }


# Convenience function for quick testing
async def run_supervisor_test(query: str):
    """
    Test function to run supervisor with a query

    Args:
        query: User query to process

    Returns:
        Final output
    """
    supervisor = RealEstateSupervisor()

    result = await supervisor.process_query(
        query=query,
        user_id="test_user",
        session_id="test_session"
    )

    return result


if __name__ == "__main__":
    import asyncio

    async def main():
        # Test supervisor
        test_query = "강남역 근처 30평대 아파트 매매 시세 알려줘"

        print(f"Testing supervisor with query: {test_query}")
        print("-" * 80)

        result = await run_supervisor_test(test_query)

        print("\nResult:")
        print(result)

    asyncio.run(main())