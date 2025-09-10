"""
Supervisor Agent
전체 워크플로우를 관리하고 에이전트들을 오케스트레이션하는 중앙 제어 에이전트
"""

import asyncio
from typing import Dict, Any, List, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from backend.agents.base_agent import BaseAgent
from backend.core.state import AgentState, ExecutionPlan
from backend.config import get_config_manager

logger = logging.getLogger(__name__)


class SupervisorAgent(BaseAgent):
    """
    Supervisor 에이전트
    - 실행 계획에 따라 에이전트 오케스트레이션
    - 병렬/순차 실행 관리
    - 결과 수집 및 집계
    - 에러 처리 및 재시도
    """
    
    def __init__(self):
        super().__init__(agent_id="supervisor_agent", name="Supervisor")
        self.config = get_config_manager()
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.agent_registry = {}  # 에이전트 인스턴스 캐시
    
    def process(self, state: AgentState) -> Dict[str, Any]:
        """
        에이전트 오케스트레이션 실행
        
        Args:
            state: Current state with execution plan
            
        Returns:
            Updated state with execution results
        """
        # 실행 계획 가져오기
        plan = state.get("plan", [])
        strategy = state.get("execution_strategy", "sequential")
        
        if not plan:
            logger.warning("No execution plan found")
            return {
                "workflow_status": "completed",
                "current_step": "no_plan"
            }
        
        logger.info(f"Starting orchestration with strategy: {strategy}")
        logger.info(f"Total steps to execute: {len(plan)}")
        
        # 전략에 따른 실행
        if strategy == "parallel":
            results = self._execute_parallel(plan, state)
        elif strategy == "hybrid":
            results = self._execute_hybrid(plan, state)
        else:  # sequential
            results = self._execute_sequential(plan, state)
        
        # 결과 집계
        aggregated_results = self._aggregate_results(results)
        
        # 워크플로우 상태 결정
        workflow_status = self._determine_workflow_status(results)
        
        logger.info(f"Orchestration complete. Status: {workflow_status}")
        
        return {
            "execution_results": results,
            "aggregated_results": aggregated_results,
            "workflow_status": workflow_status,
            "current_step": "orchestration_complete"
        }
    
    def _execute_sequential(self, plan: List[ExecutionPlan], state: AgentState) -> Dict[str, Any]:
        """
        순차 실행
        
        Returns:
            Execution results
        """
        results = state.get("execution_results", {})
        
        for step in plan:
            step_id = step["step_id"]
            agent_id = step["agent_id"]
            
            logger.info(f"Executing step {step_id}: {agent_id}")
            
            # 의존성 체크
            if not self._check_dependencies(step, results):
                logger.warning(f"Dependencies not met for {step_id}")
                results[agent_id] = {
                    "status": "skipped",
                    "reason": "dependencies_not_met"
                }
                continue
            
            # 에이전트 실행
            try:
                agent = self._get_or_create_agent(agent_id)
                if agent:
                    # 상태 업데이트
                    state["current_step"] = step_id
                    state["current_agent"] = agent_id
                    
                    # 파라미터 준비
                    if step.get("parameters"):
                        state["agent_parameters"] = step["parameters"]
                    
                    # 타임아웃 적용하여 실행
                    result = self._execute_with_timeout(
                        agent, 
                        state, 
                        step["timeout"]
                    )
                    
                    # 결과 저장
                    results[agent_id] = result
                    
                    # 상태 업데이트
                    if isinstance(result, dict):
                        for key, value in result.items():
                            if key not in ["execution_results", "current_agent"]:
                                state[key] = value
                    
                    # 실패 시 재시도
                    if result.get("status") == "failed":
                        retry_result = self._handle_retry(agent, state, step)
                        if retry_result:
                            results[agent_id] = retry_result
                else:
                    logger.error(f"Agent {agent_id} not found")
                    results[agent_id] = {
                        "status": "failed",
                        "error": "Agent not found"
                    }
                    
            except Exception as e:
                logger.error(f"Error executing {agent_id}: {str(e)}")
                results[agent_id] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return results
    
    def _execute_parallel(self, plan: List[ExecutionPlan], state: AgentState) -> Dict[str, Any]:
        """
        병렬 실행
        
        Returns:
            Execution results
        """
        results = state.get("execution_results", {})
        futures = {}
        
        # 병렬 실행 제한
        max_concurrent = self.config.get_max_concurrent_agents()
        
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            for step in plan:
                step_id = step["step_id"]
                agent_id = step["agent_id"]
                
                # 의존성이 없는 경우만 병렬 실행
                if not step.get("dependencies"):
                    logger.info(f"Submitting parallel execution for {agent_id}")
                    
                    # 각 에이전트를 위한 상태 복사
                    agent_state = state.copy()
                    agent_state["current_step"] = step_id
                    agent_state["current_agent"] = agent_id
                    
                    if step.get("parameters"):
                        agent_state["agent_parameters"] = step["parameters"]
                    
                    # 비동기 실행 제출
                    future = executor.submit(
                        self._execute_agent_task,
                        agent_id,
                        agent_state,
                        step["timeout"]
                    )
                    futures[future] = agent_id
            
            # 결과 수집
            for future in as_completed(futures):
                agent_id = futures[future]
                try:
                    result = future.result()
                    results[agent_id] = result
                    logger.info(f"Parallel execution completed for {agent_id}")
                except Exception as e:
                    logger.error(f"Parallel execution failed for {agent_id}: {str(e)}")
                    results[agent_id] = {
                        "status": "failed",
                        "error": str(e)
                    }
        
        return results
    
    def _execute_hybrid(self, plan: List[ExecutionPlan], state: AgentState) -> Dict[str, Any]:
        """
        하이브리드 실행 (순차 + 병렬 조합)
        
        Returns:
            Execution results
        """
        results = state.get("execution_results", {})
        
        # 의존성 그룹 생성
        dependency_groups = self._create_dependency_groups(plan)
        
        # 그룹별로 실행
        for group_idx, group in enumerate(dependency_groups):
            logger.info(f"Executing dependency group {group_idx + 1}/{len(dependency_groups)}")
            
            if len(group) > 1:
                # 그룹 내 병렬 실행
                group_plan = [step for step in plan if step["step_id"] in group]
                group_results = self._execute_parallel(group_plan, state)
                results.update(group_results)
            else:
                # 단일 실행
                step = next(step for step in plan if step["step_id"] in group[0])
                agent_id = step["agent_id"]
                
                agent = self._get_or_create_agent(agent_id)
                if agent:
                    state["current_step"] = step["step_id"]
                    state["current_agent"] = agent_id
                    
                    result = self._execute_with_timeout(
                        agent,
                        state,
                        step["timeout"]
                    )
                    results[agent_id] = result
        
        return results
    
    def _execute_agent_task(self, agent_id: str, state: AgentState, timeout: int) -> Dict[str, Any]:
        """
        개별 에이전트 작업 실행 (병렬 실행용)
        
        Returns:
            Agent execution result
        """
        agent = self._get_or_create_agent(agent_id)
        if not agent:
            return {
                "status": "failed",
                "error": f"Agent {agent_id} not found"
            }
        
        return self._execute_with_timeout(agent, state, timeout)
    
    def _execute_with_timeout(self, agent: BaseAgent, state: AgentState, timeout: int) -> Dict[str, Any]:
        """
        타임아웃 적용하여 에이전트 실행
        
        Returns:
            Execution result
        """
        try:
            # 동기 실행 (실제로는 asyncio 사용 권장)
            start_time = time.time()
            result = agent(state)
            execution_time = time.time() - start_time
            
            if execution_time > timeout:
                logger.warning(f"Agent {agent.agent_id} exceeded timeout ({execution_time:.2f}s > {timeout}s)")
            
            return result
            
        except Exception as e:
            logger.error(f"Agent execution error: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _get_or_create_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """
        에이전트 인스턴스 가져오기 또는 생성
        
        Returns:
            Agent instance or None
        """
        # 캐시 확인
        if agent_id in self.agent_registry:
            return self.agent_registry[agent_id]
        
        # 동적 임포트 및 생성
        try:
            if agent_id == "price_search_agent":
                from backend.agents.price_search_agent import PriceSearchAgent
                agent = PriceSearchAgent()
            elif agent_id == "finance_agent":
                from backend.agents.finance_agent import FinanceAgent
                agent = FinanceAgent()
            elif agent_id == "location_agent":
                from backend.agents.location_agent import LocationAgent
                agent = LocationAgent()
            elif agent_id == "legal_agent":
                from backend.agents.legal_agent import LegalAgent
                agent = LegalAgent()
            else:
                logger.error(f"Unknown agent ID: {agent_id}")
                return None
            
            # 캐시에 저장
            self.agent_registry[agent_id] = agent
            return agent
            
        except ImportError as e:
            logger.error(f"Failed to import agent {agent_id}: {str(e)}")
            return None
    
    def _check_dependencies(self, step: ExecutionPlan, results: Dict[str, Any]) -> bool:
        """
        의존성 충족 여부 확인
        
        Returns:
            True if all dependencies are met
        """
        dependencies = step.get("dependencies", [])
        
        if not dependencies:
            return True
        
        for dep_step_id in dependencies:
            # 의존 단계의 에이전트 ID 찾기
            dep_agent_id = dep_step_id.replace("step_", "agent_")  # 간단한 매핑
            
            if dep_agent_id not in results:
                return False
            
            if results[dep_agent_id].get("status") != "success":
                return False
        
        return True
    
    def _handle_retry(self, agent: BaseAgent, state: AgentState, step: ExecutionPlan) -> Optional[Dict]:
        """
        에이전트 실행 재시도
        
        Returns:
            Retry result or None
        """
        retry_policy = step.get("retry_policy", {})
        max_retries = retry_policy.get("max_retries", 3)
        
        retry_count = state.get("retry_attempts", 0)
        
        if retry_count >= max_retries:
            logger.warning(f"Max retries reached for {agent.agent_id}")
            return None
        
        # 재시도 지연
        delay = agent.get_retry_delay(retry_count)
        logger.info(f"Retrying {agent.agent_id} after {delay}s delay")
        time.sleep(delay)
        
        # 재시도 카운트 증가
        state["retry_attempts"] = retry_count + 1
        
        # 재실행
        try:
            result = self._execute_with_timeout(agent, state, step["timeout"])
            if result.get("status") == "success":
                logger.info(f"Retry successful for {agent.agent_id}")
            return result
        except Exception as e:
            logger.error(f"Retry failed for {agent.agent_id}: {str(e)}")
            return None
    
    def _create_dependency_groups(self, plan: List[ExecutionPlan]) -> List[List[str]]:
        """
        의존성 기반 실행 그룹 생성
        
        Returns:
            List of step ID groups
        """
        groups = []
        processed = set()
        
        for step in plan:
            step_id = step["step_id"]
            
            if step_id in processed:
                continue
            
            # 의존성이 없거나 모두 처리된 경우
            dependencies = step.get("dependencies", [])
            
            if not dependencies or all(dep in processed for dep in dependencies):
                # 같은 레벨의 다른 단계 찾기
                current_group = [step_id]
                
                for other_step in plan:
                    other_id = other_step["step_id"]
                    if other_id != step_id and other_id not in processed:
                        other_deps = other_step.get("dependencies", [])
                        
                        # 같은 의존성 레벨인 경우
                        if set(other_deps) == set(dependencies):
                            current_group.append(other_id)
                
                groups.append(current_group)
                processed.update(current_group)
        
        return groups
    
    def _aggregate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        실행 결과 집계
        
        Returns:
            Aggregated results
        """
        aggregated = {
            "total_agents": len(results),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "combined_output": {},
            "confidence_scores": {}
        }
        
        for agent_id, result in results.items():
            status = result.get("status", "unknown")
            
            if status == "success":
                aggregated["successful"] += 1
                
                # 결과 데이터 수집
                if "result" in result:
                    aggregated["combined_output"][agent_id] = result["result"]
                
                # 신뢰도 점수 수집
                if "confidence" in result:
                    aggregated["confidence_scores"][agent_id] = result["confidence"]
                    
            elif status == "failed":
                aggregated["failed"] += 1
            elif status == "skipped":
                aggregated["skipped"] += 1
        
        # 전체 신뢰도 계산
        if aggregated["confidence_scores"]:
            avg_confidence = sum(aggregated["confidence_scores"].values()) / len(aggregated["confidence_scores"])
            aggregated["overall_confidence"] = avg_confidence
        
        return aggregated
    
    def _determine_workflow_status(self, results: Dict[str, Any]) -> str:
        """
        전체 워크플로우 상태 결정
        
        Returns:
            Workflow status
        """
        statuses = [r.get("status", "unknown") for r in results.values()]
        
        if all(s == "success" for s in statuses):
            return "completed"
        elif any(s == "failed" for s in statuses):
            failed_count = statuses.count("failed")
            if failed_count == len(statuses):
                return "failed"
            else:
                return "partially_completed"
        elif all(s == "skipped" for s in statuses):
            return "skipped"
        else:
            return "completed_with_warnings"


# 노드로 사용할 함수 (LangGraph 호환)
def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph 노드 함수
    
    Args:
        state: Agent state
        
    Returns:
        Updated state
    """
    agent = SupervisorAgent()
    return agent(state)