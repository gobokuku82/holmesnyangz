# legal_search_tool.py 개선 계획

**작성일**: 2025-10-02
**목적**: 특정 조문 검색 실패 문제 해결 및 검색 성능 향상

---

## 📋 현재 상황

### ✅ 정상 작동하는 기능
- **일반 벡터 검색**: "전세금 반환", "임차인 보호" 등 → 정상
- **카테고리 필터링**: category 파라미터 → 정상
- **doc_type 필터링**: doc_type 파라미터 → 정상
- **SQL 메타데이터 보강**: law_title로 SQL 조회 → 정상

### ❌ 문제가 있는 기능
- **특정 조문 직접 검색**: "주택임대차보호법 제7조" → 0개 결과 반환
- **ChromaDB에는 데이터 존재**:
  ```python
  collection.get(where={'$and': [{'title': '주택임대차보호법'}, {'article_number': '제7조'}]})
  # → 1개 문서 존재 확인됨
  ```

---

## 🔍 문제 원인 분석

### 1. 특정 조문 감지 로직 문제
**파일**: `backend/app/service/tools/legal_search_tool.py`
**함수**: `_is_specific_article_query(query: str)`

**현재 코드 (예상)**:
```python
def _is_specific_article_query(self, query: str) -> Optional[Dict[str, str]]:
    """특정 조문 쿼리인지 감지"""
    patterns = [
        r'(.+?)\s*제(\d+)조(?:의(\d+))?',  # "주택임대차보호법 제7조"
        r'(.+?)\s*(\d+)조(?:의(\d+))?',    # "주택임대차보호법 7조"
    ]

    for pattern in patterns:
        match = re.search(pattern, query)
        if match:
            law_title = match.group(1).strip()
            article_num = match.group(2)
            sub_num = match.group(3)

            if sub_num:
                article_number = f"제{article_num}조의{sub_num}"
            else:
                article_number = f"제{article_num}조"

            return {'law_title': law_title, 'article_number': article_number}

    return None
```

**문제점**:
1. **정규식 매칭은 정상 작동** (테스트 필요)
2. **SQL 조회 실패** 가능성:
   - `metadata_helper.get_article_chunk_ids()` 함수가 없거나 오류
   - law_title 매칭 실패 (예: "주택임대차보호법" vs "주택임대차보호법(법률)")
3. **ChromaDB 직접 조회로 전환 안됨**

### 2. SQL Helper 함수 문제
**파일**: `backend/data/storage/legal_info/guides/legal_query_helper.py`
**함수**: `get_article_chunk_ids(title, article_number)`

**현재 상태**:
- 함수가 존재하는지 확인 필요
- title 매칭 방식 (정확 매칭 vs fuzzy 매칭)
- chunk_ids 반환 형식

---

## 🎯 개선 계획

### Phase 1: 특정 조문 검색 수정 (우선순위: 높음)

#### 1-1. 정규식 테스트 및 수정
**작업 내용**:
```python
# 테스트 케이스
test_queries = [
    "주택임대차보호법 제7조",
    "부동산등기법 제73조",
    "민법 제618조",
    "공인중개사법 7조",
]

# 각 쿼리에 대해 정규식 매칭 확인
for query in test_queries:
    result = _is_specific_article_query(query)
    print(f"{query} → {result}")
```

**예상 결과**:
```
주택임대차보호법 제7조 → {'law_title': '주택임대차보호법', 'article_number': '제7조'}
부동산등기법 제73조 → {'law_title': '부동산등기법', 'article_number': '제73조'}
```

#### 1-2. ChromaDB 직접 조회 로직 추가
**현재 문제**: SQL 조회 실패 시 ChromaDB로 폴백하지 않음

