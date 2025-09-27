# LangGraph 0.6.7 부동산 챗봇 시스템 아키텍처 분석 보고서

**생성일**: 2025-09-27
**프로젝트**: Holmes Nyangs - Real Estate Chatbot (BERA v0.01)
**버전**: LangGraph 0.6.7
**분석 범위**: Core Configuration & Supervisor Orchestrator

---

## 1. 시스템 개요

### 1.1 아키텍처 구조
```
holmesnyangz/backend/service/
├── core/                    # 핵심 설정 레이어
│   ├── config.py           # 시스템 정적 설정
│   ├── context.py          # 런타임 컨텍스트 정의
│   ├── states.py           # 워크플로우 상태 정의
│   ├── base_agent.py       # 에이전트 베이스 클래스
│   └── checkpointer.py     # 체크포인트 유틸리티
│
└── supervisor/              # 슈퍼바이저 오케스트레이터
    ├── supervisor.py        # 메인 슈퍼바이저
    ├── intent_analyzer.py   # 의도 분석 노드
    ├── plan_builder.py      # 계획 수립 노드
    ├── execution_coordinator.py  # 에이전트 실행 조정
    ├── result_evaluator.py  # 결과 평가 노드
    └── prompts.py          # LLM 프롬프트 템플릿
```

### 1.2 워크플로우 개요
```
START → Intent Analysis → Plan Building → Agent Execution → Result Evaluation → END
                                               ↑                    ↓
                                               └──── Retry Logic ───┘
```

---

## 2. Core 레이어 상세 분석

### 2.1 Config (config.py)

#### 클래스 구조
**Class: `Config`** (Line 15-138)

정적 시스템 설정을 관리하는 클래스로, 런타임 중 변경되지 않는 설정값 제공.

#### 주요 설정 항목

##### 2.1.1 시스템 경로 (Line 22-29)
```python
BASE_DIR: Path           # 프로젝트 루트
DB_DIR: Path            # 데이터베이스 디렉토리
CHECKPOINT_DIR: Path    # 체크포인트 저장소
LOG_DIR: Path           # 로그 디렉토리
```

##### 2.1.2 데이터베이스 경로 (Line 32-37)
```python
DATABASES: Dict[str, Path]
  - real_estate_listings    # 매물 목록 DB
  - regional_info           # 지역 통계 DB
  - user_profiles           # 사용자 프로필 DB
  - user_data              # 사용자 데이터 DB
```

##### 2.1.3 모델 설정 (Line 40-48)
```python
DEFAULT_MODELS: Dict[str, str]
  - intent: "gpt-4o-mini"      # 빠른 의도 분석
  - planning: "gpt-4o"          # 정확한 계획 수립

DEFAULT_MODEL_PARAMS: Dict[str, Dict]
  - intent: {temperature: 0.3, max_tokens: 500}
  - planning: {temperature: 0.3, max_tokens: 2000}
```

##### 2.1.4 타임아웃 설정 (Line 51-54)
```python
TIMEOUTS: Dict[str, int]
  - agent: 30    # 개별 에이전트 타임아웃 (초)
  - llm: 20      # LLM 호출 타임아웃 (초)
```

##### 2.1.5 시스템 제한 (Line 57-62)
```python
LIMITS: Dict[str, int]
  - max_recursion: 25         # 최대 재귀 깊이
  - max_retries: 3            # 최대 재시도 횟수
  - max_message_length: 10000 # 최대 메시지 길이
  - max_sql_results: 1000     # 최대 SQL 결과 수
```

##### 2.1.6 실행 설정 (Line 65-67)
```python
EXECUTION: Dict[str, bool]
  - enable_checkpointing: True  # 체크포인트 활성화
```

##### 2.1.7 로깅 설정 (Line 70-77)
```python
LOGGING: Dict[str, Any]
  - level: "INFO"
  - format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  - date_format: "%Y-%m-%d %H:%M:%S"
  - file_rotation: "daily"
  - max_log_size: "100MB"
  - backup_count: 7
```

##### 2.1.8 기능 플래그 (Line 80-82)
```python
FEATURES: Dict[str, bool]
  - enable_llm_planning: True   # LLM 계획 수립 활성화
```

#### 헬퍼 메서드

**1. `get_database_path(db_name: str) -> Path`** (Line 87-89)
- 데이터베이스 이름으로 경로 반환
- 등록되지 않은 DB는 기본 경로 반환

**2. `get_checkpoint_path(agent_name: str, session_id: str) -> Path`** (Line 92-96)
- 에이전트별 세션별 체크포인트 경로 생성
- 디렉토리 자동 생성

**3. `get_model_config(model_type: str) -> Dict[str, Any]`** (Line 99-104)
- 모델 타입에 따른 설정 반환
- 모델명 + 파라미터 통합 반환

**4. `validate() -> bool`** (Line 107-127)
- 설정 유효성 검증
- 경로 존재 여부 확인
- 이슈 리스트 반환

**5. `to_dict() -> Dict[str, Any]`** (Line 130-138)
- 설정을 딕셔너리로 내보내기
- 직렬화 가능한 형태로 변환

---

### 2.2 Context (context.py)

#### 컨텍스트 타입 정의

##### 2.2.1 **TypedDict: `AgentContext`** (Line 14-38)
런타임 메타데이터 전달용 컨텍스트 (READ-ONLY)

**필수 필드**:
```python
user_id: str           # 사용자 식별자
session_id: str        # 세션 식별자
```

**선택적 런타임 정보**:
```python
request_id: Optional[str]        # 요청 고유 ID
timestamp: Optional[str]         # 요청 타임스탬프
original_query: Optional[str]    # 원본 사용자 입력
```

**인증 정보**:
```python
api_keys: Optional[Dict[str, str]]  # 서비스 API 키
```

**사용자 설정**:
```python
language: Optional[str]  # 사용자 언어 (ko, en 등)
```

**실행 제어**:
```python
debug_mode: Optional[bool]  # 디버그 로깅 활성화
```

##### 2.2.2 **TypedDict: `SubgraphContext`** (Line 40-63)
서브그래프용 필터링된 컨텍스트

**부모로부터 상속** (필수):
```python
user_id: str
session_id: str
```

**부모로부터 상속** (선택):
```python
request_id: Optional[str]
language: Optional[str]
debug_mode: Optional[bool]
```

**서브그래프 식별**:
```python
parent_agent: str      # 부모 에이전트 이름
subgraph_name: str     # 현재 서브그래프 이름
```

**서브그래프 파라미터**:
```python
suggested_tools: Optional[List[str]]        # 툴 힌트
analysis_depth: Optional[str]               # 분석 깊이 (shallow/normal/deep)
db_paths: Optional[Dict[str, str]]         # 데이터베이스 경로
```

#### 컨텍스트 팩토리 함수

**1. `create_agent_context(user_id, session_id, **kwargs) -> Dict[str, Any]`** (Line 67-100)
- AgentContext 생성
- 필수 필드 + 선택적 필드 구성
- None 값 제거로 깔끔한 컨텍스트 생성
- request_id 자동 생성 (uuid 기반)
- timestamp 자동 생성 (ISO 형식)
- 기본 언어: "ko"

**2. `merge_with_config_defaults(context, config) -> Dict[str, Any]`** (Line 103-118)
- 컨텍스트와 Config 기본값 병합
- 컨텍스트 값이 우선순위

**3. `create_subgraph_context(parent_context, parent_agent, subgraph_name, **kwargs) -> Dict[str, Any]`** (Line 121-160)
- 서브그래프용 필터링된 컨텍스트 생성
- 부모 컨텍스트에서 필요 정보만 추출
- 서브그래프 특화 파라미터 추가

**4. `extract_api_keys_from_env() -> Dict[str, str]`** (Line 163-184)
- 환경변수에서 API 키 추출
- 패턴: "OPENAI_API_KEY", "ANTHROPIC_API_KEY"
- 소문자 키로 정규화

---

### 2.3 States (states.py)

#### 리듀서 함수

##### Custom Reducers (Line 13-33)

**1. `merge_dicts(a: Dict, b: Dict) -> Dict`** (Line 13-19)
- 딕셔너리 병합 (b가 a를 덮어씀)
- None 안전 처리

**2. `append_unique(a: List, b: List) -> List`** (Line 22-33)
- 중복 없이 리스트 병합
- 고유 아이템만 추가

#### 상태 스키마

##### 2.3.1 **TypedDict: `BaseState`** (Line 37-50)
모든 워크플로우의 기본 상태

```python
status: str                    # pending/processing/completed/failed
execution_step: str            # 현재 워크플로우 단계
errors: Annotated[List[str], add]  # 에러 메시지 누적
start_time: Optional[str]      # 시작 시간
end_time: Optional[str]        # 종료 시간
```

##### 2.3.2 **TypedDict: `DataCollectionState`** (Line 54-73)
데이터 수집 서브그래프용 상태

**입력**:
```python
query_params: Dict[str, Any]    # 데이터 수집 파라미터
target_databases: List[str]     # 대상 데이터베이스 목록
```

**수집 결과** (누적):
```python
performance_data: Annotated[List[Dict], add]  # 성과 데이터
target_data: Annotated[List[Dict], add]       # 타겟 데이터
client_data: Annotated[List[Dict], add]       # 클라이언트 데이터
```

**집계 데이터** (병합):
```python
aggregated_performance: Annotated[Dict, merge_dicts]
aggregated_target: Annotated[Dict, merge_dicts]
aggregated_client: Annotated[Dict, merge_dicts]
```

**상태**:
```python
collection_status: str
errors: Annotated[List[str], add]
```

##### 2.3.3 **TypedDict: `AnalysisState`** (Line 76-98)
분석 서브그래프용 상태

**입력 데이터**:
```python
performance_data: List[Dict]   # 데이터 수집에서 전달
target_data: List[Dict]
client_data: List[Dict]
```

**분석 파라미터**:
```python
analysis_type: str             # basic/trend/comparative/comprehensive
analysis_params: Dict[str, Any]
```

**분석 결과** (병합):
```python
basic_metrics: Annotated[Dict, merge_dicts]
trend_analysis: Annotated[Dict, merge_dicts]
comparative_analysis: Annotated[Dict, merge_dicts]
insights: Annotated[List[str], append_unique]  # 중복 제거
```

**최종 보고서**:
```python
analysis_report: Optional[Dict[str, Any]]
```

**상태**:
```python
analysis_status: str
errors: Annotated[List[str], add]
```

