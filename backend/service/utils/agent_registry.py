"""
Agent Registry for dynamic agent management
Central registry for all agents in the system
"""

from typing import Dict, Type, Optional, Any, Callable
import logging
import importlib
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseAgentInterface(ABC):
    """Interface that all agents must implement"""

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent with given parameters"""
        pass


class MockAgent(BaseAgentInterface):
    """Mock agent for testing and development"""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"mock_agent.{name}")

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mock execution that returns simulated results"""
        self.logger.info(f"Mock agent {self.name} executing with params: {params}")

        # Simulate different responses based on agent name
        mock_responses = {
            "property_search": {
                "status": "success",
                "agent": self.name,
                "data": [
                    {
                        "name": "래미안 아파트",
                        "region": "서울특별시 강남구 역삼동",
                        "price": 120000,
                        "size": 32,
                        "deal_type": "매매"
                    },
                    {
                        "name": "아크로빌",
                        "region": "서울특별시 강남구 대치동",
                        "price": 150000,
                        "size": 35,
                        "deal_type": "매매"
                    }
                ],
                "count": 2
            },
            "market_analysis": {
                "status": "success",
                "agent": self.name,
                "insights": [
                    "강남구는 학군이 우수하여 수요가 높습니다",
                    "최근 3개월간 평균 5% 가격 상승",
                    "지하철역 인근 매물의 프리미엄이 15% 수준"
                ],
                "statistics": {
                    "avg_price": 135000,
                    "price_change_3m": 0.05,
                    "total_listings": 42
                }
            },
            "region_comparison": {
                "status": "success",
                "agent": self.name,
                "comparison": {
                    "강남구": {"avg_price": 150000, "change": 0.05},
                    "서초구": {"avg_price": 140000, "change": 0.03},
                    "송파구": {"avg_price": 120000, "change": 0.07}
                }
            },
            "investment_advisor": {
                "status": "success",
                "agent": self.name,
                "recommendations": [
                    "현재 시점에서는 강남구 대치동이 투자 가치가 높음",
                    "30평대 아파트가 유동성이 좋고 수요가 안정적"
                ],
                "risk_assessment": "중간"
            }
        }

        # Return appropriate mock response
        response = mock_responses.get(self.name, {
            "status": "success",
            "agent": self.name,
            "data": f"Mock result from {self.name}",
            "params": params
        })

        return response


