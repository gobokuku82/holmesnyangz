# LangGraph 0.6.6 고급 기능 및 부동산 앱 확장 가이드

## 🔄 Hand-off / Hand-on 패턴

### 1. Human-in-the-Loop (HITL) 패턴
```python
from langgraph.prebuilt import create_react_agent
from langgraph.graph import interrupt, resume

class RealEstateState(MessagesState):
    human_approval_required: bool
    handoff_to: str  # "human" | "agent" | None
    interrupt_reason: str
    
# 인간 개입이 필요한 시점에 interrupt
def price_negotiation_agent(state: RealEstateState) -> dict:
    proposed_price = state.get("proposed_price")
    
    # 특정 조건에서 인간에게 hand-off
    if proposed_price > 1000000000:  # 10억 이상
        return {
            **state,
            "handoff_to": "human",
            "interrupt_reason": "고액 거래 승인 필요",
            "human_approval_required": True
        }
    
    # 자동 처리
    return process_negotiation(state)

# Interrupt 노드 추가
graph.add_node("human_approval", human_approval_node)
graph.add_conditional_edges(
    "price_negotiation",
    lambda x: "interrupt" if x.get("human_approval_required") else "continue",
    {
        "interrupt": "human_approval",
        "continue": "contract_generation"
    }
)
```

### 2. Agent Hand-off 패턴 (에이전트 간 전환)
```python
# 동적 에이전트 선택
def dynamic_agent_selector(state: RealEstateState) -> str:
    """상황에 따라 최적의 에이전트 선택"""
    
    query_complexity = analyze_complexity(state.get("query"))
    user_profile = state.get("user_profile", {})
    
    # 초보자 → 간단한 에이전트
    if user_profile.get("experience") == "beginner":
        if query_complexity < 3:
            return "simple_search_agent"
        else:
            return "guided_search_agent"  # 가이드 제공
    
    # 전문가 → 고급 에이전트
    elif user_profile.get("experience") == "expert":
        return "advanced_analysis_agent"
    
    # 투자자 → 투자 특화 에이전트
    elif user_profile.get("type") == "investor":
        return "investment_specialist_agent"
    
    return "general_agent"

# 조건부 hand-off
graph.add_conditional_edges(
    "supervisor",
    dynamic_agent_selector,
    {
        "simple_search_agent": "simple_search",
        "guided_search_agent": "guided_search",
        "advanced_analysis_agent": "advanced_analysis",
        "investment_specialist_agent": "investment_specialist",
        "general_agent": "property_search"
    }
)
```

## 🎭 노드 활성/비활성 패턴

### 1. Feature Flag 기반 노드 관리
```python
class FeatureFlags:
    """기능 플래그로 노드 활성화 제어"""
    AI_VALUATION = True  # AI 가치 평가
    VIRTUAL_TOUR = False  # VR 투어 (개발 중)
    MORTGAGE_CALC = True  # 대출 계산기
    INVESTMENT_ANALYSIS = True  # 투자 분석

def conditional_node_activation(state: RealEstateState) -> str:
    """기능 플래그에 따른 노드 활성화"""
    
    requested_feature = state.get("requested_feature")
    
    # 비활성화된 기능 체크
    if requested_feature == "virtual_tour" and not FeatureFlags.VIRTUAL_TOUR:
        return "feature_unavailable"
    
    # 활성화된 기능으로 라우팅
    if requested_feature == "ai_valuation" and FeatureFlags.AI_VALUATION:
        return "ai_valuation_agent"
    
    return "default_agent"
```

### 2. 동적 노드 추가/제거
```python
def build_dynamic_graph(user_tier: str):
    """사용자 등급에 따른 동적 그래프 구성"""
    
    graph = StateGraph(RealEstateState)
    
    # 기본 노드 (모든 사용자)
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("property_search", property_search_agent)
    
    # 프리미엄 사용자 전용 노드
    if user_tier in ["premium", "enterprise"]:
        graph.add_node("ai_valuation", ai_valuation_agent)
        graph.add_node("market_prediction", market_prediction_agent)
        graph.add_node("portfolio_analysis", portfolio_analysis_agent)
    
    # 엔터프라이즈 전용 노드
    if user_tier == "enterprise":
        graph.add_node("bulk_analysis", bulk_analysis_agent)
        graph.add_node("api_integration", api_integration_agent)
        graph.add_node("custom_report", custom_report_agent)
    
    return graph.compile()
```

