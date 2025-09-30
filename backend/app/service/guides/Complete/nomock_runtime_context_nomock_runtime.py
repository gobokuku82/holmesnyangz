"""
Context Definitions for LangGraph 0.6.x
Simplified without mock-related fields
"""

from typing import TypedDict, Optional, Dict, List, Any
from dataclasses import dataclass, field
import os
from datetime import datetime
import uuid


@dataclass
class LLMContext:
    """
    LLM configuration for runtime context
    """
    # ========== Provider Settings ==========
    provider: str = "openai"  # openai, azure
    api_key: Optional[str] = None
    organization: Optional[str] = None

    # ========== Model Overrides ==========
    model_overrides: Optional[Dict[str, str]] = field(default_factory=dict)

    # ========== Parameter Overrides ==========
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    response_format: Optional[Dict[str, Any]] = None

    # ========== User Context ==========
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    # ========== Feature Flags ==========
    enable_retry: bool = True
    enable_logging: bool = True


class AgentContext(TypedDict):
    """
    Runtime context for agents
    This data is now included directly in State for simplicity
    """
    # ========== LangGraph System Identifiers ==========
    chat_user_ref: str
    chat_session_id: str
    chat_thread_id: Optional[str]

    # ========== Database References ==========
    db_user_id: Optional[int]
    db_session_id: Optional[int]

    # ========== Runtime Info ==========
    request_id: Optional[str]
    timestamp: Optional[str]
    original_query: Optional[str]

    # ========== Authentication ==========
    api_keys: Optional[Dict[str, str]]

    # ========== User Settings ==========
    language: Optional[str]

    # ========== Execution Control ==========
    debug_mode: Optional[bool]
    trace_enabled: Optional[bool]

    # ========== LLM Configuration ==========
    llm_context: Optional[LLMContext]


class SubgraphContext(TypedDict):
    """
    Context for subgraphs
    """
    # ========== Required (from parent) ==========
    chat_user_ref: str
    chat_session_id: str
    chat_thread_id: Optional[str]

    # ========== Database References ==========
    db_user_id: Optional[int]
    db_session_id: Optional[int]

    # ========== Optional (from parent) ==========
    request_id: Optional[str]
    language: Optional[str]
    debug_mode: Optional[bool]

    # ========== Subgraph Identification ==========
    parent_agent: str
    subgraph_name: str

    # ========== Subgraph Parameters ==========
    suggested_tools: Optional[List[str]]
    analysis_depth: Optional[str]
    db_paths: Optional[Dict[str, str]]


