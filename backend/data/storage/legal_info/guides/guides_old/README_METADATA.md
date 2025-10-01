# 벡터 DB용 메타데이터 인덱스 시스템

## 개요
이 문서는 부동산 관련 법률 문서들의 벡터 데이터베이스 색인을 위한 메타데이터 시스템을 설명합니다.

## 파일 구조

### 1. metadata_index.json
**목적**: 모든 문서의 통합 메타데이터 인덱스

**구조**:
```json
{
  "version": "1.0",
  "created_date": "YYYY-MM-DD HH:MM:SS",
  "total_documents": 28,
  "total_chunks": 1700,
  "categories": {
    "카테고리명": {
      "name": "표시명",
      "description": "설명",
      "documents": 문서수,
      "chunks": 청크수
    }
  },
  "documents": [
    {
      "file_name": "파일명.json",
      "doc_type": "법률|시행령|시행규칙|용어집",
      "doc_id": "고유ID",
      "title": "문서제목",
      "chunks": 청크수,
      "category": "카테고리",
      "enforcement_date": "시행일",
      "hierarchy": {
        "chapters": 장수,
        "sections": 절수,
        "articles": 조수
      }
    }
  ]
}
```

### 2. document_registry.json
**목적**: 문서 간 관계 매핑

**주요 내용**:
- 법률-시행령-시행규칙 계층 관계
- 관련 문서 연결 정보
- 최신 개정 이력

### 3. chunk_statistics.json
**목적**: 청킹 통계 및 메타데이터 사용 분석

**주요 통계**:
- 카테고리별 문서/청크 수
- 문서 유형별 통계
- 메타데이터 필드 사용 빈도 (67개 필드)
- 참조 관계 통계 (총 878개 참조)
- 특수 플래그 사용 통계

### 4. category_taxonomy.json
**목적**: 카테고리 분류 체계 정의

**카테고리**:
1. **공통 매매·임대차** (9개 문서, 621 청크)
   - 부동산 등기, 공인중개사, 거래신고

2. **임대차·전세·월세** (5개 문서, 301 청크)
   - 주택임대차보호법, 민간임대주택 특별법

3. **공급 및 관리·매매·분양** (8개 문서, 518 청크)
   - 주택법, 공동주택관리법, 건축물 분양

4. **기타** (6개 문서, 260 청크)
   - 가격공시, 분양가격, 층간소음, 용어집

### 5. search_config.yaml
**목적**: 벡터 DB 검색 설정

**주요 설정**:
- 임베딩 모델: multilingual-e5-large
- 거리 메트릭: cosine
- 필터링 가능 필드 정의
- 쿼리 확장 설정 (동의어 사전)
- 리랭킹 모델 설정

## 메타데이터 필드

### 핵심 필드 (모든 문서)
- `article_number`: 조항 번호
- `article_title`: 조항 제목
- `enforcement_date`: 시행일
- `is_deleted`: 삭제 여부

### 문서 유형별 필드
- **법률**: `law_title`, `law_number`
- **시행령**: `decree_title`, `decree_number`
- **시행규칙**: `rule_title`, `rule_number`
- **용어집**: `glossary_title`, `term_name`, `term_category`

### 구조 필드
- `chapter`: 장 정보
- `section`: 절 정보
- `abbreviation`: 약칭

### 참조 필드
- `law_references`: 타 법률 참조
- `decree_references`: 시행령 참조
- `form_references`: 서식 참조

### 특수 플래그
- `is_tenant_protection`: 임차인 보호 조항
- `is_delegation`: 위임 조항
- `is_tax_related`: 세금 관련
- `is_price_disclosure_related`: 가격공시 관련

## 통계 요약

| 항목 | 값 |
|-----|-----|
| 총 파일 수 | 28개 |
| 총 청크 수 | 1,700개 |
| 카테고리 수 | 4개 |
| 문서 유형 | 4종 |
| 메타데이터 필드 | 67개 |
| 참조 관계 | 878개 |
| 평균 청크/문서 | 60.7개 |

## 사용 방법

### 1. 메타데이터 로드
```python
import json

# 메타데이터 인덱스 로드
with open('metadata_index.json', 'r', encoding='utf-8') as f:
    metadata = json.load(f)

# 특정 카테고리의 문서 필터링
category_docs = [
    doc for doc in metadata['documents']
    if doc['category'] == '1_공통 매매_임대차'
]
```

### 2. 벡터 DB 인덱싱
```python
import yaml

# 검색 설정 로드
with open('search_config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 필터링 가능 필드 확인
filterable = [
    field for field, settings in config['indexing']['metadata_fields'].items()
    if settings.get('filterable')
]
```

### 3. 문서 관계 조회
```python
# 문서 레지스트리 로드
with open('document_registry.json', 'r', encoding='utf-8') as f:
    registry = json.load(f)

# 관련 문서 찾기
for relation in registry['document_relationships']:
    if '공인중개사법' in relation['base_document']:
        print(relation['related_documents'])
```

## 업데이트 방법

메타데이터 재생성:
```bash
cd C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info\chunked
python generate_metadata_index.py
```

## 주의사항

1. 모든 JSON 파일은 UTF-8 인코딩 사용
2. 파일명에 특수문자 포함 가능 (공백, 괄호 등)
3. 용어집은 다른 법률 문서와 구조가 다름
4. 시행일은 미래 날짜 포함 (최신 2025.08.01)

## 문의

메타데이터 구조나 사용 방법에 대한 문의는 프로젝트 관리자에게 연락하세요.