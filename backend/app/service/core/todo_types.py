"""
TODO Management Types for Hierarchical Agent System
====================================================

계층적 Agent 시스템을 위한 TODO 관리 타입 정의
각 레벨(Supervisor, Agent, Tool)별로 독립적인 TODO 관리
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class TodoStatus(Enum):
    """TODO 상태"""
    PENDING = "pending"          # 대기 중
    IN_PROGRESS = "in_progress"  # 진행 중
    COMPLETED = "completed"      # 완료
    FAILED = "failed"           # 실패
    SKIPPED = "skipped"         # 건너뜀
    BLOCKED = "blocked"         # 차단됨


class TodoPriority(Enum):
    """TODO 우선순위"""
    CRITICAL = "critical"  # 매우 중요
    HIGH = "high"         # 높음
    MEDIUM = "medium"     # 보통
    LOW = "low"          # 낮음


@dataclass
class TodoItem:
    """
    기본 TODO 항목
    모든 레벨에서 사용하는 공통 구조
    """
    id: str                                    # 고유 ID
    name: str                                   # 작업 이름
    description: str                            # 상세 설명
    status: TodoStatus = TodoStatus.PENDING    # 현재 상태
    priority: TodoPriority = TodoPriority.MEDIUM  # 우선순위

    # 시간 추적
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 메타데이터
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None  # 실패 시 에러 메시지

    def start(self):
        """작업 시작"""
        self.status = TodoStatus.IN_PROGRESS
        self.started_at = datetime.now()

    def complete(self):
        """작업 완료"""
        self.status = TodoStatus.COMPLETED
        self.completed_at = datetime.now()

    def fail(self, error: str):
        """작업 실패"""
        self.status = TodoStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()

    def skip(self, reason: str = None):
        """작업 건너뛰기"""
        self.status = TodoStatus.SKIPPED
        if reason:
            self.error = f"Skipped: {reason}"

    def block(self, reason: str):
        """작업 차단"""
        self.status = TodoStatus.BLOCKED
        self.error = f"Blocked: {reason}"

    @property
    def duration(self) -> Optional[float]:
        """작업 소요 시간 (초)"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration,
            "metadata": self.metadata,
            "error": self.error
        }


@dataclass
class SupervisorTodo(TodoItem):
    """
    Supervisor 레벨 TODO
    전략적 계획 (어떤 Agent를 실행할지)
    """
    agent_name: str = ""                      # 실행할 Agent 이름
    agent_purpose: str = ""                   # Agent 실행 목적
    expected_output: str = ""                 # 예상 출력
    dependencies: List[str] = field(default_factory=list)  # 의존성 (다른 TODO ID)

    def can_start(self, completed_todos: List[str]) -> bool:
        """시작 가능 여부 확인"""
        return all(dep in completed_todos for dep in self.dependencies)


@dataclass
class AgentTodo(TodoItem):
    """
    Agent 레벨 TODO
    실행 계획 (어떤 노드/도구를 실행할지)
    """
    node_name: str = ""                       # 실행할 노드 이름
    tool_names: List[str] = field(default_factory=list)  # 사용할 도구들
    input_data: Dict[str, Any] = field(default_factory=dict)  # 입력 데이터
    output_data: Dict[str, Any] = field(default_factory=dict)  # 출력 데이터

    def add_tool_result(self, tool_name: str, result: Any):
        """도구 실행 결과 추가"""
        if "tool_results" not in self.output_data:
            self.output_data["tool_results"] = {}
        self.output_data["tool_results"][tool_name] = result


