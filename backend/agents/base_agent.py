"""
Base Agent Class
모든 에이전트가 상속받는 기본 클래스
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import time
from backend.core.state import AgentState, AgentResult
from backend.config import get_config_manager

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    모든 에이전트의 기본 클래스
    LangGraph 노드로 사용되며, 상태를 받아 처리 후 업데이트된 상태를 반환
    """
    
    def __init__(self, agent_id: str, name: str = None):
        """
        Initialize base agent
        
        Args:
            agent_id: Unique agent identifier
            name: Human-readable agent name
        """
        self.agent_id = agent_id
        self.name = name or agent_id
        self.config_manager = get_config_manager()
        self.agent_config = self.config_manager.get_agent_by_id(agent_id)
        self.execution_count = 0
        self.total_execution_time = 0.0
        
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        LangGraph 노드로 사용될 때 호출되는 메서드
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state dictionary
        """
        start_time = time.time()
        self.execution_count += 1
        
        try:
            # 로깅
            logger.info(f"[{self.name}] Starting execution #{self.execution_count}")
            logger.debug(f"[{self.name}] Input state: {state.get('current_step')}")
            
            # 상태 업데이트 - 현재 에이전트 설정
            state_updates = {
                "current_agent": self.agent_id,
                "workflow_status": "running"
            }
            
            # 에이전트별 처리 로직 실행
            result = self.process(state)
            
            # 결과를 상태 업데이트에 병합
            if isinstance(result, dict):
                state_updates.update(result)
            
            # 실행 시간 기록
            execution_time = time.time() - start_time
            self.total_execution_time += execution_time
            
            # 실행 결과 저장
            if "execution_results" not in state_updates:
                state_updates["execution_results"] = state.get("execution_results", {})
            
            state_updates["execution_results"][self.agent_id] = AgentResult(
                agent_id=self.agent_id,
                status="success",
                result=result,
                confidence=result.get("confidence", 0.8) if isinstance(result, dict) else 0.8,
                execution_time=execution_time,
                error=None,
                metadata={
                    "execution_count": self.execution_count,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # 실행 시간 메트릭 업데이트
            if "execution_times" not in state_updates:
                state_updates["execution_times"] = state.get("execution_times", {})
            state_updates["execution_times"][self.agent_id] = execution_time
            
            logger.info(f"[{self.name}] Completed in {execution_time:.2f}s")
            
            return state_updates
            
        except Exception as e:
            logger.error(f"[{self.name}] Error during execution: {str(e)}")
            
            # 에러 처리
            error_message = str(e)
            
            # 에러 상태 업데이트
            errors = state.get("errors", {})
            errors[self.agent_id] = error_message
            
            error_counts = state.get("error_counts", {})
            error_type = type(e).__name__
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
            
            # 실행 결과에 에러 기록
            execution_results = state.get("execution_results", {})
            execution_results[self.agent_id] = AgentResult(
                agent_id=self.agent_id,
                status="failed",
                result=None,
                confidence=0.0,
                execution_time=time.time() - start_time,
                error=error_message,
                metadata={
                    "error_type": error_type,
                    "execution_count": self.execution_count,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return {
                "errors": errors,
                "error_counts": error_counts,
                "execution_results": execution_results,
                "workflow_status": "error",
                "current_agent": self.agent_id
            }
    
    @abstractmethod
    def process(self, state: AgentState) -> Dict[str, Any]:
        """
        에이전트별 처리 로직 (자식 클래스에서 구현)
        
        Args:
            state: Current agent state
            
        Returns:
            Dictionary with state updates
        """
        pass
    
    def validate_input(self, state: AgentState) -> tuple[bool, Optional[str]]:
        """
        입력 상태 검증
        
        Returns:
            (is_valid, error_message)
        """
        # 필수 필드 체크
        if not state.get("query"):
            return False, "Query is required"
        
        if not state.get("session_id"):
            return False, "Session ID is required"
        
        return True, None
    
    def should_retry(self, error: Exception, retry_count: int) -> bool:
        """
        에러 발생 시 재시도 여부 결정
        
        Args:
            error: The exception that occurred
            retry_count: Current retry attempt count
            
        Returns:
            True if should retry, False otherwise
        """
        if not self.agent_config:
            return retry_count < 3
        
        max_retries = self.agent_config.retry_policy.max_retries
        
        # 재시도 가능한 에러 타입
        retriable_errors = [
            "TimeoutError",
            "ConnectionError", 
            "RateLimitError",
            "TemporaryError"
        ]
        
        error_type = type(error).__name__
        
        if error_type in retriable_errors and retry_count < max_retries:
            return True
        
        return False
    
    def get_retry_delay(self, retry_count: int) -> float:
        """
        재시도 지연 시간 계산
        
        Args:
            retry_count: Current retry attempt
            
        Returns:
            Delay in seconds
        """
        if not self.agent_config:
            return 2.0
        
        policy = self.agent_config.retry_policy
        
        if policy.backoff == "constant":
            return policy.initial_delay
        elif policy.backoff == "linear":
            return policy.initial_delay * retry_count
        elif policy.backoff == "exponential":
            delay = policy.initial_delay * (2 ** retry_count)
            return min(delay, policy.max_delay)
        else:
            return policy.initial_delay
    
    def get_tools(self) -> List[str]:
        """
        에이전트가 사용할 수 있는 도구 목록 반환
        
        Returns:
            List of tool names
        """
        if self.agent_config:
            return self.agent_config.tools
        return []
    
    def get_capabilities(self) -> List[str]:
        """
        에이전트의 능력 목록 반환
        
        Returns:
            List of capabilities
        """
        if self.agent_config:
            return self.agent_config.capabilities
        return []
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        에이전트 실행 메트릭 반환
        
        Returns:
            Dictionary with metrics
        """
        avg_execution_time = (
            self.total_execution_time / self.execution_count 
            if self.execution_count > 0 
            else 0
        )
        
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "execution_count": self.execution_count,
            "total_execution_time": self.total_execution_time,
            "average_execution_time": avg_execution_time
        }
    
    def reset_metrics(self) -> None:
        """메트릭 초기화"""
        self.execution_count = 0
        self.total_execution_time = 0.0
        logger.info(f"[{self.name}] Metrics reset")
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id='{self.agent_id}', name='{self.name}')"