"""
Hybrid Legal Search 테스트
SQLite + ChromaDB 하이브리드 검색 시스템 검증
"""

import asyncio
import sys
from pathlib import Path

# Path setup
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.tools import create_hybrid_legal_search


def print_section(title: str):
    """섹션 구분선 출력"""
    print(f"\n{'='*80}")
    print(f"{title:^80}")
    print('='*80)


def test_database_statistics():
    """DB 통계 조회 테스트"""
    print_section("데이터베이스 통계")

    legal_search = create_hybrid_legal_search()

    stats = legal_search.get_law_statistics()

    print(f"\n📊 법률 DB 통계:")
    print(f"  - 총 법령 수: {stats['total_laws']}")
    print(f"  - 총 조항 수: {stats['total_articles']}")
    print(f"  - ChromaDB 문서 수: {stats['chromadb_documents']}")

    print(f"\n📁 문서 타입 분포:")
    for doc_type, count in stats['doc_type_distribution'].items():
        print(f"  - {doc_type}: {count}")

    print(f"\n📂 카테고리 분포:")
    for category, count in stats['category_distribution'].items():
        print(f"  - {category}: {count}")

    print(f"\n⭐ 특수 조항:")
    for name, count in stats['special_articles'].items():
        print(f"  - {name}: {count}")

    legal_search.close()


def test_specific_article_search():
    """특정 조항 검색 테스트"""
    print_section("특정 조항 검색")

    legal_search = create_hybrid_legal_search()

    test_cases = [
        ("주택임대차보호법", "제7조"),
        ("민법", "제618조"),
        ("공인중개사법", "제10조")
    ]

    for law_title, article_number in test_cases:
        print(f"\n🔍 검색: {law_title} {article_number}")

        result = legal_search.search_specific_article(law_title, article_number)

        if result:
            print(f"  ✅ 조항 발견:")
            print(f"     제목: {result['article_title']}")
            print(f"     장: {result.get('chapter', 'N/A')}")
            print(f"     절: {result.get('section', 'N/A')}")
            print(f"     청크 수: {result['chunk_count']}")
            print(f"     임차인 보호: {'예' if result['is_tenant_protection'] else '아니오'}")
            print(f"     내용 (앞 200자): {result['content'][:200]}...")
        else:
            print(f"  ❌ 조항을 찾을 수 없습니다.")

    legal_search.close()


def test_hybrid_search():
    """하이브리드 검색 테스트"""
    print_section("하이브리드 검색 (SQLite + ChromaDB)")

    legal_search = create_hybrid_legal_search()

    test_queries = [
        ("전세금 인상 제한", {"is_tenant_protection": True}),
        ("계약 갱신 요구", {"is_tenant_protection": True}),
        ("보증금 반환", None),
        ("중개수수료", None)
    ]

    for query, filters in test_queries:
        print(f"\n🔍 검색어: '{query}'")
        if filters:
            print(f"   필터: {filters}")

        kwargs = {"query": query, "limit": 5}
        if filters:
            kwargs.update(filters)

        results = legal_search.hybrid_search(**kwargs)

        print(f"\n   📄 검색 결과: {len(results)}건")

        for i, result in enumerate(results[:3], 1):
            print(f"\n   [{i}] {result['law_title']} {result['article_number']}")
            print(f"       제목: {result.get('article_title', 'N/A')}")
            print(f"       관련도: {result['relevance_score']:.3f}")
            print(f"       임차인 보호: {'✓' if result['is_tenant_protection'] else '✗'}")
            print(f"       내용: {result['content'][:150]}...")

    legal_search.close()


def test_metadata_queries():
    """메타데이터 쿼리 테스트"""
    print_section("SQLite 메타데이터 쿼리")

    legal_search = create_hybrid_legal_search()

    # 1. 카테고리별 법령 조회
    print("\n📂 카테고리: 2_임대차_전세_월세")
    laws = legal_search.search_laws_by_category("2_임대차_전세_월세")
    for law in laws[:5]:
        print(f"  - {law['title']} ({law['doc_type']})")

    # 2. 문서 타입별 법령 조회
    print("\n📁 문서 타입: 법률")
    laws = legal_search.search_laws_by_doc_type("법률")
    for law in laws[:5]:
        print(f"  - {law['title']}")

    # 3. 임차인 보호 조항 조회
    print("\n⭐ 임차인 보호 조항")
    articles = legal_search.get_tenant_protection_articles()
    for article in articles[:5]:
        print(f"  - {article['law_title']} {article['article_number']}: {article.get('article_title', 'N/A')}")

    legal_search.close()


def test_vector_search():
    """벡터 검색 테스트"""
    print_section("ChromaDB 벡터 검색")

    legal_search = create_hybrid_legal_search()

    queries = [
        "전세금 5% 인상",
        "계약서 작성 의무",
        "중개보수 상한"
    ]

    for query in queries:
        print(f"\n🔍 쿼리: '{query}'")

        results = legal_search.vector_search(query, n_results=5)

        print(f"   📄 검색 결과: {len(results['ids'])}건")

        for i in range(min(3, len(results['ids']))):
            metadata = results['metadatas'][i]
            content = results['documents'][i]
            distance = results['distances'][i]

            print(f"\n   [{i+1}] {metadata.get('law_title', 'N/A')} {metadata.get('article_number', 'N/A')}")
            print(f"       거리: {distance:.3f}")
            print(f"       내용: {content[:150]}...")

    legal_search.close()


async def test_search_team_integration():
    """SearchTeam 통합 테스트"""
    print_section("SearchTeam 통합 테스트")

    from app.service_agent.teams.search_team import SearchTeamSupervisor
    from app.service.core.separated_states import StateManager

    # SearchTeam 초기화
    search_team = SearchTeamSupervisor()

    test_queries = [
        "전세금 5% 인상 가능한가요?",
        "강남 아파트 시세",
        "계약 갱신 요구권"
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"쿼리: {query}")
        print('-'*60)

        # 공유 상태 생성
        shared_state = StateManager.create_shared_state(
            query=query,
            session_id="test_hybrid_search"
        )

        # SearchTeam 실행
        result = await search_team.execute(shared_state)

        print(f"\n상태: {result['status']}")
        print(f"총 결과 수: {result.get('total_results', 0)}")
        print(f"사용된 소스: {result.get('sources_used', [])}")
        print(f"검색 시간: {result.get('search_time', 0):.2f}초")

        if result.get("legal_results"):
            print(f"\n법률 검색 결과 ({len(result['legal_results'])}건):")
            for i, legal in enumerate(result['legal_results'][:3], 1):
                print(f"  [{i}] {legal['law_title']} {legal['article_number']}")
                print(f"      {legal.get('article_title', 'N/A')}")
                print(f"      관련도: {legal.get('relevance_score', 0):.3f}")
                print(f"      내용: {legal['content'][:100]}...")


def main():
    """전체 테스트 실행"""
    print("\n" + "🔥"*40)
    print("Hybrid Legal Search System Test Suite")
    print("🔥"*40)

    try:
        # 1. DB 통계
        test_database_statistics()

        # 2. 특정 조항 검색
        test_specific_article_search()

        # 3. 하이브리드 검색
        test_hybrid_search()

        # 4. 메타데이터 쿼리
        test_metadata_queries()

        # 5. 벡터 검색
        test_vector_search()

        # 6. SearchTeam 통합
        print("\n\nSearchTeam 통합 테스트 실행 중...")
        asyncio.run(test_search_team_integration())

        print_section("✅ 전체 테스트 완료")

    except Exception as e:
        print(f"\n\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
