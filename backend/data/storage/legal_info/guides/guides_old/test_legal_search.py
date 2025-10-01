"""
Test script for Legal Search functionality
"""

import asyncio
import json
from app.service.legal_search_service import LegalSearchService


async def test_legal_search():
    """Test various search scenarios"""

    print("=" * 80)
    print("법률 검색 시스템 테스트")
    print("=" * 80)

    # Initialize service
    service = LegalSearchService()
    print("\n1. 서비스 초기화 중...")
    await service.initialize()
    print("✅ 서비스 초기화 완료")

    # Test cases
    test_cases = [
        {
            "name": "임차인 보호 조항 검색",
            "query": "임차인 보호 보증금 권리",
            "filters": {
                "is_tenant_protection": True,
                "category": "rental_lease"
            }
        },
        {
            "name": "세금 관련 조항 검색",
            "query": "취득세 양도소득세 재산세",
            "filters": {
                "is_tax_related": True
            }
        },
        {
            "name": "최근 시행 법률 검색",
            "query": "법률 시행 개정",
            "filters": {
                "date_from": "2024-01-01",
                "doc_type": ["법률", "시행령"]
            }
        },
        {
            "name": "공인중개사 관련 검색",
            "query": "공인중개사 자격 시험",
            "filters": {
                "category": "common_transaction"
            }
        },
        {
            "name": "용어 정의 검색",
            "query": "부동산 매매 임대차",
            "filters": {
                "doc_type": ["용어집"]
            }
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'-' * 60}")
        print(f"테스트 {i}: {test_case['name']}")
        print(f"쿼리: {test_case['query']}")
        print(f"필터: {test_case['filters']}")
        print(f"{'-' * 60}")

        # Execute search
        results = await service.search(
            query=test_case['query'],
            **test_case['filters'],
            limit=5
        )

        print(f"검색 결과: {results['total_results']}개")

        # Display top 3 results
        for j, result in enumerate(results['results'][:3], 1):
            print(f"\n  [{j}] {result['title']}")
            print(f"      유사도: {result['relevance_score']:.3f}")
            print(f"      문서유형: {result['metadata'].get('doc_type', 'N/A')}")
            print(f"      카테고리: {result['metadata'].get('category', 'N/A')}")
            print(f"      조항: {result['metadata'].get('article_number', 'N/A')}")

            # Show snippet of text
            text = result['text'][:150] + "..." if len(result['text']) > 150 else result['text']
            print(f"      내용: {text}")

    print("\n" + "=" * 80)
    print("테스트 완료!")
    print("=" * 80)


async def test_special_searches():
    """Test special search endpoints"""

    print("\n" + "=" * 80)
    print("특수 검색 기능 테스트")
    print("=" * 80)

    service = LegalSearchService()
    await service.initialize()

    # Test category search
    print("\n1. 카테고리별 검색: 임대차·전세·월세")
    results = await service.search_by_category("rental_lease", limit=5)
    print(f"   결과: {results['total_results']}개 문서")

    # Test recent laws
    print("\n2. 최근 법률 검색 (365일)")
    results = await service.search_recent_laws(days=365, limit=5)
    print(f"   결과: {results['total_results']}개 문서")

    # Test tenant protection
    print("\n3. 임차인 보호 관련 조항")
    results = await service.search_tenant_protection(limit=5)
    print(f"   결과: {results['total_results']}개 문서")

    # Test tax provisions
    print("\n4. 세금 관련 조항")
    results = await service.search_tax_provisions(limit=5)
    print(f"   결과: {results['total_results']}개 문서")

    # Test glossary
    print("\n5. 용어집 검색: '보증금'")
    results = await service.get_glossary("보증금")
    print(f"   결과: {results['total_terms']}개 용어")
    for term in results['entries'][:3]:
        print(f"   - {term['term']}: {term['definition'][:100]}...")

    # Get statistics
    print("\n6. 데이터베이스 통계")
    stats = service.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")


async def main():
    """Main test function"""
    print("\n어떤 테스트를 실행하시겠습니까?")
    print("1. 기본 검색 테스트")
    print("2. 특수 검색 테스트")
    print("3. 모든 테스트")

    choice = input("\n선택 (1-3): ").strip()

    if choice == "1":
        await test_legal_search()
    elif choice == "2":
        await test_special_searches()
    elif choice == "3":
        await test_legal_search()
        await test_special_searches()
    else:
        print("잘못된 선택입니다.")


if __name__ == "__main__":
    asyncio.run(main())