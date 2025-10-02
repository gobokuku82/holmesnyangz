# LLM 호출 로직 분석

**최종 업데이트**: 2025-10-02
**테스트 쿼리**: "전세 재계약해야해. 전세금은 얼마나 올릴 수 있지? 지금 5억이야."
**실행 시간**: 29.26초
**총 LLM 호출**: 4회

> **신규 업데이트 (2025-10-02)**:
> - DocumentAgent, ReviewAgent 추가
> - 법률 검색 개선 (특정 조항 검색 100% 성공률)
> - SQL + ChromaDB 하이브리드 검색 구현

---

## 📊 전체 흐름

```
사용자 질문: "전세 재계약해야해. 전세금은 얼마나 올릴 수 있지? 지금 5억이야."
    ↓
┌─────────────────────────────────────────────────────────┐
│ SUPERVISOR (supervisor.py)                              │
├─────────────────────────────────────────────────────────┤
│ 1️⃣ analyze_intent_node (Line 652-708)                  │
│    → LLM 호출 #1: analyze_intent()                     │
│    → Input: query                                       │
│    → Output: {intent_type, confidence, entities, ...}  │
│    → 소요시간: ~2.6초                                   │
│                                                          │
│ 2️⃣ create_plan_node (Line 710-767)                     │
│    → LLM 호출 #2: create_execution_plan()              │
│    → Input: query + intent                             │
│    → Output: {agents, collection_keywords, reasoning}  │
│    → 소요시간: ~5.5초                                   │
│                                                          │
│ 3️⃣ execute_agents_node (Line 769-893)                  │
│    → SearchAgent 실행 (LangGraph workflow)             │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ SEARCH AGENT (search_agent.py)                         │
├─────────────────────────────────────────────────────────┤
│ 1️⃣ create_search_plan_node (Line 265-330)              │
│    → LLM 호출 #3: create_search_plan()                 │
│    → Input: query + keywords (from supervisor)         │
│    → Output: {selected_tools, tool_parameters, ...}    │
│    → 소요시간: ~2.7초                                   │
│                                                          │
│ 2️⃣ execute_tools_node (Line 332-448)                   │
│    → LegalSearchTool.execute()                         │
│    → 실제 DB 검색 (ChromaDB + Embedding)               │
│    → 소요시간: ~0.5초 (벡터 검색)                       │
│                                                          │
│ 3️⃣ process_results_node (Line 450-514)                 │
│    → collected_data 생성                                │
│                                                          │
│ 4️⃣ decide_next_action_node (Line 516-583)              │
│    → LLM 호출 #4: decide_next_action()                 │
│    → Input: collected_data + query                     │
│    → Output: {next_action, reasoning, summary}         │
│    → 소요시간: ~2.3초                                   │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ SUPERVISOR (계속)                                       │
├─────────────────────────────────────────────────────────┤
│ 4️⃣ generate_response_node (Line 895-1003)              │
│    → LLM 호출 없음                                      │
│    → agent_results를 final_response로 포맷팅           │
└─────────────────────────────────────────────────────────┘
```

---

## 🔢 LLM 호출 상세

### Supervisor: 2번 호출 (총 ~8초)

#### LLM 호출 #1: `analyze_intent()` - Intent 분류 + 의도 분석
**위치**: `supervisor.py:652-708` → `analyze_intent_node`
**호출 메서드**: `supervisor.py:241-394` → `async def analyze_intent()`
**소요시간**: ~2.6초 (2단계 LLM 호출)

**프롬프트 Stage 1 - 서비스 관련성 판단**:
```python
system_prompt = """당신은 부동산 전문 챗봇 서비스의 관련성 분류기입니다.

이 챗봇의 서비스 범위:
1. 부동산 매매/전세/월세 정보 제공
2. 부동산 시세 및 시장 분석
3. 부동산 관련 법률 및 계약 안내
4. 부동산 대출 및 금융 정보
5. 부동산 투자 및 개발 정보
6. 건축 규제 및 인허가 정보
7. 부동산 세금 및 공과금 안내

서비스 범위에 포함되지 않는 것:
- 일반적인 인사, 감정 표현, 욕설
- 부동산과 무관한 일반 지식 질문
- 다른 산업이나 주제에 대한 질의
- 의미없는 텍스트나 무작위 단어
- 개인 정보나 자기소개 (예: "내 이름은 ~야", "나는 ~다")

중요: 문맥을 우선적으로 판단하세요!
- 부동산 관련 키워드가 있어도 전체 문맥이 부동산과 무관하면 false로 분류
- 예시: "내 이름은 양도세야" → false (개인 소개, 부동산과 무관)
- 예시: "양도세가 뭐야?" → true (부동산 세금 관련 질문)

질의가 부동산 서비스와 관련이 있는지 판단하세요.
경계선에 있는 경우(예: 일반 금융이지만 부동산 대출일 수도 있는 경우) true로 분류하세요.

JSON 형식으로 응답:
{
    "is_relevant": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "판단 근거"
}"""

user_prompt = f"사용자 질의: {query}"
```

**Stage 1 반환값**:
```json
{
  "is_relevant": true,
  "confidence": 0.95,
  "reasoning": "전세 재계약 및 전세금 인상 한도는 부동산 임대차 계약 관련 질문입니다."
}
```

