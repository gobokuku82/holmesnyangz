"""
Result Evaluator Node
Evaluates agent results and generates final output
"""

from typing import Dict, Any
from langgraph.runtime import Runtime
import logging
import json
import os

from .prompts import get_evaluation_prompt, get_response_formatting_prompt


logger = logging.getLogger(__name__)


def evaluate_quality_rule_based(agent_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate agent results quality using rule-based approach
    Fallback when LLM is not available

    Args:
        agent_results: Dictionary of agent results

    Returns:
        Evaluation result
    """
    # Check if all agents succeeded
    all_success = all(result.get("status") == "success" for result in agent_results.values())

    # Check if we have any data
    has_data = any(result.get("data") for result in agent_results.values())

    # Count failed agents
    failed_agents = [name for name, result in agent_results.items() if result.get("status") == "error"]

    # Determine quality score
    total_agents = len(agent_results)
    successful_agents = total_agents - len(failed_agents)
    quality_score = successful_agents / total_agents if total_agents > 0 else 0.0

    # Determine if retry is needed
    needs_retry = not all_success and len(failed_agents) > 0

    return {
        "quality_score": quality_score,
        "completeness": all_success and has_data,
        "accuracy": True,  # Can't determine without LLM
        "consistency": True,  # Can't determine without LLM
        "needs_retry": needs_retry,
        "retry_agents": failed_agents,
        "feedback": f"Rule-based evaluation: {successful_agents}/{total_agents} agents succeeded"
    }


async def call_llm_for_evaluation(agent_results: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    """
    Call LLM API to evaluate agent results

    Args:
        agent_results: Dictionary of agent results
        api_key: OpenAI API key

    Returns:
        Evaluation result dictionary
    """
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)

        prompt = get_evaluation_prompt(agent_results)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert in evaluating agent execution results. Always respond in JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )

        content = response.choices[0].message.content.strip()

        # Parse JSON response
        evaluation = json.loads(content)

        logger.info(f"Evaluation completed: quality_score={evaluation.get('quality_score')}")
        return evaluation

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM response, using rule-based evaluation: {e}")
        return evaluate_quality_rule_based(agent_results)
    except Exception as e:
        logger.warning(f"LLM evaluation failed, using rule-based evaluation: {e}")
        return evaluate_quality_rule_based(agent_results)


def format_response_simple(query: str, agent_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format final response using simple approach
    Fallback when LLM is not available

    Args:
        query: Original user query
        agent_results: Dictionary of agent results

    Returns:
        Formatted final output
    """
    # Collect all data from agents
    all_data = []
    insights = []

    for agent_name, result in agent_results.items():
        if result.get("status") == "success":
            data = result.get("data")
            if isinstance(data, list):
                all_data.extend(data)
            elif isinstance(data, dict):
                all_data.append(data)
            else:
                all_data.append({"agent": agent_name, "result": data})

            # Collect insights if available
            agent_insights = result.get("insights", [])
            if agent_insights:
                insights.extend(agent_insights)

    return {
        "answer": f"검색 완료: {len(all_data)}개의 결과를 찾았습니다.",
        "listings": all_data[:10],  # First 10 results
        "insights": insights,
        "metadata": {
            "total_results": len(all_data),
            "agents_used": list(agent_results.keys())
        }
    }


async def call_llm_for_formatting(query: str, agent_results: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    """
    Call LLM API to format final response

    Args:
        query: Original user query
        agent_results: Dictionary of agent results
        api_key: OpenAI API key

    Returns:
        Formatted final output dictionary
    """
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)

        prompt = get_response_formatting_prompt(query, agent_results)

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert in formatting real estate information for users. Always respond in JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )

        content = response.choices[0].message.content.strip()

        # Parse JSON response
        final_output = json.loads(content)

        logger.info(f"Response formatted successfully")
        return final_output

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM response, using simple formatting: {e}")
        return format_response_simple(query, agent_results)
    except Exception as e:
        logger.warning(f"LLM formatting failed, using simple formatting: {e}")
        return format_response_simple(query, agent_results)


async def evaluate_results_node(state: Dict[str, Any], runtime: Runtime) -> Dict[str, Any]:
    """
    Node function to evaluate agent results and generate final output

    Args:
        state: Current state dictionary
        runtime: LangGraph runtime object

    Returns:
        State update with evaluation and final_output fields
    """
    try:
        # Get context
        ctx = await runtime.context()

        agent_results = state["agent_results"]
        query = state["query"]

        logger.info(f"Evaluating results from {len(agent_results)} agents")

        # Get API key from context
        api_keys = ctx.get("api_keys", {})
        openai_api_key = api_keys.get("openai_api_key") or os.getenv("OPENAI_API_KEY")

        # Evaluate quality
        if openai_api_key:
            evaluation = await call_llm_for_evaluation(agent_results, openai_api_key)
        else:
            logger.warning("OpenAI API key not found, using rule-based evaluation")
            evaluation = evaluate_quality_rule_based(agent_results)

        logger.info(f"Evaluation: {evaluation}")

        # Check if retry is needed
        if evaluation.get("needs_retry", False):
            retry_agents = evaluation.get("retry_agents", [])
            logger.warning(f"Retry needed for agents: {retry_agents}")

            return {
                "evaluation": evaluation,
                "status": "processing",
                "execution_step": "executing_agents"  # Go back to execution
            }

        # Format final output
        if openai_api_key:
            final_output = await call_llm_for_formatting(query, agent_results, openai_api_key)
        else:
            logger.warning("OpenAI API key not found, using simple formatting")
            final_output = format_response_simple(query, agent_results)

        logger.info(f"Final output generated successfully")

        return {
            "evaluation": evaluation,
            "final_output": final_output,
            "status": "completed",
            "execution_step": "finished",
            "end_time": None  # Will be set by state factory
        }

    except Exception as e:
        logger.error(f"Result evaluation node failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "errors": [f"Result evaluation failed: {str(e)}"],
            "execution_step": "failed"
        }