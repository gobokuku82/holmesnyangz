"""
LoanDataTool MongoDB 연동 테스트 스크립트

사용법:
    python scripts/test_loan_tool.py
"""

import sys
from pathlib import Path
import asyncio

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.service_agent.tools.loan_data_tool import LoanDataTool
import json


async def test_loan_tool():
    """LoanDataTool 테스트"""
    print("=" * 80)
    print("LoanDataTool MongoDB 연동 테스트")
    print("=" * 80)

    # LoanDataTool 초기화
    loan_tool = LoanDataTool()
    print(f"\n✅ LoanDataTool 초기화 완료")
    print(f"   연결된 은행: {', '.join(loan_tool.bank_collections)}")

    # 테스트 케이스들
    test_cases = [
        {
            "name": "전세자금대출 검색",
            "query": "전세자금대출",
            "params": {}
        },
        {
            "name": "주택담보대출 검색",
            "query": "주택담보대출",
            "params": {}
        },
        {
            "name": "KB국민은행 대출 검색",
            "query": "KB국민은행 전세대출",
            "params": {}
        },
        {
            "name": "카카오뱅크 대출 검색",
            "query": "카카오뱅크 대출",
            "params": {"bank": "카카오"}
        },
        {
            "name": "보금자리론 검색",
            "query": "보금자리론",
            "params": {}
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"테스트 케이스 {i}: {test_case['name']}")
        print(f"{'=' * 80}")
        print(f"쿼리: {test_case['query']}")
        print(f"파라미터: {test_case['params']}")

        # 검색 실행
        result = await loan_tool.search(
            query=test_case['query'],
            params=test_case['params']
        )

        # 결과 출력
        print(f"\n상태: {result['status']}")
        print(f"결과 수: {result.get('result_count', 0)}")

        if result['status'] == 'success' and result.get('data'):
            print(f"\n상위 3개 결과:")
            for idx, product in enumerate(result['data'][:3], 1):
                print(f"\n  [{idx}] {product['bank_name']} - {product['product_name']}")
                print(f"      분류: {product.get('product_category', 'N/A')}")
                print(f"      요약: {product.get('summary', 'N/A')[:100]}...")

                # 상세 정보
                if product.get('interest_rates'):
                    print(f"      금리: {product['interest_rates'][:100]}...")
                if product.get('loan_limits'):
                    print(f"      한도: {product['loan_limits'][:100]}...")
        else:
            print(f"⚠️ 검색 결과 없음 또는 에러")
            if 'error' in result:
                print(f"   에러: {result['error']}")

    # 통계 정보 출력
    print(f"\n{'=' * 80}")
    print("MongoDB 대출 상품 통계")
    print(f"{'=' * 80}")

    stats = loan_tool.get_statistics()
    if 'error' not in stats:
        print(f"\n총 은행 수: {stats['total_banks']}")
        print(f"총 상품 수: {stats['total_products']}")
        print(f"\n은행별 상품 수:")
        for collection_name, bank_info in stats['banks'].items():
            print(f"  - {bank_info['name']}: {bank_info['product_count']}개")
    else:
        print(f"⚠️ 통계 조회 실패: {stats['error']}")

    print(f"\n{'=' * 80}")
    print("✅ 모든 테스트 완료")
    print(f"{'=' * 80}")


if __name__ == '__main__':
    asyncio.run(test_loan_tool())
