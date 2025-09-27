"""
Execution Coordinator Node
Executes agents according to the execution plan
FIXED VERSION: Runtime handling corrected, retry_count added
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
import asyncio
from ..utils.agent_registry import AgentRegistry

logger = logging.getLogger(__name__)


async def execute_agent(
    agent_config: Dict[str, Any], 
    context: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    """
    Execute a single agent

    Args:
        agent_config: Agent configuration with name and params
        context: Execution context

    Returns:
        Tuple of (agent_name, result)
    """
    agent_name = agent_config["name"]
    params = agent_config.get("params", {})

    try:
        logger.info(f"Executing agent: {agent_name}")
        
        # Get agent instance from registry
        agent = AgentRegistry.get_agent(agent_name)
        
        # Add context to params
        execution_params = {
            **params,
            "context": context
        }
        
        # Execute agent with params
        result = await agent.execute(execution_params)
        
        logger.info(f"Agent {agent_name} completed successfully")
        return agent_name, result

    except Exception as e:
        logger.error(f"Agent {agent_name} failed: {e}", exc_info=True)
        return agent_name, {
            "status": "error",
            "agent": agent_name,
            "error": str(e)
        }


async def execute_sequential(
    agents: List[Dict[str, Any]], 
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute agents sequentially

    Args:
        agents: List of agent configurations
        context: Execution context

    Returns:
        Dictionary of agent results
    """
    results = {}
    
    # Sort agents by order
    sorted_agents = sorted(agents, key=lambda x: x.get("order", 0))
    
    for agent_config in sorted_agents:
        agent_name, result = await execute_agent(agent_config, context)
        results[agent_name] = result
        
        # Stop if agent failed and strict mode enabled
        if result.get("status") == "error" and context.get("strict_mode", False):
            logger.warning(f"Agent {agent_name} failed in strict mode, stopping sequential execution")
            break
    
    return results


async def execute_parallel(
    agents: List[Dict[str, Any]], 
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute agents in parallel

    Args:
        agents: List of agent configurations
        context: Execution context

    Returns:
        Dictionary of agent results
    """
    # Create tasks for all agents
    tasks = [execute_agent(agent_config, context) for agent_config in agents]
    
    # Execute all tasks concurrently
    results_list = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Convert to dictionary
    results = {}
    for item in results_list:
        if isinstance(item, Exception):
            logger.error(f"Agent execution failed with exception: {item}")
            # Add error result for the agent
            results[f"unknown_agent"] = {
                "status": "error",
                "error": str(item)
            }
        else:
            agent_name, result = item
            results[agent_name] = result
    
    return results


async def execute_dag(
    agents: List[Dict[str, Any]], 
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute agents in DAG (Directed Acyclic Graph) manner
    Based on dependencies between agents

    Args:
        agents: List of agent configurations with dependencies
        context: Execution context

    Returns:
        Dictionary of agent results
    """
    from collections import defaultdict, deque
    
    # Build dependency graph
    graph = defaultdict(list)
    in_degree = defaultdict(int)
    agent_map = {agent["name"]: agent for agent in agents}
    
    # Initialize all agents in the graph
    for agent in agents:
        if agent["name"] not in in_degree:
            in_degree[agent["name"]] = 0
    
    # Build edges based on dependencies
    for agent in agents:
        deps = agent.get("dependencies", [])
        for dep in deps:
            if dep in agent_map:
                graph[dep].append(agent["name"])
                in_degree[agent["name"]] += 1
    
    # Find agents with no dependencies (starting points)
    queue = deque([name for name in agent_map.keys() if in_degree[name] == 0])
    
    if not queue:
        logger.warning("No starting agents found in DAG, falling back to sequential")
        return await execute_sequential(agents, context)
    
    results = {}
    completed = set()
    
    # Process agents in topological order
    while queue:
        # Execute all agents in the current level in parallel
        current_level = list(queue)
        queue.clear()
        
        # Execute current level agents in parallel
        level_configs = [agent_map[name] for name in current_level]
        level_results = await execute_parallel(level_configs, context)
        results.update(level_results)
        
        # Mark as completed and find next level
        for agent_name in current_level:
            completed.add(agent_name)
            
            # Check dependent agents
            for dependent in graph[agent_name]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
    
    # Check if all agents were executed
    if len(completed) < len(agents):
        unexecuted = [a["name"] for a in agents if a["name"] not in completed]
        logger.warning(f"Some agents were not executed due to cyclic dependencies: {unexecuted}")
    
    return results


async def execute_agents_node(state: Dict[str, Any], runtime: Optional[Any] = None) -> Dict[str, Any]:
    """
    Node function to execute agents according to plan
    FIXED: Proper runtime handling, added retry_count management

    Args:
        state: Current state dictionary
        runtime: LangGraph runtime object (optional)

    Returns:
        State update with agent_results field
    """
    try:
        # Handle runtime context properly
        if runtime:
            # Runtime can be either actual Runtime or MockRuntime
            if hasattr(runtime, 'context') and callable(runtime.context):
                # Actual Runtime with context method
                try:
                    ctx = runtime.context
                except:
                    ctx = runtime
            else:
                # MockRuntime or dict-like context
                ctx = runtime
        else:
            # No runtime provided, create minimal context
            ctx = {
                "user_id": "system",
                "session_id": "default",
                "debug_mode": False
            }
        
        # Extract execution plan
        execution_plan = state.get("execution_plan", {})
        strategy = execution_plan.get("strategy", "sequential")
        agents = execution_plan.get("agents", [])
        
        # Get retry information
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 2)
        failed_agents_prev = state.get("failed_agents", [])
        
        logger.info(
            f"Executing {len(agents)} agents using {strategy} strategy "
            f"(retry {retry_count}/{max_retries})"
        )
        
        # If retrying, filter to only failed agents
        if retry_count > 0 and failed_agents_prev:
            agents = [a for a in agents if a["name"] in failed_agents_prev]
            logger.info(f"Retrying {len(agents)} failed agents: {[a['name'] for a in agents]}")
        
        # Execute agents based on strategy
        if strategy == "parallel":
            agent_results = await execute_parallel(agents, ctx)
        elif strategy == "dag":
            agent_results = await execute_dag(agents, ctx)
        else:  # default: sequential
            agent_results = await execute_sequential(agents, ctx)
        
        logger.info(f"Agent execution completed: {len(agent_results)} results")
        
        # Merge with previous results if retrying
        if retry_count > 0:
            prev_results = state.get("agent_results", {})
            # Update only the retried agents
            prev_results.update(agent_results)
            agent_results = prev_results
        
        # Check if any agent failed
        failed_agents = [
            name for name, result in agent_results.items() 
            if result.get("status") == "error"
        ]
        
        if failed_agents:
            logger.warning(f"Some agents failed: {failed_agents}")
        
        return {
            "agent_results": agent_results,
            "status": "processing",
            "execution_step": "evaluating",
            "retry_count": retry_count,  # Keep current count
            "failed_agents": failed_agents
        }

    except Exception as e:
        logger.error(f"Agent execution coordinator failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "errors": [f"Agent execution failed: {str(e)}"],
            "execution_step": "failed",
            "retry_count": state.get("retry_count", 0)
        }
