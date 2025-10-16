"""
Fix database schema - add missing columns
"""

import asyncio
from sqlalchemy import text
from app.db.postgre_db import get_async_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fix_schema():
    """Add missing columns to chat_sessions table"""

    async for session in get_async_db():
        try:
            # Check if columns exist
            check_query = """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'chat_sessions'
                AND column_name IN ('last_message', 'message_count')
            """

            result = await session.execute(text(check_query))
            existing_columns = {row[0] for row in result}

            # Add missing columns
            if 'last_message' not in existing_columns:
                logger.info("Adding last_message column...")
                await session.execute(text(
                    "ALTER TABLE chat_sessions ADD COLUMN last_message TEXT"
                ))
                logger.info("✅ last_message column added")
            else:
                logger.info("last_message column already exists")

            if 'message_count' not in existing_columns:
                logger.info("Adding message_count column...")
                await session.execute(text(
                    "ALTER TABLE chat_sessions ADD COLUMN message_count INTEGER DEFAULT 0"
                ))
                logger.info("✅ message_count column added")
            else:
                logger.info("message_count column already exists")

            await session.commit()
            logger.info("Schema fixed successfully!")

        except Exception as e:
            logger.error(f"Error fixing schema: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()
            break


if __name__ == "__main__":
    import sys
    import selectors

    # Windows-specific event loop fix for asyncpg
    if sys.platform == "win32":
        selector = selectors.SelectSelector()
        loop = asyncio.SelectorEventLoop(selector)
        asyncio.set_event_loop(loop)

    asyncio.run(fix_schema())