"""
Test script to demonstrate switching between Mock and OpenAI modes
Shows how LLMContext enables runtime switching of LLM providers
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add parent directories to path
current_dir = Path(__file__).parent
service_dir = current_dir.parent
app_dir = service_dir.parent
backend_dir = app_dir.parent

sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(app_dir))
sys.path.insert(0, str(service_dir))
sys.path.insert(0, str(backend_dir / "app" / "service"))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

# Import context utilities
from core.context import (
    LLMContext,
    create_llm_context_with_overrides,
    create_agent_context
)
from supervisor.supervisor import RealEstateSupervisor


async def test_with_mode(mode: str, query: str):
    """Test a query with specified mode"""

    print(f"\n{'='*60}")
    print(f" Testing with {mode.upper()} Mode")
    print(f"{'='*60}")

    # Create LLM context based on mode
    if mode == "mock":
        llm_context = create_llm_context_with_overrides(use_mock=True)
    else:  # openai
        llm_context = create_llm_context_with_overrides(
            provider="openai",
            use_mock=False
        )

    print(f"Provider: {llm_context.provider}")
    print(f"Use Mock: {llm_context.use_mock}")
    print(f"API Key: {'SET' if llm_context.api_key else 'NOT SET'}")

    try:
        # Initialize supervisor with specific context
        supervisor = RealEstateSupervisor(llm_context=llm_context)

        # Process query
        print(f"\nQuery: {query}")
        print("Processing...")

        start_time = time.time()
        result = await supervisor.process_query(
            query=query,
            session_id=f"{mode}_test_{int(time.time())}"
        )
        execution_time = time.time() - start_time

        # Display results
        print(f"\n[SUCCESS] Query processed in {execution_time:.2f}s")

        if isinstance(result, dict):
            response_type = result.get("response_type", "unknown")
            print(f"Response Type: {response_type}")

            # Show final response summary
            final_response = result.get("final_response", {})
            if isinstance(final_response, dict):
                if "summary" in final_response:
                    print(f"\nSummary Preview:")
                    summary = final_response["summary"]
                    preview = summary[:200] + "..." if len(summary) > 200 else summary
                    print(f"  {preview}")

                if "data" in final_response:
                    data = final_response["data"]
                    if isinstance(data, list):
                        print(f"\nData: {len(data)} items found")
                    elif isinstance(data, dict):
                        print(f"\nData Keys: {list(data.keys())}")

        return True

    except Exception as e:
        print(f"\n[ERROR] Failed: {e}")
        return False


async def main():
    """Main test runner"""
    print("\n" + "="*70)
    print(" LLM Mode Switching Demonstration")
    print("="*70)

    # Check environment
    api_key = os.getenv("OPENAI_API_KEY")
    print(f"\nEnvironment:")
    print(f"  OPENAI_API_KEY: {'Available' if api_key else 'Not Found'}")

    # Test queries
    queries = [
        "강남구 아파트 시세",
        "부동산 계약시 주의사항",
        "주택담보대출 금리"
    ]

    for query in queries:
        print(f"\n{'='*70}")
        print(f" Testing Query: {query}")
        print(f"{'='*70}")

        # Test with Mock mode
        mock_success = await test_with_mode("mock", query)

        # Test with OpenAI mode (if API key available)
        if api_key:
            await asyncio.sleep(1)  # Small delay between requests
            openai_success = await test_with_mode("openai", query)
        else:
            print("\n[SKIP] OpenAI mode - No API key available")
            openai_success = None

        # Compare results
        print(f"\n{'='*60}")
        print(" Comparison:")
        print(f"  Mock Mode: {'PASS' if mock_success else 'FAIL'}")
        if openai_success is not None:
            print(f"  OpenAI Mode: {'PASS' if openai_success else 'FAIL'}")
        print(f"{'='*60}")

    print("\n" + "="*70)
    print(" Test Complete")
    print("="*70)


if __name__ == "__main__":
    # Run test
    asyncio.run(main())