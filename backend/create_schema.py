#!/usr/bin/env python3
"""
Database Schema Creation Script
================================

Creates all database tables from unified_schema.py

Usage:
    python backend/create_schema.py [--drop] [--info]

Options:
    --drop    Drop all existing tables before creating (WARNING: deletes data!)
    --info    Show schema information only (no changes)

Examples:
    # Create tables (safe, won't drop existing)
    python backend/create_schema.py

    # Drop and recreate all tables (DANGEROUS!)
    python backend/create_schema.py --drop

    # Show schema info
    python backend/create_schema.py --info
"""

import sys
import argparse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add project root to path
sys.path.insert(0, '.')

from backend.app.models.unified_schema import (
    Base,
    ALL_MODELS,
    MODEL_NAMES,
    SCHEMA_SUMMARY,
    create_all_tables,
    drop_all_tables,
    print_schema_info
)
from backend.app.core.config import settings


def get_engine():
    """Create database engine from settings."""
    # Use sync psycopg driver for migrations
    database_url = settings.DATABASE_URL.replace(
        'postgresql+psycopg://',
        'postgresql+psycopg://'
    )

    print(f"🔌 Connecting to: {database_url.split('@')[1]}")  # Hide password

    engine = create_engine(
        database_url,
        echo=False,
        pool_pre_ping=True
    )

    return engine


def check_existing_tables(engine):
    """Check which tables already exist."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """))

        existing = [row[0] for row in result]

    return existing


def create_triggers(engine):
    """
    Create triggers and functions.

    Note: SQLAlchemy doesn't support triggers directly,
    so we use raw SQL here.
    """
    print("\n📌 Creating triggers and functions...")

    triggers_sql = """
    -- Trigger 1: updated_at 자동 갱신
    CREATE OR REPLACE FUNCTION update_chat_session_timestamp()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS trigger_update_chat_session_timestamp ON chat_sessions;
    CREATE TRIGGER trigger_update_chat_session_timestamp
        BEFORE UPDATE ON chat_sessions
        FOR EACH ROW
        EXECUTE FUNCTION update_chat_session_timestamp();

    -- Trigger 2: message_count, last_message 자동 갱신
    CREATE OR REPLACE FUNCTION update_session_message_count()
    RETURNS TRIGGER AS $$
    BEGIN
        IF TG_OP = 'INSERT' AND NEW.session_id IS NOT NULL THEN
            UPDATE chat_sessions
            SET
                message_count = message_count + 1,
                last_message = LEFT(NEW.query, 100),
                updated_at = NOW()
            WHERE session_id = NEW.session_id;

            -- 제목이 "새 대화"인 경우 첫 질문으로 자동 변경
            UPDATE chat_sessions
            SET title = LEFT(NEW.query, 30) || CASE WHEN LENGTH(NEW.query) > 30 THEN '...' ELSE '' END
            WHERE session_id = NEW.session_id AND title = '새 대화';
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS trigger_update_session_message_count ON conversation_memories;
    CREATE TRIGGER trigger_update_session_message_count
        AFTER INSERT ON conversation_memories
        FOR EACH ROW
        EXECUTE FUNCTION update_session_message_count();
    """

    with engine.connect() as conn:
        conn.execute(text(triggers_sql))
        conn.commit()

    print("  ✓ Triggers created successfully")


def verify_schema(engine):
    """Verify that all tables were created correctly."""
    print("\n🔍 Verifying schema...")

    existing_tables = check_existing_tables(engine)

    print(f"\n📊 Database Status:")
    print(f"  Expected tables: {len(MODEL_NAMES)}")
    print(f"  Existing tables: {len(existing_tables)}")

    missing = set(MODEL_NAMES) - set(existing_tables)
    extra = set(existing_tables) - set(MODEL_NAMES)

    if missing:
        print(f"\n⚠️  Missing tables: {', '.join(missing)}")

    if extra:
        print(f"\n📝 Extra tables (not in schema): {', '.join(extra)}")

    if not missing and set(MODEL_NAMES).issubset(set(existing_tables)):
        print("\n✅ All required tables exist!")

        # Show row counts
        print("\n📈 Table Row Counts:")
        with engine.connect() as conn:
            for table in MODEL_NAMES:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"  {table:30s} {count:>6d} rows")

    return missing, extra


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Create database schema from unified_schema.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--drop',
        action='store_true',
        help='Drop all existing tables before creating (WARNING: deletes data!)'
    )
    parser.add_argument(
        '--info',
        action='store_true',
        help='Show schema information only (no changes)'
    )
    parser.add_argument(
        '--skip-triggers',
        action='store_true',
        help='Skip trigger creation'
    )

    args = parser.parse_args()

    # Show info mode
    if args.info:
        print_schema_info()
        sys.exit(0)

    print("=" * 70)
    print("🏗️  Database Schema Creation")
    print("=" * 70)

    try:
        # Create engine
        engine = get_engine()

        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"✓ Connected to PostgreSQL: {version.split(',')[0]}")

        # Check existing tables
        existing_tables = check_existing_tables(engine)
        print(f"\n📋 Existing tables: {len(existing_tables)}")
        if existing_tables:
            print(f"  {', '.join(existing_tables[:5])}" +
                  (f" ... (+{len(existing_tables)-5} more)" if len(existing_tables) > 5 else ""))

        # Drop tables if requested
        if args.drop:
            print("\n⚠️  WARNING: About to drop all tables!")
            confirm = input("Type 'yes' to confirm: ")
            if confirm.lower() != 'yes':
                print("Aborted.")
                sys.exit(1)

            print("\n🗑️  Dropping all tables...")
            drop_all_tables(engine)

        # Create tables
        print(f"\n🏗️  Creating {len(MODEL_NAMES)} tables...")
        create_all_tables(engine)

        # Create triggers
        if not args.skip_triggers:
            create_triggers(engine)
        else:
            print("\n⏭️  Skipping trigger creation (--skip-triggers)")

        # Verify
        missing, extra = verify_schema(engine)

        print("\n" + "=" * 70)
        if not missing:
            print("✅ Schema creation completed successfully!")
        else:
            print("⚠️  Schema creation completed with warnings")
        print("=" * 70)

    except SQLAlchemyError as e:
        print(f"\n❌ Database error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
