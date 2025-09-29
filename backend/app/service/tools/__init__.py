"""
Search Tools Module
Collection of tools for searching various data sources
"""

from .base_tool import BaseTool, ToolRegistry
from .legal_search_tool import LegalSearchTool
from .regulation_search_tool import RegulationSearchTool
from .loan_search_tool import LoanSearchTool
from .real_estate_search_tool import RealEstateSearchTool
import os

# Initialize tool registry
tool_registry = ToolRegistry()

# Check if we should use mock data for tools (default: True since DB not ready)
USE_MOCK_TOOLS = os.getenv("USE_MOCK_TOOLS", "true").lower() == "true"

# Register all available tools with mock data mode
# Note: Tools use mock DATA only, not mock LLM
tool_registry.register(LegalSearchTool(use_mock_data=USE_MOCK_TOOLS))
tool_registry.register(RegulationSearchTool(use_mock_data=USE_MOCK_TOOLS))
tool_registry.register(LoanSearchTool(use_mock_data=USE_MOCK_TOOLS))
tool_registry.register(RealEstateSearchTool(use_mock_data=USE_MOCK_TOOLS))

__all__ = [
    "BaseTool",
    "ToolRegistry",
    "LegalSearchTool",
    "RegulationSearchTool",
    "LoanSearchTool",
    "RealEstateSearchTool",
    "tool_registry"
]