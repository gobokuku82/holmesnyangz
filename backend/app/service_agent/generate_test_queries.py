"""
하이브리드 법률 검색 시스템 테스트 쿼리 생성기

SQLite 메타데이터 + ChromaDB 벡터 검색의 장점을 활용하는 100개 테스트 쿼리 생성

테스트 카테고리:
1. 특정 조항 검색 (SQLite 직접 조회)
2. 시맨틱 검색 (ChromaDB 벡터 검색)
3. 메타데이터 필터링 (doc_type, category)
4. 임차인 보호 조항 (is_tenant_protection)
5. 복합 검색 (메타데이터 + 벡터)
6. 법령 간 참조 관계
7. 카테고리별 검색
8. 시간대별 검색 (enforcement_date)
"""

import json
from pathlib import Path

# 하이브리드 검색의 장점을 활용한 테스트 쿼리 생성
TEST_QUERIES = []

# ============================================================================
# Category 1: 특정 조항 검색 (SQLite 직접 조회의 장점)
# ============================================================================
SPECIFIC_ARTICLE_QUERIES = [
    # 주택임대차보호법
    "주택임대차보호법 제1조",
    "주택임대차보호법 제2조",
    "주택임대차보호법 제3조",
    "주택임대차보호법 제4조 대항력",
    "주택임대차보호법 제5조 우선변제권",
    "주택임대차보호법 제6조 계약갱신요구권",
    "주택임대차보호법 제7조 차임 증액",
    "주택임대차보호법 제8조 확정일자",

    # 민법
    "민법 제618조 임대차",
    "민법 제622조 임차인의 의무",
    "민법 제626조 임대인의 의무",
    "민법 제627조 보증금 반환",

    # 공인중개사법
    "공인중개사법 제10조",
    "공인중개사법 제25조 중개보수",
    "공인중개사법 제30조 손해배상",
]

# ============================================================================
# Category 2: 시맨틱 검색 (ChromaDB 벡터 검색의 장점)
# ============================================================================
SEMANTIC_QUERIES = [
    # 전세 관련
    "전세금 5% 인상 제한",
    "전세 보증금은 얼마까지 올릴 수 있나요",
    "전세 계약 갱신할 때 임대료 인상률",
    "전세금 반환 시기",
    "전세 계약 종료 후 보증금 돌려받기",

    # 월세 관련
    "월세 인상 한도",
    "월세를 전세로 전환할 수 있나요",
    "월세 계약 갱신 거부",

    # 계약 갱신
    "임대차 계약 갱신 요구권",
    "2년 계약 만료 후 재계약",
    "계약 갱신 거부 사유",
    "임대인이 계약 갱신을 거부하는 경우",

    # 보증금 관련
    "임대차 보증금 반환 청구",
    "보증금 반환 지연 이자",
    "임대인이 보증금을 안 돌려줄 때",
    "소액 보증금 우선변제",

    # 대항력 관련
    "전입신고와 대항력",
    "임차권 등기명령",
    "대항력이 발생하는 시점",
    "확정일자 받는 방법",
]

# ============================================================================
# Category 3: 메타데이터 필터링 (SQLite 장점)
# ============================================================================
METADATA_FILTER_QUERIES = [
    # 문서 타입별
    "주택임대차보호법 시행령",
    "주택임대차보호법 시행규칙",
    "공인중개사법 시행령",
    "민법 임대차 규정",

    # 카테고리별
    "임대차 관련 법률",
    "전세 월세 관련 규정",
    "매매 분양 관련 법률",
]

# ============================================================================
# Category 4: 임차인 보호 조항 (is_tenant_protection 필터)
# ============================================================================
TENANT_PROTECTION_QUERIES = [
    "임차인 보호 조항",
    "임차인 권리 보호",
    "임차인에게 유리한 법",
    "세입자 보호 규정",
    "임대차 약자 보호",
]

# ============================================================================
# Category 5: 복합 검색 (하이브리드의 진가)
# ============================================================================
COMPLEX_QUERIES = [
    # 시맨틱 + 메타데이터
    "주택임대차보호법에서 전세금 인상 제한 조항",
    "민법상 임차인의 수선 의무",
    "공인중개사법상 중개수수료 상한",

    # 시맨틱 + 카테고리
    "임대차 계약에서 임차인이 알아야 할 권리",
    "전세 계약 시 주의사항",
    "월세 계약서 필수 기재사항",

    # 다중 조건
    "소액임차인 우선변제권 요건",
    "임대차 계약 해지 사유와 절차",
    "보증금 반환청구권 행사 방법",
]

# ============================================================================
# Category 6: 실전 사례 (사용자 관점)
# ============================================================================
REAL_CASE_QUERIES = [
    "집주인이 갑자기 나가라고 하면",
    "전세금을 20% 올려달라고 하는데",
    "계약서에 확정일자가 없으면",
    "전입신고를 늦게 했는데 괜찮나요",
    "임대인이 집을 팔았는데 계약은 유효한가요",
    "보증금을 못 받고 이사 가야 하나요",
    "중개사가 수수료를 더 받으려고 해요",
    "계약 만료 6개월 전 통보받았어요",
    "전세 사기 피해 예방 방법",
    "임대차 분쟁 해결 절차",
]

# ============================================================================
# Category 7: 법률 용어 검색
# ============================================================================
LEGAL_TERM_QUERIES = [
    "대항력이란",
    "우선변제권이란",
    "확정일자란",
    "임차권 등기명령이란",
    "소액임차인이란",
    "계약갱신요구권이란",
    "차임 증액청구권이란",
]