@dataclass
class ToolTodo(TodoItem):
    """
    Tool 레벨 TODO
    구체적 작업 (API 호출, 데이터 처리 등)
    """
    tool_name: str = ""                       # 도구 이름
    operation: str = ""                       # 수행할 작업
    parameters: Dict[str, Any] = field(default_factory=dict)  # 파라미터
    result: Any = None                        # 실행 결과
    retry_count: int = 0                      # 재시도 횟수
    max_retries: int = 3                      # 최대 재시도

    def should_retry(self) -> bool:
        """재시도 필요 여부"""
        return self.status == TodoStatus.FAILED and self.retry_count < self.max_retries

    def retry(self):
        """재시도"""
        self.retry_count += 1
        self.status = TodoStatus.PENDING
        self.error = None


class TodoManager:
    """
    TODO 관리자
    각 레벨에서 TODO를 관리하는 유틸리티 클래스
    """

    def __init__(self, level: str = "supervisor"):
        """
        Args:
            level: 관리 레벨 (supervisor, agent, tool)
        """
        self.level = level
        self.todos: List[TodoItem] = []
        self.completed_ids: List[str] = []

    def add_todo(self, todo: TodoItem) -> str:
        """TODO 추가"""
        self.todos.append(todo)
        return todo.id

    def get_todo(self, todo_id: str) -> Optional[TodoItem]:
        """TODO 조회"""
        for todo in self.todos:
            if todo.id == todo_id:
                return todo
        return None

    def update_status(self, todo_id: str, status: TodoStatus, error: str = None):
        """TODO 상태 업데이트"""
        todo = self.get_todo(todo_id)
        if todo:
            if status == TodoStatus.IN_PROGRESS:
                todo.start()
            elif status == TodoStatus.COMPLETED:
                todo.complete()
                self.completed_ids.append(todo_id)
            elif status == TodoStatus.FAILED:
                todo.fail(error or "Unknown error")
            else:
                todo.status = status

    def get_pending_todos(self) -> List[TodoItem]:
        """대기 중인 TODO 목록"""
        return [t for t in self.todos if t.status == TodoStatus.PENDING]

    def get_next_todo(self) -> Optional[TodoItem]:
        """다음 실행할 TODO"""
        pending = self.get_pending_todos()

        # SupervisorTodo의 경우 의존성 확인
        if self.level == "supervisor":
            for todo in pending:
                if isinstance(todo, SupervisorTodo):
                    if todo.can_start(self.completed_ids):
                        return todo
                else:
                    return todo

        # 우선순위 순으로 반환
        if pending:
            return sorted(pending, key=lambda x: x.priority.value)[0]
        return None

    def get_progress(self) -> Dict[str, Any]:
        """진행 상황 요약"""
        total = len(self.todos)
        if total == 0:
            return {
                "total": 0,
                "completed": 0,
                "in_progress": 0,
                "failed": 0,
                "progress_percent": 0
            }

        completed = len([t for t in self.todos if t.status == TodoStatus.COMPLETED])
        in_progress = len([t for t in self.todos if t.status == TodoStatus.IN_PROGRESS])
        failed = len([t for t in self.todos if t.status == TodoStatus.FAILED])

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "failed": failed,
            "pending": total - completed - in_progress - failed,
            "progress_percent": round(completed / total * 100, 1)
        }

    def get_summary(self) -> str:
        """텍스트 요약"""
        progress = self.get_progress()
        return (f"[{self.level.upper()}] "
                f"{progress['completed']}/{progress['total']} completed "
                f"({progress['progress_percent']}%)")

    def to_list(self) -> List[Dict[str, Any]]:
        """모든 TODO를 리스트로 반환"""
        return [todo.to_dict() for todo in self.todos]

    def clear_completed(self):
        """완료된 TODO 제거"""
        self.todos = [t for t in self.todos
                     if t.status not in [TodoStatus.COMPLETED, TodoStatus.SKIPPED]]


# ============================================================================
# Helper Functions
# ============================================================================

