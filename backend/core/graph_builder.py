"""
StateGraph Builder with LangGraph 0.6.6 Runtime API
Context-aware graph construction for real estate chatbot
"""

from typing import Dict, Any, Optional, List, Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from backend.core.state import AgentState
from backend.core.context import RealEstateContext
from backend.agents.analyzer_agent import AnalyzerAgent
from backend.agents.planner_agent import PlannerAgent
from backend.agents.supervisor_agent import SupervisorAgent
from backend.agents.price_search_agent import PriceSearchAgent
from backend.agents.finance_agent import FinanceAgent
from backend.agents.location_agent import LocationAgent
from backend.agents.legal_agent import LegalAgent
from backend.config.config_loader import ConfigManager


class RealEstateGraphBuilder:
    """
    LangGraph 0.6.6 StateGraph 빌더
    Context API를 활용한 런타임 그래프 구성
    """
    
    def __init__(self, context: RealEstateContext):
        """
        Args:
            context: RealEstateContext 런타임 컨텍스트
        """
        self.context = context
        self.config_manager = ConfigManager()
        self.agents = self._initialize_agents()
        self.graph = None
        
    def _initialize_agents(self) -> Dict[str, Any]:
        """에이전트 초기화"""
        agents = {
            "analyzer": AnalyzerAgent(),
            "planner": PlannerAgent(),
            "supervisor": SupervisorAgent()
        }
        
        # Context에서 사용 가능한 에이전트만 초기화
        if self.context.is_agent_available("price_search_agent"):
            agents["price_search"] = PriceSearchAgent()
        if self.context.is_agent_available("finance_agent"):
            agents["finance"] = FinanceAgent()
        if self.context.is_agent_available("location_agent"):
            agents["location"] = LocationAgent()
        if self.context.is_agent_available("legal_agent"):
            agents["legal"] = LegalAgent()
            
        return agents
    
    def build(self) -> StateGraph:
        """StateGraph 구축"""
        builder = StateGraph(AgentState)
        
        # === 노드 추가 ===
        builder.add_node("analyze", self._analyze_node)
        builder.add_node("plan", self._plan_node)
        builder.add_node("route", self._route_node)
        builder.add_node("execute", self._execute_node)
        builder.add_node("aggregate", self._aggregate_node)
        builder.add_node("error_handler", self._error_handler_node)
        
        # === 엣지 추가 ===
        # 진입점
        builder.set_entry_point("analyze")
        
        # 정상 플로우
        builder.add_edge("analyze", "plan")
        builder.add_edge("plan", "route")
        
        # 조건부 라우팅
        builder.add_conditional_edges(
            "route",
            self._should_execute,
            {
                "execute": "execute",
                "error": "error_handler",
                "end": END
            }
        )
        
        builder.add_conditional_edges(
            "execute",
            self._check_execution_status,
            {
                "aggregate": "aggregate",
                "retry": "execute",
                "error": "error_handler"
            }
        )
        
        builder.add_conditional_edges(
            "aggregate",
            self._should_continue,
            {
                "route": "route",  # 추가 실행 필요
                "end": END
            }
        )
        
        # 에러 핸들링
        builder.add_conditional_edges(
            "error_handler",
            self._handle_error_recovery,
            {
                "retry": "route",
                "end": END
            }
        )
        
        # StateGraph를 반환 (compile은 workflow_engine에서 처리)
        self.graph = builder
        return self.graph
    
    async def _analyze_node(self, state: AgentState) -> AgentState:
        """쿼리 분석 노드"""
        try:
            # Context 정보를 에이전트에 전달
            agent_context = {
                "user_id": self.context.user_id,
                "user_name": self.context.user_name,
                "session_id": self.context.session_id,
                "system_message": self.context.system_message
            }
            
            result = await self.agents["analyzer"].analyze(
                state["query"],
                context=agent_context
            )
            
            state["intent"] = result.get("intent", "unknown")
            state["entities"] = result.get("entities", {})
            state["confidence_scores"]["intent"] = result.get("confidence", 0.0)
            state["workflow_status"] = "analyzed"
            
            # 분석 결과를 메시지에 추가
            state["messages"].append(
                AIMessage(content=f"쿼리 분석 완료: {state['intent']}")
            )
            
        except Exception as e:
            state["errors"]["analyzer"] = str(e)
            state["workflow_status"] = "error"
            
        return state
    
    async def _plan_node(self, state: AgentState) -> AgentState:
        """실행 계획 수립 노드"""
        try:
            # Context의 실행 전략 반영
            exec_config = self.context.get_execution_config()
            
            result = await self.agents["planner"].plan(
                intent=state["intent"],
                entities=state["entities"],
                execution_strategy=exec_config["strategy"],
                available_agents=self.context.available_agents
            )
            
            state["plan"] = result.get("steps", [])
            state["selected_agents"] = result.get("agents", [])
            state["execution_strategy"] = result.get("strategy", "sequential")
            state["workflow_status"] = "planned"
            
            # 계획을 메시지에 추가
            plan_summary = f"실행 계획: {', '.join(state['plan'][:3])}"
            state["messages"].append(AIMessage(content=plan_summary))
            
        except Exception as e:
            state["errors"]["planner"] = str(e)
            state["workflow_status"] = "error"
            
        return state
    
    async def _route_node(self, state: AgentState) -> AgentState:
        """라우팅 결정 노드"""
        # 다음 실행할 에이전트 선택
        if not state.get("current_agent_index"):
            state["current_agent_index"] = 0
        
        if state["current_agent_index"] < len(state["selected_agents"]):
            agent_id = state["selected_agents"][state["current_agent_index"]]
            state["next_agent"] = agent_id
            state["workflow_status"] = "routing"
        else:
            state["workflow_status"] = "completed"
            
        return state
    
    async def _execute_node(self, state: AgentState) -> AgentState:
        """에이전트 실행 노드"""
        agent_id = state.get("next_agent")
        if not agent_id:
            state["workflow_status"] = "error"
            return state
        
        try:
            # Context의 모델 설정 적용
            model_config = self.context.get_model_config()
            
            # 에이전트 매핑
            agent_map = {
                "price_search_agent": "price_search",
                "finance_agent": "finance",
                "location_agent": "location",
                "legal_agent": "legal"
            }
            
            agent_key = agent_map.get(agent_id)
            if agent_key and agent_key in self.agents:
                agent = self.agents[agent_key]
                
                # Supervisor를 통한 실행
                result = await self.agents["supervisor"].execute_agent(
                    agent=agent,
                    query=state["query"],
                    entities=state["entities"],
                    context={
                        **model_config,
                        "user_id": self.context.user_id,
                        "max_retries": self.context.max_retries
                    }
                )
                
                # 결과 저장
                state["agent_results"][agent_id] = result
                state["current_agent_index"] += 1
                
                # 실행 메트릭 업데이트
                if "execution_time" in result:
                    state["execution_metrics"]["total_time"] += result["execution_time"]
                state["execution_metrics"]["agents_called"] += 1
                
                # 결과를 메시지에 추가
                state["messages"].append(
                    AIMessage(content=f"{agent_id}: {result.get('summary', 'Completed')}")
                )
                
            state["workflow_status"] = "executing"
            
        except Exception as e:
            state["errors"][agent_id] = str(e)
            state["retry_count"] += 1
            
            if state["retry_count"] >= self.context.max_retries:
                state["workflow_status"] = "error"
            else:
                state["workflow_status"] = "retry"
                
        return state
    
    async def _aggregate_node(self, state: AgentState) -> AgentState:
        """결과 집계 노드"""
        try:
            # 모든 에이전트 결과 통합
            all_results = state["agent_results"]
            
            # 최종 응답 생성
            final_response = await self._generate_final_response(all_results, state)
            state["final_response"] = final_response
            
            # 신뢰도 점수 계산
            if all_results:
                scores = [r.get("confidence", 0.5) for r in all_results.values()]
                state["confidence_scores"]["overall"] = sum(scores) / len(scores)
            
            # 최종 메시지 추가
            state["messages"].append(
                AIMessage(content=final_response)
            )
            
            state["workflow_status"] = "aggregated"
            
        except Exception as e:
            state["errors"]["aggregator"] = str(e)
            state["workflow_status"] = "error"
            
        return state
    
    async def _error_handler_node(self, state: AgentState) -> AgentState:
        """에러 처리 노드"""
        # Context의 에러 복구 설정 확인
        if self.context.features.get("enable_error_recovery"):
            # 에러 타입별 복구 전략
            error_keys = list(state["errors"].keys())
            
            if "analyzer" in error_keys and state["retry_count"] < 2:
                # 분석 재시도
                state["workflow_status"] = "retry"
                state["retry_count"] += 1
            elif state["retry_count"] < self.context.max_retries:
                # 일반 재시도
                state["workflow_status"] = "retry"
                state["retry_count"] += 1
            else:
                # 최종 실패
                state["workflow_status"] = "failed"
                state["final_response"] = self._generate_error_response(state["errors"])
        else:
            state["workflow_status"] = "failed"
            state["final_response"] = "처리 중 오류가 발생했습니다."
            
        return state
    
    # === 조건부 라우팅 함수 ===
    
    def _should_execute(self, state: AgentState) -> str:
        """실행 여부 결정"""
        if state["workflow_status"] == "error":
            return "error"
        elif state["workflow_status"] == "completed":
            return "end"
        elif state["selected_agents"] and state["current_agent_index"] < len(state["selected_agents"]):
            return "execute"
        else:
            return "end"
    
    def _check_execution_status(self, state: AgentState) -> str:
        """실행 상태 확인"""
        if state["workflow_status"] == "error":
            return "error"
        elif state["workflow_status"] == "retry":
            return "retry"
        else:
            return "aggregate"
    
    def _should_continue(self, state: AgentState) -> str:
        """계속 실행 여부"""
        if state["current_agent_index"] < len(state["selected_agents"]):
            return "route"
        else:
            return "end"
    
    def _handle_error_recovery(self, state: AgentState) -> str:
        """에러 복구 처리"""
        if state["workflow_status"] == "retry" and state["retry_count"] < self.context.max_retries:
            return "retry"
        else:
            return "end"
    
    # === 헬퍼 함수 ===
    
    async def _generate_final_response(self, results: Dict, state: AgentState) -> str:
        """최종 응답 생성"""
        response_parts = []
        
        # 의도별 응답 템플릿
        if state["intent"] == "information_search":
            response_parts.append("요청하신 정보를 찾았습니다:")
        elif state["intent"] == "recommendation":
            response_parts.append("추천 결과입니다:")
        elif state["intent"] == "consultation":
            response_parts.append("상담 결과를 안내드립니다:")
        else:
            response_parts.append("처리 결과입니다:")
        
        # 각 에이전트 결과 포함
        for agent_id, result in results.items():
            if result.get("success"):
                content = result.get("content", "")
                if content:
                    response_parts.append(f"\n• {content}")
        
        # 추가 안내
        if state["confidence_scores"].get("overall", 0) < 0.7:
            response_parts.append("\n\n추가 정보가 필요하시면 구체적으로 질문해 주세요.")
        
        return "\n".join(response_parts)
    
    def _generate_error_response(self, errors: Dict[str, str]) -> str:
        """에러 응답 생성"""
        if self.context.environment == "development":
            # 개발 환경: 상세 에러
            error_details = "\n".join([f"- {k}: {v}" for k, v in errors.items()])
            return f"처리 중 오류가 발생했습니다:\n{error_details}"
        else:
            # 프로덕션: 간단한 메시지
            return "요청을 처리할 수 없습니다. 잠시 후 다시 시도해 주세요."
    
    def get_graph(self) -> Optional[StateGraph]:
        """컴파일된 그래프 반환"""
        if not self.graph:
            self.graph = self.build()
        return self.graph
    
    def visualize(self) -> str:
        """그래프 시각화 (Mermaid 형식)"""
        if not self.graph:
            self.build()
            
        return """
        graph TD
            Start([User Query]) --> Analyze[Analyze Query]
            Analyze --> Plan[Plan Execution]
            Plan --> Route{Route Decision}
            Route -->|Execute| Execute[Execute Agent]
            Route -->|End| End([Final Response])
            Execute --> Check{Check Status}
            Check -->|Success| Aggregate[Aggregate Results]
            Check -->|Retry| Execute
            Check -->|Error| Error[Error Handler]
            Aggregate --> Continue{Continue?}
            Continue -->|Yes| Route
            Continue -->|No| End
            Error --> Recovery{Recovery?}
            Recovery -->|Retry| Route
            Recovery -->|Fail| End
        """