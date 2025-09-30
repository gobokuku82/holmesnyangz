"""
State Definitions for LangGraph 0.6.x
Workflow data that changes during execution with reducer patterns
Updated with improved naming conventions and additional tracking fields
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from operator import add
from datetime import datetime


# ============ Custom Reducer Functions (Used Only) ============

# Import TODO merger from todo_types
try:
    from .todo_types import merge_todos
except ImportError:
    # Fallback if todo_types not available
    def merge_todos(existing, new):
        return new if new else existing

def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Merge dictionaries, b overwrites a"""
    if not a:
        return b or {}
    if not b:
        return a
    return {**a, **b}


def append_unique(a: List[Any], b: List[Any]) -> List[Any]:
    """Append only unique items to list"""
    if not a:
        a = []
    if not b:
        return a
    result = a.copy()
    for item in b:
        if item not in result:
            result.append(item)
    return result


# ============ Base State ============

class BaseState(TypedDict):
    """
    Base state for all workflows

    Naming Convention:
    - chat_* : LangGraph/Chatbot system identifiers
    - db_* : Database reference IDs
    - agent_* : Agent-specific metadata
    - No prefix : Business logic fields
    """

    # ========== Session Identifiers ==========
    chat_session_id: str              # Chatbot session ID
    chat_thread_id: Optional[str]     # LangGraph thread ID
    db_session_id: Optional[int]      # Database session reference
    db_user_id: Optional[int]         # Database user reference

    # ========== Workflow Status ==========
    status: str                       # pending, processing, completed, failed
    execution_step: str               # Current step in workflow

    # ========== Agent Tracking ==========
    agent_name: Optional[str]         # Current agent name
    agent_path: Annotated[List[str], add]  # Execution path history

    # ========== Error Handling ==========
    errors: Annotated[List[str], add]  # Error messages
    error_details: Annotated[Dict[str, Any], merge_dicts]  # Detailed error info

    # ========== Timing ==========
    start_time: Optional[str]
    end_time: Optional[str]
    agent_timings: Annotated[Dict[str, float], merge_dicts]  # Agent execution times


# ============ Subgraph States ============

class DataCollectionState(TypedDict):
    """State for data collection subgraph"""

    # ========== Identifiers ==========
    chat_session_id: str
    chat_thread_id: Optional[str]
    db_session_id: Optional[int]

    # ========== Input Parameters ==========
    query_params: Dict[str, Any]      # Parameters for data collection
    target_databases: List[str]       # Which databases to query

    # ========== Collection Results ==========
    performance_data: Annotated[List[Dict[str, Any]], add]
    target_data: Annotated[List[Dict[str, Any]], add]
    client_data: Annotated[List[Dict[str, Any]], add]

    # ========== Aggregated Data ==========
    aggregated_performance: Annotated[Dict[str, Any], merge_dicts]
    aggregated_target: Annotated[Dict[str, Any], merge_dicts]
    aggregated_client: Annotated[Dict[str, Any], merge_dicts]

    # ========== Status ==========
    collection_status: str
    errors: Annotated[List[str], add]


class AnalysisState(TypedDict):
    """State for analysis subgraph"""

    # ========== Identifiers ==========
    chat_session_id: str
    chat_thread_id: Optional[str]

    # ========== Input Data ==========
    performance_data: List[Dict[str, Any]]
    target_data: List[Dict[str, Any]]
    client_data: List[Dict[str, Any]]

    # ========== Analysis Parameters ==========
    analysis_type: str  # basic, trend, comparative, comprehensive
    analysis_params: Dict[str, Any]

    # ========== Analysis Results ==========
    basic_metrics: Annotated[Dict[str, Any], merge_dicts]
    trend_analysis: Annotated[Dict[str, Any], merge_dicts]
    comparative_analysis: Annotated[Dict[str, Any], merge_dicts]
    insights: Annotated[List[str], append_unique]

    # ========== Output ==========
    analysis_report: Optional[Dict[str, Any]]

    # ========== Status ==========
    analysis_status: str
    errors: Annotated[List[str], add]


# ============ Real Estate State (Active) ============

