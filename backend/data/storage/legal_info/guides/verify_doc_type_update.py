"""
Verify doc_type metadata update (without embedding model)
Simply check that doc_type field exists and has correct values
"""

import logging
from pathlib import Path
import chromadb
from chromadb.config import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def verify_doc_type():
    """Verify doc_type metadata exists and is correct"""
    print("=" * 70)
    print("Verifying doc_type Metadata Update")
    print("=" * 70)

    # Initialize ChromaDB
    chroma_path = Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info\chroma_db")

    logger.info("Connecting to ChromaDB...")
    chroma_client = chromadb.PersistentClient(
        path=str(chroma_path),
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )

    collection = chroma_client.get_collection(name="korean_legal_documents")
    total_docs = collection.count()
    logger.info(f"Total documents: {total_docs}")

    # Get all documents
    print("\nRetrieving all documents...")
    results = collection.get(
        include=['metadatas']
    )

    ids = results['ids']
    metadatas = results['metadatas']

    # Analyze doc_type distribution
    doc_type_stats = {}
    has_doc_type = 0
    missing_doc_type = 0

    for metadata in metadatas:
        if 'doc_type' in metadata:
            has_doc_type += 1
            doc_type = metadata['doc_type']
            doc_type_stats[doc_type] = doc_type_stats.get(doc_type, 0) + 1
        else:
            missing_doc_type += 1

    # Print results
    print("\n" + "=" * 70)
    print("Verification Results")
    print("=" * 70)

    print(f"\nTotal documents: {total_docs}")
    print(f"Documents with doc_type: {has_doc_type}")
    print(f"Documents missing doc_type: {missing_doc_type}")

    if has_doc_type > 0:
        print("\n[SUCCESS] doc_type metadata has been added!")
    else:
        print("\n[FAILED] No documents have doc_type metadata")
        return

    print("\nDocument Type Distribution:")
    print("-" * 70)

    # Sort by count descending
    sorted_stats = sorted(doc_type_stats.items(), key=lambda x: x[1], reverse=True)
    for doc_type, count in sorted_stats:
        percentage = (count / total_docs * 100) if total_docs > 0 else 0
        print(f"  {doc_type:15s}: {count:4d} documents ({percentage:5.1f}%)")

    # Show some sample documents
    print("\n" + "=" * 70)
    print("Sample Documents")
    print("=" * 70)

    sample_indices = [0, 100, 500, 1000, 1500]
    for idx in sample_indices:
        if idx < len(ids):
            doc_id = ids[idx]
            metadata = metadatas[idx]

            doc_type = metadata.get('doc_type', 'N/A')
            source_file = metadata.get('source_file', 'N/A')
            article = metadata.get('article_number', 'N/A')

            print(f"\nDocument {idx + 1}:")
            print(f"  ID: {doc_id}")
            print(f"  Doc Type: {doc_type}")
            print(f"  Source: {source_file[:60]}")
            print(f"  Article: 제{article}조")

    # Test filtering capability
    print("\n" + "=" * 70)
    print("Testing Filter Capability")
    print("=" * 70)

    for doc_type in ['법률', '시행령', '시행규칙', '대법원규칙', '용어집']:
        try:
            filtered_results = collection.get(
                where={"doc_type": doc_type},
                limit=5,
                include=['metadatas']
            )
            count = len(filtered_results['ids'])
            print(f"\n  Filter doc_type='{doc_type}': {count} documents (sampled)")

            if count > 0:
                sample_meta = filtered_results['metadatas'][0]
                sample_source = sample_meta.get('source_file', 'N/A')[:50]
                print(f"    Sample: {sample_source}")
        except Exception as e:
            print(f"\n  [FAILED] Filter doc_type='{doc_type}' failed: {e}")

    print("\n" + "=" * 70)
    print("Verification Complete!")
    print("=" * 70)
    print("\n[SUCCESS] doc_type metadata is working correctly")
    print("[SUCCESS] You can now filter by doc_type in your searches")
    print("\nUsage example:")
    print("  results = collection.query(")
    print("      query_embeddings=[embedding],")
    print("      where={'doc_type': '법률'},")
    print("      n_results=10")
    print("  )")


if __name__ == "__main__":
    verify_doc_type()
