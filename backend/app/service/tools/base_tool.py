"""
Base Tool Class for Extensible Search System
All search tools should inherit from this base class
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime


class BaseTool(ABC):
    """
    Abstract base class for all search tools
    Provides common interface and mock data capability
    """

    def __init__(self, name: str, description: str, use_mock_data: bool = True):
        """
        Initialize base tool

        Args:
            name: Tool name
            description: Tool description
            use_mock_data: Whether to use mock data (default True since DB not available)
        """
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"tool.{name}")
        self.use_mock_data = use_mock_data  # Renamed for clarity - only affects data, not LLM

    @abstractmethod
    async def search(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main search method - must be implemented by subclasses

        Args:
            query: Search query
            params: Additional search parameters

        Returns:
            Search results dictionary
        """
        pass

    @abstractmethod
    async def get_mock_data(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get mock data for testing - returns mock data when DB is not available
        Must be implemented by each tool with appropriate mock data
        This is ONLY for data, not for LLM responses

        Args:
            query: Search query
            params: Additional search parameters

        Returns:
            Mock search results (simulating DB response)
        """
        pass

    async def execute(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute search with automatic mock/real mode selection

        Args:
            query: Search query
            params: Additional search parameters

        Returns:
            Search results
        """
        try:
            self.logger.info(f"Executing {self.name} with query: {query}")

            if self.use_mock_data:
                # Use mock data when DB is not available
                result = await self.get_mock_data(query, params)
            else:
                # Use real DB search when available
                result = await self.search(query, params)

            # Add metadata
            result["tool_name"] = self.name
            result["timestamp"] = datetime.now().isoformat()
            result["data_source"] = "mock" if self.use_mock_data else "database"

            self.logger.info(f"{self.name} execution completed successfully")
            return result

        except Exception as e:
            self.logger.error(f"Error in {self.name}: {e}")
            return {
                "status": "error",
                "tool_name": self.name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def set_data_mode(self, use_mock_data: bool = True):
        """
        Set tool data mode (mock data or real database)
        Note: This only affects data source, not LLM usage

        Args:
            use_mock_data: If True, use mock data; if False, use real database
        """
        self.use_mock_data = use_mock_data
        self.logger.info(f"{self.name} data mode set to: {'mock' if use_mock_data else 'database'}")

    def validate_params(self, params: Dict[str, Any], required_fields: List[str]) -> bool:
        """
        Validate required parameters

        Args:
            params: Parameters to validate
            required_fields: List of required field names

        Returns:
            True if valid, False otherwise
        """
        if not params:
            return len(required_fields) == 0

        for field in required_fields:
            if field not in params:
                self.logger.error(f"Missing required parameter: {field}")
                return False

        return True

    def format_results(
        self,
        data: List[Dict[str, Any]],
        total_count: int = None,
        query: str = None
    ) -> Dict[str, Any]:
        """
        Standard result formatting

        Args:
            data: Result data
            total_count: Total number of results
            query: Original query

        Returns:
            Formatted results dictionary
        """
        return {
            "status": "success",
            "query": query,
            "data": data,
            "count": len(data),
            "total_count": total_count or len(data),
            "has_more": (total_count or len(data)) > len(data) if total_count else False
        }


class ToolRegistry:
    """
    Registry for managing available tools
    Controls whether tools use mock data or real database
    """

    _instance = None
    _tools = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, tool: BaseTool):
        """
        Register a tool

        Args:
            tool: Tool instance to register
        """
        self._tools[tool.name] = tool
        logging.info(f"Registered tool: {tool.name}")

    def get(self, name: str) -> Optional[BaseTool]:
        """
        Get tool by name

        Args:
            name: Tool name

        Returns:
            Tool instance or None
        """
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """
        List all registered tool names

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_tool_descriptions(self) -> Dict[str, str]:
        """
        Get all tool descriptions

        Returns:
            Dictionary of tool names and descriptions
        """
        return {name: tool.description for name, tool in self._tools.items()}