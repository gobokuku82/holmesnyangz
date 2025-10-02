# Service Agent - Team-Based Multi-Agent Architecture

팀 기반 멀티 에이전트 시스템으로 법률, 부동산, 대출 검색 및 분석을 수행합니다.

## 📁 폴더 구조

```
service_agent/
├── core/                     # 핵심 컴포넌트 (Teams가 사용하는 파일만)
│   ├── agent_adapter.py     # AgentAdapter - 기존 에이전트 통합
│   ├── agent_registry.py    # AgentRegistry - 동적 에이전트 관리
│   └── separated_states.py  # SeparatedStates - 팀별 독립 상태
│
├── teams/                    # 팀 Supervisor
│   ├── search_team.py       # SearchTeam - 법률/부동산/대출 검색
│   ├── document_team.py     # DocumentTeam - 문서 생성 및 검토
│   └── analysis_team.py     # AnalysisTeam - 데이터 분석 및 리포트
│
├── supervisor/              # 메인 Supervisor
│   └── team_supervisor.py   # TeamBasedSupervisor - 팀 조정
│
├── tools/                   # 검색 도구
│   ├── hybrid_legal_search.py  # 하이브리드 법률 검색 (SQLite + ChromaDB)
│   └── __init__.py
│
├── tests/                   # 테스트
│   ├── test_hybrid_legal_search.py    # 하이브리드 검색 테스트
│   └── test_search_team_legal.py      # SearchTeam 통합 테스트
│
├── reports/                 # 아키텍처 문서
│   └── ARCHITECTURE_COMPLETE.md       # 완전한 아키텍처 문서
│
├── guides/                  # 참고용 파일 (사용하지 않음)
│   ├── core/               # Agent 전용 파일들
│   └── ...
│
└── models/                  # 임베딩 모델
    └── KURE_v1/            # 한국어 법률 임베딩 모델
```

## 🔧 핵심 컴포넌트

### 1. TeamBasedSupervisor
메인 조정자로 3개 팀(Search, Document, Analysis)을 오케스트레이션합니다.

**주요 기능:**
- Planning Agent를 통한 의도 분석
- 팀 간 순차/병렬 실행 전략 결정
- 팀 간 데이터 전달 및 결과 병합

**파일:** [supervisor/team_supervisor.py](supervisor/team_supervisor.py)

### 2. SearchTeam
법률, 부동산, 대출 검색을 담당합니다.

**검색 기능:**
- **법률 검색**: 하이브리드 검색 (SQLite 메타데이터 + ChromaDB 벡터 검색)
- **부동산 검색**: 시세 및 매물 정보
- **대출 검색**: 금리 및 한도 정보

**파일:** [teams/search_team.py](teams/search_team.py)

### 3. 하이브리드 법률 검색 시스템
계층적 하이브리드 구조로 법률 정보를 검색합니다.

**구조:**
```
SQLite (메타데이터)          ChromaDB (벡터 검색)
    ↓                              ↓
laws 테이블 (법령 정보)    ←→  korean_legal_documents
articles 테이블 (조항)              (임베딩 벡터)
legal_references (참조)              ↓
    ↓                          시맨틱 검색
메타데이터 필터링          ←→  관련 조항 추출
```

**검색 전략:**
1. **Metadata-First**: SQLite 필터링 → ChromaDB 벡터 검색
2. **Vector-First**: ChromaDB 벡터 검색 → SQLite 메타데이터 보강
3. **Specific Article**: SQLite 직접 조회 → ChromaDB chunk 내용 조회

**파일:** [tools/hybrid_legal_search.py](tools/hybrid_legal_search.py)

## 📊 데이터베이스 구조

### SQLite 메타데이터
**위치:** `C:\kdy\projects\holmesnayangs\bera_v001\holmesnyangz\backend\data\storage\legal_info\sqlite_db\legal_metadata.db`

**테이블:**
- `laws`: 법령 기본 정보 (28개 법령)
- `articles`: 조항 상세 정보 (1,552개 조항)
- `legal_references`: 법령 간 참조 관계

**스키마:** [../data/storage/legal_info/sqlite_db/schema.sql](../data/storage/legal_info/sqlite_db/schema.sql)

### ChromaDB 벡터 데이터베이스
**위치:** `C:\kdy\projects\holmesnayangs\bera_v001\holmesnyangz\backend\data\storage\legal_info\chroma_db`

**컬렉션:** `korean_legal_documents`

**임베딩 모델:** KURE_v1 (한국어 법률 특화)
**위치:** `C:\kdy\projects\holmesnayangs\bera_v001\holmesnyangz\backend\app\service_agent\models\KURE_v1`

## 🚀 사용 방법

### 0. 빠른 테스트 (권장)

**간단한 테스트 실행파일:**
```bash
cd backend
python app/service_agent/hn_agent_simple_test.py
```

**대화형 모드 사용법:**
```
Query > 전세금 5% 인상          # 쿼리 입력
Query > legal                  # 법률 검색만
Query > real_estate            # 부동산 검색만
Query > all                    # 전체 검색
Query > quit                   # 종료
```

**배치 모드:**
```bash
python app/service_agent/hn_agent_simple_test.py "전세금 인상" "계약 갱신"
```

**전체 에이전트 시스템 테스트 (모든 의존성 필요):**
```bash
python app/service_agent/hn_agent_query_test.py
```

### 1. SearchTeam 단독 실행 (코드)
```python
from app.service_agent.teams.search_team import SearchTeamSupervisor
from app.service.core.separated_states import StateManager

# SearchTeam 초기화
search_team = SearchTeamSupervisor()

# 공유 상태 생성
shared_state = StateManager.create_shared_state(
    query="전세금 5% 인상 제한",
    session_id="test_session"
)

# 법률 검색 실행
result = await search_team.execute(
    shared_state,
    search_scope=["legal"]
)

print(f"검색 결과: {len(result['legal_results'])}건")
```

