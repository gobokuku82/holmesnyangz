"""
Checkpointer management module
Provides checkpoint functionality for state persistence using AsyncSqliteSaver
"""

import logging
from pathlib import Path
from typing import Optional

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.service_agent.foundation.config import Config

logger = logging.getLogger(__name__)


class CheckpointerManager:
    """
    Manages checkpoint creation and retrieval using AsyncSqliteSaver
    """

    def __init__(self):
        """Initialize the checkpointer manager"""
        self.checkpoint_dir = Config.CHECKPOINT_DIR
        self._ensure_checkpoint_dir_exists()
        self._checkpointers = {}  # Cache for checkpointer instances
        self._context_managers = {}  # Cache for async context managers
        logger.info(f"CheckpointerManager initialized with dir: {self.checkpoint_dir}")

    def _ensure_checkpoint_dir_exists(self):
        """Ensure the checkpoint directory exists"""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def get_checkpoint_path(self, agent_name: str, session_id: str) -> Path:
        """
        Get the checkpoint database path for a specific agent and session

        Args:
            agent_name: Name of the agent
            session_id: Session identifier

        Returns:
            Path to the checkpoint database file
        """
        return Config.get_checkpoint_path(agent_name, session_id)

    async def create_checkpointer(self, db_path: Optional[str] = None) -> AsyncSqliteSaver:
        """
        Create and setup an AsyncSqliteSaver checkpointer instance

        Args:
            db_path: Optional database path. If None, uses default from config

        Returns:
            AsyncSqliteSaver instance

        Raises:
            Exception: If checkpointer setup fails
        """
        if db_path is None:
            db_path = self.checkpoint_dir / "default_checkpoint.db"
        else:
            db_path = Path(db_path)

        # Ensure parent directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Check cache
        db_path_str = str(db_path)
        if db_path_str in self._checkpointers:
            logger.debug(f"Returning cached checkpointer for: {db_path}")
            return self._checkpointers[db_path_str]

        logger.info(f"Creating AsyncSqliteSaver checkpointer at: {db_path}")

        try:
            # AsyncSqliteSaver.from_conn_string returns an async context manager
            # We need to enter the context and keep it alive
            context_manager = AsyncSqliteSaver.from_conn_string(db_path_str)

            # Enter the async context manager
            actual_checkpointer = await context_manager.__aenter__()

            # Cache both the checkpointer and context manager (to keep it alive)
            self._checkpointers[db_path_str] = actual_checkpointer
            self._context_managers[db_path_str] = context_manager

            logger.info(f"AsyncSqliteSaver checkpointer created and setup successfully")
            return actual_checkpointer

        except Exception as e:
            logger.error(f"Failed to create checkpointer: {e}", exc_info=True)
            raise

    async def close_checkpointer(self, db_path: Optional[str] = None):
        """
        Close a checkpointer and its context manager properly

        Args:
            db_path: Database path. If None, closes default checkpointer
        """
        if db_path is None:
            db_path = str(self.checkpoint_dir / "default_checkpoint.db")
        else:
            db_path = str(db_path)

        if db_path in self._context_managers:
            try:
                context_manager = self._context_managers[db_path]
                await context_manager.__aexit__(None, None, None)
                logger.info(f"Checkpointer closed for: {db_path}")
            except Exception as e:
                logger.error(f"Error closing checkpointer: {e}")
            finally:
                # Clean up cache
                self._context_managers.pop(db_path, None)
                self._checkpointers.pop(db_path, None)

    async def close_all(self):
        """Close all open checkpointers"""
        for db_path in list(self._context_managers.keys()):
            await self.close_checkpointer(db_path)

    def validate_checkpoint_setup(self) -> bool:
        """
        Validate that the checkpoint system is properly configured

        Returns:
            True if everything is set up correctly
        """
        checks = []

        # Check checkpoint directory exists
        if not self.checkpoint_dir.exists():
            checks.append(f"Checkpoint directory does not exist: {self.checkpoint_dir}")

        # Check checkpoint directory is writable
        test_file = self.checkpoint_dir / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            checks.append(f"Checkpoint directory is not writable: {e}")

        if checks:
            for check in checks:
                logger.error(check)
            return False

        logger.info("Checkpoint setup validation passed")
        return True


# Module-level singleton instance
_checkpointer_manager = None


def get_checkpointer_manager() -> CheckpointerManager:
    """
    Get the singleton CheckpointerManager instance

    Returns:
        CheckpointerManager singleton instance
    """
    global _checkpointer_manager
    if _checkpointer_manager is None:
        _checkpointer_manager = CheckpointerManager()
    return _checkpointer_manager


async def create_checkpointer(db_path: Optional[str] = None) -> AsyncSqliteSaver:
    """
    Convenience function to create a checkpointer

    Args:
        db_path: Optional database path

    Returns:
        AsyncSqliteSaver instance
    """
    manager = get_checkpointer_manager()
    return await manager.create_checkpointer(db_path)