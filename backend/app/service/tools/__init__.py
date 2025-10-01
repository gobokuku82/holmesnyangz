"""
Search Tools Module
Collection of tools for searching various data sources
"""

from .base_tool import BaseTool, ToolRegistry
from .legal_search_tool import LegalSearchTool
from .regulation_search_tool import RegulationSearchTool
from .loan_search_tool import LoanSearchTool
from .real_estate_search_tool import RealEstateSearchTool
from .analysis_tools import (
    BaseAnalysisTool,
    MarketAnalyzer,
    TrendAnalyzer,
    ComparativeAnalyzer,
    InvestmentEvaluator,
    RiskAssessor,
    AnalysisToolRegistry,
    analysis_tool_registry
)
import os

# Initialize tool registry
tool_registry = ToolRegistry()

# Check if we should use mock data for tools
# Legal search now has real DB support, so default to False for legal_search
USE_MOCK_LEGAL = os.getenv("USE_MOCK_LEGAL", "false").lower() == "true"
USE_MOCK_OTHER_TOOLS = os.getenv("USE_MOCK_TOOLS", "true").lower() == "true"

# Register all available tools
# Legal search: Use real DB by default (ChromaDB + SQLite)
# Other tools: Use mock data by default (DB not ready yet)
tool_registry.register(LegalSearchTool(use_mock_data=USE_MOCK_LEGAL))
tool_registry.register(RegulationSearchTool(use_mock_data=USE_MOCK_OTHER_TOOLS))
tool_registry.register(LoanSearchTool(use_mock_data=USE_MOCK_OTHER_TOOLS))
tool_registry.register(RealEstateSearchTool(use_mock_data=USE_MOCK_OTHER_TOOLS))

__all__ = [
    "BaseTool",
    "ToolRegistry",
    "LegalSearchTool",
    "RegulationSearchTool",
    "LoanSearchTool",
    "RealEstateSearchTool",
    "tool_registry",
    "BaseAnalysisTool",
    "MarketAnalyzer",
    "TrendAnalyzer",
    "ComparativeAnalyzer",
    "InvestmentEvaluator",
    "RiskAssessor",
    "AnalysisToolRegistry",
    "analysis_tool_registry"
]