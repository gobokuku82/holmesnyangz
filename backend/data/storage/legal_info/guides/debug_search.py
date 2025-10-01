"""
Debug script to check ChromaDB contents and search
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from pathlib import Path

def debug_chromadb():
    """Debug ChromaDB contents"""

    # Connect to ChromaDB
    chroma_path = Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info\chroma_db")

    client = chromadb.PersistentClient(
        path=str(chroma_path),
        settings=Settings(anonymized_telemetry=False)
    )

    # Get collection
    collection = client.get_collection("korean_legal_documents")

    print("=" * 60)
    print("ChromaDB Debug Info")
    print("=" * 60)

    # Get collection info
    count = collection.count()
    print(f"\nTotal documents in collection: {count}")

    # Get sample documents
    print("\nGetting sample documents...")
    sample = collection.get(limit=5, include=["documents", "metadatas"])

    print(f"\nSample of {len(sample['ids'])} documents:")
    for i, doc_id in enumerate(sample['ids']):
        print(f"\n{i+1}. ID: {doc_id}")
        print(f"   Text preview: {sample['documents'][i][:100]}...")
        metadata = sample['metadatas'][i]
        print(f"   Metadata keys: {list(metadata.keys())[:5]}...")
        if 'category' in metadata:
            print(f"   Category: {metadata['category']}")
        if 'doc_type' in metadata:
            print(f"   Doc type: {metadata['doc_type']}")

    # Test simple search without filters
    print("\n" + "=" * 60)
    print("Testing Simple Search (no filters)")
    print("=" * 60)

    # Load embedding model
    print("\nLoading embedding model...")
    model_path = Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\kure_v1")
    if model_path.exists():
        model = SentenceTransformer(str(model_path))
    else:
        model = SentenceTransformer("BAAI/bge-m3")

    # Test queries
    queries = ["부동산", "임대차", "계약", "법률"]

    for query in queries:
        print(f"\nQuery: '{query}'")

        # Generate embedding
        query_embedding = model.encode([query])

        # Search without filters
        results = collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=3,
            include=["documents", "metadatas", "distances"]
        )

        if results['ids'][0]:
            print(f"  Found {len(results['ids'][0])} results")
            for j, result_id in enumerate(results['ids'][0]):
                distance = results['distances'][0][j]
                similarity = 1 - distance
                print(f"  {j+1}. Similarity: {similarity:.3f}")
                print(f"      Text: {results['documents'][0][j][:80]}...")
        else:
            print("  No results found")

if __name__ == "__main__":
    debug_chromadb()