def create_supervisor_todo(
    agent_name: str,
    purpose: str,
    priority: TodoPriority = TodoPriority.MEDIUM,
    dependencies: List[str] = None
) -> SupervisorTodo:
    """Supervisor TODO 생성 헬퍼"""
    import uuid

    return SupervisorTodo(
        id=f"sup_{uuid.uuid4().hex[:8]}",
        name=f"Execute {agent_name}",
        description=purpose,
        agent_name=agent_name,
        agent_purpose=purpose,
        priority=priority,
        dependencies=dependencies or []
    )


def create_agent_todo(
    node_name: str,
    description: str,
    tools: List[str] = None,
    priority: TodoPriority = TodoPriority.MEDIUM
) -> AgentTodo:
    """Agent TODO 생성 헬퍼"""
    import uuid

    return AgentTodo(
        id=f"agt_{uuid.uuid4().hex[:8]}",
        name=f"Execute {node_name}",
        description=description,
        node_name=node_name,
        tool_names=tools or [],
        priority=priority
    )


def create_tool_todo(
    tool_name: str,
    operation: str,
    parameters: Dict[str, Any] = None,
    priority: TodoPriority = TodoPriority.MEDIUM
) -> ToolTodo:
    """Tool TODO 생성 헬퍼"""
    import uuid

    return ToolTodo(
        id=f"tool_{uuid.uuid4().hex[:8]}",
        name=f"{tool_name}: {operation}",
        description=f"Execute {operation} with {tool_name}",
        tool_name=tool_name,
        operation=operation,
        parameters=parameters or {},
        priority=priority
    )


# ============================================================================
# State-based TODO Management (for LangGraph State)
# ============================================================================

