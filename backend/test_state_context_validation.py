"""
Validation Test for Updated State and Context
Tests the newly updated context and state structures
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from service.core.context import (
    create_agent_context,
    create_agent_context_from_db_user,
    create_subgraph_context,
    validate_context
)
from service.core.states import (
    create_base_state,
    create_real_estate_initial_state,
    create_supervisor_initial_state,
    get_state_summary
)


def test_context_creation():
    """Test context creation with new naming conventions"""
    print("\n=== Testing Context Creation ===")

    # Test 1: Basic context creation
    print("\n1. Basic context creation")
    context = create_agent_context(
        chat_user_ref="user_test123",
        chat_session_id="session_test456"
    )
    print(f"✓ Context created with keys: {list(context.keys())}")
    assert "chat_user_ref" in context
    assert "chat_session_id" in context
    assert "chat_thread_id" in context
    print(f"  - chat_user_ref: {context['chat_user_ref']}")
    print(f"  - chat_session_id: {context['chat_session_id']}")
    print(f"  - chat_thread_id: {context['chat_thread_id']}")

    # Test 2: Context with DB references
    print("\n2. Context with database references")
    context_with_db = create_agent_context(
        chat_user_ref="user_test123",
        chat_session_id="session_test456",
        db_user_id=1001,
        db_session_id=2001
    )
    print(f"✓ Context created with DB references")
    assert context_with_db["db_user_id"] == 1001
    assert context_with_db["db_session_id"] == 2001
    print(f"  - db_user_id: {context_with_db['db_user_id']}")
    print(f"  - db_session_id: {context_with_db['db_session_id']}")

    # Test 3: Context from DB user
    print("\n3. Context from database user")
    context_from_db = create_agent_context_from_db_user(
        db_user_id=1001,
        db_session_id=2001
    )
    print(f"✓ Context created from DB user")
    assert "dbuser_1001" in context_from_db["chat_user_ref"]
    assert context_from_db["db_user_id"] == 1001
    print(f"  - chat_user_ref: {context_from_db['chat_user_ref']}")
    print(f"  - db_user_id: {context_from_db['db_user_id']}")

    # Test 4: Subgraph context
    print("\n4. Subgraph context creation")
    parent_context = create_agent_context(
        chat_user_ref="user_test123",
        chat_session_id="session_test456",
        db_user_id=1001
    )
    subgraph_ctx = create_subgraph_context(
        parent_context=parent_context,
        parent_agent="RealEstateAgent",
        subgraph_name="DataCollection"
    )
    print(f"✓ Subgraph context created")
    assert subgraph_ctx["parent_agent"] == "RealEstateAgent"
    assert subgraph_ctx["subgraph_name"] == "DataCollection"
    assert subgraph_ctx["chat_user_ref"] == "user_test123"
    print(f"  - parent_agent: {subgraph_ctx['parent_agent']}")
    print(f"  - subgraph_name: {subgraph_ctx['subgraph_name']}")

    # Test 5: Context validation
    print("\n5. Context validation")
    try:
        validate_context(context)
        print(f"✓ Context validation passed")
    except ValueError as e:
        print(f"✗ Context validation failed: {e}")
        raise

    # Test 6: Invalid context validation
    print("\n6. Invalid context validation")
    invalid_context = {"chat_user_ref": "user_test"}
    try:
        validate_context(invalid_context)
        print(f"✗ Should have raised ValueError")
        raise AssertionError("Validation should have failed")
    except ValueError as e:
        print(f"✓ Correctly caught invalid context: {e}")

    print("\n✓ All context tests passed!")


def test_state_creation():
    """Test state creation with new fields"""
    print("\n=== Testing State Creation ===")

    # Test 1: Base state creation
    print("\n1. Base state creation")
    base_state = create_base_state(
        chat_session_id="session_test456",
        chat_thread_id="thread_test789",
        db_user_id=1001,
        db_session_id=2001
    )
    print(f"✓ Base state created with keys: {list(base_state.keys())}")
    assert base_state["chat_session_id"] == "session_test456"
    assert base_state["db_user_id"] == 1001
    assert base_state["status"] == "pending"
    assert base_state["agent_path"] == []
    print(f"  - chat_session_id: {base_state['chat_session_id']}")
    print(f"  - db_user_id: {base_state['db_user_id']}")
    print(f"  - status: {base_state['status']}")
    print(f"  - agent_path: {base_state['agent_path']}")

    # Test 2: RealEstateState creation
    print("\n2. RealEstateState creation")
    real_estate_state = create_real_estate_initial_state(
        chat_session_id="session_test456",
        query="강남역 근처 30평대 아파트 매매 시세",
        db_user_id=1001
    )
    print(f"✓ RealEstateState created")
    assert real_estate_state["query"] == "강남역 근처 30평대 아파트 매매 시세"
    assert real_estate_state["chat_session_id"] == "session_test456"
    assert real_estate_state["db_user_id"] == 1001
    assert "risk_factors" in real_estate_state
    assert "agent_plan" in real_estate_state
    print(f"  - query: {real_estate_state['query']}")
    print(f"  - property_type: {real_estate_state['property_type']}")
    print(f"  - Has risk_factors field: {('risk_factors' in real_estate_state)}")

    # Test 3: SupervisorState creation
    print("\n3. SupervisorState creation")
    supervisor_state = create_supervisor_initial_state(
        chat_session_id="session_test456",
        query="테스트 쿼리",
        db_user_id=1001,
        max_retries=3
    )
    print(f"✓ SupervisorState created")
    assert supervisor_state["query"] == "테스트 쿼리"
    assert supervisor_state["retry_count"] == 0
    assert supervisor_state["max_retries"] == 3
    assert "agent_dependencies" in supervisor_state
    assert "agent_metrics" in supervisor_state
    print(f"  - query: {supervisor_state['query']}")
    print(f"  - retry_count: {supervisor_state['retry_count']}")
    print(f"  - max_retries: {supervisor_state['max_retries']}")
    print(f"  - Has agent_metrics field: {('agent_metrics' in supervisor_state)}")

    # Test 4: State summary
    print("\n4. State summary generation")
    summary = get_state_summary(real_estate_state)
    print(f"✓ State summary generated")
    assert "chat_session_id" in summary
    assert "status" in summary
    assert "agent_path" in summary
    print(f"  Summary keys: {list(summary.keys())}")
    print(f"  - status: {summary['status']}")
    print(f"  - errors_count: {summary['errors_count']}")

    print("\n✓ All state tests passed!")


def test_field_compatibility():
    """Test that all new fields are properly defined"""
    print("\n=== Testing Field Compatibility ===")

    # Test 1: Context fields
    print("\n1. Checking context field completeness")
    context = create_agent_context()
    required_context_fields = [
        "chat_user_ref", "chat_session_id", "chat_thread_id",
        "request_id", "timestamp", "language", "debug_mode"
    ]
    for field in required_context_fields:
        assert field in context, f"Missing field: {field}"
        print(f"  ✓ {field}")

    # Test 2: Base state fields
    print("\n2. Checking base state field completeness")
    base_state = create_base_state(chat_session_id="test")
    required_base_fields = [
        "chat_session_id", "status", "execution_step",
        "agent_name", "agent_path", "errors", "error_details",
        "start_time", "agent_timings"
    ]
    for field in required_base_fields:
        assert field in base_state, f"Missing field: {field}"
        print(f"  ✓ {field}")

    # Test 3: RealEstateState specific fields
    print("\n3. Checking RealEstateState specific fields")
    re_state = create_real_estate_initial_state(
        chat_session_id="test",
        query="test"
    )
    re_specific_fields = [
        "agent_plan", "agent_strategy", "db_query_results",
        "market_data", "risk_factors", "report_metadata"
    ]
    for field in re_specific_fields:
        assert field in re_state, f"Missing field: {field}"
        print(f"  ✓ {field}")

    # Test 4: SupervisorState specific fields
    print("\n4. Checking SupervisorState specific fields")
    sup_state = create_supervisor_initial_state(
        chat_session_id="test",
        query="test"
    )
    sup_specific_fields = [
        "chat_context", "intent_confidence", "agent_selection",
        "agent_dependencies", "agent_errors", "agent_metrics",
        "quality_score", "retry_needed", "response_format"
    ]
    for field in sup_specific_fields:
        assert field in sup_state, f"Missing field: {field}"
        print(f"  ✓ {field}")

    print("\n✓ All field compatibility tests passed!")


def run_all_tests():
    """Run all validation tests"""
    print("=" * 60)
    print("State and Context Validation Tests")
    print("=" * 60)

    try:
        test_context_creation()
        test_state_creation()
        test_field_compatibility()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        return True

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"✗ TEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)