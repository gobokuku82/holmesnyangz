"""
Test Configuration
Settings and utilities for testing the Real Estate Chatbot
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Add parent directories to path
current_dir = Path(__file__).parent
service_dir = current_dir.parent  # backend/app/service
app_dir = service_dir.parent      # backend/app
backend_dir = app_dir.parent      # backend

# Add paths in correct order - most specific first
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(app_dir))
sys.path.insert(0, str(service_dir))

# Also add app/service specifically for imports
sys.path.insert(0, str(backend_dir / "app" / "service"))

# Load environment variables
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[OK] Loaded environment from: {env_path}")
else:
    print(f"[WARNING] No .env file found at: {env_path}")

# Import context utilities after setting up paths
from core.context import (
    LLMContext,
    create_default_llm_context,
    create_llm_context_with_overrides,
    create_agent_context
)


class TestConfig:
    """Test configuration settings"""

    # LLM Settings - Default to OpenAI for real LLM testing
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # "openai" or "azure"
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")

    # Test Settings
    USE_MOCK_TOOLS = os.getenv("USE_MOCK_TOOLS", "true").lower() == "true"  # Tools use mock data
    TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"
    DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"

    # Logging Settings
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # LLM Context for tests
    _llm_context: Optional[LLMContext] = None

    @classmethod
    def setup_logging(cls, verbose: bool = False):
        """Setup logging configuration"""
        level = logging.DEBUG if verbose or cls.DEBUG_MODE else getattr(logging, cls.LOG_LEVEL)

        # Configure root logger
        logging.basicConfig(
            level=level,
            format=cls.LOG_FORMAT,
            handlers=[
                logging.StreamHandler(),
                # logging.FileHandler("test_log.txt")  # Optional file logging
            ]
        )

        # Set specific logger levels
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

        return logging.getLogger("test")

    @classmethod
    def get_llm_context(cls) -> LLMContext:
        """Get or create LLM context for testing"""
        if cls._llm_context is None:
            # Create default context
            cls._llm_context = create_default_llm_context()

            # Use real LLM provider
            if not cls.OPENAI_API_KEY and cls.LLM_PROVIDER == "openai":
                raise ValueError(
                    "OPENAI_API_KEY is required for OpenAI provider. "
                    "Please set it in .env file."
                )
            cls._llm_context.provider = cls.LLM_PROVIDER
            cls._llm_context.api_key = cls.OPENAI_API_KEY

        return cls._llm_context

    @classmethod
    def get_llm_mode(cls) -> str:
        """Get current LLM mode"""
        context = cls.get_llm_context()
        if context.provider == "openai" and context.api_key:
            return "OpenAI"
        elif context.provider == "azure":
            return "Azure OpenAI"
        else:
            return "Unknown"

    @classmethod
    def set_llm_mode(cls, mode: str):
        """Set LLM mode for testing"""
        if mode.lower() == "openai":
            if not cls.OPENAI_API_KEY:
                raise ValueError("OpenAI API key not found in .env")
            cls.LLM_PROVIDER = "openai"
            cls.USE_MOCK = False
            cls._llm_context = create_llm_context_with_overrides(
                provider="openai",
                api_key=cls.OPENAI_API_KEY,
                use_mock=False
            )
        elif mode.lower() == "azure":
            if not cls.AZURE_ENDPOINT:
                raise ValueError("Azure endpoint not found in .env")
            cls.LLM_PROVIDER = "azure"
            cls.USE_MOCK = False
            cls._llm_context = create_llm_context_with_overrides(
                provider="azure",
                use_mock=False
            )
        elif mode.lower() == "mock":
            cls.LLM_PROVIDER = "mock"
            cls.USE_MOCK = True
            cls._llm_context = create_llm_context_with_overrides(
                provider="mock",
                use_mock=True
            )
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'openai', 'azure', or 'mock'")

    @classmethod
    def print_config(cls):
        """Print current configuration"""
        context = cls.get_llm_context()
        print("\n" + "="*50)
        print("TEST CONFIGURATION")
        print("="*50)
        print(f"LLM Mode: {cls.get_llm_mode()}")
        print(f"Provider: {context.provider}")
        print(f"API Key Available: {'YES' if context.api_key else 'NO'}")
        print(f"Use Mock: {context.use_mock}")
        print(f"Debug Mode: {cls.DEBUG_MODE}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print("="*50 + "\n")

    @classmethod
    def create_test_agent_context(cls, **kwargs) -> Dict[str, Any]:
        """Create agent context for testing with LLMContext"""
        llm_context = cls.get_llm_context()

        # Extract specific kwargs to avoid duplicates
        chat_user_ref = kwargs.pop("chat_user_ref", "test_user")
        chat_session_id = kwargs.pop("chat_session_id", "test_session")

        # Create agent context with test defaults
        return create_agent_context(
            chat_user_ref=chat_user_ref,
            chat_session_id=chat_session_id,
            llm_context=llm_context,
            debug_mode=cls.DEBUG_MODE,
            **kwargs  # Pass remaining kwargs
        )


def format_result(result: Dict[str, Any], indent: int = 0) -> str:
    """
    Format result dictionary for display

    Args:
        result: Result dictionary
        indent: Indentation level

    Returns:
        Formatted string
    """
    lines = []
    prefix = "  " * indent

    for key, value in result.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(format_result(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}: [{len(value)} items]")
            for i, item in enumerate(value[:3]):  # Show first 3 items
                if isinstance(item, dict):
                    lines.append(f"{prefix}  [{i}]:")
                    lines.append(format_result(item, indent + 2))
                else:
                    lines.append(f"{prefix}  [{i}]: {item}")
            if len(value) > 3:
                lines.append(f"{prefix}  ... and {len(value) - 3} more items")
        else:
            # Truncate long strings
            if isinstance(value, str) and len(value) > 100:
                value = value[:100] + "..."
            lines.append(f"{prefix}{key}: {value}")

    return "\n".join(lines)


def print_section_header(title: str):
    """Print a formatted section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)