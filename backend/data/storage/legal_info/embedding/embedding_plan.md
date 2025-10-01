# ChromaDB 재임베딩 실행 계획

## 📋 실행 개요

**목표**: 청킹된 법령 파일의 메타데이터를 표준화하여 ChromaDB에 재임베딩하고 Unknown 법령 문제 해결

**예상 소요 시간**: 약 5분
- 테스트 모드: 30초
- 전체 재임베딩: 2분
- 검증: 1분

**예상 문서 개수**: 1,700개 내외

## 🔍 해결할 문제점

### 1. Unknown 법령 문제 (최우선)
```
현재: 1034개 (60%) → 목표: 0개 (0%)
```

**원인 분석**:
- 법률: `law_title` 필드 사용
- 시행령: `decree_title` 필드 사용
- 시행규칙: `rule_title` 필드 사용
- 기존 임베딩 스크립트가 `law_title`만 읽어서 시행령/시행규칙이 모두 Unknown 처리됨

**해결 방법**:
```python
title = (
    raw_metadata.get("law_title") or
    raw_metadata.get("decree_title") or
    raw_metadata.get("rule_title") or
    raw_metadata.get("glossary_title") or
    "Unknown"
)
```

### 2. 카테고리 필터링 불안정
**원인**: 메타데이터에 category 필드 없음

**해결 방법**: 폴더명에서 자동 추출
```python
category = "2_임대차_전세_월세"  # 파일 경로에서 추출
```

### 3. SQL 메타데이터 보강 실패
**원인**: title이 Unknown이라 SQL 매칭 불가

**해결 방법**: title 정규화 후 자동 해결됨

## 📊 청킹 파일 현황

### 파일 분포
```
총 28개 파일, 예상 1700개 문서

카테고리별:
- 1_공통 매매_임대차: 13개 파일 (약 750개 문서)
- 2_임대차_전세_월세: 5개 파일 (약 250개 문서)
- 3_공급_및_관리_매매_분양: 7개 파일 (약 520개 문서)
- 4_기타: 3개 파일 (약 180개 문서)
```

### 문서 타입 분포 (예상)
```
법률: 39% (약 660개)
시행령: 25% (약 425개)
시행규칙: 16% (약 270개)
대법원규칙: 13% (약 220개)
용어집: 5% (약 95개)
기타: 1% (약 20개)
```

## 🎯 표준 메타데이터 스키마

### 필수 필드 (10개)
모든 문서에 반드시 포함:
1. `doc_type` - 문서 타입
2. `title` - 통합 제목
3. `number` - 통합 번호
4. `enforcement_date` - 시행일
5. `category` - 카테고리
6. `source_file` - 원본 파일명
7. `article_number` - 조항 번호
8. `article_title` - 조항 제목
9. `chunk_index` - 청크 순번
10. `is_deleted` - 삭제 여부

### 권장 필드 (4개)
있으면 포함:
- `chapter` - 장
- `chapter_title` - 장 제목
- `section` - 절
- `abbreviation` - 약칭

### 선택적 필드 (8개)
특정 조건에서만:
- `is_tenant_protection` - 임차인 보호 (true일 때만)
- `is_tax_related` - 세금 관련 (true일 때만)
- `is_delegation` - 위임 조항 (true일 때만)
- `is_penalty_related` - 벌칙 조항 (true일 때만)
- `other_law_references` - 다른 법령 참조 (있을 때만)
- `term_name` - 용어명 (용어집만)
- `term_category` - 용어 카테고리 (용어집만)
- `term_number` - 용어 번호 (용어집만)

## 🔧 정규화 처리

### 1. doc_type 자동 추출
```python
파일명 패턴 매칭:
"(법률)" → "법률"
"시행령" → "시행령"
"시행규칙" → "시행규칙"
"대법원규칙" → "대법원규칙"
"용어" → "용어집"
```

### 2. title 통합 및 정규화
```python
# 단계 1: 필드 통합
title = law_title or decree_title or rule_title or glossary_title

# 단계 2: 약칭 제거
"부동산 거래신고 등에 관한 법률 시행령 ( 약칭: 부동산거래신고법 시행령"
→ "부동산 거래신고 등에 관한 법률 시행령"
```