## 🔀 유동적 노드 관리 방법

### 1. Subgraph 패턴 (서브그래프)
```python
def create_search_subgraph():
    """검색 전용 서브그래프"""
    subgraph = StateGraph(SearchState)
    
    subgraph.add_node("location_search", location_search)
    subgraph.add_node("price_filter", price_filter)
    subgraph.add_node("amenity_filter", amenity_filter)
    subgraph.add_node("ranking", ranking_agent)
    
    # 서브그래프 내부 라우팅
    subgraph.add_edge("location_search", "price_filter")
    subgraph.add_edge("price_filter", "amenity_filter")
    subgraph.add_edge("amenity_filter", "ranking")
    
    return subgraph.compile()

# 메인 그래프에 서브그래프 통합
main_graph = StateGraph(RealEstateState)
search_subgraph = create_search_subgraph()

main_graph.add_node("search_module", search_subgraph)
main_graph.add_edge("supervisor", "search_module")
```

### 2. Plugin 시스템
```python
class AgentPlugin:
    """플러그인 기반 에이전트 시스템"""
    
    def __init__(self):
        self.plugins = {}
    
    def register(self, name: str, agent_func: callable, dependencies: List[str] = None):
        """플러그인 등록"""
        self.plugins[name] = {
            "func": agent_func,
            "dependencies": dependencies or [],
            "enabled": True
        }
    
    def build_graph(self):
        """등록된 플러그인으로 그래프 구성"""
        graph = StateGraph(RealEstateState)
        
        for name, plugin in self.plugins.items():
            if plugin["enabled"]:
                graph.add_node(name, plugin["func"])
                
                # 의존성 기반 엣지 추가
                for dep in plugin["dependencies"]:
                    if dep in self.plugins and self.plugins[dep]["enabled"]:
                        graph.add_edge(dep, name)
        
        return graph

# 플러그인 사용 예시
plugin_system = AgentPlugin()
plugin_system.register("search", search_agent)
plugin_system.register("analysis", analysis_agent, dependencies=["search"])
plugin_system.register("report", report_agent, dependencies=["analysis"])

# 새 플러그인 동적 추가
plugin_system.register("ai_coach", ai_coaching_agent, dependencies=["search"])
```

### 3. Parallel Execution (병렬 실행)
```python
from langgraph.graph import parallel

def parallel_analysis_node(state: RealEstateState) -> dict:
    """여러 분석을 병렬로 실행"""
    
    property_id = state.get("property_id")
    
    # 병렬 실행할 작업들
    tasks = parallel(
        price_analysis=lambda: analyze_price(property_id),
        location_analysis=lambda: analyze_location(property_id),
        investment_analysis=lambda: analyze_investment(property_id),
        legal_check=lambda: check_legal_status(property_id)
    )
    
    results = await tasks.execute()
    
    return {
        **state,
        "analysis_results": results,
        "analysis_complete": True
    }

# 병렬 노드 추가
graph.add_node("parallel_analysis", parallel_analysis_node)
```

## 🚀 추가하면 좋을 혁신적 기능들

### 1. 🤖 AI 부동산 코치
```python
class AIRealEstateCoach:
    """개인화된 부동산 투자 코칭"""
    
    def analyze_user_profile(self, state: RealEstateState) -> dict:
        """사용자 프로파일 분석"""
        return {
            "investment_style": "conservative",  # 보수적/공격적
            "experience_level": "intermediate",
            "preferred_areas": ["강남", "서초"],
            "budget_range": (500000000, 800000000),
            "investment_goals": ["자가", "투자"]
        }
    
    def provide_coaching(self, state: RealEstateState) -> dict:
        """맞춤형 코칭 제공"""
        profile = self.analyze_user_profile(state)
        market_conditions = state.get("market_analysis")
        
        coaching_advice = {
            "timing": "현재는 매수 적기입니다",
            "areas_to_watch": ["마곡", "위례"],
            "risks_to_avoid": ["재건축 불확실 지역"],
            "opportunities": ["신도시 프리미엄 형성 전"],
            "action_items": [
                "마곡 신축 오피스텔 검토",
                "위례 전세가율 70% 이하 매물 확인"
            ]
        }
        
        return {**state, "coaching": coaching_advice}
```

