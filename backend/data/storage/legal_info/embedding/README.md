# ChromaDB 재임베딩 가이드

## 📋 목적

청킹된 법령 파일들의 메타데이터를 표준화하여 ChromaDB에 재임베딩

## 🔍 현재 문제점

### 1. Unknown 법령 문제
- **1034개 문서**(60%)가 `law_title='Unknown'` 상태
- SQL 메타데이터 보강 불가능
- 법령명 기반 검색 실패

### 2. 메타데이터 필드 불일치
청킹 파일마다 다른 필드명 사용:

| 문서 타입 | 제목 필드 | 번호 필드 |
|---------|---------|---------|
| 법률 | `law_title` | `law_number` |
| 시행령 | `decree_title` | `decree_number` |
| 시행규칙 | `rule_title` | `rule_number` |
| 용어집 | `glossary_title` | - |

### 3. 선택적 필드 누락
- `chapter`, `chapter_title`, `other_law_references`, `is_delegation` 등
- 일부 파일에만 존재 → 검색 필터링 불일치

## 📊 청킹 파일 분석 결과

### 전체 구조
```
backend/data/storage/legal_info/chunked/
├── 1_공통 매매_임대차/           # 13개 파일
├── 2_임대차_전세_월세/           # 5개 파일
├── 3_공급_및_관리_매매_분양/      # 7개 파일
└── 4_기타/                      # 7개 파일
    총 28개 JSON 파일
```

### 메타데이터 필드 분석

#### 필수 필드 (모든 파일에 존재)
- `article_number`: 조항 번호 (제1조, 제2조의2 등)
- `article_title`: 조항 제목
- `is_deleted`: 삭제 여부 (boolean)

#### 문서 타입별 제목/번호 필드
```python
# 법률
"law_title": "주택임대차보호법"
"law_number": "제19356호"

# 시행령
"decree_title": "부동산 거래신고 등에 관한 법률 시행령"
"decree_number": "제35485호"

# 시행규칙
"rule_title": "부동산 거래신고 등에 관한 법률 시행규칙"
"rule_number": "제1294호"

# 용어집
"glossary_title": "부동산 용어 95가지"
"term_name": "매도"
"term_number": 1
```

#### 선택적 필드 (일부 파일에만 존재)
- `chapter`: 장 (제1장, 제2장)
- `chapter_title`: 장 제목 (총칙, 벌칙)
- `section`: 절
- `abbreviation`: 약칭
- `other_law_references`: 다른 법령 참조 목록 (배열)
- `is_tenant_protection`: 임차인 보호 (boolean)
- `is_delegation`: 위임 조항 (boolean)

## 🎯 표준화된 메타데이터 스키마

### 필수 필드 (Required)
모든 문서에 반드시 포함:

```python
{
    "doc_type": str,           # 법률/시행령/시행규칙/대법원규칙/용어집/기타
    "title": str,              # 통합 제목 (law_title/decree_title/rule_title 통합)
    "number": str,             # 통합 번호 (law_number/decree_number/rule_number 통합)
    "enforcement_date": str,   # 시행일 (YYYY. MM. DD.)
    "category": str,           # 폴더명 기반 카테고리
    "source_file": str,        # 원본 청킹 파일명
    "article_number": str,     # 조항 번호
    "article_title": str,      # 조항 제목
    "chunk_index": int,        # 동일 조항 내 청크 순번
    "is_deleted": bool,        # 삭제 여부
}
```

### 권장 필드 (Recommended)
있으면 포함:

```python
{
    "chapter": str,            # 장
    "chapter_title": str,      # 장 제목
    "section": str,            # 절
    "abbreviation": str,       # 약칭
}
```

### 선택적 필드 (Optional)
특정 조건에서만 포함:

```python
{
    # Boolean 특수 조항 (true일 때만 포함)
    "is_tenant_protection": bool,
    "is_tax_related": bool,
    "is_delegation": bool,
    "is_penalty_related": bool,

    # 참조 관계 (있을 때만)
    "other_law_references": str,  # JSON 문자열로 저장

    # 용어집 전용
    "term_name": str,
    "term_category": str,
    "term_number": int,
}
```

## 🔧 정규화 규칙

### 1. doc_type 추출
파일명에서 자동 추출:

```python
"공인중개사법(법률)(제19841호).json" → "법률"
"부동산거래신고법 시행령(대통령령).json" → "시행령"
"부동산거래신고법 시행규칙(국토교통부령).json" → "시행규칙"
"부동산등기규칙(대법원규칙).json" → "대법원규칙"
"부동산_용어_95가지_chunked.json" → "용어집"
```

