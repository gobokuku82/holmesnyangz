"""
Separated State Definitions for Team-based Architecture
각 팀별로 독립적인 State를 정의하여 State pollution을 방지
"""

from typing import TypedDict, Dict, List, Any, Optional, Literal
from datetime import datetime


class SearchKeywords(TypedDict):
    """검색 키워드 구조"""
    legal: List[str]
    real_estate: List[str]
    loan: List[str]
    general: List[str]


class SharedState(TypedDict):
    """모든 팀이 공유하는 최소한의 상태"""
    user_query: str
    session_id: str
    timestamp: str
    language: str
    status: Literal["pending", "processing", "completed", "error"]
    error_message: Optional[str]


class SearchTeamState(TypedDict):
    """검색 팀 전용 State"""
    # Team identification
    team_name: str
    status: str

    # Shared context
    shared_context: Dict[str, Any]

    # Search specific
    keywords: Optional[SearchKeywords]
    search_scope: List[str]  # ["legal", "real_estate", "loan"]
    filters: Dict[str, Any]

    # Search results
    legal_results: List[Dict[str, Any]]
    real_estate_results: List[Dict[str, Any]]
    loan_results: List[Dict[str, Any]]
    aggregated_results: Dict[str, Any]

    # Metadata
    total_results: int
    search_time: float
    sources_used: List[str]
    search_progress: Dict[str, str]

    # Execution tracking
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    error: Optional[str]
    current_search: Optional[str]
    execution_strategy: Optional[str]


class DocumentTemplate(TypedDict):
    """문서 템플릿 구조"""
    template_id: str
    template_name: str
    template_content: str
    placeholders: List[str]


class DocumentContent(TypedDict):
    """문서 내용 구조"""
    title: str
    content: str
    metadata: Dict[str, Any]
    created_at: str


class ReviewResult(TypedDict):
    """검토 결과 구조"""
    reviewed: bool
    risk_level: str  # "low", "medium", "high"
    risks: List[Dict[str, Any]]
    recommendations: List[str]
    compliance_check: Dict[str, bool]


class DocumentTeamState(TypedDict):
    """문서 팀 전용 State"""
    # Team identification
    team_name: str
    status: str

    # Shared context
    shared_context: Dict[str, Any]

    # Document specific
    document_type: str  # "lease_contract", "sales_contract", etc.
    template: Optional[DocumentTemplate]
    document_content: Optional[DocumentContent]
    generation_progress: Dict[str, str]

    # Review specific
    review_needed: bool
    review_result: Optional[ReviewResult]
    final_document: Optional[str]

    # Timing
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    generation_time: Optional[float]
    review_time: Optional[float]

    # Error tracking
    error: Optional[str]


class AnalysisInput(TypedDict):
    """분석 입력 구조"""
    data_source: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]


class AnalysisMetrics(TypedDict):
    """분석 지표 구조"""
    avg_price: Optional[float]
    max_price: Optional[float]
    min_price: Optional[float]
    price_trend: Optional[str]
    risk_score: Optional[float]
    investment_score: Optional[float]


class AnalysisInsight(TypedDict):
    """분석 인사이트 구조"""
    insight_type: str
    content: str
    confidence: float
    supporting_data: Dict[str, Any]


class AnalysisReport(TypedDict):
    """분석 보고서 구조"""
    title: str
    summary: str
    sections: List[Dict[str, Any]]
    metrics: AnalysisMetrics
    insights: List[AnalysisInsight]
    recommendations: List[str]


class AnalysisTeamState(TypedDict):
    """분석 팀 전용 State"""
    # Team identification
    team_name: str
    status: str

    # Shared context
    shared_context: Dict[str, Any]

    # Analysis specific
    analysis_type: str  # "market", "risk", "comprehensive", etc.
    input_data: Dict[str, Any]

    # Analysis results
    metrics: Dict[str, float]
    insights: List[str]
    report: Dict[str, Any]
    visualization_data: Optional[Dict[str, Any]]
    recommendations: List[str]
    confidence_score: float

    # Progress tracking
    analysis_progress: Dict[str, str]

    # Timing
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    analysis_time: Optional[float]

    # Error tracking
    error: Optional[str]


class PlanningState(TypedDict):
    """계획 수립 전용 State"""
    raw_query: str
    analyzed_intent: Dict[str, Any]
    intent_confidence: float
    available_agents: List[str]
    available_teams: List[str]
    execution_steps: List[Dict[str, Any]]
    execution_strategy: str
    parallel_groups: Optional[List[List[str]]]
    plan_validated: bool
    validation_errors: List[str]
    estimated_total_time: float


class MainSupervisorState(TypedDict):
    """메인 Supervisor의 State"""
    # Core fields
    query: str
    session_id: str
    request_id: str

    # Planning
    planning_state: Optional[PlanningState]
    execution_plan: Optional[Dict[str, Any]]

    # Team states
    search_team_state: Optional[Dict[str, Any]]
    document_team_state: Optional[Dict[str, Any]]
    analysis_team_state: Optional[Dict[str, Any]]

    # Execution tracking
    current_phase: str
    active_teams: List[str]
    completed_teams: List[str]
    failed_teams: List[str]

    # Results
    team_results: Dict[str, Any]
    aggregated_results: Dict[str, Any]
    final_response: Optional[Dict[str, Any]]

    # Timing
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    total_execution_time: Optional[float]

    # Error handling
    error_log: List[str]
    status: str


