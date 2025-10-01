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
2. ⚠️ 중요: doc_type 문제
DB에 doc_type 필드가 없습니다! 대신 source_file 필드에서 추출해야 합니다:
def extract_doc_type(source_file: str) -> str:
    if '시행규칙' in source_file:
        return '시행규칙'
    elif '시행령' in source_file:
        return '시행령'
    elif '법률' in source_file or '법(' in source_file:
        return '법률'
    elif '대법원규칙' in source_file:
        return '대법원규칙'
    elif '용어' in source_file:
        return '용어집'
    return '기타'
문서 타입별 분포:
법률: 666개 (39%)
시행령: 426개 (25%)
시행규칙: 268개 (16%)
대법원규칙: 248개 (15%)
용어집: 92개 (5%)
3. 주요 메타데이터 필드
항상 있는 필드:
source_file - 원본 파일명 (doc_type 추출용)
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
CHROMADB_USAGE_GUIDE.md - 상세 가이드 문서
example_chromadb_usage.py - 실행 가능한 예제 코드
이 두 파일로 LangGraph 에이전트에서 ChromaDB를 바로 사용하실 수 있습니다!
6. 빠른 시작 코드
# 1. 에이전트 초기화
from example_chromadb_usage import LegalSearchAgent
agent = LegalSearchAgent()

# 2. 기본 검색
results = agent.search("임차인 보호")

# 3. 카테고리 필터
results = agent.search(
    "전세 계약",
    category="2_임대차_전세_월세"
)

# 4. 특수 필터
results = agent.search(
    "보증금",
    is_tenant_protection=True
)

# 5. 문서 타입별 검색 (후처리)
results = agent.search_by_doc_type("취득세", "법률")
7. 알아야 할 제약사항
✅ 가능한 것:
벡터 유사도 검색
카테고리 필터링
Boolean 메타데이터 필터 (is_tenant_protection 등)
ID로 직접 조회
참조 관계 파싱
❌ 불가능한 것 (후처리 필요):
문서 타입 직접 필터링 → source_file에서 추출 후 필터링
법률 계층 구조 탐색 → 참조 필드 파싱 후 처리