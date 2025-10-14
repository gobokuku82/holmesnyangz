"""
Script to create Long-term Memory tables in PostgreSQL
"""
import asyncio
from app.db.postgre_db import engine, Base
from app.models.memory import ConversationMemory, UserPreference, EntityMemory
from app.models.users import User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_tables():
    """Create all Memory tables"""
    try:
        logger.info("Creating Long-term Memory tables...")

        async with engine.begin() as conn:
            # Import all models to ensure they're registered
            await conn.run_sync(Base.metadata.create_all)

        logger.info("✅ Memory tables created successfully!")
        logger.info("Created tables:")
        logger.info("  - conversation_memories")
        logger.info("  - user_preferences")
        logger.info("  - entity_memories")

    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(create_tables())