**프롬프트 Stage 2 - 의도 상세 분석**:
```python
system_prompt = """당신은 부동산 전문 챗봇의 의도 분석기입니다.
사용자 질의를 분석하여 구체적인 의도와 핵심 정보를 추출하세요.

의도 타입:
- search: 매물/시세 검색
- analysis: 시장 분석
- recommendation: 추천 요청
- legal: 법률/규정 관련
- loan: 대출 관련
- general: 일반 문의
- unclear: 의도가 불명확

JSON 형식으로 응답하세요:
{
    "intent_type": "의도 타입",
    "entities": {
        "region": "지역명",
        "property_type": "부동산 유형",
        "transaction_type": "거래 유형"
    },
    "keywords": ["핵심 키워드"],
    "confidence": 0.0-1.0
}"""

user_prompt = f"사용자 질의: {query}"
```

**Stage 2 반환값**:
```json
{
  "intent_type": "legal",
  "entities": {
    "region": null,
    "property_type": "전세",
    "transaction_type": "재계약"
  },
  "keywords": ["전세금", "올릴 수 있는 금액", "재계약"],
  "confidence": 0.85,
  "is_real_estate_related": true
}
```

**목적**:
1. 부동산 관련 질문인지 필터링 (is_relevant)
2. 질문의 의도 파악 및 엔티티 추출

---

#### LLM 호출 #2: `create_execution_plan()` - 에이전트 선택 및 키워드 생성
**위치**: `supervisor.py:710-767` → `create_plan_node`
**호출 메서드**: `supervisor.py:395-543` → `async def create_execution_plan()`
**소요시간**: ~5.5초

**프롬프트**:
```python
system_prompt = """당신은 부동산 챗봇의 실행 계획 수립 전문가입니다.
사용자 의도에 따라 가장 적합한 에이전트를 선택하고 실행 계획을 수립하세요.

## 에이전트 상세 명세

### 1. search_agent (검색 에이전트) - [구현 완료]
- **목적**: 부동산 관련 데이터를 검색하고 수집하는 전문 Agent
- **기능(Capabilities)**:
  • 부동산 매물 정보 검색
  • 시세 정보 조회
  • 법률 및 규정 검색
  • 대출 상품 정보 수집
  • 여러 데이터 소스 병렬 검색
  • 검색 결과 구조화 및 요약
- **한계(Limitations)**:
  • 데이터 분석이나 인사이트 도출 불가
  • 추천 로직 수행 불가
  • 복잡한 계산이나 예측 불가
- **사용 가능한 도구**:
  • legal_search: 부동산 법률 정보 검색
  • regulation_search: 부동산 규정 및 정책 검색
  • loan_search: 부동산 대출 상품 검색
  • real_estate_search: 부동산 매물 및 시세 검색
- **적합한 사용 케이스**:
  • 부동산 매물 정보가 필요한 경우
  • 시세 조회가 필요한 경우
  • 법률/규정 정보 검색이 필요한 경우
  • 대출 정보 수집이 필요한 경우
  • 여러 종류의 정보를 동시에 수집해야 하는 경우

### 2. analysis_agent (분석 에이전트) - [구현 완료]
- **목적**: 수집된 부동산 데이터를 분석하여 인사이트를 도출하는 전문 Agent
- **기능(Capabilities)**:
  • 시장 현황 분석 (가격, 거래량, 수급)
  • 가격 트렌드 및 패턴 분석
  • 지역별/단지별 비교 분석
  • 투자 가치 평가 (ROI, 수익률)
  • 리스크 요인 식별 및 평가
  • 데이터 기반 추천사항 제공
  • 분석 결과 시각화 데이터 준비
- **사용 가능한 도구**:
  • market_analyzer: 시장 현황 분석
  • trend_analyzer: 가격 트렌드 분석
  • comparative_analyzer: 지역별 비교
  • investment_evaluator: 투자 가치 평가
  • risk_assessor: 리스크 평가

## 에이전트 선택 기준

1. **검색/수집이 필요한 경우** → search_agent 선택
   - 키워드: 검색, 조회, 찾기, 알려줘, 정보, 시세, 매물, 법률, 대출

2. **분석이 필요한 경우** → analysis_agent 선택
   - 키워드: 분석, 비교, 평가, 트렌드, 동향, 전망, 시장, 투자, 리스크

3. **추천이 필요한 경우** → recommendation_agent 선택 (미구현 시 search_agent 사용)
   - 키워드: 추천, 제안, 어떤게 좋을까, 적합한, 맞춤

### 3. document_agent (문서 생성 에이전트) - [구현 완료] 🆕
- **목적**: 부동산 관련 법률 문서를 생성하는 전문 Agent
- **기능(Capabilities)**:
  • 임대차계약서, 매매계약서, 전세계약서 생성
  • 내용증명, 계약해지통지서 작성
  • 다양한 형식 지원 (TEXT, HTML, JSON, DOCX, PDF)
- **사용 가능한 도구**:
  • document_generation: 문서 생성 도구 (Mock 템플릿)
- **적합한 사용 케이스**:
  • 계약서 초안 작성이 필요한 경우
  • 법률 문서 템플릿이 필요한 경우

### 4. review_agent (계약 검토 에이전트) - [구현 완료] 🆕
- **목적**: 부동산 계약서 및 문서를 검토하고 위험을 분석하는 전문 Agent
- **기능(Capabilities)**:
  • 계약서 위험 요소 분석
  • 법적 준수사항 확인
  • 문서 완성도 평가
  • 리스크 레벨 평가 (low/medium/high/critical)
- **사용 가능한 도구**:
  • contract_review: 계약서 검토 도구 (규칙 기반)
- **적합한 사용 케이스**:
  • 계약서 검토가 필요한 경우
  • 위험 요소 파악이 필요한 경우

## 실행 계획 수립 지침

1. 사용자 의도를 정확히 파악
2. 필요한 작업을 단계별로 분해
3. 각 단계에 적합한 에이전트 선택
4. 에이전트 간 데이터 흐름 고려
5. 현재 구현된 에이전트만 선택 (search_agent, analysis_agent, document_agent, review_agent 사용 가능)

JSON 형식으로 응답하세요:
{
    "agents": ["선택된 에이전트 목록"],
    "collection_keywords": ["수집할 키워드"],
    "execution_order": "sequential 또는 parallel",
    "reasoning": "계획 수립 근거",
    "agent_capabilities_used": ["사용할 에이전트 기능 목록"]
}"""

user_prompt = f"""사용자 질의: {query}
분석된 의도: {intent}"""
```

