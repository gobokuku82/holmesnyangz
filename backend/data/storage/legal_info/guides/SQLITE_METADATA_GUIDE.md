# SQLite 메타데이터 DB 사용 가이드

## 📋 개요

SQLite 메타데이터 데이터베이스는 **ChromaDB 검색 성능 향상**과 **빠른 법령 정보 조회**를 위해 만들어졌습니다.

### 주요 목적
1. **검색 필터링**: 사용자 질문 분석 후 ChromaDB 검색 범위 축소
2. **메타데이터 쿼리**: "몇 조까지?", "언제 시행?" 등 빠른 응답
3. **법령 간 관계**: 참조 관계 탐색

---

## 📊 데이터베이스 구조

### 1. `laws` 테이블 - 법령 기본 정보
| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| law_id | INTEGER | Primary Key | 1 |
| doc_type | TEXT | 문서 타입 | 법률/시행령/시행규칙/대법원규칙/용어집/기타 |
| title | TEXT | 법령명 | 공인중개사법 |
| number | TEXT | 법령번호 | 제19841호 |
| enforcement_date | TEXT | 시행일 | 2024. 12. 27. |
| category | TEXT | 카테고리 | 1_공통 매매_임대차 |
| total_articles | INTEGER | 총 조항 수 | 73 |
| last_article | TEXT | 마지막 조항 | 제50조 |
| source_file | TEXT | 원본 파일명 | 공인중개사법(법률)... |

**통계** (2025-10-01 기준):
- 총 법률: 28개
- 법률: 9개, 시행령: 7개, 시행규칙: 7개
- 카테고리별: 공통 9개, 공급/관리 8개, 기타 6개, 임대차 5개

### 2. `articles` 테이블 - 조항 상세 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| article_id | INTEGER | Primary Key |
| law_id | INTEGER | Foreign Key → laws |
| article_number | TEXT | 조항 번호 (제1조) |
| article_title | TEXT | 조항 제목 |
| chapter | TEXT | 장 |
| section | TEXT | 절 |
| is_deleted | INTEGER | 삭제 여부 (0/1) |
| is_tenant_protection | INTEGER | 임차인 보호 (0/1) |
| is_tax_related | INTEGER | 세금 관련 (0/1) |
| is_delegation | INTEGER | 위임 (0/1) |
| is_penalty_related | INTEGER | 벌칙 (0/1) |
| chunk_ids | TEXT | ChromaDB chunk ID 배열 (JSON) |
| metadata_json | TEXT | 전체 메타데이터 (JSON) |

**통계**:
- 총 조항: 1,552개
- 임차인 보호: 28개
- 위임: 156개
- 벌칙: 1개

### 3. `legal_references` 테이블 - 법령 간 참조
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| reference_id | INTEGER | Primary Key |
| source_article_id | INTEGER | Foreign Key → articles |
| reference_type | TEXT | law_references/decree_references/form_references |
| target_law_title | TEXT | 참조 대상 법령명 |
| target_article_number | TEXT | 참조 대상 조항 |
| reference_text | TEXT | 원본 참조 텍스트 |

---

## 🚀 빠른 시작

### 1. DB 생성 (최초 1회만)
```bash
python create_legal_metadata_db.py
```

생성 위치: `C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info\legal_metadata.db`

### 2. 기본 사용법

```python
from legal_query_helper import LegalQueryHelper

# Context manager 사용 (권장)
with LegalQueryHelper() as helper:
    # 법률 정보 조회
    total = helper.get_law_total_articles("공인중개사법")
    print(f"총 {total}개 조항")

    # 시행일 조회
    date = helper.get_law_enforcement_date("공인중개사법")
    print(f"시행일: {date}")
```

---

## 💡 주요 사용 사례

### Use Case 1: 사용자 질문에 빠르게 답변

**질문**: "공인중개사법은 몇 조까지인가요?"

```python
with LegalQueryHelper() as helper:
    total = helper.get_law_total_articles("공인중개사법")
    last = helper.get_law_last_article("공인중개사법")

    answer = f"공인중개사법은 총 {total}개 조항이 있으며, 마지막 조항은 {last}입니다."
```

**결과**: `공인중개사법은 총 33개 조항이 있으며, 마지막 조항은 제9조입니다.`

---

### Use Case 2: ChromaDB 검색 필터 생성

**질문**: "임대차 관련 법률 조항만 검색하고 싶어요"

```python
with LegalQueryHelper() as helper:
    # 필터 생성
    filter_dict = helper.build_chromadb_filter(
        doc_type="법률",
        category="2_임대차_전세_월세",
        exclude_deleted=True
    )

    # ChromaDB 검색에 적용
    results = collection.query(
        query_embeddings=[embedding],
        where=filter_dict,  # 필터 적용!
        n_results=10
    )
```

