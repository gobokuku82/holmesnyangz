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

    def __init__(self, name: str, description: str):
        """
        Initialize base tool

        Args:
            name: Tool name
            description: Tool description
        """
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"tool.{name}")
        self.use_mock = True  # Default to mock mode

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
    async def mock_search(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Mock search method - returns mock data
        Must be implemented by each tool with appropriate mock data

        Args:
            query: Search query
            params: Additional search parameters

        Returns:
            Mock search results
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

            if self.use_mock:
                result = await self.mock_search(query, params)
            else:
                result = await self.search(query, params)

            # Add metadata
            result["tool_name"] = self.name
            result["timestamp"] = datetime.now().isoformat()
            result["mode"] = "mock" if self.use_mock else "real"

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

    def set_mode(self, use_mock: bool = True):
        """
        Set tool mode (mock or real)

        Args:
            use_mock: If True, use mock data; if False, use real search
        """
        self.use_mock = use_mock
        self.logger.info(f"{self.name} mode set to: {'mock' if use_mock else 'real'}")

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