class RealEstateState(BaseState):
    """
    Real Estate Analysis Agent State
    Workflow data that changes during execution for apartment value analysis
    """

    # === Input (overwrite) ===
    query: str  # User query
    region: Optional[str]  # Region name
    property_type: Optional[str]  # Property type
    deal_type: Optional[str]  # Deal type
    price_range: Optional[Dict[str, Any]]  # Price range
    size_range: Optional[Dict[str, Any]]  # Size range in pyeong

    # === Planning (overwrite) ===
    agent_plan: Optional[Dict[str, Any]]  # Agent execution plan
    agent_strategy: Optional[str]  # Execution strategy

    # === Query Processing (overwrite) ===
    search_conditions: Dict[str, Any]  # Parsed search conditions
    generated_sql: Optional[str]  # Generated SQL
    db_query_results: Annotated[List[Dict[str, Any]], add]  # Raw DB results

    # === Data Collection (accumulate) ===
    listing_results: Annotated[List[Dict[str, Any]], add]  # Property listings
    market_data: Annotated[Dict[str, Any], merge_dicts]  # Market statistics

    # === Subgraph Results (merge) ===
    data_collection_result: Optional[Dict[str, Any]]  # From DataCollectionSubgraph
    analysis_result: Optional[Dict[str, Any]]  # From AnalysisSubgraph

    # === Aggregation (merge) ===
    collected_data: Annotated[Dict[str, Any], merge_dicts]  # From subgraphs
    execution_results: Annotated[Dict[str, Any], merge_dicts]  # Execution outcomes
    aggregated_data: Annotated[Dict[str, Any], merge_dicts]  # Aggregated metrics
    statistics: Annotated[Dict[str, float], merge_dicts]  # Statistical summaries

    # === Analysis (unique accumulate) ===
    insights: Annotated[List[str], append_unique]  # Property insights
    investment_points: Annotated[List[str], append_unique]  # Investment recommendations
    risk_factors: Annotated[List[str], append_unique]  # Risk analysis

    # === Output (overwrite) ===
    briefing: Optional[str]  # Summary briefing for user
    final_report: Optional[Dict[str, Any]]  # Complete analysis report
    report_metadata: Optional[Dict[str, Any]]  # Report generation metadata


class SupervisorState(BaseState):
    """
    Supervisor State for Main Orchestrator
    Manages intent analysis -> planning -> execution -> evaluation workflow
    """

    # === Input (overwrite) ===
    query: str  # User query
    chat_context: Optional[Dict[str, Any]]  # Chat context from previous turns

    # === Intent Analysis (overwrite) ===
    intent: Optional[Dict[str, Any]]  # Classified intent with entities
    intent_confidence: Optional[float]  # Confidence score

    # === Planning (overwrite) ===
    execution_plan: Optional[Dict[str, Any]]  # Overall execution plan
    agent_selection: Optional[List[str]]  # Selected agents to execute
    agent_dependencies: Optional[Dict[str, List[str]]]  # Agent dependencies

    # === Agent Execution (merge) ===
    agent_results: Annotated[Dict[str, Any], merge_dicts]  # Results from agents
    agent_errors: Annotated[Dict[str, str], merge_dicts]  # Agent-specific errors
    agent_metrics: Annotated[Dict[str, Dict], merge_dicts]  # Performance metrics

    # === Retry Management (overwrite) ===
    retry_count: int  # Current retry count (default: 0)
    max_retries: int  # Maximum retry attempts (default: 2)
    failed_agents: List[str]  # List of failed agents for retry

    # === Evaluation (overwrite) ===
    evaluation: Optional[Dict[str, Any]]  # Quality evaluation
    quality_score: Optional[float]  # Overall quality score
    retry_needed: Optional[bool]  # Whether retry is needed
    retry_agents: Optional[List[str]]  # Agents to retry

    # === Output (overwrite) ===
    final_output: Optional[Dict[str, Any]]  # Final formatted response
    response_format: Optional[str]  # Output format (json, text, markdown)
    response_metadata: Optional[Dict[str, Any]]  # Response metadata


class DocumentState(BaseState):
    """
    State for document generation workflows
    """

    # === Document Configuration ===
    doc_type: str  # Type of document
    doc_format: str  # Output format
    doc_template: Optional[str]  # Template to use

    # === Content Fields ===
    title: str  # Document title
    input_data: Dict[str, Any]  # Input data for generation
    sections: List[Dict[str, Any]]  # Document sections
    content: str  # Raw content
    formatted_content: str  # Formatted content

    # === Metadata ===
    document_metadata: Dict[str, Any]  # Document metadata
    generation_params: Dict[str, Any]  # Generation parameters

    # === Interactive Processing ===
    user_query: Optional[str]  # Original user query
    query_analysis: Optional[Dict[str, Any]]  # Query analysis
    required_fields: Optional[List[Dict[str, Any]]]  # Required fields
    missing_fields: Optional[List[Dict[str, Any]]]  # Missing fields
    collected_data: Annotated[Dict[str, Any], merge_dicts]  # Collected data

    # === Interaction State ===
    interaction_mode: Optional[str]  # interactive, batch, auto
    interaction_history: Annotated[List[Dict[str, Any]], add]  # History
    needs_user_input: bool  # User input needed flag
    current_prompt: Optional[str]  # Current prompt
    user_response: Optional[str]  # User response

    # === Output ===
    final_document: Dict[str, Any]  # Final document
    document_url: Optional[str]  # Generated document URL
    export_format: Optional[str]  # Export format