### 3. chunk_index 자동 부여
```python
동일 title + article_number 그룹 내에서:
주택임대차보호법 + 제3조 → [
    {"id": "article_3", "chunk_index": 0},
    {"id": "article_3_continued", "chunk_index": 1}
]
```

### 4. other_law_references 변환
```python
# ChromaDB는 배열 미지원 → JSON 문자열로 변환
["「주택법」", "「건축법」"] → '["「주택법」", "「건축법」"]'
```

## 📝 실행 단계

### STEP 1: 테스트 실행 (30초)
```bash
python backend/data/storage/legal_info/embedding/embed_legal_documents.py --test
```

**처리 내용**:
- 2_임대차_전세_월세 카테고리만 처리 (5개 파일, 약 250개 문서)
- 메타데이터 정규화 확인
- Unknown title 개수 확인

**성공 기준**:
- ✅ Unknown title: 0개
- ✅ doc_type 분포: 법률/시행령/시행규칙 모두 존재
- ✅ 모든 필수 필드 존재

### STEP 2: 결과 검증 (자동)
스크립트 내부에서 자동 실행:
```python
verify_embedding()
```

**검증 항목**:
- 전체 문서 개수
- Unknown title 개수 (0개 목표)
- doc_type 분포
- 카테고리 분포
- 샘플 메타데이터 확인

### STEP 3: 전체 재임베딩 (2분)
테스트 성공 후 실행:
```bash
python backend/data/storage/legal_info/embedding/embed_legal_documents.py --full
```

**처리 내용**:
- 4개 카테고리 전체 처리 (28개 파일, 약 1700개 문서)
- 기존 ChromaDB 컬렉션 삭제
- 새 컬렉션 생성 및 전체 재임베딩

### STEP 4: 최종 검증 (1분)
```bash
cd backend/app/service/tests
python hard_query_test_50.py
```

**확인 사항**:
- 테스트 성공률: 54% → 80%+ 목표
- 법령 매칭률: 30% → 70%+ 목표
- Unknown 관련 에러 없음

## 📊 예상 성능 개선

### 현재 상태 (Before)
```
ChromaDB 상태:
- 전체 문서: 1700개
- Unknown 법령: 1034개 (60.8%)
- 정상 법령: 666개 (39.2%)

테스트 결과 (hard_query_test_50.py):
- 성공률: 27/50 (54%)
- 법령 매칭: 15/50 (30%)
- 카테고리 매칭: 22/50 (44%)

문제점:
❌ 시행령/시행규칙이 모두 Unknown 처리
❌ SQL 메타데이터 보강 실패
❌ 카테고리 필터링 불안정
```

### 재임베딩 후 (After)
```
ChromaDB 상태:
- 전체 문서: 1700개 (동일)
- Unknown 법령: 0개 (0%) ✅
- 정상 법령: 1700개 (100%) ✅

예상 테스트 결과:
- 성공률: 40+/50 (80%+) ⬆️ +26%p
- 법령 매칭: 35+/50 (70%+) ⬆️ +40%p
- 카테고리 매칭: 45+/50 (90%+) ⬆️ +46%p

개선 사항:
✅ 모든 법령 제목 정상 추출
✅ SQL 메타데이터 보강 정상 작동
✅ 카테고리 필터링 안정화
✅ doc_type 기반 필터링 가능
```

## ⚠️ 주의사항

### 1. 백업 (선택사항)
재임베딩은 기존 컬렉션을 삭제합니다. 필요시 백업:

```bash
# Windows
xcopy backend\data\storage\legal_info\chroma_db backend\data\storage\legal_info\chroma_db_backup_20251001\ /E /I /H /Y

# Linux/Mac
cp -r backend/data/storage/legal_info/chroma_db backend/data/storage/legal_info/chroma_db_backup_20251001
```

### 2. 필수 요구사항
```bash
# 패키지 확인
pip list | findstr chromadb
pip list | findstr sentence-transformers

# 모델 존재 확인
dir backend\models\kure_v1
```

