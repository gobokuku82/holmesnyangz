"""
Test hierarchical TODO management system
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
from core.todo_types import get_todo_summary, find_todo


async def test_todo_hierarchy():
    """Test hierarchical TODO system"""

    print("="*70)
    print("HIERARCHICAL TODO SYSTEM TEST")
    print("="*70)

    # Initialize supervisor
    print("\nInitializing supervisor...")
    supervisor = RealEstateSupervisor(llm_context=TestConfig.get_llm_context())
    print("[OK] Supervisor initialized")

    # Test query
    query = "강남구 아파트 시세 정보 찾아줘"
    print(f"\nTest Query: {query}")
    print("-"*70)

    try:
        # Process query
        print("\nProcessing query with TODO tracking...")
        result = await supervisor.process_query(
            query=query,
            session_id="test_todo",
            llm_context=TestConfig.get_llm_context()
        )

        # Check if todos were created
        todos = result.get("todos", [])

        if todos:
            print(f"\n[SUCCESS] TODOs created: {len(todos)} main TODO(s)")

            # Print TODO hierarchy
            print("\n" + "="*50)
            print("TODO HIERARCHY")
            print("="*50)

            for main_todo in todos:
                print(f"\n[MAIN] [{main_todo['status']}] {main_todo['task']}")
                print(f"   ID: {main_todo['id']}")
                print(f"   Agent: {main_todo.get('agent', 'N/A')}")

                # Print subtodos
                subtodos = main_todo.get("subtodos", [])
                if subtodos:
                    print(f"   Subtodos ({len(subtodos)}):")
                    for sub in subtodos:
                        print(f"   └── [{sub['status']}] {sub['task']}")

                        # Print tool todos
                        tool_todos = sub.get("tool_todos", [])
                        if tool_todos:
                            print(f"       Tool TODOs ({len(tool_todos)}):")
                            for tool_todo in tool_todos:
                                print(f"       └── [{tool_todo['status']}] {tool_todo['task']}")

            # Get summary
            summary = get_todo_summary(todos)
            print("\n" + "="*50)
            print("TODO SUMMARY")
            print("="*50)
            print(f"Total: {summary['total']}")
            print(f"Completed: {summary['completed']}")
            print(f"In Progress: {summary['in_progress']}")
            print(f"Pending: {summary['pending']}")
            print(f"Failed: {summary['failed']}")
            print(f"Progress: {summary['progress_percent']}%")
            print(f"Summary: {summary['summary']}")

        else:
            print("[WARNING] No TODOs were created")

        # Check final response
        if result.get("final_response"):
            print("\n" + "="*50)
            print("FINAL RESPONSE")
            print("="*50)

            final = result["final_response"]
            if "message" in final:
                print(f"Message: {final['message'][:100]}...")
            if "data" in final:
                print(f"Data collected: {len(final.get('data', {}))} sources")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70)
    print("[TEST COMPLETE]")
    print("="*70)


async def test_simple_todo_flow():
    """Test simple TODO flow without full execution"""

    print("\n" + "="*70)
    print("SIMPLE TODO FLOW TEST")
    print("="*70)

    from core.todo_types import (
        create_todo_dict, update_todo_status,
        find_todo, get_todo_summary, merge_todos
    )

    # Create initial todos
    todos = []

    # Create main TODO
    main_todo = create_todo_dict(
        "main_1",
        "supervisor",
        "Execute search_agent",
        agent="search_agent",
        subtodos=[]
    )
    todos.append(main_todo)

    print("\n1. Created main TODO")
    print(f"   {main_todo}")

    # Agent adds subtodos
    subtodos = [
        create_todo_dict("sub_1", "agent", "Create search plan", "completed"),
        create_todo_dict("sub_2", "agent", "Execute tools", "in_progress"),
        create_todo_dict("sub_3", "agent", "Process results", "pending")
    ]
    main_todo["subtodos"] = subtodos

    print("\n2. Agent added subtodos")
    for sub in subtodos:
        print(f"   [{sub['status']}] {sub['task']}")

    # Add tool todos
    tool_todos = [
        create_todo_dict("tool_1", "tool", "legal_search", "completed"),
        create_todo_dict("tool_2", "tool", "loan_search", "pending")
    ]
    subtodos[1]["tool_todos"] = tool_todos

    print("\n3. Added tool TODOs to 'Execute tools' subtodo")
    for tool in tool_todos:
        print(f"   [{tool['status']}] {tool['task']}")

    # Get summary
    summary = get_todo_summary(todos)
    print(f"\n4. Summary: {summary['summary']}")
    print(f"   Details: Total={summary['total']}, Completed={summary['completed']}, "
          f"In Progress={summary['in_progress']}, Pending={summary['pending']}")

    # Test merge
    new_todos = [main_todo.copy()]
    new_todos[0]["subtodos"][2]["status"] = "completed"  # Update "Process results"

    merged = merge_todos(todos, new_todos)
    print(f"\n5. After merge (updated 'Process results' to completed)")

    summary = get_todo_summary(merged)
    print(f"   New summary: {summary['summary']}")

    print("\n[TEST COMPLETE]")


if __name__ == "__main__":
    print("\nRunning TODO hierarchy tests...\n")

    # Run simple test first
    asyncio.run(test_simple_todo_flow())

    # Auto-run full integration test
    print("\n" + "="*70)
    print("\nRunning full integration test...")
    asyncio.run(test_todo_hierarchy())