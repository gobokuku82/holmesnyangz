#!/usr/bin/env python3
"""
Verify all 1700 documents are properly embedded
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / "app" / "service"))

import chromadb
from chromadb.config import Settings
from core.config import Config
import numpy as np

print("=" * 80)
print("EMBEDDING VERIFICATION")
print("=" * 80)

# Initialize ChromaDB
chroma_path = str(Config.LEGAL_PATHS["chroma_db"])
chroma_client = chromadb.PersistentClient(
    path=chroma_path,
    settings=Settings(anonymized_telemetry=False)
)
collection = chroma_client.get_collection("korean_legal_documents")

total_docs = collection.count()
print(f"\nTotal documents in ChromaDB: {total_docs}")

# Test 1: Check if all documents have embeddings
print("\n" + "=" * 80)
print("TEST 1: Document Count Verification")
print("=" * 80)

expected_count = 1700
if total_docs == expected_count:
    print(f"OK: Document count matches ({total_docs} = {expected_count})")
else:
    print(f"WARNING: Document count mismatch ({total_docs} != {expected_count})")
    print(f"  Missing: {expected_count - total_docs} documents")

# Test 2: Sample embeddings to verify they exist and are valid
print("\n" + "=" * 80)
print("TEST 2: Embedding Quality Check")
print("=" * 80)

sample_size = 10
results = collection.get(
    limit=sample_size,
    include=['embeddings', 'metadatas', 'documents']
)

print(f"\nChecking {len(results['ids'])} sample documents:")

issues = []
for i, (doc_id, embedding, doc, metadata) in enumerate(
    zip(results['ids'], results['embeddings'], results['documents'], results['metadatas']), 1
):
    # Check embedding exists
    if embedding is None:
        issues.append(f"{doc_id}: No embedding")
        continue

    # Check embedding dimension
    embedding_dim = len(embedding)
    expected_dim = 1024  # kure_v1 dimension

    # Check embedding is not all zeros
    embedding_array = np.array(embedding)
    is_zero = np.all(embedding_array == 0)

    # Check embedding has reasonable values
    mean_val = np.mean(embedding_array)
    std_val = np.std(embedding_array)

    status = "OK"
    details = []

    if embedding_dim != expected_dim:
        status = "BAD"
        details.append(f"dim={embedding_dim} (expected {expected_dim})")
        issues.append(f"{doc_id}: Wrong dimension")

    if is_zero:
        status = "BAD"
        details.append("all zeros")
        issues.append(f"{doc_id}: All zeros")

    if abs(mean_val) > 1.0:
        status = "WARNING"
        details.append(f"mean={mean_val:.3f}")

    detail_str = ", ".join(details) if details else f"dim={embedding_dim}, mean={mean_val:.3f}, std={std_val:.3f}"

    print(f"{i}. {doc_id}: {status}")
    print(f"   {detail_str}")
    print(f"   doc_type: {metadata.get('doc_type', 'N/A')}")
    print(f"   text_length: {len(doc)} chars")

# Test 3: Check embeddings across the entire collection
print("\n" + "=" * 80)
print("TEST 3: Full Collection Embedding Check")
print("=" * 80)

# Get all IDs and check if we can retrieve them
all_results = collection.get(
    limit=total_docs,
    include=['embeddings']
)

actual_count = len(all_results['ids'])
print(f"\nRetrieved {actual_count} documents")

# Check how many have embeddings
docs_with_embeddings = sum(1 for emb in all_results['embeddings'] if emb is not None)
docs_without_embeddings = actual_count - docs_with_embeddings

print(f"Documents with embeddings: {docs_with_embeddings}")
print(f"Documents without embeddings: {docs_without_embeddings}")

# Check embedding dimensions
if docs_with_embeddings > 0:
    embedding_dims = [len(emb) for emb in all_results['embeddings'] if emb is not None]
    unique_dims = set(embedding_dims)

    print(f"\nEmbedding dimensions found: {unique_dims}")

    for dim in unique_dims:
        count = embedding_dims.count(dim)
        print(f"  {dim}D: {count} documents")

# Test 4: Verify vector search works with random samples
print("\n" + "=" * 80)
print("TEST 4: Vector Search Functionality")
print("=" * 80)

from sentence_transformers import SentenceTransformer

embedding_model_path = str(Config.LEGAL_PATHS["embedding_model"])
embedding_model = SentenceTransformer(embedding_model_path)

test_queries = ["전세금", "임대차", "부동산"]

for query in test_queries:
    embedding = embedding_model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[embedding],
        n_results=3
    )

    result_count = len(results['ids'][0])
    print(f"\nQuery '{query}': {result_count} results")

    if result_count == 0:
        issues.append(f"Vector search failed for '{query}'")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

if len(issues) > 0:
    print(f"\nFOUND {len(issues)} ISSUES:")
    for issue in issues:
        print(f"  - {issue}")
else:
    print("\nOK: All embeddings are properly generated")

print(f"\nFinal Status:")
print(f"  Total documents: {total_docs}/{expected_count}")
print(f"  Documents with embeddings: {docs_with_embeddings}/{actual_count}")
print(f"  Embedding dimension: {expected_dim}D")
print(f"  Vector search: {'OK' if len(issues) == 0 else 'ISSUES FOUND'}")

if total_docs == expected_count and docs_without_embeddings == 0 and len(issues) == 0:
    print("\nCONCLUSION: All 1700 documents are properly embedded!")
else:
    print("\nCONCLUSION: Some issues found, check details above")

print("\n" + "=" * 80)