def merge_todos(existing: List[Dict[str, Any]], new: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    TODO 리스트 병합을 위한 Reducer 함수
    LangGraph State의 Annotated 필드에서 사용

    Args:
        existing: 기존 TODO 리스트
        new: 새로운/업데이트된 TODO 리스트

    Returns:
        병합된 TODO 리스트
    """
    if not existing:
        return new
    if not new:
        return existing

    # ID를 키로 하는 맵 생성
    todo_map = {}

    # 기존 TODO를 맵에 추가
    for todo in existing:
        todo_map[todo["id"]] = todo

    # 새 TODO로 업데이트 또는 추가
    for todo in new:
        todo_id = todo["id"]
        if todo_id in todo_map:
            # 기존 TODO 업데이트
            existing_todo = todo_map[todo_id]

            # subtodos가 있으면 재귀적으로 병합
            if "subtodos" in todo and "subtodos" in existing_todo:
                todo["subtodos"] = merge_todos(
                    existing_todo.get("subtodos", []),
                    todo.get("subtodos", [])
                )

            # tool_todos도 병합
            if "tool_todos" in todo and "tool_todos" in existing_todo:
                todo["tool_todos"] = merge_todos(
                    existing_todo.get("tool_todos", []),
                    todo.get("tool_todos", [])
                )

            # 업데이트
            existing_todo.update(todo)
        else:
            # 새 TODO 추가
            todo_map[todo_id] = todo

    return list(todo_map.values())


def create_todo_dict(
    todo_id: str,
    level: str,
    task: str,
    status: str = "pending",
    **kwargs
) -> Dict[str, Any]:
    """
    TODO 딕셔너리 생성 헬퍼

    Args:
        todo_id: 고유 ID
        level: 레벨 (supervisor, agent, tool)
        task: 작업 설명
        status: 상태
        **kwargs: 추가 필드

    Returns:
        TODO 딕셔너리
    """
    from datetime import datetime

    todo = {
        "id": todo_id,
        "level": level,
        "task": task,
        "status": status,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    # 추가 필드
    todo.update(kwargs)

    return todo


def update_todo_status(
    todos: List[Dict[str, Any]],
    todo_id: str,
    status: str,
    error: str = None
) -> List[Dict[str, Any]]:
    """
    TODO 상태 업데이트 헬퍼

    Args:
        todos: TODO 리스트
        todo_id: 업데이트할 TODO ID
        status: 새 상태
        error: 에러 메시지 (실패 시)

    Returns:
        업데이트된 TODO 리스트
    """
    from datetime import datetime

    for todo in todos:
        if todo["id"] == todo_id:
            todo["status"] = status
            todo["updated_at"] = datetime.now().isoformat()
            if error:
                todo["error"] = error
            if status == "in_progress" and "started_at" not in todo:
                todo["started_at"] = datetime.now().isoformat()
            elif status in ["completed", "failed"]:
                todo["completed_at"] = datetime.now().isoformat()

        # Subtodos 재귀 확인
        if "subtodos" in todo:
            update_todo_status(todo["subtodos"], todo_id, status, error)

        # Tool todos 확인
        if "tool_todos" in todo:
            update_todo_status(todo["tool_todos"], todo_id, status, error)

    return todos


def find_todo(
    todos: List[Dict[str, Any]],
    todo_id: str = None,
    agent: str = None,
    level: str = None
) -> Optional[Dict[str, Any]]:
    """
    TODO 찾기 헬퍼

    Args:
        todos: TODO 리스트
        todo_id: 찾을 TODO ID
        agent: Agent 이름으로 찾기
        level: 레벨로 찾기

    Returns:
        찾은 TODO 또는 None
    """
    for todo in todos:
        # ID로 찾기
        if todo_id and todo["id"] == todo_id:
            return todo

        # Agent로 찾기
        if agent and todo.get("agent") == agent:
            return todo

        # Level로 찾기
        if level and todo.get("level") == level:
            return todo

        # Subtodos에서 재귀 검색
        if "subtodos" in todo:
            result = find_todo(todo["subtodos"], todo_id, agent, level)
            if result:
                return result

        # Tool todos에서 검색
        if "tool_todos" in todo:
            result = find_todo(todo["tool_todos"], todo_id, agent, level)
            if result:
                return result

    return None


def get_todo_summary(todos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    TODO 진행 상황 요약

    Args:
        todos: TODO 리스트

    Returns:
        진행 상황 요약
    """
    def count_todos(todo_list):
        counts = {"total": 0, "completed": 0, "in_progress": 0, "failed": 0, "pending": 0}

        for todo in todo_list:
            counts["total"] += 1
            status = todo.get("status", "pending")
            if status in counts:
                counts[status] += 1

            # Subtodos 카운트
            if "subtodos" in todo:
                sub_counts = count_todos(todo["subtodos"])
                for key in counts:
                    counts[key] += sub_counts[key]

            # Tool todos 카운트
            if "tool_todos" in todo:
                tool_counts = count_todos(todo["tool_todos"])
                for key in counts:
                    counts[key] += tool_counts[key]

        return counts

    counts = count_todos(todos)

    # 진행률 계산
    if counts["total"] > 0:
        progress_percent = round(counts["completed"] / counts["total"] * 100, 1)
    else:
        progress_percent = 0

    return {
        **counts,
        "progress_percent": progress_percent,
        "summary": f"{counts['completed']}/{counts['total']} completed ({progress_percent}%)"
    }


if __name__ == "__main__":
    # State 기반 TODO 테스트
    todos = []

    # Supervisor TODO 생성
    main_todo = create_todo_dict(
        "main_1",
        "supervisor",
        "Execute search_agent",
        agent="search_agent",
        subtodos=[]
    )
    todos.append(main_todo)

    # Agent가 subtodos 추가
    main_todo["subtodos"] = [
        create_todo_dict("sub_1", "agent", "create_search_plan", "completed"),
        create_todo_dict("sub_2", "agent", "execute_tools", "in_progress",
                        tool_todos=[
                            create_todo_dict("tool_1", "tool", "legal_search", "completed"),
                            create_todo_dict("tool_2", "tool", "loan_search", "pending")
                        ])
    ]

    # 요약 출력
    summary = get_todo_summary(todos)
    print(f"Progress: {summary['summary']}")
    print(f"Details: {summary}")