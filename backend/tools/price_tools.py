"""
Price Search Tools
시세 검색 에이전트가 사용하는 도구들
"""

from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
import random
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@tool
def search_real_estate_price(
    location: str,
    property_type: str = "아파트",
    transaction_type: str = "매매",
    area_range: Optional[tuple] = None
) -> Dict[str, Any]:
    """
    부동산 실거래가 검색
    
    Args:
        location: 지역명 (예: "강남구")
        property_type: 부동산 타입 (아파트, 빌라, 오피스텔)
        transaction_type: 거래 타입 (매매, 전세, 월세)
        area_range: 면적 범위 (최소, 최대) 평 단위
    
    Returns:
        검색된 매물 정보
    """
    logger.info(f"Searching prices for {location} {property_type} ({transaction_type})")
    
    # 실제로는 외부 API 호출 (국토교통부, 네이버 부동산 등)
    # 여기서는 더미 데이터 생성
    
    results = []
    num_results = random.randint(3, 7)
    
    for i in range(num_results):
        if transaction_type == "매매":
            price = random.randint(5, 30) * 100000000  # 5억 ~ 30억
            price_str = f"{price // 100000000}억 {(price % 100000000) // 10000000}천만원" if price % 100000000 else f"{price // 100000000}억"
        elif transaction_type == "전세":
            price = random.randint(3, 15) * 100000000  # 3억 ~ 15억
            price_str = f"{price // 100000000}억 {(price % 100000000) // 10000000}천만원" if price % 100000000 else f"{price // 100000000}억"
        else:  # 월세
            deposit = random.randint(5000, 30000) * 10000  # 5천 ~ 3억
            monthly = random.randint(50, 200) * 10000  # 50만 ~ 200만
            price_str = f"보증금 {deposit // 10000}만원 / 월세 {monthly // 10000}만원"
        
        area = random.randint(20, 50) if not area_range else random.randint(area_range[0], area_range[1])
        
        results.append({
            "id": f"PROP_{i+1:03d}",
            "name": f"{location} {property_type} {i+1}",
            "address": f"{location} XX동 XX-XX",
            "property_type": property_type,
            "transaction_type": transaction_type,
            "price": price_str,
            "area_sqm": area * 3.3,  # 평을 ㎡로 변환
            "area_pyeong": area,
            "floor": f"{random.randint(1, 20)}층",
            "year_built": 2024 - random.randint(0, 20),
            "date": (datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d")
        })
    
    return {
        "status": "success",
        "location": location,
        "total_results": len(results),
        "results": results,
        "search_params": {
            "property_type": property_type,
            "transaction_type": transaction_type,
            "area_range": area_range
        }
    }


@tool
def analyze_price_trend(
    location: str,
    property_type: str = "아파트",
    period_months: int = 12
) -> Dict[str, Any]:
    """
    가격 동향 분석
    
    Args:
        location: 지역명
        property_type: 부동산 타입
        period_months: 분석 기간 (개월)
    
    Returns:
        가격 동향 분석 결과
    """
    logger.info(f"Analyzing price trend for {location} {property_type} over {period_months} months")
    
    # 더미 트렌드 데이터 생성
    trend_data = []
    current_date = datetime.now()
    base_price = random.randint(5, 15) * 100000000  # 5억 ~ 15억
    
    for i in range(period_months):
        date = current_date - timedelta(days=30 * i)
        # 랜덤 변동 (-5% ~ +5%)
        variation = random.uniform(0.95, 1.05)
        price = int(base_price * variation * (1 + i * 0.01))  # 시간에 따른 상승 트렌드
        
        trend_data.append({
            "date": date.strftime("%Y-%m"),
            "avg_price": price,
            "transaction_count": random.randint(10, 50)
        })
    
    trend_data.reverse()  # 오래된 날짜부터 정렬
    
    # 트렌드 계산
    price_change = trend_data[-1]["avg_price"] - trend_data[0]["avg_price"]
    price_change_percent = (price_change / trend_data[0]["avg_price"]) * 100
    
    return {
        "status": "success",
        "location": location,
        "property_type": property_type,
        "period_months": period_months,
        "trend_summary": {
            "direction": "상승" if price_change > 0 else "하락",
            "change_amount": abs(price_change),
            "change_percent": abs(price_change_percent),
            "current_avg_price": trend_data[-1]["avg_price"],
            "previous_avg_price": trend_data[0]["avg_price"]
        },
        "monthly_data": trend_data,
        "analysis": f"{location} {property_type} 시세는 최근 {period_months}개월간 {abs(price_change_percent):.1f}% {'상승' if price_change > 0 else '하락'}했습니다."
    }


@tool
def compare_prices(
    locations: List[str],
    property_type: str = "아파트",
    transaction_type: str = "매매"
) -> Dict[str, Any]:
    """
    지역별 가격 비교
    
    Args:
        locations: 비교할 지역 목록
        property_type: 부동산 타입
        transaction_type: 거래 타입
    
    Returns:
        지역별 가격 비교 결과
    """
    logger.info(f"Comparing prices for {locations}")
    
    comparison_data = []
    
    for location in locations:
        # 각 지역별 평균 가격 생성
        avg_price = random.randint(4, 20) * 100000000
        avg_price_per_pyeong = avg_price // 30  # 30평 기준
        
        comparison_data.append({
            "location": location,
            "avg_price": avg_price,
            "avg_price_per_pyeong": avg_price_per_pyeong,
            "min_price": int(avg_price * 0.7),
            "max_price": int(avg_price * 1.3),
            "transaction_count": random.randint(20, 100),
            "market_activity": random.choice(["활발", "보통", "한산"])
        })
    
    # 가장 비싼/저렴한 지역 찾기
    sorted_by_price = sorted(comparison_data, key=lambda x: x["avg_price"])
    
    return {
        "status": "success",
        "property_type": property_type,
        "transaction_type": transaction_type,
        "comparison_data": comparison_data,
        "summary": {
            "most_expensive": sorted_by_price[-1]["location"],
            "most_affordable": sorted_by_price[0]["location"],
            "price_gap": sorted_by_price[-1]["avg_price"] - sorted_by_price[0]["avg_price"],
            "recommendation": f"{sorted_by_price[0]['location']}이(가) 가장 저렴하며, "
                            f"{sorted_by_price[-1]['location']}이(가) 가장 비쌉니다."
        }
    }


@tool
def calculate_price_per_area(
    total_price: int,
    area_pyeong: float = None,
    area_sqm: float = None
) -> Dict[str, Any]:
    """
    평당/㎡당 가격 계산
    
    Args:
        total_price: 총 가격 (원)
        area_pyeong: 면적 (평)
        area_sqm: 면적 (㎡)
    
    Returns:
        평당/㎡당 가격 정보
    """
    if not area_pyeong and not area_sqm:
        return {
            "status": "error",
            "message": "면적 정보가 필요합니다 (평 또는 ㎡)"
        }
    
    # 평과 ㎡ 상호 변환
    if area_pyeong and not area_sqm:
        area_sqm = area_pyeong * 3.3
    elif area_sqm and not area_pyeong:
        area_pyeong = area_sqm / 3.3
    
    price_per_pyeong = int(total_price / area_pyeong)
    price_per_sqm = int(total_price / area_sqm)
    
    return {
        "status": "success",
        "total_price": total_price,
        "area_pyeong": round(area_pyeong, 1),
        "area_sqm": round(area_sqm, 1),
        "price_per_pyeong": price_per_pyeong,
        "price_per_sqm": price_per_sqm,
        "formatted": {
            "total": f"{total_price // 100000000}억 {(total_price % 100000000) // 10000}만원" if total_price >= 100000000 else f"{total_price // 10000}만원",
            "per_pyeong": f"{price_per_pyeong // 10000}만원/평",
            "per_sqm": f"{price_per_sqm // 10000}만원/㎡"
        }
    }


@tool
def get_market_statistics(location: str) -> Dict[str, Any]:
    """
    시장 통계 정보 조회
    
    Args:
        location: 지역명
    
    Returns:
        시장 통계 정보
    """
    logger.info(f"Getting market statistics for {location}")
    
    return {
        "status": "success",
        "location": location,
        "statistics": {
            "avg_days_on_market": random.randint(20, 60),
            "inventory_level": random.choice(["낮음", "보통", "높음"]),
            "price_negotiation_rate": f"{random.uniform(2, 8):.1f}%",
            "popular_size": f"{random.choice(['25', '30', '34', '40'])}평형",
            "demand_supply_index": random.uniform(0.8, 1.2),
            "rental_yield": f"{random.uniform(2, 4):.1f}%",
            "market_sentiment": random.choice(["매우 긍정", "긍정", "중립", "부정"])
        },
        "insights": [
            f"{location} 지역은 현재 {'매수자' if random.random() > 0.5 else '매도자'} 우위 시장입니다.",
            f"평균 거래 소요 기간은 {random.randint(20, 60)}일입니다.",
            f"최근 3개월간 거래량이 {'증가' if random.random() > 0.5 else '감소'} 추세입니다."
        ]
    }


# 도구 목록
PRICE_TOOLS = [
    search_real_estate_price,
    analyze_price_trend,
    compare_prices,
    calculate_price_per_area,
    get_market_statistics
]