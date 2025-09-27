"""
Context Definitions for LangGraph 0.6.x
Runtime metadata passed through the context parameter
"""

from typing import TypedDict, Optional, Dict, List, Any
import os
from datetime import datetime
import uuid


# ============ Context Types ============

class AgentContext(TypedDict):
    """
    Runtime context for agents
    Contains metadata and configuration passed at execution time
    This is READ-ONLY during execution
    """

    # ========== Required Fields ==========
    user_id: str                # User identifier
    session_id: str             # Session identifier

    # ========== Optional Runtime Info ==========
    request_id: Optional[str]   # Unique request ID
    timestamp: Optional[str]    # Request timestamp
    original_query: Optional[str]  # Original user input

    # ========== Authentication ==========
    api_keys: Optional[Dict[str, str]]  # Service API keys (runtime injection)

    # ========== User Settings ==========
    language: Optional[str]     # User language (ko, en, etc.)

    # ========== Execution Control ==========
    debug_mode: Optional[bool]  # Enable debug logging


class SubgraphContext(TypedDict):
    """
    Context for subgraphs (filtered subset of AgentContext)
    Used when invoking DataCollectionSubgraph, AnalysisSubgraph, etc.
    """

    # ========== Required (from parent) ==========
    user_id: str
    session_id: str

    # ========== Optional (from parent) ==========
    request_id: Optional[str]
    language: Optional[str]
    debug_mode: Optional[bool]

    # ========== Subgraph Identification ==========
    parent_agent: str           # Name of parent agent
    subgraph_name: str         # Name of current subgraph

    # ========== Subgraph Parameters ==========
    suggested_tools: Optional[List[str]]  # Tool hints for subgraph
    analysis_depth: Optional[str]         # shallow, normal, deep
    db_paths: Optional[Dict[str, str]]   # Database paths for data collection


# ============ Context Factory Functions ============

def create_agent_context(
    user_id: str,
    session_id: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Create AgentContext with required fields and optional values

    Args:
        user_id: User identifier
        session_id: Session identifier
        **kwargs: Optional context fields

    Returns:
        Context dictionary ready for LangGraph
    """
    # Start with required fields
    context = {
        "user_id": user_id,
        "session_id": session_id,
        "request_id": kwargs.get("request_id") or f"req_{uuid.uuid4().hex[:8]}",
        "timestamp": kwargs.get("timestamp") or datetime.now().isoformat(),
    }

    # Add optional fields with defaults
    context.update({
        "original_query": kwargs.get("original_query"),
        "api_keys": kwargs.get("api_keys", {}),
        "language": kwargs.get("language", "ko"),
        "debug_mode": kwargs.get("debug_mode", False),
    })

    # Remove None values for cleaner context
    return {k: v for k, v in context.items() if v is not None}


def merge_with_config_defaults(
    context: Dict[str, Any],
    config: Any
) -> Dict[str, Any]:
    """
    Merge context with config defaults
    Context values take precedence

    Args:
        context: Runtime context
        config: Config instance

    Returns:
        Merged context with defaults
    """
    return context


def create_subgraph_context(
    parent_context: Dict[str, Any],
    parent_agent: str,
    subgraph_name: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Create context for subgraphs (filtered subset of parent context)

    Args:
        parent_context: Parent agent's context
        parent_agent: Parent agent name
        subgraph_name: Subgraph name
        **kwargs: Additional subgraph-specific parameters

    Returns:
        Filtered context for subgraph
    """
    context = {
        # Required fields from parent
        "user_id": parent_context["user_id"],
        "session_id": parent_context["session_id"],

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