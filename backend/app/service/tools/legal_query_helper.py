"""
Legal Query Helper for SQL Database
Provides fast metadata queries and ChromaDB chunk ID lookup
"""

import sqlite3
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging


class LegalQueryHelper:
    """Helper class for SQL database queries"""

    def __init__(self, db_path: str):
        """Initialize SQL database connection

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)

        # Verify database exists
        if not Path(db_path).exists():
            raise FileNotFoundError(f"Database not found: {db_path}")

        # Test connection
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM laws")
                count = cursor.fetchone()[0]
                self.logger.info(f"Connected to SQL DB: {count} laws found")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to database: {e}")

    def check_law_exists(self, title: str) -> bool:
        """Check if a law exists in the database

        Args:
            title: Law title to check (e.g., "민법", "주택임대차보호법")

        Returns:
            True if law exists, False otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Try exact match first
            cursor.execute(
                "SELECT COUNT(*) FROM laws WHERE title = ?",
                (title,)
            )
            count = cursor.fetchone()[0]

            if count > 0:
                return True

            # Try partial match (e.g., "주택임대차보호법" in "주택임대차보호법 시행령")
            cursor.execute(
                "SELECT COUNT(*) FROM laws WHERE title LIKE ?",
                (f"%{title}%",)
            )
            count = cursor.fetchone()[0]

            return count > 0

    def get_article_chunk_ids(self, title: str, article_number: str) -> List[str]:
        """Get ChromaDB chunk IDs for a specific article

        Args:
            title: Law title (e.g., "주택임대차보호법")
            article_number: Article number (e.g., "제7조")

        Returns:
            List of chunk IDs, empty list if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # First, find the law_id
            cursor.execute("""
                SELECT law_id FROM laws
                WHERE title LIKE ?
                LIMIT 1
            """, (f"%{title}%",))

            result = cursor.fetchone()
            if not result:
                self.logger.debug(f"Law not found: {title}")
                return []

            law_id = result[0]

            # Then, get chunk_ids for the article
            cursor.execute("""
                SELECT chunk_ids FROM articles
                WHERE law_id = ? AND article_number = ? AND is_deleted = 0
            """, (law_id, article_number))

            result = cursor.fetchone()
            if not result or not result[0]:
                self.logger.debug(f"Article not found: {title} {article_number}")
                return []

            # Parse JSON array of chunk IDs
            try:
                chunk_ids = json.loads(result[0])
                return chunk_ids if isinstance(chunk_ids, list) else [chunk_ids]
            except json.JSONDecodeError:
                # If not JSON, treat as single ID
                return [result[0]]

    def get_law_by_title(self, title: str, fuzzy: bool = True) -> Optional[Dict[str, Any]]:
        """Get law information by title

        Args:
            title: Law title
            fuzzy: Use fuzzy matching if True

        Returns:
            Law information dict or None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if fuzzy:
                cursor.execute("""
                    SELECT law_id, doc_type, title, number as law_number,
                           enforcement_date, category, total_articles, last_article
                    FROM laws
                    WHERE title LIKE ?
                    LIMIT 1
                """, (f"%{title}%",))
            else:
                cursor.execute("""
                    SELECT law_id, doc_type, title, number as law_number,
                           enforcement_date, category, total_articles, last_article
                    FROM laws
                    WHERE title = ?
                    LIMIT 1
                """, (title,))

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def search_articles_by_title(self, title: str, article_number: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search articles by law title and optionally article number

        Args:
            title: Law title
            article_number: Optional article number to filter

        Returns:
            List of article information
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if article_number:
                cursor.execute("""
                    SELECT a.article_id, a.article_number, a.article_title,
                           a.chapter, a.section, a.chunk_ids,
                           l.title as law_title, l.doc_type
                    FROM articles a
                    JOIN laws l ON a.law_id = l.law_id
                    WHERE l.title LIKE ? AND a.article_number = ?
                          AND a.is_deleted = 0
                """, (f"%{title}%", article_number))
            else:
                cursor.execute("""
                    SELECT a.article_id, a.article_number, a.article_title,
                           a.chapter, a.section, a.chunk_ids,
                           l.title as law_title, l.doc_type
                    FROM articles a
                    JOIN laws l ON a.law_id = l.law_id
                    WHERE l.title LIKE ? AND a.is_deleted = 0
                    ORDER BY a.article_number
                """, (f"%{title}%",))

            return [dict(row) for row in cursor.fetchall()]

    def get_all_law_titles(self) -> List[str]:
        """Get all law titles in the database

        Returns:
            List of law titles
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT title FROM laws ORDER BY title")
            return [row[0] for row in cursor.fetchall()]

    def build_chromadb_filter(
        self,
        doc_type: Optional[str] = None,
        category: Optional[str] = None,
        article_type: Optional[str] = None,
        exclude_deleted: bool = True,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Build ChromaDB filter dictionary based on SQL metadata

        Args:
            doc_type: Document type filter
            category: Category filter
            article_type: Article type (tenant_protection, tax_related, etc.)
            exclude_deleted: Exclude deleted articles

        Returns:
            Filter dictionary for ChromaDB where clause
        """
        conditions = []

        # Always exclude deleted documents by default
        if exclude_deleted:
            conditions.append({'is_deleted': {'$ne': 'True'}})

        if doc_type:
            conditions.append({'doc_type': doc_type})

        if category:
            conditions.append({'category': category})

        # Handle special article types
        if article_type == "tenant_protection":
            conditions.append({'is_tenant_protection': 'True'})
        elif article_type == "tax_related":
            conditions.append({'is_tax_related': 'True'})
        elif article_type == "delegation":
            conditions.append({'is_delegation': 'True'})
        elif article_type == "penalty":
            conditions.append({'is_penalty_related': 'True'})

        if len(conditions) == 0:
            return None
        elif len(conditions) == 1:
            return conditions[0]
        else:
            return {'$and': conditions}

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics

        Returns:
            Statistics dictionary
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            stats = {}

            # Total laws
            cursor.execute("SELECT COUNT(*) FROM laws")
            stats['total_laws'] = cursor.fetchone()[0]

            # Total articles
            cursor.execute("SELECT COUNT(*) FROM articles WHERE is_deleted = 0")
            stats['total_articles'] = cursor.fetchone()[0]

            # By document type
            cursor.execute("""
                SELECT doc_type, COUNT(*) as count
                FROM laws
                GROUP BY doc_type
            """)
            stats['by_doc_type'] = dict(cursor.fetchall())

            # By category
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM laws
                GROUP BY category
            """)
            stats['by_category'] = dict(cursor.fetchall())

            return stats