# Cleanup Analysis - 불필요한 코드 정리 계획

## 1. states.py에서 삭제할 항목

### 미사용 리듀서 함수
- `append_with_timestamp()` - 사용처 없음
- `keep_max()` - 사용처 없음
- `keep_min()` - 사용처 없음
- `increment_counter()` - 사용처 없음

### 미사용 State 클래스
- `SearchState` - search_agent 미구현
- `OrchestratorState` - orchestrator 미구현
- `DataCollectionState` - 서브그래프 미구현
- `AnalysisState` - 서브그래프 미구현

### SalesState의 미사용 필드
- `raw_data` - 수집된 데이터 사용 안함
- `recommendations` - 추천사항 생성 안함
- `max_value`, `min_value`, `total_processed` - 메트릭 추적 안함

## 2. context.py에서 삭제할 항목

### 미사용 Context 클래스
- `SubgraphContext` - 서브그래프 미구현
- `SupervisorContext` - 오케스트레이터 미구현

### AgentContext의 미사용 필드
- `auth_token` - 인증 시스템 미사용
- `permissions` - 권한 시스템 미사용
- `timezone` - 시간대 설정 미사용
- `preferences` - 사용자 선호 미사용
- `model_overrides` - 모델 오버라이드 미사용
- `feature_flags` - 기능 플래그 오버라이드 미사용
- `intent_result` - 의도 분석 미사용
- `supervisor_hints` - 수퍼바이저 힌트 미사용
- `parent_context` - 부모 컨텍스트 미사용
- `db_connections` - DB 연결 문자열 미사용
- `db_credentials` - DB 자격증명 미사용

### 미사용 헬퍼 함수
- `create_subgraph_context()` - 서브그래프 미구현
- `create_supervisor_context()` - 오케스트레이터 미구현

## 3. config.py에서 삭제할 항목

### 미사용 경로
- `MODEL_DIR` - 모델 파일 경로 사용 안함

### 미사용 데이터베이스
- `DATABASES["compliance"]` - compliance 에이전트 미구현

### 미사용 모델 설정
- `DEFAULT_MODELS["execution"]` - 실행 모델 미사용
- `DEFAULT_MODELS["response"]` - 응답 모델 미사용
- `DEFAULT_MODELS["analysis"]` - 분석 모델 미사용

### 미사용 타임아웃
- `TIMEOUTS["subgraph"]` - 서브그래프 타임아웃 미사용
- `TIMEOUTS["tool"]` - 도구 타임아웃 미사용
- `TIMEOUTS["database"]` - DB 타임아웃 미사용
- `TIMEOUTS["total"]` - 전체 타임아웃 미사용

### EXECUTION 설정 대부분
- `enable_parallel` - 병렬 실행 미사용
- `enable_caching` - 캐싱 미사용
- `checkpoint_interval` - 체크포인트 간격 미사용
- `cache_ttl` - 캐시 TTL 미사용
- `stream_mode` - 스트림 모드 미사용

### FEATURES 설정 대부분
- `enable_semantic_search` - 의미 검색 미사용
- `enable_reranking` - 재순위 미사용
- `enable_memory_store` - 메모리 저장 미사용
- `enable_tool_validation` - 도구 검증 미사용
- `enable_error_recovery` - 오류 복구 미사용

## 4. sales_analytics_agent.py에서 정리할 항목

### Mock 메서드
- `_invoke_subgraph()` - 실제 구현 없는 Mock
- `_execute_sql()` - 실제 DB 연결 없는 Mock

## 정리 우선순위

### 🔴 즉시 삭제 (안전)
1. 미사용 State 클래스들
2. 미사용 Context 클래스들
3. 미사용 리듀서 함수들
4. 미사용 헬퍼 함수들

### 🟡 신중하게 삭제
1. Config의 미사용 설정들 (나중에 필요할 수 있음)
2. AgentContext의 일부 필드들 (확장성 고려)

### 🟢 유지
1. 기본 구조와 패턴
2. 확장 가능성이 있는 필드들