### 2. 🔮 시장 예측 엔진
```python
class MarketPredictionEngine:
    """AI 기반 부동산 시장 예측"""
    
    def predict_price_trend(self, state: RealEstateState) -> dict:
        """가격 추세 예측"""
        area = state.get("target_area")
        
        # 다양한 지표 분석
        indicators = {
            "supply_demand": self.analyze_supply_demand(area),
            "development_plans": self.check_development_plans(area),
            "population_trend": self.analyze_population(area),
            "economic_indicators": self.get_economic_indicators(),
            "interest_rates": self.get_interest_forecast()
        }
        
        # ML 모델로 예측
        prediction = {
            "3_month": "+2.3%",
            "6_month": "+4.1%", 
            "1_year": "+7.2%",
            "confidence": 0.78,
            "key_factors": ["신규 지하철 개통", "학군 개선"]
        }
        
        return {**state, "market_prediction": prediction}
```

### 3. 🏘️ 커뮤니티 인사이트
```python
class CommunityInsights:
    """실거주자 커뮤니티 정보 수집/분석"""
    
    def gather_community_feedback(self, property_id: str) -> dict:
        """커뮤니티 피드백 수집"""
        return {
            "resident_satisfaction": 4.2,
            "pros": ["조용한 환경", "좋은 학군", "편의시설 접근성"],
            "cons": ["주차 부족", "관리비 상승"],
            "recent_issues": ["엘리베이터 교체 예정"],
            "community_events": ["월간 주민 회의", "플리마켓"],
            "average_residency": "4.5년"
        }
```

### 4. 📊 포트폴리오 최적화
```python
class PortfolioOptimizer:
    """부동산 포트폴리오 최적화"""
    
    def optimize_portfolio(self, state: RealEstateState) -> dict:
        """현재 포트폴리오 최적화 제안"""
        current_portfolio = state.get("user_portfolio", [])
        
        analysis = {
            "current_allocation": {
                "residential": "60%",
                "commercial": "30%",
                "land": "10%"
            },
            "risk_score": 6.5,
            "expected_return": "8.2%",
            "recommendations": [
                {
                    "action": "sell",
                    "property": "강북 오피스텔",
                    "reason": "수익률 하락 예상"
                },
                {
                    "action": "buy",
                    "property": "판교 지식산업센터",
                    "reason": "높은 임대 수익률"
                }
            ],
            "rebalancing_needed": True
        }
        
        return {**state, "portfolio_optimization": analysis}
```

### 5. 🎯 스마트 매칭 시스템
```python
class SmartMatchingSystem:
    """AI 기반 매물-고객 매칭"""
    
    def match_properties(self, state: RealEstateState) -> dict:
        """고객 니즈와 매물 매칭"""
        user_preferences = state.get("user_preferences")
        available_properties = state.get("search_results")
        
        # 다차원 매칭 스코어 계산
        matches = []
        for property in available_properties:
            score = self.calculate_match_score(
                property, 
                user_preferences,
                weights={
                    "location": 0.3,
                    "price": 0.25,
                    "size": 0.15,
                    "amenities": 0.15,
                    "investment_potential": 0.15
                }
            )
            matches.append({
                "property": property,
                "match_score": score,
                "match_reasons": self.get_match_reasons(property, user_preferences)
            })
        
        # 상위 매칭 결과
        top_matches = sorted(matches, key=lambda x: x["match_score"], reverse=True)[:5]
        
        return {**state, "matched_properties": top_matches}
```

