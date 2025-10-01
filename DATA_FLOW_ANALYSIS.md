# Supervisor → SearchAgent → Legal Tool 데이터 흐름 분석

## 📊 전체 구조

```
사용자 질문
    ↓
Supervisor (RealEstateMainState)
    ↓
SearchAgent (SearchAgentState)
    ↓
Legal Search Tool (실제 DB 검색)
    ↓
결과가 역순으로 전달
```

---

## 🔄 상세 데이터 흐름

### 1단계: Supervisor → SearchAgent

**위치**: `supervisor.py:803-815`

```python
# Supervisor가 SearchAgent에게 전달하는 데이터
input_data = {
    "original_query": state["query"],              # 사용자 원본 질문
    "collection_keywords": state.get("collection_keywords", []),  # Supervisor가 추출한 키워드
    "shared_context": state.get("shared_context", {}),
    "chat_session_id": state.get("chat_session_id", ""),
    "parent_todo_id": agent_todo["id"],
    "todos": todos,
    "todo_counter": state.get("todo_counter", 0)
}

# SearchAgent 실행
result = await agent.app.ainvoke(input_data)  # LangGraph 0.6 방식
```

**State 타입**: `RealEstateMainState` → `SearchAgentState`로 변환

---

### 2단계: SearchAgent 내부 처리 (4개 노드)

#### Node 1: `create_search_plan_node` (search_agent.py:251-316)

**입력**:
- `state["original_query"]`: "임대차 계약 보증금"
- `state["collection_keywords"]`: ["임대차", "보증금", "계약"]

**LLM 호출**:
```python
plan = await self.llm_client.create_search_plan(query, keywords)
# LLM이 반환하는 JSON:
{
    "selected_tools": ["legal_search"],
    "tool_parameters": {
        "legal_search": {
            "query": "임대차 보증금",
            "category": "2_임대차_전세_월세",
            "limit": 10
        }
    },
    "search_strategy": "법률 검색으로 임대차 보증금 관련 조항 검색"
}
```

**State 업데이트**:
```python
return {
    "search_plan": plan,
    "selected_tools": ["legal_search"],
    "tool_parameters": {...},
    "status": "searching"
}
```

---

#### Node 2: `execute_tools_node` (search_agent.py:332-434)

**입력**:
- `state["selected_tools"]`: `["legal_search"]`
- `state["tool_parameters"]`: `{"legal_search": {...}}`
- `state["original_query"]`: 원본 질문

**Tool 실행**:
```python
for tool_name in selected_tools:  # ["legal_search"]
    tool = tool_registry.get(tool_name)  # LegalSearchTool 가져오기

    params = tool_parameters.get(tool_name, {})
    # params = {"query": "임대차 보증금", "category": "2_임대차_전세_월세", "limit": 10}

    query = params.get("query", state["original_query"])

    # Tool 실행 (search_agent.py:401)
    result = await tool.execute(query, params)
    # result = {
    #     "status": "success",
    #     "data": [...법률 검색 결과...],
    #     "count": 3,
    #     "tool_name": "legal_search",
    #     "data_source": "database"
    # }

    tool_results[tool_name] = result
```

**State 업데이트**:
```python
return {
    "tool_results": {
        "legal_search": {
            "status": "success",
            "data": [...],
            "count": 3
        }
    },
    "successful_tools": ["legal_search"],
    "failed_tools": [],
    "status": "processing"
}
```

---

#### Node 3: `process_results_node` (search_agent.py:436-500)

**입력**:
- `state["tool_results"]`: Tool 실행 결과

**처리**:
```python
tool_results = state.get("tool_results", {})
# {
#     "legal_search": {
#         "status": "success",
#         "data": [
#             {
#                 "law_title": "주택임대차보호법",
#                 "article_number": "제49조",
#                 "content": "...",
#                 "relevance_score": 0.923
#             },
#             ...
#         ]
#     }
# }

collected_data = {}
for tool_name, result in tool_results.items():
    if result.get("status") == "success":
        data = result.get("data", [])
        collected_data[tool_name] = data  # 실제 법률 데이터 저장
```

