#!/usr/bin/env python3
"""
Test for non-existent laws
데이터베이스에 없는 법률들이 제대로 처리되는지 테스트
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.service.tools.legal_search_tool import LegalSearchTool


async def test_nonexistent_laws():
    """Test queries for laws that don't exist in database"""

    tool = LegalSearchTool()

    # 테스트할 없는 법률들
    nonexistent_queries = [
        "민법 제618조",
        "상가건물 임대차보호법 제10조",
        "소득세법 제89조",
        "종합부동산세법 제7조",
        "지방세법 제11조"
    ]

    print("=" * 60)
    print("Testing Non-Existent Laws")
    print("=" * 60)

    success_count = 0

    for i, query in enumerate(nonexistent_queries, 1):
        print(f"\n[{i}] Testing: {query}")

        try:
            result = await tool.search(query)

            # Check if we got the "not found" message
            if result["data"] and len(result["data"]) == 1:
                first_item = result["data"][0]
                if first_item.get("type") == "error":
                    print(f"  [OK] Correctly returned: {first_item['message']}")
                    success_count += 1
                else:
                    print(f"  [FAIL] Wrong result: {first_item.get('law_title', 'Unknown')}")
            elif result["total_count"] == 0:
                print(f"  [OK] Correctly returned 0 results")
                success_count += 1
            else:
                print(f"  [FAIL] Incorrectly returned {result['total_count']} results")
                if result["data"]:
                    print(f"     First result: {result['data'][0].get('law_title', 'Unknown')}")

        except Exception as e:
            print(f"  [ERROR] Error: {e}")

    print("\n" + "=" * 60)
    print(f"Results: {success_count}/{len(nonexistent_queries)} passed")
    print(f"Success rate: {success_count/len(nonexistent_queries)*100:.1f}%")
    print("=" * 60)

    return success_count == len(nonexistent_queries)


if __name__ == "__main__":
    success = asyncio.run(test_nonexistent_laws())
    sys.exit(0 if success else 1)