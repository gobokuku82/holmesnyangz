"""
Quick test for specific query
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
from supervisor.supervisor import RealEstateSupervisor

async def test_single_query():
    """Test single query"""
    query = "바부야"  # Test irrelevant query

    # Initialize supervisor
    print("Initializing supervisor...")
    supervisor = RealEstateSupervisor(llm_context=TestConfig.get_llm_context())
    print("[OK] Supervisor initialized\n")

    print(f"Testing query: '{query}'")
    print("-"*40)

    try:
        result = await supervisor.process_query(
            query=query,
            session_id="test",
            llm_context=TestConfig.get_llm_context()
        )

        # Print results
        print("\nRESULT:")
        print(f"Intent Type: {result.get('intent_type')}")

        if result.get('intent_type') == 'irrelevant':
            print("[SUCCESS] Query correctly filtered as irrelevant")
            final_response = result.get('final_response', {})
            print(f"Message: {final_response.get('message')}")
        else:
            print(f"[WARNING] Query was processed as: {result.get('intent_type')}")

    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    asyncio.run(test_single_query())