##### 2.3.4 **TypedDict: `RealEstateState`** (Line 102-143)
부동산 분석 에이전트 상태

**입력** (덮어쓰기):
```python
query: str                           # 사용자 질문
region: Optional[str]                # 지역명
property_type: Optional[str]         # 매물 유형 (아파트/오피스텔/빌라)
deal_type: Optional[str]             # 거래 유형 (매매/전세/월세)
price_range: Optional[Dict]          # 가격 범위
size_range: Optional[Dict]           # 평형 범위
```

**계획** (덮어쓰기):
```python
execution_plan: Optional[Dict[str, Any]]  # LLM 생성 계획
```

**쿼리 처리** (덮어쓰기):
```python
search_conditions: Dict[str, Any]    # 파싱된 검색 조건
generated_sql: Optional[str]         # 생성된 SQL
```

**데이터 수집** (누적):
```python
listing_results: Annotated[List[Dict], add]  # 매물 검색 결과
```

**서브그래프 결과** (덮어쓰기):
```python
data_collection_result: Optional[Dict]  # DataCollectionSubgraph 결과
analysis_result: Optional[Dict]         # AnalysisSubgraph 결과
```

**집계** (병합):
```python
collected_data: Annotated[Dict, merge_dicts]      # 서브그래프 데이터
execution_results: Annotated[Dict, merge_dicts]   # 실행 결과
aggregated_data: Annotated[Dict, merge_dicts]     # 집계 메트릭
statistics: Annotated[Dict[str, float], merge_dicts]  # 통계 요약
```

**분석** (고유 누적):
```python
insights: Annotated[List[str], append_unique]              # 인사이트
investment_points: Annotated[List[str], append_unique]     # 투자 포인트
```

**출력** (덮어쓰기):
```python
briefing: Optional[str]          # 요약 브리핑
final_report: Optional[Dict]     # 완전한 분석 보고서
```

##### 2.3.5 **TypedDict: `SupervisorState`** (Line 145-200)
슈퍼바이저 메인 오케스트레이터 상태

**입력** (덮어쓰기):
```python
query: str  # 사용자 질문
```

**의도 분석** (덮어쓰기):
```python
intent: Optional[Dict[str, Any]]
# 구조 예시:
{
  "type": "search" | "analysis" | "comparison" | "recommendation",
  "region": "서울특별시 강남구",
  "property_type": "아파트",
  "deal_type": "매매",
  "price_range": {"min": 100000, "max": 150000},
  "size_range": {"min": 30, "max": 40}
}
```

**계획** (덮어쓰기):
```python
execution_plan: Optional[Dict[str, Any]]
# 구조 예시:
{
  "strategy": "sequential" | "parallel" | "dag" | "swarm",
  "agents": [
    {"name": "property_search", "order": 1, "params": {...}},
    {"name": "market_analysis", "order": 2, "params": {...}}
  ]
}
```

**에이전트 실행** (병합):
```python
agent_results: Annotated[Dict[str, Any], merge_dicts]
# 구조 예시:
{
  "property_search": {"status": "success", "data": [...]},
  "market_analysis": {"status": "success", "insights": [...]}
}
```

**평가** (덮어쓰기):
```python
evaluation: Optional[Dict[str, Any]]
# 구조 예시:
{
  "quality_score": 0.85,
  "completeness": True,
  "needs_retry": False,
  "retry_agents": [],
  "feedback": "All data collected successfully"
}
```

**출력** (덮어쓰기):
```python
final_output: Optional[Dict[str, Any]]
# 구조 예시:
{
  "answer": "강남구 아파트 매매 시세는...",
  "listings": [...],
  "insights": [...],
  "metadata": {"total_listings": 10, "avg_price": 150000}
}
```

##### 2.3.6 **TypedDict: `DocumentState`** (Line 202-230)
문서 생성 워크플로우 상태

**문서 특화 필드**:
```python
doc_type: str                  # 문서 유형
doc_format: str                # 출력 형식 (markdown/html/text/word)
title: str                     # 문서 제목
input_data: Dict[str, Any]     # 입력 데이터
template_id: str               # 템플릿 식별자
sections: List[Dict]           # 문서 섹션
content: str                   # 원본 콘텐츠
formatted_content: str         # 포맷팅된 콘텐츠
document_metadata: Dict        # 문서 메타데이터
final_document: Dict           # 최종 문서
```

**대화형 처리 필드**:
```python
user_query: Optional[str]             # 원본 사용자 질문
query_analysis: Optional[Dict]        # LLM 분석 결과
template_analysis: Optional[Dict]     # 템플릿 필드 분석
required_fields: Optional[List[Dict]] # 필수 필드 정의
missing_fields: Optional[List[Dict]]  # 수집 필요 필드
collected_data: Annotated[Dict, merge_dicts]  # 대화형 수집 데이터
interaction_mode: Optional[str]       # interactive/batch/auto
interaction_history: Annotated[List[Dict], add]  # 대화 이력
needs_user_input: bool                # 사용자 입력 필요 플래그
current_prompt: Optional[str]         # 현재 사용자 프롬프트
user_response: Optional[str]          # 최신 사용자 응답
```

#### 상태 팩토리 함수

**1. `create_real_estate_initial_state(**kwargs) -> Dict[str, Any]`** (Line 234-287)
- RealEstateState 초기값 생성
- 기본값 설정:
  - status: "pending"
  - execution_step: "initializing"
  - property_type: "아파트"
  - deal_type: "매매"
  - errors: []
  - 빈 리스트/딕셔너리 초기화

**2. `create_supervisor_initial_state(**kwargs) -> Dict[str, Any]`** (Line 290-325)
- SupervisorState 초기값 생성
- 기본값 설정:
  - status: "pending"
  - execution_step: "initializing"
  - errors: []
  - start_time: 현재 시각 (ISO 형식)
  - 모든 선택적 필드: None
  - agent_results: {}

**3. `merge_state_updates(*updates: Dict) -> Dict`** (Line 328-343)
- 여러 상태 업데이트 병합
- None 값 제외
- 순차적 병합

**4. `get_state_summary(state: Dict) -> Dict`** (Line 346-365)
- 현재 상태 요약 생성
- 반환 정보:
  - status, step
  - errors_count
  - has_results (boolean)
  - data_collected (boolean)
  - insights_count
  - start_time, end_time

---

### 2.4 BaseAgent (base_agent.py)

#### 클래스 구조

**Class: `BaseAgent`** (Line 24-497) - Abstract Base Class

LangGraph 0.6.x Context API를 완전히 지원하는 에이전트 기본 클래스.
MockRuntime 지원으로 테스팅 및 개발 강화.

#### 초기화

**`__init__(agent_name: str, checkpoint_dir: Optional[str])`** (Line 31-56)

```python
self.agent_name: str            # 에이전트 이름
self.logger: Logger             # 에이전트별 로거
self.checkpoint_dir: Path       # 체크포인트 디렉토리
self.checkpointer_path: Path    # 체크포인터 DB 경로
self.workflow: Optional[StateGraph]  # 워크플로우 그래프
```

**초기화 흐름**:
1. 에이전트 이름 설정
2. 로거 초기화 (`agent.{agent_name}`)
3. 체크포인트 디렉토리 설정 (기본: `checkpoints/{agent_name}`)
4. 디렉토리 생성
5. 체크포인터 경로 설정
6. `_build_graph()` 호출하여 워크플로우 초기화

#### 추상 메서드 (서브클래스에서 구현 필수)

**1. `_get_state_schema() -> Type`** (Line 58-66)
- 에이전트의 상태 스키마 반환
- 반환 타입: TypedDict 클래스

**2. `_build_graph()`** (Line 68-74)
- LangGraph 워크플로우 구축
- StateGraph 생성 시 state_schema와 context_schema 모두 지정 필요

**3. `async _validate_input(input_data: Dict) -> bool`** (Line 76-87)
- 입력 데이터 유효성 검증
- 처리 전 호출됨

#### 헬퍼 메서드

**1. `_create_initial_state(input_data: Dict) -> Dict`** (Line 89-106)
- 입력 데이터에서 초기 상태 생성
- 워크플로우 필드만 포함 (컨텍스트 필드 제외)
- 제외 필드: user_id, session_id, metadata, original_query, intent_result
- 기본 상태 필드:
  - status: "pending"
  - execution_step: "starting"

**2. `_create_context(input_data: Dict) -> AgentContext`** (Line 108-128)
- 입력 데이터에서 컨텍스트 생성
- 실행 중 변경되지 않는 메타데이터 포함
- create_agent_context() 팩토리 함수 사용
- 기본값:
  - user_id: "default"
  - session_id: "default"
  - context_type: "agent"

**3. `_create_mock_runtime(state: Dict) -> MockRuntime`** (Line 130-198)
- 테스팅 및 개발용 MockRuntime 생성
- Runtime 호환 인터페이스 제공

**MockRuntime 클래스** (Line 141-180):
```python
# 속성
context: Dict[str, Any]        # 컨텍스트 데이터
_state: Dict[str, Any]         # 상태 데이터
agent_name: str                # 에이전트 이름
logger: Logger                 # 로거
is_mock: bool = True           # Mock 플래그

# 메서드
get_context_value(key, default) -> Any    # 컨텍스트 값 안전 조회
log(message, level)                        # 로깅 헬퍼
user_id -> str                             # Property: 사용자 ID
session_id -> str                          # Property: 세션 ID
request_id -> str                          # Property: 요청 ID
get_state_value(key, default) -> Any      # 상태 값 안전 조회
```

**MockRuntime 컨텍스트 기본값**:
```python
{
  "user_id": "system",
  "session_id": f"mock_{agent_name}_{timestamp}",
  "agent_name": agent_name,
  "request_id": f"mock_req_{uuid}",
  "debug_mode": True,
  "is_mock": True,
  "timestamp": ISO timestamp,
  "environment": "development"
}
```

**4. `_wrap_node_with_runtime(node_func: Callable) -> Callable`** (Line 200-257)
- 노드 함수를 래핑하여 Runtime 파라미터 처리
- MockRuntime 지원 강화

**래핑 로직**:
1. 노드 함수 시그니처 검사 (inspect 사용)
2. "runtime" 파라미터 존재 확인
3. Runtime이 필요하나 없는 경우 MockRuntime 생성
4. 노드 실행 with Runtime (real or mock)
5. 에러 핸들링 및 로깅
6. 원본 함수 메타데이터 보존

#### 실행 메서드

