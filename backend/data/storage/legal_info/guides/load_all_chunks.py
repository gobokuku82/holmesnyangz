"""
Load ALL 1,700 chunks into ChromaDB
This script will load all documents without user interaction
"""

import logging
from app.service.vectordb_service import VectorDBService
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Main function to load all documents"""
    print("=" * 60)
    print("Loading ALL Legal Documents into ChromaDB")
    print("=" * 60)
    print("\nThis will load approximately 1,700 chunks.")
    print("Expected time: 10-20 minutes on CPU")
    print("-" * 60)

    # Initialize VectorDB Service
    vectordb = VectorDBService()

    # Step 1: Initialize ChromaDB
    print("\n1. Initializing ChromaDB...")
    start_time = time.time()

    if vectordb.initialize():
        print("[SUCCESS] ChromaDB initialized")
        # Check existing documents
        stats = vectordb.get_statistics()
        print(f"   Current documents in DB: {stats['total_chunks']}")
    else:
        print("[ERROR] Failed to initialize ChromaDB")
        return

    # Step 2: Clear existing collection if needed
    if stats['total_chunks'] < 1700:
        print(f"\n2. Need to load {1700 - stats['total_chunks']} more documents...")

        # If collection has partial data, we should reset it
        if stats['total_chunks'] > 0 and stats['total_chunks'] < 1700:
            print("   Clearing partial data to reload completely...")
            # Reset collection
            vectordb.chroma_client.delete_collection("korean_legal_documents")
            vectordb.collection = vectordb.chroma_client.create_collection(
                name="korean_legal_documents",
                metadata={"description": "Korean real estate legal documents"}
            )
            print("   Collection reset")

    # Step 3: Load ALL documents
    print("\n3. Loading documents into ChromaDB...")
    print("   Processing 4 categories:")
    print("   - 1_공통 매매_임대차")
    print("   - 2_임대차_전세_월세")
    print("   - 3_공급_및_관리_매매_분양")
    print("   - 4_기타")
    print("\n   Progress will be shown every 100 documents...")

    doc_count = vectordb.load_documents()

    elapsed_time = time.time() - start_time
    print(f"\n[SUCCESS] Loaded {doc_count} chunks into ChromaDB")
    print(f"Time taken: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")

    # Step 4: Verify and show statistics
    print("\n4. Final Database Statistics:")
    stats = vectordb.get_statistics()
    for key, value in stats.items():
        print(f"   - {key}: {value}")

    # Verify by checking some sample data
    print("\n5. Verifying data...")
    test_results = vectordb.search("부동산", n_results=5)
    if test_results:
        print(f"   [SUCCESS] Sample search returned {len(test_results)} results")
        print(f"   First result similarity: {test_results[0]['similarity_score']:.3f}")
    else:
        print("   [WARNING] Sample search returned no results")

    print("\n" + "=" * 60)
    print("ChromaDB loading completed successfully!")
    print("=" * 60)

    # Summary
    print("\nSUMMARY:")
    print(f"  Total chunks loaded: {doc_count}")
    print(f"  Time taken: {elapsed_time/60:.2f} minutes")
    print(f"  Database location: {vectordb.chroma_path}")
    print("\nYou can now use the search API endpoints!")

if __name__ == "__main__":
    main()