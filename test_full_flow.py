"""
Test full flow: SearchAgent → LegalSearchTool
"""

import asyncio
import sys
from pathlib import Path

# Add service directory to path
service_dir = Path(__file__).parent / "backend" / "app" / "service"
sys.path.insert(0, str(service_dir))

from agents.search_agent import SearchAgent
from core.context import create_default_llm_context
from tools import tool_registry


async def test_full_flow():
    """Test SearchAgent → LegalSearchTool integration"""

    print("=" * 80)
    print("Full Flow Test: SearchAgent → LegalSearchTool")
    print("=" * 80)

    # Step 1: Check LegalSearchTool is registered
    print("\n[Step 1] Check LegalSearchTool Registration")
    legal_tool = tool_registry.get("legal_search")

    if legal_tool:
        print("  ✓ LegalSearchTool found in registry")
        print(f"    - Embedding Model: {hasattr(legal_tool, 'embedding_model')}")
        print(f"    - ChromaDB Collection: {hasattr(legal_tool, 'collection')}")
        print(f"    - Metadata Helper: {hasattr(legal_tool, 'metadata_helper')}")
    else:
        print("  ✗ LegalSearchTool NOT found!")
        return

    # Step 2: Test LegalSearchTool directly
    print("\n[Step 2] Test LegalSearchTool Directly")
    try:
        result = await legal_tool.execute(
            query="임대차 보증금",
            params={"category": "2_임대차_전세_월세", "limit": 3}
        )

        print(f"  ✓ Tool execution successful")
        print(f"    - Status: {result.get('status')}")
        print(f"    - Data Source: {result.get('data_source')}")
        print(f"    - Result Count: {result.get('count')}")

        if result.get('data'):
            print(f"    - First Result: {result['data'][0].get('law_title', 'N/A')}")
    except Exception as e:
        print(f"  ✗ Tool execution failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 3: Test SearchAgent with LegalSearchTool
    print("\n[Step 3] Test SearchAgent → LegalSearchTool Integration")
    try:
        # Create SearchAgent
        llm_context = create_default_llm_context()
        search_agent = SearchAgent(llm_context)
        print("  ✓ SearchAgent created")

        # Prepare input (simulating supervisor input)
        input_data = {
            "original_query": "임대차 계약 시 보증금 관련 규정",
            "collection_keywords": ["임대차", "보증금", "계약"],
            "shared_context": {},
            "chat_session_id": "test_session",
            "todos": [],
            "todo_counter": 0
        }

        print("  Running SearchAgent workflow...")
        print(f"    - Query: {input_data['original_query']}")
        print(f"    - Keywords: {input_data['collection_keywords']}")

        # Execute SearchAgent
        result = await search_agent.execute(input_data)

        print(f"  ✓ SearchAgent execution completed")
        print(f"    - Status: {result.get('status')}")
        print(f"    - Next Action: {result.get('next_action')}")

        collected_data = result.get('collected_data', {})
        print(f"    - Collected Data Keys: {list(collected_data.keys())}")

        if 'legal_search' in collected_data:
            legal_results = collected_data['legal_search']
            print(f"    - Legal Search Results: {len(legal_results)} items")
            if legal_results:
                first_item = legal_results[0]
                print(f"    - First Result:")
                print(f"      • Law: {first_item.get('law_title', 'N/A')}")
                print(f"      • Article: {first_item.get('article_number', 'N/A')}")
                print(f"      • Score: {first_item.get('relevance_score', 'N/A')}")

        print(f"    - Search Summary: {result.get('search_summary', 'N/A')}")

    except Exception as e:
        print(f"  ✗ SearchAgent execution failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 4: Verify data flow
    print("\n[Step 4] Verify Data Flow")
    if result.get('status') == 'success':
        print("  ✓ Status: SUCCESS")

        if collected_data and 'legal_search' in collected_data:
            print("  ✓ Data Flow: SearchAgent → LegalSearchTool → Results")
            print("  ✓ collected_data contains legal_search results")
        else:
            print("  ✗ No legal_search data in collected_data")
    else:
        print(f"  ✗ Status: {result.get('status')}")

    print("\n" + "=" * 80)
    print("Full Flow Test Completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_full_flow())
