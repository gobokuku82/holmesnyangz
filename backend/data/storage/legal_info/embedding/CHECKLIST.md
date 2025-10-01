# 임베딩 실행 체크리스트

내일 작업 시작 전에 순서대로 확인하세요.

## ✅ Phase 1: 사전 준비 (5분)

### 1-1. 사전 점검 스크립트 실행
```bash
python backend/data/storage/legal_info/embedding/pre_check.py
```

**확인 사항:**
- [ ] Python 3.8+ 버전 확인
- [ ] chromadb, sentence-transformers 패키지 설치됨
- [ ] 청킹 파일 28개 존재
- [ ] 임베딩 모델 (kure_v1) 존재
- [ ] 디스크 여유 공간 1GB+

**문제 발생 시**: `troubleshooting.md` 참조

---

### 1-2. 기존 시스템 백업 (선택사항)
```bash
# ChromaDB 백업
xcopy backend\data\storage\legal_info\chroma_db backend\data\storage\legal_info\chroma_db_backup_20251002\ /E /I /H /Y

# SQLite 백업
copy backend\data\storage\legal_info\legal_metadata.db backend\data\storage\legal_info\legal_metadata_backup_20251002.db
```

- [ ] ChromaDB 백업 완료 (선택사항)
- [ ] SQLite 백업 완료 (선택사항)

---

## ✅ Phase 2: 테스트 실행 (2분)

### 2-1. 테스트 모드 실행 (1개 카테고리만)
```bash
python backend/data/storage/legal_info/embedding/embed_legal_documents.py --test
```

**예상 결과:**
```
✅ ChromaDB 재임베딩 완료!
📊 처리 통계:
   - 처리 파일: 5개
   - 임베딩 문서: 250개
   - 소요 시간: 30초

📈 카테고리별 통계:
   - 2_임대차_전세_월세: 250개

🔍 임베딩 결과 검증 중...
✅ 전체 문서 개수: 250
⚠️ Unknown title 문서: 0개 (0.0%)

📊 doc_type 분포:
   - 법률: 100개 (40.0%)
   - 시행령: 80개 (32.0%)
   - 시행규칙: 70개 (28.0%)
```

**체크리스트:**
- [ ] 테스트 실행 성공
- [ ] Unknown title: **0개** (중요!)
- [ ] doc_type 분포 정상 (법률/시행령/시행규칙 모두 존재)
- [ ] 에러 없음

**❌ 실패 시**:
- `troubleshooting.md` 참조
- 로그 확인 후 문제 해결
- 다시 테스트 실행

---

### 2-2. 검증 결과 확인
자동으로 실행되는 `verify_embedding()` 결과 확인:

- [ ] Unknown title 개수: 0개
- [ ] doc_type 분포 확인
- [ ] 카테고리 분포 확인
- [ ] 샘플 메타데이터 정상

---

## ✅ Phase 3: 전체 재임베딩 (5분)

**⚠️ 주의**: 테스트가 성공한 경우에만 진행!

### 3-1. 다른 프로세스 종료
ChromaDB 사용 중인 프로세스 모두 종료:

- [ ] LangGraph 에이전트 중지
- [ ] Jupyter Notebook 커널 재시작
- [ ] 다른 Python 스크립트 종료

---

### 3-2. 전체 재임베딩 실행
```bash
python backend/data/storage/legal_info/embedding/embed_legal_documents.py --full
```

**예상 결과:**
```
✅ ChromaDB 재임베딩 완료!
📊 처리 통계:
   - 처리 파일: 28개
   - 임베딩 문서: 1700개
   - 소요 시간: 90-120초

📈 카테고리별 통계:
   - 1_공통 매매_임대차: 750개
   - 2_임대차_전세_월세: 250개
   - 3_공급_및_관리_매매_분양: 520개
   - 4_기타: 180개

🔍 임베딩 결과 검증 중...
✅ 전체 문서 개수: 1700
⚠️ Unknown title 문서: 0개 (0.0%)

📊 doc_type 분포:
   - 법률: 666개 (39.2%)
   - 시행령: 426개 (25.1%)
   - 시행규칙: 268개 (15.8%)
   - 대법원규칙: 225개 (13.2%)
   - 용어집: 92개 (5.4%)
   - 기타: 23개 (1.4%)
```

**체크리스트:**
- [ ] 전체 실행 성공
- [ ] 처리 파일: 28개
- [ ] 임베딩 문서: 1600-1800개 사이
- [ ] Unknown title: **0개** (매우 중요!)
- [ ] doc_type 분포 정상
- [ ] 4개 카테고리 모두 존재

---

## ✅ Phase 4: 최종 검증 (3분)

