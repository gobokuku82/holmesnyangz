"""
Test execution plan creation
"""

import asyncio
import json
from pathlib import Path
import sys

# Add parent directories to path
current_dir = Path(__file__).parent
service_dir = current_dir.parent
sys.path.insert(0, str(service_dir))

from test_config import TestConfig
from supervisor.supervisor import LLMManager

async def test_plan_creation():
    """Test plan creation with single query"""

    query = "강남구 아파트 시세 알려줘"
    intent = {
        "intent_type": "search",
        "is_real_estate_related": True,
        "entities": {
            "region": "강남구",
            "property_type": "아파트",
            "transaction_type": "매매"
        },
        "keywords": ["강남구", "아파트", "시세"],
        "confidence": 0.9
    }

    print("="*60)
    print("EXECUTION PLAN TEST")
    print("="*60)
    print(f"\nQuery: {query}")
    print(f"Intent: {intent['intent_type']}")

    # Create LLM Manager
    llm_manager = LLMManager(context=TestConfig.get_llm_context())

    try:
        # Create execution plan
        print("\nCreating execution plan...")
        plan = await llm_manager.create_execution_plan(query, intent)

        print("\n[RESULT]")
        print(f"Selected Agents: {plan.get('agents', [])}")
        print(f"Keywords: {plan.get('collection_keywords', [])}")
        print(f"Reasoning: {plan.get('reasoning', 'N/A')}")

        if 'agent_capabilities_used' in plan:
            print(f"Capabilities: {plan.get('agent_capabilities_used', [])}")

        # Check if search_agent was selected
        if 'search_agent' in plan.get('agents', []):
            print("\n[SUCCESS] search_agent correctly selected!")
        else:
            print(f"\n[WARNING] Unexpected agents: {plan.get('agents', [])}")

    except Exception as e:
        print(f"\n[ERROR] {e}")

if __name__ == "__main__":
    asyncio.run(test_plan_creation())