"""
Search Tools Module
Collection of tools for searching various data sources
"""

from .base_tool import BaseTool, ToolRegistry
from .legal_search_tool import LegalSearchTool
from .regulation_search_tool import RegulationSearchTool
from .loan_search_tool import LoanSearchTool
from .real_estate_search_tool import RealEstateSearchTool
from .document_generation_tool import DocumentGenerationTool
from .contract_review_tool import ContractReviewTool
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
USE_MOCK_TOOLS = os.getenv("USE_MOCK_TOOLS", "true").lower() == "true"

# Register all available tools
# Legal search: Always use real DB (ChromaDB + SQLite)
# Other tools: Use mock data by default (DB not ready yet)
tool_registry.register(LegalSearchTool())  # No mock mode - always real DB
tool_registry.register(RegulationSearchTool(use_mock_data=USE_MOCK_TOOLS))
tool_registry.register(LoanSearchTool(use_mock_data=USE_MOCK_TOOLS))
tool_registry.register(RealEstateSearchTool(use_mock_data=USE_MOCK_TOOLS))
tool_registry.register(DocumentGenerationTool())  # Mock data for now
tool_registry.register(ContractReviewTool())  # Rule-based review

__all__ = [
    "BaseTool",
    "ToolRegistry",
    "LegalSearchTool",
    "RegulationSearchTool",
    "LoanSearchTool",
    "RealEstateSearchTool",
    "DocumentGenerationTool",
    "ContractReviewTool",
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