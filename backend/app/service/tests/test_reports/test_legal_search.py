"""
Test script for Legal Search Tool with real database
"""

import asyncio
import sys
from pathlib import Path

# Add service directory to path
service_dir = Path(__file__).parent.parent
if str(service_dir) not in sys.path:
    sys.path.insert(0, str(service_dir))

from tools.legal_search_tool import LegalSearchTool


async def test_legal_search():
    """Test legal search with real database"""

    print("=" * 80)
    print("Legal Search Tool - Real Database Test")
    print("=" * 80)

    # Initialize tool with real DB
    tool = LegalSearchTool(use_mock_data=False)

    # Test queries
    test_cases = [
        {
            "name": "임대차 보증금 관련 검색",
            "query": "임대차 계약 시 보증금 관련 규정",
            "params": {
                "category": "2_임대차_전세_월세",
                "limit": 3
            }
        },
        {
            "name": "공인중개사법 시행령 검색",
            "query": "중개보수",
            "params": {
                "doc_type": "시행령",
                "limit": 3
            }
        },
        {
            "name": "임차인 보호 조항 검색",
            "query": "임차인의 권리",
            "params": {
                "is_tenant_protection": True,
                "limit": 3
            }
        },
        {
            "name": "일반 법률 검색 (자동 필터)",
            "query": "전세 계약 갱신",
            "params": {
                "limit": 3
            }
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"Test {i}: {test_case['name']}")
        print(f"{'=' * 80}")
        print(f"Query: {test_case['query']}")
        print(f"Params: {test_case['params']}")
        print()

        try:
            # Execute search
            result = await tool.execute(
                query=test_case['query'],
                params=test_case['params']
            )

            # Display results
            print(f"Status: {result.get('status')}")
            print(f"Data Source: {result.get('data_source')}")
            print(f"Results Count: {result.get('count')}")

            if result.get('status') == 'success' and result.get('data'):
                print(f"\nTop Results:")
                for j, item in enumerate(result['data'][:3], 1):
                    print(f"\n  {j}. [{item.get('doc_type')}] {item.get('law_title')}")
                    print(f"     {item.get('article_number')} - {item.get('article_title')}")
                    print(f"     Relevance: {item.get('relevance_score'):.3f}")
                    print(f"     Content: {item.get('content')[:150]}...")
            else:
                print(f"Error or no data: {result.get('error', 'Unknown')}")

        except Exception as e:
            print(f"Test failed with error: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 80}")
    print("All tests completed!")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    asyncio.run(test_legal_search())
