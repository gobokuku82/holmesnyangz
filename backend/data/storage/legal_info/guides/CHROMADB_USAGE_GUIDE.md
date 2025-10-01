# ChromaDB 사용 가이드 (LangGraph 에이전트용)

## 📌 기본 정보

### 1. ChromaDB 경로 및 설정

```python
CHROMA_DB_PATH = r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info\chroma_db"
COLLECTION_NAME = "korean_legal_documents"
EMBEDDING_MODEL_PATH = r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\kure_v1"
```

### 2. 데이터 구성

- **총 문서 수**: 1,700개 청크
- **임베딩 차원**: 1,024 (kure_v1 모델)
- **벡터 데이터 크기**: 41 MB
- **메타데이터 DB**: 20 MB (SQLite)

---

## 📊 문서 타입별 분포

| 문서 타입 | 개수 | 비율 | 설명 |
|----------|------|------|------|
| **법률** | 666 | 39.2% | 기본 법령 (예: 공인중개사법) |
| **시행령** | 426 | 25.1% | 대통령령 (예: 공인중개사법 시행령) |
| **시행규칙** | 268 | 15.8% | 부령 (예: 공인중개사법 시행규칙) |
| **대법원규칙** | 248 | 14.6% | 법원 규칙 (부동산등기규칙 등) |
| **용어집** | 92 | 5.4% | 부동산 용어 95가지 |

### 문서 타입 추출 규칙

**파일명 패턴으로 문서 타입 식별:**

```python
def extract_doc_type(source_file: str) -> str:
    """파일명에서 문서 타입 추출"""
    if '시행규칙' in source_file:
        return '시행규칙'
    elif '시행령' in source_file:
        return '시행령'
    elif '법률' in source_file or source_file.endswith('법(') or '법(' in source_file:
        return '법률'
    elif '대법원규칙' in source_file or '법원규칙' in source_file:
        return '대법원규칙'
    elif '용어' in source_file or 'glossary' in source_file.lower():
        return '용어집'
    else:
        return '기타'
```

**주의:** DB에 `document_type` 필드가 있지만 용어집 92개에만 존재. 나머지는 `source_file` 필드에서 추출 필요.

---

## 🔍 주요 메타데이터 필드

### 필수 필드 (모든 문서)

| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `source_file` | string | 원본 파일명 | "공인중개사법(법률)(제19841호)..." |
| `category` | string | 카테고리 폴더 | "1_공통 매매_임대차" |
| `chunk_index` | int | 청크 순번 | 1, 2, 3... |
| `article_number` | string | 조항 번호 | "제1조", "제2조" |
| `article_title` | string | 조항 제목 | "목적", "정의" |
| `is_deleted` | bool | 삭제 여부 | false |
| `enforcement_date` | string | 시행일 | "2024. 7. 10." |

### 법률/시행령/시행규칙 전용 필드

| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `law_title` | string | 법률명 | "공인중개사법" |
| `law_number` | string | 법률 번호 | "제19841호" |
| `decree_title` | string | 시행령명 | "공인중개사법 시행령" |
| `decree_number` | string | 시행령 번호 | "제34401호" |
| `rule_title` | string | 시행규칙명 | "공인중개사법 시행규칙" |
| `rule_number` | string | 시행규칙 번호 | "제1349호" |
| `chapter` | string | 장 | "제1장 총칙" |
| `section` | string | 절 | "제1절 통칙" |

### 참조 필드 (리스트 - JSON 문자열)

| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `law_references` | string | 법률 참조 | '["영 제8조", "법 제10조"]' |
| `decree_references` | string | 시행령 참조 | '["영 제8조제1항"]' |
| `form_references` | string | 양식 참조 | '["별지 제1호서식"]' |
| `table_references` | string | 표 참조 | '["별표 1"]' |

**중요:** 참조 필드는 JSON 문자열로 저장되어 있어 파싱 필요:
```python
import json
law_refs = json.loads(metadata.get('law_references', '[]'))
```

### 특수 Boolean 필드 (필터링용)

| 필드명 | 개수 | 설명 |
|--------|------|------|
| `is_tenant_protection` | 28 | 임차인 보호 조항 |
| `is_delegation` | 156 | 위임 조항 |
| `is_price_disclosure_related` | 90 | 가격공시 관련 |
| `is_tax_related` | 7 | 세금 관련 |
| `is_penalty_related` | 64 | 벌칙 조항 |
| `is_mediation_related` | 35 | 중재 관련 |
| `is_financial` | 42 | 금융 관련 |
| `is_committee_related` | 78 | 위원회 관련 |

### 용어집 전용 필드

| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `term_name` | string | 용어명 | "임대차" |
| `term_category` | string | 용어 카테고리 | "계약" |
| `glossary_title` | string | 용어집 제목 | "부동산_용어_95가지" |
| `definition_length` | int | 정의 길이 | 150 |

---

