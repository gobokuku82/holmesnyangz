#!/usr/bin/env python3
"""
Regenerate ChromaDB with fixed metadata handling
This script will:
1. Delete existing ChromaDB collection
2. Reload all chunks with properly preserved boolean metadata
3. Verify the new data quality
"""

import logging
import time
import sys
from pathlib import Path

# Add paths
backend_dir = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(backend_dir / "data" / "storage" / "legal_info" / "guides" / "guides_old"))

from vectordb_service import VectorDBService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main regeneration function"""
    print("=" * 80)
    print("ChromaDB REGENERATION with Fixed Metadata Handling")
    print("=" * 80)
    print()
    print("This will:")
    print("  1. Delete existing ChromaDB collection")
    print("  2. Reload all 1,700 chunks with fixed metadata")
    print("  3. Verify boolean fields are properly preserved")
    print()
    print("Expected time: ~2 hours (embedding 1,700 documents)")
    print("=" * 80)
    print()

    input_text = input("Press ENTER to continue or Ctrl+C to cancel... ")

    # Initialize VectorDB Service
    print("\n[1/4] Initializing VectorDB Service...")
    vectordb = VectorDBService()

    if not vectordb.initialize():
        logger.error("Failed to initialize VectorDB")
        return False

    # Get current stats
    current_count = vectordb.collection.count()
    print(f"      Current documents in ChromaDB: {current_count}")

    # Delete existing collection
    print("\n[2/4] Deleting existing collection...")
    try:
        vectordb.chroma_client.delete_collection("korean_legal_documents")
        print("      Collection deleted successfully")
    except Exception as e:
        logger.warning(f"Could not delete collection: {e}")

    # Recreate collection
    print("\n[3/4] Creating new collection...")
    try:
        vectordb.collection = vectordb.chroma_client.create_collection(
            name="korean_legal_documents",
            metadata={"description": "Korean real estate legal documents with fixed metadata"}
        )
        print("      New collection created")
    except Exception as e:
        logger.error(f"Failed to create collection: {e}")
        return False

    # Load all documents with fixed metadata handling
    print("\n[4/4] Loading all documents with fixed metadata...")
    print("      This will take approximately 2 hours...")
    print("      Progress will be shown every 100 documents")
    print()

    start_time = time.time()
    doc_count = vectordb.load_documents()
    elapsed_time = time.time() - start_time

    print()
    print("=" * 80)
    print("REGENERATION COMPLETE")
    print("=" * 80)
    print(f"  Documents loaded: {doc_count}")
    print(f"  Time taken: {elapsed_time/60:.2f} minutes ({elapsed_time/3600:.2f} hours)")
    print()

    # Verify metadata quality
    print("Verifying metadata quality...")
    print()

    # Test search with filters
    test_queries = [
        ("is_tenant_protection", {"is_tenant_protection": True}),
        ("is_tax_related", {"is_tax_related": True}),
        ("is_delegation", {"is_delegation": True}),
        ("is_deleted False", {"is_deleted": False}),
    ]

    print("Testing filters:")
    for filter_name, filter_dict in test_queries:
        try:
            # Use ChromaDB query with filter
            from sentence_transformers import SentenceTransformer

            # Get first result to test filter
            results = vectordb.collection.get(
                where=filter_dict,
                limit=5
            )
            count = len(results['ids'])
            print(f"  {filter_name}: {count} documents found")
        except Exception as e:
            print(f"  {filter_name}: ERROR - {e}")

    print()
    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("1. Run quick_test.py to verify search works:")
    print("   python backend/app/service/tests/quick_test.py")
    print()
    print("2. Check metadata quality:")
    print("   python backend/app/service/tests/analyze_db_metadata.py")
    print()
    print("=" * 80)

    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nRegeneration cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Regeneration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
