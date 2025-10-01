#!/usr/bin/env python3
"""
Check difference between None and absent fields
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / "app" / "service"))

import chromadb
from chromadb.config import Settings
from core.config import Config

chroma_path = str(Config.LEGAL_PATHS["chroma_db"])
chroma_client = chromadb.PersistentClient(
    path=chroma_path,
    settings=Settings(anonymized_telemetry=False)
)
collection = chroma_client.get_collection("korean_legal_documents")

results = collection.get(limit=5, include=['metadatas'])

print("Checking 5 documents:\n")

for i, (doc_id, metadata) in enumerate(zip(results['ids'], results['metadatas']), 1):
    print(f"{i}. {doc_id}")
    print(f"   metadata keys: {list(metadata.keys())}")
    print(f"   'is_tenant_protection' in metadata: {'is_tenant_protection' in metadata}")

    value = metadata.get('is_tenant_protection')
    print(f"   metadata.get('is_tenant_protection'): {value} (type: {type(value).__name__})")

    if 'is_tenant_protection' in metadata:
        direct_value = metadata['is_tenant_protection']
        print(f"   metadata['is_tenant_protection']: {direct_value} (type: {type(direct_value).__name__})")

    print()

# Check a document that should have is_tenant_protection=True
print("\nChecking document with is_tenant_protection=True:")
results = collection.get(
    where={"is_tenant_protection": True},
    limit=1,
    include=['metadatas']
)

if results['ids']:
    metadata = results['metadatas'][0]
    print(f"Document: {results['ids'][0]}")
    print(f"Metadata keys: {list(metadata.keys())}")
    print(f"is_tenant_protection value: {metadata.get('is_tenant_protection')}")
    print(f"is_tenant_protection in metadata: {'is_tenant_protection' in metadata}")