### 2. title 통합
우선순위대로 선택:

```python
title = (
    raw_metadata.get("law_title") or
    raw_metadata.get("decree_title") or
    raw_metadata.get("rule_title") or
    raw_metadata.get("glossary_title") or
    "Unknown"
)

# 약칭 제거
if " ( 약칭:" in title:
    title = title.split(" ( 약칭:")[0].strip()
```

### 3. category 추출
폴더명에서 자동 추출:

```
chunked/1_공통 매매_임대차/파일.json → category: "1_공통 매매_임대차"
```

### 4. chunk_index 부여
동일한 `title + article_number`를 가진 문서들에게 순번 부여:

```python
주택임대차보호법 제3조 (긴 조문이 3개 청크로 분할된 경우)
→ chunk_index: 0, 1, 2
```

### 5. other_law_references 처리
배열을 JSON 문자열로 변환 (ChromaDB는 배열 메타데이터 미지원):

```python
["「주택법」", "「건축법」"] → '["「주택법」", "「건축법」"]'
```

## 📁 파일 설명

### `embed_legal_documents.py`
ChromaDB 재임베딩 메인 스크립트

**주요 함수:**
- `extract_doc_type()`: 파일명에서 문서 타입 추출
- `normalize_metadata()`: 메타데이터 정규화
- `assign_chunk_indices()`: chunk_index 부여
- `embed_documents()`: 임베딩 실행
- `verify_embedding()`: 결과 검증

**실행 방법:**
```bash
# 테스트 (2_임대차_전세_월세만)
python backend/data/storage/legal_info/embedding/embed_legal_documents.py --test

# 전체 재임베딩
python backend/data/storage/legal_info/embedding/embed_legal_documents.py --full

# 특정 카테고리만
python backend/data/storage/legal_info/embedding/embed_legal_documents.py --category=2_임대차_전세_월세
```

### `metadata_schema.json`
표준 메타데이터 스키마 정의 (참조용)

### `embedding_plan.md`
상세 실행 계획 및 예상 효과

## ⚠️ 주의사항

### 1. 기존 ChromaDB 백업
재임베딩 전에 반드시 백업:

```bash
# Windows
xcopy backend\data\storage\legal_info\chroma_db backend\data\storage\legal_info\chroma_db_backup_YYYYMMDD\ /E /I /H /Y

# Linux/Mac
cp -r backend/data/storage/legal_info/chroma_db backend/data/storage/legal_info/chroma_db_backup_YYYYMMDD
```

### 2. 필수 패키지 확인
```bash
pip install chromadb sentence-transformers
```

### 3. 모델 경로 확인
`backend/models/kure_v1` 폴더 존재 여부 확인

### 4. 예상 소요 시간
- 테스트 모드 (1개 카테고리): ~30초
- 전체 재임베딩 (28개 파일): ~2분

## 📊 예상 효과

### Before (현재)
- Unknown 법령: **1034개 (60%)**
- 테스트 성공률: **54%**
- 법령 매칭률: **30%**
- 카테고리 필터링: 불안정

### After (재임베딩 후)
- Unknown 법령: **0개 (0%)** ✅
- 테스트 성공률: **80%+** (예상)
- 법령 매칭률: **70%+** (예상)
- 카테고리 필터링: 정상 작동 ✅
- SQL 메타데이터 보강: 정상 작동 ✅

## 🚀 실행 순서

1. **백업 생성** (선택사항)
2. **테스트 실행** (`--test`)
3. **결과 검증** (Unknown 개수 확인)
4. **전체 실행** (`--full`)
5. **최종 검증** (`hard_query_test_50.py` 실행)

## 📝 검증 체크리스트

재임베딩 후 확인할 사항:

- [ ] 전체 문서 개수: 1700개 내외
- [ ] Unknown title: 0개
- [ ] doc_type 분포: 법률 39%, 시행령 25%, 시행규칙 16%, 대법원규칙 13%, 용어집 5%, 기타 1%
- [ ] 카테고리 분포: 4개 카테고리 모두 존재
- [ ] 샘플 메타데이터: title, doc_type, category, chunk_index 모두 정상

## 🔗 관련 파일

- 청킹 파일: `backend/data/storage/legal_info/chunked/`
- ChromaDB: `backend/data/storage/legal_info/chroma_db/`
- 임베딩 모델: `backend/models/kure_v1/`
- 테스트 스크립트: `backend/app/service/tests/hard_query_test_50.py`
