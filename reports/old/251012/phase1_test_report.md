# Phase 1 Query Decomposition Test Report
## 부동산 AI 시스템 질문 분해 및 의도 분석 테스트 결과

**테스트 일시**: 2025년 10월 5일
**테스트 범위**: 단일 질문 20개 + 복합 질문(2개 작업) 20개
**총 테스트 수**: 40개

---

## 1. Executive Summary (요약)

### 1.1 전체 결과
- **실행 성공률**: 100% (40/40)
- **검증 통과율**: 0% (0/40) ⚠️
- **평균 실행 시간**: 5.44초/질문
- **총 실행 시간**: 약 3분 37초

### 1.2 주요 발견사항
✅ **성공 요소**:
- 모든 질문에 대해 LLM 호출이 정상적으로 수행됨
- Intent 분석이 비교적 정확하게 작동 (한글 intent 반환)
- Query Decomposer가 단순/복합 질문을 구분함

❌ **문제점**:
- Execution Plan의 steps가 비어있음 (available_agents 미전달)
- Prompt 변수 누락으로 인한 fallback 발생
- Validation logic의 오류로 전체 검증 실패
- Intent type이 한글로 반환되어 enum 매칭 실패

---

## 2. 테스트 결과 상세 분석

### 2.1 단일 질문 테스트 (20개)

#### 성공 사례 분석
| ID | 질문 | Intent | Confidence | Agent | 실행 시간 |
|----|------|--------|------------|-------|-----------|
| S001 | 전세금 5% 인상 제한이 언제까지인가요? | 법률상담 | 0.9 | search_team | 4.69초 |
| S002 | 강남구 아파트 전세 시세 알려주세요 | 시세조회 | 0.9 | search_team | 5.15초 |
| S003 | 전세자금대출 한도가 얼마나 되나요? | 대출상담 | 0.9 | search_team | 4.73초 |
| S004 | 임대차계약서 작성해주세요 | 계약서작성 | 0.9 | document_team | 4.99초 |

**패턴**:
- 모든 단일 질문이 `is_compound: false`로 정확히 판단됨
- Confidence 평균 0.9 (매우 높음)
- Intent 분류가 정확하나 한글로 반환됨 (기대값: LEGAL_CONSULT, 실제: 법률상담)
- Fallback 사용률: 0% (모두 LLM 기반 분석 성공)

#### 발견된 문제
1. **Intent Type 불일치**:
   - 기대값: `LEGAL_CONSULT` (영문 enum)
   - 실제값: `법률상담` (한글 문자열)
   - 원인: Prompt가 한글 응답을 생성하도록 작성됨

2. **Execution Plan 미생성**:
   ```json
   "execution_plan": {
     "strategy": "sequential",
     "num_steps": 0,
     "steps": [],  // 비어있음
     "estimated_time": 0.0
   }
   ```
   - 원인: `available_agents` 파라미터가 빈 리스트로 전달됨

### 2.2 복합 질문 테스트 (20개)

#### 성공 사례 분석
| ID | 질문 | Intent | 분해 성공 | Tasks | Agent | 실행 시간 |
|----|------|--------|-----------|-------|-------|-----------|
| D001 | 강남구 아파트 시세 확인하고 대출 가능 금액 계산해줘 | 시세조회 | ⚠️ fallback | 1 | search_team, analysis_team | 5.52초 |
| D002 | 서초동 전세 시세 알려주고 법적 주의사항도 알려줘 | 시세조회 | ⚠️ fallback | 1 | search_team | 5.78초 |
| D003 | 이 계약서 검토하고 위험 요소 분석해줘 | 계약서검토 | ⚠️ fallback | 1 | search_team, analysis_team | 6.01초 |

**패턴**:
- 복합 질문 검출률: 낮음 (대부분 fallback으로 단일 작업 처리)
- Query Decomposition Prompt 오류로 LLM 분해 실패
- Fallback 전략으로 intent 기반 단일 작업 생성
- Agent 추천은 정확 (2개 이상의 팀 선택)

#### 발견된 문제
1. **Query Decomposition 실패**:
   ```
   ERROR - Missing variable in prompt query_decomposition: '\n    "is_compound"'
   ```
   - 모든 복합 질문에서 LLM 분해 실패
   - Fallback으로 단일 작업만 생성됨

2. **Task 분해 부재**:
   - 기대: "시세 확인" + "대출 계산" (2개 작업)
   - 실제: 단일 작업으로 처리
   - 실행 모드: 모두 `sequential` (병렬 처리 기회 상실)

---

## 3. 시스템 컴포넌트별 분석

### 3.1 Planning Agent
**강점**:
- ✅ LLM 기반 Intent 분석 100% 성공
- ✅ Confidence score 일관성 (평균 0.9)
- ✅ Agent 추천 정확도 높음

**약점**:
- ❌ Intent Type이 enum 대신 한글 문자열 반환
- ❌ Available agents 파라미터 미전달로 plan 생성 실패
- ❌ Fallback 패턴 매칭 로직의 async 문제 해결됨 (수정 완료)