**1. `async execute(input_data: Dict, config: Optional[Dict]) -> Dict`** (Line 259-363)
- Context API를 사용한 에이전트 워크플로우 실행

**실행 흐름**:
```
1. 입력 검증 (_validate_input)
   ↓
2. 초기 상태 생성 (_create_initial_state)
   ↓
3. 컨텍스트 생성 (_create_context)
   ↓
4. Config 준비
   - recursion_limit: 25 (기본값)
   - thread_id: session_id 사용
   ↓
5. 워크플로우 컴파일 (AsyncSqliteSaver)
   ↓
6. 타임아웃 내 실행 (app.ainvoke)
   - initial_state
   - config
   - context
   ↓
7. 결과 반환
```

**반환 형식** (성공):
```python
{
  "status": "success",
  "data": result,
  "agent": agent_name,
  "context": {
    "user_id": str,
    "session_id": str,
    "request_id": str
  }
}
```

**반환 형식** (실패):
```python
{
  "status": "error",
  "error": str,
  "agent": agent_name
}
```

**타임아웃**:
- 기본: 30초
- config["timeout"]으로 설정 가능
- asyncio.wait_for 사용

**2. `async get_state(thread_id: str) -> Optional[Dict]`** (Line 365-383)
- 특정 스레드의 현재 상태 조회
- AsyncSqliteSaver 사용
- app.aget_state() 호출
- 실패 시 None 반환

**3. `async update_state(thread_id, state_update, context) -> bool`** (Line 385-414)
- 특정 스레드의 상태 부분 업데이트
- Context API 패턴 따름
- app.aupdate_state() 사용
- 성공 시 True, 실패 시 False

**4. `@staticmethod create_partial_update(**kwargs) -> Dict`** (Line 417-428)
- 노드용 부분 상태 업데이트 생성 헬퍼
- 사용 예:
```python
return self.create_partial_update(
    field1=new_value1,
    field2=new_value2
)
```

#### 테스팅 및 디버깅 메서드

**1. `async test_node(node_name, test_state, test_context) -> Dict`** (Line 431-466)
- 개별 노드 단위 테스트
- Mock 데이터로 노드 실행
- 유닛 테스팅에 유용

**흐름**:
1. 노드 함수 조회 (getattr)
2. MockRuntime 생성 with test_context
3. 노드 래핑 (_wrap_node_with_runtime)
4. 노드 실행
5. 결과 반환

**2. `validate_state_schema(state: Dict) -> tuple[bool, List[str]]`** (Line 468-497)
- 상태 딕셔너리가 스키마와 일치하는지 검증

**검증 항목**:
1. 필수 필드 존재 여부
   - Optional이 아닌 필드 체크
2. 알 수 없는 필드 경고 (에러는 아님)

**반환**:
- (is_valid: bool, errors: List[str])

---

### 2.5 Checkpointer (checkpointer.py)

#### 함수 목록

**1. `get_checkpointer(checkpoint_path: str, async_mode: bool) -> Optional[Checkpointer]`** (Line 15-47)
- 체크포인터 인스턴스 생성

**파라미터**:
- checkpoint_path: 체크포인트 DB 경로
- async_mode: True면 AsyncSqliteSaver, False면 SqliteSaver

**동작**:
1. 경로의 부모 디렉토리 생성
2. async_mode에 따라 적절한 Saver 생성
3. from_conn_string() 사용
4. 실패 시 None 반환

**2. `async cleanup_old_checkpoints(checkpoint_dir: Path, keep_last: int) -> int`** (Line 50-92)
- 오래된 체크포인트 파일 정리

**파라미터**:
- checkpoint_dir: 체크포인트 디렉토리
- keep_last: 유지할 최신 파일 수 (기본: 5)

**동작**:
1. 디렉토리 내 모든 .db 파일 조회
2. 수정 시간 기준 정렬 (최신 순)
3. keep_last 개수만큼 유지
4. 나머지 삭제
5. 삭제된 파일 수 반환

---

## 3. Supervisor 레이어 상세 분석

### 3.1 Supervisor (supervisor.py)

#### 클래스 구조

**Class: `RealEstateSupervisor(BaseAgent)`** (Line 37-245)

부동산 챗봇의 메인 오케스트레이터. LangGraph 0.6.7+ 문법 (START/END 노드) 사용.

#### 초기화

**`__init__(agent_name, checkpoint_dir, max_retries)`** (Line 49-65)

**파라미터**:
- agent_name: 기본값 "real_estate_supervisor"
- checkpoint_dir: 체크포인트 디렉토리 (선택)
- max_retries: 최대 재시도 횟수 (기본: 2)

**초기화 순서**:
1. max_retries 설정
2. super().__init__() 호출 (BaseAgent 초기화)
3. 로그 출력

#### 상태 스키마

**`_get_state_schema() -> Type`** (Line 67-74)
- SupervisorState 반환

#### 재시도 로직

**`_should_retry(state: Dict) -> Literal["retry", "end"]`** (Line 76-108)

조건부 엣지의 라우팅 함수. 에이전트 실행 재시도 여부 결정.

**동작**:
1. state에서 evaluation 추출
2. needs_retry 플래그 확인
3. retry_count 확인
4. retry_count < max_retries 이면 "retry"
5. 그렇지 않으면 "end"

**로깅**:
- 재시도 시: 시도 횟수 로깅
- 최대 재시도 도달 시: 경고 로깅

#### 워크플로우 구축

**`_build_graph()`** (Line 110-168)

LangGraph 0.6.7+ 최신 문법 사용. START/END 노드 명시.

**그래프 구조**:
```
START
  ↓
analyze_intent (의도 분석)
  ↓
build_plan (계획 수립)
  ↓
execute_agents (Agent 실행)
  ↓
evaluate_results (결과 평가)
  ↓
Should Retry? (조건부 엣지)
  ├─ "retry" → execute_agents (재시도)
  └─ "end" → END (종료)
```

**StateGraph 생성**:
```python
StateGraph(
    state_schema=SupervisorState,
    context_schema=AgentContext
)
```

**노드 추가**:
1. analyze_intent: intent_analyzer.analyze_intent_node
2. build_plan: plan_builder.build_plan_node
3. execute_agents: execution_coordinator.execute_agents_node
4. evaluate_results: result_evaluator.evaluate_results_node

**엣지 추가**:
1. START → analyze_intent
2. analyze_intent → build_plan
3. build_plan → execute_agents
4. execute_agents → evaluate_results
5. evaluate_results → (조건부)
   - "retry" → execute_agents
   - "end" → END

**현대적 특징**:
- START 노드 사용 (set_entry_point() 대체)
- 명시적 END 노드
- 깔끔한 라우팅 로직 분리 (_should_retry)

#### 입력 검증

**`async _validate_input(input_data: Dict) -> bool`** (Line 170-193)

**검증 항목**:
1. "query" 필드 존재
2. query가 문자열 타입
3. query가 빈 문자열이 아님

**실패 시**: 에러 로그 + False 반환

#### 초기 상태 생성

**`_create_initial_state(input_data: Dict) -> Dict`** (Line 195-209)
- create_supervisor_initial_state() 팩토리 함수 사용
- query 필드 전달

#### 고수준 쿼리 처리

**`async process_query(query, user_id, session_id, config) -> Dict`** (Line 211-244)

사용자 쿼리 처리를 위한 편의 메서드.

**동작**:
1. input_data 구성
   - query
   - user_id (기본: "default_user")
   - session_id (기본: "default_session")
2. execute() 호출
3. 성공 시 final_output 반환
4. 실패 시 에러 정보 반환

**반환 형식** (성공):
```python
{
  "answer": str,
  "listings": List,
  "insights": List,
  "metadata": Dict
}
```

**반환 형식** (실패):
```python
{
  "error": str,
  "status": "failed"
}
```

#### 테스트 함수

**`async run_supervisor_test(query: str) -> Dict`** (Line 248-266)
- 빠른 테스팅용 편의 함수
- RealEstateSupervisor 인스턴스 생성
- test_user, test_session으로 쿼리 실행
- 결과 반환

#### 메인 실행

**`if __name__ == "__main__":`** (Line 269-284)
- asyncio 기반 테스트 코드
- 예제 쿼리: "강남역 근처 30평대 아파트 매매 시세 알려줘"
- 결과 출력

---

### 3.2 Intent Analyzer (intent_analyzer.py)

#### 함수 구조

**1. `async call_llm_for_intent(query: str, api_key: str) -> Dict`** (Line 18-67)

사용자 질의 의도 분석을 위한 LLM 호출.

**동작**:
1. AsyncOpenAI 클라이언트 생성
2. get_intent_analysis_prompt() 프롬프트 생성
3. LLM 호출:
   - 모델: gpt-4o-mini
   - temperature: 0.3
   - max_tokens: 500
   - 시스템 프롬프트: "You are an expert in analyzing real estate queries. Always respond in JSON format."
4. 응답 파싱 (JSON)
5. 성공 시 intent 딕셔너리 반환

**에러 처리**:
- JSONDecodeError: 기본 intent 반환
  ```python
  {
    "intent_type": "search",
    "region": None,
    "property_type": None,
    "deal_type": None,
    "price_range": None,
    "size_range": None
  }
  ```
- 기타 예외: 예외 발생 (상위로 전파)

**2. `async analyze_intent_node(state: Dict, runtime: Runtime) -> Dict`** (Line 70-117)

슈퍼바이저의 의도 분석 노드 함수.

**동작**:
1. Runtime에서 컨텍스트 조회 (await runtime.context())
2. state에서 query 추출
3. 컨텍스트에서 API 키 조회
   - ctx["api_keys"]["openai_api_key"] 우선
   - 없으면 환경변수 OPENAI_API_KEY
4. API 키 없으면 실패 반환
5. call_llm_for_intent() 호출
6. 성공 시 상태 업데이트 반환

**반환 형식** (성공):
```python
{
  "intent": {
    "intent_type": "search" | "analysis" | "comparison" | "recommendation",
    "region": str,
    "property_type": str,
    "deal_type": str,
    "price_range": Dict,
    "size_range": Dict
  },
  "status": "processing",
  "execution_step": "planning"
}
```

**반환 형식** (실패):
```python
{
  "status": "failed",
  "errors": [error_message],
  "execution_step": "failed"
}
```

---

### 3.3 Plan Builder (plan_builder.py)

#### 함수 구조

**1. `build_plan_rule_based(intent: Dict) -> Dict`** (Line 18-125)

규칙 기반 실행 계획 생성 (LLM 없이).

