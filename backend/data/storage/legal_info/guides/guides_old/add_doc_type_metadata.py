"""
Add doc_type metadata to existing ChromaDB documents
Extracts doc_type from source_file field and updates metadata
"""

import logging
from pathlib import Path
import chromadb
from chromadb.config import Settings
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_doc_type(source_file: str) -> str:
    """
    Extract document type from source filename

    Args:
        source_file: Filename containing document type indicator

    Returns:
        Document type: 시행규칙, 시행령, 법률, 대법원규칙, 용어집, or 기타
    """
    if '시행규칙' in source_file:
        return '시행규칙'
    elif '시행령' in source_file:
        return '시행령'
    elif '법률' in source_file or '법(' in source_file:
        return '법률'
    elif '대법원규칙' in source_file:
        return '대법원규칙'
    elif '용어' in source_file:
        return '용어집'
    return '기타'


def main():
    """Main function to add doc_type metadata to all documents"""
    print("=" * 70)
    print("Adding doc_type metadata to ChromaDB documents")
    print("=" * 70)

    # Initialize ChromaDB
    chroma_path = Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info\chroma_db")

    logger.info(f"Connecting to ChromaDB at: {chroma_path}")
    chroma_client = chromadb.PersistentClient(
        path=str(chroma_path),
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )

    # Get collection
    collection_name = "korean_legal_documents"
    try:
        collection = chroma_client.get_collection(name=collection_name)
        total_docs = collection.count()
        logger.info(f"Found collection '{collection_name}' with {total_docs} documents")
    except Exception as e:
        logger.error(f"Failed to get collection: {e}")
        return

    if total_docs == 0:
        logger.warning("No documents found in collection")
        return

    # Get all documents with metadata
    print(f"\nRetrieving all {total_docs} documents...")
    results = collection.get(
        include=['metadatas']
    )

    ids = results['ids']
    metadatas = results['metadatas']

    logger.info(f"Retrieved {len(ids)} documents")

    # Process documents in batches
    batch_size = 100
    updated_count = 0
    doc_type_stats = {}

    print(f"\nUpdating metadata (batch size: {batch_size})...")

    for i in tqdm(range(0, len(ids), batch_size), desc="Processing batches"):
        batch_ids = ids[i:i + batch_size]
        batch_metadatas = metadatas[i:i + batch_size]

        # Update each metadata with doc_type
        updated_metadatas = []
        for metadata in batch_metadatas:
            source_file = metadata.get('source_file', '')
            doc_type = extract_doc_type(source_file)

            # Add doc_type to metadata
            metadata['doc_type'] = doc_type
            updated_metadatas.append(metadata)

            # Track statistics
            doc_type_stats[doc_type] = doc_type_stats.get(doc_type, 0) + 1

        # Update ChromaDB
        try:
            collection.update(
                ids=batch_ids,
                metadatas=updated_metadatas
            )
            updated_count += len(batch_ids)
        except Exception as e:
            logger.error(f"Failed to update batch {i//batch_size + 1}: {e}")
            continue

    # Print statistics
    print("\n" + "=" * 70)
    print("Update completed successfully!")
    print("=" * 70)
    print(f"\nTotal documents updated: {updated_count}")
    print("\nDocument type distribution:")
    print("-" * 50)

    # Sort by count descending
    sorted_stats = sorted(doc_type_stats.items(), key=lambda x: x[1], reverse=True)
    for doc_type, count in sorted_stats:
        percentage = (count / updated_count * 100) if updated_count > 0 else 0
        print(f"  {doc_type:15s}: {count:4d} documents ({percentage:5.1f}%)")

    # Verify update by sampling
    print("\n" + "=" * 70)
    print("Verification")
    print("=" * 70)

    sample_results = collection.get(
        ids=[ids[0], ids[100], ids[500]],
        include=['metadatas']
    )

    print("\nSample documents:")
    for i, (sample_id, metadata) in enumerate(zip(sample_results['ids'], sample_results['metadatas']), 1):
        doc_type = metadata.get('doc_type', 'N/A')
        source_file = metadata.get('source_file', 'N/A')
        print(f"\n  Sample {i}:")
        print(f"    ID: {sample_id}")
        print(f"    Source: {source_file}")
        print(f"    Doc Type: {doc_type}")

    print("\n" + "=" * 70)
    print("Done! You can now filter by doc_type in your searches.")
    print("=" * 70)


if __name__ == "__main__":
    main()
