"""
Enhanced BaseAgent - 기존 BaseAgent를 확장한 개선 버전
Agent Registry와 팀 구조를 지원하는 확장 클래스
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

from .base_agent import BaseAgent
from .agent_registry import AgentCapabilities, register_agent

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent 실행 상태"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AgentExecutionResult:
    """표준화된 Agent 실행 결과"""
    status: AgentStatus
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    next_agents: List[str] = field(default_factory=list)


class EnhancedBaseAgent(BaseAgent):
    """
    기존 BaseAgent를 확장하여 Registry와 팀 구조 지원
    """

    def __init__(
        self,
        agent_name: str,
        team: Optional[str] = None,
        priority: int = 0,
        auto_register: bool = True,
        **kwargs
    ):
        """
        Enhanced BaseAgent 초기화

        Args:
            agent_name: Agent 이름
            team: 소속 팀 (optional)
            priority: 실행 우선순위
            auto_register: 자동으로 Registry에 등록할지 여부
            **kwargs: BaseAgent 추가 인자
        """
        # 기존 BaseAgent 초기화
        super().__init__(agent_name, **kwargs)

        # 확장 속성
        self.team = team
        self.priority = priority
        self.capabilities = None

        # Registry에 자동 등록
        if auto_register:
            self._register_to_registry()

    def _register_to_registry(self):
        """Agent Registry에 자동 등록"""
        from .agent_registry import AgentRegistry

        capabilities = self.get_capabilities()
        if capabilities:
            self.capabilities = AgentCapabilities(
                name=self.agent_name,
                description=capabilities.get("description", ""),
                input_types=capabilities.get("input_types", []),
                output_types=capabilities.get("output_types", []),
                required_tools=capabilities.get("required_tools", []),
                team=self.team
            )

        AgentRegistry.register(
            name=self.agent_name,
            agent_class=self.__class__,
            team=self.team,
            capabilities=self.capabilities,
            priority=self.priority,
            enabled=True
        )

        logger.info(f"Agent '{self.agent_name}' registered (team: {self.team})")

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Agent 능력 정의 (서브클래스에서 오버라이드)

        Returns:
            능력 정의 딕셔너리
        """
        return {
            "description": "Base enhanced agent",
            "input_types": ["query"],
            "output_types": ["result"],
            "required_tools": []
        }

    async def execute_with_result(
        self,
        input_data: Dict[str, Any],
        config: Optional[Dict] = None
    ) -> AgentExecutionResult:
        """
        표준화된 결과 형식으로 실행

        Args:
            input_data: 입력 데이터
            config: 실행 설정

        Returns:
            AgentExecutionResult 인스턴스
        """
        start_time = datetime.now()

        try:
            # 기존 execute 호출
            result = await self.execute(input_data, config)

            # 결과 변환
            if result["status"] == "success":
                status = AgentStatus.COMPLETED
                data = result.get("data", {})
                error = None
            else:
                status = AgentStatus.FAILED
                data = None
                error = result.get("error", "Unknown error")

            execution_time = (datetime.now() - start_time).total_seconds()

            return AgentExecutionResult(
                status=status,
                data=data,
                error=error,
                execution_time=execution_time,
                metadata={
                    "agent": self.agent_name,
                    "team": self.team,
                    "context": result.get("context", {})
                }
            )

        except Exception as e:
            logger.error(f"Agent {self.agent_name} execution failed: {e}")

            return AgentExecutionResult(
                status=AgentStatus.FAILED,
                error=str(e),
                execution_time=(datetime.now() - start_time).total_seconds(),
                metadata={"agent": self.agent_name, "team": self.team}
            )

    def suggest_next_agents(self, current_state: Dict[str, Any]) -> List[str]:
        """
        현재 상태를 기반으로 다음에 실행할 Agent 제안

        Args:
            current_state: 현재 워크플로우 상태

        Returns:
            추천 Agent 이름 목록
        """
        # 기본 구현 - 서브클래스에서 오버라이드
        return []

    def can_handle(self, input_type: str) -> bool:
        """
        특정 입력 타입을 처리할 수 있는지 확인

        Args:
            input_type: 입력 타입

        Returns:
            처리 가능 여부
        """
        if not self.capabilities:
            return False
        return input_type in self.capabilities.input_types

    def get_team_members(self) -> List[str]:
        """같은 팀의 다른 Agent들 조회"""
        if not self.team:
            return []

        from .agent_registry import AgentRegistry
        team_agents = AgentRegistry.get_team_agents(self.team)

        # 자기 자신 제외
        return [agent for agent in team_agents if agent != self.agent_name]

    async def collaborate_with(
        self,
        agent_name: str,
        input_data: Dict[str, Any]
    ) -> Optional[AgentExecutionResult]:
        """
        다른 Agent와 협업 실행

        Args:
            agent_name: 협업할 Agent 이름
            input_data: 전달할 데이터

        Returns:
            실행 결과 또는 None
        """
        from .agent_registry import AgentRegistry

        collaborator = AgentRegistry.create_agent(agent_name)
        if not collaborator:
            logger.error(f"Cannot find agent '{agent_name}' for collaboration")
            return None

        if hasattr(collaborator, 'execute_with_result'):
            return await collaborator.execute_with_result(input_data)
        else:
            # 기존 Agent와의 호환성
            result = await collaborator.execute(input_data)
            return AgentExecutionResult(
                status=AgentStatus.COMPLETED if result["status"] == "success" else AgentStatus.FAILED,
                data=result.get("data"),
                error=result.get("error"),
                metadata={"collaborator": agent_name}
            )


# 데코레이터를 통한 간편한 Agent 정의
def enhanced_agent(
    name: str,
    team: Optional[str] = None,
    priority: int = 0,
    capabilities: Optional[Dict] = None
):
    """
    Enhanced Agent 데코레이터

    Usage:
        @enhanced_agent("my_agent", team="search", priority=10)
        class MyAgent(EnhancedBaseAgent):
            pass
    """
    def decorator(agent_class):
        # 원래 __init__ 저장
        original_init = agent_class.__init__

        def new_init(self, *args, **kwargs):
            # team, priority 설정
            kwargs.setdefault('team', team)
            kwargs.setdefault('priority', priority)

            # 원래 __init__ 호출
            original_init(self, name, *args, **kwargs)

            # capabilities 설정
            if capabilities:
                self.get_capabilities = lambda: capabilities

        agent_class.__init__ = new_init
        return agent_class

    return decorator