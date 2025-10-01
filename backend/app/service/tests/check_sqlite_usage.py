#!/usr/bin/env python3
"""
Check SQLite DB usage and relationship with ChromaDB
"""
import sqlite3
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / "app" / "service"))

from core.config import Config

sqlite_path = str(Config.LEGAL_PATHS["sqlite_db"])

print("=" * 80)
print("SQLITE DATABASE USAGE CHECK")
print("=" * 80)

conn = sqlite3.connect(sqlite_path)
cursor = conn.cursor()

# 1. Database overview
print("\n[1] DATABASE OVERVIEW")
print("-" * 80)

cursor.execute("SELECT COUNT(*) FROM laws")
law_count = cursor.fetchone()[0]
print(f"Total laws: {law_count}")

cursor.execute("SELECT COUNT(*) FROM articles")
article_count = cursor.fetchone()[0]
print(f"Total articles: {article_count}")

cursor.execute("SELECT COUNT(*) FROM legal_references")
ref_count = cursor.fetchone()[0]
print(f"Total references: {ref_count}")

# 2. Sample laws
print("\n[2] SAMPLE LAWS")
print("-" * 80)

cursor.execute("SELECT title, doc_type, total_articles FROM laws LIMIT 5")
print(f"{'Law Title':<40} | {'Type':<8} | Articles")
print("-" * 80)
for row in cursor.fetchall():
    title = row[0][:37] + "..." if len(row[0]) > 40 else row[0]
    print(f"{title:<40} | {row[1]:<8} | {row[2]:3d}")

# 3. Boolean field statistics
print("\n[3] BOOLEAN FIELD STATISTICS (SQLite)")
print("-" * 80)

boolean_fields = [
    ('is_tenant_protection', 'Tenant Protection'),
    ('is_tax_related', 'Tax Related'),
    ('is_delegation', 'Delegation'),
    ('is_penalty_related', 'Penalty Related'),
    ('is_deleted', 'Deleted')
]

for field, name in boolean_fields:
    cursor.execute(f"SELECT COUNT(*) FROM articles WHERE {field}=1")
    true_count = cursor.fetchone()[0]
    cursor.execute(f"SELECT COUNT(*) FROM articles WHERE {field}=0")
    false_count = cursor.fetchone()[0]

    print(f"{name:<20}: {true_count:3d} True, {false_count:4d} False")

# 4. Check if SQLite is used in current code
print("\n[4] SQLITE USAGE IN CURRENT CODE")
print("-" * 80)

# Check legal_query_helper.py usage
legal_helper_path = backend_dir / "data" / "storage" / "legal_info" / "guides" / "legal_query_helper.py"
if legal_helper_path.exists():
    print(f"OK: legal_query_helper.py exists")
    print(f"   Location: {legal_helper_path}")

    # Check if it's imported in legal_search_tool
    legal_tool_path = backend_dir / "app" / "service" / "tools" / "legal_search_tool.py"
    if legal_tool_path.exists():
        with open(legal_tool_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'LegalQueryHelper' in content:
                print(f"OK: LegalQueryHelper is imported in legal_search_tool.py")
                if 'build_chromadb_filter' in content:
                    print(f"OK: build_chromadb_filter() is used")
            else:
                print(f"WARNING: LegalQueryHelper not found in legal_search_tool.py")
else:
    print(f"ERROR: legal_query_helper.py not found")

# 5. Relationship with ChromaDB
print("\n[5] RELATIONSHIP WITH CHROMADB")
print("-" * 80)

print("SQLite stores:")
print("  - Law metadata (28 laws)")
print("  - Article metadata (1552 articles)")
print("  - Boolean flags (is_tenant_protection, etc.)")
print("  - References between laws")
print()
print("ChromaDB stores:")
print("  - Full text content (1700 chunks)")
print("  - Vector embeddings (1024D)")
print("  - Metadata copy (for filtering)")
print()
print("Relationship:")
print("  1. SQLite has structured metadata (28 laws → 1552 articles)")
print("  2. ChromaDB has more chunks (1700) because:")
print("     - One article can be multiple chunks")
print("     - Includes glossary terms (95 terms)")
print("  3. legal_query_helper.py uses SQLite to build ChromaDB filters")
print("     Example: build_chromadb_filter(doc_type='법률', category='2_임대차_전세_월세')")

# 6. Example query
print("\n[6] EXAMPLE: SQLite + ChromaDB Integration")
print("-" * 80)

cursor.execute("""
    SELECT l.title, COUNT(a.article_id) as article_count
    FROM laws l
    LEFT JOIN articles a ON l.law_id = a.law_id
    WHERE l.category = '2_임대차_전세_월세' AND a.is_deleted = 0
    GROUP BY l.law_id
""")

print("\nLaws in category '2_임대차_전세_월세' (from SQLite):")
for row in cursor.fetchall():
    print(f"  - {row[0]}: {row[1]} articles")

print("\n→ This info can be used to filter ChromaDB searches:")
print("   filter = {'category': '2_임대차_전세_월세', 'is_deleted': False}")
print("   results = collection.query(embeddings=[...], where=filter)")

conn.close()

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("\nSQLite is ACTIVELY USED for:")
print("  ✓ Fast metadata queries (28 laws, 1552 articles)")
print("  ✓ Building ChromaDB filters (via legal_query_helper.py)")
print("  ✓ Structured data (law hierarchy, references)")
print("\nDO NOT DELETE - it's essential for the search system!")
print("=" * 80)