**필터 결과**:
```python
{
    '$and': [
        {'doc_type': '법률'},
        {'category': '2_임대차_전세_월세'},
        {'is_deleted': 'False'}
    ]
}
```

**효과**: 1,700개 → 약 200개로 검색 범위 축소 (약 88% 감소)

---

### Use Case 3: 특수 조항만 검색

**질문**: "임차인 보호 조항만 찾아주세요"

```python
with LegalQueryHelper() as helper:
    # 임차인 보호 조항 조회
    articles = helper.get_special_articles(
        article_type="tenant_protection",
        category="2_임대차_전세_월세"  # 선택적
    )

    # ChromaDB 필터로 변환
    filter_dict = helper.build_chromadb_filter(
        article_type="tenant_protection",
        exclude_deleted=True
    )

    # 검색
    results = collection.query(
        query_embeddings=[embedding],
        where=filter_dict,
        n_results=10
    )
```

**결과**: 28개 임차인 보호 조항만 검색 대상

---

### Use Case 4: 특정 법률의 chunk ID 가져오기

**시나리오**: 특정 법률 전체를 검색 대상으로 설정

```python
with LegalQueryHelper() as helper:
    # 주택임대차보호법의 모든 chunk ID 조회
    chunk_ids = helper.get_chunk_ids_for_law(
        "주택임대차보호법",
        include_deleted=False
    )

    # ChromaDB에서 직접 조회
    results = collection.get(
        ids=chunk_ids,
        include=['documents', 'metadatas']
    )
```

**효과**: 특정 법률 내에서만 검색 가능

---

### Use Case 5: 비슷한 시기 시행 법률 찾기

**질문**: "공인중개사법과 비슷한 시기에 시행된 법률은?"

```python
with LegalQueryHelper() as helper:
    # 공인중개사법 시행일 기준으로 검색
    similar_laws = helper.get_laws_by_similar_enforcement_date(
        reference_title="공인중개사법",
        days_before=30,
        days_after=30
    )

    for law in similar_laws[:5]:
        print(f"{law['title']} - {law['enforcement_date']}")
```

---

## 📖 API 레퍼런스

### 법령 정보 조회

#### `get_law_by_title(title, fuzzy=True)`
법령명으로 법령 정보 조회

```python
law = helper.get_law_by_title("공인중개사법")
# Returns: {'law_id': 1, 'title': '공인중개사법', 'total_articles': 33, ...}
```

#### `get_law_total_articles(title)`
법령의 총 조항 수

```python
total = helper.get_law_total_articles("공인중개사법")
# Returns: 33
```

#### `get_law_enforcement_date(title)`
법령의 시행일

```python
date = helper.get_law_enforcement_date("공인중개사법")
# Returns: "2024. 7. 10."
```

#### `get_laws_by_doc_type(doc_type)`
문서 타입별 법령 조회

```python
laws = helper.get_laws_by_doc_type("법률")
# Returns: [{'law_id': 1, 'title': '공인중개사법', ...}, ...]
```

#### `get_laws_by_category(category)`
카테고리별 법령 조회

```python
laws = helper.get_laws_by_category("2_임대차_전세_월세")
# Returns: [법령 정보 리스트]
```

#### `search_laws(keyword)`
키워드로 법령 검색

```python
laws = helper.search_laws("임대차")
# Returns: [주택임대차보호법, 상가건물임대차보호법, ...]
```

---

### 조항 정보 조회

#### `get_articles_by_law(title, include_deleted=False)`
특정 법령의 모든 조항 조회

```python
articles = helper.get_articles_by_law("공인중개사법")
# Returns: [{'article_id': 1, 'article_number': '제1조', ...}, ...]
```

#### `get_article_chunk_ids(title, article_number)`
특정 조항의 ChromaDB chunk ID 조회

```python
chunk_ids = helper.get_article_chunk_ids("공인중개사법", "제1조")
# Returns: ['chunk_10', 'chunk_11']
```

#### `get_special_articles(article_type, category=None)`
특수 조항 검색

```python
# article_type: tenant_protection, tax_related, delegation, penalty_related
articles = helper.get_special_articles("tenant_protection")
# Returns: [임차인 보호 조항 리스트]
```

---

### ChromaDB 필터 생성

#### `build_chromadb_filter(...)`
ChromaDB where 필터 생성

```python
filter_dict = helper.build_chromadb_filter(
    doc_type="법률",              # 선택적
    category="2_임대차_전세_월세",  # 선택적
    law_title="공인중개사법",       # 선택적
    article_type="tenant_protection",  # 선택적
    exclude_deleted=True          # 기본값 True
)
# Returns: {'$and': [...]}
```

