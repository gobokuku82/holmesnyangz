"""
Workflow Tracker
워크플로우 실행 상태 추적 및 WebSocket 브로드캐스트
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class WorkflowStage(str, Enum):
    """워크플로우 단계"""
    IDLE = "idle"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ERROR = "error"


class AgentStatus(str, Enum):
    """에이전트 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class WorkflowTracker:
    """
    워크플로우 실행 추적기
    각 단계별 진행 상황과 에이전트 실행을 추적
    """
    
    def __init__(self, session_id: str, thread_id: str):
        """
        Args:
            session_id: 세션 ID
            thread_id: 스레드 ID
        """
        self.session_id = session_id
        self.thread_id = thread_id
        self.current_stage = WorkflowStage.IDLE
        self.stage_progress = 0.0
        self.agents_sequence: List[Dict[str, Any]] = []
        self.current_agent_index = -1
        self.agent_progress = 0.0
        self.start_time = None
        self.stage_times: Dict[str, float] = {}
        self.listeners: List[Callable] = []
        self.message = ""
        
    def add_listener(self, callback: Callable):
        """이벤트 리스너 추가"""
        self.listeners.append(callback)
    
    def remove_listener(self, callback: Callable):
        """이벤트 리스너 제거"""
        if callback in self.listeners:
            self.listeners.remove(callback)
    
    async def _broadcast_update(self):
        """현재 상태를 모든 리스너에게 브로드캐스트"""
        event = self.get_current_state()
        
        for listener in self.listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event)
                else:
                    listener(event)
            except Exception as e:
                logger.error(f"Failed to broadcast to listener: {e}")
    
    def get_current_state(self) -> Dict[str, Any]:
        """현재 워크플로우 상태 반환"""
        current_agent = None
        if 0 <= self.current_agent_index < len(self.agents_sequence):
            current_agent = self.agents_sequence[self.current_agent_index]
        
        return {
            "type": "workflow_update",
            "session_id": self.session_id,
            "thread_id": self.thread_id,
            "stage": self.current_stage.value,
            "stage_progress": self.stage_progress,
            "agents_sequence": self.agents_sequence,
            "current_agent": current_agent.get("id") if current_agent else None,
            "current_agent_index": self.current_agent_index,
            "agent_progress": self.agent_progress,
            "message": self.message,
            "timestamp": datetime.now().isoformat(),
            "elapsed_time": self._get_elapsed_time()
        }
    
    def _get_elapsed_time(self) -> float:
        """경과 시간 계산"""
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0.0
    
    async def start_workflow(self):
        """워크플로우 시작"""
        self.start_time = datetime.now()
        self.current_stage = WorkflowStage.ANALYZING
        self.stage_progress = 0.0
        self.message = "워크플로우를 시작합니다..."
        logger.info(f"Workflow started for thread {self.thread_id}")
        await self._broadcast_update()
    
    async def update_analyzing(self, progress: float, message: str = ""):
        """분석 단계 업데이트"""
        self.current_stage = WorkflowStage.ANALYZING
        self.stage_progress = min(progress, 100.0)
        self.message = message or "사용자 의도를 분석하고 있습니다..."
        
        if progress >= 100:
            self.stage_times["analyzing"] = self._get_elapsed_time()
            
        await self._broadcast_update()
    
    async def update_planning(self, progress: float, selected_agents: List[Dict[str, Any]], message: str = ""):
        """계획 단계 업데이트"""
        self.current_stage = WorkflowStage.PLANNING
        self.stage_progress = min(progress, 100.0)
        self.message = message or "실행 계획을 수립하고 있습니다..."
        
        # 에이전트 시퀀스 설정
        if selected_agents and not self.agents_sequence:
            self.agents_sequence = [
                {
                    "id": agent.get("id"),
                    "name": agent.get("name"),
                    "order": idx,
                    "status": AgentStatus.PENDING.value,
                    "progress": 0.0,
                    "start_time": None,
                    "end_time": None,
                    "result": None
                }
                for idx, agent in enumerate(selected_agents)
            ]
        
        if progress >= 100:
            self.stage_times["planning"] = self._get_elapsed_time()
            
        await self._broadcast_update()
    
    async def start_execution(self):
        """실행 단계 시작"""
        self.current_stage = WorkflowStage.EXECUTING
        self.stage_progress = 0.0
        self.current_agent_index = 0
        self.message = "에이전트를 실행하고 있습니다..."
        
        # 첫 번째 에이전트 상태 업데이트
        if self.agents_sequence:
            self.agents_sequence[0]["status"] = AgentStatus.RUNNING.value
            self.agents_sequence[0]["start_time"] = datetime.now().isoformat()
        
        await self._broadcast_update()
    
    async def update_agent_progress(self, agent_id: str, progress: float, message: str = ""):
        """에이전트 진행 상황 업데이트"""
        # 현재 에이전트 찾기
        for idx, agent in enumerate(self.agents_sequence):
            if agent["id"] == agent_id:
                self.current_agent_index = idx
                agent["progress"] = min(progress, 100.0)
                
                if agent["status"] != AgentStatus.RUNNING.value:
                    agent["status"] = AgentStatus.RUNNING.value
                    agent["start_time"] = datetime.now().isoformat()
                
                # 전체 실행 진행률 계산
                completed_agents = sum(1 for a in self.agents_sequence if a["status"] == AgentStatus.COMPLETED.value)
                total_agents = len(self.agents_sequence)
                
                if total_agents > 0:
                    base_progress = (completed_agents / total_agents) * 100
                    current_agent_contribution = (progress / 100.0) * (100.0 / total_agents)
                    self.stage_progress = base_progress + current_agent_contribution
                
                self.agent_progress = progress
                self.message = message or f"{agent['name']} 실행 중..."
                
                if progress >= 100:
                    await self.complete_agent(agent_id)
                else:
                    await self._broadcast_update()
                break
    
    async def complete_agent(self, agent_id: str, result: Any = None):
        """에이전트 완료"""
        for idx, agent in enumerate(self.agents_sequence):
            if agent["id"] == agent_id:
                agent["status"] = AgentStatus.COMPLETED.value
                agent["progress"] = 100.0
                agent["end_time"] = datetime.now().isoformat()
                agent["result"] = result
                
                # 다음 에이전트로 이동
                if idx + 1 < len(self.agents_sequence):
                    self.current_agent_index = idx + 1
                    next_agent = self.agents_sequence[idx + 1]
                    next_agent["status"] = AgentStatus.RUNNING.value
                    next_agent["start_time"] = datetime.now().isoformat()
                    self.agent_progress = 0.0
                    self.message = f"{next_agent['name']} 실행 중..."
                else:
                    # 모든 에이전트 완료
                    self.stage_progress = 100.0
                    await self.complete_workflow()
                    return
                
                await self._broadcast_update()
                break
    
    async def fail_agent(self, agent_id: str, error: str):
        """에이전트 실패"""
        for agent in self.agents_sequence:
            if agent["id"] == agent_id:
                agent["status"] = AgentStatus.ERROR.value
                agent["end_time"] = datetime.now().isoformat()
                agent["error"] = error
                break
        
        self.current_stage = WorkflowStage.ERROR
        self.message = f"에이전트 실행 실패: {error}"
        await self._broadcast_update()
    
    async def complete_workflow(self, message: str = ""):
        """워크플로우 완료"""
        self.current_stage = WorkflowStage.COMPLETED
        self.stage_progress = 100.0
        self.message = message or "워크플로우가 성공적으로 완료되었습니다!"
        self.stage_times["executing"] = self._get_elapsed_time()
        
        logger.info(f"Workflow completed for thread {self.thread_id}")
        logger.info(f"Total time: {self._get_elapsed_time():.2f}s")
        logger.info(f"Agents executed: {[a['id'] for a in self.agents_sequence]}")
        
        await self._broadcast_update()
    
    async def fail_workflow(self, error: str):
        """워크플로우 실패"""
        self.current_stage = WorkflowStage.ERROR
        self.message = f"워크플로우 실패: {error}"
        
        logger.error(f"Workflow failed for thread {self.thread_id}: {error}")
        
        await self._broadcast_update()
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """실행 요약 정보 반환"""
        completed_agents = [a for a in self.agents_sequence if a["status"] == AgentStatus.COMPLETED.value]
        failed_agents = [a for a in self.agents_sequence if a["status"] == AgentStatus.ERROR.value]
        
        return {
            "session_id": self.session_id,
            "thread_id": self.thread_id,
            "status": self.current_stage.value,
            "total_time": self._get_elapsed_time(),
            "stage_times": self.stage_times,
            "total_agents": len(self.agents_sequence),
            "completed_agents": len(completed_agents),
            "failed_agents": len(failed_agents),
            "agents_summary": [
                {
                    "id": agent["id"],
                    "name": agent["name"],
                    "status": agent["status"],
                    "progress": agent["progress"],
                    "duration": self._calculate_agent_duration(agent)
                }
                for agent in self.agents_sequence
            ]
        }
    
    def _calculate_agent_duration(self, agent: Dict[str, Any]) -> Optional[float]:
        """에이전트 실행 시간 계산"""
        if agent.get("start_time") and agent.get("end_time"):
            start = datetime.fromisoformat(agent["start_time"])
            end = datetime.fromisoformat(agent["end_time"])
            return (end - start).total_seconds()
        return None


