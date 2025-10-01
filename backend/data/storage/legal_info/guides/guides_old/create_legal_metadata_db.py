"""
Create SQLite metadata database from ChromaDB legal documents
Enables fast filtering and metadata queries for LangGraph agents
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import chromadb
from chromadb.config import Settings
from tqdm import tqdm
import json
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LegalMetadataDB:
    """Create and manage SQLite metadata database for legal documents"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Connect to SQLite database"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        logger.info(f"Connected to SQLite database: {self.db_path}")

    def create_schema(self):
        """Create database schema with optimized indexes"""
        cursor = self.conn.cursor()

        # Table 1: Laws - 법령 기본 정보
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS laws (
                law_id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_type TEXT NOT NULL,
                title TEXT NOT NULL,
                number TEXT,
                enforcement_date TEXT,
                category TEXT NOT NULL,
                total_articles INTEGER DEFAULT 0,
                last_article TEXT,
                source_file TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(title, number, doc_type)
            )
        """)

        # Table 2: Articles - 조항 상세 정보
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                article_id INTEGER PRIMARY KEY AUTOINCREMENT,
                law_id INTEGER NOT NULL,
                article_number TEXT NOT NULL,
                article_title TEXT,
                chapter TEXT,
                section TEXT,
                is_deleted INTEGER DEFAULT 0,
                is_tenant_protection INTEGER DEFAULT 0,
                is_tax_related INTEGER DEFAULT 0,
                is_delegation INTEGER DEFAULT 0,
                is_penalty_related INTEGER DEFAULT 0,
                chunk_ids TEXT,  -- JSON array of ChromaDB chunk IDs
                metadata_json TEXT,  -- Full metadata as JSON for flexibility
                FOREIGN KEY (law_id) REFERENCES laws(law_id),
                UNIQUE(law_id, article_number)
            )
        """)

        # Table 3: Legal References - 법령 간 참조 관계
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS legal_references (
                reference_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_article_id INTEGER NOT NULL,
                reference_type TEXT NOT NULL,  -- law_references, decree_references, form_references
                target_law_title TEXT,
                target_article_number TEXT,
                reference_text TEXT,  -- Original reference text
                FOREIGN KEY (source_article_id) REFERENCES articles(article_id)
            )
        """)

        # Create indexes for fast queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_laws_doc_type ON laws(doc_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_laws_enforcement_date ON laws(enforcement_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_laws_category ON laws(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_laws_title ON laws(title)")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_law_id ON articles(law_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_number ON articles(article_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_deleted ON articles(is_deleted)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_tenant ON articles(is_tenant_protection)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_tax ON articles(is_tax_related)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_delegation ON articles(is_delegation)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_penalty ON articles(is_penalty_related)")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_references_source ON legal_references(source_article_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_references_type ON legal_references(reference_type)")

        self.conn.commit()
        logger.info("Database schema created successfully")

    def extract_law_info(self, metadata: Dict[str, Any]) -> Dict[str, str]:
        """Extract law information from metadata"""
        # Determine doc_type and corresponding fields
        doc_type = metadata.get('doc_type', '기타')

        if doc_type == '법률':
            title = metadata.get('law_title', '')
            number = metadata.get('law_number', '')
        elif doc_type == '시행령':
            title = metadata.get('decree_title', '')
            number = metadata.get('decree_number', '')
        elif doc_type == '시행규칙':
            title = metadata.get('rule_title', '')
            number = metadata.get('rule_number', '')
        elif doc_type == '대법원규칙':
            title = metadata.get('court_rule_title', metadata.get('rule_title', ''))
            number = metadata.get('court_rule_number', metadata.get('rule_number', ''))
        else:
            # Extract from source_file
            source_file = metadata.get('source_file', '')
            title = source_file.split('(')[0] if '(' in source_file else source_file
            number = ''

        return {
            'doc_type': doc_type,
            'title': title,
            'number': number,
            'enforcement_date': metadata.get('enforcement_date', ''),
            'category': metadata.get('category', ''),
            'source_file': metadata.get('source_file', '')
        }

    def populate_from_chromadb(self, chroma_path: str):
        """Load data from ChromaDB and populate SQLite"""
        logger.info("Connecting to ChromaDB...")

        # Connect to ChromaDB
        chroma_client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False)
        )
        collection = chroma_client.get_collection("korean_legal_documents")
        total_docs = collection.count()
        logger.info(f"Total documents in ChromaDB: {total_docs}")

        # Get all documents
        logger.info("Retrieving all documents from ChromaDB...")
        results = collection.get(include=['metadatas'])
        chunk_ids = results['ids']
        metadatas = results['metadatas']

        # Group by law
        laws_data = defaultdict(lambda: {
            'articles': [],
            'info': None,
            'article_numbers': set()
        })

        logger.info("Grouping documents by law...")
        for chunk_id, metadata in tqdm(zip(chunk_ids, metadatas), total=len(chunk_ids), desc="Processing"):
            law_info = self.extract_law_info(metadata)
            law_key = (law_info['title'], law_info['number'], law_info['doc_type'])

            if laws_data[law_key]['info'] is None:
                laws_data[law_key]['info'] = law_info

            # Store article info
            article_number = metadata.get('article_number', '')
            laws_data[law_key]['article_numbers'].add(article_number)
            laws_data[law_key]['articles'].append({
                'chunk_id': chunk_id,
                'article_number': article_number,
                'article_title': metadata.get('article_title', ''),
                'chapter': metadata.get('chapter', ''),
                'section': metadata.get('section', ''),
                'is_deleted': 1 if metadata.get('is_deleted') == 'True' or metadata.get('is_deleted') == True else 0,
                'is_tenant_protection': 1 if metadata.get('is_tenant_protection') == 'True' or metadata.get('is_tenant_protection') == True else 0,
                'is_tax_related': 1 if metadata.get('is_tax_related') == 'True' or metadata.get('is_tax_related') == True else 0,
                'is_delegation': 1 if metadata.get('is_delegation') == 'True' or metadata.get('is_delegation') == True else 0,
                'is_penalty_related': 1 if metadata.get('is_penalty_related') == 'True' or metadata.get('is_penalty_related') == True else 0,
                'metadata': metadata
            })

        # Insert into database
        cursor = self.conn.cursor()

        logger.info(f"Inserting {len(laws_data)} laws into database...")
        for law_key, law_data in tqdm(laws_data.items(), desc="Inserting laws"):
            law_info = law_data['info']
            article_numbers = sorted(law_data['article_numbers'])

            # Calculate total articles and last article
            total_articles = len(article_numbers)
            last_article = article_numbers[-1] if article_numbers else ''

            # Insert law
            cursor.execute("""
                INSERT OR IGNORE INTO laws
                (doc_type, title, number, enforcement_date, category, total_articles, last_article, source_file)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                law_info['doc_type'],
                law_info['title'],
                law_info['number'],
                law_info['enforcement_date'],
                law_info['category'],
                total_articles,
                last_article,
                law_info['source_file']
            ))

            # Get law_id
            law_id = cursor.execute("""
                SELECT law_id FROM laws
                WHERE title = ? AND number = ? AND doc_type = ?
            """, (law_info['title'], law_info['number'], law_info['doc_type'])).fetchone()[0]

            # Group articles by article_number (handle multiple chunks per article)
            articles_by_number = defaultdict(list)
            for article in law_data['articles']:
                articles_by_number[article['article_number']].append(article)

            # Insert articles
            for article_number, article_chunks in articles_by_number.items():
                # Use first chunk's data for article info, collect all chunk_ids
                first_chunk = article_chunks[0]
                chunk_ids_list = [chunk['chunk_id'] for chunk in article_chunks]

                cursor.execute("""
                    INSERT OR IGNORE INTO articles
                    (law_id, article_number, article_title, chapter, section,
                     is_deleted, is_tenant_protection, is_tax_related, is_delegation, is_penalty_related,
                     chunk_ids, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    law_id,
                    article_number,
                    first_chunk['article_title'],
                    first_chunk['chapter'],
                    first_chunk['section'],
                    first_chunk['is_deleted'],
                    first_chunk['is_tenant_protection'],
                    first_chunk['is_tax_related'],
                    first_chunk['is_delegation'],
                    first_chunk['is_penalty_related'],
                    json.dumps(chunk_ids_list, ensure_ascii=False),
                    json.dumps(first_chunk['metadata'], ensure_ascii=False)
                ))

                # Get article_id for references
                article_id = cursor.execute("""
                    SELECT article_id FROM articles
                    WHERE law_id = ? AND article_number = ?
                """, (law_id, article_number)).fetchone()[0]

                # Parse and insert references
                metadata = first_chunk['metadata']
                for ref_type in ['law_references', 'decree_references', 'form_references']:
                    ref_data = metadata.get(ref_type)
                    if ref_data:
                        # Handle JSON string
                        if isinstance(ref_data, str):
                            try:
                                ref_data = json.loads(ref_data)
                            except:
                                continue

                        if isinstance(ref_data, list):
                            for ref in ref_data:
                                if isinstance(ref, dict):
                                    cursor.execute("""
                                        INSERT INTO legal_references
                                        (source_article_id, reference_type, target_law_title, target_article_number, reference_text)
                                        VALUES (?, ?, ?, ?, ?)
                                    """, (
                                        article_id,
                                        ref_type,
                                        ref.get('law_title', ref.get('title', '')),
                                        ref.get('article', ''),
                                        str(ref)
                                    ))

        self.conn.commit()
        logger.info("Database population completed")

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        cursor = self.conn.cursor()

        stats = {}

        # Total counts
        stats['total_laws'] = cursor.execute("SELECT COUNT(*) FROM laws").fetchone()[0]
        stats['total_articles'] = cursor.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        stats['total_references'] = cursor.execute("SELECT COUNT(*) FROM legal_references").fetchone()[0]

        # By doc_type
        stats['by_doc_type'] = {}
        for row in cursor.execute("SELECT doc_type, COUNT(*) as count FROM laws GROUP BY doc_type ORDER BY count DESC"):
            stats['by_doc_type'][row[0]] = row[1]

        # By category
        stats['by_category'] = {}
        for row in cursor.execute("SELECT category, COUNT(*) as count FROM laws GROUP BY category ORDER BY count DESC"):
            stats['by_category'][row[0]] = row[1]

        # Special articles
        stats['tenant_protection'] = cursor.execute("SELECT COUNT(*) FROM articles WHERE is_tenant_protection = 1").fetchone()[0]
        stats['tax_related'] = cursor.execute("SELECT COUNT(*) FROM articles WHERE is_tax_related = 1").fetchone()[0]
        stats['delegation'] = cursor.execute("SELECT COUNT(*) FROM articles WHERE is_delegation = 1").fetchone()[0]
        stats['penalty_related'] = cursor.execute("SELECT COUNT(*) FROM articles WHERE is_penalty_related = 1").fetchone()[0]

        return stats

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


def main():
    """Main function to create and populate database"""
    print("=" * 70)
    print("Creating Legal Metadata SQLite Database")
    print("=" * 70)

    # Paths
    base_path = Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info")
    db_path = base_path / "legal_metadata.db"
    chroma_path = base_path / "chroma_db"

    # Remove existing database
    if db_path.exists():
        logger.info(f"Removing existing database: {db_path}")
        db_path.unlink()

    # Create database
    db = LegalMetadataDB(str(db_path))
    db.connect()

    # Create schema
    logger.info("Creating database schema...")
    db.create_schema()

    # Populate from ChromaDB
    logger.info("Populating database from ChromaDB...")
    db.populate_from_chromadb(str(chroma_path))

    # Show statistics
    print("\n" + "=" * 70)
    print("Database Statistics")
    print("=" * 70)

    stats = db.get_statistics()

    print(f"\nTotal Counts:")
    print(f"  Laws: {stats['total_laws']}")
    print(f"  Articles: {stats['total_articles']}")
    print(f"  References: {stats['total_references']}")

    print(f"\nBy Document Type:")
    for doc_type, count in stats['by_doc_type'].items():
        print(f"  {doc_type}: {count}")

    print(f"\nBy Category:")
    for category, count in stats['by_category'].items():
        print(f"  {category}: {count}")

    print(f"\nSpecial Articles:")
    print(f"  Tenant Protection: {stats['tenant_protection']}")
    print(f"  Tax Related: {stats['tax_related']}")
    print(f"  Delegation: {stats['delegation']}")
    print(f"  Penalty Related: {stats['penalty_related']}")

    db.close()

    print("\n" + "=" * 70)
    print("Database created successfully!")
    print(f"Location: {db_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
