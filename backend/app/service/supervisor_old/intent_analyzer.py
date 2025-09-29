"""
Intent Analyzer Node
Analyzes user query to extract intent and entities
"""

from typing import Dict, Any
from langgraph.runtime import Runtime
import logging
import json
import os

from .prompts import get_intent_analysis_prompt


logger = logging.getLogger(__name__)


async def call_llm_for_intent(query: str, api_key: str) -> Dict[str, Any]:
    """
    Call LLM API to analyze user intent

    Args:
        query: User query string
        api_key: OpenAI API key

    Returns:
        Parsed intent dictionary
    """
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)

        prompt = get_intent_analysis_prompt(query)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert in analyzing real estate queries. Always respond in JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )

        content = response.choices[0].message.content.strip()

        # Parse JSON response
        intent = json.loads(content)

        logger.info(f"Intent analyzed successfully: {intent.get('intent_type')}")
        return intent

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        # Return default intent
        return {
            "intent_type": "search",
            "region": None,
            "property_type": None,
            "deal_type": None,
            "price_range": None,
            "size_range": None
        }
    except Exception as e:
        logger.error(f"Failed to call LLM for intent analysis: {e}", exc_info=True)
        raise


async def analyze_intent_node(state: Dict[str, Any], runtime: Runtime) -> Dict[str, Any]:
    """
    Node function to analyze user intent

    Args:
        state: Current state dictionary
        runtime: LangGraph runtime object

    Returns:
        State update with intent field
    """
    try:
        # Get context
        ctx = await runtime.context()

        query = state["query"]
        logger.info(f"Analyzing intent for query: {query}")

        # Get API key from context
        api_keys = ctx.get("api_keys", {})
        openai_api_key = api_keys.get("openai_api_key") or os.getenv("OPENAI_API_KEY")

        if not openai_api_key:
            logger.error("OpenAI API key not found in context or environment")
            return {
                "status": "failed",
                "errors": ["OpenAI API key not found"],
                "execution_step": "failed"
            }

        # Call LLM to analyze intent
        intent = await call_llm_for_intent(query, openai_api_key)

        logger.info(f"Intent analysis completed: {intent}")

        return {
            "intent": intent,
            "status": "processing",
            "execution_step": "planning"
        }

    except Exception as e:
        logger.error(f"Intent analysis node failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "errors": [f"Intent analysis failed: {str(e)}"],
            "execution_step": "failed"
        }