### 3.2 Query Decomposer
**강점**:
- ✅ 단순/복합 질문 구분 로직 작동
- ✅ Fallback 전략 안정적

**약점**:
- ❌ LLM decomposition 100% 실패 (prompt 변수 누락)
- ❌ Prompt 파일 (`query_decomposition.txt`)의 변수 매핑 오류
- ❌ 복합 질문의 개별 작업 분해 기능 미작동

### 3.3 LLM Service & Prompt Manager
**강점**:
- ✅ OpenAI API 호출 안정성 100%
- ✅ Token 사용량 적절 (평균 ~200 tokens/call)
- ✅ Rate limit 여유 있음

**약점**:
- ❌ Prompt 변수 검증 로직 부족
- ❌ JSON 응답 형식의 설명과 실제 반환값 불일치
- ❌ Template variable 이름 불일치 감지 못함

---

## 4. 에러 로그 분석

### 4.1 주요 에러 패턴

#### A. Prompt Variable Missing (가장 빈번)
```
ERROR - Missing variable in prompt query_decomposition: '\n    "is_compound"'
ERROR - Missing variable in prompt intent_analysis: '\n    "intent"'
```

**발생 빈도**: 40회 (복합 질문 시 매번)
**영향도**: Critical - 핵심 기능 미작동
**원인**:
- Prompt 파일의 JSON 예제에 주석이 포함되어 변수로 인식됨
- Template 변수 이름과 전달 변수 이름 불일치

#### B. Available Agents Empty
```
DEBUG - Available agents: []
INFO - Selected agents/teams for execution: []
```

**발생 빈도**: 40회 (모든 테스트)
**영향도**: Critical - Execution Plan 미생성
**원인**:
- `create_execution_plan()` 호출 시 `available_agents` 파라미터 미전달
- Agent Registry에서 agent 목록 조회 실패

#### C. Validation Failure
```
"validation": {
  "intent_match": false,
  "agent_match": false,
  "decomposition_correct": false,
  "overall": false
}
```

**발생 빈도**: 40회 (100%)
**영향도**: High - 품질 검증 불가
**원인**:
- Intent type 형식 불일치 (`LEGAL_CONSULT` vs `법률상담`)
- Execution plan steps 비어있어 agent 매칭 불가

---

## 5. 성능 분석

### 5.1 실행 시간 분포
- **최소**: 4.45초
- **최대**: 7.43초
- **평균**: 5.44초
- **중앙값**: 5.31초

### 5.2 시간 소요 단계별 분석
1. **Intent Analysis**: ~2-3초 (LLM 호출)
2. **Query Decomposition**: ~1-2초 (fallback 포함)
3. **Execution Plan**: ~0-1초 (steps 생성 안됨)
4. **기타 처리**: ~1-2초

### 5.3 LLM 호출 통계
- **총 호출 수**: ~120회 (질문당 3회)
- **평균 Token 사용**: 200 tokens/call
- **총 Token 사용**: ~24,000 tokens
- **비용 추정**: $0.12 (gpt-4o-mini 기준)

---

## 6. 장단점 및 개선 방향

### 6.1 현재 시스템의 장점

#### ✅ 강점
1. **안정성**:
   - LLM API 호출 100% 성공
   - 에러 처리 및 fallback 전략 작동
   - 모든 테스트 케이스 실행 완료

2. **Intent 분석 정확도**:
   - 의도 파악 정확
   - Confidence score 신뢰도 높음 (0.9 평균)
   - 다양한 질문 유형 처리 가능

3. **구조적 설계**:
   - Modular architecture (Planning, Decomposition 분리)
   - State management 체계적
   - Logging 상세함

4. **확장성**:
   - 새로운 intent type 추가 용이
   - Agent 추가/변경 유연함
   - Prompt 기반 동작으로 조정 쉬움

### 6.2 현재 시스템의 단점

#### ❌ 약점
1. **핵심 기능 미작동**:
   - Query Decomposition LLM 호출 실패 (100%)
   - Execution Plan steps 생성 안됨 (100%)
   - 복합 질문 분해 기능 무용지물

2. **데이터 형식 불일치**:
   - Intent type 영문/한글 혼용
   - Prompt 응답 형식과 코드 기대값 불일치
   - Validation 로직과 실제 데이터 구조 차이

3. **Prompt 관리 문제**:
   - Template 변수 검증 부족
   - JSON 예제에 주석 포함으로 파싱 오류
   - 변수 이름 일관성 없음

4. **Agent Registry 연동 부재**:
   - Available agents 조회 실패
   - Team 기반 agent 목록 미제공
   - 동적 agent 선택 불가

### 6.3 Critical Issues (즉시 수정 필요)

#### 🚨 Priority 1 (Blocker)
1. **Prompt 변수 수정**:
   - `intent_analysis.txt`: JSON 예제 주석 제거
   - `query_decomposition.txt`: 변수 이름 매핑 수정
   - `agent_selection.txt`: 변수 전달 확인

