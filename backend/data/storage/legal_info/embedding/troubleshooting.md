# 문제 해결 가이드 (Troubleshooting)

## 🔧 일반적인 오류 및 해결 방법

### 1. 임포트 에러

#### ModuleNotFoundError: No module named 'chromadb'
```bash
# 해결 방법
pip install chromadb sentence-transformers
```

#### ModuleNotFoundError: No module named 'sentence_transformers'
```bash
pip install sentence-transformers
```

#### 전체 패키지 설치
```bash
cd backend/data/storage/legal_info/embedding
pip install -r requirements.txt
```

---

### 2. 경로 관련 오류

#### FileNotFoundError: 청킹 파일을 찾을 수 없음
```
FileNotFoundError: [Errno 2] No such file or directory: 'backend/data/storage/legal_info/chunked'
```

**원인**: 스크립트를 잘못된 디렉토리에서 실행

**해결 방법**:
```bash
# 프로젝트 루트에서 실행
cd C:\kdy\Projects\holmesnyangz\beta_v001
python backend/data/storage/legal_info/embedding/embed_legal_documents.py --test
```

#### FileNotFoundError: 임베딩 모델을 찾을 수 없음
```
OSError: backend/models/kure_v1 not found
```

**확인 방법**:
```bash
dir backend\models\kure_v1
```

**해결 방법**:
- 모델 파일이 없는 경우: `backend/models/kure_v1` 폴더에 모델 다운로드 필요
- 경로가 다른 경우: `embed_legal_documents.py`의 `MODEL_PATH` 수정

---

### 3. ChromaDB 관련 오류

#### PermissionError: ChromaDB 파일 잠김
```
PermissionError: [WinError 32] 다른 프로세스가 파일을 사용 중입니다
```

**원인**: ChromaDB를 사용 중인 다른 프로세스 존재

**해결 방법**:
```bash
# 1. ChromaDB 사용 중인 프로세스 종료
# - LangGraph 에이전트 중지
# - Jupyter Notebook 커널 재시작
# - 터미널 세션 종료

# 2. 다시 실행
python backend/data/storage/legal_info/embedding/embed_legal_documents.py --test
```

#### ValueError: Collection already exists
```
ValueError: Collection korean_legal_documents already exists
```

**원인**: 스크립트 내부 delete_collection 실패

**해결 방법**:
```python
# 수동으로 컬렉션 삭제
import chromadb

client = chromadb.PersistentClient(path="backend/data/storage/legal_info/chroma_db")
try:
    client.delete_collection("korean_legal_documents")
    print("삭제 완료")
except:
    print("컬렉션 없음")
```

---

### 4. 메모리 관련 오류

#### RuntimeError: CUDA out of memory
```
RuntimeError: CUDA out of memory
```

**원인**: GPU 메모리 부족 (대용량 배치 처리 시)

**해결 방법 1**: batch_size 줄이기
```python
# embed_legal_documents.py 수정
batch_size = 50  # 기본값 100에서 50으로 변경
```

**해결 방법 2**: CPU 사용
```python
# embed_legal_documents.py 수정
model = SentenceTransformer(str(MODEL_PATH), device='cpu')
```

#### MemoryError: 메모리 부족
```
MemoryError: Unable to allocate array
```

**원인**: 시스템 RAM 부족

**해결 방법**:
- 다른 프로그램 종료
- batch_size를 20~30으로 감소
- 카테고리별로 분할 실행 (`--category` 옵션)

---

### 5. 인코딩 에러

#### UnicodeDecodeError: 한글 읽기 실패
```
UnicodeDecodeError: 'cp949' codec can't decode byte
```

**원인**: Windows 기본 인코딩 문제

**해결 방법**: 스크립트에서 `encoding='utf-8'` 명시 (이미 적용됨)

#### UnicodeEncodeError: 출력 에러
```
UnicodeEncodeError: 'cp949' codec can't encode character
```

**원인**: Windows 콘솔 출력 인코딩 문제

**해결 방법**:
```bash
# 콘솔 UTF-8 설정
chcp 65001
python embed_legal_documents.py --test
```

---

### 6. 실행 속도 문제

#### 임베딩이 너무 느림 (>10분)
**예상 시간**: 전체 1700개 문서 = 약 2분

**확인 사항**:
1. GPU 사용 여부 확인
```python
import torch
print(torch.cuda.is_available())  # True면 GPU 사용 가능
```

2. 모델 로딩 확인
```python
model = SentenceTransformer(MODEL_PATH)
print(model.device)  # cuda:0 또는 cpu
```

**해결 방법**:
- GPU 사용: 자동으로 감지됨
- CPU만 사용 시: batch_size 줄이기

---

### 7. 검증 실패

#### Unknown title이 여전히 많음 (100개 이상)
**예상**: 재임베딩 후 0개

**확인 방법**:
```python
# 샘플 확인
collection = chroma_client.get_collection("korean_legal_documents")
unknown = collection.get(where={"title": "Unknown"}, limit=5)
print(unknown['metadatas'])
```

**원인 분석**:
- 청킹 파일 메타데이터 자체가 누락됨
- normalize_metadata 함수 로직 오류

