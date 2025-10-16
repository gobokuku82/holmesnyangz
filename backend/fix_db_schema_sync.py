"""
Fix database schema - add missing columns (synchronous version)
"""

from sqlalchemy import create_engine, text
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_schema():
    """Add missing columns to chat_sessions table"""

    # Create synchronous engine using settings
    engine = create_engine(settings.sqlalchemy_url)

    with engine.connect() as conn:
        try:
            # Check if columns exist
            check_query = """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'chat_sessions'
                AND column_name IN ('last_message', 'message_count', 'is_active', 'title', 'metadata')
            """

            result = conn.execute(text(check_query))
            existing_columns = {row[0] for row in result}

            # Add missing columns
            if 'last_message' not in existing_columns:
                logger.info("Adding last_message column...")
                conn.execute(text(
                    "ALTER TABLE chat_sessions ADD COLUMN last_message TEXT"
                ))
                logger.info("✅ last_message column added")
            else:
                logger.info("last_message column already exists")

            if 'message_count' not in existing_columns:
                logger.info("Adding message_count column...")
                conn.execute(text(
                    "ALTER TABLE chat_sessions ADD COLUMN message_count INTEGER DEFAULT 0"
                ))
                logger.info("✅ message_count column added")
            else:
                logger.info("message_count column already exists")

            if 'is_active' not in existing_columns:
                logger.info("Adding is_active column...")
                conn.execute(text(
                    "ALTER TABLE chat_sessions ADD COLUMN is_active BOOLEAN DEFAULT TRUE"
                ))
                logger.info("✅ is_active column added")
            else:
                logger.info("is_active column already exists")

            if 'title' not in existing_columns:
                logger.info("Adding title column...")
                conn.execute(text(
                    "ALTER TABLE chat_sessions ADD COLUMN title VARCHAR(200) DEFAULT '새 대화'"
                ))
                logger.info("✅ title column added")
            else:
                logger.info("title column already exists")

            if 'metadata' not in existing_columns:
                logger.info("Adding metadata column...")
                conn.execute(text(
                    "ALTER TABLE chat_sessions ADD COLUMN metadata JSONB"
                ))
                logger.info("✅ metadata column added")
            else:
                logger.info("metadata column already exists")

            conn.commit()
            logger.info("Schema fixed successfully!")

        except Exception as e:
            logger.error(f"Error fixing schema: {e}")
            conn.rollback()
            raise


if __name__ == "__main__":
    fix_schema()