# ============ New Real Estate Main Orchestrator State ============

class RealEstateMainState(TypedDict):
    """
    Main State for Real Estate Chatbot Supervisor
    Manages the overall workflow and agent communication
    Enhanced with hierarchical TODO management
    """

    # === Session Identifiers ===
    chat_session_id: str
    chat_thread_id: Optional[str]
    db_session_id: Optional[int]
    db_user_id: Optional[int]

    # === Input ===
    query: str  # User query

    # === Unified TODO Management ===
    todos: Annotated[List[Dict[str, Any]], merge_todos]  # 계층적 TODO 리스트 (전체)
    todo_counter: int  # TODO ID 생성용 카운터
    current_phase: Optional[str]  # 현재 단계 (planning, executing, evaluating)
    chat_context: Optional[Dict[str, Any]]  # Previous conversation context

    # === Intent Analysis ===
    intent: Optional[Dict[str, Any]]  # Analyzed intent with entities
    intent_confidence: Optional[float]  # Confidence score
    intent_type: Optional[str]  # search, analysis, recommendation, etc.

    # === Planning ===
    execution_plan: Optional[Dict[str, Any]]  # Overall execution plan
    collection_keywords: Optional[List[str]]  # Keywords for data collection
    selected_agents: Optional[List[str]]  # Agents to execute

    # === Agent Communication ===
    agent_results: Annotated[Dict[str, Any], merge_dicts]  # Results from agents
    shared_context: Annotated[Dict[str, Any], merge_dicts]  # Shared data between agents
    current_agent: Optional[str]  # Currently executing agent
    agent_sequence: Optional[List[str]]  # Execution sequence

    # === Status Tracking ===
    status: str  # pending, processing, completed, failed
    execution_step: str  # Current step in workflow
    errors: Annotated[List[str], add]  # Error messages

    # === Output ===
    final_response: Optional[Dict[str, Any]]  # Final formatted response
    response_type: Optional[str]  # direct, delegated, processed
    response_metadata: Optional[Dict[str, Any]]  # Response metadata


class SearchAgentState(TypedDict):
    """
    State for Search Agent Subgraph
    Manages data collection and routing decisions
    Enhanced with Agent-level TODO management
    """

    # === Input from Supervisor ===
    original_query: str  # Original user query
    collection_keywords: List[str]  # Keywords to search for
    shared_context: Dict[str, Any]  # Shared context from supervisor
    chat_session_id: str  # Session identifier

    # === TODO Reference (Agent accesses parent todos) ===
    # Agent는 parent state의 todos를 참조하고 업데이트함
    parent_todo_id: Optional[str]  # 부모 TODO ID (supervisor에서 할당)
    current_task: Optional[str]  # 현재 작업 중인 노드/도구
    todos: Annotated[List[Dict[str, Any]], merge_todos]  # TODO list passed from supervisor
    todo_counter: int  # Counter for generating unique TODO IDs

    # === Search Planning ===
    search_plan: Optional[Dict[str, Any]]  # LLM-generated search plan
    selected_tools: Optional[List[str]]  # Tools to use for searching
    tool_parameters: Optional[Dict[str, Any]]  # Parameters for each tool

    # === Tool Execution ===
    tool_results: Annotated[Dict[str, Any], merge_dicts]  # Results from tools
    successful_tools: Annotated[List[str], append_unique]  # Successfully executed tools
    failed_tools: Annotated[List[str], append_unique]  # Failed tools

    # === Data Processing ===
    collected_data: Annotated[Dict[str, Any], merge_dicts]  # Aggregated data
    data_summary: Optional[str]  # Summary of collected data
    data_quality_score: Optional[float]  # Quality assessment

    # === Routing Decision ===
    next_action: Optional[str]  # return_to_supervisor, pass_to_agent, direct_output
    target_agent: Optional[str]  # Target agent if passing data
    routing_reason: Optional[str]  # Reason for routing decision

    # === Status ===
    status: str  # pending, searching, processing, completed
    execution_step: str  # Current step
    errors: Annotated[List[str], add]  # Error messages

    # === Output ===
    search_summary: Optional[str]  # Summary for supervisor
    output_data: Optional[Dict[str, Any]]  # Structured output


