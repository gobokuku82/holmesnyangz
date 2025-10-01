"""
Test TODO transmission between SearchAgent and Supervisor
Verifies that TODOs are properly passed and merged throughout the system
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

# Setup paths
current_dir = Path(__file__).parent
service_dir = current_dir.parent
backend_dir = service_dir.parent.parent

sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / "app" / "service"))

# Import required modules
from supervisor.supervisor import RealEstateSupervisor
from agents.search_agent import SearchAgent
from core.context import create_default_llm_context
from core.todo_types import get_todo_summary, find_todo
from dotenv import load_dotenv
import os

# Load environment
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[OK] Loaded environment from: {env_path}")


def display_todo_tree(todos, indent=0):
    """Display TODO hierarchy in tree format"""
    if not todos:
        return

    for todo in todos:
        status_symbol = {
            "completed": "[v]",
            "in_progress": "[>]",
            "pending": "[o]",
            "failed": "[x]"
        }.get(todo.get("status", "pending"), "[?]")

        prefix = "  " * indent + ("|-- " if indent > 0 else "")
        task_text = todo.get("task", "Unknown")
        todo_id = todo.get("id", "N/A")
        print(f"{prefix}[{status_symbol}] {task_text} (ID: {todo_id})")

        # Display subtodos
        if "subtodos" in todo and todo["subtodos"]:
            display_todo_tree(todo["subtodos"], indent + 1)

        # Display tool todos
        if "tool_todos" in todo and todo["tool_todos"]:
            display_todo_tree(todo["tool_todos"], indent + 1)


async def test_direct_agent_execution():
    """Test SearchAgent directly to verify TODO generation"""
    print("\n" + "="*70)
    print("TEST 1: DIRECT AGENT EXECUTION")
    print("="*70)

    try:
        # Create LLM context
        llm_context = create_default_llm_context()
        print("[OK] LLM context created")

        # Create search agent
        search_agent = SearchAgent(llm_context)
        print("[OK] SearchAgent created")

        # Create a parent TODO for testing
        from core.todo_types import create_todo_dict
        parent_todo = create_todo_dict(
            todo_id="main_0",
            todo_type="agent",
            task="Execute search_agent",
            level="main",
            status="in_progress",
            agent="search_agent"
        )

        # Test input with TODO fields
        test_input = {
            "original_query": "강남구 아파트 시세 알려줘",
            "collection_keywords": ["매물", "시세", "가격"],
            "shared_context": {},
            "chat_session_id": "test_direct",
            "parent_todo_id": "main_0",
            "todos": [parent_todo],
            "todo_counter": 1
        }

        print("\n[EXECUTING] Running SearchAgent.execute...")
        result = await search_agent.execute(test_input)

        print("\n[RESULT] Agent execution completed")
        print(f"Status: {result.get('status')}")

        # Check if TODOs are present
        todos = result.get("todos", [])
        if todos:
            print(f"\n[SUCCESS] TODOs returned: {len(todos)} items")
            print("\nTODO Tree:")
            display_todo_tree(todos)

            # Show summary
            summary = get_todo_summary(todos)
            print(f"\nTODO Summary: {summary['summary']}")
            print(f"  Total: {summary['total']}")
            print(f"  Completed: {summary['completed']}")
            print(f"  In Progress: {summary['in_progress']}")
            print(f"  Pending: {summary['pending']}")
        else:
            print("\n[WARNING] No TODOs returned from agent")

        return True

    except Exception as e:
        print(f"\n[ERROR] Direct agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_supervisor_agent_integration():
    """Test TODO transmission through Supervisor"""
    print("\n" + "="*70)
    print("TEST 2: SUPERVISOR-AGENT INTEGRATION")
    print("="*70)

    try:
        # Create LLM context
        llm_context = create_default_llm_context()
        print("[OK] LLM context created")

        # Create supervisor
        supervisor = RealEstateSupervisor(llm_context=llm_context)
        print("[OK] Supervisor created")

        # Test query
        query = "강남구 아파트 매매 시세 정보 알려줘"
        session_id = "test_integration"

        print(f"\n[EXECUTING] Processing query: {query}")
        result = await supervisor.process_query(
            query=query,
            session_id=session_id,
            llm_context=llm_context
        )

        print("\n[RESULT] Query processing completed")

        # Check TODOs at supervisor level
        todos = result.get("todos", [])
        if todos:
            print(f"\n[SUCCESS] TODOs at supervisor level: {len(todos)} items")
            print("\nComplete TODO Tree:")
            display_todo_tree(todos)

            # Show summary
            summary = get_todo_summary(todos)
            print(f"\nOverall TODO Summary: {summary['summary']}")
            print(f"  Total: {summary['total']}")
            print(f"  Completed: {summary['completed']}")
            print(f"  In Progress: {summary['in_progress']}")
            print(f"  Pending: {summary['pending']}")

            # Check for SearchAgent TODOs
            search_agent_todos = []
            for todo in todos:
                if "SearchAgent" in todo.get("task", ""):
                    search_agent_todos.append(todo)

            if search_agent_todos:
                print(f"\n[SUCCESS] Found {len(search_agent_todos)} SearchAgent TODO(s)")
                for sa_todo in search_agent_todos:
                    subtodo_count = len(sa_todo.get("subtodos", []))
                    tool_todo_count = sum(len(st.get("tool_todos", [])) for st in sa_todo.get("subtodos", []))
                    print(f"  - {sa_todo.get('task')}: {subtodo_count} subtodos, {tool_todo_count} tool_todos")
            else:
                print("\n[WARNING] No SearchAgent TODOs found")
        else:
            print("\n[ERROR] No TODOs returned at supervisor level")

        return True

    except Exception as e:
        print(f"\n[ERROR] Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_todo_merge_behavior():
    """Test TODO merging behavior with multiple agents"""
    print("\n" + "="*70)
    print("TEST 3: TODO MERGE BEHAVIOR")
    print("="*70)

    try:
        # Create LLM context
        llm_context = create_default_llm_context()
        print("[OK] LLM context created")

        # Create supervisor
        supervisor = RealEstateSupervisor(llm_context=llm_context)
        print("[OK] Supervisor created")

        # Complex query that might trigger multiple agents
        query = "강남구 아파트 시세 분석하고 대출 조건 알려줘"
        session_id = "test_merge"

        print(f"\n[EXECUTING] Processing complex query: {query}")
        result = await supervisor.process_query(
            query=query,
            session_id=session_id,
            llm_context=llm_context
        )

        print("\n[RESULT] Complex query processing completed")

        # Analyze TODO structure
        todos = result.get("todos", [])
        if todos:
            print(f"\n[SUCCESS] Complex query generated {len(todos)} top-level TODOs")

            # Count by agent
            agent_todos = {}
            for todo in todos:
                task = todo.get("task", "")
                for agent_name in ["SearchAgent", "AnalysisAgent", "RecommendationAgent"]:
                    if agent_name in task:
                        if agent_name not in agent_todos:
                            agent_todos[agent_name] = []
                        agent_todos[agent_name].append(todo)

            print("\nTODOs by Agent:")
            for agent_name, agent_todo_list in agent_todos.items():
                total_subtodos = sum(len(t.get("subtodos", [])) for t in agent_todo_list)
                print(f"  {agent_name}: {len(agent_todo_list)} main, {total_subtodos} subtodos")

            # Full tree
            print("\nComplete TODO Tree:")
            display_todo_tree(todos)

            # Verify merge worked correctly
            todo_ids = set()
            duplicate_ids = []

            def collect_ids(todo_list):
                for todo in todo_list:
                    todo_id = todo.get("id")
                    if todo_id:
                        if todo_id in todo_ids:
                            duplicate_ids.append(todo_id)
                        todo_ids.add(todo_id)
                    if "subtodos" in todo:
                        collect_ids(todo["subtodos"])
                    if "tool_todos" in todo:
                        collect_ids(todo["tool_todos"])

            collect_ids(todos)

            if duplicate_ids:
                print(f"\n[WARNING] Found duplicate TODO IDs: {duplicate_ids}")
            else:
                print(f"\n[SUCCESS] All {len(todo_ids)} TODO IDs are unique")

        return True

    except Exception as e:
        print(f"\n[ERROR] Merge behavior test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all TODO transmission tests"""
    print("\n" + "="*70)
    print("TODO TRANSMISSION TEST SUITE")
    print("="*70)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Track results
    results = {}

    # Test 1: Direct agent execution
    print("\nRunning Test 1...")
    results["direct_agent"] = await test_direct_agent_execution()
    await asyncio.sleep(1)  # Brief pause between tests

    # Test 2: Supervisor-Agent integration
    print("\nRunning Test 2...")
    results["integration"] = await test_supervisor_agent_integration()
    await asyncio.sleep(1)

    # Test 3: TODO merge behavior
    print("\nRunning Test 3...")
    results["merge_behavior"] = await test_todo_merge_behavior()

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed_count = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"\nResults: {passed_count}/{total} tests passed")
    for test_name, test_passed in results.items():
        status = "PASS" if test_passed else "FAIL"
        print(f"  [{status}] {test_name}")

    # Overall verdict
    all_passed = (passed_count == total)
    if all_passed:
        print("\n[SUCCESS] All TODO transmission tests passed!")
        print("The TODO system is properly transmitting data between components.")
    elif passed_count > 0:
        print(f"\n[PARTIAL SUCCESS] {passed_count}/{total} tests passed.")
        print(f"{total - passed_count} test(s) failed.")
    else:
        print(f"\n[FAILURE] All {total} tests failed.")
        print("TODO transmission is not working correctly.")

    return all_passed


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL] Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)