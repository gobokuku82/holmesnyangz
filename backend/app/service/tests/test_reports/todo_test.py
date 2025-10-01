"""
TODO System Test
Tests the hierarchical TODO management system functionality
"""

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

print("="*70)
print("TODO SYSTEM TEST")
print("="*70)
print(f"\nTest directory: {current_dir}")
print(f"Service directory: {service_dir}\n")

# Track results
test_results = []

def test_case(name, test_func):
    """Run a test case and track results"""
    print(f"\n[TEST] {name}")
    print("-" * 50)
    try:
        result = test_func()
        if result:
            print(f"[OK] {name} passed")
            test_results.append(("PASS", name))
            return True
        else:
            print(f"[FAIL] {name} failed")
            test_results.append(("FAIL", name))
            return False
    except Exception as e:
        print(f"[ERROR] {name} - {e}")
        test_results.append(("ERROR", name))
        return False

# Import TODO functions
try:
    from core.todo_types import (
        create_todo_dict,
        update_todo_status,
        find_todo,
        get_todo_summary,
        merge_todos,
        TodoStatus,
        TodoPriority,
        TodoManager
    )
    print("[OK] TODO modules imported successfully")
except ImportError as e:
    print(f"[FATAL] Could not import TODO modules: {e}")
    sys.exit(1)

# ============================================================================
# TEST CASES
# ============================================================================

def test_create_todo():
    """Test creating TODO items"""
    # Create basic TODO
    todo = create_todo_dict(
        todo_id="test_1",
        level="supervisor",
        task="Test task",
        status="pending"
    )

    # Verify structure
    assert todo["id"] == "test_1", "ID mismatch"
    assert todo["level"] == "supervisor", "Level mismatch"
    assert todo["task"] == "Test task", "Task mismatch"
    assert todo["status"] == "pending", "Status mismatch"
    assert "created_at" in todo, "Missing created_at"
    assert "updated_at" in todo, "Missing updated_at"

    print(f"  Created TODO: {todo['id']} - {todo['task']}")

    # Create TODO with extra fields
    todo2 = create_todo_dict(
        todo_id="test_2",
        level="agent",
        task="Agent task",
        status="in_progress",
        agent="search_agent",
        custom_field="custom_value"
    )

    assert todo2["agent"] == "search_agent", "Custom field not added"
    assert todo2["custom_field"] == "custom_value", "Custom field not added"

    print(f"  Created TODO with custom fields: {todo2['id']}")
    return True


def test_update_status():
    """Test updating TODO status"""
    todos = [
        create_todo_dict("main_1", "supervisor", "Main task", "pending"),
        create_todo_dict("main_2", "supervisor", "Another task", "pending")
    ]

    # Update first TODO to in_progress
    todos = update_todo_status(todos, "main_1", "in_progress")

    # Verify update
    todo1 = find_todo(todos, todo_id="main_1")
    assert todo1["status"] == "in_progress", "Status not updated"
    assert "started_at" in todo1, "Missing started_at timestamp"

    print(f"  Updated main_1 to in_progress")

    # Update to completed
    todos = update_todo_status(todos, "main_1", "completed")
    todo1 = find_todo(todos, todo_id="main_1")
    assert todo1["status"] == "completed", "Status not completed"
    assert "completed_at" in todo1, "Missing completed_at timestamp"

    print(f"  Updated main_1 to completed")

    # Update with error
    todos = update_todo_status(todos, "main_2", "failed", "Test error")
    todo2 = find_todo(todos, todo_id="main_2")
    assert todo2["status"] == "failed", "Status not failed"
    assert todo2["error"] == "Test error", "Error message not set"

    print(f"  Updated main_2 to failed with error")
    return True


