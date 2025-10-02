"""
Test script for new Document and Review agents
"""

import os
import sys
import asyncio
from datetime import datetime

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from agents.document_agent import DocumentAgent
from agents.review_agent import ReviewAgent


async def test_document_agent():
    """Test Document Generation Agent"""
    print("\n" + "="*60)
    print("DOCUMENT GENERATION AGENT TEST")
    print("="*60)

    agent = DocumentAgent()

    # Test 1: Generate rental contract
    print("\n[TEST 1] Generating rental contract...")
    result = await agent.execute({
        "original_query": "서울 강남구 아파트 월세계약서 만들어줘. 보증금 5천만원, 월세 100만원",
        "chat_session_id": "test_doc_1",
        "document_params": {
            "property_address": "서울시 강남구 테헤란로 123",
            "deposit": "50,000,000",
            "monthly_rent": "1,000,000",
            "lessor_name": "김철수",
            "lessee_name": "이영희",
            "contract_period": "2년"
        }
    })

    print(f"Status: {result['status']}")
    print(f"Document Type: {result.get('document_type')}")
    if result.get('generated_document'):
        print(f"Document ID: {result['generated_document'].get('metadata', {}).get('document_id')}")
    if result.get('document_summary'):
        print("Summary:")
        print(result['document_summary'])

    # Test 2: Generate content certification
    print("\n[TEST 2] Generating content certification...")
    result = await agent.execute({
        "original_query": "임대료 인상 내용증명 작성해줘",
        "chat_session_id": "test_doc_2",
        "document_format": "HTML"
    })

    print(f"Status: {result['status']}")
    print(f"Format: {result.get('document_format')}")
    if result.get('validation_errors'):
        print(f"Validation Issues: {result['validation_errors']}")

    return True


async def test_review_agent():
    """Test Contract Review Agent"""
    print("\n" + "="*60)
    print("CONTRACT REVIEW AGENT TEST")
    print("="*60)

    agent = ReviewAgent()

    # Test 1: Review high-risk contract
    print("\n[TEST 1] Reviewing high-risk rental contract...")

    risky_contract = """
부동산 임대차 계약서

임대인 김철수와 임차인 이영희는 다음과 같이 계약한다.

제1조 (목적물)
서울시 강남구 테헤란로 123, 면적 85㎡

제2조 (임대차 기간)
2024년 1월 1일부터 2025년 12월 31일까지

제3조 (보증금과 월세)
보증금: 5천만원, 월세: 100만원

제4조 (특약사항)
- 중도 해지 절대 불가
- 원상복구 비용 전액 임차인 부담
- 임차인은 모든 권리를 포기한다
- 보증금은 어떠한 경우에도 반환하지 않는다

임대인: 김철수 (인)
임차인: 이영희 (인)
"""

    result = await agent.execute({
        "original_query": "이 임대차계약서 검토해줘",
        "document_content": risky_contract,
        "chat_session_id": "test_review_1"
    })

    print(f"Status: {result['status']}")
    print(f"Risk Level: {result.get('risk_level')}")
    print(f"Risk Factors Found: {len(result.get('risk_factors', []))}")

    if result.get('risk_factors'):
        print("\nTop Risk Factors:")
        for risk in result['risk_factors'][:3]:
            print(f"  - [{risk['risk_level']}] {risk['description']}")

    if result.get('recommendations'):
        print("\nRecommendations:")
        for rec in result['recommendations'][:3]:
            print(f"  - {rec}")

    # Test 2: Review normal contract
    print("\n[TEST 2] Reviewing normal contract...")

    normal_contract = """
부동산 매매 계약서

매도인 박영수와 매수인 최민정은 다음과 같이 계약한다.

제1조 (목적물)
서울시 송파구 올림픽로 456
대지면적: 200㎡, 건물면적: 150㎡

제2조 (매매대금)
매매대금: 10억원

제3조 (계약금과 잔금)
계약금: 1억원 (계약시)
잔금: 9억원 (2024년 3월 1일)

제4조 (소유권 이전)
잔금 지불과 동시에 소유권 이전

매도인: 박영수 (인)
매수인: 최민정 (인)
"""

    result = await agent.execute({
        "original_query": "이 매매계약서 검토해줘",
        "document_content": normal_contract,
        "chat_session_id": "test_review_2"
    })

    print(f"Status: {result['status']}")
    print(f"Risk Level: {result.get('risk_level')}")

    if result.get('review_report'):
        print("\nReport Preview (first 500 chars):")
        print(result['review_report'][:500] + "...")

    return True


async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("NEW AGENTS TEST SUITE")
    print("Testing Document Generation and Contract Review Agents")
    print("="*70)

    try:
        # Test Document Agent
        doc_success = await test_document_agent()
        print(f"\n[RESULT] Document Agent Test: {'PASS' if doc_success else 'FAIL'}")

        # Test Review Agent
        review_success = await test_review_agent()
        print(f"\n[RESULT] Review Agent Test: {'PASS' if review_success else 'FAIL'}")

        # Overall result
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Document Generation Agent: {'[OK]' if doc_success else '[FAIL]'}")
        print(f"Contract Review Agent: {'[OK]' if review_success else '[FAIL]'}")

        if doc_success and review_success:
            print("\nAll tests PASSED successfully!")
            return True
        else:
            print("\nSome tests FAILED. Check logs above.")
            return False

    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)