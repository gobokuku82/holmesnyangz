📋 최종 요약: LangGraph 에이전트에서 법률 데이터 사용 시 필수 정보
1. 핵심 정보
# 데이터베이스 경로
CHROMA_PATH = r".\backend\data\storage\legal_info\chroma_db"
SQLITE_PATH = r".\backend\data\storage\legal_info\sqlite_db\legal_metadata.db"
SCHEMA_PATH = r".\backend\data\storage\legal_info\sqlite_db\schema.sql"

# ChromaDB 정보
COLLECTION = "korean_legal_documents"
TOTAL_DOCS = 1700  # ChromaDB chunks

# SQLite 정보
TOTAL_LAWS = 28     # 법령 수
TOTAL_ARTICLES = 1552  # 조항 수

# 임베딩 모델
MODEL_PATH = r".\backend\app\service\models\kure_v1"
EMBEDDING_DIM = 1024

# 리랭커 모델 (선택)
RERANKER_PATH = r".\backend\app\service\models\bge-reranker-v2-m3-ko"
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
SQLITE_METADATA_GUIDE.md - SQLite 메타데이터 상세 가이드
schema.sql - SQLite 테이블 스키마 정의 (laws, articles, legal_references) ⭐ NEW
legal_query_helper.py - SQLite 쿼리 헬퍼 클래스
unified_legal_agent.py - 통합 에이전트 (SQLite + ChromaDB) ⭐ NEW
6. 빠른 시작 코드

## ⭐ 권장: 통합 에이전트 (SQLite + ChromaDB)
```python
from unified_legal_agent import UnifiedLegalAgent

# 에이전트 초기화
agent = UnifiedLegalAgent()

# 메타데이터 질문 (SQLite만 사용 - 즉시 응답)
result = agent.answer_question("공인중개사법은 몇 조까지인가요?")
print(result['answer'])  # "공인중개사법은 총 70개 조항이 있으며..."
print(result['source'])  # "sqlite"

# 내용 검색 (SQLite 필터 + ChromaDB 벡터 검색)
result = agent.answer_question("임대차 계약 시 보증금 관련 규정")
print(result['answer'])  # 검색 결과 포맷팅된 답변
print(result['source'])  # "chromadb"
print(result['filter_used'])  # ChromaDB 필터 확인
```

## 또는: ChromaDB 직접 사용
```python
from example_chromadb_usage import LegalSearchAgent

agent = LegalSearchAgent()
results = agent.search("임차인 보호", category="2_임대차_전세_월세")
```
7. 알아야 할 제약사항
✅ 가능한 것:
벡터 유사도 검색
카테고리 필터링
문서 타입 필터링 (doc_type 필드)
Boolean 메타데이터 필터 (is_tenant_protection 등)
ID로 직접 조회
참조 관계 파싱
❌ 불가능한 것 (후처리 필요):
법률 계층 구조 탐색 → 참조 필드 파싱 후 처리