# ============================================================================
# Category 8: 공인중개사 관련
# ============================================================================
REAL_ESTATE_AGENT_QUERIES = [
    "공인중개사 중개수수료 계산",
    "중개보수 상한액",
    "중개사 의무사항",
    "부동산 중개 계약서 작성",
    "중개사 과실 손해배상",
    "중개수수료는 누가 내나요",
]

# ============================================================================
# Category 9: 특수 상황
# ============================================================================
SPECIAL_CASE_QUERIES = [
    "재개발 지역 임대차 계약",
    "다가구 주택 임대차",
    "상가 임대차와 주택 임대차 차이",
    "전세권 설정 등기",
    "임대차 계약 무효 사유",
]

# ============================================================================
# Category 10: 절차 및 방법
# ============================================================================
PROCEDURE_QUERIES = [
    "임대차 계약서 작성 방법",
    "확정일자 받는 절차",
    "전입신고 방법",
    "임차권 등기명령 신청",
    "보증금 반환 소송 절차",
    "임대차 분쟁조정 신청",
]

# 모든 쿼리 통합
TEST_QUERIES.extend(SPECIFIC_ARTICLE_QUERIES)
TEST_QUERIES.extend(SEMANTIC_QUERIES)
TEST_QUERIES.extend(METADATA_FILTER_QUERIES)
TEST_QUERIES.extend(TENANT_PROTECTION_QUERIES)
TEST_QUERIES.extend(COMPLEX_QUERIES)
TEST_QUERIES.extend(REAL_CASE_QUERIES)
TEST_QUERIES.extend(LEGAL_TERM_QUERIES)
TEST_QUERIES.extend(REAL_ESTATE_AGENT_QUERIES)
TEST_QUERIES.extend(SPECIAL_CASE_QUERIES)
TEST_QUERIES.extend(PROCEDURE_QUERIES)

# 쿼리 메타데이터 추가
QUERIES_WITH_METADATA = []
for i, query in enumerate(TEST_QUERIES[:100], 1):  # 100개로 제한
    # 카테고리 결정
    if query in SPECIFIC_ARTICLE_QUERIES:
        category = "특정조항검색"
        expected_strategy = "SQLite 직접 조회"
    elif query in SEMANTIC_QUERIES:
        category = "시맨틱검색"
        expected_strategy = "ChromaDB 벡터 검색"
    elif query in METADATA_FILTER_QUERIES:
        category = "메타데이터필터링"
        expected_strategy = "SQLite 필터 + 벡터 검색"
    elif query in TENANT_PROTECTION_QUERIES:
        category = "임차인보호조항"
        expected_strategy = "is_tenant_protection 필터"
    elif query in COMPLEX_QUERIES:
        category = "복합검색"
        expected_strategy = "하이브리드 (메타데이터 + 벡터)"
    elif query in REAL_CASE_QUERIES:
        category = "실전사례"
        expected_strategy = "시맨틱 검색"
    elif query in LEGAL_TERM_QUERIES:
        category = "법률용어"
        expected_strategy = "벡터 검색"
    elif query in REAL_ESTATE_AGENT_QUERIES:
        category = "공인중개사"
        expected_strategy = "메타데이터 + 벡터"
    elif query in SPECIAL_CASE_QUERIES:
        category = "특수상황"
        expected_strategy = "복합 검색"
    else:
        category = "절차방법"
        expected_strategy = "시맨틱 검색"

    QUERIES_WITH_METADATA.append({
        "id": i,
        "query": query,
        "category": category,
        "expected_strategy": expected_strategy
    })


def save_queries(output_path: str = "test_queries_100.json"):
    """테스트 쿼리를 JSON 파일로 저장"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "total_count": len(QUERIES_WITH_METADATA),
            "categories": {
                "특정조항검색": len(SPECIFIC_ARTICLE_QUERIES),
                "시맨틱검색": len(SEMANTIC_QUERIES),
                "메타데이터필터링": len(METADATA_FILTER_QUERIES),
                "임차인보호조항": len(TENANT_PROTECTION_QUERIES),
                "복합검색": len(COMPLEX_QUERIES),
                "실전사례": len(REAL_CASE_QUERIES),
                "법률용어": len(LEGAL_TERM_QUERIES),
                "공인중개사": len(REAL_ESTATE_AGENT_QUERIES),
                "특수상황": len(SPECIAL_CASE_QUERIES),
                "절차방법": len(PROCEDURE_QUERIES),
            },
            "queries": QUERIES_WITH_METADATA
        }, f, ensure_ascii=False, indent=2)

    print(f"[OK] {len(QUERIES_WITH_METADATA)} test queries saved: {output_path}")


if __name__ == "__main__":
    save_queries()

    # 카테고리별 통계 출력
    print("\n[Category Statistics]")
    print(f"  1. Specific Article: {len(SPECIFIC_ARTICLE_QUERIES)}")
    print(f"  2. Semantic Search: {len(SEMANTIC_QUERIES)}")
    print(f"  3. Metadata Filter: {len(METADATA_FILTER_QUERIES)}")
    print(f"  4. Tenant Protection: {len(TENANT_PROTECTION_QUERIES)}")
    print(f"  5. Complex Search: {len(COMPLEX_QUERIES)}")
    print(f"  6. Real Cases: {len(REAL_CASE_QUERIES)}")
    print(f"  7. Legal Terms: {len(LEGAL_TERM_QUERIES)}")
    print(f"  8. Real Estate Agent: {len(REAL_ESTATE_AGENT_QUERIES)}")
    print(f"  9. Special Cases: {len(SPECIAL_CASE_QUERIES)}")
    print(f" 10. Procedures: {len(PROCEDURE_QUERIES)}")
    print(f"\nTotal: {len(QUERIES_WITH_METADATA)} queries")
