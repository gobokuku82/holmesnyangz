"""
Simple test script for Legal Search functionality
"""

import asyncio
from app.service.legal_search_service import LegalSearchService


async def test_search():
    """Test basic search functionality"""

    print("=" * 60)
    print("Testing Legal Search with Real Data")
    print("=" * 60)

    # Initialize service
    service = LegalSearchService()
    print("\n1. Initializing service...")
    await service.initialize()
    print("[SUCCESS] Service initialized")

    # Test queries
    test_cases = [
        ("임차인 보호", {"is_tenant_protection": True}),
        ("취득세", {"is_tax_related": True}),
        ("공인중개사", {}),
        ("전세 보증금", {"category": "rental_lease"}),
        ("매매계약", {"category": "common_transaction"})
    ]

    print("\n2. Running test queries...")
    print("-" * 60)

    for query, filters in test_cases:
        print(f"\nQuery: '{query}'")
        if filters:
            print(f"Filters: {filters}")

        results = await service.search(
            query=query,
            **filters,
            limit=3
        )

        print(f"Results: {results['total_results']} found")

        # Show top result
        if results['results']:
            top_result = results['results'][0]
            print(f"Top match: {top_result['title']}")
            print(f"Score: {top_result['relevance_score']:.3f}")
            text_preview = top_result['text'][:100] + "..." if len(top_result['text']) > 100 else top_result['text']
            print(f"Text: {text_preview}")

    # Get statistics
    print("\n" + "=" * 60)
    print("Database Statistics:")
    stats = service.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_search())