"""
Direct ChromaDB test to debug filtering issues
"""

import sys
from pathlib import Path
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# Paths
backend_dir = Path(__file__).parent.parent.parent.parent
chroma_path = backend_dir / "data" / "storage" / "legal_info" / "chroma_db"
embedding_model_path = backend_dir / "app" / "service" / "models" / "kure_v1"

print("=" * 80)
print("Direct ChromaDB Test")
print("=" * 80)

# Initialize ChromaDB
print(f"\nLoading ChromaDB from: {chroma_path}")
client = chromadb.PersistentClient(
    path=str(chroma_path),
    settings=Settings(anonymized_telemetry=False)
)
collection = client.get_collection("korean_legal_documents")
print(f"Collection loaded: {collection.count()} documents")

# Load embedding model
print(f"\nLoading embedding model from: {embedding_model_path}")
model = SentenceTransformer(str(embedding_model_path))
print("Model loaded successfully")

# Test 1: No filter
print(f"\n{'='*80}")
print("Test 1: Search WITHOUT filter")
print(f"{'='*80}")
query = "임대차 보증금"
embedding = model.encode(query).tolist()
results = collection.query(
    query_embeddings=[embedding],
    n_results=3,
    include=['documents', 'metadatas', 'distances']
)
print(f"Query: {query}")
print(f"Results found: {len(results['ids'][0])}")
if results['ids'][0]:
    for i, (doc, meta, dist) in enumerate(zip(results['documents'][0], results['metadatas'][0], results['distances'][0]), 1):
        print(f"\n{i}. Distance: {dist:.4f}")
        print(f"   Metadata keys: {list(meta.keys())}")
        print(f"   doc_type: {meta.get('doc_type')}")
        print(f"   category: {meta.get('category')}")
        print(f"   is_deleted: {meta.get('is_deleted')}")
        print(f"   Content: {doc[:100]}...")

# Test 2: With category filter
print(f"\n{'='*80}")
print("Test 2: Search WITH category filter")
print(f"{'='*80}")
filter_dict = {"category": "2_임대차_전세_월세"}
print(f"Filter: {filter_dict}")
results = collection.query(
    query_embeddings=[embedding],
    where=filter_dict,
    n_results=3,
    include=['documents', 'metadatas', 'distances']
)
print(f"Results found: {len(results['ids'][0])}")
if results['ids'][0]:
    for i, (doc, meta, dist) in enumerate(zip(results['documents'][0], results['metadatas'][0], results['distances'][0]), 1):
        print(f"\n{i}. Distance: {dist:.4f}")
        print(f"   doc_type: {meta.get('doc_type')}")
        print(f"   category: {meta.get('category')}")
        print(f"   Content: {doc[:100]}...")

# Test 3: Check available categories
print(f"\n{'='*80}")
print("Test 3: Check all unique categories in DB")
print(f"{'='*80}")
all_docs = collection.get(limit=100, include=['metadatas'])
categories = set()
doc_types = set()
for meta in all_docs['metadatas']:
    if meta.get('category'):
        categories.add(meta.get('category'))
    if meta.get('doc_type'):
        doc_types.add(meta.get('doc_type'))

print(f"Unique categories found: {sorted(categories)}")
print(f"Unique doc_types found: {sorted(doc_types)}")

print("\n" + "=" * 80)
print("Test completed!")
print("=" * 80)