### 2. TeamBasedSupervisor 실행
```python
from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor

# Supervisor 초기화
supervisor = TeamBasedSupervisor()

# 쿼리 실행
initial_state = {
    "query": "강남 아파트 전세 계약 관련 법률",
    "session_id": "test_session"
}

result = await supervisor.app.ainvoke(initial_state)

print(f"활성 팀: {result['active_teams']}")
print(f"팀 결과: {result['team_results']}")
```

### 3. 하이브리드 법률 검색 직접 사용
```python
from app.service_agent.tools import create_hybrid_legal_search

# 검색 시스템 초기화
legal_search = create_hybrid_legal_search()

# 하이브리드 검색 (SQLite + ChromaDB)
results = legal_search.hybrid_search(
    query="전세 보증금 반환",
    limit=10,
    is_tenant_protection=True  # 임차인 보호 조항만
)

for result in results:
    print(f"{result['law_title']} {result['article_number']}")
    print(f"관련도: {result['relevance_score']:.3f}")
    print(f"내용: {result['content'][:200]}...")
```

## 🧪 테스트

### 법률 검색 테스트
```bash
cd backend
python app/service_agent/tests/test_search_team_legal.py
```

**테스트 항목:**
1. 법률 검색 단독 테스트
2. 다중 범위 검색 (법률 + 부동산 + 대출)
3. 임차인 보호 조항 필터 테스트
4. 특정 조항 검색 테스트

### 하이브리드 검색 테스트
```bash
python app/service_agent/tests/test_hybrid_legal_search.py
```

**테스트 항목:**
1. 데이터베이스 통계 조회
2. 특정 조항 검색 (예: "주택임대차보호법 제7조")
3. 하이브리드 검색 (SQLite + ChromaDB)
4. 메타데이터 쿼리
5. 벡터 검색
6. SearchTeam 통합 테스트

## ⚙️ 의존성

### 필수 패키지
```bash
# 핵심
langgraph>=0.6.0
langchain>=0.3.0

# 법률 검색
chromadb
sentence-transformers

# DB
sqlite3 (Python 내장)

# 기타
openai
```

### 의존성 문제 해결
현재 `chromadb` 모듈이 설치되지 않은 경우 법률 검색 기능이 비활성화됩니다.

**해결 방법:**
```bash
pip install chromadb sentence-transformers
```

## 📖 아키텍처 문서

전체 아키텍처 상세 문서: [reports/ARCHITECTURE_COMPLETE.md](reports/ARCHITECTURE_COMPLETE.md)

**주요 내용:**
- Part 1: 아키텍처 개요 및 시스템 다이어그램
- Part 2: 실행 흐름 및 코드 예제
- Part 3: 핵심 컴포넌트 (AgentRegistry, AgentAdapter, SeparatedStates)
- Part 4-5: 팀 Supervisor 및 Planning Agent
- Part 6: 실제 시나리오 ("강남 아파트 시세 분석")
- Part 7-11: 기술 인사이트, 성능, 로드맵

## 🔄 팀 간 데이터 흐름

```
User Query
    ↓
TeamBasedSupervisor
    ↓
Planning Agent (의도 분석)
    ↓
SearchTeam (법률/부동산/대출 검색)
    ↓ (StateManager.merge_team_results)
AnalysisTeam (SearchTeam 결과 분석)
    ↓ (StateManager.merge_team_results)
DocumentTeam (최종 문서 생성)
    ↓
Final Response
```

**핵심 메커니즘:**
1. **SeparatedStates**: 각 팀이 독립적인 상태를 가짐 (State Pollution 방지)
2. **StateManager**: 팀 결과를 MainSupervisorState에 병합
3. **shared_context**: 팀 간 데이터 전달 채널
4. **Sequential Execution**: SearchTeam → AnalysisTeam → DocumentTeam 순차 실행

## ⚡ 성능 최적화

### 법률 검색 최적화
1. **SQLite 인덱스**: doc_type, category, enforcement_date 등
2. **ChromaDB 캐싱**: 벡터 검색 결과 캐싱
3. **Metadata-First 전략**: 빠른 SQLite 필터링 후 벡터 검색

### 팀 실행 최적화
1. **병렬 실행**: 독립적인 팀들은 동시 실행
2. **순차 실행**: 의존성 있는 팀들은 순차 실행
3. **Early Exit**: 오류 발생 시 즉시 종료

## 📝 주요 차이점 (service vs service_agent)

| 항목 | service | service_agent |
|------|---------|---------------|
| 구조 | 단일 Agent | 팀 기반 Multi-Agent |
| 상태 관리 | 공유 State | 팀별 독립 State |
| 실행 전략 | 순차 실행 | 순차/병렬 선택 |
| 법률 검색 | LegalSearchTool | 하이브리드 검색 (SQLite + ChromaDB) |
| 조정 | EnhancedBaseAgent | TeamBasedSupervisor |
| Planning | 없음 | Planning Agent (LLM 기반) |

## 🎯 향후 개선 계획

1. **법률 검색 고도화**
   - 판례 검색 추가
   - 법령 해석 LLM 통합
   - 시간대별 법령 버전 관리

2. **팀 확장**
   - 계약서 검토 팀 추가
   - 세무 상담 팀 추가

3. **성능 개선**
   - 벡터 검색 캐싱 강화
   - 병렬 실행 최적화

4. **모니터링**
   - 팀별 성능 메트릭
   - 검색 품질 평가

---

**작성일:** 2025-10-02
**버전:** 1.0.0
**작성자:** Claude Code
