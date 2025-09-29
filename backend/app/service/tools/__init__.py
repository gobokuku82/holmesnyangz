"""
Search Tools Module
Collection of tools for searching various data sources
"""

from .base_tool import BaseTool, ToolRegistry
from .legal_search_tool import LegalSearchTool
from .regulation_search_tool import RegulationSearchTool
from .loan_search_tool import LoanSearchTool
from .real_estate_search_tool import RealEstateSearchTool

# Initialize tool registry
tool_registry = ToolRegistry()

# Register all available tools
tool_registry.register(LegalSearchTool())
tool_registry.register(RegulationSearchTool())
tool_registry.register(LoanSearchTool())
tool_registry.register(RealEstateSearchTool())

__all__ = [
    "BaseTool",
    "ToolRegistry",
    "LegalSearchTool",
    "RegulationSearchTool",
    "LoanSearchTool",
    "RealEstateSearchTool",
    "tool_registry"
]