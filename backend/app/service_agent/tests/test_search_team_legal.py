"""
SearchTeam 법률 검색 통합 테스트
기존 LegalSearchTool을 활용한 법률 검색 기능 검증
"""

import asyncio
import sys
import logging
from pathlib import Path

# Path setup
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from app.service_agent.teams.search_team import SearchTeamSupervisor
from app.service.core.separated_states import StateManager


def print_section(title: str):
    """섹션 구분선 출력"""
    print(f"\n{'='*80}")
    print(f"{title:^80}")
    print('='*80)


async def test_legal_search_only():
    """법률 검색 단독 테스트"""
    print_section("법률 검색 단독 테스트")

    search_team = SearchTeamSupervisor()

    test_queries = [
        "전세금 5% 인상 제한",
        "계약 갱신 요구권",
        "주택임대차보호법 제7조",
        "중개수수료 상한"
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"쿼리: {query}")
        print('-'*60)

        # 공유 상태 생성
        shared_state = StateManager.create_shared_state(
            query=query,
            session_id="test_legal_search"
        )

        # SearchTeam 실행 (법률 검색만)
        result = await search_team.execute(
            shared_state,
            search_scope=["legal"]
        )

        print(f"\n[Results]")
        print(f"  Status: {result['status']}")
        print(f"  Total: {result.get('total_results', 0)}")
        print(f"  Time: {result.get('search_time', 0):.2f}s")
        print(f"  Sources: {result.get('sources_used', [])}")

        if result.get("legal_results"):
            print(f"\n[Legal Results] ({len(result['legal_results'])})")
            for i, legal in enumerate(result['legal_results'][:5], 1):
                print(f"\n  [{i}] {legal['law_title']} {legal['article_number']}")
                print(f"      제목: {legal.get('article_title', 'N/A')}")
                print(f"      관련도: {legal.get('relevance_score', 0):.3f}")
                print(f"      장: {legal.get('chapter', 'N/A')}")
                print(f"      절: {legal.get('section', 'N/A')}")
                print(f"      내용: {legal['content'][:150]}...")
        else:
            print("\n  [X] No results")

        if result.get("error"):
            print(f"\n  [!] Error: {result['error']}")


async def test_multi_scope_search():
    """다중 범위 검색 테스트 (법률 + 부동산 + 대출)"""
    print_section("다중 범위 검색 테스트")

    search_team = SearchTeamSupervisor()

    test_query = "강남 아파트 전세 계약 관련 법률과 시세"

    print(f"\n쿼리: {test_query}")
    print('-'*60)

    # 공유 상태 생성
    shared_state = StateManager.create_shared_state(
        query=test_query,
        session_id="test_multi_search"
    )

    # SearchTeam 실행 (모든 범위)
    result = await search_team.execute(shared_state)

    print(f"\n[Results]")
    print(f"  Status: {result['status']}")
    print(f"  Total: {result.get('total_results', 0)}")
    print(f"  Time: {result.get('search_time', 0):.2f}s")
    print(f"  Sources: {result.get('sources_used', [])}")
    print(f"  Scope: {result.get('search_scope', [])}")

    # 법률 검색 결과
    if result.get("legal_results"):
        print(f"\n[Legal Results] ({len(result['legal_results'])})")
        for i, legal in enumerate(result['legal_results'][:3], 1):
            print(f"  [{i}] {legal['law_title']} {legal['article_number']}: {legal.get('article_title', 'N/A')}")

    # 부동산 검색 결과
    if result.get("real_estate_results"):
        print(f"\n[Real Estate Results] ({len(result['real_estate_results'])})")
        for i, estate in enumerate(result['real_estate_results'][:3], 1):
            print(f"  [{i}] {estate}")

    # 대출 검색 결과
    if result.get("loan_results"):
        print(f"\n[Loan Results] ({len(result['loan_results'])})")
        for i, loan in enumerate(result['loan_results'][:3], 1):
            print(f"  [{i}] {loan}")


async def test_tenant_protection_filter():
    """임차인 보호 조항 필터 테스트"""
    print_section("임차인 보호 조항 필터 테스트")

    search_team = SearchTeamSupervisor()

    test_queries = [
        "전세 보증금 반환",
        "임차인 권리",
        "임대차 계약 갱신"
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"쿼리: {query}")
        print('-'*60)

        shared_state = StateManager.create_shared_state(
            query=query,
            session_id="test_tenant_protection"
        )

        result = await search_team.execute(
            shared_state,
            search_scope=["legal"]
        )

        if result.get("legal_results"):
            print(f"\n[Legal Results] ({len(result['legal_results'])})")
            for i, legal in enumerate(result['legal_results'][:3], 1):
                print(f"\n  [{i}] {legal['law_title']} {legal['article_number']}")
                print(f"      Title: {legal.get('article_title', 'N/A')}")
                print(f"      Content: {legal['content'][:100]}...")


async def test_specific_article():
    """특정 조항 검색 테스트"""
    print_section("특정 조항 검색 테스트")

    search_team = SearchTeamSupervisor()

    test_cases = [
        "주택임대차보호법 제7조",
        "민법 제618조",
        "공인중개사법 제10조"
    ]

    for query in test_cases:
        print(f"\n{'='*60}")
        print(f"쿼리: {query}")
        print('-'*60)

        shared_state = StateManager.create_shared_state(
            query=query,
            session_id="test_specific_article"
        )

        result = await search_team.execute(
            shared_state,
            search_scope=["legal"]
        )

        if result.get("legal_results"):
            print(f"\n[Legal Result]")
            legal = result['legal_results'][0]
            print(f"  Law: {legal['law_title']}")
            print(f"  Article: {legal['article_number']}")
            print(f"  Title: {legal.get('article_title', 'N/A')}")
            print(f"  Chapter: {legal.get('chapter', 'N/A')}")
            print(f"  Section: {legal.get('section', 'N/A')}")
            print(f"  Content:\n{legal['content'][:300]}...")
        else:
            print("\n  [X] No results")


async def main():
    """전체 테스트 실행"""
    print("\n" + "="*80)
    print("SearchTeam Legal Search Integration Test Suite")
    print("="*80)

    try:
        # 1. 법률 검색 단독 테스트
        await test_legal_search_only()

        # 2. 다중 범위 검색 테스트
        await test_multi_scope_search()

        # 3. 임차인 보호 조항 필터 테스트
        await test_tenant_protection_filter()

        # 4. 특정 조항 검색 테스트
        await test_specific_article()

        print_section("[OK] All Tests Completed")

    except Exception as e:
        print(f"\n\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
