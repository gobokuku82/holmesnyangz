"""
Plan Builder Node
Creates execution plan based on analyzed intent
"""

from typing import Dict, Any, List
from langgraph.runtime import Runtime
import logging
import json
import os

from .prompts import get_plan_building_prompt


logger = logging.getLogger(__name__)


def build_plan_rule_based(intent: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build execution plan using rule-based approach
    Fallback when LLM is not available or fails

    Args:
        intent: Analyzed intent dictionary

    Returns:
        Execution plan
    """
    intent_type = intent.get("intent_type", "search")
    agents = []

    # Rule-based agent selection
    if intent_type == "search":
        agents.append({
            "name": "property_search",
            "order": 1,
            "params": {
                "region": intent.get("region"),
                "property_type": intent.get("property_type"),
                "deal_type": intent.get("deal_type"),
                "price_range": intent.get("price_range"),
                "size_range": intent.get("size_range")
            }
        })
        strategy = "sequential"

    elif intent_type == "analysis":
        agents.append({
            "name": "property_search",
            "order": 1,
            "params": {
                "region": intent.get("region"),
                "property_type": intent.get("property_type"),
                "deal_type": intent.get("deal_type")
            }
        })
        agents.append({
            "name": "market_analysis",
            "order": 2,
            "params": {
                "region": intent.get("region"),
                "property_type": intent.get("property_type")
            }
        })
        strategy = "sequential"

    elif intent_type == "comparison":
        agents.append({
            "name": "property_search",
            "order": 1,
            "params": {
                "region": intent.get("region"),
                "property_type": intent.get("property_type"),
                "deal_type": intent.get("deal_type")
            }
        })
        agents.append({
            "name": "region_comparison",
            "order": 2,
            "params": {
                "region": intent.get("region")
            }
        })
        strategy = "sequential"

    elif intent_type == "recommendation":
        agents.append({
            "name": "property_search",
            "order": 1,
            "params": {
                "region": intent.get("region"),
                "property_type": intent.get("property_type"),
                "deal_type": intent.get("deal_type")
            }
        })
        agents.append({
            "name": "market_analysis",
            "order": 2,
            "params": {
                "region": intent.get("region")
            }
        })
        agents.append({
            "name": "investment_advisor",
            "order": 3,
            "params": {
                "budget": intent.get("price_range"),
                "size": intent.get("size_range")
            }
        })
        strategy = "sequential"

    else:
        # Default: search only
        agents.append({
            "name": "property_search",
            "order": 1,
            "params": intent
        })
        strategy = "sequential"

    return {
        "strategy": strategy,
        "agents": agents
    }


async def call_llm_for_planning(intent: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    """
    Call LLM API to build execution plan

    Args:
        intent: Analyzed intent dictionary
        api_key: OpenAI API key

    Returns:
        Execution plan dictionary
    """
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)

        prompt = get_plan_building_prompt(intent)

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert in planning agent execution strategies. Always respond in JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )

        content = response.choices[0].message.content.strip()

        # Parse JSON response
        plan = json.loads(content)

        logger.info(f"Execution plan created: {len(plan.get('agents', []))} agents")
        return plan

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM response, using rule-based planning: {e}")
        return build_plan_rule_based(intent)
    except Exception as e:
        logger.warning(f"LLM planning failed, using rule-based planning: {e}")
        return build_plan_rule_based(intent)


async def build_plan_node(state: Dict[str, Any], runtime: Runtime) -> Dict[str, Any]:
    """
    Node function to build execution plan

    Args:
        state: Current state dictionary
        runtime: LangGraph runtime object

    Returns:
        State update with execution_plan field
    """
    try:
        # Get context
        ctx = await runtime.context()

        intent = state["intent"]
        logger.info(f"Building execution plan for intent type: {intent.get('intent_type')}")

        # Get API key from context
        api_keys = ctx.get("api_keys", {})
        openai_api_key = api_keys.get("openai_api_key") or os.getenv("OPENAI_API_KEY")

        if not openai_api_key:
            logger.warning("OpenAI API key not found, using rule-based planning")
            execution_plan = build_plan_rule_based(intent)
        else:
            # Try LLM-based planning first
            execution_plan = await call_llm_for_planning(intent, openai_api_key)

        logger.info(f"Execution plan built: {execution_plan}")

        return {
            "execution_plan": execution_plan,
            "status": "processing",
            "execution_step": "executing_agents"
        }

    except Exception as e:
        logger.error(f"Plan building node failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "errors": [f"Plan building failed: {str(e)}"],
            "execution_step": "failed"
        }