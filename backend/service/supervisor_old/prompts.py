"""
LLM Prompt Templates for Supervisor
Used for intent analysis, planning, and evaluation
"""

from typing import Dict, Any


INTENT_ANALYSIS_PROMPT = """
당신은 부동산 챗봇의 의도 분석 전문가입니다. 사용자의 질문을 분석하여 다음 정보를 JSON 형식으로 추출하세요.

**추출할 정보:**
1. intent_type: 질문의 유형
   - "search": 매물 검색 (예: "강남 아파트 찾아줘")
   - "analysis": 시세 분석 (예: "강남 아파트 시세 알려줘")
   - "comparison": 지역 비교 (예: "강남과 서초 아파트 비교해줘")
   - "recommendation": 추천 (예: "투자하기 좋은 아파트 추천해줘")

2. region: 지역명 (예: "서울특별시 강남구", "경기도 성남시")
3. property_type: 매물 유형 ("아파트", "오피스텔", "빌라", "단독주택" 중 하나, 없으면 null)
4. deal_type: 거래 유형 ("매매", "전세", "월세" 중 하나, 없으면 null)
5. price_range: 가격 범위 (예: {{"min": 100000, "max": 150000}}, 없으면 null)
6. size_range: 평형 범위 (예: {{"min": 30, "max": 40}}, 없으면 null)

**사용자 질문:**
{query}

**응답 형식 (JSON):**
{{
  "intent_type": "search",
  "region": "서울특별시 강남구",
  "property_type": "아파트",
  "deal_type": "매매",
  "price_range": {{"min": 100000, "max": 150000}},
  "size_range": {{"min": 30, "max": 40}}
}}

**중요:** JSON 형식으로만 응답하고, 추가 설명은 하지 마세요.
"""


PLAN_BUILDING_PROMPT = """
당신은 부동산 챗봇의 실행 계획 수립 전문가입니다. 사용자 의도를 기반으로 필요한 Agent와 실행 전략을 결정하세요.

**사용 가능한 Agent:**
1. property_search: 매물 검색 Agent
2. market_analysis: 시장 분석 Agent
3. region_comparison: 지역 비교 Agent
4. investment_advisor: 투자 자문 Agent

**실행 전략:**
- "sequential": 순차 실행 (Agent 간 의존성이 있을 때)
- "parallel": 병렬 실행 (독립적인 Agent들)
- "dag": DAG 방식 (복잡한 의존성)

**사용자 의도:**
{intent}

**응답 형식 (JSON):**
{{
  "strategy": "sequential",
  "agents": [
    {{
      "name": "property_search",
      "order": 1,
      "params": {{
        "region": "서울특별시 강남구",
        "property_type": "아파트",
        "deal_type": "매매"
      }}
    }},
    {{
      "name": "market_analysis",
      "order": 2,
      "params": {{
        "region": "서울특별시 강남구"
      }}
    }}
  ]
}}

**규칙:**
1. intent_type이 "search"면 property_search만 사용
2. intent_type이 "analysis"면 property_search + market_analysis
3. intent_type이 "comparison"면 property_search + region_comparison
4. intent_type이 "recommendation"면 모든 Agent 사용

**중요:** JSON 형식으로만 응답하고, 추가 설명은 하지 마세요.
"""


EVALUATION_PROMPT = """
당신은 부동산 챗봇의 결과 평가 전문가입니다. Agent 실행 결과를 평가하여 품질을 판단하세요.

**Agent 실행 결과:**
{agent_results}

**평가 기준:**
1. **완전성 (completeness):** 모든 필요한 데이터가 수집되었는가?
2. **정확성 (accuracy):** 데이터가 정확하고 신뢰할 수 있는가?
3. **일관성 (consistency):** Agent 결과들이 서로 모순되지 않는가?

**응답 형식 (JSON):**
{{
  "quality_score": 0.85,
  "completeness": true,
  "accuracy": true,
  "consistency": true,
  "needs_retry": false,
  "retry_agents": [],
  "feedback": "모든 데이터가 성공적으로 수집되었습니다."
}}

**재시도 조건:**
- Agent가 에러를 반환했을 때
- 데이터가 불완전할 때 (completeness: false)
- 데이터가 부정확할 때 (accuracy: false)

**중요:** JSON 형식으로만 응답하고, 추가 설명은 하지 마세요.
"""


RESPONSE_FORMATTING_PROMPT = """
당신은 부동산 챗봇의 응답 생성 전문가입니다. Agent 결과를 사용자 친화적인 형식으로 변환하세요.

**사용자 질문:**
{query}

**Agent 결과:**
{agent_results}

**응답 형식:**
1. **간단한 답변 (answer):** 사용자 질문에 대한 직접적인 답변 (2-3문장)
2. **매물 목록 (listings):** 검색된 매물 리스트 (최대 10개)
3. **인사이트 (insights):** 분석 결과 및 특징 (bullet points)
4. **메타데이터 (metadata):** 통계 정보

**응답 예시:**
{{
  "answer": "강남구의 30평대 아파트 매매 시세는 평균 12억원입니다. 최근 3개월 간 5% 상승했으며, 교통 접근성이 좋은 지역의 가격이 더 높습니다.",
  "listings": [
    {{
      "name": "래미안 아파트",
      "region": "서울특별시 강남구 역삼동",
      "price": 120000,
      "size": 32,
      "deal_type": "매매"
    }}
  ],
  "insights": [
    "강남구는 학군이 우수하여 수요가 높습니다",
    "지하철역 인근 매물의 가격이 15% 더 높습니다",
    "최근 신규 공급 부족으로 가격 상승세를 보입니다"
  ],
  "metadata": {{
    "total_listings": 10,
    "avg_price": 120000,
    "price_range": {{"min": 100000, "max": 150000}},
    "region": "서울특별시 강남구"
  }}
}}

**중요:**
- 한국어로 작성하세요
- 사용자가 이해하기 쉽게 작성하세요
- JSON 형식으로만 응답하세요
"""


def get_intent_analysis_prompt(query: str) -> str:
    """Get intent analysis prompt with user query"""
    return INTENT_ANALYSIS_PROMPT.format(query=query)


def get_plan_building_prompt(intent: Dict[str, Any]) -> str:
    """Get plan building prompt with extracted intent"""
    import json
    return PLAN_BUILDING_PROMPT.format(intent=json.dumps(intent, ensure_ascii=False, indent=2))


def get_evaluation_prompt(agent_results: Dict[str, Any]) -> str:
    """Get evaluation prompt with agent results"""
    import json
    return EVALUATION_PROMPT.format(agent_results=json.dumps(agent_results, ensure_ascii=False, indent=2))


def get_response_formatting_prompt(query: str, agent_results: Dict[str, Any]) -> str:
    """Get response formatting prompt"""
    import json
    return RESPONSE_FORMATTING_PROMPT.format(
        query=query,
        agent_results=json.dumps(agent_results, ensure_ascii=False, indent=2)
    )