def create_agent_context(
    chat_user_ref: str = None,
    chat_session_id: str = None,
    db_user_id: int = None,
    db_session_id: int = None,
    llm_context: LLMContext = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create AgentContext with required fields and optional values

    Args:
        chat_user_ref: Chatbot user reference
        chat_session_id: Chatbot session ID
        db_user_id: Database user ID
        db_session_id: Database session ID
        **kwargs: Optional context fields

    Returns:
        Context dictionary
    """
    # Auto-generate chatbot identifiers if not provided
    if not chat_user_ref:
        chat_user_ref = f"user_{uuid.uuid4().hex[:12]}"
    if not chat_session_id:
        chat_session_id = f"session_{uuid.uuid4().hex[:12]}"

    # Start with required fields
    context = {
        # Chatbot system identifiers
        "chat_user_ref": chat_user_ref,
        "chat_session_id": chat_session_id,
        "chat_thread_id": kwargs.get("chat_thread_id") or f"thread_{uuid.uuid4().hex[:8]}",

        # Database references (optional)
        "db_user_id": db_user_id,
        "db_session_id": db_session_id,

        # Runtime metadata
        "request_id": kwargs.get("request_id") or f"req_{uuid.uuid4().hex[:8]}",
        "timestamp": kwargs.get("timestamp") or datetime.now().isoformat(),
        "original_query": kwargs.get("original_query"),

        # Settings
        "api_keys": kwargs.get("api_keys", {}),
        "language": kwargs.get("language", "ko"),
        "debug_mode": kwargs.get("debug_mode", False),
        "trace_enabled": kwargs.get("trace_enabled", False),

        # LLM Configuration
        "llm_context": llm_context or create_default_llm_context(),
    }

    # Remove None values for cleaner context
    return {k: v for k, v in context.items() if v is not None}


def create_agent_context_from_db_user(
    db_user_id: int,
    db_session_id: int = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create AgentContext starting from database user

    Args:
        db_user_id: Database user ID
        db_session_id: Database session ID
        **kwargs: Additional context fields

    Returns:
        Context with both chat and DB identifiers
    """
    # Generate chat identifiers linked to DB user
    chat_user_ref = f"dbuser_{db_user_id}_{uuid.uuid4().hex[:8]}"
    chat_session_id = f"dbsession_{db_session_id or 'new'}_{uuid.uuid4().hex[:8]}"

    return create_agent_context(
        chat_user_ref=chat_user_ref,
        chat_session_id=chat_session_id,
        db_user_id=db_user_id,
        db_session_id=db_session_id,
        **kwargs
    )


def create_subgraph_context(
    parent_context: Dict[str, Any],
    parent_agent: str,
    subgraph_name: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Create context for subgraphs

    Args:
        parent_context: Parent agent's context
        parent_agent: Parent agent name
        subgraph_name: Subgraph name
        **kwargs: Additional subgraph-specific parameters

    Returns:
        Filtered context for subgraph
    """
    context = {
        # Chatbot identifiers from parent
        "chat_user_ref": parent_context["chat_user_ref"],
        "chat_session_id": parent_context["chat_session_id"],
        "chat_thread_id": parent_context.get("chat_thread_id"),

        # Database references from parent
        "db_user_id": parent_context.get("db_user_id"),
        "db_session_id": parent_context.get("db_session_id"),

        # Optional fields from parent
        "request_id": parent_context.get("request_id"),
        "language": parent_context.get("language", "ko"),
        "debug_mode": parent_context.get("debug_mode", False),

        # Subgraph identification
        "parent_agent": parent_agent,
        "subgraph_name": subgraph_name,

        # Subgraph-specific parameters
        "suggested_tools": kwargs.get("suggested_tools", []),
        "analysis_depth": kwargs.get("analysis_depth", "normal"),
        "db_paths": kwargs.get("db_paths", {}),
    }

    # Remove None values for cleaner context
    return {k: v for k, v in context.items() if v is not None}


def create_default_llm_context() -> LLMContext:
    """
    Create default LLM context from environment variables

    Returns:
        LLMContext with default settings
    """
    return LLMContext(
        provider=os.getenv("LLM_PROVIDER", "openai"),
        api_key=os.getenv("OPENAI_API_KEY"),
        organization=os.getenv("OPENAI_ORG_ID")
    )


def create_llm_context_with_overrides(
    base_context: LLMContext = None,
    **overrides
) -> LLMContext:
    """
    Create LLM context with overrides

    Args:
        base_context: Base context to start from
        **overrides: Field overrides

    Returns:
        New LLMContext with overrides applied
    """
    base = base_context or create_default_llm_context()

    # Apply overrides
    for key, value in overrides.items():
        if hasattr(base, key):
            setattr(base, key, value)

    return base


def extract_api_keys_from_env() -> Dict[str, str]:
    """
    Extract API keys from environment variables

    Returns:
        Dictionary of API keys
    """
    api_keys = {}

    # Common API key patterns
    key_patterns = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ]

    for key in key_patterns:
        value = os.getenv(key)
        if value:
            # Convert to lowercase key for consistency
            api_keys[key.lower()] = value

    return api_keys


def validate_context(context: Dict[str, Any]) -> bool:
    """
    Validate context has required fields

    Args:
        context: Context dictionary

    Returns:
        True if valid, raises ValueError if not
    """
    required_fields = ["chat_user_ref", "chat_session_id"]

    for field in required_fields:
        if field not in context:
            raise ValueError(f"Missing required context field: {field}")

    # Check type consistency
    if "db_user_id" in context and context["db_user_id"] is not None:
        if not isinstance(context["db_user_id"], int):
            raise ValueError(f"db_user_id must be integer, got {type(context['db_user_id'])}")

    if "db_session_id" in context and context["db_session_id"] is not None:
        if not isinstance(context["db_session_id"], int):
            raise ValueError(f"db_session_id must be integer, got {type(context['db_session_id'])}")

    return True