**수정 방안**:
```python
def search(self, query: str, params: Dict = None):
    # 특정 조문 검색 감지
    article_query = self._is_specific_article_query(query)

    if article_query:
        law_title = article_query['law_title']
        article_number = article_query['article_number']

        # 방법 1: SQL로 chunk_ids 조회
        try:
            chunk_ids = self.metadata_helper.get_article_chunk_ids(
                title=law_title,
                article_number=article_number
            )

            if chunk_ids:
                # ChromaDB에서 해당 ID들 가져오기
                results = self.collection.get(
                    ids=chunk_ids,
                    include=['documents', 'metadatas']
                )
                return self._format_chromadb_results(results)
        except Exception as e:
            self.logger.warning(f"SQL 조회 실패: {e}")

        # 방법 2: SQL 실패 시 ChromaDB 직접 필터링 (폴백)
        try:
            results = self.collection.get(
                where={
                    '$and': [
                        {'title': {'$contains': law_title}},  # 부분 매칭
                        {'article_number': article_number}
                    ]
                },
                limit=10,
                include=['documents', 'metadatas']
            )

            if results['ids']:
                return self._format_chromadb_results(results)
        except Exception as e:
            self.logger.warning(f"ChromaDB 필터링 실패: {e}")

        # 방법 3: 모두 실패 시 일반 벡터 검색으로 폴백
        self.logger.info(f"특정 조문 직접 조회 실패, 벡터 검색으로 전환: {query}")

    # 일반 벡터 검색
    # ... 기존 로직 ...
```

#### 1-3. Title 매칭 개선
**문제**: "주택임대차보호법" vs "주택임대차보호법(법률)(제19356호)"

**해결 방법**:
```python
# SQL 조회 시 LIKE 사용
SELECT chunk_ids FROM articles
WHERE law_id IN (
    SELECT id FROM laws
    WHERE title LIKE '%주택임대차보호법%'  -- 부분 매칭
)
AND article_number = '제7조'

# 또는 ChromaDB 필터링 시
where={'title': {'$contains': '주택임대차보호법'}}
```

---

### Phase 2: 검색 성능 최적화 (우선순위: 중간)

#### 2-1. 카테고리 자동 선택 개선
**현재 문제**: SearchAgent LLM이 카테고리를 잘못 선택하거나 선택하지 않음

**해결 방법**:
- SearchAgent 프롬프트에 카테고리별 예시 추가
- Few-shot 학습 예시 추가

```python
# SearchAgent 프롬프트 예시
"""
카테고리 선택 가이드:
1. "1_공통 매매_임대차": 공인중개사, 부동산 거래신고, 등기 등
2. "2_임대차_전세_월세": 주택임대차보호법, 민간임대주택법 등
3. "3_공급_및_관리_매매_분양": 주택법, 공동주택관리법, 건축물 분양법 등
4. "4_기타": 가격공시, 용어집 등

예시:
- "전세금 반환" → 2_임대차_전세_월세
- "분양가 상한제" → 3_공급_및_관리_매매_분양
- "중개수수료" → 1_공통 매매_임대차
"""
```

#### 2-2. 검색 결과 리랭킹 추가 (선택사항)
**목적**: 벡터 검색 결과의 정확도 향상

**방법**:
```python
# 1. 벡터 검색으로 top 20 가져오기
initial_results = collection.query(
    query_embeddings=[embedding],
    n_results=20
)

# 2. 리랭커로 재정렬
from sentence_transformers import CrossEncoder
reranker = CrossEncoder('backend/app/service/models/bge-reranker-v2-m3-ko')

scores = reranker.predict([
    (query, doc) for doc in initial_results['documents'][0]
])

# 3. 상위 10개만 반환
sorted_results = sorted(zip(scores, initial_results), reverse=True)[:10]
```

---

### Phase 3: 에러 처리 및 로깅 강화 (우선순위: 낮음)

#### 3-1. 상세 로깅 추가
```python
def search(self, query: str, params: Dict = None):
    self.logger.info(f"검색 시작: query='{query}', params={params}")

    # 특정 조문 검색 시도
    article_query = self._is_specific_article_query(query)
    if article_query:
        self.logger.info(f"특정 조문 감지: {article_query}")
        # ... 처리 로직 ...

    # 벡터 검색 시도
    self.logger.info(f"벡터 검색 시작: n_results={n_results}")
    # ... 처리 로직 ...

    self.logger.info(f"검색 완료: {len(results)}개 결과 반환")
    return results
```

#### 3-2. 예외 처리 강화
```python
try:
    # ChromaDB 조회
    results = self.collection.query(...)
except Exception as e:
    self.logger.error(f"ChromaDB 조회 실패: {e}", exc_info=True)
    return {
        'status': 'error',
        'message': f'검색 중 오류 발생: {str(e)}',
        'data': []
    }
```

---

## 🧪 테스트 계획