**로직**:
```
intent_type에 따른 분기:

"search":
  - property_search (order: 1)
  - strategy: "sequential"

"analysis":
  - property_search (order: 1)
  - market_analysis (order: 2)
  - strategy: "sequential"

"comparison":
  - property_search (order: 1)
  - region_comparison (order: 2)
  - strategy: "sequential"

"recommendation":
  - property_search (order: 1)
  - market_analysis (order: 2)
  - investment_advisor (order: 3)
  - strategy: "sequential"

default:
  - property_search (order: 1)
  - strategy: "sequential"
```

**반환 형식**:
```python
{
  "strategy": "sequential",
  "agents": [
    {
      "name": "property_search",
      "order": 1,
      "params": {
        "region": str,
        "property_type": str,
        "deal_type": str,
        "price_range": Dict,
        "size_range": Dict
      }
    },
    ...
  ]
}
```

**2. `async call_llm_for_planning(intent: Dict, api_key: str) -> Dict`** (Line 128-169)

LLM 기반 실행 계획 생성.

**동작**:
1. AsyncOpenAI 클라이언트 생성
2. get_plan_building_prompt() 프롬프트 생성
3. LLM 호출:
   - 모델: gpt-4o
   - temperature: 0.3
   - max_tokens: 2000
   - 시스템 프롬프트: "You are an expert in planning agent execution strategies. Always respond in JSON format."
4. 응답 파싱 (JSON)
5. 성공 시 plan 반환

**에러 처리**:
- JSONDecodeError: 규칙 기반 폴백
- 기타 예외: 규칙 기반 폴백

**3. `async build_plan_node(state: Dict, runtime: Runtime) -> Dict`** (Line 172-215)

슈퍼바이저의 계획 수립 노드 함수.

**동작**:
1. Runtime에서 컨텍스트 조회
2. state에서 intent 추출
3. 컨텍스트에서 API 키 조회
4. API 키 있으면 LLM 기반 계획 (call_llm_for_planning)
5. API 키 없으면 규칙 기반 계획 (build_plan_rule_based)
6. 성공 시 상태 업데이트 반환

**반환 형식** (성공):
```python
{
  "execution_plan": {
    "strategy": str,
    "agents": List[Dict]
  },
  "status": "processing",
  "execution_step": "executing_agents"
}
```

**반환 형식** (실패):
```python
{
  "status": "failed",
  "errors": [error_message],
  "execution_step": "failed"
}
```

---

### 3.4 Execution Coordinator (execution_coordinator.py)

#### 함수 구조

**1. `get_agent(agent_name: str) -> Agent`** (Line 15-51)

동적 에이전트 임포트 및 인스턴스 반환.

**현재 상태**: Mock 에이전트 반환 (TODO: 실제 에이전트 구현)

**MockAgent 클래스** (Line 37-49):
```python
class MockAgent:
    def __init__(self, name: str):
        self.name = name

    async def execute(self, params: Dict) -> Dict:
        # Mock 실행
        return {
          "status": "success",
          "agent": name,
          "data": f"Mock result from {name}",
          "params": params
        }
```

**향후 구현 계획**:
```python
# from service.agents.property_search import PropertySearchAgent
# from service.agents.market_analysis import MarketAnalysisAgent
# 등등
```

**2. `async execute_agent(agent_config: Dict, ctx: Dict) -> tuple[str, Dict]`** (Line 54-86)

단일 에이전트 실행.

**동작**:
1. agent_config에서 name, params 추출
2. get_agent()로 에이전트 인스턴스 조회
3. agent.execute(params) 호출
4. 성공 시 (agent_name, result) 튜플 반환

**에러 처리**:
- 예외 발생 시 에러 결과 반환:
```python
(agent_name, {
  "status": "error",
  "agent": agent_name,
  "error": str(e)
})
```

**3. `async execute_sequential(agents: List[Dict], ctx: Dict) -> Dict`** (Line 89-114)

순차적 에이전트 실행.

**동작**:
1. agents를 order 기준 정렬
2. 각 에이전트 순차 실행 (for loop)
3. 결과를 딕셔너리에 누적
4. 에이전트 실패 시 중단 (strict mode)
5. 결과 딕셔너리 반환

**반환 형식**:
```python
{
  "property_search": {"status": "success", "data": ...},
  "market_analysis": {"status": "success", "data": ...}
}
```

**4. `async execute_parallel(agents: List[Dict], ctx: Dict) -> Dict`** (Line 117-143)

병렬 에이전트 실행.

**동작**:
1. 모든 에이전트에 대한 태스크 생성
2. asyncio.gather() 실행 (return_exceptions=True)
3. 결과를 딕셔너리로 변환
4. 예외 발생 에이전트 스킵
5. 결과 딕셔너리 반환

**5. `async execute_dag(agents: List[Dict], ctx: Dict) -> Dict`** (Line 146-163)

DAG 방식 에이전트 실행 (Directed Acyclic Graph).

**현재 상태**: Sequential 폴백 (TODO: 완전한 DAG 구현)

**향후 구현**: 에이전트 간 의존성 추적 필요

**6. `async execute_agents_node(state: Dict, runtime: Runtime) -> Dict`** (Line 166-215)

슈퍼바이저의 에이전트 실행 노드 함수.

**동작**:
1. Runtime에서 컨텍스트 조회
2. state에서 execution_plan 추출
3. strategy, agents 추출
4. strategy에 따라 실행:
   - "parallel" → execute_parallel()
   - "dag" → execute_dag()
   - default → execute_sequential()
5. 실패한 에이전트 확인
6. 상태 업데이트 반환

**반환 형식** (성공):
```python
{
  "agent_results": {
    "agent_name": {"status": "success", "data": ...},
    ...
  },
  "status": "processing",
  "execution_step": "evaluating"
}
```

**반환 형식** (실패):
```python
{
  "status": "failed",
  "errors": [error_message],
  "execution_step": "failed"
}
```

---

### 3.5 Result Evaluator (result_evaluator.py)

#### 함수 구조

**1. `evaluate_quality_rule_based(agent_results: Dict) -> Dict`** (Line 18-54)

규칙 기반 품질 평가 (LLM 없이).

**평가 로직**:
1. 모든 에이전트 성공 여부 확인
2. 데이터 존재 여부 확인
3. 실패한 에이전트 카운트
4. quality_score 계산: successful / total
5. needs_retry 결정: 실패 에이전트 존재 시

**반환 형식**:
```python
{
  "quality_score": float,        # 0.0 ~ 1.0
  "completeness": bool,          # 모든 에이전트 성공 & 데이터 존재
  "accuracy": True,              # LLM 없이는 판단 불가
  "consistency": True,           # LLM 없이는 판단 불가
  "needs_retry": bool,           # 실패 에이전트 존재 여부
  "retry_agents": List[str],     # 실패한 에이전트 목록
  "feedback": str                # 평가 피드백
}
```

**2. `async call_llm_for_evaluation(agent_results: Dict, api_key: str) -> Dict`** (Line 57-98)

LLM 기반 품질 평가.

**동작**:
1. AsyncOpenAI 클라이언트 생성
2. get_evaluation_prompt() 프롬프트 생성
3. LLM 호출:
   - 모델: gpt-4o-mini
   - temperature: 0.3
   - max_tokens: 1000
   - 시스템 프롬프트: "You are an expert in evaluating agent execution results. Always respond in JSON format."
4. 응답 파싱 (JSON)
5. 성공 시 evaluation 반환

**에러 처리**:
- JSONDecodeError: 규칙 기반 폴백
- 기타 예외: 규칙 기반 폴백

**3. `format_response_simple(query: str, agent_results: Dict) -> Dict`** (Line 101-140)

단순 응답 포맷팅 (LLM 없이).

**동작**:
1. agent_results에서 성공한 에이전트의 데이터 수집
2. 리스트/딕셔너리/기타 데이터 통합
3. insights 수집
4. 최대 10개 결과만 포함

**반환 형식**:
```python
{
  "answer": str,                  # "검색 완료: N개의 결과를 찾았습니다."
  "listings": List[Dict],         # 상위 10개 결과
  "insights": List[str],          # 에이전트의 인사이트 통합
  "metadata": {
    "total_results": int,
    "agents_used": List[str]
  }
}
```

**4. `async call_llm_for_formatting(query: str, agent_results: Dict, api_key: str) -> Dict`** (Line 143-185)

LLM 기반 응답 포맷팅.

**동작**:
1. AsyncOpenAI 클라이언트 생성
2. get_response_formatting_prompt() 프롬프트 생성
3. LLM 호출:
   - 모델: gpt-4o
   - temperature: 0.7
   - max_tokens: 2000
   - 시스템 프롬프트: "You are an expert in formatting real estate information for users. Always respond in JSON format."
4. 응답 파싱 (JSON)
5. 성공 시 final_output 반환

**에러 처리**:
- JSONDecodeError: 단순 포맷팅 폴백
- 기타 예외: 단순 포맷팅 폴백

**5. `async evaluate_results_node(state: Dict, runtime: Runtime) -> Dict`** (Line 188-255)

슈퍼바이저의 결과 평가 노드 함수.

**동작**:
1. Runtime에서 컨텍스트 조회
2. state에서 agent_results, query 추출
3. 컨텍스트에서 API 키 조회
4. 품질 평가:
   - API 키 있으면 LLM 기반 (call_llm_for_evaluation)
   - API 키 없으면 규칙 기반 (evaluate_quality_rule_based)
5. 재시도 필요 시:
   - evaluation 반환
   - execution_step: "executing_agents"
6. 재시도 불필요 시:
   - 응답 포맷팅:
     - API 키 있으면 LLM 기반 (call_llm_for_formatting)
     - API 키 없으면 단순 포맷팅 (format_response_simple)
   - final_output 반환

**반환 형식** (재시도 필요):
```python
{
  "evaluation": {
    "quality_score": float,
    "completeness": bool,
    "needs_retry": True,
    "retry_agents": List[str],
    "feedback": str
  },
  "status": "processing",
  "execution_step": "executing_agents"
}
```

**반환 형식** (완료):
```python
{
  "evaluation": {
    "quality_score": float,
    "completeness": bool,
    "needs_retry": False,
    ...
  },
  "final_output": {
    "answer": str,
    "listings": List[Dict],
    "insights": List[str],
    "metadata": Dict
  },
  "status": "completed",
  "execution_step": "finished",
  "end_time": None
}
```

