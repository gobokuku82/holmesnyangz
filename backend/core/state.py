"""
Agent State Definition for LangGraph 0.6.6
Defines the shared state structure for all nodes and agents
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from datetime import datetime


class AgentState(TypedDict):
    """
    Comprehensive state definition for the multi-agent system
    All nodes and agents share and modify this state
    """
    
    # === 기본 상태 ===
    query: str  # 사용자의 원본 질의
    messages: Annotated[List[BaseMessage], add_messages]  # 대화 메시지 기록
    
    # === 분석 결과 ===
    intent: str  # 파악된 의도 (information_search, calculation, recommendation 등)
    entities: Dict[str, Any]  # 추출된 엔티티 (위치, 가격, 면적 등)
    confidence: float  # 분석 신뢰도 (0.0 ~ 1.0)
    query_complexity: str  # 질의 복잡도 (simple, moderate, complex)
    
    # === 계획 수립 ===
    plan: List[Dict[str, Any]]  # 실행 계획 단계별 정의
    selected_agents: List[str]  # 선택된 에이전트 ID 목록
    execution_strategy: str  # 실행 전략 (sequential, parallel, hybrid)
    priority_order: List[str]  # 에이전트 실행 우선순위
    
    # === 실행 제어 ===
    current_step: str  # 현재 실행 중인 단계
    current_agent: Optional[str]  # 현재 활성 에이전트 ID
    workflow_status: str  # 워크플로우 상태 (initialized, running, paused, completed, failed)
    execution_results: Dict[str, Any]  # 각 에이전트의 실행 결과 저장
    
    # === 에러 관리 ===
    errors: Dict[str, str]  # 에러 발생 기록 {agent_id: error_message}
    error_counts: Dict[str, int]  # 에러 타입별 카운트
    retry_attempts: int  # 재시도 횟수
    max_retries: int  # 최대 재시도 횟수
    
    # === 성능 메트릭 ===
    start_time: str  # 처리 시작 시간
    end_time: Optional[str]  # 처리 종료 시간
    execution_times: Dict[str, float]  # 각 노드/에이전트별 실행 시간
    
    # === 메타데이터 ===
    session_id: str  # 세션 고유 ID
    user_id: Optional[str]  # 사용자 ID (옵션)
    timestamp: str  # 요청 타임스탬프
    config: Dict[str, Any]  # 런타임 설정
    
    # === 응답 생성 ===
    final_response: Optional[str]  # 최종 응답 텍스트
    response_metadata: Dict[str, Any]  # 응답 메타데이터 (출처, 신뢰도 등)
    formatting_style: str  # 응답 포맷 스타일 (structured, natural, mixed)
    
    # === 컨텍스트 정보 ===
    user_context: Dict[str, Any]  # 사용자 컨텍스트 (선호도, 히스토리 등)
    domain_context: Dict[str, Any]  # 도메인 특화 컨텍스트 (부동산 관련)
    conversation_history: List[Dict[str, str]]  # 이전 대화 기록


class ExecutionPlan(TypedDict):
    """실행 계획의 각 단계를 정의"""
    step_id: str  # 단계 ID
    agent_id: str  # 실행할 에이전트 ID
    action: str  # 수행할 작업
    parameters: Dict[str, Any]  # 작업 파라미터
    dependencies: List[str]  # 의존하는 다른 단계 ID
    timeout: int  # 타임아웃 (초)
    retry_policy: Dict[str, Any]  # 재시도 정책


class AgentResult(TypedDict):
    """에이전트 실행 결과 구조"""
    agent_id: str  # 에이전트 ID
    status: str  # 실행 상태 (success, failed, timeout)
    result: Any  # 실행 결과 데이터
    confidence: float  # 결과 신뢰도
    execution_time: float  # 실행 시간 (초)
    error: Optional[str]  # 에러 메시지 (실패 시)
    metadata: Dict[str, Any]  # 추가 메타데이터


# 상태 초기화 함수
def create_initial_state(query: str, user_id: Optional[str] = None) -> AgentState:
    """초기 상태 생성"""
    import uuid
    
    return AgentState(
        # 기본 상태
        query=query,
        messages=[],
        
        # 분석 결과 (초기값)
        intent="",
        entities={},
        confidence=0.0,
        query_complexity="simple",
        
        # 계획 수립 (초기값)
        plan=[],
        selected_agents=[],
        execution_strategy="sequential",
        priority_order=[],
        
        # 실행 제어
        current_step="initialization",
        current_agent=None,
        workflow_status="initialized",
        execution_results={},
        
        # 에러 관리
        errors={},
        error_counts={},
        retry_attempts=0,
        max_retries=3,
        
        # 성능 메트릭
        start_time=datetime.now().isoformat(),
        end_time=None,
        execution_times={},
        
        # 메타데이터
        session_id=str(uuid.uuid4()),
        user_id=user_id,
        timestamp=datetime.now().isoformat(),
        config={},
        
        # 응답 생성
        final_response=None,
        response_metadata={},
        formatting_style="structured",
        
        # 컨텍스트
        user_context={},
        domain_context={},
        conversation_history=[]
    )


# 상태 유효성 검증
def validate_state(state: AgentState) -> tuple[bool, List[str]]:
    """
    상태 유효성 검증
    Returns: (is_valid, error_messages)
    """
    errors = []
    
    # 필수 필드 체크
    required_fields = ["query", "session_id", "workflow_status", "messages"]
    for field in required_fields:
        if field not in state or state[field] is None:
            errors.append(f"Missing required field: {field}")
    
    # 워크플로우 상태 검증
    valid_statuses = ["initialized", "running", "paused", "completed", "failed"]
    if state.get("workflow_status") not in valid_statuses:
        errors.append(f"Invalid workflow_status: {state.get('workflow_status')}")
    
    # 신뢰도 범위 검증
    confidence = state.get("confidence", 0)
    if not 0 <= confidence <= 1:
        errors.append(f"Confidence must be between 0 and 1, got: {confidence}")
    
    return len(errors) == 0, errors