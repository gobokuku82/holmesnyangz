# LLM 호출 로직 분석

## 📊 전체 흐름

```
사용자 질문: "전세 재계약시 전세금은 얼마나 올릴 수 있어?"
    ↓
┌─────────────────────────────────────────────────────────┐
│ SUPERVISOR (supervisor.py)                              │
├─────────────────────────────────────────────────────────┤
│ 1️⃣ analyze_intent_node (Line 652-708)                  │
│    → LLM 호출 #1: analyze_intent()                     │
│    → Input: query                                       │
│    → Output: {intent_type, confidence, entities, ...}  │
│                                                          │
│ 2️⃣ create_plan_node (Line 710-767)                     │
│    → LLM 호출 #2: create_execution_plan()              │
│    → Input: query + intent                             │
│    → Output: {agents, collection_keywords, reasoning}  │
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
│                                                          │
│ 2️⃣ execute_tools_node (Line 332-434)                   │
│    → LegalSearchTool.execute()                         │
│    → 실제 DB 검색 (ChromaDB + Embedding)               │
│                                                          │
│ 3️⃣ process_results_node (Line 436-500)                 │
│    → collected_data 생성                                │
│                                                          │
│ 4️⃣ decide_next_action_node (Line 502-569)              │
│    → LLM 호출 #4: decide_next_action()                 │
│    → Input: collected_data + query                     │
│    → Output: {next_action, reasoning, summary}         │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ SUPERVISOR (계속)                                       │
├─────────────────────────────────────────────────────────┤
│ 4️⃣ generate_response_node (Line 894-959)               │
│    → LLM 호출 없음                                      │
│    → agent_results를 final_response로 포맷팅           │
└─────────────────────────────────────────────────────────┘
```

---

## 🔢 LLM 호출 상세

### Supervisor: 2번 호출

#### LLM 호출 #1: `analyze_intent()` (Line 666)
**위치**: `supervisor.py:652-708` → `analyze_intent_node`

**호출 메서드**: `supervisor.py:241-394` → `async def analyze_intent()`

**프롬프트**:
```python
system_prompt = """당신은 부동산 전문 상담사입니다.
사용자의 질의를 분석하여 다음을 파악하세요:
1. 의도 유형 (intent_type): search, analysis, legal, loan, investment, general
2. 주요 엔티티: 지역, 부동산 유형, 거래 유형, 가격대
3. 키워드 추출
...
"""

user_prompt = f"사용자 질의: {query}"
```

**반환값**:
```json
{
  "intent_type": "legal",
  "confidence": 0.85,
  "entities": {
    "region": null,
    "property_type": "전세",
    "transaction_type": "재계약"
  },
  "keywords": ["전세금", "재계약", "인상 한도"],
  "is_real_estate_related": true
}
```

**목적**: 질문의 의도 파악 및 관련성 판단

---

#### LLM 호출 #2: `create_execution_plan()` (Line 725)
**위치**: `supervisor.py:710-767` → `create_plan_node`

**호출 메서드**: `supervisor.py:395-543` → `async def create_execution_plan()`

**프롬프트**:
```python
system_prompt = """당신은 부동산 정보 시스템의 실행 계획 전문가입니다.
사용자 의도를 분석하여 적절한 에이전트를 선택하고 실행 계획을 수립하세요.

사용 가능한 에이전트:
1. search_agent: 데이터 검색 (법률, 규정, 대출, 매물)
2. analysis_agent: 데이터 분석 (시장 분석, 투자 분석, 트렌드)
...
"""

user_prompt = f"""
사용자 질의: {query}
의도 분석 결과:
- 의도 유형: {intent['intent_type']}
- 주요 엔티티: {intent.get('entities')}
- 추출된 키워드: {intent.get('keywords')}
"""
```

**반환값**:
```json
{
  "agents": ["search_agent"],
  "collection_keywords": ["전세금 인상 한도", "전세 재계약 법률", "전세금 인상 규정"],
  "reasoning": "전세 재계약 시 전세금 인상에 대한 법률 및 규정을 확인하기 위해 search_agent를 사용",
  "expected_data_sources": ["legal_search", "regulation_search"]
}
```

