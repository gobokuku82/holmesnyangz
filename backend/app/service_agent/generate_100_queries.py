"""
100개 쿼리 생성 스크립트
다양한 카테고리의 부동산 관련 질문 생성
"""

import json
from pathlib import Path

def generate_queries():
    """100개의 다양한 테스트 쿼리 생성"""

    queries = {
        # 법률 상담 (25개)
        "legal": [
            {"id": "legal_01", "query": "전세금 5% 인상이 가능한가요?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_02", "query": "보증금 반환 안 받으면 어떻게 하나요?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_03", "query": "소액임차인 최우선변제금액은 얼마인가요?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_04", "query": "전세 계약 중 집주인이 바뀌면 어떻게 되나요?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_05", "query": "임대차보호법 적용 범위가 어떻게 되나요?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_06", "query": "월세를 전세로 바꿀 수 있나요?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_07", "query": "전세권 설정 비용은 얼마나 드나요?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_08", "query": "임대인이 집 수리를 안 해주면 어떻게 하나요?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_09", "query": "묵시적 갱신 조건이 뭔가요?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_10", "query": "확정일자 받는 방법 알려주세요", "intent": "LEGAL_CONSULT"},
            {"id": "legal_11", "query": "전세 사기 예방 방법 알려주세요", "intent": "LEGAL_CONSULT"},
            {"id": "legal_12", "query": "임차권등기명령 신청 조건은?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_13", "query": "계약금 돌려받을 수 있나요?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_14", "query": "중개수수료는 누가 내나요?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_15", "query": "전입신고 언제까지 해야 하나요?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_16", "query": "재개발 지역 전세 계약 주의사항은?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_17", "query": "다가구주택도 임대차보호법 적용되나요?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_18", "query": "전세 계약서에 특약 넣을 수 있나요?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_19", "query": "임대인 동의 없이 전대 가능한가요?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_20", "query": "보증금 반환 소송 절차는?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_21", "query": "전세보증보험 가입 의무인가요?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_22", "query": "계약 해지 통보는 언제 해야 하나요?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_23", "query": "상가 임대차보호법도 있나요?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_24", "query": "월세 연체 시 법적 조치는?", "intent": "LEGAL_CONSULT"},
            {"id": "legal_25", "query": "전세금 증액 제한이 있나요?", "intent": "LEGAL_CONSULT"},
        ],

        # 시세 조회 (25개)
        "market": [
            {"id": "market_01", "query": "강남구 아파트 시세 알려주세요", "intent": "MARKET_INQUIRY"},
            {"id": "market_02", "query": "서초구 전세 매물 있나요?", "intent": "MARKET_INQUIRY"},
            {"id": "market_03", "query": "송파구 아파트 값 어떻게 되나요?", "intent": "MARKET_INQUIRY"},
            {"id": "market_04", "query": "마포구 전세 시세가 궁금해요", "intent": "MARKET_INQUIRY"},
            {"id": "market_05", "query": "용산구 아파트 매매가 추이는?", "intent": "MARKET_INQUIRY"},
            {"id": "market_06", "query": "강동구 빌라 전세 시세는?", "intent": "MARKET_INQUIRY"},
            {"id": "market_07", "query": "성북구 원룸 월세 얼마인가요?", "intent": "MARKET_INQUIRY"},
            {"id": "market_08", "query": "은평구 신축 아파트 가격은?", "intent": "MARKET_INQUIRY"},
            {"id": "market_09", "query": "광진구 재개발 지역 시세는?", "intent": "MARKET_INQUIRY"},
            {"id": "market_10", "query": "노원구 전세 급매물 있나요?", "intent": "MARKET_INQUIRY"},
            {"id": "market_11", "query": "강서구 오피스텔 시세 알려주세요", "intent": "MARKET_INQUIRY"},
            {"id": "market_12", "query": "관악구 투룸 전세 가격은?", "intent": "MARKET_INQUIRY"},
            {"id": "market_13", "query": "동작구 아파트 시세 상승률은?", "intent": "MARKET_INQUIRY"},
            {"id": "market_14", "query": "중랑구 빌라 매매 시세는?", "intent": "MARKET_INQUIRY"},
            {"id": "market_15", "query": "성동구 역세권 전세 시세는?", "intent": "MARKET_INQUIRY"},
            {"id": "market_16", "query": "양천구 신축 빌라 가격은?", "intent": "MARKET_INQUIRY"},
            {"id": "market_17", "query": "구로구 다가구 월세는?", "intent": "MARKET_INQUIRY"},
            {"id": "market_18", "query": "금천구 원룸 시세 얼마인가요?", "intent": "MARKET_INQUIRY"},
            {"id": "market_19", "query": "영등포구 오피스텔 전세는?", "intent": "MARKET_INQUIRY"},
            {"id": "market_20", "query": "동대문구 아파트 실거래가는?", "intent": "MARKET_INQUIRY"},
            {"id": "market_21", "query": "강남 대치동 학군 아파트 시세는?", "intent": "MARKET_INQUIRY"},
            {"id": "market_22", "query": "서초 반포 아파트 가격 추이는?", "intent": "MARKET_INQUIRY"},
            {"id": "market_23", "query": "송파 잠실 신축 아파트 분양가는?", "intent": "MARKET_INQUIRY"},
            {"id": "market_24", "query": "마포 상암동 아파트 전세는?", "intent": "MARKET_INQUIRY"},
            {"id": "market_25", "query": "용산 이촌동 아파트 매매가는?", "intent": "MARKET_INQUIRY"},
        ],

        # 대출 상담 (20개)
        "loan": [
            {"id": "loan_01", "query": "주택담보대출 금리 비교해주세요", "intent": "LOAN_CONSULT"},
            {"id": "loan_02", "query": "전세자금대출 조건이 어떻게 되나요?", "intent": "LOAN_CONSULT"},
            {"id": "loan_03", "query": "신혼부부 대출 한도는?", "intent": "LOAN_CONSULT"},
            {"id": "loan_04", "query": "디딤돌대출 신청 방법 알려주세요", "intent": "LOAN_CONSULT"},
            {"id": "loan_05", "query": "보금자리론 금리가 얼마인가요?", "intent": "LOAN_CONSULT"},
            {"id": "loan_06", "query": "LTV 비율이 뭔가요?", "intent": "LOAN_CONSULT"},
            {"id": "loan_07", "query": "DSR 규제가 뭔가요?", "intent": "LOAN_CONSULT"},
            {"id": "loan_08", "query": "중도상환수수료 없는 대출은?", "intent": "LOAN_CONSULT"},
            {"id": "loan_09", "query": "버팀목전세자금 자격 조건은?", "intent": "LOAN_CONSULT"},
            {"id": "loan_10", "query": "청년전세대출 한도 얼마인가요?", "intent": "LOAN_CONSULT"},
            {"id": "loan_11", "query": "주택구입자금 대출 서류는?", "intent": "LOAN_CONSULT"},
            {"id": "loan_12", "query": "전세보증금 대출 금리는?", "intent": "LOAN_CONSULT"},
            {"id": "loan_13", "query": "생애최초 주택구입 대출 조건은?", "intent": "LOAN_CONSULT"},
            {"id": "loan_14", "query": "아파트 담보대출 한도는?", "intent": "LOAN_CONSULT"},
            {"id": "loan_15", "query": "대환대출 받을 수 있나요?", "intent": "LOAN_CONSULT"},
            {"id": "loan_16", "query": "이자 납입 방식 비교해주세요", "intent": "LOAN_CONSULT"},
            {"id": "loan_17", "query": "고정금리와 변동금리 차이는?", "intent": "LOAN_CONSULT"},
            {"id": "loan_18", "query": "대출 갈아타기 하면 이득인가요?", "intent": "LOAN_CONSULT"},
            {"id": "loan_19", "query": "신용점수 낮으면 대출 못 받나요?", "intent": "LOAN_CONSULT"},
            {"id": "loan_20", "query": "집단대출과 개별대출 차이는?", "intent": "LOAN_CONSULT"},
        ],

        # 복합 상담 (30개) - 법률+시세, 시세+대출, 법률+대출 등
        "complex": [
            {"id": "complex_01", "query": "강남 아파트 매매가와 대출 한도 알려주세요", "intent": "COMPREHENSIVE"},
            {"id": "complex_02", "query": "서초 전세 계약 시 법적 주의사항과 금리는?", "intent": "COMPREHENSIVE"},
            {"id": "complex_03", "query": "송파구 아파트 시세와 전세 대출 비교", "intent": "COMPREHENSIVE"},
            {"id": "complex_04", "query": "전세 계약하려는데 시세랑 법률 자문 필요해요", "intent": "COMPREHENSIVE"},
            {"id": "complex_05", "query": "강남구 신축 매매 시 대출과 세금 알려주세요", "intent": "COMPREHENSIVE"},
            {"id": "complex_06", "query": "전세에서 월세 전환 시 시세와 법적 절차는?", "intent": "COMPREHENSIVE"},
            {"id": "complex_07", "query": "재개발 지역 투자 시 법률과 시세 분석", "intent": "COMPREHENSIVE"},
            {"id": "complex_08", "query": "생애최초 아파트 구입 대출과 시세 상담", "intent": "COMPREHENSIVE"},
            {"id": "complex_09", "query": "전세 사기 예방법과 보증보험 비교", "intent": "COMPREHENSIVE"},
            {"id": "complex_10", "query": "마포구 전세 계약서 작성과 금리 비교", "intent": "COMPREHENSIVE"},
            {"id": "complex_11", "query": "용산 아파트 갈아타기 시 대출과 세금", "intent": "COMPREHENSIVE"},
            {"id": "complex_12", "query": "강동구 빌라 매매 시 법적 리스크와 시세", "intent": "COMPREHENSIVE"},
            {"id": "complex_13", "query": "신혼부부 전세 대출과 계약 주의사항", "intent": "COMPREHENSIVE"},
            {"id": "complex_14", "query": "성북구 재건축 아파트 투자 상담", "intent": "COMPREHENSIVE"},
            {"id": "complex_15", "query": "청년 전세대출과 임대차보호법 적용", "intent": "COMPREHENSIVE"},
            {"id": "complex_16", "query": "은평구 신축 분양과 중도금 대출", "intent": "COMPREHENSIVE"},
            {"id": "complex_17", "query": "다가구주택 매매 시 법률과 대출 조건", "intent": "COMPREHENSIVE"},
            {"id": "complex_18", "query": "광진구 역세권 투자 리스크 분석", "intent": "COMPREHENSIVE"},
            {"id": "complex_19", "query": "전세금 반환보증보험과 대출 연계", "intent": "COMPREHENSIVE"},
            {"id": "complex_20", "query": "노원구 아파트 증여 시 세금과 법률", "intent": "COMPREHENSIVE"},
            {"id": "complex_21", "query": "관악구 원룸 임대사업 시작하려는데 조언", "intent": "COMPREHENSIVE"},
            {"id": "complex_22", "query": "동작구 오피스텔 투자 수익률 분석", "intent": "COMPREHENSIVE"},
            {"id": "complex_23", "query": "중랑구 다세대 매매 법률 리스크는?", "intent": "COMPREHENSIVE"},
            {"id": "complex_24", "query": "성동구 상가주택 복합 매매 상담", "intent": "COMPREHENSIVE"},
            {"id": "complex_25", "query": "양천구 재건축 조합원 자격과 대출", "intent": "COMPREHENSIVE"},
            {"id": "complex_26", "query": "구로구 지식산업센터 투자 분석", "intent": "COMPREHENSIVE"},
            {"id": "complex_27", "query": "금천구 원룸텔 임대수익 계산", "intent": "COMPREHENSIVE"},
            {"id": "complex_28", "query": "영등포 오피스텔 갭투자 리스크", "intent": "COMPREHENSIVE"},
            {"id": "complex_29", "query": "동대문구 상가 임대차 법률 상담", "intent": "COMPREHENSIVE"},
            {"id": "complex_30", "query": "강서구 아파트 경매 입찰 전략", "intent": "COMPREHENSIVE"},
        ]
    }

    # 전체 쿼리 리스트로 변환
    all_queries = []
    for category, items in queries.items():
        for item in items:
            all_queries.append({
                "query_id": item["id"],
                "category": category,
                "query": item["query"],
                "expected_intent": item["intent"]
            })

    return all_queries


def save_queries(queries, output_file="test_queries_100.json"):
    """쿼리를 JSON 파일로 저장"""
    output_path = Path(__file__).parent / output_file

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "total": len(queries),
            "categories": {
                "legal": 25,
                "market": 25,
                "loan": 20,
                "complex": 30
            },
            "queries": queries
        }, f, ensure_ascii=False, indent=2)

    print(f"[OK] Generated {len(queries)} queries")
    print(f"[OK] Saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    queries = generate_queries()
    save_queries(queries)

    # 통계 출력
    categories = {}
    for q in queries:
        cat = q['category']
        categories[cat] = categories.get(cat, 0) + 1

    print("\n[STATS] Query Distribution:")
    for cat, count in categories.items():
        print(f"   {cat}: {count} queries")