**파라미터**:
- `doc_type`: 법률/시행령/시행규칙/대법원규칙/용어집/기타
- `category`: 1_공통 매매_임대차 / 2_임대차_전세_월세 / 3_공급_및_관리_매매_분양 / 4_기타
- `law_title`: 법령명 (부분 일치)
- `article_type`: tenant_protection/tax_related/delegation/penalty_related
- `exclude_deleted`: 삭제 조항 제외 여부

---

### 기타

#### `get_chunk_ids_for_law(title, include_deleted=False)`
특정 법령의 모든 chunk ID 조회

```python
chunk_ids = helper.get_chunk_ids_for_law("공인중개사법")
# Returns: ['chunk_10', 'chunk_11', ..., 'chunk_40']
```

#### `get_statistics()`
데이터베이스 통계

```python
stats = helper.get_statistics()
# Returns: {'total_laws': 28, 'total_articles': 1552, ...}
```

---

## 🎯 LangGraph 에이전트 통합 예시

```python
from legal_query_helper import LegalQueryHelper
import chromadb
from sentence_transformers import SentenceTransformer

class LegalSearchAgent:
    def __init__(self):
        self.metadata_helper = LegalQueryHelper()
        self.chroma_client = chromadb.PersistentClient(...)
        self.collection = self.chroma_client.get_collection("korean_legal_documents")
        self.embedding_model = SentenceTransformer(...)

    def answer_question(self, question: str):
        # Step 1: 메타데이터로 빠른 답변 시도
        if "몇 조" in question:
            # "공인중개사법은 몇 조까지?"
            for law_title in self.extract_law_names(question):
                total = self.metadata_helper.get_law_total_articles(law_title)
                if total:
                    return f"{law_title}은(는) 총 {total}개 조항이 있습니다."

        if "언제" in question and "시행" in question:
            # "공인중개사법은 언제 시행?"
            for law_title in self.extract_law_names(question):
                date = self.metadata_helper.get_law_enforcement_date(law_title)
                if date:
                    return f"{law_title}의 시행일은 {date}입니다."

        # Step 2: 메타데이터로 필터 생성
        filter_dict = self.build_filter_from_question(question)

        # Step 3: ChromaDB 검색 (필터 적용)
        embedding = self.embedding_model.encode(question)
        results = self.collection.query(
            query_embeddings=[embedding.tolist()],
            where=filter_dict,
            n_results=5
        )

        # Step 4: 결과 반환
        return self.format_results(results)

    def build_filter_from_question(self, question: str):
        """질문 분석 → 필터 생성"""
        # 질문에서 키워드 추출
        doc_type = None
        category = None
        article_type = None

        if "법률" in question:
            doc_type = "법률"
        elif "시행령" in question:
            doc_type = "시행령"

        if "임대차" in question or "전세" in question or "월세" in question:
            category = "2_임대차_전세_월세"

        if "임차인 보호" in question:
            article_type = "tenant_protection"

        # 필터 생성
        return self.metadata_helper.build_chromadb_filter(
            doc_type=doc_type,
            category=category,
            article_type=article_type,
            exclude_deleted=True
        )
```

---

## 📈 성능 개선 효과

### 검색 범위 축소 예시

| 필터 조건 | 검색 대상 | 비율 |
|-----------|----------|------|
| 필터 없음 | 1,700개 | 100% |
| doc_type='법률' | ~666개 | 39% |
| doc_type='법률' + category='임대차' | ~200개 | 12% |
| doc_type='법률' + article_type='tenant_protection' | ~28개 | 1.6% |

**결과**: 최대 **98.4% 검색 범위 축소** 가능!

---

## 🔧 유지보수

### DB 재생성
ChromaDB 업데이트 후 메타데이터 DB 재생성:

```bash
python create_legal_metadata_db.py
```

### 데이터 검증
```bash
python test_metadata_integration.py
```

---

## 📝 참고사항

1. **DB 위치**: `backend/data/storage/legal_info/legal_metadata.db`
2. **자동 생성**: ChromaDB에서 자동으로 메타데이터 추출
3. **읽기 전용**: 검색/조회 용도로만 사용
4. **동기화**: ChromaDB 업데이트 시 재생성 필요

---

## 🎓 추가 예제

모든 예제와 테스트는 다음 파일 참고:
- `legal_query_helper.py` - 기본 사용법
- `test_metadata_integration.py` - 통합 테스트
- `create_legal_metadata_db.py` - DB 생성

---

**작성일**: 2025-10-01
**버전**: 1.0
**데이터 기준**: ChromaDB 1,700개 문서
