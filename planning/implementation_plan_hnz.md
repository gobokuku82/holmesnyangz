# 부동산 AI 앱 구현 계획서

## 📅 프로젝트 개요

### 프로젝트명: Smart Real Estate AI Assistant
- **기술 스택**: LangGraph 0.6.6, FastAPI, React, ChromaDB
- **개발 기간**: 8주
- **팀 구성**: 백엔드 2명, 프론트엔드 2명, AI 엔지니어 1명

## 🎯 Phase 1: 기반 구축 (1-2주)

### Week 1: 환경 설정 및 기본 구조
```
Day 1-2: 프로젝트 초기화
- LangGraph 0.6.6 환경 구성
- 기존 코드베이스 마이그레이션
- 부동산 도메인 모델 정의

Day 3-4: 데이터베이스 설계
- 매물 테이블 (properties)
- 거래 테이블 (transactions)
- 시세 테이블 (market_prices)
- 고객 테이블 (customers)

Day 5: API 구조 설계
- RESTful API 엔드포인트 정의
- WebSocket 연결 구조
- Progress tracking 시스템
```

### Week 2: 핵심 에이전트 개발
```
Day 1-2: Supervisor Agent
- 의도 파악 로직
- 라우팅 규칙 구현
- 실행 계획 생성

Day 3-4: Property Search Agent
- 검색 로직 구현
- 필터링 기능
- 정렬 알고리즘

Day 5: Price Analysis Agent
- 시세 분석 로직
- 투자 수익률 계산
- 시장 동향 분석
```

## 🏗️ Phase 2: 핵심 기능 구현 (3-4주)

### Week 3: 검색 시스템 구축
```
Day 1-2: 내부 DB 검색
- SQLite 쿼리 최적화
- 인덱싱 전략
- 캐싱 구현

Day 3-4: 외부 API 통합
- 국토부 API 연동
- KB부동산 API 연동
- 네이버 부동산 크롤링

Day 5: ChromaDB 구축
- 임베딩 모델 설정
- 벡터 검색 구현
- 유사 매물 추천
```

### Week 4: 분석 시스템 구축
```
Day 1-2: 가격 분석 도구
- 실거래가 비교
- 적정가 산출
- 가격 추이 분석

Day 3-4: 투자 분석 도구
- ROI 계산기
- 대출 시뮬레이션
- 세금 계산기

Day 5: 리포트 생성
- 분석 보고서 템플릿
- 차트 생성
- PDF 출력
```

## 🎨 Phase 3: 프론트엔드 개발 (5-6주)

### Week 5: React 기본 구조
```
Day 1-2: 프로젝트 설정
- Create React App / Vite
- 라우팅 설정
- 상태 관리 (Redux/Zustand)

Day 3-4: UI 컴포넌트
- Material-UI / Ant Design 설정
- 기본 레이아웃
- 반응형 디자인

Day 5: Progress Bar 구현
- 컴포넌트 개발
- 애니메이션 추가
- 상태 연동
```

### Week 6: 핵심 기능 UI
```
Day 1-2: 검색 인터페이스
- 검색 폼
- 필터 UI
- 결과 리스트

Day 3-4: 상세 페이지
- 매물 상세 정보
- 이미지 갤러리
- 지도 통합

Day 5: 대화 인터페이스
- 채팅 UI
- 메시지 스트리밍
- 파일 업로드
```

## 🔌 Phase 4: 통합 및 최적화 (7-8주)

### Week 7: 시스템 통합
```
Day 1-2: WebSocket 연동
- 실시간 통신 구현
- Progress 업데이트
- 에러 처리

Day 3-4: API 통합
- 백엔드 API 연결
- 인증/인가
- 에러 핸들링

Day 5: 성능 최적화
- 쿼리 최적화
- 캐싱 전략
- 로딩 최적화
```

### Week 8: 테스트 및 배포
```
Day 1-2: 테스트
- 단위 테스트
- 통합 테스트
- E2E 테스트

Day 3-4: 배포 준비
- Docker 컨테이너화
- CI/CD 파이프라인
- 환경 변수 설정

Day 5: 배포 및 모니터링
- 프로덕션 배포
- 모니터링 설정
- 로그 수집
```

## 📊 구현 우선순위

### Critical (Must Have)
1. Property Search Agent - 매물 검색
2. Price Analysis Agent - 가격 분석
3. Progress Bar - 진행 상태 표시
4. WebSocket 통신 - 실시간 업데이트
5. 기본 UI - 검색, 리스트, 상세

### High (Should Have)
1. Document Generator - 계약서 생성
2. Legal Compliance - 법률 검토
3. 투자 분석 도구
4. 지도 통합
5. 이미지 갤러리

### Medium (Nice to Have)
1. Customer Service Agent - 고객 상담
2. 추천 시스템
3. 알림 기능
4. 즐겨찾기
5. 비교 기능