### 테스트 케이스 1: 특정 조문 검색
```python
test_cases = [
    {
        'query': '주택임대차보호법 제7조',
        'expected_results': '> 0',
        'expected_law': '주택임대차보호법',
        'expected_article': '제7조'
    },
    {
        'query': '부동산등기법 제73조',
        'expected_results': '> 0',
        'expected_law': '부동산등기법',
        'expected_article': '제73조'
    },
    {
        'query': '공인중개사법 제33조',
        'expected_results': '> 0',
        'expected_law': '공인중개사법',
        'expected_article': '제33조'
    }
]
```

### 테스트 케이스 2: 일반 검색 (회귀 테스트)
```python
regression_tests = [
    {'query': '전세금 반환', 'expected_results': '> 0'},
    {'query': '임차인 보호', 'expected_results': '> 0'},
    {'query': '보증금 우선변제', 'expected_results': '> 0'},
]
```

### 테스트 실행
```bash
# 특정 조문 검색 테스트
python backend/app/service/tests/test_specific_article_search.py

# hard_query_test_50 재실행
python backend/app/service/tests/hard_query_test_50.py
```

---

## 📊 예상 개선 효과

### Before (현재)
- **특정 조문 검색**: 0% 성공 (0/10)
- **일반 검색**: 90% 성공 (36/40)
- **전체**: 72% 성공 (36/50)

### After (개선 후)
- **특정 조문 검색**: 80%+ 성공 (8+/10) ⬆️
- **일반 검색**: 90% 유지 (36/40)
- **전체**: 88%+ 성공 (44+/50) ⬆️ +16%p

---

## 🔧 구현 우선순위

### 즉시 수정 (Phase 1)
1. **정규식 테스트** - 5분
2. **ChromaDB 직접 조회 폴백 추가** - 30분
3. **Title 부분 매칭 수정** - 15분

**예상 소요 시간**: 50분

### 추후 개선 (Phase 2, 3)
4. SearchAgent 프롬프트 개선 - 1시간
5. 로깅 강화 - 30분
6. 리랭킹 추가 (선택) - 2시간

---

## 📝 구현 체크리스트

### Phase 1: 특정 조문 검색 수정
- [ ] `_is_specific_article_query()` 정규식 테스트
- [ ] ChromaDB 직접 조회 폴백 로직 추가
- [ ] Title 부분 매칭 (`$contains`) 적용
- [ ] 테스트 케이스 작성 및 실행
- [ ] hard_query_test_50 재실행하여 개선 확인

### Phase 2: 성능 최적화
- [ ] SearchAgent 프롬프트에 카테고리 예시 추가
- [ ] Few-shot 학습 예시 추가
- [ ] 카테고리 선택 정확도 테스트

### Phase 3: 에러 처리
- [ ] 상세 로깅 추가
- [ ] 예외 처리 강화
- [ ] 에러 메시지 사용자 친화적으로 개선

---

## 🎯 성공 기준

### 필수 (Phase 1)
- [x] ChromaDB 임베딩 완료 (1,700개, Unknown 0개)
- [ ] 특정 조문 검색 성공률 80% 이상
- [ ] hard_query_test_50 전체 성공률 85% 이상

### 선택 (Phase 2, 3)
- [ ] 카테고리 자동 선택 정확도 90% 이상
- [ ] 평균 검색 속도 < 5초
- [ ] 에러 발생 시 명확한 메시지 제공

---

## 📁 관련 파일

### 수정 대상
- `backend/app/service/tools/legal_search_tool.py` - 메인 수정 파일
- `backend/data/storage/legal_info/guides/legal_query_helper.py` - SQL helper (확인 필요)

### 테스트
- `backend/app/service/tests/hard_query_test_50.py` - 기존 테스트
- `backend/app/service/tests/test_specific_article_search.py` - 신규 생성 필요

### 참조
- `backend/data/storage/legal_info/embedding/EMBEDDING_RESULT_REPORT.md` - 임베딩 결과
- `backend/data/storage/legal_info/guides/Information_for_legal_info_data.md` - 메타데이터 정보

---

## 🚀 다음 단계

1. **Phase 1 구현** (50분)
   - ChromaDB 직접 조회 폴백 추가
   - Title 부분 매칭 수정

2. **테스트 및 검증** (30분)
   - 특정 조문 검색 테스트
   - hard_query_test_50 재실행

3. **결과 확인** (10분)
   - 성공률 개선 확인
   - 추가 개선 사항 도출

**총 예상 시간**: 1시간 30분

---

**작성자**: Claude Code
**최종 수정**: 2025-10-02 10:05
