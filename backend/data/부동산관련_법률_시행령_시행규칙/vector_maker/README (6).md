# 부동산 법률 문서 벡터DB 구축 시스템

## 📁 프로젝트 구조

```
.
├── config.py                 # 전체 설정 파일
├── document_analyzer.py      # 문서 구조 분석 모듈
├── document_preprocessor.py  # 전처리 모듈
├── document_chunker.py       # 청킹 모듈
├── vectordb_builder.py       # 임베딩 및 벡터DB 모듈
├── main_pipeline.py          # 메인 파이프라인
└── data/
    ├── raw/                  # 원본 문서
    ├── processed/            # 전처리된 문서
    ├── chunks/               # 청킹 결과
    └── vectordb/
        └── chroma/           # ChromaDB 저장소
```

## 🚀 빠른 시작

### 1. 필요 패키지 설치

```bash
pip install python-docx pandas numpy
pip install sentence-transformers chromadb
pip install tiktoken tqdm
```

### 2. 기본 사용법

```python
from main_pipeline import DocumentPipeline

# 파이프라인 초기화
pipeline = DocumentPipeline()

# 단일 문서 처리 (테스트 모드)
stats = pipeline.process_single_document(
    "path/to/document.docx",
    test_mode=True  # 임베딩 전에 중단하고 청킹 결과 확인
)

# 단일 문서 전체 처리
stats = pipeline.process_single_document(
    "path/to/document.docx",
    test_mode=False
)

# 배치 처리
doc_files = ["doc1.docx", "doc2.docx", "doc3.docx"]
results = pipeline.process_batch(doc_files)

# 검색 테스트
test_queries = [
    "공인중개사법",
    "부동산 거래 신고",
    "임대차 계약"
]
pipeline.run_retrieval_test(test_queries)
```

## 📋 단계별 처리

### 1. 문서 구조 분석

```python
from document_analyzer import DocumentAnalyzer

analyzer = DocumentAnalyzer()
structure = analyzer.analyze("document.docx")
analyzer.print_structure_summary(structure)
```

**출력 정보:**
- 문서 타입 (table, text, mixed)
- 표 개수 및 구조
- 메타데이터 (법령 번호, 날짜 등)

### 2. 전처리

```python
from document_preprocessor import DocumentPreprocessor

preprocessor = DocumentPreprocessor()
processed_data = preprocessor.preprocess("document.docx")
preprocessor.save_processed_data(processed_data, "output_path")
```

**전처리 기능:**
- 표 데이터 정규화
- 텍스트 클리닝
- 법률 참조 추출
- 구조 정보 보존

### 3. 청킹

```python
from document_chunker import DocumentChunker

chunker = DocumentChunker(
    chunk_size=500,      # 토큰 기준
    chunk_overlap=50,    # 오버랩 토큰
    min_chunk_size=100   # 최소 청크 크기
)

chunks = chunker.chunk_document(processed_data, doc_id="doc001")
chunker.print_chunking_summary(chunks)
```

**청킹 특징:**
- 의미 단위 보존
- 표 구조 보존
- 오버랩 처리
- 메타데이터 유지

### 4. 임베딩 및 벡터DB

```python
from vectordb_builder import VectorDBBuilder

vectordb = VectorDBBuilder(
    embedding_model="BAAI/bge-m3",
    collection_name="real_estate_law"
)

# 임베딩 생성
embeddings = vectordb.embed_chunks(chunks)

# 벡터DB 저장
vectordb.add_to_vectordb(chunks, embeddings)

# 검색
results = vectordb.search("부동산 거래 신고", n_results=5)
```

## 🧪 테스트 및 검증

### 청킹 테스트

```python
# test_mode=True로 실행하면 청킹 결과를 상세히 확인
pipeline.process_single_document("document.docx", test_mode=True)
```

### 임베딩 검증

```python
from vectordb_builder import EmbeddingValidator

validator = EmbeddingValidator(embeddings, chunks)
validator.print_validation_report()
```

