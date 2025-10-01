#!/usr/bin/env python3
"""
Analyze ChromaDB and SQLite metadata quality
"""
import sys
from pathlib import Path
import sqlite3
import json

backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

sys.path.insert(0, str(backend_dir / "app" / "service"))

import chromadb
from chromadb.config import Settings
from core.config import Config

print("=" * 80)
print("METADATA QUALITY ANALYSIS")
print("=" * 80)

# === 1. ChromaDB Analysis ===
print("\n[1] CHROMADB ANALYSIS")
print("-" * 80)

chroma_path = str(Config.LEGAL_PATHS["chroma_db"])
chroma_client = chromadb.PersistentClient(
    path=chroma_path,
    settings=Settings(anonymized_telemetry=False)
)
collection = chroma_client.get_collection("korean_legal_documents")

total_docs = collection.count()
print(f"Total documents in ChromaDB: {total_docs}")

# Get all documents (in batches)
batch_size = 500
metadata_stats = {
    'doc_type': {},
    'category': {},
    'is_tenant_protection': {'True': 0, 'False': 0, 'None': 0},
    'is_tax_related': {'True': 0, 'False': 0, 'None': 0},
    'is_delegation': {'True': 0, 'False': 0, 'None': 0},
    'is_penalty_related': {'True': 0, 'False': 0, 'None': 0},
    'is_deleted': {'True': 0, 'False': 0, 'None': 0},
}

print("\nScanning all documents...")
offset = 0
while offset < total_docs:
    limit = min(batch_size, total_docs - offset)
    results = collection.get(
        limit=limit,
        offset=offset,
        include=['metadatas']
    )

    for metadata in results['metadatas']:
        # Doc type
        doc_type = metadata.get('doc_type', 'None')
        metadata_stats['doc_type'][doc_type] = metadata_stats['doc_type'].get(doc_type, 0) + 1

        # Category
        category = metadata.get('category', 'None')
        metadata_stats['category'][category] = metadata_stats['category'].get(category, 0) + 1

        # Boolean fields
        for field in ['is_tenant_protection', 'is_tax_related', 'is_delegation', 'is_penalty_related', 'is_deleted']:
            value = metadata.get(field)
            if value is True:
                metadata_stats[field]['True'] += 1
            elif value is False:
                metadata_stats[field]['False'] += 1
            else:
                metadata_stats[field]['None'] += 1

    offset += limit
    print(f"  Processed {offset}/{total_docs} documents...")

print("\n--- Doc Type Distribution ---")
for doc_type, count in sorted(metadata_stats['doc_type'].items(), key=lambda x: -x[1]):
    pct = (count / total_docs) * 100
    print(f"  {doc_type}: {count} ({pct:.1f}%)")

print("\n--- Category Distribution ---")
for category, count in sorted(metadata_stats['category'].items(), key=lambda x: -x[1]):
    pct = (count / total_docs) * 100
    print(f"  {category}: {count} ({pct:.1f}%)")

print("\n--- Boolean Fields Distribution ---")
for field in ['is_tenant_protection', 'is_tax_related', 'is_delegation', 'is_penalty_related', 'is_deleted']:
    stats = metadata_stats[field]
    print(f"\n{field}:")
    print(f"  True:  {stats['True']:4d} ({stats['True']/total_docs*100:5.1f}%)")
    print(f"  False: {stats['False']:4d} ({stats['False']/total_docs*100:5.1f}%)")
    print(f"  None:  {stats['None']:4d} ({stats['None']/total_docs*100:5.1f}%)")

# === 2. SQLite Analysis ===
print("\n" + "=" * 80)
print("[2] SQLITE METADATA ANALYSIS")
print("-" * 80)

sqlite_path = str(Config.LEGAL_PATHS["sqlite_db"])
conn = sqlite3.connect(sqlite_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Check laws table
cursor.execute("SELECT COUNT(*) as count FROM laws")
law_count = cursor.fetchone()['count']
print(f"Total laws: {law_count}")

# Check articles table
cursor.execute("SELECT COUNT(*) as count FROM articles")
article_count = cursor.fetchone()['count']
print(f"Total articles: {article_count}")

# Check article boolean fields
print("\n--- Article Boolean Fields in SQLite ---")
boolean_fields_sql = ['is_tenant_protection', 'is_tax_related', 'is_delegation', 'is_penalty_related', 'is_deleted']
for field in boolean_fields_sql:
    cursor.execute(f"""
        SELECT
            SUM(CASE WHEN {field} = 1 THEN 1 ELSE 0 END) as true_count,
            SUM(CASE WHEN {field} = 0 THEN 1 ELSE 0 END) as false_count,
            SUM(CASE WHEN {field} IS NULL THEN 1 ELSE 0 END) as null_count
        FROM articles
    """)
    result = cursor.fetchone()
    print(f"\n{field}:")
    print(f"  True:  {result['true_count']:4d} ({result['true_count']/article_count*100:5.1f}%)")
    print(f"  False: {result['false_count']:4d} ({result['false_count']/article_count*100:5.1f}%)")
    print(f"  NULL:  {result['null_count']:4d} ({result['null_count']/article_count*100:5.1f}%)")

conn.close()

# === 3. Consistency Check ===
print("\n" + "=" * 80)
print("[3] CONSISTENCY CHECK: ChromaDB vs SQLite")
print("-" * 80)

print(f"\nChromaDB documents: {total_docs}")
print(f"SQLite articles: {article_count}")

if total_docs > article_count:
    print(f"⚠️  ChromaDB has MORE documents than SQLite ({total_docs - article_count} extra)")
elif total_docs < article_count:
    print(f"⚠️  ChromaDB has FEWER documents than SQLite ({article_count - total_docs} missing)")
else:
    print("✓ Document counts match")

# === 4. Recommendations ===
print("\n" + "=" * 80)
print("[4] RECOMMENDATIONS")
print("-" * 80)

issues = []

# Check if metadata is mostly None
for field in ['is_tenant_protection', 'is_tax_related', 'is_delegation', 'is_penalty_related']:
    none_pct = (metadata_stats[field]['None'] / total_docs) * 100
    if none_pct > 90:
        issues.append(f"⚠️  {field}: {none_pct:.1f}% are None (metadata not populated)")
    elif none_pct > 50:
        issues.append(f"⚠️  {field}: {none_pct:.1f}% are None (metadata incomplete)")

# Check if categories are diverse
if len(metadata_stats['category']) <= 2:
    issues.append(f"⚠️  Only {len(metadata_stats['category'])} unique categories (low diversity)")

if issues:
    print("\nISSUES FOUND:")
    for issue in issues:
        print(f"  {issue}")

    print("\n📝 RECOMMENDATION:")
    print("  → Metadata quality is LOW")
    print("  → Two options:")
    print("     1. Re-generate ChromaDB with proper metadata from SQLite")
    print("     2. Disable article_type filters and use only doc_type/category")
else:
    print("\n✓ Metadata quality is GOOD")
    print("  → No need to regenerate database")

print("\n" + "=" * 80)
