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


class TestConfig:
    """Test configuration settings"""

    # LLM Settings
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")  # "openai", "azure", or "mock"
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")

    # Test Settings
    USE_MOCK = os.getenv("USE_MOCK_DATA", "true").lower() == "true"
    TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"
    DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"

    # Logging Settings
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

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
    def get_llm_mode(cls) -> str:
        """Get current LLM mode"""
        if cls.OPENAI_API_KEY and cls.LLM_PROVIDER == "openai":
            return "OpenAI"
        elif cls.AZURE_ENDPOINT and cls.LLM_PROVIDER == "azure":
            return "Azure OpenAI"
        else:
            return "Mock"

    @classmethod
    def set_llm_mode(cls, mode: str):
        """Set LLM mode for testing"""
        if mode.lower() == "openai":
            if not cls.OPENAI_API_KEY:
                raise ValueError("OpenAI API key not found in .env")
            os.environ["LLM_PROVIDER"] = "openai"
            cls.LLM_PROVIDER = "openai"
        elif mode.lower() == "azure":
            if not cls.AZURE_ENDPOINT:
                raise ValueError("Azure endpoint not found in .env")
            os.environ["LLM_PROVIDER"] = "azure"
            cls.LLM_PROVIDER = "azure"
        else:
            os.environ["LLM_PROVIDER"] = "mock"
            cls.LLM_PROVIDER = "mock"

    @classmethod
    def print_config(cls):
        """Print current configuration"""
        print("\n" + "="*50)
        print("TEST CONFIGURATION")
        print("="*50)
        print(f"LLM Mode: {cls.get_llm_mode()}")
        print(f"API Key Available: {'YES' if cls.OPENAI_API_KEY else 'NO'}")
        print(f"Use Mock Data: {cls.USE_MOCK}")
        print(f"Debug Mode: {cls.DEBUG_MODE}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print("="*50 + "\n")


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