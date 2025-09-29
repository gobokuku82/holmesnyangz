"""
Loan Search Tool
Searches for loan products and financial information
"""

from typing import Dict, Any, List
from .base_tool import BaseTool
import random


class LoanSearchTool(BaseTool):
    """
    Tool for searching loan information
    - Mortgage products
    - Interest rates
    - Loan conditions
    - Financial institutions
    """

    def __init__(self, use_mock_data: bool = True):
        super().__init__(
            name="loan_search",
            description="대출 정보 검색 - 주택담보대출, 금리, 대출 조건, 금융기관 정보",
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

    async def get_mock_data(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Mock search returning sample loan data

        Args:
            query: Search query
            params: Additional parameters including loan_amount, property_price, etc.

        Returns:
            Mock loan search results
        """
        query_lower = query.lower() if query else ""

        # Extract parameters
        loan_amount = params.get("loan_amount", 300000000) if params else 300000000  # 3억원 default
        property_price = params.get("property_price", 500000000) if params else 500000000  # 5억원 default
        loan_type = params.get("loan_type", "주택담보대출") if params else "주택담보대출"

        mock_data = []

        # Mortgage loan products
        if "주택" in query_lower or "mortgage" in query_lower or loan_type == "주택담보대출":
            mock_data.extend([
                {
                    "type": "loan_product",
                    "bank": "KB국민은행",
                    "product_name": "KB주택담보대출",
                    "category": "주택담보대출",
                    "interest_rate": {
                        "min": 3.85,
                        "max": 4.95,
                        "base_rate": "변동금리",
                        "spread": "+1.2%p"
                    },
                    "loan_limit": {
                        "ltv": "70%",
                        "max_amount": property_price * 0.7,
                        "actual_limit": min(loan_amount, property_price * 0.7)
                    },
                    "conditions": {
                        "income_requirement": "연소득 3천만원 이상",
                        "credit_score": "NICE 600점 이상",
                        "employment": "재직 6개월 이상"
                    },
                    "fees": {
                        "origination_fee": "대출금액의 0.1%",
                        "early_repayment_fee": "잔액의 1.2% (3년 이내)"
                    },
                    "special_offers": [
                        "온라인 신청 시 0.2%p 우대",
                        "급여이체 고객 0.1%p 추가 우대"
                    ]
                },
                {
                    "type": "loan_product",
                    "bank": "신한은행",
                    "product_name": "신한 주택담보대출",
                    "category": "주택담보대출",
                    "interest_rate": {
                        "min": 3.92,
                        "max": 5.02,
                        "base_rate": "고정금리(3년)",
                        "spread": "+1.3%p"
                    },
                    "loan_limit": {
                        "ltv": "70%",
                        "max_amount": property_price * 0.7,
                        "actual_limit": min(loan_amount, property_price * 0.7)
                    },
                    "conditions": {
                        "income_requirement": "연소득 2천5백만원 이상",
                        "credit_score": "KCB 630점 이상",
                        "employment": "재직 3개월 이상"
                    },
                    "repayment_options": [
                        "원리금균등상환",
                        "원금균등상환",
                        "만기일시상환 (1년 이내)"
                    ]
                }
            ])

        # Jeonse loan products
        if "전세" in query_lower or "jeonse" in query_lower:
            mock_data.extend([
                {
                    "type": "loan_product",
                    "bank": "우리은행",
                    "product_name": "우리전세론",
                    "category": "전세자금대출",
                    "interest_rate": {
                        "min": 3.2,
                        "max": 4.5,
                        "base_rate": "변동금리"
                    },
                    "loan_limit": {
                        "max_percentage": "80%",
                        "max_amount": 400000000,  # 4억원
                        "region_limit": {
                            "서울": 500000000,
                            "경기": 400000000,
                            "기타": 300000000
                        }
                    },
                    "conditions": {
                        "income_requirement": "연소득 2천만원 이상",
                        "property_requirement": "전용면적 85㎡ 이하",
                        "tenant_requirement": "세대주"
                    },
                    "special_conditions": [
                        "주택도시보증공사 보증서 필요",
                        "임차보증금 5% 이상 자기자금"
                    ]
                }
            ])

        # Credit loan products
        if "신용" in query_lower or "credit" in query_lower:
            mock_data.extend([
                {
                    "type": "loan_product",
                    "bank": "카카오뱅크",
                    "product_name": "카카오뱅크 신용대출",
                    "category": "신용대출",
                    "interest_rate": {
                        "min": 4.5,
                        "max": 12.0,
                        "determination": "신용등급별 차등"
                    },
                    "loan_limit": {
                        "max_amount": 100000000,  # 1억원
                        "income_multiple": 1.5,
                        "actual_limit": "연소득의 150% 이내"
                    },
                    "conditions": {
                        "income_requirement": "연소득 2천만원 이상",
                        "credit_score": "KCB 520점 이상",
                        "employment": "재직 3개월 이상"
                    },
                    "features": [
                        "비대면 신청 가능",
                        "당일 입금",
                        "중도상환수수료 없음"
                    ]
                }
            ])

        # Interest rate comparison
        if "금리" in query_lower or "비교" in query_lower:
            mock_data.append({
                "type": "rate_comparison",
                "title": "주요 은행 주택담보대출 금리 비교",
                "category": "금리비교",
                "comparison_date": "2024-01-20",
                "banks": [
                    {"name": "KB국민은행", "rate": "3.85~4.95%", "type": "변동금리"},
                    {"name": "신한은행", "rate": "3.92~5.02%", "type": "고정금리(3년)"},
                    {"name": "하나은행", "rate": "3.88~4.98%", "type": "혼합형"},
                    {"name": "우리은행", "rate": "3.90~5.00%", "type": "변동금리"},
                    {"name": "NH농협", "rate": "3.83~4.93%", "type": "변동금리"}
                ],
                "market_trend": "기준금리 동결로 당분간 현 수준 유지 전망",
                "tips": [
                    "은행별 우대조건 확인 필수",
                    "고정금리 vs 변동금리 신중히 선택",
                    "총 대출비용(금리+수수료) 비교"
                ]
            })

        # Government-backed loans
        if "정부" in query_lower or "서민" in query_lower or "정책" in query_lower:
            mock_data.extend([
                {
                    "type": "government_loan",
                    "program": "디딤돌대출",
                    "category": "정부지원대출",
                    "provider": "주택도시기금",
                    "interest_rate": {
                        "income_below_20m": "2.15%",
                        "income_below_40m": "2.40%",
                        "income_below_60m": "2.65%",
                        "income_above_60m": "2.90%"
                    },
                    "loan_limit": {
                        "max_amount": 250000000,  # 2.5억원
                        "ltv": "70%",
                        "additional_for_newlyweds": 30000000  # 신혼부부 추가 3천만원
                    },
                    "eligibility": [
                        "부부합산 연소득 6천만원 이하",
                        "순자산 4.58억원 이하",
                        "무주택세대주"
                    ],
                    "special_benefits": [
                        "신혼부부 금리 우대",
                        "다자녀가구 추가 대출한도",
                        "청약저축 가입자 우대"
                    ]
                }
            ])

        # Default mock data if no specific match
        if not mock_data:
            mock_data = [
                {
                    "type": "general_loan_info",
                    "title": "대출 상품 일반 정보",
                    "category": "일반",
                    "content": f"'{query}'에 대한 대출 정보입니다.",
                    "general_tips": [
                        "여러 금융기관 비교 필수",
                        "총 대출비용 계산",
                        "상환능력 고려한 대출규모 결정"
                    ],
                    "consultation": "정확한 대출 조건은 금융기관 상담 필요"
                }
            ]

        # Add calculation results if loan amount and property price are provided
        if loan_amount and property_price:
            ltv_ratio = (loan_amount / property_price) * 100
            mock_data.insert(0, {
                "type": "loan_calculation",
                "title": "대출 가능성 분석",
                "requested_amount": loan_amount,
                "property_value": property_price,
                "ltv_ratio": f"{ltv_ratio:.1f}%",
                "feasibility": "가능" if ltv_ratio <= 70 else "LTV 초과로 조정 필요",
                "max_loanable": property_price * 0.7,
                "recommendation": f"최대 대출 가능액: {property_price * 0.7:,.0f}원"
            })

        # Add metadata
        for item in mock_data:
            item["relevance_score"] = random.uniform(0.7, 1.0)

        # Sort by relevance
        mock_data.sort(key=lambda x: x["relevance_score"], reverse=True)

        return self.format_results(
            data=mock_data[:5],  # Return top 5 results
            total_count=len(mock_data),
            query=query
        )