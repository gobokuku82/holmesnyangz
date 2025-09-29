"""
Regulation Search Tool
Searches for real estate regulations and policies
"""

from typing import Dict, Any, List
from .base_tool import BaseTool
import random


class RegulationSearchTool(BaseTool):
    """
    Tool for searching regulations and policies
    - Government regulations
    - Regional policies
    - Building codes
    - Development restrictions
    """

    def __init__(self, use_mock_data: bool = True):
        super().__init__(
            name="regulation_search",
            description="규정 및 정책 검색 - 정부 규제, 지역 정책, 건축 규정 등",
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
        Mock search returning sample regulation data

        Args:
            query: Search query
            params: Additional parameters

        Returns:
            Mock regulation search results
        """
        query_lower = query.lower() if query else ""
        region = params.get("region", "서울") if params else "서울"

        mock_data = []

        # LTV/DTI regulations
        if "ltv" in query_lower or "dti" in query_lower or "대출" in query_lower:
            mock_data.extend([
                {
                    "type": "financial_regulation",
                    "title": "주택담보대출 규제 (LTV/DTI/DSR)",
                    "category": "금융규제",
                    "effective_date": "2024-01-01",
                    "details": {
                        "LTV": {
                            "투기과열지구": "40%",
                            "조정대상지역": "60%",
                            "기타지역": "70%"
                        },
                        "DTI": {
                            "투기과열지구": "40%",
                            "조정대상지역": "50%",
                            "기타지역": "60%"
                        },
                        "DSR": {
                            "전지역": "40% (개인별 산정)"
                        }
                    },
                    "exceptions": [
                        "생애최초 주택구매자 우대",
                        "서민·실수요자 요건 충족 시 완화"
                    ],
                    "source": "금융위원회"
                }
            ])

        # Regional regulations
        if "지역" in query_lower or "규제" in query_lower or region:
            mock_data.extend([
                {
                    "type": "regional_regulation",
                    "title": f"{region} 부동산 규제 현황",
                    "category": "지역규제",
                    "designation": "투기과열지구" if region in ["서울", "강남"] else "조정대상지역",
                    "regulations": [
                        "전매제한: 소유권 이전등기 후 2년",
                        "재건축 초과이익 환수",
                        "분양권 전매 제한",
                        "1주택자 양도세 비과세 요건 강화"
                    ],
                    "last_updated": "2023-12-01"
                },
                {
                    "type": "development_restriction",
                    "title": f"{region} 개발제한구역 현황",
                    "category": "개발규제",
                    "restricted_areas": [
                        "그린벨트 지정 구역",
                        "군사시설 보호구역",
                        "문화재 보호구역"
                    ],
                    "development_possibilities": [
                        "소규모 주택 건설 일부 허용",
                        "공공임대주택 건설 가능 구역"
                    ]
                }
            ])

        # Building codes
        if "건축" in query_lower or "용적률" in query_lower or "건폐율" in query_lower:
            mock_data.extend([
                {
                    "type": "building_code",
                    "title": "주거지역 건축 규제",
                    "category": "건축규정",
                    "zoning_types": {
                        "제1종전용주거지역": {
                            "건폐율": "50%",
                            "용적률": "100%",
                            "높이제한": "2층 이하"
                        },
                        "제2종전용주거지역": {
                            "건폐율": "50%",
                            "용적률": "150%",
                            "높이제한": "4층 이하"
                        },
                        "제1종일반주거지역": {
                            "건폐율": "60%",
                            "용적률": "200%",
                            "높이제한": "4층 이하"
                        },
                        "제2종일반주거지역": {
                            "건폐율": "60%",
                            "용적률": "250%",
                            "높이제한": "7층 이하"
                        },
                        "제3종일반주거지역": {
                            "건폐율": "50%",
                            "용적률": "300%",
                            "높이제한": "제한 없음"
                        }
                    },
                    "additional_restrictions": [
                        "일조권 사선 제한",
                        "인접대지 경계선으로부터 이격거리"
                    ]
                }
            ])

        # Transaction regulations
        if "거래" in query_lower or "신고" in query_lower:
            mock_data.extend([
                {
                    "type": "transaction_regulation",
                    "title": "부동산 거래신고 의무",
                    "category": "거래규제",
                    "requirements": [
                        "계약 체결일로부터 30일 이내 신고",
                        "거래가격 등 거래내역 신고",
                        "자금조달계획서 제출 (일정금액 이상)"
                    ],
                    "penalties": {
                        "미신고": "500만원 이하 과태료",
                        "거짓신고": "3천만원 이하 과태료"
                    },
                    "thresholds": {
                        "자금조달계획서": "투기과열지구 3억원, 조정대상지역 6억원, 기타 9억원"
                    }
                }
            ])

        # Tax regulations
        if "세금" in query_lower or "세제" in query_lower:
            mock_data.extend([
                {
                    "type": "tax_regulation",
                    "title": "종합부동산세 과세 기준",
                    "category": "세제규정",
                    "tax_base": {
                        "주택": "공시가격 합계 6억원 초과",
                        "토지": "공시가격 합계 5억원 초과"
                    },
                    "tax_rates": {
                        "1주택자": "0.5% ~ 2.7%",
                        "2주택자": "0.6% ~ 3.0%",
                        "3주택자_이상": "1.2% ~ 6.0%"
                    },
                    "deductions": [
                        "1주택자 11억원 공제",
                        "고령자·장기보유 공제"
                    ]
                }
            ])

        # Default mock data if no specific match
        if not mock_data:
            mock_data = [
                {
                    "type": "general_regulation",
                    "title": "부동산 관련 일반 규정",
                    "category": "일반",
                    "content": f"'{query}'에 대한 규정 정보입니다.",
                    "summary": "부동산 거래 및 개발 관련 일반적인 규정사항",
                    "key_points": [
                        "거래 전 규제지역 확인 필수",
                        "건축 규정 사전 검토",
                        "세제 변경사항 주의"
                    ]
                }
            ]

        # Add metadata to each result
        for item in mock_data:
            item["relevance_score"] = random.uniform(0.7, 1.0)
            item["region"] = region
            item["search_query"] = query

        # Sort by relevance
        mock_data.sort(key=lambda x: x["relevance_score"], reverse=True)

        return self.format_results(
            data=mock_data[:5],  # Return top 5 results
            total_count=len(mock_data),
            query=query
        )