class AnalysisAgentState(TypedDict):
    """
    State for Analysis Agent Subgraph
    Manages data analysis and insight generation
    Processes data from SearchAgent or directly from Supervisor
    """

    # === Input from Supervisor or SearchAgent ===
    original_query: str  # Original user query
    analysis_type: str  # Type of analysis: market, trend, comparative, investment, comprehensive
    input_data: Dict[str, Any]  # Data to analyze (from SearchAgent or direct)
    shared_context: Dict[str, Any]  # Shared context from supervisor/previous agent
    chat_session_id: str  # Session identifier

    # === TODO Management ===
    parent_todo_id: Optional[str]  # Parent TODO ID from supervisor
    current_task: Optional[str]  # Currently executing node/tool
    todos: Annotated[List[Dict[str, Any]], merge_todos]  # TODO list for tracking
    todo_counter: int  # Counter for unique TODO IDs

    # === Analysis Planning ===
    analysis_plan: Optional[Dict[str, Any]]  # LLM-generated analysis plan
    selected_methods: Optional[List[str]]  # Analysis methods to apply
    analysis_parameters: Optional[Dict[str, Any]]  # Parameters for each method

    # === Data Preparation ===
    prepared_data: Optional[Dict[str, Any]]  # Cleaned and normalized data
    data_validation: Optional[Dict[str, Any]]  # Data quality validation results
    data_metrics: Optional[Dict[str, Any]]  # Basic data metrics

    # === Analysis Results ===
    market_analysis: Optional[Dict[str, Any]]  # Market conditions analysis
    trend_analysis: Optional[Dict[str, Any]]  # Trend and pattern analysis
    comparative_analysis: Optional[Dict[str, Any]]  # Comparative analysis results
    investment_analysis: Optional[Dict[str, Any]]  # Investment value analysis
    risk_analysis: Optional[Dict[str, Any]]  # Risk assessment results

    # === Insights and Recommendations ===
    insights: Annotated[List[str], append_unique]  # Key insights discovered
    recommendations: Annotated[List[str], append_unique]  # Action recommendations
    risk_factors: Annotated[List[str], append_unique]  # Identified risks
    opportunities: Annotated[List[str], append_unique]  # Identified opportunities

    # === Synthesis ===
    analysis_summary: Optional[str]  # Executive summary of analysis
    confidence_scores: Optional[Dict[str, float]]  # Confidence in each analysis
    data_coverage: Optional[float]  # Percentage of data analyzed

    # === Output ===
    final_report: Optional[Dict[str, Any]]  # Complete analysis report
    visualization_data: Optional[Dict[str, Any]]  # Data prepared for visualization
    key_metrics: Optional[Dict[str, Any]]  # Key performance metrics

    # === Routing Decision ===
    next_action: Optional[str]  # return_to_supervisor, direct_output, pass_to_agent
    target_agent: Optional[str]  # Target agent if passing results
    routing_reason: Optional[str]  # Reason for routing decision

    # === Status ===
    status: str  # pending, analyzing, processing, completed
    execution_step: str  # Current execution step
    errors: Annotated[List[str], add]  # Error messages

    # === Metadata ===
    analysis_duration: Optional[float]  # Time taken for analysis
    tool_usage: Annotated[Dict[str, int], merge_dicts]  # Count of tool usage


# ============ State Factory Functions ============