**해결 방법**:
1. 청킹 파일 확인
2. `normalize_metadata` 함수 디버깅
3. 로그 추가하여 어느 파일에서 Unknown 발생하는지 확인

#### doc_type 분포가 이상함
**예상 분포**:
- 법률: 35-45%
- 시행령: 20-30%
- 시행규칙: 12-20%

**확인 방법**:
```python
collection = chroma_client.get_collection("korean_legal_documents")
for doc_type in ["법률", "시행령", "시행규칙"]:
    results = collection.get(where={"doc_type": doc_type}, limit=10000)
    print(f"{doc_type}: {len(results['ids'])}개")
```

**원인**: `extract_doc_type` 함수의 패턴 매칭 오류

**해결 방법**: 파일명 패턴 확인 후 함수 수정

---

### 8. JSON 파싱 에러

#### JSONDecodeError: 청킹 파일 읽기 실패
```
json.decoder.JSONDecodeError: Expecting value
```

**원인**: 손상된 JSON 파일 또는 빈 파일

**확인 방법**:
```bash
# 파일 크기 확인
dir backend\data\storage\legal_info\chunked\*\*.json
```

**해결 방법**:
- 0바이트 파일 제거 또는 재생성
- JSON 유효성 검사 추가

---

### 9. 테스트 실패

#### hard_query_test_50.py 성공률이 낮음 (<50%)
**예상**: 재임베딩 후 80%+ 목표

**확인 사항**:
1. Unknown 문서 개수 (0개여야 함)
2. 카테고리 필터링 작동 여부
3. doc_type 필터링 작동 여부

**디버깅 방법**:
```python
# 특정 쿼리 테스트
from backend.app.service.tools.legal_search_tool import LegalSearchTool

tool = LegalSearchTool()
result = await tool.search("전세금 반환", params={"category": "2_임대차_전세_월세"})
print(result)
```

---

### 10. 스크립트 중단 시

#### KeyboardInterrupt 또는 강제 종료
**문제**:
- 기존 컬렉션은 이미 삭제됨
- 새 컬렉션은 일부만 생성됨

**해결 방법**:
```bash
# 처음부터 다시 실행
python backend/data/storage/legal_info/embedding/embed_legal_documents.py --full
```

---

## 🔍 디버깅 팁

### 1. 로그 추가
임베딩 중 문제 발생 시 로그 추가:

```python
# normalize_metadata 함수에 추가
def normalize_metadata(raw_metadata, category, source_file, chunk_id):
    try:
        # ... 기존 코드 ...
        return normalized
    except Exception as e:
        print(f"❌ 메타데이터 정규화 실패: {source_file}, {chunk_id}")
        print(f"   원본 메타데이터: {raw_metadata}")
        print(f"   에러: {e}")
        raise
```

### 2. 단계별 테스트

```python
# 1단계: 파일 읽기만
json_file = Path("chunked/2_임대차_전세_월세/주택임대차보호법(법률)(제19356호)(20230719)_chunked.json")
with open(json_file, "r", encoding="utf-8") as f:
    chunks = json.load(f)
print(f"총 {len(chunks)}개 청크")

# 2단계: 메타데이터 정규화
for chunk in chunks[:3]:  # 처음 3개만
    normalized = normalize_metadata(
        chunk["metadata"],
        "2_임대차_전세_월세",
        json_file.name,
        chunk["id"]
    )
    print(normalized)

# 3단계: 임베딩 생성
model = SentenceTransformer(MODEL_PATH)
texts = [chunk["text"] for chunk in chunks[:3]]
embeddings = model.encode(texts)
print(f"임베딩 shape: {embeddings.shape}")
```

### 3. 샘플 데이터 확인

```python
# 재임베딩 후 샘플 확인
collection = chroma_client.get_collection("korean_legal_documents")

# 첫 10개 문서
sample = collection.get(limit=10, include=["metadatas", "documents"])
for i, (doc_id, meta, text) in enumerate(zip(sample['ids'], sample['metadatas'], sample['documents']), 1):
    print(f"\n[{i}] {doc_id}")
    print(f"    title: {meta.get('title')}")
    print(f"    doc_type: {meta.get('doc_type')}")
    print(f"    text: {text[:100]}...")
```

---

## 📞 추가 도움이 필요한 경우

### 로그 파일 생성
```bash
python embed_legal_documents.py --full > embedding_log.txt 2>&1
```

### 시스템 정보 확인
```bash
python --version
pip list | findstr chromadb
pip list | findstr sentence-transformers
nvidia-smi  # GPU 확인 (있는 경우)
```

### 체크리스트
- [ ] Python 3.8 이상 설치됨
- [ ] 필수 패키지 설치됨 (chromadb, sentence-transformers)
- [ ] 청킹 파일 존재 (28개 파일)
- [ ] 임베딩 모델 존재 (backend/models/kure_v1)
- [ ] ChromaDB 디렉토리 쓰기 권한 있음
- [ ] 디스크 여유 공간 1GB 이상
- [ ] RAM 8GB 이상 여유