### Low (Future)
1. AR/VR 뷰어
2. AI 가격 예측
3. 커뮤니티 기능
4. 중개사 매칭
5. 금융 상품 연계

## 🛠️ 기술 상세 구현

### 1. StateGraph 구조 (전체 기능 활용)
```python
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from typing import Annotated, TypedDict

# State 정의 (MessagesState 상속)
class RealEstateState(MessagesState):
    current_agent: str
    property_data: Dict[str, Any]
    search_results: List[Dict]
    analysis_results: Dict[str, Any]
    execution_plan: List[str]
    current_step: int
    progress: Annotated[List[Dict], add_progress]  # 리듀서 사용

# 그래프 구성
graph = StateGraph(RealEstateState)

# 노드 추가
graph.add_node("supervisor", supervisor_agent)
graph.add_node("property_search", property_search_agent)
graph.add_node("price_analysis", price_analysis_agent)
graph.add_node("document_generator", document_agent)
graph.add_node("legal_compliance", compliance_agent)
graph.add_node("tools", tool_node)  # ToolNode 사용

# 엣지 설정
graph.add_edge(START, "supervisor")

# 조건부 라우팅
graph.add_conditional_edges(
    "supervisor",
    route_by_intent,
    {
        "search": "property_search",
        "analyze": "price_analysis",
        "document": "document_generator",
        "tools": "tools",
        "end": END
    }
)

# 도구 실행 조건
graph.add_conditional_edges(
    "property_search",
    tools_condition,  # prebuilt 함수 사용
    {"tools": "tools", END: END}
)

# 자동 라우팅
graph.add_edge("property_search", "price_analysis")
graph.add_edge("document_generator", "legal_compliance")

# 컴파일 with 체크포인터
checkpointer = SqliteSaver.from_conn_string("sqlite:///real_estate.db")
app = graph.compile(checkpointer=checkpointer)
```

### 2. Progress Tracking
```python
async def update_progress(state: RealEstateState, websocket: WebSocket):
    progress_data = {
        "type": "progress_update",
        "current_step": state.current_step,
        "total_steps": len(state.execution_plan),
        "percentage": (state.current_step / len(state.execution_plan)) * 100,
        "agent": state.current_agent,
        "message": f"Processing: {state.current_agent}"
    }
    await websocket.send_json(progress_data)
```

### 3. React Progress Component
```jsx
const ProgressBar = ({ steps, currentStep, percentage }) => {
    return (
        <div className="progress-container">
            <LinearProgress variant="determinate" value={percentage} />
            <Stepper activeStep={currentStep}>
                {steps.map((step) => (
                    <Step key={step}>
                        <StepLabel>{step}</StepLabel>
                    </Step>
                ))}
            </Stepper>
        </div>
    );
};
```

## 📈 성공 지표 (KPIs)

### 기술 지표
- API 응답 시간: < 500ms
- 검색 정확도: > 90%
- 시스템 가용성: > 99.9%
- 동시 사용자: > 1000명

### 비즈니스 지표
- 사용자 만족도: > 4.5/5
- 검색 → 문의 전환율: > 20%
- 평균 세션 시간: > 10분
- 재방문율: > 60%

## 🚀 마일스톤

### M1 (Week 2): 기본 구조 완성
- LangGraph 그래프 구축
- 핵심 에이전트 구현
- 데이터베이스 설계

### M2 (Week 4): 백엔드 MVP
- 검색 기능 완성
- 분석 기능 완성
- API 엔드포인트 구현

### M3 (Week 6): 프론트엔드 MVP
- UI 컴포넌트 완성
- Progress Bar 구현
- WebSocket 연동

### M4 (Week 8): 프로덕션 준비
- 통합 테스트 완료
- 성능 최적화 완료
- 배포 및 모니터링

## 🔄 리스크 관리

### 기술적 리스크
- **리스크**: LangGraph 0.6.6 문서 부족
- **대응**: 기존 코드 참조, 커뮤니티 활용

### 데이터 리스크
- **리스크**: 외부 API 의존성
- **대응**: 캐싱, fallback 메커니즘

### 일정 리스크
- **리스크**: 복잡도 증가
- **대응**: MVP 우선, 단계적 구현

## 📚 참고 자료

### 필수 문서
- LangGraph 0.6.6 공식 문서
- 국토부 API 가이드
- React 공식 문서
- WebSocket 구현 가이드

### 도메인 지식
- 부동산 용어 사전
- 중개업법 가이드
- 투자 분석 방법론

## ✅ 일일 체크리스트

### 개발자
- [ ] 코드 리뷰 완료
- [ ] 테스트 작성
- [ ] 문서 업데이트
- [ ] Progress 로깅

### PM
- [ ] 일정 확인
- [ ] 리스크 체크
- [ ] 팀 미팅
- [ ] 진행 상황 보고