**반환값**:
```json
{
  "agents": ["search_agent"],
  "collection_keywords": ["전세금 인상 한도", "전세 재계약 법률", "전세금 올릴 수 있는 금액"],
  "execution_order": "sequential",
  "reasoning": "전세 재계약 시 전세금 인상 한도에 대한 법률 정보를 검색하여 제공해야 하므로 search_agent를 선택했습니다.",
  "agent_capabilities_used": ["법률 및 규정 검색", "검색 결과 구조화 및 요약"]
}
```

**목적**:
1. 어떤 에이전트를 사용할지 결정
2. 에이전트에 전달할 검색 키워드 생성

---

### SearchAgent: 2번 호출 (총 ~5초)

#### LLM 호출 #3: `create_search_plan()` - 검색 도구 선택 및 파라미터 생성
**위치**: `search_agent.py:265-330` → `create_search_plan_node`
**호출 메서드**: `search_agent.py:107-175` → `async def create_search_plan()`
**소요시간**: ~2.7초

**프롬프트 (수정 후 - 2025-10-01 17:51 적용)**:
```python
system_prompt = """당신은 부동산 정보 검색 전문가입니다.
주어진 키워드를 바탕으로 적절한 검색 도구를 선택하고 검색 계획을 수립하세요.

사용 가능한 도구:
- legal_search: 법률, 계약, 세금 정보 (ChromaDB 벡터 검색 + 메타데이터 필터링)
  * 지원 필터: doc_type (법률/시행령/시행규칙/대법원규칙/용어집/기타)
  * 지원 필터: category (1_공통 매매_임대차, 2_임대차_전세_월세, 3_공급_및_관리_매매_분양, 4_기타)
  * 지원 필터: is_tenant_protection (임차인 보호 조항)
  * 지원 필터: is_tax_related (세금 관련 조항)
- regulation_search: 규정, 정책, 건축 규제
- loan_search: 대출, 금리, 금융 상품
- real_estate_search: 매물, 시세, 거래 정보

⚠️ legal_search 필터 사용 가이드:
【doc_type 필터 - 매우 신중하게 사용】
  • doc_type은 사용자가 "시행령", "시행규칙", "대법원규칙" 등을 명시적으로 언급한 경우만 사용
  • "법률", "법", "법령" 같은 일반적인 단어는 doc_type 지정 금지 (벡터 검색으로 자동 처리됨)
  • "기타"는 절대 사용 금지 (전체 데이터의 1.4%만 해당)
  • 불확실하면 doc_type을 생략 → 전체 문서에서 벡터 검색 수행 (권장)

【category 필터 - 적극 활용 권장】
  • "임대차", "전세", "월세" → category="2_임대차_전세_월세"
  • "매매", "분양", "공급" → category="3_공급_및_관리_매매_분양"
  • category는 doc_type보다 안전하고 효과적

법률 검색 예시:
- "전세금 인상 법률" → legal_search (doc_type 없음, category="2_임대차_전세_월세")
- "임대차 계약 보증금" → legal_search (doc_type 없음, category="2_임대차_전세_월세")
- "공인중개사법 시행령" → legal_search with doc_type="시행령" (명시적으로 "시행령" 언급)
- "임차인 보호 조항" → legal_search with is_tenant_protection=true
- "주택임대차보호법" → legal_search (doc_type 없음, 벡터 검색으로 자동 매칭)

JSON 형식으로 응답:
{
    "selected_tools": ["도구1", "도구2"],
    "tool_parameters": {
        "도구1": {
            "query": "검색 쿼리",
            "category": "카테고리 (권장)"
        },
        "도구2": {"param1": "value1"}
    },
    "search_strategy": "검색 전략 설명"
}"""

user_prompt = f"""사용자 질의: {query}
수집 키워드: {', '.join(keywords)}"""
```