**반환 형식** (실패):
```python
{
  "status": "failed",
  "errors": [error_message],
  "execution_step": "failed"
}
```

---

### 3.6 Prompts (prompts.py)

#### 프롬프트 템플릿

**1. `INTENT_ANALYSIS_PROMPT`** (Line 9-39)

사용자 질의 의도 분석용 프롬프트.

**추출 정보**:
1. intent_type: "search" | "analysis" | "comparison" | "recommendation"
2. region: 지역명 (예: "서울특별시 강남구")
3. property_type: "아파트" | "오피스텔" | "빌라" | "단독주택" (null 가능)
4. deal_type: "매매" | "전세" | "월세" (null 가능)
5. price_range: {"min": int, "max": int} (null 가능)
6. size_range: {"min": int, "max": int} (평형, null 가능)

**응답 형식**: JSON

**언어**: 한국어

**2. `PLAN_BUILDING_PROMPT`** (Line 42-89)

실행 계획 수립용 프롬프트.

**사용 가능한 Agent**:
1. property_search: 매물 검색
2. market_analysis: 시장 분석
3. region_comparison: 지역 비교
4. investment_advisor: 투자 자문

**실행 전략**:
- sequential: 순차 실행 (의존성 있을 때)
- parallel: 병렬 실행 (독립적일 때)
- dag: DAG 방식 (복잡한 의존성)

**규칙**:
- "search" → property_search만
- "analysis" → property_search + market_analysis
- "comparison" → property_search + region_comparison
- "recommendation" → 모든 Agent

**응답 형식**: JSON
```json
{
  "strategy": "sequential",
  "agents": [
    {
      "name": "property_search",
      "order": 1,
      "params": {...}
    }
  ]
}
```

**3. `EVALUATION_PROMPT`** (Line 92-120)

에이전트 결과 품질 평가용 프롬프트.

**평가 기준**:
1. completeness: 모든 필요한 데이터 수집되었는가?
2. accuracy: 데이터가 정확하고 신뢰할 수 있는가?
3. consistency: Agent 결과들이 서로 모순되지 않는가?

**재시도 조건**:
- Agent가 에러 반환
- 데이터 불완전 (completeness: false)
- 데이터 부정확 (accuracy: false)

**응답 형식**: JSON
```json
{
  "quality_score": 0.85,
  "completeness": true,
  "accuracy": true,
  "consistency": true,
  "needs_retry": false,
  "retry_agents": [],
  "feedback": "모든 데이터가 성공적으로 수집되었습니다."
}
```

**4. `RESPONSE_FORMATTING_PROMPT`** (Line 123-167)

최종 사용자 응답 포맷팅용 프롬프트.

**응답 구조**:
1. answer: 직접적인 답변 (2-3문장, 한국어)
2. listings: 검색된 매물 리스트 (최대 10개)
3. insights: 분석 결과 및 특징 (bullet points)
4. metadata: 통계 정보

**응답 형식**: JSON
```json
{
  "answer": "강남구의 30평대 아파트 매매 시세는...",
  "listings": [
    {
      "name": "래미안 아파트",
      "region": "서울특별시 강남구 역삼동",
      "price": 120000,
      "size": 32,
      "deal_type": "매매"
    }
  ],
  "insights": [
    "강남구는 학군이 우수하여 수요가 높습니다",
    ...
  ],
  "metadata": {
    "total_listings": 10,
    "avg_price": 120000,
    "price_range": {"min": 100000, "max": 150000},
    "region": "서울특별시 강남구"
  }
}
```

**언어**: 한국어

#### 헬퍼 함수

**1. `get_intent_analysis_prompt(query: str) -> str`** (Line 170-172)
- 사용자 query를 INTENT_ANALYSIS_PROMPT에 삽입
- format() 사용

**2. `get_plan_building_prompt(intent: Dict) -> str`** (Line 175-178)
- intent 딕셔너리를 JSON 문자열로 변환
- PLAN_BUILDING_PROMPT에 삽입
- ensure_ascii=False (한글 보존)

**3. `get_evaluation_prompt(agent_results: Dict) -> str`** (Line 181-184)
- agent_results 딕셔너리를 JSON 문자열로 변환
- EVALUATION_PROMPT에 삽입
- ensure_ascii=False

**4. `get_response_formatting_prompt(query: str, agent_results: Dict) -> str`** (Line 187-193)
- query와 agent_results를 RESPONSE_FORMATTING_PROMPT에 삽입
- agent_results는 JSON 문자열로 변환
- ensure_ascii=False

---

## 4. 데이터 플로우 분석

### 4.1 전체 실행 흐름

```
사용자 질의 입력
    ↓
RealEstateSupervisor.process_query()
    ↓
execute(input_data, config)
    ↓
[START 노드]
    ↓
analyze_intent_node
    - LLM (gpt-4o-mini) 호출
    - intent 추출
    - state["intent"] 업데이트
    ↓
build_plan_node
    - LLM (gpt-4o) 호출 또는 규칙 기반
    - execution_plan 생성
    - state["execution_plan"] 업데이트
    ↓
execute_agents_node
    - strategy에 따라 실행 (sequential/parallel/dag)
    - 각 에이전트 execute() 호출
    - state["agent_results"] 업데이트
    ↓
evaluate_results_node
    - LLM 또는 규칙 기반 품질 평가
    - state["evaluation"] 업데이트
    - 재시도 필요 시:
        ↓
      execute_agents_node (재실행)
    - 재시도 불필요 시:
        - LLM 또는 단순 응답 포맷팅
        - state["final_output"] 업데이트
        ↓
      [END 노드]
    ↓
최종 결과 반환
```

### 4.2 State 변화 추적

**초기 상태** (create_supervisor_initial_state):
```python
{
  "status": "pending",
  "execution_step": "initializing",
  "errors": [],
  "start_time": "2025-09-27T...",
  "query": "강남역 근처 30평대 아파트 매매 시세 알려줘",
  "intent": None,
  "execution_plan": None,
  "agent_results": {},
  "evaluation": None,
  "final_output": None,
  "end_time": None
}
```

**analyze_intent_node 후**:
```python
{
  ...
  "intent": {
    "intent_type": "search",
    "region": "서울특별시 강남구",
    "property_type": "아파트",
    "deal_type": "매매",
    "size_range": {"min": 30, "max": 40}
  },
  "status": "processing",
  "execution_step": "planning"
}
```

**build_plan_node 후**:
```python
{
  ...
  "execution_plan": {
    "strategy": "sequential",
    "agents": [
      {
        "name": "property_search",
        "order": 1,
        "params": {...}
      }
    ]
  },
  "execution_step": "executing_agents"
}
```

**execute_agents_node 후**:
```python
{
  ...
  "agent_results": {
    "property_search": {
      "status": "success",
      "agent": "property_search",
      "data": [...]
    }
  },
  "execution_step": "evaluating"
}
```

**evaluate_results_node 후** (완료):
```python
{
  ...
  "evaluation": {
    "quality_score": 1.0,
    "completeness": true,
    "needs_retry": false,
    "feedback": "..."
  },
  "final_output": {
    "answer": "강남역 근처 30평대 아파트...",
    "listings": [...],
    "insights": [...],
    "metadata": {...}
  },
  "status": "completed",
  "execution_step": "finished",
  "end_time": "2025-09-27T..."
}
```

### 4.3 Context 전파

**컨텍스트 생성** (execute):
```python
context = create_agent_context(
    user_id="default_user",
    session_id="default_session",
    original_query="강남역 근처...",
    api_keys={"openai_api_key": "sk-..."}
)
```

**노드에서 컨텍스트 사용**:
```python
async def node_func(state: Dict, runtime: Runtime):
    ctx = await runtime.context()

    # 컨텍스트 값 조회
    user_id = ctx.get("user_id")
    session_id = ctx.get("session_id")
    api_keys = ctx.get("api_keys", {})
    openai_key = api_keys.get("openai_api_key")

    # LLM 호출 등
    ...
```

**컨텍스트 불변성**:
- 노드는 컨텍스트를 읽기만 함 (READ-ONLY)
- 상태(state)만 업데이트 가능
- 컨텍스트는 런타임 메타데이터 제공

---

## 5. 고도화 권장사항

### 5.1 Core 레이어 개선

#### 5.1.1 Config
**현재 상태**: 정적 클래스 기반 설정

**개선 방안**:
1. **환경별 설정 분리**
   ```python
   class Config:
       @classmethod
       def get_env_config(cls, env: str) -> Dict:
           # development, staging, production
           pass
   ```

2. **설정 검증 강화**
   - Pydantic 도입
   - 타입 안전성 확보
   - 자동 검증

3. **동적 설정 로드**
   - 외부 설정 파일 지원 (YAML, TOML)
   - 설정 리로드 기능

4. **시크릿 관리**
   - API 키를 환경변수 외 방식 지원
   - AWS Secrets Manager, HashiCorp Vault 연동

#### 5.1.2 Context
**현재 상태**: TypedDict 기반 컨텍스트

**개선 방안**:
1. **컨텍스트 유효성 검증**
   ```python
   def validate_context(context: Dict) -> bool:
       # 필수 필드 검증
       # 타입 검증
       pass
   ```

2. **컨텍스트 빌더 패턴**
   ```python
   class ContextBuilder:
       def set_user(self, user_id: str): ...
       def set_session(self, session_id: str): ...
       def build(self) -> AgentContext: ...
   ```

3. **컨텍스트 상속 체계**
   - 여러 레벨의 컨텍스트 (글로벌, 에이전트, 노드)
   - 컨텍스트 병합 전략

#### 5.1.3 States
**현재 상태**: TypedDict + Annotated 리듀서

**개선 방안**:
1. **상태 전이 검증**
   ```python
   def validate_state_transition(
       from_state: str,
       to_state: str
   ) -> bool:
       # 유효한 전이인지 검증
       pass
   ```

2. **상태 스냅샷 및 복원**
   ```python
   def create_state_snapshot(state: Dict) -> bytes:
       pass

   def restore_state_from_snapshot(snapshot: bytes) -> Dict:
       pass
   ```

3. **상태 마이그레이션**
   - 스키마 변경 시 기존 상태 마이그레이션
   - 버전 관리

4. **커스텀 리듀서 확장**
   ```python
   def merge_lists_ordered(a: List, b: List) -> List:
       # 순서 유지 병합
       pass

   def merge_with_conflict_resolution(a: Dict, b: Dict) -> Dict:
       # 충돌 해결 전략
       pass
   ```

