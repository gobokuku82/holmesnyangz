"""
Debug TODO creation and transmission in SearchAgent
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
from agents.search_agent import SearchAgent
from core.context import create_default_llm_context
from core.todo_types import create_todo_dict, get_todo_summary
from dotenv import load_dotenv
import os

# Load environment
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[OK] Loaded environment from: {env_path}")


async def debug_search_agent_todos():
    """Debug TODO creation in SearchAgent"""
    print("\n" + "="*70)
    print("DEBUG: SEARCHAGENT TODO CREATION")
    print("="*70)

    try:
        # Create LLM context
        llm_context = create_default_llm_context()
        print("[OK] LLM context created")

        # Create search agent
        search_agent = SearchAgent(llm_context)
        print("[OK] SearchAgent created")

        # Create a parent TODO manually
        parent_todo = create_todo_dict(
            todo_id="main_0",
            todo_type="agent",
            task="Execute search_agent",
            level="main",  # Add level parameter
            status="in_progress",
            agent="search_agent"
        )

        # Initial todos list with parent
        initial_todos = [parent_todo]

        print("\n[DEBUG] Initial TODO structure:")
        print(json.dumps(parent_todo, indent=2, ensure_ascii=False))

        # Test input with explicit parent TODO
        test_input = {
            "original_query": "강남구 아파트 시세 알려줘",
            "collection_keywords": ["매물", "시세", "가격"],
            "shared_context": {},
            "chat_session_id": "debug_session",
            "parent_todo_id": "main_0",  # Explicitly set parent ID
            "todos": initial_todos,       # Pass initial todos
            "todo_counter": 1              # Start counter at 1
        }

        print("\n[DEBUG] Test input:")
        print(f"  parent_todo_id: {test_input['parent_todo_id']}")
        print(f"  todo_counter: {test_input['todo_counter']}")
        print(f"  todos length: {len(test_input['todos'])}")

        print("\n[EXECUTING] Running SearchAgent.execute...")

        # Execute the agent
        result = await search_agent.execute(test_input)

        print("\n[RESULT] Execution completed")
        print(f"  Status: {result.get('status')}")
        print(f"  Search Summary: {result.get('search_summary', 'N/A')}")

        # Check returned TODOs
        returned_todos = result.get("todos", [])
        print(f"\n[DEBUG] Returned TODOs: {len(returned_todos)} items")

        if returned_todos:
            # Check if parent TODO was updated
            updated_parent = None
            for todo in returned_todos:
                if todo.get("id") == "main_0":
                    updated_parent = todo
                    break

            if updated_parent:
                print("\n[DEBUG] Parent TODO found and updated:")
                print(f"  Status: {updated_parent.get('status')}")
                print(f"  Subtodos: {len(updated_parent.get('subtodos', []))}")

                if updated_parent.get('subtodos'):
                    print("\n[DEBUG] Subtodos created:")
                    for subtodo in updated_parent['subtodos']:
                        print(f"    - {subtodo.get('task')} [{subtodo.get('status')}]")
                        if subtodo.get('tool_todos'):
                            for tool_todo in subtodo['tool_todos']:
                                print(f"        * {tool_todo.get('task')} [{tool_todo.get('status')}]")
                else:
                    print("\n[WARNING] No subtodos created in parent TODO")
            else:
                print("\n[WARNING] Parent TODO not found in returned TODOs")

            # Show full TODO structure
            print("\n[DEBUG] Full returned TODO structure:")
            print(json.dumps(returned_todos, indent=2, ensure_ascii=False)[:2000])

            # Get summary
            summary = get_todo_summary(returned_todos)
            print(f"\n[DEBUG] TODO Summary: {summary['summary']}")
        else:
            print("\n[ERROR] No TODOs returned!")

        # Check if we got data
        collected_data = result.get("collected_data", {})
        if collected_data:
            print(f"\n[DEBUG] Data collected from {len(collected_data)} sources:")
            for source, data in collected_data.items():
                if isinstance(data, list):
                    print(f"  - {source}: {len(data)} items")
                else:
                    print(f"  - {source}: data collected")

        return True

    except Exception as e:
        print(f"\n[ERROR] Debug test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run debug test"""
    print("\n" + "="*70)
    print("SEARCHAGENT TODO DEBUG TEST")
    print("="*70)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    success = await debug_search_agent_todos()

    if success:
        print("\n[SUCCESS] Debug test completed successfully")
    else:
        print("\n[FAILURE] Debug test failed")

    return success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)