"""
Real Estate Supervisor
Main orchestrator for the real estate chatbot system
Manages: Intent Analysis → Planning → Execution → Evaluation

MODERNIZED VERSION:
- Uses START/END nodes (LangGraph 0.6.7+ syntax)
- Removed deprecated set_entry_point()
- Extracted retry logic to class method
- Added configurable max_retries
- Enhanced type hints
"""

from typing import Dict, Any, Type, Optional, Literal
from langgraph.graph import StateGraph, START, END
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

    Modern LangGraph 0.6.7+ Implementation with START/END nodes

    Workflow:
        START → Intent Analysis → Plan Building → Agent Execution → Result Evaluation → END
        (with conditional retry loop from evaluation back to execution)
    """

    def __init__(
        self,
        agent_name: str = "real_estate_supervisor",
        checkpoint_dir: Optional[str] = None,
        max_retries: int = 2
    ):
        """
        Initialize Real Estate Supervisor

        Args:
            agent_name: Name of the supervisor (default: "real_estate_supervisor")
            checkpoint_dir: Directory for checkpoints
            max_retries: Maximum number of retry attempts (default: 2)
        """
        self.max_retries = max_retries
        super().__init__(agent_name, checkpoint_dir)
        logger.info(f"RealEstateSupervisor initialized (max_retries={max_retries})")

    def _get_state_schema(self) -> Type:
        """
        Get the state schema for this supervisor

        Returns:
            SupervisorState type
        """
        return SupervisorState

    def _should_retry(self, state: Dict[str, Any]) -> Literal["retry", "end"]:
        """
        Determine if agent execution should be retried

        This method is used as a routing function for conditional edges.
        It checks the evaluation results and decides whether to retry
        failed agents or proceed to completion.

        Args:
            state: Current state dictionary containing evaluation results

        Returns:
            "retry" if retry is needed, "end" to finish workflow
        """
        evaluation = state.get("evaluation", {})
        needs_retry = evaluation.get("needs_retry", False)

        # Get retry count from state
        retry_count = state.get("retry_count", 0)

        if needs_retry and retry_count < self.max_retries:
            logger.info(
                f"Retrying agent execution "
                f"(attempt {retry_count + 1}/{self.max_retries})"
            )
            return "retry"
        else:
            if needs_retry:
                logger.warning(
                    f"Max retries ({self.max_retries}) reached, "
                    f"proceeding with current results"
                )
            return "end"

    def _build_graph(self) -> None:
        """
        Build the LangGraph workflow for supervisor using modern syntax

        Modern Features:
        - Uses START node instead of set_entry_point()
        - Explicit END node in conditional edges
        - Clean separation of routing logic in _should_retry method

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

        # Add edges with explicit START and END
        # Modern syntax: START node defines entry point
        self.workflow.add_edge(START, "analyze_intent")

        # Sequential flow edges
        self.workflow.add_edge("analyze_intent", "build_plan")
        self.workflow.add_edge("build_plan", "execute_agents")
        self.workflow.add_edge("execute_agents", "evaluate_results")

        # Conditional edge for retry logic
        # Routes to either retry (execute_agents) or end (END)
        self.workflow.add_conditional_edges(
            "evaluate_results",
            self._should_retry,  # Use class method for better organization
            {
                "retry": "execute_agents",
                "end": END
            }
        )

        # Note: set_entry_point() is deprecated and removed
        # START node serves the same purpose with clearer semantics

        logger.info("Supervisor workflow graph built successfully with modern syntax")

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
            chat_session_id=input_data.get("chat_session_id", "default_session"),
            query=input_data.get("query", ""),
            chat_thread_id=input_data.get("chat_thread_id"),
            db_user_id=input_data.get("db_user_id"),
            db_session_id=input_data.get("db_session_id")
        )

    async def process_query(
        self,
        query: str,
        chat_user_ref: str = "default_user",
        chat_session_id: str = "default_session",
        db_user_id: int = None,
        db_session_id: int = None,
        config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        High-level method to process user query

        Args:
            query: User query string
            chat_user_ref: Chatbot user reference
            chat_session_id: Chatbot session ID
            db_user_id: Database user ID (optional)
            db_session_id: Database session ID (optional)
            config: Optional execution config

        Returns:
            Final output dictionary
        """
        input_data = {
            "query": query,
            "chat_user_ref": chat_user_ref,
            "chat_session_id": chat_session_id,
            "db_user_id": db_user_id,
            "db_session_id": db_session_id
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
async def run_supervisor_test(query: str) -> Dict[str, Any]:
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