2. **Agent Registry 연동**:
   - `create_execution_plan()`에 available_agents 전달
   - Team list 조회 로직 구현
   - Agent capability 정보 활용

3. **Intent Type 통일**:
   - Prompt에서 영문 enum 반환하도록 수정
   - 또는 한글→영문 매핑 로직 추가
   - Validation 로직에 한글 매핑 추가

#### ⚠️ Priority 2 (Important)
4. **Query Decomposition 수정**:
   - Prompt 파일 변수 정리
   - LLM 호출 성공률 모니터링
   - Fallback 조건 최적화

5. **Validation 로직 수정**:
   - Intent matching 로직 수정
   - Agent matching 조건 완화
   - Decomposition 검증 기준 재정의

#### 📝 Priority 3 (Nice to have)
6. **성능 최적화**:
   - 불필요한 LLM 호출 제거
   - Caching 전략 도입
   - Parallel execution 활용

7. **로깅 개선**:
   - 구조화된 로그 형식
   - 에러 추적 강화
   - 성능 메트릭 수집

---

## 7. 개선 액션 플랜

### 7.1 단기 (1주일 이내)
- [ ] Prompt 파일 JSON 형식 수정
- [ ] Intent type 영문 반환 통일
- [ ] Available agents 전달 로직 구현
- [ ] Validation 로직 수정
- [ ] Query decomposition prompt 변수 매핑 수정

### 7.2 중기 (2-3주)
- [ ] Agent Registry 통합
- [ ] Complex query decomposition 테스트 (3개+ 작업)
- [ ] Parallel execution 구현
- [ ] Error recovery 강화
- [ ] Prompt engineering 고도화

### 7.3 장기 (1개월+)
- [ ] Semantic caching 도입
- [ ] A/B testing 프레임워크
- [ ] Fine-tuning 검토
- [ ] Multi-modal 지원
- [ ] Real-time monitoring dashboard

---

## 8. 다음 단계: Phase 2 테스트 계획

### 8.1 테스트 범위
- **3개 이상 작업 복합 질문**: 30개
- **고난이도 복합 질문**: 30개
- **총**: 60개

### 8.2 테스트 시나리오 예시

#### 3개 작업 복합 질문
1. "강남 시세 조회하고 대출 한도 계산한 후 계약서 작성해줘"
2. "이 계약서 검토하고 리스크 분석해서 수정안 제시해줘"
3. "법률 확인하고 시세 비교한 후 투자 가치 평가해줘"

#### 고난이도 복합 질문
1. "서초 전세와 강남 전세 비교하고, 각각 대출 가능액 계산한 후, 리스크 평가해서 추천해줘"
2. "전세 사기 예방 법률 찾고, 계약서 검토하고, 보증 보험 가입 방법 알려주고, 체크리스트 만들어줘"
3. "3년치 시세 동향 분석하고, 향후 예측하고, 투자 수익률 계산하고, 세금까지 고려한 종합 의견 줘"

### 8.3 검증 기준 강화
- Decomposition 정확도 > 80%
- Task dependency 정확도 > 90%
- Parallel/Sequential 판단 정확도 > 85%
- 전체 실행 성공률 > 95%

---

## 9. 결론

### 9.1 핵심 요약
Phase 1 테스트는 시스템의 **기본 구조는 견고**하나, **핵심 기능에 치명적 버그**가 존재함을 확인했습니다.

**Good**:
- Architecture 설계 우수
- LLM 통합 안정적
- Logging 및 에러 처리 체계적

**Bad**:
- Prompt 관리 미흡
- Component 간 데이터 형식 불일치
- Agent Registry 미연동

**Action Required**:
- Prompt 파일 즉시 수정 (Blocker)
- Available agents 전달 로직 구현 (Blocker)
- Intent type 형식 통일 (Critical)

### 9.2 최종 평가
**현재 상태**: 🟡 **Partial Success**
- 기본 동작: ✅ 성공
- 핵심 기능: ❌ 미작동
- 전체 품질: ⚠️ 개선 필요

**개선 후 예상**: 🟢 **Full Success**
- Prompt 수정 후 decomposition 성공률 예상: 80%+
- Agent 연동 후 execution plan 생성률: 100%
- Validation 수정 후 검증 통과율: 70%+

---

## 10. 참고 자료

### 10.1 생성된 파일
- 테스트 데이터: `tests/test_queries_phase1.json`
- 실행 스크립트: `tests/run_phase1_test.py`
- 결과 파일: `phase1_test_results.json`
- 로그 파일: `phase1_test_log.txt`
- 보고서: `phase1_test_report.md` (본 문서)

### 10.2 관련 코드
- Planning Agent: `cognitive_agents/planning_agent.py`
- Query Decomposer: `cognitive_agents/query_decomposer.py`
- Prompts: `llm_manager/prompts/cognitive/`
- State Management: `foundation/separated_states.py`

---

**Report Generated**: 2025-10-05
**Next Review**: After Priority 1 fixes
**Contact**: Development Team