**반환값 (실제 로그)**:
```json
{
  "selected_tools": ["legal_search"],
  "tool_parameters": {
    "legal_search": {
      "query": "전세금 인상 한도",
      "category": "2_임대차_전세_월세",
      "limit": 10
    }
  },
  "search_strategy": "전세금 인상 한도에 대한 법률 정보를 찾기 위해 legal_search 도구를 사용하여 관련 법률 문서를 검색합니다. '전세금 인상 한도'라는 키워드를 통해 전세 재계약 시 인상..."
}
```

**실제 실행된 검색**:
```python
# 로그: 2025-10-01 17:52:23
Searching legal DB - query: 전세금 인상 한도, doc_type: None, category: 2_임대차_전세_월세
Filter dict: {'is_deleted': False}
```

**주요 개선점 (2025-10-01 적용)**:
- ✅ `doc_type: None` - 과도한 필터링 방지 (이전: `doc_type: "기타"` → 0 results)
- ✅ `category: "2_임대차_전세_월세"` - 적절한 카테고리 필터 사용
- ✅ 10개 결과 반환 (이전: 0개)

**목적**:
1. 어떤 Tool을 사용할지 선택
2. Tool 파라미터 생성 (필터링 조건 포함)

---

#### LLM 호출 #4: `decide_next_action()` - 검색 결과 평가 및 다음 액션 결정
**위치**: `search_agent.py:516-583` → `decide_next_action_node`
**호출 메서드**: `search_agent.py:177-228` → `async def decide_next_action()`
**소요시간**: ~2.3초

**프롬프트**:
```python
system_prompt = """수집된 데이터를 분석하고 다음 행동을 결정하세요.

가능한 행동:
- return_to_supervisor: 감독자에게 결과 반환
- pass_to_agent: 다른 에이전트에게 전달 (target_agent 지정)
- direct_output: 사용자에게 직접 출력

JSON 형식으로 응답:
{
    "next_action": "선택한 행동",
    "target_agent": "대상 에이전트 (pass_to_agent인 경우)",
    "reasoning": "결정 이유",
    "summary": "데이터 요약"
}"""

user_prompt = f"""원본 질의: {query}
수집된 데이터 개수: {len(collected_data)}
데이터 카테고리: {list(collected_data.keys())}"""
```

**반환값**:
```json
{
  "next_action": "return_to_supervisor",
  "target_agent": null,
  "reasoning": "전세 재계약 시 전세금 인상 한도에 대한 법률 정보가 충분히 수집되었으므로 감독자에게 반환합니다.",
  "summary": "전세 재계약 시 5억 원의 전세금 인상 가능성에 대한 법적 기준을 조사한 데이터가 수집되었습니다."
}
```

**목적**:
1. 검색 결과가 충분한지 판단
2. 추가 에이전트 호출 필요 여부 결정

---

## 🔍 검색 결과 상세 (ChromaDB + Embedding)

### 검색 실행 정보
- **검색 엔진**: ChromaDB (벡터 유사도 검색)
- **임베딩 모델**: kure_v1 (Korean Legal Embedding, 1024D)
- **총 문서 수**: 1,700개
- **검색 소요시간**: ~0.5초

### 필터 적용
```python
Filter: {'is_deleted': False}
Category: 2_임대차_전세_월세
```

### 반환된 법률 문서 (Top 10, 관련도 순)

| # | Doc Type | 법률명 | 조항 | 제목 | 관련도 |
|---|----------|--------|------|------|--------|
| 1 | 법률 | 주택임대차보호법 | 제7조 | 차임 등의 증감청구권 | 0.175 |
| 2 | 시행령 | 주택임대차보호법 시행령 | 제10조 | 보증금 중 일정액의 범위 등 | 0.166 |
| 3 | 법률 | 부동산등기법 | 제73조 | 전세금반환채권의 일부양도에 따른 전세권 일부이전등기 | 0.144 |
| 4 | 시행령 | 주택임대차보호법 시행령 | **제8조** | **차임 등 증액청구의 기준 등 (5% 한도!)** | 0.102 |
| 5 | 시행규칙 | 공인중개사법 시행규칙 | 제20조 | 중개보수 및 실비의 한도 등 | 0.102 |
| 6 | 시행령 | 민간임대주택법 시행령 | 제34조의2 | 임대료 | 0.101 |
| 7 | 법률 | 민간임대주택법 | 제44조의2 | 초과 임대료의 반환 청구 | 0.095 |
| 8 | 법률 | 민간임대주택법 | 제63조 | 가산금리 | 0.081 |
| 9 | 시행령 | 주택임대차보호법 시행령 | 제11조 | 우선변제를 받을 임차인의 범위 | 0.074 |
| 10 | 법률 | 주택임대차보호법 | 제10조의2 | 초과 차임 등의 반환청구 | 0.071 |

### 핵심 법률 정보 (사용자 질문에 대한 답)

**질문**: "전세금은 얼마나 올릴 수 있지? 지금 5억이야."

