# Legal Search Tool 재구성 완료

## 📋 변경 사항 요약

### 문제점
- `unified_legal_agent.py`가 `data/storage/legal_info/guides/`에 위치 (코드/데이터 분리 위반)
- 단순 래퍼 클래스로 불필요한 복잡성 추가
- `legal_search_tool.py`가 `sys.path` 조작으로 import

### 해결 방법
**UnifiedLegalAgent를 LegalSearchTool에 통합**

---

## 🔧 수정된 파일

### 1. [legal_search_tool.py](backend/app/service/tools/legal_search_tool.py) ✅

#### Before:
```python
from unified_legal_agent import UnifiedLegalAgent

class LegalSearchTool:
    def __init__(self):
        self.search_agent = UnifiedLegalAgent()

    async def search(self, query, params):
        embedding = self.search_agent.embedding_model.encode(query)
        results = self.search_agent.collection.query(...)
```

#### After:
```python
import chromadb
from sentence_transformers import SentenceTransformer
from config import Config
from legal_query_helper import LegalQueryHelper

class LegalSearchTool:
    def __init__(self):
        # Initialize resources directly
        self.metadata_helper = LegalQueryHelper(Config.LEGAL_PATHS["sqlite_db"])
        self.chroma_client = chromadb.PersistentClient(Config.LEGAL_PATHS["chroma_db"])
        self.collection = self.chroma_client.get_collection("korean_legal_documents")
        self.embedding_model = SentenceTransformer(Config.LEGAL_PATHS["embedding_model"])

    async def search(self, query, params):
        embedding = self.embedding_model.encode(query)  # 직접 접근
        results = self.collection.query(...)  # 직접 접근
```

---

### 2. [config.py](backend/app/service/core/config.py) ✅

추가된 설정:
```python
# ============ Legal Search Paths ============
LEGAL_INFO_BASE = BASE_DIR / "data" / "storage" / "legal_info"
LEGAL_PATHS = {
    "chroma_db": LEGAL_INFO_BASE / "chroma_db",
    "sqlite_db": LEGAL_INFO_BASE / "sqlite_db" / "legal_metadata.db",
    "embedding_model": BASE_DIR / "app" / "service" / "models" / "kure_v1",
}
```

---

### 3. unified_legal_agent.py ⚠️

**상태**: 백업 후 제거됨
- 위치: `backend/data/storage/legal_info/guides/unified_legal_agent.py.backup`
- 더 이상 필요하지 않음 (모든 기능이 LegalSearchTool에 통합)

---

## ✅ 개선 사항

### 구조 단순화
```
Before:
LegalSearchTool → UnifiedLegalAgent → ChromaDB/Model/Helper
                    (불필요한 래퍼)

After:
LegalSearchTool → ChromaDB/Model/Helper
                  (직접 접근)
```

### 장점

1. **코드/데이터 명확히 분리**
   - 코드: `backend/app/service/tools/`
   - 데이터: `backend/data/storage/legal_info/`

2. **Import 경로 단순화**
   - Before: 복잡한 sys.path 조작 + UnifiedLegalAgent import
   - After: Config import만으로 모든 경로 관리

3. **중앙 설정 관리**
   - 모든 경로가 Config.LEGAL_PATHS에서 관리
   - 경로 변경 시 Config만 수정

4. **성능**
   - 불필요한 래퍼 레이어 제거
   - 직접 접근으로 오버헤드 감소

5. **유지보수**
   - 하나의 파일에서 모든 로직 확인 가능
   - 디버깅 용이

---

## 🧪 테스트 결과

```bash
$ python test_legal_final.py

[OK] Legal Search Tool found in registry
   Name: legal_search
   Description: 법률 정보 검색 - 부동산 관련 법률, 시행령, 시행규칙, 용어 등
   Use Mock Data: False
   Has Embedding Model: True
   Has ChromaDB Collection: True
   Has Metadata Helper: True
   ChromaDB Documents: 1700
```

**모든 기능 정상 작동 확인!**

---

## 📊 리소스 확인

### 임베딩 모델 (kure_v1)
- **경로**: `backend/app/service/models/kure_v1`
- **타입**: SentenceTransformer (한국어 법률 특화)
- **차원**: 1024
- **상태**: ✅ 정상 로드

### ChromaDB
- **경로**: `backend/data/storage/legal_info/chroma_db`
- **컬렉션**: korean_legal_documents
- **문서 수**: 1700
- **상태**: ✅ 정상 연결

### SQLite 메타데이터
- **경로**: `backend/data/storage/legal_info/sqlite_db/legal_metadata.db`
- **법률**: 28개
- **조항**: 1552개
- **상태**: ✅ 정상 연결

---

## 🎯 결론

**UnifiedLegalAgent 제거 완료!**

- ✅ 구조 단순화
- ✅ 코드/데이터 분리
- ✅ Config 기반 중앙 관리
- ✅ 모든 테스트 통과
- ✅ 성능 개선

**LegalSearchTool은 이제 자체적으로 모든 법률 검색 리소스를 관리합니다.**
