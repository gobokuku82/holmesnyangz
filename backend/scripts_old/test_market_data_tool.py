"""
MarketDataTool 테스트 스크립트
PostgreSQL 연동 확인
"""

import sys
import asyncio
from pathlib import Path

# backend 디렉토리를 Python path에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


async def test_market_data_tool():
    """MarketDataTool 테스트"""
    from app.service_agent.tools.market_data_tool import MarketDataTool

    print("\n" + "=" * 60)
    print("    MarketDataTool PostgreSQL 연동 테스트")
    print("=" * 60)

    try:
        # Tool 초기화
        tool = MarketDataTool()
        print("✅ MarketDataTool 초기화 성공")

        # 테스트 케이스 1: 특정 지역 검색
        print("\n" + "-" * 60)
        print("테스트 1: 강남구 아파트 시세")
        print("-" * 60)

        result1 = await tool.search("강남구 아파트 시세", {"property_type": "apartment"})

        print(f"Status: {result1['status']}")
        print(f"Result Count: {result1['result_count']}")

        if result1['status'] == 'success' and result1['data']:
            for i, item in enumerate(result1['data'][:3], 1):
                print(f"\n{i}. {item['region']} - {item['property_type']}")
                sale_price = f"{item['avg_sale_price']:,}만원" if item['avg_sale_price'] else "데이터 없음"
                deposit = f"{item['avg_deposit']:,}만원" if item['avg_deposit'] else "데이터 없음"
                print(f"   평균 매매가: {sale_price}")
                print(f"   평균 보증금: {deposit}")
                print(f"   거래 건수: {item['transaction_count']}건")

        # 테스트 케이스 2: 전체 지역 검색
        print("\n" + "-" * 60)
        print("테스트 2: 전체 지역 빌라 시세 (상위 5개)")
        print("-" * 60)

        result2 = await tool.search("빌라 시세", {"property_type": "villa"})

        print(f"Status: {result2['status']}")
        print(f"Total Result Count: {result2['result_count']}")

        if result2['status'] == 'success' and result2['data']:
            for i, item in enumerate(result2['data'][:5], 1):
                print(f"{i}. {item['region']} - {item['transaction_count']}건")

        # 테스트 케이스 3: 송파구 검색
        print("\n" + "-" * 60)
        print("테스트 3: 송파구 오피스텔 시세")
        print("-" * 60)

        result3 = await tool.search("송파구 오피스텔", {"property_type": "officetel"})

        print(f"Status: {result3['status']}")
        print(f"Result Count: {result3['result_count']}")

        if result3['status'] == 'success' and result3['data']:
            for i, item in enumerate(result3['data'][:3], 1):
                print(f"\n{i}. {item['region']}")
                sale_price = f"{item['avg_sale_price']:,}만원" if item['avg_sale_price'] else "데이터 없음"
                print(f"   평균 매매가: {sale_price}")
                print(f"   거래 건수: {item['transaction_count']}건")

        # 테스트 케이스 4: 파라미터 없이 쿼리만
        print("\n" + "-" * 60)
        print("테스트 4: 쿼리만으로 지역 추출 (강남구 시세)")
        print("-" * 60)

        result4 = await tool.search("강남구 시세 알려줘", {})

        print(f"Status: {result4['status']}")
        print(f"Result Count: {result4['result_count']}")
        print(f"Extracted Region: {result4['metadata'].get('region')}")

        if result4['status'] == 'success' and result4['data']:
            print(f"\n총 {len(result4['data'])}개 매물 타입 발견:")
            for item in result4['data'][:5]:
                print(f"  - {item['property_type']}: {item['transaction_count']}건")

        print("\n" + "=" * 60)
        print("✅ 모든 테스트 완료!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_market_data_tool())