검증 항목:
- 차원 일관성
- 유사도 분포
- 중복 임베딩

### 검색 품질 테스트

```python
# 다양한 쿼리로 검색 테스트
test_queries = [
    "특정 법률 조항",
    "복잡한 질의",
    "키워드 조합"
]
pipeline.run_retrieval_test(test_queries)
```

## ⚙️ 설정 커스터마이징

`config.py` 파일에서 다음 설정을 조정할 수 있습니다:

```python
# 청킹 설정
CHUNK_SIZE = 500        # 청크 크기 (토큰)
CHUNK_OVERLAP = 50      # 오버랩 크기
MIN_CHUNK_SIZE = 100    # 최소 청크 크기

# 임베딩 설정
EMBEDDING_MODEL = "BAAI/bge-m3"  # 임베딩 모델
EMBEDDING_DIMENSION = 1024       # 임베딩 차원

# ChromaDB 설정
COLLECTION_NAME = "real_estate_law"
DISTANCE_METRIC = "cosine"
```

## 📊 문서별 특별 처리

### 표가 많은 문서

```python
# 표 중심 처리 설정
chunker = DocumentChunker(
    chunk_size=800,  # 표를 위해 크기 증가
    chunk_overlap=0   # 표는 오버랩 불필요
)
```

### 긴 텍스트 문서

```python
# 텍스트 중심 처리 설정
chunker = DocumentChunker(
    chunk_size=400,   # 작은 청크
    chunk_overlap=100  # 더 많은 오버랩
)
```

## 🔍 고급 검색 기능

### 필터링 검색

```python
# 특정 문서 타입만 검색
results = vectordb.search(
    query="부동산 거래",
    n_results=5,
    filter_dict={"chunk_type": "table"}
)
```

### 유사도 임계값 설정

```python
results = vectordb.search(query, n_results=10)
# 유사도 0.7 이상만 필터링
filtered = [r for r in results['results'] if r['similarity'] > 0.7]
```

## 📈 성능 모니터링

```python
# 처리 통계 저장
pipeline.save_processing_stats()

# 벡터DB 통계
stats = vectordb.get_collection_stats()
print(f"Total documents: {stats['total_documents']}")
```

## 🛠️ 문제 해결

### 메모리 부족
- `chunk_size` 감소
- 배치 크기 조정
- 문서를 더 작은 단위로 분할

### 검색 품질 저하
- `chunk_overlap` 증가
- 청킹 전략 조정
- 전처리 강화

### 처리 속도
- 배치 처리 활용
- 임베딩 캐싱
- 병렬 처리 적용

## 📝 예제: 전체 워크플로우

```python
# 1. 준비
from pathlib import Path
from main_pipeline import DocumentPipeline

pipeline = DocumentPipeline()

# 2. 문서 준비
doc_dir = Path("./documents")
doc_files = list(doc_dir.glob("*.docx"))

# 3. 배치 처리 (테스트 모드)
print("Testing with first document...")
pipeline.process_single_document(
    doc_files[0],
    test_mode=True
)

# 4. 확인 후 전체 처리
input("Press Enter to continue with full processing...")
results = pipeline.process_batch(doc_files)

# 5. 검색 테스트
queries = [
    "공인중개사 자격",
    "부동산 거래신고 의무",
    "임대차 보호법"
]
pipeline.run_retrieval_test(queries)

# 6. 결과 저장
pipeline.save_processing_stats("./results/stats.json")
vectordb.export_collection("./results/collection.json")
```

## 📌 주의사항

1. **문서 형식**: 현재 `.docx` 형식만 지원
2. **표 처리**: 복잡한 병합 셀은 단순화됨
3. **메모리**: 대용량 문서는 배치로 나누어 처리
4. **임베딩 모델**: BGE-M3는 한국어 지원이 우수하지만 다른 모델로 변경 가능

## 🚦 다음 단계

1. PDF 지원 추가
2. 멀티모달 임베딩 (표 이미지)
3. 증분 업데이트 지원
4. 웹 인터페이스 구축
5. RAG 시스템 통합
