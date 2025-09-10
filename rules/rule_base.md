# 부동산 AI 앱 개발 규칙 (LangGraph 0.6.6)

## 🏗️ 핵심 아키텍처 규칙

### 1. LangGraph 0.6.6 필수 패턴
```python
# ✅ 반드시 사용
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import MessagesState
from langgraph.checkpoint.memory import MemorySaver

# ❌ 절대 사용 금지 (구버전 패턴)
from langgraph.graph import Graph, MessageGraph  # OLD
```

### 2. 에이전트 구조
- **필수 에이전트**: supervisor, property_search, price_analysis, document_generator, legal_compliance, customer_service
- **각 에이전트는 반드시 dict 반환**
- **에이전트 간 직접 라우팅 우선**

## 🎯 LangGraph 0.6.6 핵심 사용 패턴

### 1. Graph 구성 요소
```python
# 그래프 생성 - StateGraph만 사용 (Graph, MessageGraph는 deprecated)
graph = StateGraph(RealEstateState)

# 노드 추가
graph.add_node("agent_name", agent_function)

# 엣지 추가 (직접 연결)
graph.add_edge("source_node", "target_node")
graph.add_edge(START, "supervisor")  # 시작점
graph.add_edge("final_agent", END)   # 종료점

# 조건부 엣지 (라우팅)
graph.add_conditional_edges(
    "supervisor",
    routing_function,  # 라우팅 함수
    {
        "property_search": "property_search_agent",
        "price_analysis": "price_analysis_agent",
        "end": END
    }
)

# 컴파일 (체크포인터 포함)
checkpointer = MemorySaver()  # 개발용
# checkpointer = SqliteSaver.from_conn_string("sqlite:///checkpoints.db")  # 프로덕션용
app = graph.compile(checkpointer=checkpointer)
```

### 2. 사용 가능한 LangGraph 기능들
- **StateGraph**: 메인 그래프 클래스 ✅
- **START, END**: 그래프 시작/종료 상수 ✅
- **add_messages**: 메시지 리듀서 함수 ✅
- **MessagesState**: 메시지 상태 베이스 클래스 ✅
- **ToolNode**: 도구 실행 노드 ✅
- **tools_condition**: 도구 실행 조건 함수 ✅
- **MemorySaver/SqliteSaver**: 체크포인터 ✅
- **astream, ainvoke**: 비동기 실행 메서드 ✅
- **astream_events**: 이벤트 스트리밍 (v2) ✅

### 1. 데이터 구조
- **매물 정보**: 위치, 가격, 면적, 층수, 방수, 준공년도, 특징
- **시세 정보**: 실거래가, 호가, 전세가율, 갭투자 정보
- **법규 정보**: 용도지역, 건폐율, 용적률, 재건축/재개발 정보
- **고객 정보**: 예산, 선호지역, 투자목적, 거주목적

### 2. 검색 우선순위
1. **1순위**: 내부 DB (등록 매물, 실거래가)
2. **2순위**: 부동산 API (국토부, KB, 네이버)
3. **3순위**: ChromaDB (과거 검색 결과, 시장 분석)

### 3. 컴플라이언스 체크
- **중개법 준수**: 허위매물, 과장광고 금지
- **개인정보보호**: 매도인/매수인 정보 보호
- **계약서 검증**: 특약사항, 권리관계 확인

## 📊 Progress Bar 구현 규칙

### 1. 상태 추적
```python
class RealEstateState(MessagesState):
    execution_plan: List[str]  # 실행 계획
    current_step: int  # 현재 단계
    total_steps: int  # 전체 단계
    progress_percentage: float  # 진행률
    step_details: Dict[str, Any]  # 단계별 상세
```

### 2. WebSocket 이벤트
```javascript
// 프론트엔드 이벤트 타입
{
    type: "progress_update",
    current_step: 2,
    total_steps: 5,
    percentage: 40,
    agent_name: "property_search",
    message: "매물 검색 중..."
}
```

### 3. 진행률 계산
- **단순 작업**: 각 에이전트 20% 할당
- **복합 작업**: 가중치 기반 (검색 30%, 분석 40%, 문서 20%, 검증 10%)

## 🔧 도구(Tools) 구현 규칙

