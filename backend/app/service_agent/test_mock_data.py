"""
Mock Data Tool Test
"""

import asyncio
import sys
import logging
from pathlib import Path

# Logging setup
logging.basicConfig(level=logging.INFO)

backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.teams.search_team import SearchTeamSupervisor
from app.service_agent.core.context import create_default_llm_context
from app.service.core.separated_states import StateManager


async def test_market_search():
    """부동산 시세 검색 테스트"""
    print("\n" + "="*80)
    print("TEST: Real Estate Market Search")
    print("="*80)

    llm_context = create_default_llm_context()
    search_team = SearchTeamSupervisor(llm_context=llm_context)

    query = "강남구 아파트 시세 알려주세요"
    print(f"\n[Query] {query}")

    # 공유 상태 생성
    shared_state = StateManager.create_shared_state(
        query=query,
        session_id="test_market"
    )

    # 명시적으로 real_estate scope 지정
    result = await search_team.execute(shared_state, search_scope=["real_estate"])

    print(f"\n[Results]")
    print(f"  Status: {result.get('status')}")
    print(f"  Search Scope: {result.get('search_scope')}")
    print(f"  Real Estate Results: {len(result.get('real_estate_results', []))} items")

    if result.get('real_estate_results'):
        for item in result['real_estate_results'][:2]:
            print(f"\n  [Region: {item.get('region')}]")
            avg_prices = item.get('average_price', {})
            print(f"    매매: {avg_prices.get('매매', 'N/A')}")
            print(f"    전세: {avg_prices.get('전세', 'N/A')}")
            print(f"    월세: {avg_prices.get('월세', 'N/A')}")

            price_trend = item.get('price_trend', {})
            if price_trend:
                print(f"    가격 추세 (1개월): {price_trend.get('1개월', 'N/A')}")


async def test_loan_search():
    """대출 상품 검색 테스트"""
    print("\n" + "="*80)
    print("TEST: Loan Product Search")
    print("="*80)

    llm_context = create_default_llm_context()
    search_team = SearchTeamSupervisor(llm_context=llm_context)

    query = "주택담보대출 금리가 얼마인가요?"
    print(f"\n[Query] {query}")

    # 공유 상태 생성
    shared_state = StateManager.create_shared_state(
        query=query,
        session_id="test_loan"
    )

    # 명시적으로 loan scope 지정
    result = await search_team.execute(shared_state, search_scope=["loan"])

    print(f"\n[Results]")
    print(f"  Status: {result.get('status')}")
    print(f"  Search Scope: {result.get('search_scope')}")
    print(f"  Loan Results: {len(result.get('loan_results', []))} items")

    if result.get('loan_results'):
        for item in result['loan_results'][:3]:
            print(f"\n  [Bank: {item.get('bank_name', 'N/A')}]")
            print(f"    상품명: {item.get('product_name', 'N/A')}")
            interest_rate = item.get('interest_rate', {})
            print(f"    최저 금리: {interest_rate.get('최저', 'N/A')}")
            print(f"    최고 금리: {interest_rate.get('최고', 'N/A')}")
            loan_limit = item.get('loan_limit', {})
            print(f"    최대 한도: {loan_limit.get('최대한도', 'N/A')}")


async def main():
    await test_market_search()
    await test_loan_search()


if __name__ == "__main__":
    asyncio.run(main())
