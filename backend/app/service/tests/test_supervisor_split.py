"""
Test Supervisor Split
supervisor.py (production) vs supervisor_mock.py (test) 검증
"""

import asyncio
import sys
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

from core.context import create_llm_context_with_overrides


async def test_production_supervisor():
    """Test production supervisor (OpenAI only)"""
    print("\n" + "="*60)
    print(" Test 1: Production Supervisor (OpenAI)")
    print("="*60)

    from supervisor.supervisor import RealEstateSupervisor

    # Create context for OpenAI
    llm_context = create_llm_context_with_overrides(
        provider="openai",
        use_mock=False  # This should be ignored in production
    )

    print(f"Provider: {llm_context.provider}")
    print(f"Use Mock: {llm_context.use_mock}")

    try:
        supervisor = RealEstateSupervisor(llm_context=llm_context)

        # Check that no mock methods exist
        assert not hasattr(supervisor.llm_manager, '_mock_analyze_intent'), "Mock method found in production supervisor!"
        assert not hasattr(supervisor.llm_manager, '_mock_create_plan'), "Mock method found in production supervisor!"

        print("[SUCCESS] Production supervisor has no mock methods")

        # Test with a simple query
        query = "강남구 아파트 시세"
        print(f"\nQuery: {query}")

        result = await supervisor.process_query(
            query=query,
            session_id="prod_test"
        )

        print(f"Response Type: {result.get('response_type', 'unknown')}")
        return True

    except Exception as e:
        print(f"[ERROR] {e}")
        return False


async def test_mock_supervisor():
    """Test mock supervisor"""
    print("\n" + "="*60)
    print(" Test 2: Mock Supervisor (Test Only)")
    print("="*60)

    from supervisor.supervisor_mock import RealEstateSupervisorMock

    try:
        supervisor = RealEstateSupervisorMock()

        # Check that it uses MockLLMManager
        assert hasattr(supervisor, 'llm_manager'), "No llm_manager found!"
        assert supervisor.llm_manager.__class__.__name__ == 'MockLLMManager', "Not using MockLLMManager!"

        print("[SUCCESS] Mock supervisor uses MockLLMManager")

        # Test with a simple query
        query = "서초구 전세 매물"
        print(f"\nQuery: {query}")

        result = await supervisor.process_query(
            query=query,
            session_id="mock_test"
        )

        print(f"Response Type: {result.get('response_type', 'unknown')}")
        print(f"Intent Type: {result.get('intent_type', 'unknown')}")

        # Check that mock returns results
        if result.get('final_response'):
            print("[SUCCESS] Mock supervisor returned response")
            return True
        else:
            print("[FAIL] Mock supervisor did not return response")
            return False

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_no_api_key_handling():
    """Test production supervisor with no API key"""
    print("\n" + "="*60)
    print(" Test 3: Production Supervisor Error Handling")
    print("="*60)

    from supervisor.supervisor import RealEstateSupervisor

    # Create context with no API key
    llm_context = create_llm_context_with_overrides(
        provider="openai",
        api_key="",  # Empty API key
        use_mock=False
    )

    supervisor = RealEstateSupervisor(llm_context=llm_context)

    query = "부동산 계약 주의사항"
    print(f"Query: {query}")

    result = await supervisor.process_query(
        query=query,
        session_id="error_test"
    )

    # Should return error response
    if result.get('final_response'):
        response = result['final_response']
        if response.get('type') == 'error':
            print("[SUCCESS] Error properly handled")
            print(f"Message: {response.get('message')}")
            return True
        else:
            print(f"[FAIL] Expected error, got: {response.get('type')}")
            return False
    else:
        print("[FAIL] No final_response")
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print(" Supervisor Split Test Suite")
    print("="*70)
    print("\nVerifying separation of production and mock supervisors")

    tests = [
        ("Production Supervisor", test_production_supervisor),
        ("Mock Supervisor", test_mock_supervisor),
        ("Error Handling", test_no_api_key_handling)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n[ERROR] Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "="*70)
    print(" TEST SUMMARY")
    print("="*70)

    for test_name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"  {status} {test_name}")

    total = len(results)
    passed = sum(1 for _, s in results if s)
    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] Supervisor split successful!")
        print("- supervisor.py: Production only (no mock)")
        print("- supervisor_mock.py: Test only (mock implementation)")
    else:
        print("\n[FAIL] Some tests failed")


if __name__ == "__main__":
    asyncio.run(main())