**목적**: 어떤 에이전트를 사용할지 결정 + 검색 키워드 생성

---

### SearchAgent: 2번 호출

#### LLM 호출 #3: `create_search_plan()` (Line 319)
**위치**: `search_agent.py:265-330` → `create_search_plan_node`

**호출 메서드**: `llm_client/search_agent_llm.py:107-175`

**프롬프트**:
```python
system_prompt = """당신은 부동산 정보 검색 전문가입니다.
주어진 키워드를 바탕으로 적절한 검색 도구를 선택하고 검색 계획을 수립하세요.

사용 가능한 도구:
- legal_search: 법률, 계약, 세금 정보 (ChromaDB 벡터 검색 + 메타데이터 필터링)
  * 지원 필터: doc_type, category, is_tenant_protection, is_tax_related
- regulation_search: 규정, 정책, 건축 규제
- loan_search: 대출, 금리, 금융 상품
- real_estate_search: 매물, 시세, 거래 정보
...
"""

user_prompt = f"""
사용자 질의: {query}
수집 키워드: {', '.join(keywords)}
"""
```

**반환값**:
```json
{
  "selected_tools": ["legal_search", "regulation_search"],
  "tool_parameters": {
    "legal_search": {
      "query": "전세금 인상 한도",
      "category": "2_임대차_전세_월세",
      "limit": 10
    },
    "regulation_search": {
      "query": "전세 재계약 규정"
    }
  },
  "search_strategy": "법률 검색으로 임대차 보증금 관련 조항 검색"
}
```

**목적**: 어떤 Tool을 사용할지 + Tool 파라미터 생성

---

#### LLM 호출 #4: `decide_next_action()` (Line 543)
**위치**: `search_agent.py:502-569` → `decide_next_action_node`

**호출 메서드**: `llm_client/search_agent_llm.py:177-238`

**프롬프트**:
```python
system_prompt = """당신은 검색 결과를 평가하는 전문가입니다.
수집된 데이터를 분석하고 다음 행동을 결정하세요.

가능한 행동:
1. return_to_supervisor: 충분한 데이터 수집 완료
2. search_more: 추가 검색 필요
3. refine_query: 쿼리 수정 후 재검색
...
"""

user_prompt = f"""
원본 질의: {query}
수집된 데이터:
- legal_search: 10개 결과
- regulation_search: 5개 결과
"""
```

**반환값**:
```json
{
  "next_action": "return_to_supervisor",
  "reasoning": "법률 데이터 충분히 수집됨",
  "summary": "전세 재계약 시 전세금 인상 가능성에 대한 법적 규제에 대한 데이터가 수집되었습니다",
  "data_quality": "good"
}
```

**목적**: 검색 결과가 충분한지 판단

---

## 📈 LLM 호출 요약

| # | 위치 | 메서드 | 목적 | Input | Output |
|---|------|--------|------|-------|--------|
| 1 | Supervisor | `analyze_intent()` | 질문 의도 파악 | query | intent_type, entities, keywords |
| 2 | Supervisor | `create_execution_plan()` | 에이전트 선택 | query + intent | agents, collection_keywords |
| 3 | SearchAgent | `create_search_plan()` | Tool 선택 | query + keywords | selected_tools, tool_parameters |
| 4 | SearchAgent | `decide_next_action()` | 결과 평가 | collected_data + query | next_action, summary |

**총 LLM 호출: 4번** (Supervisor 2번 + SearchAgent 2번)

---

## 💡 사전처리 강화 가능 영역

### 현재 문제점

1. **LLM 호출 #3 (create_search_plan)**
   - Supervisor가 이미 `collection_keywords`를 생성했는데
   - SearchAgent가 다시 LLM으로 Tool 선택
   - **중복 작업!**

2. **LLM 호출 #4 (decide_next_action)**
   - 단순히 "데이터 충분한가?" 판단
   - Rule-based로 가능 (예: result count > 0 → return)
   - **불필요한 LLM 호출!**

---

## 🎯 최적화 방안

### Option 1: Supervisor에서 Tool까지 직접 지정 (LLM 3번 → 2번)