**State 업데이트**:
```python
return {
    "collected_data": {
        "legal_search": [
            {"law_title": "...", "content": "...", ...},
            {"law_title": "...", "content": "...", ...}
        ]
    },
    "data_summary": "legal_search: 3개 결과",
    "data_quality_score": 1.0,
    "status": "processed"
}
```

---

#### Node 4: `decide_next_action_node` (search_agent.py:502-569)

**입력**:
- `state["collected_data"]`: 수집된 법률 데이터

**LLM 호출**:
```python
decision = await self.llm_client.decide_next_action(collected_data, query)
# {
#     "next_action": "return_to_supervisor",
#     "reasoning": "법률 데이터 충분히 수집됨",
#     "summary": "임대차 보증금 관련 법률 3건 검색 완료"
# }
```

**State 업데이트**:
```python
return {
    "next_action": "return_to_supervisor",
    "collected_data": {...},  # 그대로 전달
    "search_summary": "임대차 보증금 관련 법률 3건 검색 완료",
    "shared_context": {**shared_context, ...collected_data},  # 병합!
    "status": "completed"
}
```

---

### 3단계: SearchAgent → Supervisor 결과 반환

**위치**: `search_agent.py:599-623`

```python
async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
    # LangGraph 실행
    result = await self.app.ainvoke(initial_state)

    # Supervisor에게 반환
    return {
        "status": "success",
        "next_action": result.get("next_action"),
        "collected_data": result.get("collected_data", {}),  # ← 법률 데이터!
        "search_summary": result.get("search_summary", ""),
        "shared_context": result.get("shared_context", {}),
        "todos": result.get("todos", [])
    }
```

**Supervisor가 받는 데이터**:
```python
agent_results["search_agent"] = {
    "status": "success",
    "collected_data": {
        "legal_search": [
            {
                "law_title": "주택임대차보호법",
                "article_number": "제49조",
                "article_title": "임대보증금에 대한 보호",
                "content": "임대인은 임대차 계약 시...",
                "relevance_score": 0.923,
                "doc_type": "법률",
                "category": "2_임대차_전세_월세"
            }
        ]
    },
    "search_summary": "임대차 보증금 관련 법률 3건 검색 완료"
}
```

---

## 🔍 Legal Search Tool 내부 동작

**위치**: `legal_search_tool.py:53-106`

```python
async def search(self, query: str, params: Dict[str, Any] = None):
    # 1. 파라미터 추출
    params = params or {}
    doc_type = params.get('doc_type') or self._detect_doc_type(query)
    category = params.get('category') or self._detect_category(query)
    # query = "임대차 보증금"
    # doc_type = None (자동 감지 안됨)
    # category = "2_임대차_전세_월세" (LLM이 전달한 값 또는 자동 감지)

    # 2. ChromaDB 필터 생성
    filter_dict = self.search_agent.metadata_helper.build_chromadb_filter(
        doc_type=doc_type,
        category=category,
        article_type=self._detect_article_type(query),
        exclude_deleted=True
    )
    # filter_dict = {
    #     "$and": [
    #         {"is_deleted": "False"},
    #         {"category": "2_임대차_전세_월세"}
    #     ]
    # }

    # 3. 벡터 검색
    embedding = self.search_agent.embedding_model.encode(query).tolist()
    # embedding = [0.123, -0.456, 0.789, ...]  # 1024차원 벡터

    results = self.search_agent.collection.query(
        query_embeddings=[embedding],
        where=filter_dict,
        n_results=10,
        include=['documents', 'metadatas', 'distances']
    )
    # ChromaDB가 반환:
    # {
    #     'ids': [['chunk_123', 'chunk_456', ...]],
    #     'documents': [['법률 조항 내용...', '법률 조항 내용...']],
    #     'metadatas': [[{...}, {...}]],
    #     'distances': [[0.077, 0.123, ...]]  # 낮을수록 유사
    # }

    # 4. 결과 포맷팅
    formatted_data = self._format_chromadb_results(results)
    # [
    #     {
    #         "doc_id": "chunk_123",
    #         "law_title": "주택임대차보호법",
    #         "article_number": "제49조",
    #         "content": "...",
    #         "relevance_score": 0.923  # 1 - distance
    #     }
    # ]

    return self.format_results(
        data=formatted_data,
        total_count=len(formatted_data),
        query=query
    )
```