def create_base_state(
    chat_session_id: str,
    chat_thread_id: str = None,
    db_session_id: int = None,
    db_user_id: int = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create base state with common fields

    Args:
        chat_session_id: Chatbot session ID
        chat_thread_id: LangGraph thread ID
        db_session_id: Database session ID
        db_user_id: Database user ID
        **kwargs: Additional state fields

    Returns:
        Base state dictionary
    """
    return {
        # Identifiers
        "chat_session_id": chat_session_id,
        "chat_thread_id": chat_thread_id,
        "db_session_id": db_session_id,
        "db_user_id": db_user_id,

        # Status
        "status": "pending",
        "execution_step": "initializing",
        "agent_name": None,
        "agent_path": [],

        # Errors
        "errors": [],
        "error_details": {},

        # Timing
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "agent_timings": {},

        # Additional fields from kwargs
        **kwargs
    }


def create_real_estate_initial_state(
    chat_session_id: str,
    query: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Create initial RealEstateState with defaults

    Args:
        chat_session_id: Chatbot session ID
        query: User query
        **kwargs: Additional field values

    Returns:
        Initial state dictionary
    """
    base_state = create_base_state(
        chat_session_id=chat_session_id,
        chat_thread_id=kwargs.get("chat_thread_id"),
        db_session_id=kwargs.get("db_session_id"),
        db_user_id=kwargs.get("db_user_id")
    )

    return {
        **base_state,

        # Input
        "query": query,
        "region": kwargs.get("region"),
        "property_type": kwargs.get("property_type", "아파트"),
        "deal_type": kwargs.get("deal_type", "매매"),
        "price_range": kwargs.get("price_range"),
        "size_range": kwargs.get("size_range"),

        # Planning
        "agent_plan": None,
        "agent_strategy": None,

        # Query Processing
        "search_conditions": {},
        "generated_sql": None,
        "db_query_results": [],

        # Data Collection
        "listing_results": [],
        "market_data": {},

        # Subgraph Results
        "data_collection_result": None,
        "analysis_result": None,

        # Aggregation
        "collected_data": {},
        "execution_results": {},
        "aggregated_data": {},
        "statistics": {},

        # Analysis
        "insights": [],
        "investment_points": [],
        "risk_factors": [],

        # Output
        "briefing": None,
        "final_report": None,
        "report_metadata": None
    }


def create_supervisor_initial_state(
    chat_session_id: str,
    query: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Create initial SupervisorState with defaults

    Args:
        chat_session_id: Chatbot session ID
        query: User query
        **kwargs: Additional field values

    Returns:
        Initial state dictionary
    """
    base_state = create_base_state(
        chat_session_id=chat_session_id,
        chat_thread_id=kwargs.get("chat_thread_id"),
        db_session_id=kwargs.get("db_session_id"),
        db_user_id=kwargs.get("db_user_id")
    )

    return {
        **base_state,

        # Input
        "query": query,
        "chat_context": kwargs.get("chat_context"),

        # Intent Analysis
        "intent": None,
        "intent_confidence": None,

        # Planning
        "execution_plan": None,
        "agent_selection": None,
        "agent_dependencies": None,

        # Agent Execution
        "agent_results": {},
        "agent_errors": {},
        "agent_metrics": {},

        # Retry Management
        "retry_count": 0,
        "max_retries": kwargs.get("max_retries", 2),
        "failed_agents": [],

        # Evaluation
        "evaluation": None,
        "quality_score": None,
        "retry_needed": None,
        "retry_agents": None,

        # Output
        "final_output": None,
        "response_format": kwargs.get("response_format", "text"),
        "response_metadata": None
    }


def merge_state_updates(*updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge multiple state updates

    Args:
        *updates: State update dictionaries

    Returns:
        Merged state update
    """
    result = {}
    for update in updates:
        for key, value in update.items():
            if value is not None:
                result[key] = value
    return result


def get_state_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get summary of current state

    Args:
        state: Current state

    Returns:
        Summary dictionary
    """
    return {
        "chat_session_id": state.get("chat_session_id"),
        "db_session_id": state.get("db_session_id"),
        "status": state.get("status"),
        "step": state.get("execution_step"),
        "current_agent": state.get("agent_name"),
        "agent_path": state.get("agent_path", []),
        "errors_count": len(state.get("errors", [])),
        "has_results": bool(state.get("final_report") or state.get("final_output")),
        "data_collected": bool(state.get("collected_data") or state.get("listing_results")),
        "insights_count": len(state.get("insights", [])),
        "quality_score": state.get("quality_score"),
        "retry_count": state.get("retry_count", 0),
        "start_time": state.get("start_time"),
        "end_time": state.get("end_time"),
        "execution_time": calculate_execution_time(
            state.get("start_time"),
            state.get("end_time")
        ) if state.get("end_time") else None
    }


def calculate_execution_time(start_time: str, end_time: str) -> float:
    """Calculate execution time in seconds"""
    if not start_time or not end_time:
        return None
    start = datetime.fromisoformat(start_time)
    end = datetime.fromisoformat(end_time)
    return (end - start).total_seconds()