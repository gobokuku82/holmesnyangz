"""
Test various queries for two-stage validation
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

async def test_query(supervisor, query):
    """Test a single query"""
    print(f"\nQuery: '{query}'")

    try:
        result = await supervisor.process_query(
            query=query,
            session_id="test",
            llm_context=TestConfig.get_llm_context()
        )

        intent_type = result.get('intent_type')
        print(f"Result: {intent_type}")

        if intent_type == 'irrelevant':
            print("  -> Filtered as irrelevant [OK]")
        else:
            print(f"  -> Processed as {intent_type}")

        return intent_type

    except Exception as e:
        print(f"  -> ERROR: {e}")
        return "error"

async def main():
    """Test various queries"""
    print("="*50)
    print("TESTING VARIOUS QUERIES")
    print("="*50)

    # Initialize supervisor
    print("\nInitializing supervisor...")
    supervisor = RealEstateSupervisor(llm_context=TestConfig.get_llm_context())
    print("[OK] Supervisor initialized")

    # Test queries
    test_cases = [
        # Irrelevant queries
        ("바부야", "Should be irrelevant"),
        ("안녕하세요", "Greeting - should be irrelevant"),
        ("오늘 날씨 어때?", "Weather - should be irrelevant"),

        # Real estate queries
        ("강남구 아파트 시세 알려줘", "Should be processed"),
        ("전세 대출 조건이 뭐야?", "Should be processed"),
    ]

    print("\n" + "-"*50)
    print("RUNNING TESTS:")
    print("-"*50)

    results = []
    for query, description in test_cases:
        print(f"\nTest: {description}")
        intent_type = await test_query(supervisor, query)
        results.append((query, intent_type))

        # Small delay between requests to avoid rate limits
        await asyncio.sleep(2)

    # Summary
    print("\n" + "="*50)
    print("SUMMARY:")
    print("="*50)

    for query, intent_type in results:
        status = "[FILTERED]" if intent_type == "irrelevant" else f"[{intent_type.upper()}]"
        print(f"{status:12} {query}")

    print("\n[OK] Test complete")

if __name__ == "__main__":
    asyncio.run(main())