**답변 근거 법률**:
- **주택임대차보호법 시행령 제8조** (관련도 0.102)
  - 내용: "차임등의 증액청구는 약정한 차임등의 **20분의 1의 금액을 초과하지 못한다**"
  - 해석: **5% 한도** (5억 × 5% = 2,500만원까지 인상 가능)

---

## 🔧 Tool에서의 LLM 호출 여부

### 결론: Tool은 LLM을 호출하지 않음 ✅

모든 Tool을 검증한 결과, **어떤 Tool도 LLM(GPT)을 호출하지 않습니다**.

### Tool별 동작 방식

#### 1. legal_search_tool.py (실제 DB 사용)
**동작**:
- ChromaDB 벡터 검색 (임베딩 유사도 비교)
- SQL 메타데이터 조회 (SQLite)
- 특정 조문 직접 조회 (정규식 패턴 매칭)

**LLM 호출**: ❌ 없음
- 임베딩 모델(`kure_v1`) 사용하지만 이는 LLM이 아님
- 벡터 변환만 수행, GPT API 호출 없음

**코드 증거**:
```python
# Line 155: 임베딩 생성 (로컬 모델, LLM 아님)
embedding = self.embedding_model.encode(query).tolist()

# Line 157: ChromaDB 벡터 검색 (DB 쿼리, LLM 아님)
results = self.collection.query(
    query_embeddings=[embedding],
    where=filter_dict,
    n_results=limit
)

# Line 212: SQL 메타데이터 보강 (DB 쿼리, LLM 아님)
law_info = self.metadata_helper.get_law_by_title(law_title, fuzzy=True)
```

---

#### 2. regulation_search_tool.py (Mock 데이터)
**동작**: Mock 데이터 반환만

**LLM 호출**: ❌ 없음

---

#### 3. loan_search_tool.py (Mock 데이터)
**동작**: Mock 데이터 반환만

**LLM 호출**: ❌ 없음

---

#### 4. real_estate_search_tool.py (Mock 데이터)
**동작**: Mock 데이터 반환만

**LLM 호출**: ❌ 없음

---

#### 5. analysis_tools.py (통계 분석)
**동작**:
- 시장 분석 (통계 계산)
- 트렌드 분석 (추세 계산)
- 비교 분석 (데이터 비교)
- 투자 평가 (수익률 계산)
- 리스크 평가 (점수 계산)

**LLM 호출**: ❌ 없음

---

### LLM vs 임베딩 모델 차이

| 항목 | LLM (GPT-4o-mini) | 임베딩 모델 (kure_v1) |
|------|------------------|---------------------|
| **목적** | 텍스트 생성, 추론, 판단 | 텍스트 → 벡터 변환 |
| **입력** | 프롬프트 (자연어) | 텍스트 (단일 문장) |
| **출력** | 텍스트 (JSON/자연어) | 1024차원 벡터 |
| **API 호출** | OpenAI API 호출 (비용 발생) | 로컬 모델 (비용 없음) |
| **소요 시간** | 2-5초 | 0.05초 |
| **사용 위치** | Supervisor, SearchAgent | legal_search_tool만 |

---

### 시스템 전체 LLM 호출 요약

**총 LLM 호출**: 4회 (모두 Supervisor + SearchAgent)

| 구분 | LLM 호출 | 벡터 검색 | SQL 쿼리 |
|------|---------|----------|---------|
| **Supervisor** | 2회 ✓ | - | - |
| **SearchAgent** | 2회 ✓ | - | - |
| **Tool (legal_search)** | - | 1회 (0.15초) | N회 (0.005초) |
| **Tool (기타)** | - | - | - |

**전체 처리 시간 분석** (쿼리: "전세금 인상 한도"):
```
총 29.26초
├─ LLM 호출: ~13초 (44%)
│  ├─ Supervisor LLM #1: 2.6초
│  ├─ Supervisor LLM #2: 5.5초
│  ├─ SearchAgent LLM #3: 2.7초
│  └─ SearchAgent LLM #4: 2.3초
│
├─ 벡터 검색 (Tool): 0.15초 (0.5%)
├─ SQL 쿼리 (Tool): 0.005초 (0.02%)
└─ 기타 (초기화, 직렬화): ~16초 (55%)
```

**핵심**:
- Tool 실행은 매우 빠름 (0.155초)
- 병목은 LLM 호출 (13초)
- 최적화 방향: LLM 호출 횟수 감소 (4회 → 1-2회)

---

## 📈 LLM 호출 요약

| # | 위치 | 메서드 | 목적 | 소요시간 | Input | Output |
|---|------|--------|------|----------|-------|--------|
| 1 | Supervisor | `analyze_intent()` (Stage 1+2) | 서비스 관련성 + 질문 의도 파악 | ~2.6초 | query | intent_type, entities, keywords, confidence |
| 2 | Supervisor | `create_execution_plan()` | 에이전트 선택 + 키워드 생성 | ~5.5초 | query + intent | agents, collection_keywords, reasoning |
| 3 | SearchAgent | `create_search_plan()` | Tool 선택 + 파라미터 생성 | ~2.7초 | query + keywords | selected_tools, tool_parameters, search_strategy |
| 4 | SearchAgent | `decide_next_action()` | 검색 결과 평가 | ~2.3초 | collected_data + query | next_action, summary, reasoning |