#### 5.1.4 BaseAgent
**현재 상태**: MockRuntime 지원

**개선 방안**:
1. **에이전트 생명주기 관리**
   ```python
   async def on_start(self):
       # 초기화 작업
       pass

   async def on_stop(self):
       # 정리 작업
       pass

   async def on_error(self, error: Exception):
       # 에러 핸들링
       pass
   ```

2. **에이전트 메트릭 수집**
   ```python
   def collect_metrics(self) -> Dict:
       # 실행 시간, 성공률, 에러율 등
       pass
   ```

3. **에이전트 간 통신**
   - 메시지 버스 패턴
   - 이벤트 기반 통신

4. **에이전트 버전 관리**
   ```python
   class BaseAgent:
       VERSION = "1.0.0"

       @classmethod
       def get_version(cls) -> str:
           pass
   ```

5. **에이전트 테스팅 도구 확장**
   ```python
   async def test_workflow(
       self,
       test_cases: List[Dict]
   ) -> TestReport:
       # 워크플로우 전체 테스팅
       pass
   ```

#### 5.1.5 Checkpointer
**현재 상태**: SQLite 기반 체크포인팅

**개선 방안**:
1. **다중 백엔드 지원**
   - Redis
   - PostgreSQL
   - S3

2. **체크포인트 압축**
   ```python
   def compress_checkpoint(data: bytes) -> bytes:
       pass
   ```

3. **체크포인트 암호화**
   ```python
   def encrypt_checkpoint(data: bytes, key: str) -> bytes:
       pass
   ```

4. **체크포인트 버전 관리**
   - 시간 기반 스냅샷
   - 태그 기반 스냅샷

---

### 5.2 Supervisor 레이어 개선

#### 5.2.1 Supervisor
**현재 상태**: 기본 재시도 로직

**개선 방안**:
1. **동적 라우팅**
   ```python
   def _route_next(self, state: Dict) -> str:
       # 상태 기반 동적 노드 선택
       pass
   ```

2. **병렬 분기**
   ```python
   # 여러 경로 동시 실행 후 병합
   self.workflow.add_conditional_edges(
       "analyze_intent",
       self._split_routing,
       {
           "path_A": ["nodeA1", "nodeA2"],
           "path_B": ["nodeB1", "nodeB2"]
       }
   )
   ```

3. **서브그래프 통합**
   ```python
   from langgraph.graph import StateGraph

   # 서브그래프 생성
   data_collection_graph = StateGraph(...)

   # 메인 그래프에 추가
   self.workflow.add_node(
       "collect_data",
       data_collection_graph.compile()
   )
   ```

4. **우선순위 큐 기반 실행**
   ```python
   execution_plan: {
       "agents": [
           {"name": "...", "priority": 1},
           {"name": "...", "priority": 2}
       ]
   }
   ```

5. **실행 전략 확장**
   - 현재: sequential, parallel, dag
   - 추가: swarm, hierarchical, pipeline

#### 5.2.2 Intent Analyzer
**현재 상태**: 단일 LLM 호출

**개선 방안**:
1. **다단계 의도 분석**
   ```python
   async def analyze_intent_multi_stage(query: str):
       # Stage 1: 기본 분류
       basic_intent = await classify_intent(query)

       # Stage 2: 엔티티 추출
       entities = await extract_entities(query, basic_intent)

       # Stage 3: 검증
       validated = await validate_intent(basic_intent, entities)

       return validated
   ```

2. **의도 신뢰도 점수**
   ```python
   {
       "intent_type": "search",
       "confidence": 0.95,
       "alternatives": [
           {"type": "analysis", "confidence": 0.03}
       ]
   }
   ```

3. **컨텍스트 기반 의도 추론**
   - 대화 이력 활용
   - 사용자 프로필 활용

4. **다국어 지원**
   ```python
   async def analyze_intent_multilingual(
       query: str,
       language: str
   ):
       pass
   ```

5. **의도 캐싱**
   ```python
   @lru_cache(maxsize=1000)
   def get_cached_intent(query_hash: str):
       pass
   ```

#### 5.2.3 Plan Builder
**현재 상태**: 규칙 기반 + LLM 기반

**개선 방안**:
1. **계획 최적화**
   ```python
   def optimize_plan(plan: Dict) -> Dict:
       # 불필요한 에이전트 제거
       # 병렬화 가능 구간 식별
       # 비용 최소화
       pass
   ```

2. **에이전트 간 의존성 그래프**
   ```python
   plan: {
       "agents": [
           {
               "name": "agent_A",
               "depends_on": []
           },
           {
               "name": "agent_B",
               "depends_on": ["agent_A"]
           }
       ]
   }
   ```

3. **조건부 계획**
   ```python
   plan: {
       "agents": [
           {
               "name": "agent_A",
               "execute_if": "intent_type == 'search'"
           }
       ]
   }
   ```

4. **계획 템플릿**
   ```python
   PLAN_TEMPLATES = {
       "search": {...},
       "analysis": {...},
       "comparison": {...}
   }
   ```

5. **계획 검증**
   ```python
   def validate_plan(plan: Dict, intent: Dict) -> bool:
       # 계획이 의도를 충족하는지 검증
       pass
   ```

#### 5.2.4 Execution Coordinator
**현재 상태**: Mock 에이전트 사용

**개선 방안**:
1. **실제 에이전트 구현**
   ```python
   # service/agents/property_search.py
   class PropertySearchAgent(BaseAgent):
       async def execute(self, params: Dict):
           # 실제 DB 쿼리
           pass

   # service/agents/market_analysis.py
   class MarketAnalysisAgent(BaseAgent):
       async def execute(self, params: Dict):
           # 시장 분석 로직
           pass
   ```

2. **에이전트 레지스트리**
   ```python
   class AgentRegistry:
       _agents = {}

       @classmethod
       def register(cls, name: str, agent_class: Type):
           cls._agents[name] = agent_class

       @classmethod
       def get(cls, name: str):
           return cls._agents[name]()
   ```

3. **에이전트 풀 관리**
   ```python
   class AgentPool:
       def __init__(self, max_agents: int):
           self.pool = asyncio.Queue(maxsize=max_agents)

       async def acquire(self, agent_name: str):
           pass

       async def release(self, agent):
           pass
   ```

4. **에이전트 타임아웃 및 재시도**
   ```python
   async def execute_agent_with_retry(
       agent_config: Dict,
       max_retries: int = 3,
       timeout: int = 30
   ):
       for attempt in range(max_retries):
           try:
               result = await asyncio.wait_for(
                   execute_agent(agent_config),
                   timeout=timeout
               )
               return result
           except asyncio.TimeoutError:
               if attempt < max_retries - 1:
                   continue
               raise
   ```

5. **DAG 실행 완전 구현**
   ```python
   async def execute_dag_complete(
       agents: List[Dict],
       ctx: Dict
   ) -> Dict:
       # 1. 의존성 그래프 구축
       graph = build_dependency_graph(agents)

       # 2. 토폴로지 정렬
       sorted_agents = topological_sort(graph)

       # 3. 레벨별 병렬 실행
       for level in sorted_agents:
           level_results = await execute_parallel(level, ctx)
           # 결과를 다음 레벨에 전달

       return all_results
   ```

6. **에이전트 모니터링**
   ```python
   class AgentMonitor:
       def log_start(self, agent_name: str):
           pass

       def log_end(self, agent_name: str, duration: float):
           pass

       def log_error(self, agent_name: str, error: Exception):
           pass

       def get_metrics(self) -> Dict:
           pass
   ```

#### 5.2.5 Result Evaluator
**현재 상태**: 규칙 기반 + LLM 기반

**개선 방안**:
1. **평가 메트릭 확장**
   ```python
   evaluation: {
       "quality_score": float,
       "completeness": bool,
       "accuracy": bool,
       "consistency": bool,
       "relevance": float,        # 추가
       "freshness": float,        # 추가
       "coverage": float,         # 추가
       "needs_retry": bool,
       "retry_agents": List[str]
   }
   ```

2. **다중 평가자 앙상블**
   ```python
   async def evaluate_ensemble(agent_results: Dict):
       # 여러 평가 전략 병렬 실행
       evals = await asyncio.gather(
           evaluate_rule_based(agent_results),
           evaluate_llm_based(agent_results),
           evaluate_ml_based(agent_results)
       )

       # 앙상블 결과 생성
       return merge_evaluations(evals)
   ```

3. **사용자 피드백 통합**
   ```python
   evaluation: {
       ...,
       "user_feedback": {
           "satisfaction": 4.5,
           "comments": ["..."]
       }
   }
   ```

4. **A/B 테스팅 지원**
   ```python
   async def evaluate_with_ab_test(
       agent_results_A: Dict,
       agent_results_B: Dict
   ):
       # 두 결과 비교 평가
       pass
   ```

5. **응답 포맷팅 개선**
   ```python
   final_output: {
       "answer": str,
       "listings": List[Dict],
       "insights": List[str],
       "metadata": Dict,
       "visualizations": List[Dict],  # 추가: 차트/그래프 데이터
       "recommendations": List[Dict], # 추가: 개인화 추천
       "references": List[str]        # 추가: 출처 정보
   }
   ```

6. **응답 캐싱**
   ```python
   @cache_response(ttl=3600)  # 1시간 캐싱
   async def format_response(query: str, agent_results: Dict):
       pass
   ```

#### 5.2.6 Prompts
**현재 상태**: 정적 문자열 템플릿

**개선 방안**:
1. **프롬프트 버전 관리**
   ```python
   class PromptVersion:
       v1_0 = "..."
       v1_1 = "..."
       current = v1_1
   ```

2. **프롬프트 템플릿 엔진**
   ```python
   from jinja2 import Template

   template = Template(INTENT_ANALYSIS_PROMPT)
   prompt = template.render(
       query=query,
       examples=examples,
       context=context
   )
   ```

3. **Few-shot 예제 동적 선택**
   ```python
   def select_examples(query: str, k: int = 3):
       # 쿼리와 유사한 예제 선택
       pass
   ```

4. **프롬프트 최적화**
   ```python
   def optimize_prompt(prompt: str, budget: int):
       # 토큰 수 줄이기
       # 핵심 정보 유지
       pass
   ```

5. **다국어 프롬프트**
   ```python
   PROMPTS = {
       "ko": {...},
       "en": {...},
       "ja": {...}
   }

   def get_prompt(key: str, lang: str = "ko"):
       return PROMPTS[lang][key]
   ```

