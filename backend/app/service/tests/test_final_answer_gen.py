#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Final test to verify complete answer generation flow
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from app.service.supervisor.supervisor import RealEstateSupervisor


async def test_complete_flow():
    """Test the complete answer generation flow"""

    print("=" * 80)
    print("Testing Complete Answer Generation Flow")
    print("=" * 80)

    # Initialize supervisor
    supervisor = RealEstateSupervisor()

    # Test query
    query = "전세금 5% 올리는게 가능한가요?"

    print(f"\nTest Query: {query}")
    print("-" * 60)

    try:
        # Process query
        print("Processing query...")
        result = await supervisor.process_query(
            query=query,
            session_id="test_final"
        )

        print("\nResult structure:")
        print(f"  - Keys: {list(result.keys())}")

        # Check multiple possible response locations
        if "response" in result:
            response = result["response"]
        elif "final_response" in result:
            response = result["final_response"]
            print("\nUsing 'final_response' key instead of 'response'")
        else:
            response = None

        if response:
            # Check if it's an error response
            if isinstance(response, dict):
                if response.get("type") == "error":
                    print(f"\n[ERROR RESPONSE]")
                    print(f"  Status: {response.get('status')}")
                    print(f"  Message: {response.get('message')}")
                    print(f"  Details: {response.get('details')}")

                elif response.get("type") == "answer":
                    print(f"\n[SUCCESS - Natural Language Answer Generated]")
                    print(f"\nAnswer:")
                    print("-" * 40)
                    print(response.get("answer", "No answer found"))
                    print("-" * 40)

                    if "sources" in response:
                        print(f"\nSources: {response['sources']}")

                    if "data" in response:
                        print(f"\nRaw data available: YES")
                        # Show data structure
                        for agent, data in response["data"].items():
                            if isinstance(data, dict):
                                print(f"  - {agent}: {list(data.keys())}")

                elif response.get("type") == "data":
                    print(f"\n[DATA ONLY - No Natural Language Answer]")
                    print("Available data:")
                    data = response.get("data", {})
                    for agent, agent_data in data.items():
                        if isinstance(agent_data, dict):
                            print(f"  - {agent}: {list(agent_data.keys())}")

                else:
                    print(f"\nResponse type: {response.get('type', 'unknown')}")
                    print(f"Response keys: {list(response.keys())}")

            else:
                print(f"\nUnexpected response format: {type(response)}")

        else:
            print("\nNo 'response' key in result")
            print(f"Available data: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}...")

    except Exception as e:
        print(f"\nException occurred: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_complete_flow())