def test_hierarchical_structure():
    """Test hierarchical TODO structure"""
    # Create main TODO with subtodos
    main_todo = create_todo_dict(
        "main_1",
        "supervisor",
        "Execute agent",
        agent="search_agent",
        subtodos=[]
    )

    # Add subtodos
    subtodos = [
        create_todo_dict("sub_1", "agent", "Plan", "completed"),
        create_todo_dict("sub_2", "agent", "Execute", "in_progress"),
        create_todo_dict("sub_3", "agent", "Process", "pending")
    ]
    main_todo["subtodos"] = subtodos

    # Add tool todos to second subtodo
    tool_todos = [
        create_todo_dict("tool_1", "tool", "Tool A", "completed"),
        create_todo_dict("tool_2", "tool", "Tool B", "pending")
    ]
    subtodos[1]["tool_todos"] = tool_todos

    # Create list with main TODO
    todos = [main_todo]

    # Test finding at different levels
    found_main = find_todo(todos, todo_id="main_1")
    assert found_main is not None, "Main TODO not found"
    print(f"  Found main TODO: {found_main['id']}")

    found_sub = find_todo(todos, todo_id="sub_2")
    assert found_sub is not None, "Subtodo not found"
    print(f"  Found subtodo: {found_sub['id']}")

    found_tool = find_todo(todos, todo_id="tool_1")
    assert found_tool is not None, "Tool TODO not found"
    print(f"  Found tool TODO: {found_tool['id']}")

    # Test finding by agent
    found_agent = find_todo(todos, agent="search_agent")
    assert found_agent is not None, "TODO not found by agent"
    print(f"  Found TODO by agent: {found_agent['id']}")

    return True


def test_todo_summary():
    """Test TODO summary calculation"""
    # Create hierarchical structure
    todos = [
        create_todo_dict("main_1", "supervisor", "Main 1", "completed",
                        subtodos=[
                            create_todo_dict("sub_1", "agent", "Sub 1", "completed"),
                            create_todo_dict("sub_2", "agent", "Sub 2", "completed")
                        ]),
        create_todo_dict("main_2", "supervisor", "Main 2", "in_progress",
                        subtodos=[
                            create_todo_dict("sub_3", "agent", "Sub 3", "in_progress",
                                           tool_todos=[
                                               create_todo_dict("tool_1", "tool", "Tool 1", "completed"),
                                               create_todo_dict("tool_2", "tool", "Tool 2", "pending")
                                           ]),
                            create_todo_dict("sub_4", "agent", "Sub 4", "pending")
                        ]),
        create_todo_dict("main_3", "supervisor", "Main 3", "pending")
    ]

    # Get summary
    summary = get_todo_summary(todos)

    # Verify counts
    assert summary["total"] == 8, f"Total count wrong: {summary['total']} != 8"
    assert summary["completed"] == 4, f"Completed count wrong: {summary['completed']} != 4"
    assert summary["in_progress"] == 2, f"In-progress count wrong: {summary['in_progress']} != 2"
    assert summary["pending"] == 2, f"Pending count wrong: {summary['pending']} != 2"

    print(f"  Total: {summary['total']}")
    print(f"  Completed: {summary['completed']}")
    print(f"  In Progress: {summary['in_progress']}")
    print(f"  Pending: {summary['pending']}")
    print(f"  Progress: {summary['progress_percent']}%")
    print(f"  Summary: {summary['summary']}")

    return True


def test_merge_todos():
    """Test merging TODO lists"""
    # Create initial todos
    todos1 = [
        create_todo_dict("main_1", "supervisor", "Task 1", "pending"),
        create_todo_dict("main_2", "supervisor", "Task 2", "in_progress")
    ]

    # Create updates
    todos2 = [
        create_todo_dict("main_1", "supervisor", "Task 1", "completed"),  # Update existing
        create_todo_dict("main_3", "supervisor", "Task 3", "pending")     # Add new
    ]

    # Merge
    merged = merge_todos(todos1, todos2)

    # Verify merge
    assert len(merged) == 3, f"Merge count wrong: {len(merged)} != 3"

    todo1 = find_todo(merged, todo_id="main_1")
    assert todo1["status"] == "completed", "TODO not updated in merge"

    todo3 = find_todo(merged, todo_id="main_3")
    assert todo3 is not None, "New TODO not added in merge"

    print(f"  Merged {len(todos1)} + {len(todos2)} = {len(merged)} TODOs")
    print(f"  main_1 status updated: pending -> completed")
    print(f"  main_3 added as new TODO")

    return True


