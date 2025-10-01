#!/usr/bin/env python3
"""
Debug ChromaDB filter issue
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

# Initialize ChromaDB
chroma_path = str(Config.LEGAL_PATHS["chroma_db"])
chroma_client = chromadb.PersistentClient(
    path=chroma_path,
    settings=Settings(anonymized_telemetry=False)
)
collection = chroma_client.get_collection("korean_legal_documents")

print(f"Total documents: {collection.count()}")

# Test 1: No filter
print("\n=== Test 1: No Filter ===")
embedding_model_path = str(Config.LEGAL_PATHS["embedding_model"])
embedding_model = SentenceTransformer(embedding_model_path)
query = "전세금 반환"
embedding = embedding_model.encode(query).tolist()

results = collection.query(
    query_embeddings=[embedding],
    n_results=3,
    include=['documents', 'metadatas']
)
print(f"Results: {len(results['ids'][0])}")
if results['ids'][0]:
    for i, (doc_id, metadata) in enumerate(zip(results['ids'][0], results['metadatas'][0])):
        print(f"\n{i+1}. {doc_id}")
        print(f"   Doc Type: {metadata.get('doc_type')}")
        print(f"   Law Title: {metadata.get('law_title', 'N/A')}")
        print(f"   Article: {metadata.get('article_number', 'N/A')}")
        print(f"   is_tax_related: {metadata.get('is_tax_related')} (type: {type(metadata.get('is_tax_related'))})")

# Test 2: With is_deleted filter only
print("\n\n=== Test 2: is_deleted=False Only ===")
results = collection.query(
    query_embeddings=[embedding],
    where={"is_deleted": False},
    n_results=3,
    include=['documents', 'metadatas']
)
print(f"Results: {len(results['ids'][0])}")

# Test 3: Check how many docs have is_tax_related=True
print("\n\n=== Test 3: Count is_tax_related=True ===")
try:
    results = collection.query(
        query_embeddings=[embedding],
        where={"$and": [{"is_tax_related": True}, {"is_deleted": False}]},
        n_results=100,
        include=['metadatas']
    )
    print(f"Documents with is_tax_related=True: {len(results['ids'][0])}")
except Exception as e:
    print(f"Error: {e}")

# Test 4: Check metadata values for is_tax_related
print("\n\n=== Test 4: Sample metadata values ===")
results = collection.get(
    limit=10,
    include=['metadatas']
)
print(f"Checking {len(results['ids'])} documents:")
for i, metadata in enumerate(results['metadatas']):
    is_tax = metadata.get('is_tax_related')
    print(f"{i+1}. is_tax_related: {is_tax} (type: {type(is_tax).__name__})")

# Test 5: Actual filter used in code
print("\n\n=== Test 5: Filter Used in Code ===")
filter_dict = {"$and": [{"is_tax_related": True}, {"is_deleted": False}]}
print(f"Filter: {filter_dict}")
results = collection.query(
    query_embeddings=[embedding],
    where=filter_dict,
    n_results=10,
    include=['documents', 'metadatas']
)
print(f"Results: {len(results['ids'][0])}")
