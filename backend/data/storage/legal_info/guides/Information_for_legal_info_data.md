📋 최종 요약: LangGraph 에이전트에서 ChromaDB 사용 시 필수 정보
1. 핵심 정보
# ChromaDB 경로
CHROMA_PATH = r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info\chroma_db"

# 컬렉션명
COLLECTION = "korean_legal_documents"

# 임베딩 모델
MODEL_PATH = r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\kure_v1"

# 총 문서 수
TOTAL_DOCS = 1700

# 임베딩 차원
EMBEDDING_DIM = 1024
2. ✅ doc_type 메타데이터 (2025-10-01 업데이트 완료)
doc_type 필드가 메타데이터에 추가되었습니다! 이제 직접 필터링 가능합니다.

문서 타입별 분포:
법률: 666개 (39.2%)
시행령: 426개 (25.1%)
시행규칙: 268개 (15.8%)
대법원규칙: 225개 (13.2%)
용어집: 92개 (5.4%)
기타: 23개 (1.4%)

사용 예시:
```python
results = collection.query(
    query_embeddings=[embedding],
    where={"doc_type": "법률"},
    n_results=10
)
```
3. 주요 메타데이터 필드
항상 있는 필드:
doc_type - 문서 타입 (법률/시행령/시행규칙/대법원규칙/용어집/기타)
source_file - 원본 파일명
category - 카테고리 폴더명
article_number - 조항 번호
article_title - 조항 제목
is_deleted - 삭제 여부 (항상 false 필터링 권장)
chunk_index - 청크 순번
법률 관련 필드:
law_title, law_number
decree_title, decree_number
rule_title, rule_number
chapter, section
enforcement_date
참조 필드 (JSON 문자열):
law_references - 법률 참조
decree_references - 시행령 참조
form_references - 양식 참조
Boolean 필터 (특수 조항):
is_tenant_protection (28개) - 임차인 보호
is_tax_related (7개) - 세금 관련
is_delegation (156개) - 위임
is_penalty_related (64개) - 벌칙
4. 카테고리 정보
"1_공통 매매_임대차"          # 공통 거래
"2_임대차_전세_월세"          # 임대차
"3_공급_및_관리_매매_분양"    # 공급/관리
"4_기타"                      # 기타
5. 사용 파일
생성된 파일:
CHROMADB_USAGE_GUIDE.md - ChromaDB 사용 가이드
SQLITE_METADATA_GUIDE.md - SQLite 메타데이터 사용 가이드 ⭐ NEW
example_chromadb_usage.py - ChromaDB 예제 코드
legal_query_helper.py - SQLite 쿼리 헬퍼 ⭐ NEW
legal_metadata.db - SQLite 메타데이터 DB (28개 법률, 1,552개 조항) ⭐ NEW
6. 빠른 시작 코드

## A. ChromaDB 직접 사용
```python
from example_chromadb_usage import LegalSearchAgent
agent = LegalSearchAgent()

# 기본 검색
results = agent.search("임차인 보호")

# 카테고리 필터
results = agent.search("전세 계약", category="2_임대차_전세_월세")
```

## B. SQLite 메타데이터 활용 ⭐ 권장
```python
from legal_query_helper import LegalQueryHelper

with LegalQueryHelper() as helper:
    # 1. 빠른 메타데이터 조회
    total = helper.get_law_total_articles("공인중개사법")  # 33
    date = helper.get_law_enforcement_date("공인중개사법")  # 2024. 7. 10.

    # 2. ChromaDB 필터 생성 (검색 범위 축소)
    filter_dict = helper.build_chromadb_filter(
        doc_type="법률",
        category="2_임대차_전세_월세",
        article_type="tenant_protection"
    )

    # 3. ChromaDB 검색 시 필터 적용
    results = collection.query(
        query_embeddings=[embedding],
        where=filter_dict,  # 1,700개 → 28개로 축소!
        n_results=10
    )
```
7. 알아야 할 제약사항 및 성능 개선

✅ 가능한 것:
- 벡터 유사도 검색 (ChromaDB)
- 카테고리 필터링 (ChromaDB + SQLite)
- 문서 타입 필터링 (ChromaDB + SQLite)
- Boolean 메타데이터 필터 (ChromaDB)
- ID로 직접 조회 (ChromaDB + SQLite)
- **메타데이터 빠른 조회** (SQLite) ⭐ NEW
- **검색 범위 자동 축소** (SQLite → ChromaDB 필터) ⭐ NEW

❌ 불가능한 것:
- 법률 계층 구조 탐색 → 참조 필드 파싱 후 처리 (SQLite legal_references 테이블 활용 가능)

📈 성능 개선 효과 (SQLite 메타데이터 활용):
- 메타데이터 조회: ChromaDB 검색 불필요 → **즉시 응답**
- 검색 범위 축소: 1,700개 → 28개 (임차인 보호) → **98.4% 감소**
- 필터링 속도: SQLite 인덱스 활용 → **밀리초 단위 응답**

상세 가이드: SQLITE_METADATA_GUIDE.md 참조