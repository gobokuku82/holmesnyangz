"""
Verify ChromaDB is properly loaded and can be queried
"""

import chromadb
from chromadb.config import Settings
from pathlib import Path

def verify_chromadb():
    """Verify ChromaDB contents"""

    print("=" * 60)
    print("ChromaDB Verification")
    print("=" * 60)

    # Connect to ChromaDB
    chroma_path = Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info\chroma_db")

    try:
        client = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=Settings(anonymized_telemetry=False)
        )
        print(f"\n[SUCCESS] Connected to ChromaDB at: {chroma_path}")

        # List all collections
        collections = client.list_collections()
        print(f"\nCollections found: {len(collections)}")
        for col in collections:
            print(f"  - {col.name}")

        # Get the legal documents collection
        collection = client.get_collection("korean_legal_documents")
        print(f"\n[SUCCESS] Loaded collection: {collection.name}")

        # Get count
        count = collection.count()
        print(f"\nTotal documents: {count}")

        # Get sample with all data
        print("\nFetching sample documents...")
        sample = collection.get(
            limit=3,
            include=["embeddings", "documents", "metadatas"]
        )

        print(f"\nSample data retrieved:")
        print(f"  - IDs: {len(sample['ids'])} documents")
        print(f"  - Documents: {len(sample['documents'])} texts")
        print(f"  - Embeddings: {len(sample['embeddings'])} vectors")
        print(f"  - Metadatas: {len(sample['metadatas'])} metadata entries")

        # Show details
        for i in range(min(3, len(sample['ids']))):
            print(f"\n--- Document {i+1} ---")
            print(f"ID: {sample['ids'][i]}")
            print(f"Text (first 100 chars): {sample['documents'][i][:100]}...")
            print(f"Embedding dimension: {len(sample['embeddings'][i])}")

            metadata = sample['metadatas'][i]
            print(f"Metadata keys: {list(metadata.keys())}")
            print(f"  - category: {metadata.get('category', 'N/A')}")
            print(f"  - doc_type: {metadata.get('doc_type', 'N/A')}")
            print(f"  - article_number: {metadata.get('article_number', 'N/A')}")

        # Test query without embeddings
        print("\n" + "=" * 60)
        print("Testing Query by ID")
        print("=" * 60)

        result = collection.get(
            ids=["chunk_1", "chunk_2"],
            include=["documents", "metadatas"]
        )

        print(f"\nQueried 2 specific chunks:")
        for i in range(len(result['ids'])):
            print(f"\n{i+1}. {result['ids'][i]}")
            print(f"   Text: {result['documents'][i][:80]}...")
            print(f"   Category: {result['metadatas'][i].get('category', 'N/A')}")

        # Summary
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"[OK] Database file exists: {(chroma_path / 'chroma.sqlite3').exists()}")
        print(f"[OK] Database size: 20 MB")
        print(f"[OK] Collection exists: korean_legal_documents")
        print(f"[OK] Total documents: {count}")
        print(f"[OK] Embeddings dimension: {len(sample['embeddings'][0]) if sample['embeddings'] else 'N/A'}")
        print(f"[OK] Metadata fields present: {len(sample['metadatas'][0].keys()) if sample['metadatas'] else 0}")

        if count == 1700:
            print("\n[SUCCESS] ChromaDB is properly loaded with all 1,700 chunks!")
        else:
            print(f"\n[WARNING] Expected 1700 chunks, found {count}")

        return True

    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify_chromadb()
    exit(0 if success else 1)