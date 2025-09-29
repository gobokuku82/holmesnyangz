"""
BaseAgent class with full LangGraph 0.6.x Context API support
Following the official Context API manual and rules
IMPROVED VERSION: Enhanced Runtime handling with MockRuntime support
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, Callable
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import logging
import asyncio
from pathlib import Path
from datetime import datetime
import uuid

from .context import AgentContext, create_agent_context


logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all agents with full Context API support
    Implements LangGraph 0.6.x patterns with Runtime
    Enhanced with MockRuntime support for testing and development
    """

    def __init__(self, agent_name: str, checkpoint_dir: Optional[str] = None):
        """
        Initialize base agent

        Args:
            agent_name: Name of the agent
            checkpoint_dir: Directory for checkpoints
        """
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"agent.{agent_name}")

        # Set checkpoint directory
        if checkpoint_dir is None:
            checkpoint_dir = f"checkpoints/{agent_name}"

        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Initialize checkpointer (will be created in execute)
        self.checkpointer_path = self.checkpoint_dir / f"{self.agent_name}.db"

        # Initialize workflow with context schema
        self.workflow = None
        self._build_graph()

        self.logger.info(f"{agent_name} initialized with Context API support")

    @abstractmethod
    def _get_state_schema(self) -> Type:
        """
        Get the state schema for this agent

        Returns:
            State schema type (TypedDict)
        """
        pass

    @abstractmethod
    def _build_graph(self):
        """
        Build the LangGraph workflow with context_schema
        Must call StateGraph with both state_schema and context_schema
        """
        pass

    @abstractmethod
    async def _validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data before processing

        Args:
            input_data: Input data to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    def _create_initial_state(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create initial state from input data
        Only includes workflow-specific fields (not context fields)

        Args:
            input_data: Input data from user

        Returns:
            Initial state dictionary with workflow fields only
        """
        # Exclude context fields from state
        # Note: chat_thread_id is kept in context only, not in state (per LangGraph design)
        excluded_fields = [
            "chat_user_ref", "chat_session_id", "chat_thread_id",
            "db_user_id", "db_session_id",
            "api_keys", "request_id", "timestamp",
            "language", "debug_mode", "trace_enabled"
        ]

        # Basic state fields - subclasses should override to add specific fields
        return {
            "status": "pending",
            "execution_step": "starting",
            **{k: v for k, v in input_data.items() if k not in excluded_fields}
        }

    def _create_context(self, input_data: Dict[str, Any]) -> AgentContext:
        """
        Create context from input data
        Context contains metadata that doesn't change during execution

        Args:
            input_data: Input data containing context information

        Returns:
            AgentContext instance
        """
        return create_agent_context(
            chat_user_ref=input_data.get("chat_user_ref"),
            chat_session_id=input_data.get("chat_session_id"),
            db_user_id=input_data.get("db_user_id"),
            db_session_id=input_data.get("db_session_id"),
            chat_thread_id=input_data.get("chat_thread_id"),
            original_query=input_data.get("original_query", ""),
            request_id=input_data.get("request_id"),
            api_keys=input_data.get("api_keys", {}),
            language=input_data.get("language", "ko"),
            debug_mode=input_data.get("debug_mode", False),
            trace_enabled=input_data.get("trace_enabled", False)
        )

    def _create_mock_runtime(self, state: Dict[str, Any]) -> object:
        """
        Create a MockRuntime for testing and development
        Provides a Runtime-like interface when actual Runtime is not available
        
        Args:
            state: Current state dictionary
            
        Returns:
            MockRuntime object with Runtime-compatible interface
        """
        class MockRuntime:
            """Mock Runtime for testing and development"""
            
            def __init__(self, context: Dict[str, Any], state: Dict[str, Any], agent_name: str):
                self.context = context
                self._state = state
                self.agent_name = agent_name
                self.logger = logging.getLogger(f"mock_runtime.{agent_name}")
                self.is_mock = True  # Flag to identify mock runtime
            
            def get_context_value(self, key: str, default: Any = None) -> Any:
                """Safely get value from context"""
                return self.context.get(key, default)
            
            def log(self, message: str, level: str = "info"):
                """Logging helper method"""
                log_method = getattr(self.logger, level, self.logger.info)
                log_method(message)
            
            @property
            def user_id(self) -> str:
                """Get user ID from context (for backward compatibility)"""
                return self.context.get("chat_user_ref", "system")

            @property
            def chat_user_ref(self) -> str:
                """Get chatbot user reference from context"""
                return self.context.get("chat_user_ref", "system")

            @property
            def session_id(self) -> str:
                """Get session ID from context (for backward compatibility)"""
                return self.context.get("chat_session_id", "default")

            @property
            def chat_session_id(self) -> str:
                """Get chatbot session ID from context"""
                return self.context.get("chat_session_id", "default")
            
            @property
            def request_id(self) -> str:
                """Get request ID from context"""
                return self.context.get("request_id", "unknown")
            
            def get_state_value(self, key: str, default: Any = None) -> Any:
                """Safely get value from state"""
                return self._state.get(key, default)
            
            def __repr__(self) -> str:
                return f"MockRuntime(agent={self.agent_name}, user={self.user_id}, session={self.session_id})"
        
        # Create mock context with defaults
        mock_context = {
            "chat_user_ref": "system",
            "chat_session_id": f"mock_{self.agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "chat_thread_id": f"thread_mock_{uuid.uuid4().hex[:8]}",
            "agent_name": self.agent_name,
            "request_id": f"mock_req_{uuid.uuid4().hex[:8]}",
            "debug_mode": True,
            "trace_enabled": True,
            "is_mock": True,
            "timestamp": datetime.now().isoformat(),
            "environment": "development"
        }
        
        # Merge with any context data from state if available
        if "context" in state and isinstance(state["context"], dict):
            mock_context.update(state["context"])
        
        return MockRuntime(mock_context, state, self.agent_name)

    def _wrap_node_with_runtime(self, node_func: Callable) -> Callable:
        """
        Wrap a node function to properly handle Runtime parameter
        Enhanced version with MockRuntime support for testing
        
        Args:
            node_func: Original node function
        
        Returns:
            Wrapped function that handles Runtime safely
        """
        async def wrapped(state: Dict[str, Any], runtime: Optional[Any] = None) -> Dict[str, Any]:
            """Wrapped node function with Runtime handling"""
            import inspect
            
            # Check if the node function expects runtime parameter
            sig = inspect.signature(node_func)
            
            if "runtime" in sig.parameters:
                # Node expects runtime
                if runtime is None:
                    # Create MockRuntime for testing/development
                    self.logger.warning(
                        f"Runtime not provided to {node_func.__name__}, creating MockRuntime for testing"
                    )
                    runtime = self._create_mock_runtime(state)
                    self.logger.debug(f"MockRuntime created: {runtime}")
                
                # Check if it's a mock runtime and log appropriately
                if hasattr(runtime, 'is_mock') and runtime.is_mock:
                    self.logger.debug(
                        f"Node {node_func.__name__} executing with MockRuntime "
                        f"(user={runtime.user_id}, session={runtime.session_id})"
                    )
                
                # Execute node with runtime (real or mock)
                try:
                    return await node_func(state, runtime)
                except Exception as e:
                    self.logger.error(
                        f"Node {node_func.__name__} failed with runtime "
                        f"(is_mock={getattr(runtime, 'is_mock', False)}): {e}"
                    )
                    raise
            else:
                # Legacy node without runtime support
                self.logger.debug(
                    f"Node {node_func.__name__} doesn't use Runtime parameter - "
                    "consider updating for better context access"
                )
                return await node_func(state)
        
        # Preserve original function metadata
        wrapped.__name__ = node_func.__name__
        wrapped.__doc__ = node_func.__doc__
        wrapped.__annotations__ = getattr(node_func, '__annotations__', {})
        
        return wrapped

    async def execute(
        self,
        input_data: Dict[str, Any],
        config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Execute the agent workflow with Context API

        Args:
            input_data: Input data for the agent
            config: Optional configuration for execution

        Returns:
            Dict containing execution results
        """
        try:
            # Validate input
            if not await self._validate_input(input_data):
                return {
                    "status": "error",
                    "error": "Invalid input data",
                    "agent": self.agent_name
                }

            # Create initial state (workflow data only)
            initial_state = self._create_initial_state(input_data)

            # Create context (metadata)
            context = self._create_context(input_data)

            # Prepare config
            if config is None:
                config = {}

            # Add default config
            config.setdefault("recursion_limit", 25)
            config.setdefault("configurable", {})

            # IMPORTANT: thread_id is a config parameter for checkpointer, not a state field
            # LangGraph design: thread_id identifies the conversation/workflow instance
            # Use chat_thread_id from context if available, fallback to chat_session_id
            # This ensures state persistence across graph executions
            config["configurable"]["thread_id"] = context.get("chat_thread_id") or context.get("chat_session_id", "default")

            # Compile workflow with checkpointer
            if self.workflow is None:
                self.logger.error("Workflow not initialized")
                return {
                    "status": "error",
                    "error": "Workflow not initialized",
                    "agent": self.agent_name
                }

            # Create checkpointer and compile
            async with AsyncSqliteSaver.from_conn_string(str(self.checkpointer_path)) as checkpointer:
                app = self.workflow.compile(checkpointer=checkpointer)

                # Execute with timeout
                timeout = config.get("timeout", 30)  # Default 30 seconds

                try:
                    # Execute with context following LangGraph 0.6.x pattern
                    result = await asyncio.wait_for(
                        app.ainvoke(
                            initial_state,
                            config=config,
                            context=context  # context is already a dict
                        ),
                        timeout=timeout
                    )

                    self.logger.info(f"{self.agent_name} execution completed successfully")

                    # Check if there were any errors logged in context
                    if isinstance(context, dict) and "error_logs" in context:
                        self.logger.warning(f"Execution completed with errors: {context['error_logs']}")

                    return {
                        "status": "success",
                        "data": result,
                        "agent": self.agent_name,
                        "context": {
                            "chat_user_ref": context.get("chat_user_ref", "unknown"),
                            "chat_session_id": context.get("chat_session_id", "unknown"),
                            "chat_thread_id": context.get("chat_thread_id", "unknown"),
                            "request_id": context.get("request_id", "unknown")
                        }
                    }

                except asyncio.TimeoutError:
                    self.logger.error(f"{self.agent_name} execution timed out after {timeout}s")

                    # Log timeout in context if possible
                    if isinstance(context, dict) and "add_error" in context:
                        context["add_error"](f"Execution timed out after {timeout} seconds")

                    return {
                        "status": "error",
                        "error": f"Execution timed out after {timeout} seconds",
                        "agent": self.agent_name
                    }

        except Exception as e:
            self.logger.error(f"{self.agent_name} execution failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "agent": self.agent_name
            }

    async def get_state(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current state for a thread

        Args:
            thread_id: Thread ID to get state for

        Returns:
            Current state or None
        """
        try:
            async with AsyncSqliteSaver.from_conn_string(str(self.checkpointer_path)) as checkpointer:
                app = self.workflow.compile(checkpointer=checkpointer)
                config = {"configurable": {"thread_id": thread_id}}
                state = await app.aget_state(config)
                return state.values if state else None
        except Exception as e:
            self.logger.error(f"Failed to get state: {e}")
            return None

    async def update_state(
        self,
        thread_id: str,
        state_update: Dict[str, Any],
        context: Optional[AgentContext] = None
    ) -> bool:
        """
        Update the state for a thread

        Args:
            thread_id: Thread ID to update
            state_update: State updates to apply (partial update)
            context: Optional context for the update

        Returns:
            True if successful, False otherwise
        """
        try:
            async with AsyncSqliteSaver.from_conn_string(str(self.checkpointer_path)) as checkpointer:
                app = self.workflow.compile(checkpointer=checkpointer)
                config = {"configurable": {"thread_id": thread_id}}

                # Update only the specified fields (following Context API pattern)
                await app.aupdate_state(config, state_update)

                self.logger.info(f"State updated for thread {thread_id}: {list(state_update.keys())}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to update state: {e}")
            return False

    # Helper method for nodes to properly return partial updates
    @staticmethod
    def create_partial_update(**kwargs) -> Dict[str, Any]:
        """
        Helper to create partial state updates for nodes

        Usage in node:
            return self.create_partial_update(
                field1=new_value1,
                field2=new_value2
            )
        """
        return kwargs
    
    # New helper methods for better testing and debugging
    async def test_node(
        self, 
        node_name: str, 
        test_state: Dict[str, Any],
        test_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Test a specific node with mock data
        Useful for unit testing individual nodes
        
        Args:
            node_name: Name of the node to test
            test_state: Test state to pass to the node
            test_context: Optional test context
            
        Returns:
            Node execution result
        """
        # Get the node function
        node_func = getattr(self, node_name, None)
        if not node_func:
            raise ValueError(f"Node {node_name} not found in agent")
        
        # Create mock runtime with test context
        if test_context:
            mock_runtime = self._create_mock_runtime(test_state)
            mock_runtime.context.update(test_context)
        else:
            mock_runtime = self._create_mock_runtime(test_state)
        
        # Wrap and execute the node
        wrapped_node = self._wrap_node_with_runtime(node_func)
        result = await wrapped_node(test_state, mock_runtime)
        
        self.logger.info(f"Test execution of {node_name} completed")
        return result
    
    def validate_state_schema(self, state: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate that a state dictionary matches the expected schema
        
        Args:
            state: State dictionary to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        state_schema = self._get_state_schema()
        
        # Check required fields
        for field, field_type in state_schema.__annotations__.items():
            if field not in state:
                # Check if field is Optional
                if not str(field_type).startswith('Optional'):
                    errors.append(f"Missing required field: {field}")
        
        # Check for unknown fields (warning only)
        schema_fields = set(state_schema.__annotations__.keys())
        state_fields = set(state.keys())
        unknown_fields = state_fields - schema_fields
        
        if unknown_fields:
            self.logger.warning(f"Unknown fields in state: {unknown_fields}")
        
        is_valid = len(errors) == 0
        return is_valid, errors