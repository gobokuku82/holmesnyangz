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
⚠️ 주의: 이 필드들은 해당하는 문서에만 존재하며, 대부분의 문서에는 필드 자체가 없음 (absent)
is_tenant_protection (28개) - 임차인 보호 조항만 True
is_tax_related (7개) - 세금 관련 용어만 True
is_delegation (156개) - 위임 조항만 True
is_penalty_related (1개) - 벌칙 조항만 True
is_deleted (679개 False, 16개 True) - 삭제된 조항 표시

필터 사용 예시:
- {"is_tenant_protection": True} → 28개 문서만 검색
- {"is_deleted": False} → 삭제되지 않은 679개 문서만 검색
- 필터 없음 → 전체 1700개 문서 검색 (권장)
4. 카테고리 정보
"1_공통 매매_임대차"          # 공통 거래
"2_임대차_전세_월세"          # 임대차
"3_공급_및_관리_매매_분양"    # 공급/관리
"4_기타"                      # 기타
5. 사용 파일
생성된 파일:
CHROMADB_USAGE_GUIDE.md - ChromaDB 사용 가이드
SQLITE_METADATA_GUIDE.md - SQLite 메타데이터 상세 가이드
schema.sql - SQLite 테이블 스키마 정의 (laws, articles, legal_references)
legal_query_helper.py - SQLite 쿼리 헬퍼 클래스 (필터 생성용)

주요 코드:
backend/app/service/tools/legal_search_tool.py - 법률 검색 도구 (ChromaDB + SQLite 통합)
6. 빠른 시작 코드

## ⭐ 권장: LegalSearchTool 사용 (현재 시스템)
```python
from backend.app.service.tools.legal_search_tool import LegalSearchTool

# 도구 초기화 (자동으로 ChromaDB + SQLite 연결)
tool = LegalSearchTool()

# 기본 검색 (필터 없음)
results = await tool.search("전세금 반환 보증")
print(results['data'])  # 10개 결과 리턴

# 문서 타입 필터
results = await tool.search("공인중개사법", params={"doc_type": "법률"})

# 카테고리 필터
results = await tool.search("임차인 보호", params={"category": "2_임대차_전세_월세"})

# Boolean 필터 (해당 필드가 있는 문서만)
results = await tool.search("보증금", params={"is_deleted": False})
```

## 또는: ChromaDB 직접 사용
```python
import chromadb
from sentence_transformers import SentenceTransformer

chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_collection("korean_legal_documents")
model = SentenceTransformer("./kure_v1")

embedding = model.encode("검색 쿼리").tolist()
results = collection.query(
    query_embeddings=[embedding],
    where={"doc_type": "법률"},  # 선택적
    n_results=10
)
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