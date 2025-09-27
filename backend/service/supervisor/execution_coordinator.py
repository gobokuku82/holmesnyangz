"""
Execution Coordinator Node
Executes agents according to the execution plan
"""

from typing import Dict, Any, List
from langgraph.runtime import Runtime
import logging
import asyncio


logger = logging.getLogger(__name__)


def get_agent(agent_name: str):
    """
    Dynamically import and return agent instance

    Args:
        agent_name: Name of the agent to import

    Returns:
        Agent instance

    Note:
        This is a placeholder. Actual agents will be implemented separately.
        For now, returns a mock agent for testing.
    """
    logger.info(f"Loading agent: {agent_name}")

    # TODO: Implement actual agent loading
    # from service.agents.property_search import PropertySearchAgent
    # from service.agents.market_analysis import MarketAnalysisAgent
    # etc.

    # For now, return a mock agent
    class MockAgent:
        def __init__(self, name: str):
            self.name = name

        async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
            """Mock agent execution"""
            logger.info(f"Mock agent {self.name} executing with params: {params}")
            return {
                "status": "success",
                "agent": self.name,
                "data": f"Mock result from {self.name}",
                "params": params
            }

    return MockAgent(agent_name)


async def execute_agent(agent_config: Dict[str, Any], ctx: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    """
    Execute a single agent

    Args:
        agent_config: Agent configuration with name and params
        ctx: Runtime context

    Returns:
        Tuple of (agent_name, result)
    """
    agent_name = agent_config["name"]
    params = agent_config.get("params", {})

    try:
        logger.info(f"Executing agent: {agent_name}")

        # Get agent instance
        agent = get_agent(agent_name)

        # Execute agent with params
        result = await agent.execute(params)

        logger.info(f"Agent {agent_name} completed successfully")
        return agent_name, result

    except Exception as e:
        logger.error(f"Agent {agent_name} failed: {e}", exc_info=True)
        return agent_name, {
            "status": "error",
            "agent": agent_name,
            "error": str(e)
        }


async def execute_sequential(agents: List[Dict[str, Any]], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute agents sequentially

    Args:
        agents: List of agent configurations
        ctx: Runtime context

    Returns:
        Dictionary of agent results
    """
    results = {}

    # Sort agents by order
    sorted_agents = sorted(agents, key=lambda x: x.get("order", 0))

    for agent_config in sorted_agents:
        agent_name, result = await execute_agent(agent_config, ctx)
        results[agent_name] = result

        # Stop if agent failed and strict mode enabled
        if result.get("status") == "error":
            logger.warning(f"Agent {agent_name} failed, stopping sequential execution")
            break

    return results


async def execute_parallel(agents: List[Dict[str, Any]], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute agents in parallel

    Args:
        agents: List of agent configurations
        ctx: Runtime context

    Returns:
        Dictionary of agent results
    """
    # Create tasks for all agents
    tasks = [execute_agent(agent_config, ctx) for agent_config in agents]

    # Execute all tasks concurrently
    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    # Convert to dictionary
    results = {}
    for item in results_list:
        if isinstance(item, Exception):
            logger.error(f"Agent execution failed with exception: {item}")
            continue
        agent_name, result = item
        results[agent_name] = result

    return results


async def execute_dag(agents: List[Dict[str, Any]], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute agents in DAG (Directed Acyclic Graph) manner
    Based on dependencies between agents

    Args:
        agents: List of agent configurations
        ctx: Runtime context

    Returns:
        Dictionary of agent results

    Note:
        For now, falls back to sequential execution.
        Full DAG implementation requires dependency tracking.
    """
    logger.info("DAG execution mode - currently using sequential fallback")
    return await execute_sequential(agents, ctx)


async def execute_agents_node(state: Dict[str, Any], runtime: Runtime) -> Dict[str, Any]:
    """
    Node function to execute agents according to plan

    Args:
        state: Current state dictionary
        runtime: LangGraph runtime object

    Returns:
        State update with agent_results field
    """
    try:
        # Get context
        ctx = await runtime.context()

        execution_plan = state["execution_plan"]
        strategy = execution_plan.get("strategy", "sequential")
        agents = execution_plan.get("agents", [])

        logger.info(f"Executing {len(agents)} agents using {strategy} strategy")

        # Execute agents based on strategy
        if strategy == "parallel":
            agent_results = await execute_parallel(agents, ctx)
        elif strategy == "dag":
            agent_results = await execute_dag(agents, ctx)
        else:  # default: sequential
            agent_results = await execute_sequential(agents, ctx)

        logger.info(f"Agent execution completed: {len(agent_results)} results")

        # Check if any agent failed
        failed_agents = [name for name, result in agent_results.items() if result.get("status") == "error"]

        if failed_agents:
            logger.warning(f"Some agents failed: {failed_agents}")

        return {
            "agent_results": agent_results,
            "status": "processing",
            "execution_step": "evaluating"
        }

    except Exception as e:
        logger.error(f"Agent execution coordinator failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "errors": [f"Agent execution failed: {str(e)}"],
            "execution_step": "failed"
        }