class StateManager:
    """State 변환 및 관리 유틸리티"""

    @staticmethod
    def create_shared_state(
        query: str,
        session_id: str,
        language: str = "ko",
        timestamp: Optional[str] = None
    ) -> SharedState:
        """공유 State 생성"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        return SharedState(
            user_query=query,
            session_id=session_id,
            timestamp=timestamp,
            language=language,
            status="pending",
            error_message=None
        )

    @staticmethod
    def extract_shared_state(state: Dict[str, Any]) -> SharedState:
        """전체 State에서 공유 State만 추출"""
        return SharedState(
            user_query=state.get("user_query", ""),
            session_id=state.get("session_id", ""),
            timestamp=state.get("timestamp", datetime.now().isoformat()),
            language=state.get("language", "ko"),
            status=state.get("status", "pending"),
            error_message=state.get("error_message")
        )

    @staticmethod
    def merge_team_results(
        main_state: MainSupervisorState,
        team_name: str,
        team_result: Dict[str, Any]
    ) -> MainSupervisorState:
        """팀 결과를 메인 State에 병합"""
        # Store team result
        main_state["team_results"][team_name] = team_result

        # Update completed/failed teams
        if team_result.get("status") in ["completed", "success"]:
            if team_name not in main_state["completed_teams"]:
                main_state["completed_teams"].append(team_name)
        else:
            if team_name not in main_state["failed_teams"]:
                main_state["failed_teams"].append(team_name)

        # Remove from active teams
        if team_name in main_state["active_teams"]:
            main_state["active_teams"].remove(team_name)

        return main_state

    @staticmethod
    def merge_team_result(
        main_state: MainSupervisorState,
        team_name: str,
        team_result: Dict[str, Any]
    ) -> MainSupervisorState:
        """팀 결과를 메인 State에 병합"""
        if team_name == "search":
            main_state["search_team_result"] = team_result
        elif team_name == "document":
            main_state["document_team_result"] = team_result
        elif team_name == "analysis":
            main_state["analysis_team_result"] = team_result

        # Update completed teams
        if team_name not in main_state["completed_teams"]:
            main_state["completed_teams"].append(team_name)

        # Remove from active teams
        if team_name in main_state["active_teams"]:
            main_state["active_teams"].remove(team_name)

        return main_state

    @staticmethod
    def create_initial_team_state(
        team_type: str,
        shared_state: SharedState,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """팀별 초기 State 생성"""

        base_state = dict(shared_state)

        if team_type == "search":
            state = SearchTeamState(
                **base_state,
                search_keywords=[],
                search_scope=["legal", "real_estate", "loan"],
                search_results={},
                legal_search_results=None,
                real_estate_search_results=None,
                loan_search_results=None,
                search_metadata={},
                execution_step="initialized"
            )

        elif team_type == "document":
            state = DocumentTeamState(
                **base_state,
                document_type=additional_data.get("document_type", "contract") if additional_data else "contract",
                document_template=None,
                document_data={},
                generated_document=None,
                review_needed=True,
                review_results=None,
                review_risks=None,
                review_recommendations=None,
                final_document=None,
                execution_step="initialized"
            )

        elif team_type == "analysis":
            state = AnalysisTeamState(
                **base_state,
                analysis_type=additional_data.get("analysis_type", "comprehensive") if additional_data else "comprehensive",
                analysis_input={},
                analysis_metrics={},
                analysis_insights=[],
                analysis_report=None,
                visualization_data=None,
                recommendations=None,
                confidence_score=None,
                execution_step="initialized"
            )

        else:
            raise ValueError(f"Unknown team type: {team_type}")

        # Add any additional data
        if additional_data:
            state.update(additional_data)

        return state


class StateValidator:
    """State 유효성 검증"""

    @staticmethod
    def validate_search_state(state: Dict[str, Any]) -> tuple[bool, List[str]]:
        """검색 팀 State 검증"""
        errors = []

        if not state.get("user_query"):
            errors.append("user_query is required")

        if not state.get("session_id"):
            errors.append("session_id is required")

        search_scope = state.get("search_scope", [])
        valid_scopes = ["legal", "real_estate", "loan"]
        for scope in search_scope:
            if scope not in valid_scopes:
                errors.append(f"Invalid search scope: {scope}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_document_state(state: Dict[str, Any]) -> tuple[bool, List[str]]:
        """문서 팀 State 검증"""
        errors = []

        if not state.get("user_query"):
            errors.append("user_query is required")

        if not state.get("document_type"):
            errors.append("document_type is required")

        valid_types = ["contract", "agreement", "report", "notice", "application"]
        if state.get("document_type") not in valid_types:
            errors.append(f"Invalid document type: {state.get('document_type')}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_analysis_state(state: Dict[str, Any]) -> tuple[bool, List[str]]:
        """분석 팀 State 검증"""
        errors = []

        if not state.get("user_query"):
            errors.append("user_query is required")

        if not state.get("analysis_type"):
            errors.append("analysis_type is required")

        valid_types = ["market", "risk", "comprehensive", "comparison", "trend"]
        if state.get("analysis_type") not in valid_types:
            errors.append(f"Invalid analysis type: {state.get('analysis_type')}")

        return len(errors) == 0, errors