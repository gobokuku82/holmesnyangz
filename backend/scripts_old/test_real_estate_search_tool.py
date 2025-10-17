"""
RealEstateSearchTool 테스트 스크립트
PostgreSQL 연동 확인
"""

import sys
import asyncio
from pathlib import Path

# backend 디렉토리를 Python path에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


async def test_real_estate_search_tool():
    """RealEstateSearchTool 테스트"""
    from app.service_agent.tools.real_estate_search_tool import RealEstateSearchTool

    print("\n" + "=" * 80)
    print("    RealEstateSearchTool PostgreSQL 연동 테스트")
    print("=" * 80)

    try:
        # Tool 초기화
        tool = RealEstateSearchTool()
        print("✅ RealEstateSearchTool 초기화 성공")

        # 테스트 케이스 1: 기본 검색 (강남구 아파트)
        print("\n" + "-" * 80)
        print("테스트 1: 강남구 아파트 검색")
        print("-" * 80)

        result1 = await tool.search(
            "강남구 아파트",
            {"property_type": "apartment", "limit": 3}
        )

        print(f"Status: {result1['status']}")
        print(f"Result Count: {result1['result_count']}")

        if result1['status'] == 'success' and result1['data']:
            for i, item in enumerate(result1['data'], 1):
                print(f"\n{i}. {item['name']} ({item['property_type']})")
                print(f"   지역: {item['region']}")
                print(f"   주소: {item['address']}")
                print(f"   세대수: {item['total_households']}세대")
                print(f"   면적: {item['min_exclusive_area']}~{item['max_exclusive_area']}㎡")
                print(f"   준공일: {item['completion_date']}")

                # 최근 거래 내역
                if 'recent_transactions' in item and item['recent_transactions']:
                    print(f"   최근 거래:")
                    for t in item['recent_transactions'][:2]:
                        t_type = t.get('transaction_type', '알 수 없음')
                        t_date = t.get('transaction_date', '알 수 없음')
                        print(f"     - {t_type} ({t_date})")

                        if 'sale_price_range' in t:
                            price_range = t['sale_price_range']
                            print(f"       매매가: {price_range['min']:,}~{price_range['max']:,}{price_range['unit']}")

                        if 'deposit_range' in t:
                            deposit_range = t['deposit_range']
                            print(f"       보증금: {deposit_range['min']:,}~{deposit_range['max']:,}{deposit_range['unit']}")

        # 테스트 케이스 2: 가격 범위 필터링
        print("\n" + "-" * 80)
        print("테스트 2: 송파구 오피스텔 (5억 이하)")
        print("-" * 80)

        result2 = await tool.search(
            "송파구 오피스텔",
            {
                "property_type": "officetel",
                "max_price": 50000,  # 5억 (만원 단위)
                "limit": 3
            }
        )

        print(f"Status: {result2['status']}")
        print(f"Result Count: {result2['result_count']}")

        if result2['status'] == 'success' and result2['data']:
            for i, item in enumerate(result2['data'], 1):
                print(f"\n{i}. {item['name']}")
                print(f"   지역: {item['region']}")
                print(f"   면적: {item['min_exclusive_area']}~{item['max_exclusive_area']}㎡")

                if 'recent_transactions' in item and item['recent_transactions']:
                    t = item['recent_transactions'][0]
                    if 'sale_price_range' in t:
                        price_range = t['sale_price_range']
                        print(f"   최근 매매가: {price_range['min']:,}~{price_range['max']:,}{price_range['unit']}")

        # 테스트 케이스 3: 면적 범위 필터링
        print("\n" + "-" * 80)
        print("테스트 3: 강남구 아파트 (80~120㎡)")
        print("-" * 80)

        result3 = await tool.search(
            "강남구 아파트",
            {
                "property_type": "apartment",
                "min_area": 80.0,
                "max_area": 120.0,
                "limit": 3
            }
        )

        print(f"Status: {result3['status']}")
        print(f"Result Count: {result3['result_count']}")

        if result3['status'] == 'success' and result3['data']:
            for i, item in enumerate(result3['data'], 1):
                print(f"\n{i}. {item['name']}")
                print(f"   면적: {item['min_exclusive_area']}~{item['max_exclusive_area']}㎡")
                print(f"   세대수: {item['total_households']}세대")

        # 테스트 케이스 4: 주변 시설 정보 포함
        print("\n" + "-" * 80)
        print("테스트 4: 강남구 아파트 (주변 시설 정보 포함)")
        print("-" * 80)

        result4 = await tool.search(
            "강남구 아파트",
            {
                "property_type": "apartment",
                "limit": 2,
                "include_nearby": True
            }
        )

        print(f"Status: {result4['status']}")
        print(f"Result Count: {result4['result_count']}")

        if result4['status'] == 'success' and result4['data']:
            for i, item in enumerate(result4['data'], 1):
                print(f"\n{i}. {item['name']}")
                print(f"   지역: {item['region']}")

                if 'nearby_facilities' in item:
                    facilities = item['nearby_facilities']

                    if facilities.get('subway'):
                        subway = facilities['subway']
                        print(f"   지하철: {subway.get('line', '')} {subway.get('station', '')} "
                              f"(도보 {subway.get('walking_time', '?')}분)")

                    schools = facilities.get('schools', {})
                    if schools.get('elementary'):
                        print(f"   초등학교: {', '.join(schools['elementary'][:2])}")

        # 테스트 케이스 5: 페이지네이션
        print("\n" + "-" * 80)
        print("테스트 5: 빌라 검색 (페이지네이션)")
        print("-" * 80)

        # 첫 페이지
        result5_page1 = await tool.search(
            "빌라",
            {"property_type": "villa", "limit": 3, "offset": 0}
        )

        # 두 번째 페이지
        result5_page2 = await tool.search(
            "빌라",
            {"property_type": "villa", "limit": 3, "offset": 3}
        )

        print(f"첫 페이지: {result5_page1['result_count']}개")
        if result5_page1['data']:
            for item in result5_page1['data']:
                print(f"  - {item['name']} ({item['region']})")

        print(f"\n두 번째 페이지: {result5_page2['result_count']}개")
        if result5_page2['data']:
            for item in result5_page2['data']:
                print(f"  - {item['name']} ({item['region']})")

        print("\n" + "=" * 80)
        print("✅ 모든 테스트 완료!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_real_estate_search_tool())