---

## 🎯 핵심 포인트

### ✅ 올바르게 작동하는 부분

1. **State 전달**: Supervisor → SearchAgent는 완벽히 연결됨
2. **Tool 실행**: `tool.execute(query, params)`로 제대로 호출됨
3. **DB 검색**: ChromaDB + 임베딩 모델 정상 작동
4. **결과 반환**: `collected_data`에 법률 데이터 저장되어 Supervisor로 전달

### ⚠️ 개선 가능한 부분

1. **파라미터 중복 전달**:
   ```python
   # SearchAgent가 LLM으로 생성한 params:
   tool_parameters = {
       "legal_search": {
           "query": "임대차 보증금",
           "category": "2_임대차_전세_월세"
       }
   }

   # Tool 내부에서 또 다시 자동 감지:
   category = params.get('category') or self._detect_category(query)
   ```
   → LLM이 이미 파라미터를 생성했으므로 자동 감지는 폴백용

2. **Data 연결 확인**:
   ```python
   # search_agent.py:401 - Tool 실행
   result = await tool.execute(query, params)

   # search_agent.py:403 - State에 저장
   tool_results[tool_name] = result

   # search_agent.py:468 - collected_data로 변환
   collected_data[tool_name] = result.get("data", [])

   # search_agent.py:548 - shared_context에 병합
   shared_context.update(collected_data)

   # search_agent.py:606 - Supervisor로 반환
   return {"collected_data": collected_data, "shared_context": shared_context}
   ```
   ✅ **데이터가 제대로 연결됩니다!**

---

## 📝 실제 실행 예시

### 사용자 질문: "임대차 계약 시 보증금 관련 규정 알려줘"

```
1️⃣ Supervisor:
   - 키워드 추출: ["임대차", "계약", "보증금", "규정"]
   - 에이전트 선택: ["search_agent"]

2️⃣ SearchAgent - Node 1 (Plan):
   LLM 응답:
   {
       "selected_tools": ["legal_search"],
       "tool_parameters": {
           "legal_search": {
               "query": "임대차 보증금",
               "category": "2_임대차_전세_월세",
               "limit": 10
           }
       }
   }

3️⃣ SearchAgent - Node 2 (Execute):
   Legal Tool 호출:
   - query: "임대차 보증금"
   - params: {"category": "2_임대차_전세_월세", "limit": 10}

   ChromaDB 검색:
   - 필터: category="2_임대차_전세_월세" + is_deleted=False
   - 벡터 유사도 검색
   - 결과: 3개 법률 조항 발견

4️⃣ SearchAgent - Node 3 (Process):
   collected_data = {
       "legal_search": [
           {"law_title": "주택임대차보호법", "article_number": "제49조", ...},
           {"law_title": "주택임대차보호법", "article_number": "제37조", ...},
           {"law_title": "주택임대차보호법 시행규칙", "article_number": "제20조의2", ...}
       ]
   }

5️⃣ SearchAgent - Node 4 (Decide):
   next_action: "return_to_supervisor"

6️⃣ Supervisor 수신:
   agent_results["search_agent"]["collected_data"]
   → 법률 데이터 3건 포함
```

---

## ✅ 결론

**데이터는 올바르게 연결되어 있습니다!**

- Supervisor → SearchAgent: `input_data`로 query와 keywords 전달
- SearchAgent → Legal Tool: `tool.execute(query, params)`로 검색 요청
- Legal Tool → ChromaDB: 벡터 검색 + 메타데이터 필터링
- ChromaDB → Legal Tool: 실제 법률 문서 반환
- Legal Tool → SearchAgent: `result["data"]`에 법률 데이터
- SearchAgent → Supervisor: `collected_data`에 법률 데이터 저장
- Supervisor: `agent_results["search_agent"]["collected_data"]`로 접근 가능

**State 타입**:
- `RealEstateMainState` (Supervisor)
- `SearchAgentState` (SearchAgent 내부)
- 서로 변환되며 `collected_data` 필드로 데이터 공유