**총 LLM 호출**: 4번
**총 LLM 소요시간**: ~13.1초
**벡터 검색 시간**: ~0.15초 (카테고리 필터 적용 후)
**전체 실행 시간**: 29.26초 (나머지는 초기화, 직렬화 등)

---

## 💾 실제 로그 타임라인 (2025-10-01 17:51:57 실행)

```
17:51:57.275 - [START] Supervisor: analyze_intent_node
17:51:57.660 - [LLM #1-1] Stage 1: 서비스 관련성 판단 (OpenAI API 호출)
17:51:59.896 - [LLM #1-2] Stage 2: 의도 상세 분석 (OpenAI API 호출)
17:52:02.350 - [LLM #1 완료] Intent: legal, confidence: 85%

17:52:02.350 - [START] Supervisor: create_plan_node
17:52:02.350 - [LLM #2] 실행 계획 생성 (OpenAI API 호출)
17:52:07.879 - [LLM #2 완료] Selected agents: search_agent
                    Keywords: 전세금 인상 한도, 전세 재계약 법률, 전세금 올릴 수 있는 금액

17:52:07.879 - [START] Supervisor: execute_agents_node
17:52:20.958 - [START] SearchAgent: create_search_plan_node
17:52:20.958 - [LLM #3] 검색 계획 생성 (OpenAI API 호출)
17:52:23.652 - [LLM #3 완료] Selected tools: legal_search
                    Parameters: {query: "전세금 인상 한도", category: "2_임대차_전세_월세"}

17:52:23.652 - [START] SearchAgent: execute_tools_node
17:52:23.652 - [TOOL] legal_search 실행 (ChromaDB 벡터 검색)
                    Filter: {'is_deleted': False}
17:52:24.162 - [TOOL 완료] legal_search: 10 results

17:52:24.162 - [START] SearchAgent: decide_next_action_node
17:52:24.162 - [LLM #4] 다음 액션 결정 (OpenAI API 호출)
17:52:26.509 - [LLM #4 완료] Next action: return_to_supervisor

17:52:26.525 - [START] Supervisor: generate_response_node
17:52:26.525 - [완료] Final response 생성 (LLM 호출 없음)
```

---

## 💡 프롬프트 엔지니어링 개선 사항

### 개선 #1: SearchAgent doc_type 필터링 문제 해결 (2025-10-01 적용)

**문제**:
- SearchAgent LLM이 `doc_type: "기타"` 선택 → 0 results
- "기타"는 전체 데이터의 1.4%만 해당 (23/1700 문서)

**해결책**: 프롬프트에 필터 사용 가이드 추가

**Before** (Lines 123-154):
```python
법률 검색 예시:
- "임대차 계약 보증금" → legal_search with category="2_임대차_전세_월세"
- "공인중개사법 시행령" → legal_search with doc_type="시행령"
- "임차인 보호 조항" → legal_search with is_tenant_protection=true
```

**After** (Lines 136-153):
```python
⚠️ legal_search 필터 사용 가이드:
【doc_type 필터 - 매우 신중하게 사용】
  • doc_type은 사용자가 "시행령", "시행규칙", "대법원규칙" 등을 명시적으로 언급한 경우만 사용
  • "법률", "법", "법령" 같은 일반적인 단어는 doc_type 지정 금지 (벡터 검색으로 자동 처리됨)
  • "기타"는 절대 사용 금지 (전체 데이터의 1.4%만 해당)
  • 불확실하면 doc_type을 생략 → 전체 문서에서 벡터 검색 수행 (권장)

【category 필터 - 적극 활용 권장】
  • "임대차", "전세", "월세" → category="2_임대차_전세_월세"
  • "매매", "분양", "공급" → category="3_공급_및_관리_매매_분양"
  • category는 doc_type보다 안전하고 효과적

법률 검색 예시:
- "전세금 인상 법률" → legal_search (doc_type 없음, category="2_임대차_전세_월세")
- "임대차 계약 보증금" → legal_search (doc_type 없음, category="2_임대차_전세_월세")
- "공인중개사법 시행령" → legal_search with doc_type="시행령" (명시적으로 "시행령" 언급)
```

**결과**:
- ❌ Before: `doc_type: "기타"` → 0 results
- ✅ After: `doc_type: None`, `category: "2_임대차_전세_월세"` → 10 results

**파일**: `backend/app/service/agents/search_agent.py:136-153`

---

## 🎯 향후 최적화 방안

### Option 1: Supervisor LLM 호출 통합 (4회 → 3회)

**현재 문제**:
- LLM #1: analyze_intent() - 의도 분석
- LLM #2: create_execution_plan() - 에이전트 선택
- 두 작업이 유사하고 직렬 처리됨

**제안**:
```python
# 통합 프롬프트
system_prompt = """당신은 부동산 챗봇의 의도 분석 및 실행 계획 전문가입니다.
사용자 질의를 분석하여 다음을 한 번에 수행하세요:
1. 서비스 관련성 판단 (is_relevant)
2. 의도 분류 (intent_type)
3. 에이전트 선택 (agents)
4. 검색 키워드 생성 (collection_keywords)

JSON 형식으로 응답:
{
    "is_relevant": true/false,
    "intent_type": "legal",
    "agents": ["search_agent"],
    "collection_keywords": ["키워드1", "키워드2"],
    "confidence": 0.85
}"""
```