### 4-1. ChromaDB 직접 확인
```python
import chromadb

client = chromadb.PersistentClient(path="backend/data/storage/legal_info/chroma_db")
collection = client.get_collection("korean_legal_documents")

# 전체 개수
print(f"전체 문서: {collection.count()}개")

# Unknown 확인
unknown = collection.get(where={"title": "Unknown"}, limit=1000)
print(f"Unknown: {len(unknown['ids'])}개")

# 샘플 확인
sample = collection.get(limit=3, include=["metadatas"])
for meta in sample['metadatas']:
    print(f"- {meta['title']} ({meta['doc_type']}) / {meta['category']}")
```

**체크리스트:**
- [ ] 전체 문서 개수: 1600-1800개
- [ ] Unknown: 0개
- [ ] 샘플 메타데이터 정상 (title, doc_type, category 모두 존재)

---

### 4-2. 검색 기능 테스트
```python
from backend.app.service.tools.legal_search_tool import LegalSearchTool
import asyncio

tool = LegalSearchTool()

# 테스트 1: 기본 검색
result = await tool.search("전세금 반환")
print(f"결과 개수: {len(result['data'])}")
print(f"첫 번째 결과: {result['data'][0]['law_title']}")

# 테스트 2: 카테고리 필터
result = await tool.search("임차인 보호", params={"category": "2_임대차_전세_월세"})
print(f"필터링 결과: {len(result['data'])}개")

# 테스트 3: doc_type 필터
result = await tool.search("공인중개사", params={"doc_type": "법률"})
print(f"법률만 검색: {len(result['data'])}개")
```

**체크리스트:**
- [ ] 기본 검색 작동
- [ ] 카테고리 필터링 작동
- [ ] doc_type 필터링 작동
- [ ] Unknown 관련 에러 없음

---

### 4-3. 50개 쿼리 테스트 실행
```bash
python backend/app/service/tests/hard_query_test_50.py
```

**예상 결과:**
```
성공률: 40+/50 (80%+)
법령 매칭률: 35+/50 (70%+)
카테고리 매칭률: 45+/50 (90%+)
```

**체크리스트:**
- [ ] 성공률: 80% 이상 (40개+)
- [ ] 법령 매칭률: 70% 이상 (35개+)
- [ ] Unknown 에러 없음

**❌ 성공률이 낮은 경우 (<60%)**:
- ChromaDB 문제가 아니라 LLM 프롬프트 문제일 수 있음
- `SearchAgent` 프롬프트 개선 필요
- 카테고리 선택 로직 개선 필요

---

## ✅ Phase 5: 완료 및 정리 (1분)

### 5-1. 최종 확인
- [ ] Unknown title: 0개 확인
- [ ] 전체 문서 개수: 정상 범위
- [ ] 검색 기능: 정상 작동
- [ ] 테스트 성공률: 목표 달성

---

### 5-2. 문서 업데이트
```markdown
# Information_for_legal_info_data.md 업데이트

## ChromaDB 상태 (2025-10-02 업데이트)
- 전체 문서: 1700개
- Unknown 문서: 0개 ✅
- 재임베딩 완료: 2025-10-02

## 표준 메타데이터 스키마 적용
- title 필드 통합 (law_title/decree_title/rule_title → title)
- doc_type 자동 추출
- category 자동 추출
- chunk_index 자동 부여
```

- [ ] 문서 업데이트 완료

---

### 5-3. 백업 정리 (선택사항)
```bash
# 재임베딩 성공 시 이전 백업 삭제
rmdir /s backend\data\storage\legal_info\chroma_db_backup_YYYYMMDD
```

- [ ] 백업 정리 완료 (선택사항)

---

## 📊 성공 기준 요약

| 항목 | 현재 (Before) | 목표 (After) | 확인 |
|-----|--------------|-------------|-----|
| Unknown 문서 | 1034개 (60%) | **0개 (0%)** | [ ] |
| 전체 문서 | 1700개 | 1700개 | [ ] |
| 테스트 성공률 | 54% | **80%+** | [ ] |
| 법령 매칭률 | 30% | **70%+** | [ ] |
| 카테고리 필터 | 불안정 | **정상** | [ ] |
| doc_type 필터 | 없음 | **정상** | [ ] |

---

## 🚨 실패 시 롤백 계획

### 롤백 조건
- Unknown 문서가 100개 이상
- 전체 문서가 1000개 미만
- 테스트 성공률이 40% 미만

### 롤백 방법
```bash
# 1. 기존 ChromaDB 삭제
rmdir /s backend\data\storage\legal_info\chroma_db

# 2. 백업 복원
xcopy backend\data\storage\legal_info\chroma_db_backup_20251002\ backend\data\storage\legal_info\chroma_db\ /E /I /H /Y
```

---

## 📝 완료 후 작업

재임베딩 완료 및 검증 성공 후:

1. **이 체크리스트 완료 표시**
   - 모든 [ ]를 [x]로 변경

2. **결과 기록**
   - 최종 문서 개수:
   - Unknown 개수:
   - 테스트 성공률:
   - 소요 시간:

3. **다음 단계**
   - [ ] SQLite DB 재생성 (선택사항)
   - [ ] SearchAgent 프롬프트 개선 (선택사항)
   - [ ] 성능 모니터링 계획 수립