class WorkflowTrackerManager:
    """워크플로우 추적기 관리자"""
    
    def __init__(self):
        self.trackers: Dict[str, WorkflowTracker] = {}
    
    def create_tracker(self, session_id: str, thread_id: str) -> WorkflowTracker:
        """새 추적기 생성"""
        tracker = WorkflowTracker(session_id, thread_id)
        self.trackers[thread_id] = tracker
        return tracker
    
    def get_tracker(self, thread_id: str) -> Optional[WorkflowTracker]:
        """추적기 조회"""
        return self.trackers.get(thread_id)
    
    def remove_tracker(self, thread_id: str):
        """추적기 제거"""
        if thread_id in self.trackers:
            del self.trackers[thread_id]
    
    def get_all_trackers(self) -> Dict[str, WorkflowTracker]:
        """모든 추적기 반환"""
        return self.trackers
    
    def cleanup_old_trackers(self, max_age_hours: int = 24):
        """오래된 추적기 정리"""
        current_time = datetime.now()
        to_remove = []
        
        for thread_id, tracker in self.trackers.items():
            if tracker.start_time:
                age = (current_time - tracker.start_time).total_seconds() / 3600
                if age > max_age_hours:
                    to_remove.append(thread_id)
        
        for thread_id in to_remove:
            self.remove_tracker(thread_id)
            logger.info(f"Removed old tracker for thread {thread_id}")


# 싱글톤 인스턴스
_tracker_manager = WorkflowTrackerManager()


def get_tracker_manager() -> WorkflowTrackerManager:
    """추적기 관리자 인스턴스 반환"""
    return _tracker_manager