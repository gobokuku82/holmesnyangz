#!/usr/bin/env python3
"""
Quick single query test
"""
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
current_file = Path(__file__)
tests_dir = current_file.parent
service_dir = tests_dir.parent
app_dir = service_dir.parent
backend_dir = app_dir.parent

if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

sys.path.insert(0, str(backend_dir / "app" / "service"))

from supervisor.supervisor import RealEstateSupervisor
from core.context import create_default_llm_context

async def test_query(query: str):
    """Test a single query"""
    print(f"\n=== Testing Query ===")
    print(f"Query: {query}\n")

    # Initialize supervisor
    llm_context = create_default_llm_context()
    supervisor = RealEstateSupervisor(llm_context=llm_context)

    # Create initial state
    initial_state = {
        "query": query,
        "chat_session_id": "test_session",
        "shared_context": {},
        "messages": [],
        "todos": [],
        "todo_counter": 0
    }

    # Run workflow
    app = supervisor.workflow.compile()
    final_state = await app.ainvoke(initial_state)

    # Print key results
    print("=== Results ===")
    print(f"Intent Type: {final_state.get('intent_type')}")
    print(f"Selected Agents: {final_state.get('selected_agents', [])}")
    print(f"\nAgent Results:")
    for agent_name, result in final_state.get('agent_results', {}).items():
        print(f"\n{agent_name}:")
        print(f"  Status: {result.get('status')}")

        # Check for collected_data
        collected_data = result.get('collected_data', {})
        if collected_data:
            print(f"  Collected Data Keys: {list(collected_data.keys())}")
            for tool_name, tool_result in collected_data.items():
                if isinstance(tool_result, list):
                    print(f"    {tool_name}: {len(tool_result)} results")
                elif isinstance(tool_result, dict):
                    print(f"    {tool_name}: {tool_result.get('total_count', 0)} results")
        else:
            print(f"  Collected Data: EMPTY")

    print(f"\nFinal Response:")
    final_response = final_state.get('final_response', {})
    print(json.dumps(final_response, ensure_ascii=False, indent=2))

    print(f"\nTODOs: {len(final_state.get('todos', []))} created")
    for todo in final_state.get('todos', []):
        print(f"  [{todo.get('status')}] {todo.get('task', 'Unknown')}")

    return final_state

if __name__ == "__main__":
    query = "전세금 반환 보증 관련 법률 알려줘"
    asyncio.run(test_query(query))
