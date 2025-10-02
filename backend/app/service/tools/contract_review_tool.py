"""
Contract Review Tool

계약서 및 법률 문서 검토 도구
- 위험 요소 분석
- 법적 준수사항 확인
- 개선 권고사항 제시
- RuleDB 연동 고려 (추후 구현)
"""

import os
import sys
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
import re
import logging

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from tools.base_tool import BaseTool


class ContractReviewTool(BaseTool):
    """계약서 검토 도구"""

    def __init__(self):
        super().__init__(
            name="contract_review",
            description="계약서 및 법률 문서 검토, 위험 분석, 준수사항 확인",
            use_mock_data=True  # Always use rule-based review for now
        )
        self.tool_name = "contract_review"
        self.logger = logging.getLogger(__name__)

        # 위험 레벨 정의
        self.risk_levels = {
            "low": "낮음",
            "medium": "중간",
            "high": "높음",
            "critical": "매우 높음"
        }

        # 검토 규칙 (추후 RuleDB로 대체)
        self._initialize_review_rules()

    def _initialize_review_rules(self):
        """검토 규칙 초기화 (Mock 데이터)"""
        self.review_rules = {
            "임대차계약서": {
                "required_clauses": [
                    "임대차 기간",
                    "보증금",
                    "월세",
                    "목적물의 표시",
                    "계약 해지"
                ],
                "risk_patterns": [
                    {
                        "pattern": r"특약\s*사항.*임차인.*포기",
                        "risk_level": "high",
                        "description": "임차인 권리 포기 조항 발견"
                    },
                    {
                        "pattern": r"원상\s*복구.*전액.*임차인.*부담",
                        "risk_level": "medium",
                        "description": "원상복구 비용 전액 임차인 부담"
                    },
                    {
                        "pattern": r"중도\s*해지.*불가",
                        "risk_level": "high",
                        "description": "중도 해지 불가 조항"
                    }
                ],
                "compliance_checks": {
                    "주택임대차보호법": [
                        "보증금 5% 초과 증액 금지",
                        "계약갱신요구권 보장",
                        "우선변제권 확인"
                    ]
                }
            },
            "매매계약서": {
                "required_clauses": [
                    "매매대금",
                    "계약금",
                    "잔금",
                    "소유권 이전",
                    "목적물의 표시"
                ],
                "risk_patterns": [
                    {
                        "pattern": r"하자.*면책",
                        "risk_level": "high",
                        "description": "매도인 하자 면책 조항"
                    },
                    {
                        "pattern": r"계약금.*몰수",
                        "risk_level": "medium",
                        "description": "계약금 몰수 조항"
                    }
                ],
                "compliance_checks": {
                    "부동산거래신고법": [
                        "거래신고 의무",
                        "신고기한 준수"
                    ]
                }
            }
        }

    async def search(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        계약서 검토 실행

        Args:
            query: 검토 요청 (예: "이 임대차계약서 검토해줘")
            params: {
                "document_content": "계약서 내용",
                "document_type": "임대차계약서",
                "review_focus": ["risk", "compliance", "completeness"]
            }
        """
        try:
            params = params or {}
            document_content = params.get("document_content", "")
            document_type = params.get("document_type") or self._detect_document_type(document_content)
            review_focus = params.get("review_focus", ["risk", "compliance", "completeness"])

            self.logger.info(f"Reviewing {document_type}, focus: {review_focus}")

            if not document_content:
                return self.format_results(
                    data=[{
                        "type": "error",
                        "message": "검토할 문서 내용이 없습니다"
                    }],
                    total_count=0,
                    query=query
                )

            # 문서 검토 실행
            review_results = await self._perform_review(
                document_content,
                document_type,
                review_focus
            )

            return self.format_results(
                data=[review_results],
                total_count=1,
                query=query
            )

        except Exception as e:
            self.logger.error(f"Contract review error: {e}")
            return self.format_results(
                data=[{
                    "type": "error",
                    "message": f"문서 검토 중 오류 발생: {str(e)}"
                }],
                total_count=0,
                query=query
            )

    def _detect_document_type(self, content: str) -> str:
        """문서 유형 자동 감지"""
        content_lower = content.lower()

        type_keywords = {
            "임대차계약서": ["임대차", "임대인", "임차인", "보증금", "월세"],
            "매매계약서": ["매매", "매도인", "매수인", "매매대금"],
            "전세계약서": ["전세", "전세금"],
            "근저당권설정계약서": ["근저당", "채무자", "채권자"],
            "내용증명": ["내용증명", "통지", "발신인", "수신인"]
        }

        for doc_type, keywords in type_keywords.items():
            match_count = sum(1 for keyword in keywords if keyword in content_lower)
            if match_count >= 2:  # 2개 이상 매칭시 해당 유형으로 판단
                return doc_type

        return "일반문서"

    async def _perform_review(
        self,
        content: str,
        document_type: str,
        review_focus: List[str]
    ) -> Dict[str, Any]:
        """실제 문서 검토 수행"""

        review_results = {
            "document_type": document_type,
            "review_timestamp": datetime.now().isoformat(),
            "risk_factors": [],
            "compliance_check": {},
            "completeness_check": {},
            "recommendations": [],
            "overall_risk_level": "low",
            "summary": ""
        }

        # 1. 위험 요소 분석
        if "risk" in review_focus:
            risk_factors = self._analyze_risks(content, document_type)
            review_results["risk_factors"] = risk_factors
            review_results["overall_risk_level"] = self._calculate_overall_risk(risk_factors)

        # 2. 법적 준수사항 확인
        if "compliance" in review_focus:
            compliance_check = self._check_compliance(content, document_type)
            review_results["compliance_check"] = compliance_check

        # 3. 완성도 확인
        if "completeness" in review_focus:
            completeness_check = self._check_completeness(content, document_type)
            review_results["completeness_check"] = completeness_check

        # 4. 개선 권고사항 생성
        recommendations = self._generate_recommendations(
            review_results["risk_factors"],
            review_results["compliance_check"],
            review_results["completeness_check"]
        )
        review_results["recommendations"] = recommendations

        # 5. 요약 생성
        review_results["summary"] = self._generate_summary(review_results)

        return review_results

    def _analyze_risks(self, content: str, document_type: str) -> List[Dict[str, Any]]:
        """위험 요소 분석"""
        risk_factors = []

        # 문서 유형별 규칙 가져오기
        rules = self.review_rules.get(document_type, {})
        risk_patterns = rules.get("risk_patterns", [])

        for risk_rule in risk_patterns:
            pattern = risk_rule["pattern"]
            if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                risk_factors.append({
                    "risk_level": risk_rule["risk_level"],
                    "description": risk_rule["description"],
                    "location": self._find_pattern_location(content, pattern),
                    "recommendation": f"{risk_rule['description']}에 대한 재검토 필요"
                })

        # 일반적인 위험 패턴 확인
        general_risks = [
            {
                "pattern": r"일방적.*해지",
                "risk_level": "medium",
                "description": "일방적 해지 조항"
            },
            {
                "pattern": r"손해.*배상.*면책",
                "risk_level": "high",
                "description": "손해배상 면책 조항"
            },
            {
                "pattern": r"분쟁.*시.*관할",
                "risk_level": "low",
                "description": "분쟁 관할 조항 확인 필요"
            }
        ]

        for risk_rule in general_risks:
            pattern = risk_rule["pattern"]
            if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                risk_factors.append({
                    "risk_level": risk_rule["risk_level"],
                    "description": risk_rule["description"],
                    "location": self._find_pattern_location(content, pattern),
                    "recommendation": f"{risk_rule['description']} 주의"
                })

        return risk_factors

    def _check_compliance(self, content: str, document_type: str) -> Dict[str, Any]:
        """법적 준수사항 확인"""
        compliance_results = {}

        rules = self.review_rules.get(document_type, {})
        compliance_checks = rules.get("compliance_checks", {})

        for law_name, check_items in compliance_checks.items():
            law_compliance = {
                "law": law_name,
                "checks": [],
                "compliance_rate": 0.0
            }

            for check_item in check_items:
                # 간단한 키워드 매칭 (실제로는 더 복잡한 로직 필요)
                is_compliant = self._check_compliance_item(content, check_item)
                law_compliance["checks"].append({
                    "item": check_item,
                    "compliant": is_compliant,
                    "status": "준수" if is_compliant else "확인필요"
                })

            # 준수율 계산
            compliant_count = sum(1 for check in law_compliance["checks"] if check["compliant"])
            total_count = len(law_compliance["checks"])
            if total_count > 0:
                law_compliance["compliance_rate"] = compliant_count / total_count

            compliance_results[law_name] = law_compliance

        return compliance_results

    def _check_compliance_item(self, content: str, check_item: str) -> bool:
        """개별 준수사항 확인 (Mock 구현)"""
        # 실제로는 더 복잡한 로직이 필요
        # 현재는 간단한 키워드 매칭으로 구현
        compliance_keywords = {
            "보증금 5% 초과 증액 금지": ["보증금", "증액", "5%"],
            "계약갱신요구권 보장": ["계약갱신", "갱신요구"],
            "우선변제권 확인": ["우선변제", "변제권"],
            "거래신고 의무": ["거래신고", "신고"],
            "신고기한 준수": ["신고", "기한"]
        }

        keywords = compliance_keywords.get(check_item, [check_item])
        content_lower = content.lower()

        # 모든 키워드가 포함되어 있으면 준수로 판단
        for keyword in keywords:
            if keyword.lower() not in content_lower:
                return False
        return True

    def _check_completeness(self, content: str, document_type: str) -> Dict[str, Any]:
        """문서 완성도 확인"""
        completeness_results = {
            "required_clauses": [],
            "missing_clauses": [],
            "completeness_score": 0.0
        }

        rules = self.review_rules.get(document_type, {})
        required_clauses = rules.get("required_clauses", [])

        for clause in required_clauses:
            is_present = self._check_clause_presence(content, clause)
            if is_present:
                completeness_results["required_clauses"].append(clause)
            else:
                completeness_results["missing_clauses"].append(clause)

        # 완성도 점수 계산
        total_required = len(required_clauses)
        if total_required > 0:
            completeness_results["completeness_score"] = \
                len(completeness_results["required_clauses"]) / total_required

        return completeness_results

    def _check_clause_presence(self, content: str, clause: str) -> bool:
        """조항 존재 여부 확인"""
        # 간단한 키워드 매칭
        clause_keywords = {
            "임대차 기간": ["임대차", "기간"],
            "보증금": ["보증금"],
            "월세": ["월세", "임대료"],
            "목적물의 표시": ["목적물", "표시", "소재지"],
            "계약 해지": ["해지", "해제"],
            "매매대금": ["매매대금", "매매가격"],
            "계약금": ["계약금"],
            "잔금": ["잔금"],
            "소유권 이전": ["소유권", "이전"]
        }

        keywords = clause_keywords.get(clause, [clause])
        content_lower = content.lower()

        return any(keyword.lower() in content_lower for keyword in keywords)

    def _find_pattern_location(self, content: str, pattern: str) -> str:
        """패턴 위치 찾기"""
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        if match:
            # 줄 번호 찾기
            lines = content[:match.start()].split('\n')
            line_number = len(lines)
            return f"약 {line_number}번째 줄"
        return "위치 미확인"

    def _calculate_overall_risk(self, risk_factors: List[Dict[str, Any]]) -> str:
        """전체 위험 레벨 계산"""
        if not risk_factors:
            return "low"

        risk_scores = {
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4
        }

        total_score = sum(risk_scores.get(factor["risk_level"], 0) for factor in risk_factors)
        avg_score = total_score / len(risk_factors)

        if avg_score >= 3.5:
            return "critical"
        elif avg_score >= 2.5:
            return "high"
        elif avg_score >= 1.5:
            return "medium"
        else:
            return "low"

    def _generate_recommendations(
        self,
        risk_factors: List[Dict],
        compliance_check: Dict,
        completeness_check: Dict
    ) -> List[str]:
        """개선 권고사항 생성"""
        recommendations = []

        # 위험 요소 기반 권고
        for risk in risk_factors:
            if risk["risk_level"] in ["high", "critical"]:
                recommendations.append(f"⚠️ {risk['recommendation']}")

        # 준수사항 기반 권고
        for law_name, compliance in compliance_check.items():
            non_compliant = [c for c in compliance.get("checks", []) if not c["compliant"]]
            if non_compliant:
                recommendations.append(
                    f"📋 {law_name} 관련 {len(non_compliant)}개 항목 확인 필요"
                )

        # 완성도 기반 권고
        missing = completeness_check.get("missing_clauses", [])
        if missing:
            recommendations.append(
                f"📝 누락된 필수 조항 추가 필요: {', '.join(missing)}"
            )

        # 일반 권고사항
        if not recommendations:
            recommendations.append("✅ 전반적으로 양호한 계약서입니다")

        return recommendations

    def _generate_summary(self, review_results: Dict[str, Any]) -> str:
        """검토 요약 생성"""
        risk_level = review_results.get("overall_risk_level", "low")
        risk_level_kr = self.risk_levels.get(risk_level, risk_level)
        risk_count = len(review_results.get("risk_factors", []))
        recommendation_count = len(review_results.get("recommendations", []))

        # 완성도 점수
        completeness_score = 0.0
        if review_results.get("completeness_check"):
            completeness_score = review_results["completeness_check"].get("completeness_score", 0.0)

        summary = f"""
계약서 검토 결과:
- 문서 유형: {review_results.get('document_type', 'N/A')}
- 전체 위험도: {risk_level_kr}
- 발견된 위험 요소: {risk_count}개
- 문서 완성도: {completeness_score:.0%}
- 개선 권고사항: {recommendation_count}개
"""
        return summary.strip()

    async def get_mock_data(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """BaseTool abstract method implementation - not used but required"""
        # This tool doesn't use the mock data pattern from BaseTool
        # It has its own rule-based review system
        return await self.search(query, params)

    def get_capabilities(self) -> Dict[str, Any]:
        """도구의 기능 정보 반환"""
        return {
            "tool_name": self.tool_name,
            "description": self.description,
            "supported_document_types": list(self.review_rules.keys()),
            "review_focus_areas": ["risk", "compliance", "completeness"],
            "risk_levels": list(self.risk_levels.values()),
            "parameters": {
                "document_content": "검토할 문서 내용",
                "document_type": "문서 유형 (자동 감지 가능)",
                "review_focus": "검토 중점 영역 리스트"
            },
            "uses_ruledb": False,  # 추후 True로 변경
            "version": "1.0.0"
        }


# 테스트 코드
if __name__ == "__main__":
    import asyncio

    async def test():
        tool = ContractReviewTool()

        # 테스트 1: 임대차계약서 검토
        print("\n=== Test 1: 임대차계약서 검토 ===")
        sample_contract = """
부동산 임대차 계약서

임대인 김철수(이하 "갑")과 임차인 이영희(이하 "을")는 다음과 같이 계약한다.

제1조 (목적물의 표시)
소재지: 서울시 강남구 테헤란로 123
면적: 85㎡

제2조 (임대차 기간)
임대차 기간은 2024년 1월 1일부터 2025년 12월 31일까지로 한다.

제3조 (보증금과 월세)
1. 보증금: 금 50,000,000원
2. 월세: 금 1,000,000원

제4조 (특약사항)
- 중도 해지 불가
- 원상복구 비용은 전액 임차인이 부담한다
"""
        result = await tool.search(
            "이 임대차계약서 검토해줘",
            {
                "document_content": sample_contract,
                "review_focus": ["risk", "compliance", "completeness"]
            }
        )
        print(f"Status: {result['status']}")
        if result['data']:
            review = result['data'][0]
            print(f"Summary: {review.get('summary')}")
            print(f"Risk Factors: {len(review.get('risk_factors', []))}개")
            print(f"Recommendations: {review.get('recommendations')}")

        # 테스트 2: 빈 문서
        print("\n=== Test 2: 빈 문서 ===")
        result = await tool.search("계약서 검토", {"document_content": ""})
        print(f"Status: {result['status']}")
        if result['data']:
            print(f"Error: {result['data'][0].get('message')}")

    asyncio.run(test())