def test_merge_nested_todos():
    """Test merging nested TODO structures"""
    # Create initial structure
    todos1 = [
        create_todo_dict("main_1", "supervisor", "Main", "pending",
                        subtodos=[
                            create_todo_dict("sub_1", "agent", "Sub 1", "pending"),
                            create_todo_dict("sub_2", "agent", "Sub 2", "pending")
                        ])
    ]

    # Create update with modified subtodos
    todos2 = [
        create_todo_dict("main_1", "supervisor", "Main", "in_progress",
                        subtodos=[
                            create_todo_dict("sub_1", "agent", "Sub 1", "completed"),  # Update
                            create_todo_dict("sub_3", "agent", "Sub 3", "pending")     # Add new
                        ])
    ]

    # Merge
    merged = merge_todos(todos1, todos2)

    # Verify nested merge
    main = find_todo(merged, todo_id="main_1")
    assert main["status"] == "in_progress", "Main TODO not updated"
    assert len(main["subtodos"]) == 3, f"Subtodos not merged correctly: {len(main['subtodos'])} != 3"

    sub1 = find_todo(merged, todo_id="sub_1")
    assert sub1["status"] == "completed", "Subtodo not updated"

    sub3 = find_todo(merged, todo_id="sub_3")
    assert sub3 is not None, "New subtodo not added"

    print(f"  Merged nested structure successfully")
    print(f"  main_1 updated: pending -> in_progress")
    print(f"  sub_1 updated: pending -> completed")
    print(f"  sub_3 added as new subtodo")

    return True


def test_todo_manager():
    """Test TodoManager class"""
    manager = TodoManager(level="supervisor")

    # Add TODOs
    from core.todo_types import create_supervisor_todo

    todo1 = create_supervisor_todo("search_agent", "데이터 수집", TodoPriority.HIGH)
    todo2 = create_supervisor_todo("analysis_agent", "데이터 분석",
                                  TodoPriority.MEDIUM, [todo1.id])

    manager.add_todo(todo1)
    manager.add_todo(todo2)

    # Get pending TODOs
    pending = manager.get_pending_todos()
    assert len(pending) == 2, f"Pending count wrong: {len(pending)} != 2"

    # Update status
    manager.update_status(todo1.id, TodoStatus.COMPLETED)

    # Check if todo2 can start now (dependency satisfied)
    next_todo = manager.get_next_todo()
    assert next_todo.id == todo2.id, "Next TODO should be todo2"

    # Get progress
    progress = manager.get_progress()
    assert progress["completed"] == 1, "Completed count wrong"
    assert progress["pending"] == 1, "Pending count wrong"

    print(f"  TodoManager test passed")
    print(f"  Added {len(manager.todos)} TODOs")
    print(f"  Progress: {manager.get_summary()}")

    return True


# ============================================================================
# RUN TESTS
# ============================================================================

print("\n" + "="*70)
print("RUNNING TODO SYSTEM TESTS")
print("="*70)

# Run all test cases
test_case("Create TODO", test_create_todo)
test_case("Update Status", test_update_status)
test_case("Hierarchical Structure", test_hierarchical_structure)
test_case("TODO Summary", test_todo_summary)
test_case("Merge TODOs", test_merge_todos)
test_case("Merge Nested TODOs", test_merge_nested_todos)
test_case("TodoManager Class", test_todo_manager)

# ============================================================================
# TEST SUMMARY
# ============================================================================

print("\n" + "="*70)
print("TEST SUMMARY")
print("="*70)

total = len(test_results)
passed = len([r for r in test_results if r[0] == "PASS"])
failed = len([r for r in test_results if r[0] == "FAIL"])
errors = len([r for r in test_results if r[0] == "ERROR"])

print(f"\nTotal tests: {total}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Errors: {errors}")
print(f"Success rate: {(passed/total*100):.1f}%")

# Show failed tests
if failed > 0 or errors > 0:
    print("\n" + "-"*70)
    print("FAILED TESTS")
    print("-"*70)
    for status, name in test_results:
        if status in ["FAIL", "ERROR"]:
            print(f"  [{status}] {name}")

# Final verdict
print("\n" + "="*70)
if failed == 0 and errors == 0:
    print("[SUCCESS] All TODO system tests passed!")
else:
    print(f"[FAILURE] {failed + errors} test(s) failed.")
print("="*70)

# Return status for CI/CD
sys.exit(0 if (failed == 0 and errors == 0) else 1)