6. **프롬프트 A/B 테스팅**
   ```python
   @ab_test(variants=["v1", "v2"])
   def get_intent_prompt(query: str, variant: str):
       pass
   ```

---

### 5.3 새로운 컴포넌트 추가

#### 5.3.1 에이전트 구현
**priority: HIGH**

```python
# service/agents/property_search.py
class PropertySearchAgent(BaseAgent):
    def _get_state_schema(self):
        return PropertySearchState

    def _build_graph(self):
        # 1. 쿼리 파싱
        # 2. SQL 생성
        # 3. DB 실행
        # 4. 결과 포맷팅
        pass

# service/agents/market_analysis.py
class MarketAnalysisAgent(BaseAgent):
    def _get_state_schema(self):
        return MarketAnalysisState

    def _build_graph(self):
        # 1. 데이터 수집
        # 2. 통계 분석
        # 3. 트렌드 분석
        # 4. 인사이트 생성
        pass

# service/agents/region_comparison.py
class RegionComparisonAgent(BaseAgent):
    pass

# service/agents/investment_advisor.py
class InvestmentAdvisorAgent(BaseAgent):
    pass
```

#### 5.3.2 데이터베이스 레이어
**priority: HIGH**

```python
# service/database/connection_pool.py
class ConnectionPool:
    def __init__(self, db_paths: Dict[str, Path]):
        self.pools = {}

    async def acquire(self, db_name: str):
        pass

    async def release(self, connection):
        pass

# service/database/query_builder.py
class QueryBuilder:
    def select(self, table: str):
        pass

    def where(self, condition: str):
        pass

    def build(self) -> str:
        pass

# service/database/models.py
from sqlalchemy import declarative_base

Base = declarative_base()

class PropertyListing(Base):
    __tablename__ = "listings"
    # 필드 정의
    pass

class RegionalInfo(Base):
    __tablename__ = "regional_info"
    # 필드 정의
    pass
```

#### 5.3.3 API 레이어
**priority: MEDIUM**

```python
# api/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class QueryRequest(BaseModel):
    query: str
    user_id: str
    session_id: str

class QueryResponse(BaseModel):
    answer: str
    listings: List[Dict]
    insights: List[str]
    metadata: Dict

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    supervisor = RealEstateSupervisor()
    result = await supervisor.process_query(
        query=request.query,
        user_id=request.user_id,
        session_id=request.session_id
    )
    return result

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# api/websocket.py
from fastapi import WebSocket

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # 스트리밍 응답
    async for chunk in supervisor.stream_query(...):
        await websocket.send_json(chunk)
```

#### 5.3.4 캐싱 레이어
**priority: MEDIUM**

```python
# service/cache/redis_cache.py
import redis.asyncio as aioredis

class RedisCache:
    def __init__(self, url: str):
        self.redis = aioredis.from_url(url)

    async def get(self, key: str):
        pass

    async def set(self, key: str, value: Any, ttl: int):
        pass

    async def delete(self, key: str):
        pass

# service/cache/decorator.py
def cache_result(ttl: int = 3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = generate_cache_key(func, args, kwargs)
            cached = await cache.get(key)
            if cached:
                return cached

            result = await func(*args, **kwargs)
            await cache.set(key, result, ttl)
            return result
        return wrapper
    return decorator
```

#### 5.3.5 모니터링 및 로깅
**priority: MEDIUM**

```python
# service/monitoring/metrics.py
from prometheus_client import Counter, Histogram

query_counter = Counter(
    "query_total",
    "Total queries processed"
)

query_duration = Histogram(
    "query_duration_seconds",
    "Query processing duration"
)

agent_errors = Counter(
    "agent_errors_total",
    "Total agent errors",
    ["agent_name"]
)

# service/monitoring/logger.py
import structlog

logger = structlog.get_logger()

def log_query_start(query: str, user_id: str):
    logger.info(
        "query_started",
        query=query,
        user_id=user_id
    )

def log_query_end(query: str, duration: float, status: str):
    logger.info(
        "query_completed",
        query=query,
        duration=duration,
        status=status
    )
```

#### 5.3.6 테스팅 프레임워크
**priority: LOW**

```python
# tests/unit/test_intent_analyzer.py
import pytest

@pytest.mark.asyncio
async def test_analyze_intent_search():
    query = "강남 아파트 찾아줘"
    intent = await analyze_intent(query)

    assert intent["intent_type"] == "search"
    assert "강남" in intent["region"]

# tests/integration/test_supervisor.py
@pytest.mark.asyncio
async def test_supervisor_end_to_end():
    supervisor = RealEstateSupervisor()
    result = await supervisor.process_query(
        query="강남역 근처 30평대 아파트 매매 시세",
        user_id="test",
        session_id="test"
    )

    assert result["status"] == "success"
    assert len(result["listings"]) > 0

# tests/load/locustfile.py
from locust import HttpUser, task

class ChatbotUser(HttpUser):
    @task
    def query(self):
        self.client.post("/query", json={
            "query": "강남 아파트",
            "user_id": "load_test",
            "session_id": "load_test"
        })
```

---

## 6. 기술 스택 및 의존성

### 6.1 현재 사용 중인 라이브러리

```
langgraph==0.6.7             # 워크플로우 오케스트레이션
openai                        # LLM API
python-dotenv                 # 환경변수 관리
pathlib (built-in)           # 경로 관리
asyncio (built-in)           # 비동기 처리
logging (built-in)           # 로깅
typing (built-in)            # 타입 힌팅
json (built-in)              # JSON 처리
uuid (built-in)              # ID 생성
datetime (built-in)          # 시간 처리
operator (built-in)          # 리듀서 함수
```

### 6.2 추가 권장 라이브러리

**데이터베이스**:
```
sqlalchemy>=2.0              # ORM
alembic                      # 마이그레이션
aiosqlite                    # 비동기 SQLite
psycopg2-binary              # PostgreSQL (선택)
```

**API 서버**:
```
fastapi>=0.100               # API 프레임워크
uvicorn[standard]            # ASGI 서버
pydantic>=2.0                # 데이터 검증
```

**캐싱**:
```
redis[hiredis]>=5.0          # Redis 클라이언트
aioredis                     # 비동기 Redis
```

**모니터링**:
```
prometheus-client            # 메트릭 수집
structlog                    # 구조화된 로깅
sentry-sdk                   # 에러 추적
```

**테스팅**:
```
pytest>=7.0                  # 테스트 프레임워크
pytest-asyncio               # 비동기 테스트
pytest-cov                   # 커버리지
locust                       # 부하 테스트
```

**유틸리티**:
```
tenacity                     # 재시도 로직
pydantic-settings            # 설정 관리
python-multipart             # 파일 업로드
jinja2                       # 템플릿 엔진
```

---

## 7. 성능 최적화 전략

### 7.1 LLM 호출 최적화

**1. 프롬프트 캐싱**
```python
# 동일 쿼리에 대한 LLM 응답 캐싱
@cache_llm_response(ttl=86400)  # 24시간
async def call_llm_for_intent(query: str):
    pass
```

**2. 배치 처리**
```python
async def analyze_intents_batch(queries: List[str]):
    # 여러 쿼리를 한 번에 처리
    pass
```

**3. 모델 선택 전략**
```python
def select_model(task_complexity: str):
    if task_complexity == "low":
        return "gpt-4o-mini"  # 빠르고 저렴
    else:
        return "gpt-4o"  # 정확하지만 느림
```

### 7.2 데이터베이스 최적화

**1. 연결 풀링**
```python
pool = ConnectionPool(
    min_size=5,
    max_size=20,
    timeout=30
)
```

**2. 쿼리 최적화**
```python
# 인덱스 추가
CREATE INDEX idx_region ON listings(region);
CREATE INDEX idx_price ON listings(price);

# 쿼리 계획 분석
EXPLAIN QUERY PLAN SELECT ...
```

**3. 읽기 복제본**
```python
# 읽기는 복제본, 쓰기는 마스터
read_db = get_connection("replica")
write_db = get_connection("master")
```

### 7.3 병렬 처리

**1. 에이전트 병렬 실행**
```python
# 독립적인 에이전트들은 병렬 실행
results = await asyncio.gather(
    property_search.execute(),
    market_analysis.execute(),
    region_comparison.execute()
)
```

**2. 데이터 수집 병렬화**
```python
# 여러 DB에서 동시 수집
results = await asyncio.gather(
    fetch_from_listings_db(),
    fetch_from_regional_db(),
    fetch_from_user_db()
)
```

### 7.4 메모리 최적화

**1. 스트리밍 응답**
```python
async def stream_query_results(query: str):
    async for chunk in process_query_stream(query):
        yield chunk  # 부분 결과 즉시 반환
```

**2. 페이지네이션**
```python
def get_listings(offset: int = 0, limit: int = 100):
    # 대량 데이터는 페이지로 나눠 처리
    pass
```

**3. 결과 압축**
```python
import gzip

def compress_result(data: Dict) -> bytes:
    return gzip.compress(json.dumps(data).encode())
```

---

## 8. 보안 고려사항

### 8.1 API 키 관리

**1. 환경변수 분리**
```bash
# .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...

# .env.example (버전 관리에 포함)
OPENAI_API_KEY=your_key_here
```

**2. 시크릿 관리 서비스**
```python
from aws_secretsmanager import get_secret

api_key = get_secret("openai_api_key")
```

### 8.2 입력 검증

**1. 쿼리 검증**
```python
def validate_query(query: str) -> bool:
    if len(query) > MAX_QUERY_LENGTH:
        return False

    if contains_sql_injection(query):
        return False

    return True
```

**2. SQL 인젝션 방지**
```python
# ❌ 나쁜 예
query = f"SELECT * FROM listings WHERE region = '{region}'"

# ✅ 좋은 예
query = "SELECT * FROM listings WHERE region = ?"
cursor.execute(query, (region,))
```

### 8.3 접근 제어

**1. 사용자 인증**
```python
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401)
    return user
```

**2. Rate Limiting**
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/query")
@limiter.limit("10/minute")
async def process_query(request: QueryRequest):
    pass
```

---

## 9. 배포 및 운영

### 9.1 Docker 컨테이너화

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./checkpoints:/app/checkpoints
      - ./logs:/app/logs
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
```

### 9.2 CI/CD 파이프라인

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/ --cov=service
      - name: Lint
        run: ruff check .
```

### 9.3 모니터링 설정

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'chatbot'
    static_configs:
      - targets: ['api:8000']
```

