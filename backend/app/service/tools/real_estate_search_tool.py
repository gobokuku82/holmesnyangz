"""
Real Estate Search Tool
Searches for real estate properties, prices, and market information
"""

from typing import Dict, Any, List, Tuple, Optional
from .base_tool import BaseTool
import random
import re
from datetime import datetime, timedelta


class RealEstateSearchTool(BaseTool):
    """
    Tool for searching real estate information
    - Property listings
    - Market prices
    - Transaction history
    - Regional statistics
    """

    def __init__(self, use_mock_data: bool = True):
        super().__init__(
            name="real_estate_search",
            description="부동산 정보 검색 - 매물, 시세, 거래 내역, 지역 통계",
            use_mock_data=use_mock_data
        )

    async def search(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Real search implementation (to be implemented with actual data source)

        Args:
            query: Search query
            params: Additional parameters

        Returns:
            Search results
        """
        # TODO: Implement real search when data source is available
        self.logger.warning("Real search not implemented, falling back to mock")
        return await self.get_mock_data(query, params)

    def _parse_query_constraints(self, query: str) -> Dict[str, Any]:
        """
        Parse constraints from the query string

        Args:
            query: Query string

        Returns:
            Parsed constraints
        """
        constraints = {}
        query_lower = query.lower() if query else ""

        # Parse price constraints (e.g., "30억미만", "10억이상", "5-10억")
        price_patterns = [
            (r'(\d+)억\s*미만', lambda m: {'price_max': int(m.group(1)) * 100000000}),
            (r'(\d+)억\s*이하', lambda m: {'price_max': int(m.group(1)) * 100000000}),
            (r'(\d+)억\s*이상', lambda m: {'price_min': int(m.group(1)) * 100000000}),
            (r'(\d+)억\s*초과', lambda m: {'price_min': int(m.group(1)) * 100000000}),
            (r'(\d+)\s*-\s*(\d+)억', lambda m: {
                'price_min': int(m.group(1)) * 100000000,
                'price_max': int(m.group(2)) * 100000000
            })
        ]

        for pattern, extractor in price_patterns:
            match = re.search(pattern, query)
            if match:
                constraints.update(extractor(match))
                break

        # Parse size constraints (e.g., "50평이상", "30평대", "30-40평")
        size_patterns = [
            (r'(\d+)평\s*이상', lambda m: {'size_min': int(m.group(1))}),
            (r'(\d+)평\s*초과', lambda m: {'size_min': int(m.group(1)) + 1}),
            (r'(\d+)평\s*이하', lambda m: {'size_max': int(m.group(1))}),
            (r'(\d+)평\s*미만', lambda m: {'size_max': int(m.group(1)) - 1}),
            (r'(\d+)평대', lambda m: {
                'size_min': int(m.group(1)),
                'size_max': int(m.group(1)) + 9
            }),
            (r'(\d+)\s*-\s*(\d+)평', lambda m: {
                'size_min': int(m.group(1)),
                'size_max': int(m.group(2))
            })
        ]

        for pattern, extractor in size_patterns:
            match = re.search(pattern, query)
            if match:
                constraints.update(extractor(match))
                break

        # Parse region
        regions = ['강남구', '서초구', '송파구', '용산구', '마포구', '성동구']
        for region in regions:
            if region in query:
                constraints['region'] = region
                break

        # Parse property type
        if '아파트' in query:
            constraints['property_type'] = '아파트'
        elif '빌라' in query or '연립' in query:
            constraints['property_type'] = '빌라'
        elif '오피스텔' in query:
            constraints['property_type'] = '오피스텔'

        # Parse transaction type
        if '매매' in query or '매물' in query:
            constraints['transaction_type'] = '매매'
        elif '전세' in query:
            constraints['transaction_type'] = '전세'
        elif '월세' in query:
            constraints['transaction_type'] = '월세'

        return constraints

    async def get_mock_data(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Mock search returning sample real estate data

        Args:
            query: Search query
            params: Additional parameters including region, price_range, size, etc.

        Returns:
            Mock real estate search results
        """
        query_lower = query.lower() if query else ""

        # Parse constraints from query
        parsed_constraints = self._parse_query_constraints(query)

        # Merge with params if provided
        if params:
            parsed_constraints.update(params)

        # Extract parameters with defaults
        region = parsed_constraints.get("region", "강남구")
        property_type = parsed_constraints.get("property_type", "아파트")
        transaction_type = parsed_constraints.get("transaction_type", "매매")
        price_min = parsed_constraints.get("price_min", 500000000)
        price_max = parsed_constraints.get("price_max", 5000000000)  # Default 50억
        size_min = parsed_constraints.get("size_min", 20)
        size_max = parsed_constraints.get("size_max", 100)

        mock_data = []

        # Property listings
        if "매물" in query_lower or "listing" in query_lower or transaction_type:
            # Generate sample listings
            complexes = [
                {"name": "래미안대치팰리스", "built_year": 2018, "total_units": 523},
                {"name": "아크로리버파크", "built_year": 2016, "total_units": 814},
                {"name": "반포자이", "built_year": 2008, "total_units": 2444},
                {"name": "래미안블레스티지", "built_year": 2019, "total_units": 449},
                {"name": "헬리오시티", "built_year": 2018, "total_units": 9510},
                {"name": "타워팰리스", "built_year": 2002, "total_units": 2310},
                {"name": "갤러리아포레", "built_year": 2020, "total_units": 408}
            ]

            # Generate varied properties - some matching criteria, some not
            for i, complex_info in enumerate(complexes):
                # Generate varied sizes - ensure some match the criteria
                if i < 3 and size_min > 40:  # If looking for large properties
                    property_size = random.randint(max(size_min, 50), min(size_max, 80))
                else:
                    property_size = random.randint(25, 65)  # General range

                # Generate price based on size and constraints
                price_per_pyeong = random.randint(25000000, 45000000)
                base_price = property_size * price_per_pyeong

                # Skip if doesn't match basic criteria
                if base_price > price_max or base_price < price_min:
                    if i < 2:  # Force first 2 to match criteria
                        base_price = random.randint(price_min, min(price_max, price_min * 2))
                        property_size = base_price // price_per_pyeong
                    elif random.random() > 0.3:  # 30% chance to include anyway
                        continue

                if property_size < size_min or property_size > size_max:
                    if i < 2:  # Force first 2 to match criteria
                        property_size = random.randint(size_min, size_max)
                        base_price = property_size * price_per_pyeong
                    elif random.random() > 0.3:  # 30% chance to include anyway
                        continue

                listing = {
                    "type": "property_listing",
                    "listing_id": f"2024-{region}-{i+1:04d}",
                    "complex_name": complex_info["name"],
                    "address": f"{region} {complex_info['name']}",
                    "property_type": property_type,
                    "transaction_type": transaction_type,
                    "size": {
                        "pyeong": property_size,
                        "sqm": property_size * 3.3
                    },
                    "floor": f"{random.randint(5, 20)}층/{random.randint(25, 35)}층",
                    "direction": random.choice(["남향", "남동향", "동향", "서향"]),
                    "price": {
                        "amount": base_price,
                        "per_pyeong": price_per_pyeong,
                        "negotiable": random.choice([True, False])
                    },
                    "built_year": complex_info["built_year"],
                    "move_in_date": random.choice(["즉시입주", "협의가능", "2024-03-01"]),
                    "features": random.sample([
                        "역세권", "학군우수", "한강조망", "신축급",
                        "풀옵션", "주차2대", "관리우수", "조용한환경"
                    ], 3),
                    "contact": {
                        "agency": f"{region} 공인중개사",
                        "phone": f"02-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
                    },
                    "listing_date": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
                    "matches_criteria": (
                        base_price >= price_min and base_price <= price_max and
                        property_size >= size_min and property_size <= size_max
                    )
                }

                mock_data.append(listing)

        # Market price information
        if "시세" in query_lower or "price" in query_lower:
            # Calculate average based on query constraints
            avg_price = (price_min + price_max) // 2 if price_max < 5000000000 else 850000000
            avg_size = (size_min + size_max) // 2 if size_max < 100 else 35

            mock_data.append({
                "type": "market_price",
                "region": region,
                "property_type": property_type,
                "reference_date": datetime.now().strftime("%Y-%m-%d"),
                "size_range": f"{size_min}-{size_max}평" if size_max < 100 else "전체",
                "price_statistics": {
                    "average_price": {
                        "total": avg_price,
                        "per_pyeong": avg_price // avg_size,
                        "mom_change": "+1.2%",  # Month-over-month
                        "yoy_change": "+5.3%"   # Year-over-year
                    },
                    "price_range": {
                        "min": 650000000,
                        "max": 1200000000,
                        "median": 820000000
                    },
                    "transaction_volume": {
                        "this_month": 156,
                        "last_month": 142,
                        "change": "+9.9%"
                    }
                },
                "popular_complexes": [
                    {"name": "래미안대치팰리스", "avg_price": 950000000, "transactions": 12},
                    {"name": "아크로리버파크", "avg_price": 1100000000, "transactions": 8},
                    {"name": "반포자이", "avg_price": 1500000000, "transactions": 15}
                ],
                "market_trend": "상승세",
                "analysis": "재건축 기대감과 교통 개선으로 꾸준한 상승세 유지"
            })

        # Transaction history
        if "거래" in query_lower or "transaction" in query_lower:
            recent_transactions = []
            for i in range(5):
                days_ago = random.randint(1, 60)
                transaction = {
                    "date": (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d"),
                    "complex": random.choice(["래미안대치팰리스", "아크로리버파크", "반포자이"]),
                    "size": size + random.randint(-5, 5),
                    "floor": f"{random.randint(5, 20)}층",
                    "price": random.randint(price_min, price_max),
                    "transaction_type": transaction_type,
                    "price_change": f"{random.choice(['+', '-'])}{random.uniform(1, 5):.1f}%"
                }
                recent_transactions.append(transaction)

            mock_data.append({
                "type": "transaction_history",
                "region": region,
                "period": "최근 2개월",
                "total_transactions": 234,
                "recent_transactions": sorted(recent_transactions, key=lambda x: x["date"], reverse=True),
                "statistics": {
                    "average_price": 880000000,
                    "highest_price": 1350000000,
                    "lowest_price": 620000000,
                    "most_traded_size": "30-35평",
                    "most_active_complex": "래미안대치팰리스"
                }
            })

        # Regional statistics
        if "통계" in query_lower or "지역" in query_lower or "statistics" in query_lower:
            mock_data.append({
                "type": "regional_statistics",
                "region": region,
                "data_date": datetime.now().strftime("%Y-%m"),
                "demographics": {
                    "population": 542000,
                    "households": 215000,
                    "population_density": "16,500/km²"
                },
                "housing_statistics": {
                    "total_units": 180000,
                    "apartment_ratio": "68%",
                    "average_age": "15년",
                    "homeownership_rate": "42%"
                },
                "infrastructure": {
                    "subway_stations": 12,
                    "schools": {"elementary": 25, "middle": 15, "high": 12},
                    "hospitals": 8,
                    "parks": 15
                },
                "development_projects": [
                    {
                        "name": "GTX-A 개통",
                        "completion": "2024년 하반기",
                        "impact": "접근성 대폭 개선 예상"
                    },
                    {
                        "name": "재건축 단지",
                        "count": 5,
                        "status": "추진중"
                    }
                ],
                "investment_rating": "A",
                "key_factors": [
                    "우수한 교육 인프라",
                    "교통 접근성 개선",
                    "재건축 호재"
                ]
            })

        # Comparison data
        if "비교" in query_lower or "compare" in query_lower:
            mock_data.append({
                "type": "comparison",
                "title": f"{region} 주요 단지 비교",
                "comparison_items": [
                    {
                        "complex": "래미안대치팰리스",
                        "avg_price": 950000000,
                        "price_per_pyeong": 31000000,
                        "built_year": 2018,
                        "pros": ["신축", "역세권", "학군"],
                        "cons": ["높은 가격", "주차난"]
                    },
                    {
                        "complex": "아크로리버파크",
                        "avg_price": 1100000000,
                        "price_per_pyeong": 35000000,
                        "built_year": 2016,
                        "pros": ["한강조망", "대단지", "편의시설"],
                        "cons": ["관리비 높음", "교통 혼잡"]
                    },
                    {
                        "complex": "반포자이",
                        "avg_price": 1500000000,
                        "price_per_pyeong": 45000000,
                        "built_year": 2008,
                        "pros": ["프리미엄 단지", "넓은 평형", "조경"],
                        "cons": ["매우 높은 가격", "구축"]
                    }
                ],
                "recommendation": "예산과 선호도에 따라 선택, 장기 투자 관점에서는 모두 우수"
            })

        # Investment analysis
        if "투자" in query_lower or "investment" in query_lower:
            mock_data.append({
                "type": "investment_analysis",
                "region": region,
                "analysis_date": datetime.now().strftime("%Y-%m-%d"),
                "investment_score": 8.5,
                "factors": {
                    "price_growth_potential": "높음",
                    "rental_yield": "2.8-3.2%",
                    "liquidity": "매우 좋음",
                    "development_potential": "재건축/재개발 다수"
                },
                "risks": [
                    "정부 규제 강화 가능성",
                    "금리 인상 리스크",
                    "공급 과잉 우려"
                ],
                "opportunities": [
                    "GTX 개통 호재",
                    "재건축 진행",
                    "인구 유입 지속"
                ],
                "recommendation": "중장기 투자 적합, 단기 차익 실현은 제한적"
            })

        # Default mock data if no specific match
        if not mock_data:
            mock_data = [
                {
                    "type": "general_info",
                    "title": "부동산 정보",
                    "region": region,
                    "content": f"'{query}'에 대한 {region} 부동산 정보입니다.",
                    "summary": {
                        "market_status": "안정세",
                        "average_price": "8-10억원대",
                        "recommendation": "실거주 목적 적합"
                    }
                }
            ]

        # Add metadata and calculate relevance
        for item in mock_data:
            # Higher score for items matching criteria
            base_score = random.uniform(0.5, 0.8)
            if item.get("type") == "property_listing":
                if item.get("matches_criteria"):
                    base_score = random.uniform(0.85, 1.0)
            item["relevance_score"] = base_score
            item["data_source"] = "Real Estate Database (Mock)"

        # Sort by relevance (matching criteria first)
        mock_data.sort(key=lambda x: (x.get("matches_criteria", False), x["relevance_score"]), reverse=True)

        return self.format_results(
            data=mock_data[:5],  # Return top 5 results
            total_count=len(mock_data),
            query=query
        )