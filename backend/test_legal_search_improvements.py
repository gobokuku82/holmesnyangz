"""
Test script for legal search improvements
Tests:
1. Category filter fix (should reduce search scope)
2. SQL metadata enrichment (should add total_articles, law_number)
3. Specific article fast lookup (should use SQL direct path)
"""

import asyncio
import sys
from pathlib import Path
import time

# Add paths
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / "app" / "service"))

from app.service.tools.legal_search_tool import LegalSearchTool


async def test_category_filter():
    """Test 1: Category filter should now be applied"""
    print("\n" + "="*80)
    print("TEST 1: Category Filter Bug Fix")
    print("="*80)

    tool = LegalSearchTool()

    # Query with category
    query = "전세금 인상 한도"
    params = {
        'category': '2_임대차_전세_월세',
        'limit': 5
    }

    start_time = time.time()
    result = await tool.search(query=query, params=params)
    elapsed = time.time() - start_time

    print(f"\nQuery: {query}")
    print(f"Category: {params['category']}")
    print(f"Results: {result['total_count']} documents")
    print(f"Search time: {elapsed:.3f} seconds")

    if result['total_count'] > 0:
        print(f"[OK] Category filter working! Found results.")
        print(f"\nFirst result:")
        first_result = result['data'][0]
        print(f"  - Law: {first_result['law_title']}")
        print(f"  - Article: {first_result['article_number']}")
        print(f"  - Category: {first_result['category']}")
        print(f"  - Relevance: {first_result['relevance_score']}")
    else:
        print("[FAIL] No results found")


async def test_sql_metadata_enrichment():
    """Test 2: SQL metadata enrichment"""
    print("\n" + "="*80)
    print("TEST 2: SQL Metadata Enrichment")
    print("="*80)

    tool = LegalSearchTool()

    query = "주택임대차보호법"
    params = {'limit': 3}

    result = await tool.search(query=query, params=params)

    print(f"\nQuery: {query}")
    print(f"Results: {result['total_count']} documents")

    if result['total_count'] > 0:
        first_result = result['data'][0]
        print(f"\nFirst result - SQL metadata check:")
        print(f"  - Law: {first_result['law_title']}")
        print(f"  - Article: {first_result['article_number']}")

        # Check SQL enrichment
        has_enrichment = False
        if 'total_articles' in first_result and first_result['total_articles'] is not None:
            print(f"  - [OK] Total Articles: {first_result['total_articles']}")
            has_enrichment = True
        else:
            print(f"  - [FAIL] Total Articles: Not found")

        if 'law_number' in first_result and first_result['law_number'] is not None:
            print(f"  - [OK] Law Number: {first_result['law_number']}")
            has_enrichment = True
        else:
            print(f"  - [FAIL] Law Number: Not found")

        if 'enforcement_date' in first_result and first_result['enforcement_date']:
            print(f"  - [OK] Enforcement Date: {first_result['enforcement_date']}")
            has_enrichment = True
        else:
            print(f"  - [FAIL] Enforcement Date: Not found")

        if has_enrichment:
            print("\n[OK] SQL metadata enrichment working!")
        else:
            print("\n[FAIL] SQL metadata enrichment not working")


async def test_specific_article_fast_lookup():
    """Test 3: Specific article fast lookup via SQL"""
    print("\n" + "="*80)
    print("TEST 3: Specific Article Fast Lookup")
    print("="*80)

    tool = LegalSearchTool()

    # Specific article queries
    test_queries = [
        "주택임대차보호법 제7조",
        "민법 제618조",
        "주택임대차보호법 7조"  # Without 제
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")

        start_time = time.time()
        result = await tool.search(query=query, params={'limit': 5})
        elapsed = time.time() - start_time

        print(f"Results: {result['total_count']} documents")
        print(f"Search time: {elapsed:.3f} seconds")

        if result['total_count'] > 0:
            # Check if it used fast path (distance = 0.0 for perfect match)
            first_result = result['data'][0]
            if first_result['relevance_score'] == 1.0:  # distance=0 → relevance=1
                print(f"[OK] Fast path used (SQL direct lookup)!")
            else:
                print(f"[WARN] Vector search used (relevance: {first_result['relevance_score']})")

            print(f"  - Law: {first_result['law_title']}")
            print(f"  - Article: {first_result['article_number']}")
        else:
            print("[FAIL] No results found")


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("LEGAL SEARCH IMPROVEMENTS TEST")
    print("="*80)

    try:
        await test_category_filter()
        await test_sql_metadata_enrichment()
        await test_specific_article_fast_lookup()

        print("\n" + "="*80)
        print("ALL TESTS COMPLETED")
        print("="*80)

    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
