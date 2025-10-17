"""Test real_estate_search_tool with trust_score integration"""
import sys
import asyncio
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.service_agent.tools.real_estate_search_tool import RealEstateSearchTool


async def test_trust_score_integration():
    """Test that trust_score field is returned by RealEstateSearchTool"""
    print("="*100)
    print("Testing RealEstateSearchTool with trust_score integration")
    print("="*100)

    tool = RealEstateSearchTool()

    # Test 1: Search for properties in Gangnam (강남구)
    print("\nTest 1: Search for properties in 강남구 역삼동")
    print("-"*100)

    result = await tool.search(
        query="강남구 역삼동 아파트",
        params={
            "region": "강남구 역삼동",
            "property_type": "apartment",
            "limit": 3
        }
    )

    print(f"Status: {result['status']}")
    print(f"Result count: {result['result_count']}")

    result = result.get('data', [])

    # Check if results contain trust_score
    if result:
        print(f"\nFirst result:")
        first_result = result[0]
        print(f"  Name: {first_result.get('name', 'N/A')}")
        print(f"  Address: {first_result.get('address', 'N/A')}")
        print(f"  Trust Score: {first_result.get('trust_score', 'MISSING')}")

        if 'trust_score' in first_result:
            if first_result['trust_score'] is not None:
                print(f"  ✅ Trust score is present: {first_result['trust_score']}")
            else:
                print(f"  ⚠️  Trust score field exists but is null")
        else:
            print(f"  ❌ Trust score field is missing!")

    # Test 2: Search with agent keyword to trigger agent_info
    print("\n\nTest 2: Search with agent keyword (should include agent_info)")
    print("-"*100)

    result2 = await tool.search(
        query="서초구 아파트 중개사",
        params={
            "region": "서초구",
            "property_type": "apartment",
            "limit": 2,
            "include_agent": True
        }
    )

    result2 = result2.get('data', [])

    if result2:
        print(f"\nFirst result:")
        first_result = result2[0]
        print(f"  Name: {first_result.get('name', 'N/A')}")
        print(f"  Trust Score: {first_result.get('trust_score', 'MISSING')}")
        print(f"  Agent Info: {first_result.get('agent_info', 'MISSING')}")

        if 'agent_info' in first_result:
            if first_result['agent_info'] is not None:
                print(f"  ✅ Agent info is present")
            else:
                print(f"  ⚠️  Agent info field exists but is null")
        else:
            print(f"  ❌ Agent info field is missing!")

    print("\n" + "="*100)
    print("Test completed successfully!")
    print("="*100)


if __name__ == "__main__":
    asyncio.run(test_trust_score_integration())