**예상 효과**:
- LLM 호출 1회 절감 (4회 → 3회)
- 실행 시간 ~5초 절감 (29초 → 24초)

---

### Option 2: decide_next_action을 Rule-based로 (4회 → 3회)

**현재 문제**:
- LLM #4: decide_next_action() - 단순히 "데이터 충분한가?" 판단
- 대부분의 경우 result count만 체크하면 됨

**제안**:
```python
async def decide_next_action_node(self, state):
    collected_data = state.get("collected_data", {})

    # Rule-based 판단
    total_results = sum(len(data) for data in collected_data.values() if isinstance(data, list))

    if total_results >= 5:
        # 충분한 데이터 → Supervisor로 복귀
        return {
            "next_action": "return_to_supervisor",
            "summary": f"{total_results}개 검색 결과 수집 완료",
            "reasoning": "충분한 검색 결과가 수집되어 감독자에게 반환합니다."
        }
    elif total_results == 0:
        # 데이터 없음 → 에러
        return {
            "next_action": "return_to_supervisor",
            "summary": "검색 결과 없음",
            "reasoning": "검색 결과가 없어 감독자에게 반환합니다."
        }
    else:
        # 애매한 경우만 LLM 호출 (1-4개 결과)
        decision = await self.llm_client.decide_next_action(collected_data, state["original_query"])
        return decision
```

**예상 효과**:
- 80% 케이스에서 LLM 호출 1회 절감 (4회 → 3회)
- 실행 시간 ~2초 절감 (29초 → 27초)

---

### Option 3: 간단한 질문 Rule-based 사전 처리 (4회 → 2회)

**제안**:
```python
async def preprocess_query_node(state):
    query = state["query"]

    # Rule 1: 법률 관련 키워드 매칭
    legal_keywords = ["법률", "규정", "계약", "세금", "전세금 인상", "보증금 증액"]
    if any(k in query for k in legal_keywords):
        return {
            "intent_type": "legal",
            "selected_agents": ["search_agent"],
            "collection_keywords": extract_keywords_rule_based(query),
            "selected_tools": ["legal_search"],
            "tool_parameters": {
                "legal_search": {
                    "query": query,
                    "category": detect_category(query),
                    "limit": 10
                }
            },
            "skip_llm": True  # LLM #1, #2, #3 스킵!
        }

    # Rule 2: 시세/매물 키워드
    if any(k in query for k in ["시세", "매물", "가격", "얼마"]):
        return {
            "intent_type": "search",
            "selected_agents": ["search_agent"],
            "selected_tools": ["real_estate_search"],
            "skip_llm": True
        }

    # 복잡한 경우만 LLM 사용
    return {"skip_llm": False}
```

**예상 효과**:
- 간단한 질문 (70% 케이스): LLM 2-3회 절감 (4회 → 1-2회)
- 실행 시간 대폭 단축 (29초 → 5-10초)

---

## 🏆 추천 최적화 전략: Hybrid Approach

```
Phase 1: 사전 필터링 (Rule-based)
  - 명확한 키워드 → 즉시 Tool 선택 (LLM 스킵)
  - 애매한 경우 → LLM 사용

Phase 2: Supervisor LLM 통합
  - analyze_intent + create_execution_plan을 1회로 통합
  - 2회 → 1회 (5초 절감)

Phase 3: SearchAgent decide_next_action Rule화
  - 결과 개수로 판단 (result >= 5 → return)
  - 1회 → 0회 (2초 절감)

최종 결과:
- 간단한 질문: LLM 1-2회 (현재 4회)
- 복잡한 질문: LLM 2-3회 (현재 4회)
- 평균 실행시간: 10-15초 (현재 29초)
- 비용 절감: 50-75%
```

---

## 📊 현재 vs 최적화 후 비교

| 항목 | 현재 | Phase 1 | Phase 2 | Phase 3 (최종) |
|------|------|---------|---------|----------------|
| LLM #1 (analyze_intent) | ✓ | Rule | Rule | Rule |
| LLM #2 (create_plan) | ✓ | ✓ | (통합) | (통합) |
| LLM #3 (search_plan) | ✓ | Rule | Rule | Rule |
| LLM #4 (decide_action) | ✓ | ✓ | ✓ | Rule |
| **총 LLM 호출** | **4회** | **2회** | **1회** | **1회** |
| **실행 시간** | **29초** | **15초** | **10초** | **8초** |
| **비용** | 4x | 2x | 1x | 1x |
| **정확도** | 높음 | 높음 | 중간 | 중간 |

---

## 🔧 구현 우선순위

### 1순위: Option 2 (decide_next_action Rule화) ⭐⭐⭐
- **난이도**: 낮음
- **효과**: LLM 1회 절감 (25% 절감)
- **리스크**: 낮음 (기존 로직 유지)
- **구현 시간**: 1시간

### 2순위: Option 1 (Supervisor LLM 통합) ⭐⭐
- **난이도**: 중간
- **효과**: LLM 1회 절감 (25% 절감)
- **리스크**: 중간 (프롬프트 복잡도 증가)
- **구현 시간**: 3시간

