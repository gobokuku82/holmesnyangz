"""Test agent_info field with specific property"""
import sys
import asyncio
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.postgre_db import SessionLocal
from app.models.real_estate import RealEstate, RealEstateAgent
from app.service_agent.tools.real_estate_search_tool import RealEstateSearchTool


async def test_agent_info():
    # First find a property with an agent
    session = SessionLocal()
    agent = session.query(RealEstateAgent).first()
    property_id = agent.real_estate_id

    # Get the property details
    property_obj = session.query(RealEstate).filter(RealEstate.id == property_id).first()

    print(f"Testing with Property ID: {property_id}")
    print(f"Property Name: {property_obj.name}")
    print(f"Property Region: {property_obj.region.name if property_obj.region else 'N/A'}")
    print(f"Agent Name: {agent.agent_name}")
    print("="*100)

    session.close()

    # Now test with RealEstateSearchTool
    tool = RealEstateSearchTool()

    # Search with specific region
    region_name = property_obj.region.name if property_obj.region else None
    property_type = property_obj.property_type.value if property_obj.property_type else None

    if region_name:
        result = await tool.search(
            query=f"{region_name} {property_type}",
            params={
                "region": region_name,
                "property_type": property_type,
                "limit": 50,  # Increase limit to find our property
                "include_agent": True  # Explicitly request agent info
            }
        )

        print(f"Search Status: {result['status']}")
        print(f"Found {result['result_count']} properties")

        data = result.get('data', [])

        # Find our target property
        target_property = None
        for item in data:
            if item['id'] == property_id:
                target_property = item
                break

        if target_property:
            print(f"\n✅ Found target property (ID: {property_id}):")
            print(f"  Name: {target_property.get('name')}")
            print(f"  Trust Score: {target_property.get('trust_score')}")

            if 'agent_info' in target_property and target_property['agent_info']:
                print(f"  ✅ Agent Info:")
                print(f"    Agent Name: {target_property['agent_info'].get('agent_name')}")
                print(f"    Company Name: {target_property['agent_info'].get('company_name')}")
                print(f"    Is Direct Trade: {target_property['agent_info'].get('is_direct_trade')}")
            else:
                print(f"  ❌ Agent info is missing!")
        else:
            print(f"\n⚠️ Target property not found in search results")


if __name__ == "__main__":
    asyncio.run(test_agent_info())