### 6. 🔍 실시간 모니터링
```python
class RealTimeMonitor:
    """실시간 시장 모니터링 및 알림"""
    
    async def monitor_market(self, state: RealEstateState):
        """실시간 시장 변화 감지"""
        
        # WebSocket으로 실시간 데이터 수신
        async with websocket.connect("ws://real-estate-feed") as ws:
            while True:
                data = await ws.recv()
                event = json.loads(data)
                
                # 중요 이벤트 감지
                if self.is_significant(event):
                    await self.notify_user({
                        "type": event["type"],
                        "message": f"관심 지역 {event['area']}에 새로운 매물이 등록되었습니다",
                        "property": event["property"],
                        "alert_level": "high"
                    })
```

### 7. 📝 자동 계약서 검토
```python
class ContractReviewer:
    """AI 기반 계약서 자동 검토"""
    
    def review_contract(self, contract_text: str) -> dict:
        """계약서 위험 요소 검토"""
        
        issues = []
        
        # 특약사항 분석
        special_terms = self.extract_special_terms(contract_text)
        for term in special_terms:
            risk = self.assess_risk(term)
            if risk["level"] > 7:
                issues.append({
                    "clause": term,
                    "risk_level": risk["level"],
                    "explanation": risk["explanation"],
                    "suggestion": risk["suggestion"]
                })
        
        # 법적 검토
        legal_issues = self.check_legal_compliance(contract_text)
        
        return {
            "risk_score": len(issues) * 10,
            "issues_found": issues,
            "legal_compliance": legal_issues,
            "recommendations": self.generate_recommendations(issues),
            "negotiation_points": self.identify_negotiation_points(contract_text)
        }
```

## 📱 Progress Bar 고도화

### 1. 다단계 Progress 표시
```python
class MultiLevelProgress:
    """다단계 진행률 표시"""
    
    def __init__(self):
        self.main_progress = 0
        self.sub_progress = {}
        self.details = {}
    
    def update(self, level: str, value: float, message: str = None):
        """진행률 업데이트"""
        if level == "main":
            self.main_progress = value
        else:
            self.sub_progress[level] = value
        
        if message:
            self.details[level] = message
        
        # WebSocket으로 전송
        return {
            "type": "progress_update",
            "main": self.main_progress,
            "sub": self.sub_progress,
            "details": self.details,
            "timestamp": datetime.now().isoformat()
        }
```

### 2. React Progress Component (고급)
```jsx
const AdvancedProgressBar = ({ progress }) => {
    return (
        <Box sx={{ width: '100%' }}>
            {/* 메인 진행률 */}
            <LinearProgress 
                variant="determinate" 
                value={progress.main} 
                sx={{ height: 10, borderRadius: 5 }}
            />
            
            {/* 서브 태스크 진행률 */}
            {Object.entries(progress.sub).map(([task, value]) => (
                <Box key={task} sx={{ mt: 1 }}>
                    <Typography variant="caption">{task}</Typography>
                    <LinearProgress 
                        variant="determinate" 
                        value={value}
                        sx={{ height: 4 }}
                    />
                </Box>
            ))}
            
            {/* 실시간 메시지 */}
            <Typography variant="body2" sx={{ mt: 2 }}>
                {progress.currentMessage}
            </Typography>
            
            {/* 예상 완료 시간 */}
            <Typography variant="caption" color="text.secondary">
                예상 완료: {progress.estimatedTime}
            </Typography>
        </Box>
    );
};
```

## 🎯 구현 우선순위 (업데이트)

### Phase 1 (필수)
1. 기본 검색/분석 + Progress Bar
2. Human-in-the-Loop (고액 거래)
3. 동적 에이전트 선택

### Phase 2 (중요)
1. AI 부동산 코치
2. 스마트 매칭 시스템
3. 병렬 분석 실행

### Phase 3 (차별화)
1. 시장 예측 엔진
2. 포트폴리오 최적화
3. 커뮤니티 인사이트

### Phase 4 (고도화)
1. 실시간 모니터링
2. 자동 계약서 검토
3. Plugin 시스템