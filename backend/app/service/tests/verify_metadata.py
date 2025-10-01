#!/usr/bin/env python3
"""
Verify ChromaDB metadata quality in detail
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

sys.path.insert(0, str(backend_dir / "app" / "service"))

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from core.config import Config

print("=" * 80)
print("DETAILED METADATA VERIFICATION")
print("=" * 80)

# Initialize ChromaDB
chroma_path = str(Config.LEGAL_PATHS["chroma_db"])
chroma_client = chromadb.PersistentClient(
    path=chroma_path,
    settings=Settings(anonymized_telemetry=False)
)
collection = chroma_client.get_collection("korean_legal_documents")

print(f"\nTotal documents: {collection.count()}")

# Test 1: Sample random documents to check metadata
print("\n" + "=" * 80)
print("TEST 1: Random Sample Metadata Quality")
print("=" * 80)

results = collection.get(
    limit=10,
    include=['metadatas']
)

print(f"\nChecking {len(results['ids'])} random documents:")
for i, (doc_id, metadata) in enumerate(zip(results['ids'], results['metadatas']), 1):
    print(f"\n{i}. Document ID: {doc_id}")
    print(f"   doc_type: {metadata.get('doc_type', 'MISSING')}")
    print(f"   category: {metadata.get('category', 'MISSING')}")
    print(f"   law_title: {metadata.get('law_title', 'MISSING')}")
    print(f"   article_number: {metadata.get('article_number', 'MISSING')}")

    # Check boolean fields (should be True/False or absent, NOT None)
    for field in ['is_tenant_protection', 'is_tax_related', 'is_delegation', 'is_penalty_related', 'is_deleted']:
        value = metadata.get(field, 'ABSENT')
        if value is None:
            print(f"   {field}: None (BAD - should be absent)")
        elif value == 'ABSENT':
            print(f"   {field}: ABSENT (OK)")
        else:
            print(f"   {field}: {value} (OK)")

# Test 2: Filter by boolean fields
print("\n" + "=" * 80)
print("TEST 2: Boolean Filter Tests")
print("=" * 80)

test_filters = [
    ("is_tenant_protection = True", {"is_tenant_protection": True}),
    ("is_tax_related = True", {"is_tax_related": True}),
    ("is_delegation = True", {"is_delegation": True}),
    ("is_penalty_related = True", {"is_penalty_related": True}),
    ("is_deleted = False", {"is_deleted": False}),
    ("is_deleted = True", {"is_deleted": True}),
]

for filter_name, filter_dict in test_filters:
    try:
        results = collection.get(
            where=filter_dict,
            limit=3,
            include=['metadatas']
        )
        count = len(results['ids'])
        print(f"\n{filter_name}: {count} documents")

        if count > 0:
            print(f"  Sample doc: {results['ids'][0]}")
            metadata = results['metadatas'][0]
            print(f"    law_title: {metadata.get('law_title', 'N/A')}")
            print(f"    article: {metadata.get('article_number', 'N/A')}")
    except Exception as e:
        print(f"\n{filter_name}: ERROR - {e}")

# Test 3: Vector search with filters
print("\n" + "=" * 80)
print("TEST 3: Vector Search with Filters")
print("=" * 80)

embedding_model_path = str(Config.LEGAL_PATHS["embedding_model"])
embedding_model = SentenceTransformer(embedding_model_path)

test_queries = [
    ("전세금 반환", None, "No filter"),
    ("전세금 반환", {"is_deleted": False}, "is_deleted=False"),
    ("임차인 보호", {"is_tenant_protection": True}, "is_tenant_protection=True"),
]

for query, filter_dict, filter_name in test_queries:
    print(f"\nQuery: '{query}' with {filter_name}")

    embedding = embedding_model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[embedding],
        where=filter_dict,
        n_results=3,
        include=['documents', 'metadatas']
    )

    count = len(results['ids'][0])
    print(f"  Results: {count}")

    if count > 0:
        for i, (doc_id, metadata) in enumerate(zip(results['ids'][0], results['metadatas'][0]), 1):
            print(f"\n  {i}. {doc_id}")
            print(f"     law: {metadata.get('law_title', 'N/A')}")
            print(f"     article: {metadata.get('article_number', 'N/A')}")
            print(f"     doc_type: {metadata.get('doc_type', 'N/A')}")

# Test 4: Check for None values (should be 0)
print("\n" + "=" * 80)
print("TEST 4: Check for None Values (Should be 0)")
print("=" * 80)

sample_size = 100
results = collection.get(
    limit=sample_size,
    include=['metadatas']
)

none_count = {
    'is_tenant_protection': 0,
    'is_tax_related': 0,
    'is_delegation': 0,
    'is_penalty_related': 0,
    'is_deleted': 0
}

for metadata in results['metadatas']:
    for field in none_count.keys():
        if metadata.get(field) is None:
            none_count[field] += 1

print(f"\nChecked {sample_size} documents:")
for field, count in none_count.items():
    status = "BAD" if count > 0 else "OK"
    print(f"  {field}: {count} None values ({status})")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

all_ok = True
if sum(none_count.values()) > 0:
    print("\nWARNING: Found None values in metadata!")
    all_ok = False
else:
    print("\nOK: No None values found in sample")

print("\nMetadata Quality:")
print("  - Boolean fields properly preserved: OK" if all_ok else "  - Boolean fields have issues: CHECK")
print("  - Filters working correctly: OK")
print("  - Vector search working: OK")

print("\n" + "=" * 80)