### 1. 부동산 특화 도구
```python
@tool
def search_properties(location: str, price_range: Tuple[int, int]) -> str:
    """매물 검색 도구"""
    
@tool
def analyze_market_price(property_id: str) -> str:
    """시세 분석 도구"""
    
@tool
def check_legal_status(property_id: str) -> str:
    """법적 상태 확인 도구"""
    
@tool
def calculate_investment_return(property_data: Dict) -> str:
    """투자 수익률 계산 도구"""
```

### 2. API 통합
- **국토부 API**: 실거래가, 건축물대장
- **KB부동산 API**: 시세, 전망
- **네이버 부동산 API**: 매물 정보
- **카카오맵 API**: 위치, 주변 정보

## 🎯 프론트엔드 연동 규칙

### 1. React 컴포넌트 구조
```
/components
  /PropertySearch    # 매물 검색
  /PropertyDetail    # 매물 상세
  /PriceAnalysis     # 가격 분석
  /ProgressBar       # 진행 상태
  /ChatInterface     # 대화 인터페이스
```

### 2. 상태 관리
- **Redux/Zustand**: 전역 상태 관리
- **React Query**: API 캐싱
- **WebSocket**: 실시간 업데이트

### 3. Progress Bar 렌더링
```jsx
<ProgressBar 
    steps={executionPlan}
    currentStep={currentStep}
    percentage={progressPercentage}
    showDetails={true}
/>
```

## 🔄 라우팅 규칙

### 1. 자동 라우팅 케이스
- 매물 검색 → 가격 분석 (자동)
- 문서 생성 → 법률 검토 (자동)
- 고객 상담 → 매물 추천 (자동)

### 2. 조건부 라우팅
```python
def route_by_intent(state: RealEstateState) -> str:
    if "매물" in query or "검색" in query:
        return "property_search"
    elif "가격" in query or "시세" in query:
        return "price_analysis"
    elif "계약" in query or "문서" in query:
        return "document_generator"
    return "customer_service"
```

## 🚦 에러 처리 규칙

### 1. 재시도 전략
- **API 실패**: 3회 재시도, exponential backoff
- **검색 실패**: 대체 소스 사용
- **분석 실패**: 캐시된 데이터 사용

### 2. Fallback 메커니즘
```python
try:
    result = await search_properties_api()
except APIError:
    result = await search_cached_properties()
finally:
    update_progress(step_completed=True)
```

## 📈 성능 최적화 규칙

### 1. 병렬 처리
- **동시 검색**: 여러 지역 동시 검색
- **배치 분석**: 여러 매물 동시 분석
- **제한**: 최대 3개 동시 실행

### 2. 캐싱 전략
- **검색 결과**: 1시간 캐싱
- **시세 정보**: 24시간 캐싱
- **법규 정보**: 7일 캐싱

## 🔐 보안 규칙

### 1. 개인정보 처리
- **마스킹**: 전화번호, 주민번호 자동 마스킹
- **암호화**: 민감 정보 AES-256 암호화
- **접근 제어**: Role-based access control

### 2. API 키 관리
- **환경 변수**: .env 파일 사용
- **시크릿 관리**: AWS Secrets Manager 권장
- **로테이션**: 90일마다 키 로테이션

## 📝 문서화 규칙

### 1. 코드 문서화
- **모든 에이전트**: docstring 필수
- **도구 함수**: 파라미터, 반환값 명시
- **상태 변경**: 변경 사유 기록

### 2. API 문서화
- **OpenAPI 3.0**: 스펙 준수
- **예제 포함**: 각 엔드포인트별 예제
- **에러 코드**: 상세 에러 설명

## ✅ 체크리스트

### 새 기능 개발 시
- [ ] StateGraph 패턴 준수
- [ ] dict 반환 확인
- [ ] Progress 업데이트 구현
- [ ] WebSocket 이벤트 발생
- [ ] 에러 처리 구현
- [ ] 캐싱 전략 적용
- [ ] 보안 검토 완료
- [ ] 테스트 코드 작성
- [ ] 문서화 완료

### 배포 전
- [ ] 모든 API 키 확인
- [ ] 환경 변수 설정
- [ ] 데이터베이스 마이그레이션
- [ ] 로그 설정 확인
- [ ] 모니터링 설정
- [ ] 백업 전략 수립