```
Before:
Supervisor (LLM #2) → agents + keywords
  ↓
SearchAgent (LLM #3) → tools + parameters

After:
Supervisor (LLM #2) → agents + keywords + tools + parameters
  ↓
SearchAgent (LLM 없음) → tools 실행만
```

**변경점**:
- `create_execution_plan()`에서 Tool까지 선택
- SearchAgent는 `create_search_plan_node` 스킵

**장점**: LLM 호출 1회 절감
**단점**: Supervisor의 프롬프트가 복잡해짐

---

### Option 2: Rule-based 사전 필터링 강화 (LLM 4번 → 2-3번)

```python
# supervisor.py - analyze_intent_node 이전에 추가
async def preprocess_query_node(state):
    query = state["query"]

    # Rule 1: 간단한 키워드 매칭으로 의도 파악
    if any(k in query for k in ["법률", "규정", "계약", "세금"]):
        intent_type = "legal"
        agents = ["search_agent"]
        tools = ["legal_search"]

        # LLM 호출 #1, #2 스킵!
        return {
            "intent_type": intent_type,
            "selected_agents": agents,
            "selected_tools": tools,
            "skip_llm": True
        }

    # Rule 2: 시세/매물 키워드
    if any(k in query for k in ["시세", "매물", "가격"]):
        ...

    # 복잡한 경우만 LLM 사용
    return {"skip_llm": False}
```

**장점**:
- 간단한 질문은 즉시 처리 (LLM 0-1회)
- 복잡한 질문만 전체 LLM 파이프라인 사용

**단점**:
- Rule 유지보수 필요

---

### Option 3: decide_next_action을 Rule-based로 (LLM 4번 → 3번)

```python
# search_agent.py - decide_next_action_node
async def decide_next_action_node(self, state):
    collected_data = state.get("collected_data", {})

    # Rule-based 판단
    total_results = sum(len(data) for data in collected_data.values())

    if total_results >= 5:
        # 충분한 데이터 → Supervisor로 복귀
        return {
            "next_action": "return_to_supervisor",
            "summary": f"{total_results}개 검색 결과 수집 완료"
        }
    elif total_results == 0:
        # 데이터 없음 → 에러
        return {
            "next_action": "return_to_supervisor",
            "summary": "검색 결과 없음"
        }
    else:
        # 애매한 경우만 LLM 호출
        decision = await self.llm_client.decide_next_action(...)
        return decision
```

**장점**: LLM 호출 1회 절감
**단점**: 복잡한 판단 불가능

---

## 🏆 추천 전략: **Hybrid Approach**

```
1단계: 사전 필터링 (Rule-based)
  - 명확한 키워드 → 즉시 Tool 선택
  - 애매한 경우 → LLM 사용

2단계: Supervisor LLM 호출 최적화
  - intent + plan을 한 번에 (기존 2번 → 1번)

3단계: SearchAgent decide_next_action Rule화
  - 결과 개수만 체크 (LLM 불필요)

최종: LLM 4번 → 2번 (50% 절감)
```

---

## 📊 현재 vs 최적화 후

| 단계 | 현재 | 최적화 후 |
|------|------|-----------|
| Intent 분석 | LLM #1 | Rule or LLM #1 |
| Plan 생성 | LLM #2 | (통합) |
| Tool 선택 | LLM #3 | Rule-based |
| 결과 판단 | LLM #4 | Rule-based |
| **총 호출** | **4번** | **1-2번** |
| **시간** | ~10-15초 | ~3-5초 |
| **비용** | 4x | 1-2x |

---

## 질문에 대한 답변

> supervisor가 llm을 2번 호출, agent가 1번 호출 맞는가?

**아니요! 실제로는:**
- Supervisor: 2번 호출 ✓
- SearchAgent: **2번 호출** (create_search_plan + decide_next_action)
- **총 4번 호출**

> 이 과정에서 사전처리를 강화할수 없는가?

**가능합니다!**

**가장 효과적인 방법**:
1. **Supervisor의 2번 호출을 1번으로 통합** (intent + plan)
2. **SearchAgent의 decide_next_action을 Rule-based로** (결과 개수 체크)
3. **간단한 질문은 Rule-based 사전 필터링** (키워드 매칭)

→ **4번 → 1-2번으로 감소 가능**