## 📂 카테고리 구조

### 카테고리별 문서 수

```python
CATEGORIES = {
    "1_공통 매매_임대차": {
        "id": "common_transaction",
        "name": "공통 매매·임대차",
        "count": 621,  # 추정
        "keywords": ["등기", "중개", "거래", "신고", "매매", "임대차"]
    },
    "2_임대차_전세_월세": {
        "id": "rental_lease",
        "name": "임대차·전세·월세",
        "count": 301,  # 추정
        "keywords": ["임대차", "전세", "월세", "보증금", "임차인", "임대인"]
    },
    "3_공급_및_관리_매매_분양": {
        "id": "supply_management",
        "name": "공급 및 관리·매매·분양",
        "count": 518,  # 추정
        "keywords": ["주택", "공동주택", "아파트", "분양", "관리", "입주자"]
    },
    "4_기타": {
        "id": "others",
        "name": "기타",
        "count": 260,  # 추정
        "keywords": ["가격공시", "공시지가", "분양가", "층간소음"]
    }
}
```

---

## 💻 LangGraph 에이전트 연동 코드 예시

### 1. 기본 ChromaDB 연결

```python
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from pathlib import Path
import json

class LegalSearchAgent:
    def __init__(self):
        # ChromaDB 연결
        chroma_path = Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info\chroma_db")
        self.client = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=Settings(anonymized_telemetry=False)
        )

        # 컬렉션 가져오기
        self.collection = self.client.get_collection("korean_legal_documents")

        # 임베딩 모델 로드
        model_path = Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\kure_v1")
        self.embedding_model = SentenceTransformer(str(model_path))

    def extract_doc_type(self, source_file: str) -> str:
        """파일명에서 문서 타입 추출"""
        if '시행규칙' in source_file:
            return '시행규칙'
        elif '시행령' in source_file:
            return '시행령'
        elif '법률' in source_file or '법(' in source_file:
            return '법률'
        elif '대법원규칙' in source_file or '법원규칙' in source_file:
            return '대법원규칙'
        elif '용어' in source_file:
            return '용어집'
        return '기타'

    def search(self, query: str, filters: dict = None, n_results: int = 10):
        """법률 문서 검색"""

        # 쿼리 임베딩 생성
        query_embedding = self.embedding_model.encode([query])

        # ChromaDB 검색
        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=n_results,
            where=self._build_where_clause(filters) if filters else None,
            include=["documents", "metadatas", "distances"]
        )

        # 결과 포맷팅
        formatted_results = []
        for i in range(len(results['ids'][0])):
            metadata = results['metadatas'][0][i]

            # 문서 타입 추출
            doc_type = self.extract_doc_type(metadata.get('source_file', ''))

            formatted_results.append({
                'id': results['ids'][0][i],
                'text': results['documents'][0][i],
                'doc_type': doc_type,
                'similarity': 1 - results['distances'][0][i],
                'metadata': metadata
            })

        return formatted_results

    def _build_where_clause(self, filters: dict):
        """필터 조건 생성"""
        where_conditions = []

        # 카테고리 필터
        if filters.get('category'):
            where_conditions.append({
                "category": {"$eq": filters['category']}
            })

        # Boolean 필터
        for key in ['is_tenant_protection', 'is_tax_related', 'is_deleted']:
            if key in filters and filters[key] is not None:
                where_conditions.append({
                    key: {"$eq": filters[key]}
                })

        # 삭제된 문서 제외 (기본)
        if 'is_deleted' not in filters:
            where_conditions.append({
                "is_deleted": {"$eq": False}
            })

        # 조건 결합
        if len(where_conditions) == 0:
            return None
        elif len(where_conditions) == 1:
            return where_conditions[0]
        else:
            return {"$and": where_conditions}
```

### 2. 사용 예시

```python
# 에이전트 초기화
agent = LegalSearchAgent()

# 예시 1: 기본 검색
results = agent.search("임차인 보호 조항")

# 예시 2: 카테고리 필터링
results = agent.search(
    query="전세 계약",
    filters={"category": "2_임대차_전세_월세"}
)

# 예시 3: 임차인 보호 조항만 검색
results = agent.search(
    query="보증금 반환",
    filters={"is_tenant_protection": True}
)

# 예시 4: 특정 문서 타입만 검색 (후처리)
results = agent.search("취득세")
law_results = [r for r in results if r['doc_type'] == '법률']

# 결과 출력
for result in results[:3]:
    print(f"문서 타입: {result['doc_type']}")
    print(f"유사도: {result['similarity']:.3f}")
    print(f"조항: {result['metadata'].get('article_number', 'N/A')}")
    print(f"내용: {result['text'][:100]}...")
    print("-" * 60)
```

### 3. 참조 필드 파싱

