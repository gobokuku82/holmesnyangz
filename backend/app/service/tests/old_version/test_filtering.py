"""
Test the two-stage validation filtering system
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

# Test queries
TEST_QUERIES = [
    # Irrelevant queries
    ("바부야", "irrelevant"),  # Meaningless/insult
    ("안녕하세요", "irrelevant"),  # Greeting
    ("오늘 날씨 어때?", "irrelevant"),  # Weather
    ("1+1은 뭐야?", "irrelevant"),  # Math
    ("김치찌개 만드는 법", "irrelevant"),  # Cooking

    # Real estate queries
    ("강남구 아파트 시세", "real_estate"),
    ("전세 대출 조건", "real_estate"),
    ("부동산 계약서 작성법", "real_estate"),
    ("양도세 계산 방법", "real_estate"),

    # Edge cases
    ("대출", "edge"),  # Could be real estate or general
    ("세금", "edge"),  # Could be property tax or general
]


async def test_query(supervisor, query, expected_type):
    """Test a single query"""
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"Expected: {expected_type}")
    print("-"*60)

    try:
        result = await supervisor.process_query(
            query=query,
            session_id="test",
            llm_context=TestConfig.get_llm_context()
        )

        # Check intent type
        intent_type = result.get("intent_type", "unknown")
        final_response = result.get("final_response", {})

        print(f"Intent Type: {intent_type}")

        if intent_type == "irrelevant":
            print(f"[OK] Correctly filtered as irrelevant")
            print(f"Message: {final_response.get('message', 'N/A')}")
        elif intent_type in ["search", "analysis", "legal", "loan", "general"]:
            print(f"Processed as real estate query (type: {intent_type})")
        else:
            print(f"Unclear or error: {intent_type}")

        # Print reasoning if available
        if "reasoning" in result:
            print(f"Reasoning: {result['reasoning']}")

        return intent_type

    except Exception as e:
        print(f"ERROR: {e}")
        return "error"


async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("TESTING TWO-STAGE VALIDATION SYSTEM")
    print("="*70)

    # Initialize supervisor
    print("\nInitializing supervisor...")
    supervisor = RealEstateSupervisor(llm_context=TestConfig.get_llm_context())
    print("[OK] Supervisor initialized")

    # Run tests
    results = []
    for query, expected_type in TEST_QUERIES:
        intent = await test_query(supervisor, query, expected_type)
        results.append({
            "query": query,
            "expected": expected_type,
            "actual": intent
        })

        # Small delay between requests
        await asyncio.sleep(1)

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    irrelevant_correct = sum(1 for r in results
                            if r["expected"] == "irrelevant"
                            and r["actual"] == "irrelevant")
    irrelevant_total = sum(1 for r in results if r["expected"] == "irrelevant")

    real_estate_correct = sum(1 for r in results
                             if r["expected"] == "real_estate"
                             and r["actual"] not in ["irrelevant", "error"])
    real_estate_total = sum(1 for r in results if r["expected"] == "real_estate")

    print(f"\nIrrelevant Queries: {irrelevant_correct}/{irrelevant_total} correctly filtered")
    print(f"Real Estate Queries: {real_estate_correct}/{real_estate_total} correctly processed")

    # Show failures
    failures = [r for r in results
                if (r["expected"] == "irrelevant" and r["actual"] != "irrelevant")
                or (r["expected"] == "real_estate" and r["actual"] == "irrelevant")]

    if failures:
        print(f"\nFailures ({len(failures)}):")
        for f in failures:
            print(f"  - '{f['query']}': expected {f['expected']}, got {f['actual']}")

    print("\n[OK] Test complete")


if __name__ == "__main__":
    asyncio.run(main())