### 3. 디스크 공간
- ChromaDB: 약 500MB
- 임시 파일: 약 100MB
- 여유 공간: 1GB 이상 권장

### 4. 실행 중단 시
스크립트는 원자적(atomic) 작업이 아니므로 중단 시:
- 기존 컬렉션은 이미 삭제됨
- 새 컬렉션은 일부만 생성됨
- **해결책**: 처음부터 다시 실행 (`--full` 재실행)

## 🔍 검증 체크리스트

재임베딩 완료 후 확인:

### ChromaDB 상태
- [ ] 전체 문서 개수: 1600~1800개 사이
- [ ] Unknown title: 0개 ✅
- [ ] doc_type 분포: 법률 35-45%, 시행령 20-30%, 시행규칙 12-20%
- [ ] 카테고리 분포: 4개 카테고리 모두 존재
- [ ] 샘플 메타데이터: 필수 10개 필드 모두 존재

### 검색 기능
- [ ] 법령명 검색: "주택임대차보호법" 검색 시 결과 반환
- [ ] 카테고리 필터: category="2_임대차_전세_월세" 필터 작동
- [ ] doc_type 필터: doc_type="시행령" 필터 작동
- [ ] SQL 보강: title로 SQL 조회 성공

### 테스트 결과
- [ ] hard_query_test_50.py 성공률 80% 이상
- [ ] 법령 매칭률 70% 이상
- [ ] Unknown 관련 에러 없음

## 🚀 실행 명령어 요약

```bash
# 1. 테스트 모드 (1개 카테고리)
python backend/data/storage/legal_info/embedding/embed_legal_documents.py --test

# 2. 특정 카테고리만
python backend/data/storage/legal_info/embedding/embed_legal_documents.py --category=2_임대차_전세_월세

# 3. 전체 재임베딩
python backend/data/storage/legal_info/embedding/embed_legal_documents.py --full

# 4. 최종 검증
python backend/app/service/tests/hard_query_test_50.py
```

## 📈 성공 시나리오

```
1. 테스트 실행 (--test)
   ↓
   Unknown: 0개 확인 ✅
   ↓
2. 전체 실행 (--full)
   ↓
   1700개 문서 임베딩 완료 ✅
   ↓
3. 검증 테스트 (hard_query_test_50.py)
   ↓
   성공률 80%+ 달성 ✅
   ↓
4. 완료! 🎉
```

## 🔄 롤백 계획

예상치 못한 문제 발생 시:

### 롤백 조건
- Unknown 문서가 100개 이상
- 전체 문서 개수가 1000개 미만
- 테스트 성공률이 40% 미만

### 롤백 방법
1. 백업 복원:
```bash
# 기존 삭제
rmdir /s backend\data\storage\legal_info\chroma_db

# 백업 복원
xcopy backend\data\storage\legal_info\chroma_db_backup_20251001\ backend\data\storage\legal_info\chroma_db\ /E /I /H /Y
```

2. 재임베딩 재시도:
   - 스크립트 수정 후 다시 실행

## 📞 문제 발생 시

### 일반적인 오류

**1. ModuleNotFoundError: No module named 'chromadb'**
```bash
pip install chromadb sentence-transformers
```

**2. FileNotFoundError: 모델 경로 없음**
```bash
# 모델 경로 확인
dir backend\models\kure_v1
```

**3. PermissionError: ChromaDB 잠김**
```bash
# ChromaDB 사용 중인 프로세스 종료 후 재실행
```

**4. 임베딩 속도가 너무 느림 (>10분)**
- GPU 사용 여부 확인
- batch_size 줄이기 (100 → 50)

## 📝 완료 후 작업

재임베딩 성공 후:

1. **SQLite DB 재생성** (선택사항)
   - ChromaDB 메타데이터 기반으로 laws/articles 테이블 재구축
   - 현재는 skip 가능 (기존 SQLite DB 사용 가능)

2. **LLM 프롬프트 개선** (선택사항)
   - SearchAgent의 카테고리 선택 정확도 향상
   - doc_type 필터 활용 예시 추가

3. **모니터링**
   - 주기적으로 hard_query_test_50.py 실행
   - 성능 저하 시 재임베딩 고려
