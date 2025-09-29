"""
Test script for LLMContext integration
Verifies that the new context-based LLM system works correctly
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directories to path
current_dir = Path(__file__).parent
service_dir = current_dir.parent  # backend/app/service
app_dir = service_dir.parent      # backend/app
backend_dir = app_dir.parent      # backend

sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(app_dir))
sys.path.insert(0, str(service_dir))
sys.path.insert(0, str(backend_dir / "app" / "service"))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

# Import context utilities
from core.context import (
    LLMContext,
    create_default_llm_context,
    create_llm_context_with_overrides,
    create_agent_context
)
from supervisor.supervisor import RealEstateSupervisor


async def test_llm_context_creation():
    """Test creating different LLM contexts"""
    print("\n" + "="*60)
    print("TEST 1: LLM Context Creation")
    print("="*60)

    # Test default context
    default_context = create_default_llm_context()
    print(f"\nDefault Context:")
    print(f"  Provider: {default_context.provider}")
    print(f"  API Key: {'SET' if default_context.api_key else 'NOT SET'}")
    print(f"  Use Mock: {default_context.use_mock}")

    # Test OpenAI context
    openai_context = create_llm_context_with_overrides(
        provider="openai",
        use_mock=False
    )
    print(f"\nOpenAI Context:")
    print(f"  Provider: {openai_context.provider}")
    print(f"  API Key: {'SET' if openai_context.api_key else 'NOT SET'}")
    print(f"  Use Mock: {openai_context.use_mock}")

    # Test Mock context
    mock_context = create_llm_context_with_overrides(
        use_mock=True
    )
    print(f"\nMock Context:")
    print(f"  Provider: {mock_context.provider}")
    print(f"  Use Mock: {mock_context.use_mock}")

    return True


async def test_supervisor_with_context():
    """Test supervisor initialization with LLMContext"""
    print("\n" + "="*60)
    print("TEST 2: Supervisor with LLMContext")
    print("="*60)

    try:
        # Create LLM context
        llm_context = create_llm_context_with_overrides(
            provider="openai",
            use_mock=False  # Try to use real OpenAI
        )

        print(f"\nInitializing Supervisor...")
        print(f"  LLM Provider: {llm_context.provider}")
        print(f"  Use Mock: {llm_context.use_mock}")

        # Initialize supervisor
        supervisor = RealEstateSupervisor(llm_context=llm_context)
        print("[OK] Supervisor initialized successfully")

        # Test LLM manager
        if hasattr(supervisor, 'llm_manager'):
            print(f"[OK] LLM Manager created")
            print(f"  Context Provider: {supervisor.llm_manager.context.provider}")
            print(f"  Context Mock Mode: {supervisor.llm_manager.context.use_mock}")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to initialize supervisor: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_simple_query():
    """Test a simple query with the new context system"""
    print("\n" + "="*60)
    print("TEST 3: Simple Query Processing")
    print("="*60)

    try:
        # Create contexts
        llm_context = create_llm_context_with_overrides(
            provider="openai",
            use_mock=False  # Use real OpenAI
        )

        agent_context = create_agent_context(
            chat_user_ref="test_user",
            chat_session_id="test_session",
            llm_context=llm_context
        )

        print(f"\nContext Setup:")
        print(f"  LLM Provider: {llm_context.provider}")
        print(f"  Use Mock: {llm_context.use_mock}")
        print(f"  API Key Available: {'YES' if llm_context.api_key else 'NO'}")

        # Initialize supervisor
        supervisor = RealEstateSupervisor(llm_context=llm_context)

        # Test query
        query = "강남구 아파트 시세"
        print(f"\nProcessing Query: {query}")

        result = await supervisor.process_query(
            query=query,
            session_id="test_session",
            llm_context=llm_context  # Pass LLM context directly
        )

        print(f"\n[OK] Query processed successfully")

        # Display result type
        if isinstance(result, dict):
            print(f"Result Type: {result.get('response_type', 'unknown')}")

            # Check final response
            final_response = result.get('final_response')
            if final_response:
                print(f"Final Response Available: YES")
                if isinstance(final_response, dict):
                    print(f"Response Keys: {list(final_response.keys())}")
            else:
                print(f"Final Response Available: NO")

        return True

    except Exception as e:
        print(f"\n[ERROR] Query processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_mock_vs_openai():
    """Compare Mock vs OpenAI modes"""
    print("\n" + "="*60)
    print("TEST 4: Mock vs OpenAI Comparison")
    print("="*60)

    query = "강남구 아파트 시세"

    # Test with Mock
    print("\n--- Testing with Mock Mode ---")
    try:
        mock_context = create_llm_context_with_overrides(use_mock=True)
        mock_supervisor = RealEstateSupervisor(llm_context=mock_context)

        mock_result = await mock_supervisor.process_query(
            query=query,
            session_id="mock_test"
        )
        print("[OK] Mock mode processed successfully")
    except Exception as e:
        print(f"[ERROR] Mock mode failed: {e}")

    # Test with OpenAI (if API key available)
    print("\n--- Testing with OpenAI Mode ---")
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            openai_context = create_llm_context_with_overrides(
                provider="openai",
                use_mock=False
            )
            openai_supervisor = RealEstateSupervisor(llm_context=openai_context)

            openai_result = await openai_supervisor.process_query(
                query=query,
                session_id="openai_test"
            )
            print("[OK] OpenAI mode processed successfully")
        except Exception as e:
            print(f"[ERROR] OpenAI mode failed: {e}")
    else:
        print("[SKIP] No OpenAI API key available")

    return True


async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print(" LLMContext Integration Test Suite")
    print("="*70)

    # Check environment
    api_key = os.getenv("OPENAI_API_KEY")
    print(f"\nEnvironment Check:")
    print(f"  OPENAI_API_KEY: {'SET' if api_key else 'NOT SET'}")
    print(f"  API Key Length: {len(api_key) if api_key else 0}")

    tests = [
        ("Context Creation", test_llm_context_creation),
        ("Supervisor Initialization", test_supervisor_with_context),
        ("Query Processing", test_simple_query),
        ("Mock vs OpenAI", test_mock_vs_openai)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\nRunning: {test_name}")
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"[ERROR] Test failed with exception: {e}")
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


if __name__ == "__main__":
    asyncio.run(main())