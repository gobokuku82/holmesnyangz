"""
Loan Data Tool - 대출 상품 정보 제공
Mock 데이터 기반
"""

import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path


logger = logging.getLogger(__name__)


class LoanDataTool:
    """대출 상품 데이터 Tool"""

    def __init__(self):
        self.mock_data = self._load_mock_data()

    def _load_mock_data(self) -> Dict:
        """Load mock loan data"""
        try:
            backend_dir = Path(__file__).parent.parent.parent.parent
            data_path = backend_dir / "data" / "storage" / "loan" / "mock_loan_products.json"

            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            logger.info(f"Loan data loaded: {len(data.get('loan_types', {}))} loan types")
            return data

        except Exception as e:
            logger.error(f"Failed to load mock data: {e}")
            return {"loan_types": {}, "regulations": {}}

    async def search(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Search loan products"""
        params = params or {}

        loan_type = params.get('loan_type') or self._extract_loan_type(query)

        logger.info(f"Loan search - type: {loan_type}, query: {query[:50]}")

        loan_types_data = self.mock_data.get('loan_types', {})
        results = []

        if loan_type and loan_type in loan_types_data:
            loan_data = loan_types_data[loan_type]

            # Format bank data
            if 'banks' in loan_data:
                for bank_info in loan_data['banks'][:5]:
                    results.append({
                        "loan_type": loan_type,
                        "description": loan_data.get('description', ''),
                        **bank_info
                    })
        else:
            # 타입이 없거나 잘못된 경우 - 모든 대출 상품 반환
            logger.warning(f"Loan type not found or not specified, returning all types")
            for type_name, loan_data in loan_types_data.items():
                if 'banks' in loan_data:
                    for bank_info in loan_data['banks'][:2]:  # 각 타입별 2개씩
                        results.append({
                            "loan_type": type_name,
                            "description": loan_data.get('description', ''),
                            **bank_info
                        })
                if len(results) >= 5:
                    break

        return {
            "status": "success",
            "data": results,
            "regulations": self.mock_data.get('regulations', {}),
            "interest_rate_trend": self.mock_data.get('interest_rate_trend', {}),
            "loan_tips": self.mock_data.get('loan_tips', []),
            "result_count": len(results)
        }

    def _extract_loan_type(self, query: str) -> Optional[str]:
        """Extract loan type from query"""
        if "주택담보" in query or "담보대출" in query:
            return "주택담보대출"
        elif "전세" in query:
            return "전세자금대출"
        elif "신용" in query:
            return "신용대출"
        return None