```python
def parse_references(metadata: dict):
    """참조 필드를 리스트로 파싱"""
    references = {}

    for ref_type in ['law_references', 'decree_references', 'form_references']:
        ref_value = metadata.get(ref_type, '[]')
        if isinstance(ref_value, str):
            try:
                references[ref_type] = json.loads(ref_value)
            except:
                references[ref_type] = []
        else:
            references[ref_type] = ref_value

    return references

# 사용 예시
result = results[0]
refs = parse_references(result['metadata'])
print(f"법률 참조: {refs['law_references']}")
print(f"시행령 참조: {refs['decree_references']}")
```

---

## 🎯 검색 전략 권장사항

### 1. 필터 우선순위

```python
# 가장 효과적인 필터 순서
FILTER_PRIORITY = [
    "is_deleted",           # 항상 false로 필터링 (삭제된 조항 제외)
    "category",             # 카테고리로 범위 좁히기
    "is_tenant_protection", # Boolean 특수 필터
    "is_tax_related",       # Boolean 특수 필터
]
```

### 2. 문서 타입별 검색

문서 타입은 메타데이터에 없으므로 **후처리 필터링** 권장:

```python
# Step 1: ChromaDB 검색 (n_results를 크게)
results = agent.search(query, n_results=50)

# Step 2: 문서 타입으로 후처리 필터링
filtered = [r for r in results if r['doc_type'] == '법률'][:10]
```

### 3. 계층적 검색 (법률 → 시행령 → 시행규칙)

```python
def hierarchical_search(query: str, law_title: str):
    """특정 법률의 전체 계층 검색"""

    # Step 1: 법률 검색
    results = agent.search(query, n_results=100)

    # Step 2: 문서 타입별 분류
    by_type = {
        '법률': [],
        '시행령': [],
        '시행규칙': []
    }

    for r in results:
        doc_type = r['doc_type']
        # 특정 법률 관련 문서만
        if law_title in r['metadata'].get('source_file', ''):
            if doc_type in by_type:
                by_type[doc_type].append(r)

    return by_type

# 사용
results = hierarchical_search("공인중개사 자격", "공인중개사법")
print(f"법률: {len(results['법률'])}개")
print(f"시행령: {len(results['시행령'])}개")
print(f"시행규칙: {len(results['시행규칙'])}개")
```

---

## ⚠️ 주의사항

1. **문서 타입 필터링**: DB에 `doc_type` 필드가 없으므로 `source_file`에서 추출 필요
2. **참조 필드**: JSON 문자열로 저장되어 있어 파싱 필요
3. **삭제 조항**: `is_deleted=False` 필터를 항상 적용 권장
4. **임베딩 시간**: CPU 사용 시 쿼리당 1-2초 소요
5. **한글 인코딩**: Windows 환경에서 출력 시 UTF-8 설정 필요

---

## 📚 추가 참고 자료

### 메타데이터 전체 필드 목록 (67개)

```python
ALL_METADATA_FIELDS = [
    'abbreviation', 'amendment_count', 'appendix_info', 'appendix_references',
    'article_number', 'article_title', 'article_type', 'category', 'chapter',
    'chapter_title', 'chunk_index', 'civil_execution_references', 'decree_number',
    'decree_references', 'decree_title', 'definition_length', 'deletion_date',
    'document_type', 'enforcement_date', 'env_rule_number', 'form_references',
    'glossary_title', 'has_amendments', 'has_appendix_reference', 'has_decree_reference',
    'has_formula', 'has_key_terms', 'has_ministry_rule_reference', 'has_penalty',
    'has_rule_reference', 'in_appendix', 'is_abbreviation', 'is_appraisal_related',
    'is_committee_related', 'is_court_rule', 'is_delegation', 'is_deleted',
    'is_financial', 'is_form_related', 'is_legal_term', 'is_mediation_related',
    'is_moved', 'is_noise_related', 'is_penalty_related', 'is_pilot_program',
    'is_price_disclosure_related', 'is_pricing_related', 'is_regulatory_review',
    'is_series_article', 'is_tax_related', 'is_tenant_protection', 'item_count',
    'law_article_references', 'law_number', 'law_references', 'law_title',
    'newly_established', 'other_law_references', 'price_disclosure_target',
    'rule_number', 'rule_title', 'section', 'section_title', 'series_group',
    'source_file', 'special_enforcement_date', 'table_references', 'term_category',
    'term_name', 'term_number'
]
```

### 시행일자 포맷

- 형식: `"2024. 7. 10."` (공백 포함)
- 정렬 가능하지만 날짜 파싱 필요

---

## 🔧 성능 최적화 팁

1. **배치 검색**: 여러 쿼리를 한 번에 처리
2. **캐싱**: 자주 사용하는 검색 결과 캐싱
3. **n_results 조정**: 필요한 만큼만 검색 (기본 10개)
4. **필터 먼저**: 메타데이터 필터로 후보 좁히고 벡터 검색

---

이 가이드로 LangGraph 에이전트에서 ChromaDB를 직접 사용하실 수 있습니다!