### 3순위: Option 3 (Rule-based 사전 처리) ⭐⭐⭐⭐⭐
- **난이도**: 높음
- **효과**: LLM 2-3회 절감 (50-75% 절감)
- **리스크**: 높음 (정확도 저하 가능성)
- **구현 시간**: 1-2일

---

## 📝 프롬프트 엔지니어링 체크리스트

### ✅ 완료된 개선
- [x] SearchAgent doc_type 필터 과도 사용 방지 (2025-10-01)
- [x] legal_search 필터 사용 가이드 추가
- [x] 예시 기반 프롬프트 개선 (Few-shot Learning)

### 🔄 진행 중
- [ ] Supervisor LLM 호출 통합 검토
- [ ] decide_next_action Rule화 검토

### 📋 향후 계획
- [ ] Rule-based 사전 처리 시스템 설계
- [ ] 프롬프트 버전 관리 시스템 구축
- [ ] A/B 테스트 프레임워크 도입
- [ ] LLM 응답 캐싱 시스템 구축

---

## 🆕 2025-10-02 업데이트: 신규 Agent 추가

### DocumentAgent LLM 호출 분석
**위치**: `agents/document_agent.py`
**LLM 호출**: 현재 0회 (Simple rule-based)

```python
# 현재 구현: Rule-based 문서 유형 감지
def _simple_analyze(self, query: str) -> Dict[str, Any]:
    query_lower = query.lower()
    if "임대차" in query_lower or "월세" in query_lower:
        doc_type = "임대차계약서"
    # ... 키워드 매칭
```

**향후 LLM 통합 시**:
```python
# LLM을 사용한 파라미터 추출
prompt = """
문서 생성 요청: {query}
필요한 파라미터를 추출하세요:
- 임대인/임차인 이름
- 주소
- 금액
"""
```

### ReviewAgent LLM 호출 분석
**위치**: `agents/review_agent.py`
**LLM 호출**: 현재 0회 (Rule-based review)

**규칙 기반 위험 분석**:
```python
risk_patterns = [
    {
        "pattern": r"중도\s*해지.*불가",
        "risk_level": "high",
        "description": "중도 해지 불가 조항"
    }
]
```

**향후 LLM 통합 시**:
- 복잡한 조항 해석
- 맥락 기반 위험 평가
- 자연어 권고사항 생성

---

## 🔧 법률 검색 개선 사항 (2025-10-02)

### SQL + ChromaDB 하이브리드 구현
**파일**: `tools/legal_query_helper.py` (신규)

**검색 플로우 개선**:
```python
1. SQL에서 법률 존재 확인
   → check_law_exists(title)

2. 존재하는 경우 chunk_ids 조회
   → get_article_chunk_ids(title, article_number)

3. ChromaDB에서 직접 조회 (벡터 검색 스킵)
   → collection.get(ids=chunk_ids)

4. 없는 법률은 "찾을 수 없습니다" 반환
   → format_results(data=[{"type": "error", ...}])
```

**성과**:
- 특정 조항 검색: 80% → 100% 성공률
- "주택임대차보호법 제7조" 정확히 반환
- 존재하지 않는 법률 명확히 구분

### 테스트 결과 요약

#### hard_query_test_100.py 결과
- **Part 1 (1-50)**: 실제 법률 검색
  - 성공: 31/50 (62%)
  - 특정 조항 완벽 검색 (제7조, 제8조 등)
- **Part 2 (51-100)**: 없는 법률 검증
  - Unicode 에러로 중단 (Windows 이슈)

#### test_nonexistent_laws.py 결과
- 5개 없는 법률 모두 "찾을 수 없습니다" 반환
- 100% 성공률

---

## 📚 참고 자료

### 파일 위치
- Supervisor: `backend/app/service/supervisor/supervisor.py`
- SearchAgent: `backend/app/service/agents/search_agent.py`
- DocumentAgent: `backend/app/service/agents/document_agent.py` 🆕
- ReviewAgent: `backend/app/service/agents/review_agent.py` 🆕
- LegalSearchTool: `backend/app/service/tools/legal_search_tool.py`
- LegalQueryHelper: `backend/app/service/tools/legal_query_helper.py` 🆕
- DocumentGenerationTool: `backend/app/service/tools/document_generation_tool.py` 🆕
- ContractReviewTool: `backend/app/service/tools/contract_review_tool.py` 🆕
- 테스트 스크립트: `backend/app/service/tests/query_test_2agent.py`
- 신규 테스트: `backend/app/service/tests/test_new_agents.py` 🆕

### 주요 설정
- LLM 모델: `gpt-4o-mini`
- Temperature: 0.3 (search), 0.1 (intent)
- Max Tokens: 1000
- Response Format: JSON

### ChromaDB 통계
- 총 문서: 1,700개
- DB 크기: 59MB
- 임베딩 차원: 1024D
- 문서 타입 분포:
  - 법률: 666 (39.2%)
  - 시행령: 426 (25.1%)
  - 시행규칙: 268 (15.8%)
  - 대법원규칙: 225 (13.2%)
  - 용어집: 92 (5.4%)
  - 기타: 23 (1.4%) ← 최소!