```python
# service/monitoring/metrics.py
from prometheus_client import start_http_server

# 메트릭 서버 시작
start_http_server(8001)
```

---

## 10. 결론 및 다음 단계

### 10.1 현재 구현 상태 요약

**✅ 완료된 부분**:
1. Core 레이어 기본 구조 (Config, Context, States, BaseAgent, Checkpointer)
2. Supervisor 워크플로우 오케스트레이션
3. Intent Analysis → Plan Building → Execution → Evaluation 파이프라인
4. LangGraph 0.6.7 최신 문법 적용 (START/END 노드)
5. MockRuntime 기반 테스팅 지원
6. LLM 기반 + 규칙 기반 하이브리드 접근

**⚠️ 미완성 부분**:
1. 실제 에이전트 구현 (현재 Mock)
2. 데이터베이스 연동
3. API 서버
4. 캐싱 레이어
5. 프로덕션 레벨 에러 핸들링
6. 모니터링 및 로깅 인프라

### 10.2 우선순위별 개발 로드맵

**Phase 1: 핵심 기능 구현** (2-3주)
1. 실제 에이전트 구현
   - PropertySearchAgent
   - MarketAnalysisAgent
2. 데이터베이스 연동
   - SQLAlchemy 모델 정의
   - 쿼리 빌더 구현
3. 기본 API 서버
   - FastAPI 엔드포인트
   - 입력 검증

**Phase 2: 품질 향상** (2주)
1. 테스트 커버리지 80% 이상
2. 에러 핸들링 강화
3. 로깅 체계 구축
4. 성능 최적화 (캐싱, 병렬 처리)

**Phase 3: 프로덕션 준비** (2주)
1. Docker 컨테이너화
2. CI/CD 파이프라인
3. 모니터링 (Prometheus, Grafana)
4. 보안 강화 (인증, Rate Limiting)

**Phase 4: 고도화** (지속)
1. 다중 에이전트 전략 (Swarm, Hierarchical)
2. 서브그래프 통합
3. A/B 테스팅 프레임워크
4. 사용자 피드백 루프

### 10.3 기술 부채 및 리팩토링 필요 사항

1. **Mock 에이전트 제거**: 실제 구현으로 대체
2. **프롬프트 관리**: 버전 관리 및 템플릿 엔진 도입
3. **설정 관리**: Pydantic Settings로 마이그레이션
4. **타입 안전성**: mypy strict 모드 적용
5. **문서화**: Docstring 보완, API 문서 자동 생성

### 10.4 참고 자료

**LangGraph 공식 문서**:
- https://langchain-ai.github.io/langgraph/
- Context API: https://langchain-ai.github.io/langgraph/concepts/low_level/#context

**관련 패턴**:
- Multi-Agent Systems
- Agent Orchestration Patterns
- Supervisor Pattern
- DAG-based Workflows

---

## 부록 A: 전체 클래스 및 함수 목록

### Core 레이어

#### config.py
- **Class: Config**
  - `get_database_path(db_name: str) -> Path`
  - `get_checkpoint_path(agent_name: str, session_id: str) -> Path`
  - `get_model_config(model_type: str) -> Dict[str, Any]`
  - `validate() -> bool`
  - `to_dict() -> Dict[str, Any]`

#### context.py
- **TypedDict: AgentContext**
- **TypedDict: SubgraphContext**
- **Functions:**
  - `create_agent_context(user_id: str, session_id: str, **kwargs) -> Dict[str, Any]`
  - `merge_with_config_defaults(context: Dict, config: Any) -> Dict[str, Any]`
  - `create_subgraph_context(parent_context: Dict, parent_agent: str, subgraph_name: str, **kwargs) -> Dict[str, Any]`
  - `extract_api_keys_from_env() -> Dict[str, str]`

#### states.py
- **Functions (Reducers):**
  - `merge_dicts(a: Dict, b: Dict) -> Dict`
  - `append_unique(a: List, b: List) -> List`
- **TypedDict:**
  - `BaseState`
  - `DataCollectionState`
  - `AnalysisState`
  - `RealEstateState`
  - `SupervisorState`
  - `DocumentState`
- **Factory Functions:**
  - `create_real_estate_initial_state(**kwargs) -> Dict`
  - `create_supervisor_initial_state(**kwargs) -> Dict`
  - `merge_state_updates(*updates: Dict) -> Dict`
  - `get_state_summary(state: Dict) -> Dict`

#### base_agent.py
- **Class: BaseAgent** (ABC)
  - `__init__(agent_name: str, checkpoint_dir: Optional[str])`
  - Abstract:
    - `_get_state_schema() -> Type`
    - `_build_graph()`
    - `async _validate_input(input_data: Dict) -> bool`
  - Protected:
    - `_create_initial_state(input_data: Dict) -> Dict`
    - `_create_context(input_data: Dict) -> AgentContext`
    - `_create_mock_runtime(state: Dict) -> MockRuntime`
    - `_wrap_node_with_runtime(node_func: Callable) -> Callable`
  - Public:
    - `async execute(input_data: Dict, config: Optional[Dict]) -> Dict`
    - `async get_state(thread_id: str) -> Optional[Dict]`
    - `async update_state(thread_id: str, state_update: Dict, context: Optional[AgentContext]) -> bool`
    - `@staticmethod create_partial_update(**kwargs) -> Dict`
    - `async test_node(node_name: str, test_state: Dict, test_context: Optional[Dict]) -> Dict`
    - `validate_state_schema(state: Dict) -> tuple[bool, List[str]]`

#### checkpointer.py
- **Functions:**
  - `get_checkpointer(checkpoint_path: str, async_mode: bool) -> Optional[Checkpointer]`
  - `async cleanup_old_checkpoints(checkpoint_dir: Path, keep_last: int) -> int`

### Supervisor 레이어

#### supervisor.py
- **Class: RealEstateSupervisor(BaseAgent)**
  - `__init__(agent_name: str, checkpoint_dir: Optional[str], max_retries: int)`
  - `_get_state_schema() -> Type`
  - `_should_retry(state: Dict) -> Literal["retry", "end"]`
  - `_build_graph()`
  - `async _validate_input(input_data: Dict) -> bool`
  - `_create_initial_state(input_data: Dict) -> Dict`
  - `async process_query(query: str, user_id: str, session_id: str, config: Optional[Dict]) -> Dict`
- **Functions:**
  - `async run_supervisor_test(query: str) -> Dict`

#### intent_analyzer.py
- **Functions:**
  - `async call_llm_for_intent(query: str, api_key: str) -> Dict`
  - `async analyze_intent_node(state: Dict, runtime: Runtime) -> Dict`

#### plan_builder.py
- **Functions:**
  - `build_plan_rule_based(intent: Dict) -> Dict`
  - `async call_llm_for_planning(intent: Dict, api_key: str) -> Dict`
  - `async build_plan_node(state: Dict, runtime: Runtime) -> Dict`

#### execution_coordinator.py
- **Functions:**
  - `get_agent(agent_name: str) -> Agent`
  - `async execute_agent(agent_config: Dict, ctx: Dict) -> tuple[str, Dict]`
  - `async execute_sequential(agents: List[Dict], ctx: Dict) -> Dict`
  - `async execute_parallel(agents: List[Dict], ctx: Dict) -> Dict`
  - `async execute_dag(agents: List[Dict], ctx: Dict) -> Dict`
  - `async execute_agents_node(state: Dict, runtime: Runtime) -> Dict`

#### result_evaluator.py
- **Functions:**
  - `evaluate_quality_rule_based(agent_results: Dict) -> Dict`
  - `async call_llm_for_evaluation(agent_results: Dict, api_key: str) -> Dict`
  - `format_response_simple(query: str, agent_results: Dict) -> Dict`
  - `async call_llm_for_formatting(query: str, agent_results: Dict, api_key: str) -> Dict`
  - `async evaluate_results_node(state: Dict, runtime: Runtime) -> Dict`

#### prompts.py
- **Constants:**
  - `INTENT_ANALYSIS_PROMPT`
  - `PLAN_BUILDING_PROMPT`
  - `EVALUATION_PROMPT`
  - `RESPONSE_FORMATTING_PROMPT`
- **Functions:**
  - `get_intent_analysis_prompt(query: str) -> str`
  - `get_plan_building_prompt(intent: Dict) -> str`
  - `get_evaluation_prompt(agent_results: Dict) -> str`
  - `get_response_formatting_prompt(query: str, agent_results: Dict) -> str`

---

## 부록 B: 상태 전이 다이어그램

```
SupervisorState 전이:

[초기화]
status: pending
execution_step: initializing
    ↓
[의도 분석]
status: processing
execution_step: planning
intent: {...}
    ↓
[계획 수립]
execution_step: executing_agents
execution_plan: {...}
    ↓
[에이전트 실행]
execution_step: evaluating
agent_results: {...}
    ↓
[결과 평가]
evaluation: {...}
    ↓
  [needs_retry?]
    ├─ Yes → execution_step: executing_agents (재실행)
    └─ No →
        status: completed
        execution_step: finished
        final_output: {...}
        end_time: "..."
```

---

## 부록 C: 에러 처리 매트릭스

| 에러 타입 | 발생 위치 | 처리 전략 | 재시도 여부 |
|---------|---------|---------|----------|
| API Key 누락 | intent_analyzer, plan_builder, result_evaluator | 규칙 기반 폴백 | No |
| LLM API 호출 실패 | 모든 LLM 호출 | 예외 로깅 + 규칙 기반 폴백 | Yes (최대 3회) |
| JSON 파싱 실패 | LLM 응답 파싱 | 기본값 반환 또는 폴백 | No |
| 에이전트 타임아웃 | execute_agent | 에러 결과 반환 | Yes (evaluation 단계) |
| 데이터베이스 연결 실패 | (미구현) | 에러 반환 | Yes |
| 체크포인트 저장 실패 | execute | 경고 로그 + 계속 진행 | No |
| 입력 검증 실패 | _validate_input | 에러 반환 (즉시 종료) | No |
| 워크플로우 미초기화 | execute | 에러 반환 (즉시 종료) | No |

---

**보고서 작성 완료**

이 보고서는 LangGraph 0.6.7 기반 부동산 챗봇 시스템의 전체 아키텍처, 구현 상태, 고도화 방안을 상세히 분석했습니다. 각 클래스, 함수, 상태, 컨텍스트, 설정을 라인 번호와 함께 문서화하여 향후 개발 및 유지보수에 활용할 수 있습니다.