class AgentRegistry:
    """
    Central registry for managing agents
    Supports both registered agents and dynamic loading
    """

    # Class-level storage for registered agents
    _agents: Dict[str, Type[BaseAgentInterface]] = {}
    _instances: Dict[str, BaseAgentInterface] = {}
    _factories: Dict[str, Callable[[], BaseAgentInterface]] = {}

    @classmethod
    def register(cls, name: str, agent_class: Optional[Type[BaseAgentInterface]] = None):
        """
        Register an agent class
        Can be used as a decorator or called directly

        Usage:
            @AgentRegistry.register("property_search")
            class PropertySearchAgent(BaseAgent):
                pass

        Or:
            AgentRegistry.register("property_search", PropertySearchAgent)
        """
        def decorator(agent_cls: Type[BaseAgentInterface]) -> Type[BaseAgentInterface]:
            cls._agents[name] = agent_cls
            logger.info(f"Registered agent: {name} -> {agent_cls.__name__}")
            return agent_cls

        if agent_class:
            # Direct registration
            cls._agents[name] = agent_class
            logger.info(f"Registered agent: {name} -> {agent_class.__name__}")
            return agent_class
        else:
            # Decorator usage
            return decorator

    @classmethod
    def register_factory(cls, name: str, factory: Callable[[], BaseAgentInterface]):
        """
        Register a factory function for creating agents
        Useful for agents that need complex initialization

        Args:
            name: Agent name
            factory: Function that returns an agent instance
        """
        cls._factories[name] = factory
        logger.info(f"Registered agent factory: {name}")

    @classmethod
    def get_agent(cls, name: str, use_singleton: bool = True, **kwargs) -> BaseAgentInterface:
        """
        Get an agent instance by name

        Args:
            name: Agent name
            use_singleton: If True, reuse existing instance (default: True)
            **kwargs: Additional arguments for agent initialization

        Returns:
            Agent instance
        """
        # Check for existing instance if using singleton
        if use_singleton and name in cls._instances:
            logger.debug(f"Returning cached instance for agent: {name}")
            return cls._instances[name]

        # Try factory first
        if name in cls._factories:
            logger.info(f"Creating agent from factory: {name}")
            instance = cls._factories[name]()
            if use_singleton:
                cls._instances[name] = instance
            return instance

        # Try registered class
        if name in cls._agents:
            logger.info(f"Creating agent from registered class: {name}")
            instance = cls._agents[name](**kwargs)
            if use_singleton:
                cls._instances[name] = instance
            return instance

        # Try dynamic import
        instance = cls._try_dynamic_import(name, **kwargs)
        if instance:
            if use_singleton:
                cls._instances[name] = instance
            return instance

        # Fallback to mock agent
        logger.warning(f"Agent {name} not found, returning MockAgent for development")
        mock = MockAgent(name)
        if use_singleton:
            cls._instances[name] = mock
        return mock

    @classmethod
    def _try_dynamic_import(cls, name: str, **kwargs) -> Optional[BaseAgentInterface]:
        """
        Try to dynamically import an agent

        Args:
            name: Agent name
            **kwargs: Agent initialization arguments

        Returns:
            Agent instance or None
        """
        # Common module paths to try
        module_paths = [
            f"service.agents.{name}",
            f"service.agents.{name}_agent",
            f"agents.{name}",
            f"backend.service.agents.{name}"
        ]

        # Common class name patterns
        class_patterns = [
            f"{name.title().replace('_', '')}Agent",
            f"{name.title().replace('_', '')}",
            name.replace('_', '').title(),
            f"{name.upper()}Agent"
        ]

        for module_path in module_paths:
            try:
                module = importlib.import_module(module_path)

                for class_name in class_patterns:
                    if hasattr(module, class_name):
                        agent_class = getattr(module, class_name)
                        logger.info(f"Dynamically imported {class_name} from {module_path}")

                        # Register for future use
                        cls._agents[name] = agent_class

                        # Create and return instance
                        return agent_class(**kwargs)

            except ImportError:
                continue
            except Exception as e:
                logger.debug(f"Failed to import {module_path}: {e}")

        return None

    @classmethod
    def list_agents(cls) -> Dict[str, str]:
        """
        List all registered agents

        Returns:
            Dictionary mapping agent names to their types
        """
        result = {}

        # Add registered classes
        for name, agent_class in cls._agents.items():
            result[name] = f"Class: {agent_class.__name__}"

        # Add factories
        for name in cls._factories:
            if name not in result:
                result[name] = "Factory Function"

        # Add instances
        for name, instance in cls._instances.items():
            if name not in result:
                result[name] = f"Instance: {instance.__class__.__name__}"

        return result

    @classmethod
    def clear(cls):
        """Clear all registered agents and instances"""
        cls._agents.clear()
        cls._instances.clear()
        cls._factories.clear()
        logger.info("Agent registry cleared")

    @classmethod
    def remove_agent(cls, name: str):
        """Remove a specific agent from registry"""
        removed = False

        if name in cls._agents:
            del cls._agents[name]
            removed = True

        if name in cls._instances:
            del cls._instances[name]
            removed = True

        if name in cls._factories:
            del cls._factories[name]
            removed = True

        if removed:
            logger.info(f"Removed agent: {name}")
        else:
            logger.warning(f"Agent not found: {name}")


# Pre-register mock agents for testing
def register_mock_agents():
    """Register common mock agents for testing"""
    mock_agents = [
        "property_search",
        "market_analysis",
        "region_comparison",
        "investment_advisor"
    ]

    for agent_name in mock_agents:
        AgentRegistry.register_factory(
            agent_name,
            lambda name=agent_name: MockAgent(name)
        )

    logger.info(f"Registered {len(mock_agents)} mock agents")


# Auto-register mock agents on module import
register_mock_agents()