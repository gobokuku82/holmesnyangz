"""
Real Estate Supervisor
Main orchestrator for the real estate chatbot system
Manages: Intent Analysis → Planning → Execution → Evaluation

ENHANCED VERSION:
- Integrated caching system
- Better error handling
- Performance monitoring
- Improved retry logic
"""

from typing import Dict, Any, Type, Optional, Literal
from langgraph.graph import StateGraph, START, END
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.base_agent import BaseAgent
from core.states import SupervisorState
from core.context import AgentContext
from utils.cache_manager import QueryCache
from utils.metrics import MetricsCollector

from .intent_analyzer import analyze_intent_node
from .plan_builder import build_plan_node
from .execution_coordinator import execute_agents_node
from .result_evaluator import evaluate_results_node

logger = logging.getLogger(__name__)


class RealEstateSupervisor(BaseAgent):
    """
    Enhanced Main Supervisor for Real Estate Chatbot
    
    Features:
    - Query result caching
    - Performance metrics collection
    - Improved error handling
    - Configurable retry logic
    
    Workflow:
        START → Intent Analysis → Plan Building → Agent Execution 
        → Result Evaluation → END
        (with conditional retry loop from evaluation back to execution)
    """

    def __init__(
        self,
        agent_name: str = "real_estate_supervisor",
        checkpoint_dir: Optional[str] = None,
        max_retries: int = 2,
        enable_cache: bool = True,
        cache_ttl_seconds: int = 1800,
        enable_metrics: bool = True
    ):
        """
        Initialize Enhanced Real Estate Supervisor

        Args:
            agent_name: Name of the supervisor
            checkpoint_dir: Directory for checkpoints
            max_retries: Maximum number of retry attempts
            enable_cache: Enable query result caching
            cache_ttl_seconds: Cache TTL in seconds
            enable_metrics: Enable performance metrics collection
        """
        self.max_retries = max_retries
        
        # Initialize caching
        self.cache = QueryCache() if enable_cache else None
        self.cache_enabled = enable_cache
        self.cache_ttl = cache_ttl_seconds
        
        # Initialize metrics
        self.metrics = MetricsCollector() if enable_metrics else None
        self.metrics_enabled = enable_metrics
        
        # Statistics
        self.total_queries = 0
        self.successful_queries = 0
        self.failed_queries = 0
        self.cache_hits = 0
        
        super().__init__(agent_name, checkpoint_dir)
        
        logger.info(
            f"RealEstateSupervisor initialized: "
            f"max_retries={max_retries}, "
            f"cache={'enabled' if enable_cache else 'disabled'}, "
            f"metrics={'enabled' if enable_metrics else 'disabled'}"
        )

    def _get_state_schema(self) -> Type:
        """Get the state schema for this supervisor"""
        return SupervisorState

    def _should_retry(self, state: Dict[str, Any]) -> Literal["retry", "end"]:
        """
        Determine if agent execution should be retried
        Enhanced with better retry logic and logging

        Args:
            state: Current state dictionary containing evaluation results

        Returns:
            "retry" if retry is needed, "end" to finish workflow
        """
        evaluation = state.get("evaluation", {})
        needs_retry = evaluation.get("needs_retry", False)
        retry_count = state.get("retry_count", 0)
        failed_agents = state.get("failed_agents", [])

        if needs_retry and retry_count < self.max_retries:
            # Check if we have specific agents to retry
            retry_agents = evaluation.get("retry_agents", [])
            
            logger.info(
                f"Retrying agent execution "
                f"(attempt {retry_count + 1}/{self.max_retries})"
            )
            
            if retry_agents:
                logger.info(f"Agents to retry: {retry_agents}")
            
            # Record retry metric
            if self.metrics:
                self.metrics.record_event("supervisor_retry", {
                    "retry_count": retry_count + 1,
                    "failed_agents": failed_agents
                })
            
            return "retry"
        else:
            if needs_retry:
                logger.warning(
                    f"Max retries ({self.max_retries}) reached, "
                    f"proceeding with current results. "
                    f"Failed agents: {failed_agents}"
                )
                
                # Record max retries reached
                if self.metrics:
                    self.metrics.record_event("supervisor_max_retries_reached", {
                        "failed_agents": failed_agents
                    })
            
            return "end"

    def _build_graph(self) -> None:
        """
        Build the LangGraph workflow for supervisor using modern syntax

        Enhanced with wrapped nodes for metrics collection
        """
        self.workflow = StateGraph(
            state_schema=SupervisorState,
            context_schema=AgentContext
        )

        # Wrap nodes with metrics collection if enabled
        if self.metrics_enabled:
            analyze_intent = self._wrap_with_metrics("analyze_intent", analyze_intent_node)
            build_plan = self._wrap_with_metrics("build_plan", build_plan_node)
            execute_agents = self._wrap_with_metrics("execute_agents", execute_agents_node)
            evaluate_results = self._wrap_with_metrics("evaluate_results", evaluate_results_node)
        else:
            analyze_intent = analyze_intent_node
            build_plan = build_plan_node
            execute_agents = execute_agents_node
            evaluate_results = evaluate_results_node

        # Add nodes
        self.workflow.add_node("analyze_intent", analyze_intent)
        self.workflow.add_node("build_plan", build_plan)
        self.workflow.add_node("execute_agents", execute_agents)
        self.workflow.add_node("evaluate_results", evaluate_results)

        # Add edges with explicit START and END
        self.workflow.add_edge(START, "analyze_intent")
        self.workflow.add_edge("analyze_intent", "build_plan")
        self.workflow.add_edge("build_plan", "execute_agents")
        self.workflow.add_edge("execute_agents", "evaluate_results")

        # Conditional edge for retry logic
        self.workflow.add_conditional_edges(
            "evaluate_results",
            self._should_retry,
            {
                "retry": "execute_agents",
                "end": END
            }
        )

        logger.info("Enhanced supervisor workflow graph built successfully")

    def _wrap_with_metrics(self, node_name: str, node_func):
        """
        Wrap a node function with metrics collection

        Args:
            node_name: Name of the node for metrics
            node_func: Original node function

        Returns:
            Wrapped function with metrics
        """
        async def wrapped(state: Dict[str, Any], runtime: Any) -> Dict[str, Any]:
            start_time = datetime.now()
            
            try:
                result = await node_func(state, runtime)
                
                # Record success metric
                duration = (datetime.now() - start_time).total_seconds()
                self.metrics.record_latency(node_name, duration)
                self.metrics.record_success(node_name, True)
                
                return result
                
            except Exception as e:
                # Record failure metric
                duration = (datetime.now() - start_time).total_seconds()
                self.metrics.record_latency(node_name, duration)
                self.metrics.record_success(node_name, False)
                self.metrics.record_error(node_name, str(e))
                
                raise
        
        return wrapped

    async def _validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data before processing
        Enhanced with better validation

        Args:
            input_data: Input data to validate

        Returns:
            True if valid, False otherwise
        """
        # Check required field
        if "query" not in input_data:
            self.logger.error("Missing required field: query")
            return False

        query = input_data["query"]
        
        if not isinstance(query, str):
            self.logger.error("Query must be a string")
            return False

        if len(query.strip()) == 0:
            self.logger.error("Query cannot be empty")
            return False
        
        # Check query length
        if len(query) > 1000:
            self.logger.error("Query too long (max 1000 characters)")
            return False
        
        # Validate user_id if provided
        if "user_id" in input_data:
            if not isinstance(input_data["user_id"], str):
                self.logger.error("user_id must be a string")
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
            query=input_data.get("query", ""),
            max_retries=self.max_retries
        )

    async def process_query(
        self,
        query: str,
        user_id: str = "default_user",
        session_id: str = "default_session",
        config: Optional[Dict] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Enhanced method to process user query with caching and metrics

        Args:
            query: User query string
            user_id: User identifier
            session_id: Session identifier
            config: Optional execution config
            use_cache: Whether to use cache for this query

        Returns:
            Final output dictionary
        """
        self.total_queries += 1
        start_time = datetime.now()
        
        try:
            # Check cache first if enabled
            if self.cache and use_cache:
                cached_result = await self.cache.get_cached_result(
                    query=query,
                    user_id=user_id,
                    session_id=session_id
                )
                
                if cached_result:
                    self.cache_hits += 1
                    logger.info(f"Cache hit for query: {query[:50]}...")
                    
                    # Record cache hit metric
                    if self.metrics:
                        self.metrics.record_event("cache_hit", {
                            "user_id": user_id,
                            "query_length": len(query)
                        })
                    
                    return cached_result

            # Process query normally
            input_data = {
                "query": query,
                "user_id": user_id,
                "session_id": session_id
            }

            result = await self.execute(input_data, config)

            if result["status"] == "success":
                self.successful_queries += 1
                final_output = result["data"].get("final_output", {})
                
                # Cache successful result
                if self.cache and use_cache:
                    await self.cache.cache_result(
                        query=query,
                        result=final_output,
                        user_id=user_id,
                        ttl_seconds=self.cache_ttl,
                        session_id=session_id
                    )
                    logger.info(f"Cached result for query: {query[:50]}...")
                
                # Record success metrics
                if self.metrics:
                    duration = (datetime.now() - start_time).total_seconds()
                    self.metrics.record_latency("query_processing", duration)
                    self.metrics.record_success("query_processing", True)
                
                return final_output
            else:
                self.failed_queries += 1
                
                # Record failure metrics
                if self.metrics:
                    duration = (datetime.now() - start_time).total_seconds()
                    self.metrics.record_latency("query_processing", duration)
                    self.metrics.record_success("query_processing", False)
                    self.metrics.record_error("query_processing", result.get("error"))
                
                return {
                    "error": result.get("error", "Unknown error"),
                    "status": "failed"
                }
                
        except Exception as e:
            self.failed_queries += 1
            logger.error(f"Query processing failed: {e}", exc_info=True)
            
            # Record exception metrics
            if self.metrics:
                duration = (datetime.now() - start_time).total_seconds()
                self.metrics.record_latency("query_processing", duration)
                self.metrics.record_success("query_processing", False)
                self.metrics.record_error("query_processing", str(e))
            
            return {
                "error": f"Processing failed: {str(e)}",
                "status": "error"
            }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get supervisor statistics

        Returns:
            Dictionary with statistics
        """
        stats = {
            "total_queries": self.total_queries,
            "successful_queries": self.successful_queries,
            "failed_queries": self.failed_queries,
            "success_rate": (
                self.successful_queries / self.total_queries 
                if self.total_queries > 0 else 0
            ),
            "cache_hits": self.cache_hits,
            "cache_hit_rate": (
                self.cache_hits / self.total_queries 
                if self.total_queries > 0 else 0
            )
        }
        
        # Add cache statistics
        if self.cache:
            stats["cache_stats"] = self.cache.get_stats()
        
        # Add metrics statistics
        if self.metrics:
            stats["metrics"] = self.metrics.get_summary()
        
        return stats

    async def clear_cache(self):
        """Clear the query cache"""
        if self.cache:
            await self.cache.cache.clear()
            logger.info("Query cache cleared")

    async def invalidate_user_cache(self, user_id: str):
        """
        Invalidate cache for a specific user

        Args:
            user_id: User identifier
        """
        if self.cache:
            await self.cache.invalidate_user_cache(user_id)
            logger.info(f"Cache invalidated for user: {user_id}")


# Convenience function for quick testing
async def run_supervisor_test(
    query: str,
    enable_cache: bool = True,
    enable_metrics: bool = True
) -> Dict[str, Any]:
    """
    Test function to run supervisor with a query

    Args:
        query: User query to process
        enable_cache: Enable caching
        enable_metrics: Enable metrics

    Returns:
        Final output
    """
    supervisor = RealEstateSupervisor(
        enable_cache=enable_cache,
        enable_metrics=enable_metrics
    )

    result = await supervisor.process_query(
        query=query,
        user_id="test_user",
        session_id="test_session"
    )
    
    # Print statistics
    stats = supervisor.get_statistics()
    logger.info(f"Supervisor statistics: {stats}")

    return result


if __name__ == "__main__":
    import asyncio

    async def main():
        # Test supervisor
        test_query = "강남역 근처 30평대 아파트 매매 시세 알려줘"

        print(f"Testing enhanced supervisor with query: {test_query}")
        print("-" * 80)

        result = await run_supervisor_test(test_query)

        print("\nResult:")
        print(result)

    asyncio.run(main())
