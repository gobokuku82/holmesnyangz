"""
Planner Agent
분석 결과를 바탕으로 실행 계획을 수립하는 에이전트
에이전트 실행 순서와 전략을 결정
"""

from typing import Dict, Any, List, Optional
import logging
from backend.agents.base_agent import BaseAgent
from backend.core.state import AgentState, ExecutionPlan
from backend.config import get_config_manager

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """
    계획 수립 에이전트
    - 실행 전략 결정 (순차/병렬)
    - 에이전트 실행 순서 최적화
    - 의존성 관리
    - 타임아웃 설정
    """
    
    def __init__(self):
        super().__init__(agent_id="planner_agent", name="실행 계획 수립가")
        self.config = get_config_manager()
    
    def process(self, state: AgentState) -> Dict[str, Any]:
        """
        실행 계획 수립
        
        Args:
            state: Current state with analysis results
            
        Returns:
            Updated state with execution plan
        """
        # 분석 결과 가져오기
        intent = state.get("intent", "unknown")
        entities = state.get("entities", {})
        complexity = state.get("query_complexity", "simple")
        selected_agents = state.get("selected_agents", [])
        
        if not selected_agents:
            logger.warning("No agents selected, using default")
            selected_agents = ["price_search_agent"]
        
        # 1. 실행 전략 결정
        execution_strategy = self._determine_strategy(complexity, selected_agents)
        
        # 2. 에이전트 우선순위 결정
        priority_order = self._determine_priority(selected_agents, intent, entities)
        
        # 3. 실행 계획 생성
        execution_plan = self._create_execution_plan(
            priority_order,
            execution_strategy,
            entities
        )
        
        # 4. 의존성 확인 및 조정
        execution_plan = self._resolve_dependencies(execution_plan)
        
        # 5. 최적화
        execution_plan = self._optimize_plan(execution_plan, execution_strategy)
        
        logger.info(f"Execution Plan Created:")
        logger.info(f"  - Strategy: {execution_strategy}")
        logger.info(f"  - Priority order: {priority_order}")
        logger.info(f"  - Total steps: {len(execution_plan)}")
        
        return {
            "plan": execution_plan,
            "execution_strategy": execution_strategy,
            "priority_order": priority_order,
            "current_step": "planning_complete"
        }
    
    def _determine_strategy(self, complexity: str, agents: List[str]) -> str:
        """
        실행 전략 결정
        
        Returns:
            "sequential", "parallel", or "hybrid"
        """
        # 복잡도와 에이전트 수에 따른 전략 결정
        agent_count = len(agents)
        
        if complexity == "simple" and agent_count == 1:
            return "sequential"
        
        if complexity == "complex" and agent_count > 2:
            # 복잡한 질의는 병렬 처리로 속도 향상
            if self.config.config.routing.parallel_execution.enabled:
                return "parallel"
        
        if complexity == "moderate" and agent_count > 1:
            # 중간 복잡도는 하이브리드 전략
            return "hybrid"
        
        # 기본값
        return "sequential"
    
    def _determine_priority(self, agents: List[str], intent: str, entities: Dict) -> List[str]:
        """
        에이전트 실행 우선순위 결정
        
        Returns:
            Ordered list of agent IDs
        """
        # 에이전트 설정에서 우선순위 가져오기
        agent_priorities = {}
        
        for agent_id in agents:
            agent_config = self.config.get_agent_by_id(agent_id)
            if agent_config:
                # 기본 우선순위
                priority = agent_config.priority
                
                # 의도와 일치하면 우선순위 상승
                if intent in agent_config.trigger_conditions.intents:
                    priority -= 1  # 낮은 숫자가 높은 우선순위
                
                # 엔티티와 일치하면 우선순위 상승
                matching_entities = 0
                for entity_type in entities.keys():
                    if entity_type in agent_config.trigger_conditions.entities:
                        matching_entities += 1
                priority -= matching_entities * 0.5
                
                agent_priorities[agent_id] = priority
            else:
                agent_priorities[agent_id] = 99  # 설정이 없으면 낮은 우선순위
        
        # 우선순위에 따라 정렬
        sorted_agents = sorted(agent_priorities.items(), key=lambda x: x[1])
        
        return [agent_id for agent_id, _ in sorted_agents]
    
    def _create_execution_plan(self, 
                               agents: List[str], 
                               strategy: str,
                               entities: Dict) -> List[ExecutionPlan]:
        """
        실행 계획 생성
        
        Returns:
            List of execution plan steps
        """
        plan = []
        
        for idx, agent_id in enumerate(agents):
            agent_config = self.config.get_agent_by_id(agent_id)
            
            if not agent_config:
                continue
            
            # 기본 계획 단계
            step = ExecutionPlan(
                step_id=f"step_{idx+1}",
                agent_id=agent_id,
                action=self._determine_action(agent_id, entities),
                parameters=self._prepare_parameters(agent_id, entities),
                dependencies=[],
                timeout=agent_config.max_execution_time,
                retry_policy={
                    "max_retries": agent_config.retry_policy.max_retries,
                    "backoff": agent_config.retry_policy.backoff
                }
            )
            
            # 전략에 따른 의존성 설정
            if strategy == "sequential" and idx > 0:
                # 순차 실행: 이전 단계에 의존
                step["dependencies"] = [f"step_{idx}"]
            elif strategy == "hybrid":
                # 하이브리드: 특정 에이전트만 의존성 설정
                step["dependencies"] = self._determine_hybrid_dependencies(
                    agent_id, 
                    agents[:idx],
                    idx
                )
            # parallel은 의존성 없음
            
            plan.append(step)
        
        return plan
    
    def _determine_action(self, agent_id: str, entities: Dict) -> str:
        """
        에이전트별 액션 결정
        
        Returns:
            Action description
        """
        action_map = {
            "price_search_agent": "search_and_analyze_prices",
            "finance_agent": "calculate_and_simulate_finance",
            "location_agent": "analyze_location_and_accessibility",
            "legal_agent": "review_legal_requirements"
        }
        
        return action_map.get(agent_id, "process_query")
    
    def _prepare_parameters(self, agent_id: str, entities: Dict) -> Dict[str, Any]:
        """
        에이전트별 파라미터 준비
        
        Returns:
            Parameters for agent execution
        """
        params = {"entities": entities}
        
        # 에이전트별 특화 파라미터
        if agent_id == "price_search_agent":
            params["search_params"] = {
                "location": entities.get("location", []),
                "property_type": entities.get("property_type"),
                "transaction_type": entities.get("transaction_type"),
                "price_range": entities.get("price")
            }
        
        elif agent_id == "finance_agent":
            params["finance_params"] = {
                "loan_required": entities.get("finance_related", False),
                "price_info": entities.get("price"),
                "income": entities.get("income")
            }
        
        elif agent_id == "location_agent":
            params["location_params"] = {
                "target_location": entities.get("location", []),
                "facility_types": entities.get("facilities", []),
                "distance_preference": entities.get("distance")
            }
        
        elif agent_id == "legal_agent":
            params["legal_params"] = {
                "transaction_type": entities.get("transaction_type"),
                "legal_concern": entities.get("legal_related", False),
                "contract_review": entities.get("contract")
            }
        
        return params
    
    def _determine_hybrid_dependencies(self, 
                                      current_agent: str,
                                      previous_agents: List[str],
                                      current_idx: int) -> List[str]:
        """
        하이브리드 전략에서 의존성 결정
        
        Returns:
            List of dependency step IDs
        """
        dependencies = []
        
        # 금융 에이전트는 가격 검색 결과가 필요
        if current_agent == "finance_agent" and "price_search_agent" in previous_agents:
            price_idx = previous_agents.index("price_search_agent")
            dependencies.append(f"step_{price_idx + 1}")
        
        # 법률 에이전트는 가격과 금융 정보가 있으면 도움됨
        if current_agent == "legal_agent":
            for agent in ["price_search_agent", "finance_agent"]:
                if agent in previous_agents:
                    idx = previous_agents.index(agent)
                    dependencies.append(f"step_{idx + 1}")
        
        return dependencies
    
    def _resolve_dependencies(self, plan: List[ExecutionPlan]) -> List[ExecutionPlan]:
        """
        의존성 충돌 해결 및 검증
        
        Returns:
            Validated execution plan
        """
        # 순환 의존성 체크
        for step in plan:
            visited = set()
            if self._has_circular_dependency(step["step_id"], plan, visited):
                logger.warning(f"Circular dependency detected for {step['step_id']}")
                step["dependencies"] = []  # 순환 의존성 제거
        
        return plan
    
    def _has_circular_dependency(self, 
                                step_id: str,
                                plan: List[ExecutionPlan],
                                visited: set) -> bool:
        """
        순환 의존성 체크
        
        Returns:
            True if circular dependency exists
        """
        if step_id in visited:
            return True
        
        visited.add(step_id)
        
        # 현재 단계의 의존성 찾기
        current_step = next((s for s in plan if s["step_id"] == step_id), None)
        if not current_step:
            return False
        
        for dep_id in current_step.get("dependencies", []):
            if self._has_circular_dependency(dep_id, plan, visited.copy()):
                return True
        
        return False
    
    def _optimize_plan(self, 
                       plan: List[ExecutionPlan],
                       strategy: str) -> List[ExecutionPlan]:
        """
        실행 계획 최적화
        
        Returns:
            Optimized execution plan
        """
        if strategy == "parallel":
            # 병렬 실행 시 타임아웃 조정
            max_concurrent = self.config.get_max_concurrent_agents()
            
            for step in plan:
                # 동시 실행으로 인한 리소스 경쟁 고려
                step["timeout"] = int(step["timeout"] * 1.2)
        
        elif strategy == "sequential":
            # 순차 실행 시 전체 타임아웃 관리
            total_timeout = sum(step["timeout"] for step in plan)
            
            if total_timeout > 120:  # 2분 초과 시
                logger.warning(f"Total timeout {total_timeout}s exceeds limit")
                # 각 단계 타임아웃 비례 조정
                scale_factor = 120 / total_timeout
                for step in plan:
                    step["timeout"] = int(step["timeout"] * scale_factor)
        
        return plan


# 노드로 사용할 함수 (LangGraph 호환)
def planner_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph 노드 함수
    
    Args:
        state: Agent state
        
    Returns:
        Updated state
    """
    agent = PlannerAgent()
    return agent(state)