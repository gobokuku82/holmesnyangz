"""
Initialize ChromaDB with legal documents
Run this script to load all chunked data into ChromaDB
"""

import asyncio
import logging
from app.service.vectordb_service import VectorDBService
from app.service.legal_search_service import LegalSearchService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def initialize_vectordb():
    """Initialize ChromaDB and load all documents"""
    print("=" * 60)
    print("Initializing ChromaDB for Legal Documents")
    print("=" * 60)

    # Initialize VectorDB Service
    vectordb = VectorDBService()

    # Step 1: Initialize ChromaDB
    print("\n1. Initializing ChromaDB...")
    if vectordb.initialize():
        print("[SUCCESS] ChromaDB initialized successfully")
    else:
        print("[ERROR] Failed to initialize ChromaDB")
        return

    # Step 2: Load documents
    print("\n2. Loading documents into ChromaDB...")
    print("This may take a few minutes for 1,700 chunks...")

    doc_count = vectordb.load_documents()
    print(f"[SUCCESS] Loaded {doc_count} chunks into ChromaDB")

    # Step 3: Get statistics
    print("\n3. Database Statistics:")
    stats = vectordb.get_statistics()
    for key, value in stats.items():
        print(f"   - {key}: {value}")

    print("\n" + "=" * 60)
    print("ChromaDB initialization completed!")
    print("=" * 60)

async def test_search():
    """Test the search functionality"""
    print("\n" + "=" * 60)
    print("Testing Search Functionality")
    print("=" * 60)

    # Initialize search service
    search_service = LegalSearchService()
    await search_service.initialize()

    # Test queries
    test_queries = [
        {
            "query": "임차인 보호",
            "params": {
                "is_tenant_protection": True,
                "category": "rental_lease"
            }
        },
        {
            "query": "취득세 계산",
            "params": {
                "is_tax_related": True
            }
        },
        {
            "query": "공인중개사 자격",
            "params": {
                "doc_type": ["법률", "시행령"]
            }
        },
        {
            "query": "전세 보증금",
            "params": {
                "category": "rental_lease"
            }
        }
    ]

    for i, test in enumerate(test_queries, 1):
        print(f"\n{i}. Testing query: '{test['query']}'")
        if test['params']:
            print(f"   Filters: {test['params']}")

        results = await search_service.search(
            query=test['query'],
            **test['params'],
            limit=3
        )

        print(f"   Found {results['total_results']} results")
        for j, result in enumerate(results['results'][:3], 1):
            print(f"   {j}. {result['title']} (Score: {result['relevance_score']:.3f})")

    print("\n" + "=" * 60)
    print("Search testing completed!")
    print("=" * 60)

async def main():
    """Main function"""
    # Initialize VectorDB
    await initialize_vectordb()

    # Test search
    print("\nDo you want to test search functionality? (y/n): ", end="")
    response = input().strip().lower()
    if response == 'y':
        await test_search()

if __name__ == "__main__":
    asyncio.run(main())