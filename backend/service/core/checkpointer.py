"""
Checkpointer utilities for state management

IMPORTANT: thread_id Usage in LangGraph
- thread_id is a configuration parameter, NOT a state field
- It's passed via config["configurable"]["thread_id"] when invoking graphs
- Use context.chat_thread_id or context.chat_session_id as the thread_id value
- This ensures proper state persistence across graph executions
"""

from typing import Optional
from pathlib import Path
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.sqlite import SqliteSaver
import logging


logger = logging.getLogger(__name__)


def get_checkpointer(
    checkpoint_path: str,
    async_mode: bool = True
) -> Optional[AsyncSqliteSaver]:
    """
    Get a checkpointer instance

    Args:
        checkpoint_path: Path to the checkpoint database
        async_mode: Whether to use async checkpointer

    Returns:
        Checkpointer instance or None if failed
    """
    try:
        # Ensure directory exists
        checkpoint_path = Path(checkpoint_path)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        if async_mode:
            # Use AsyncSqliteSaver for async operations
            checkpointer = AsyncSqliteSaver.from_conn_string(str(checkpoint_path))
            logger.info(f"AsyncSqliteSaver initialized at {checkpoint_path}")
        else:
            # Use regular SqliteSaver for sync operations
            checkpointer = SqliteSaver.from_conn_string(str(checkpoint_path))
            logger.info(f"SqliteSaver initialized at {checkpoint_path}")

        return checkpointer

    except Exception as e:
        logger.error(f"Failed to initialize checkpointer: {e}")
        return None


async def cleanup_old_checkpoints(
    checkpoint_dir: Path,
    keep_last: int = 5
) -> int:
    """
    Clean up old checkpoint files

    Args:
        checkpoint_dir: Directory containing checkpoints
        keep_last: Number of recent checkpoints to keep

    Returns:
        Number of files cleaned up
    """
    try:
        if not checkpoint_dir.exists():
            return 0

        # Get all checkpoint files sorted by modification time
        checkpoint_files = sorted(
            checkpoint_dir.glob("*.db"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        # Keep only the most recent files
        files_to_remove = checkpoint_files[keep_last:]
        removed_count = 0

        for file_path in files_to_remove:
            try:
                file_path.unlink()
                removed_count += 1
                logger.debug(f"Removed old checkpoint: {file_path}")
            except Exception as e:
                logger.error(f"Failed to remove {file_path}: {e}")

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old checkpoint files")

        return removed_count

    except Exception as e:
        logger.error(f"Failed to cleanup checkpoints: {e}")
        return 0