"""
BaseAgent class with LangGraph 0.6.x support
Simplified version without MockRuntime
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type
from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import logging
import asyncio
from pathlib import Path
from datetime import datetime

from .context import create_agent_context

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all agents with LangGraph support
    Simplified without MockRuntime complexity
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

        # Initialize checkpointer path
        self.checkpointer_path = self.checkpoint_dir / f"{self.agent_name}.db"

        # Initialize workflow
        self.workflow = None
        self._build_graph()

        self.logger.info(f"{agent_name} initialized")

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
        Build the LangGraph workflow
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
        Includes both workflow fields and context fields in state

        Args:
            input_data: Input data from user

        Returns:
            Initial state dictionary
        """
        # Basic state fields - subclasses should override to add specific fields
        return {
            "status": "pending",
            "execution_step": "starting",
            # Include essential context in state
            "chat_user_ref": input_data.get("chat_user_ref", "system"),
            "chat_session_id": input_data.get("chat_session_id", "default"),
            "api_keys": input_data.get("api_keys", {}),
            **{k: v for k, v in input_data.items() if k not in ["chat_user_ref", "chat_session_id", "api_keys"]}
        }

    def _create_context(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create context from input data

        Args:
            input_data: Input data containing context information

        Returns:
            Context dictionary
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

    async def execute(
        self,
        input_data: Dict[str, Any],
        config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Execute the agent workflow

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

            # Create initial state (includes context in state)
            initial_state = self._create_initial_state(input_data)

            # Create context (for backwards compatibility)
            context = self._create_context(input_data)

            # Prepare config
            if config is None:
                config = {}

            # Add default config
            config.setdefault("recursion_limit", 25)
            config.setdefault("configurable", {})

            # Use context's chat_thread_id or chat_session_id for thread_id
            config["configurable"]["thread_id"] = context.get("chat_thread_id") or context.get("chat_session_id", "default")

            # Compile workflow
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
                    result = await asyncio.wait_for(
                        app.ainvoke(initial_state, config=config),
                        timeout=timeout
                    )

                    self.logger.info(f"{self.agent_name} execution completed successfully")

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
        state_update: Dict[str, Any]
    ) -> bool:
        """
        Update the state for a thread

        Args:
            thread_id: Thread ID to update
            state_update: State updates to apply

        Returns:
            True if successful, False otherwise
        """
        try:
            async with AsyncSqliteSaver.from_conn_string(str(self.checkpointer_path)) as checkpointer:
                app = self.workflow.compile(checkpointer=checkpointer)
                config = {"configurable": {"thread_id": thread_id}}
                await app.aupdate_state(config, state_update)
                self.logger.info(f"State updated for thread {thread_id}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to update state: {e}")
            return False

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