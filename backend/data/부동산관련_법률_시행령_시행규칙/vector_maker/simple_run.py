"""
Simple embedding pipeline runner for Korean legal documents
"""
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from main_pipeline import DocumentPipeline
from config import RAW_DIR

def main():
    print("="*60)
    print("Korean Legal Documents Embedding Pipeline")
    print("="*60)

    # Initialize pipeline
    print("\n1. Initializing pipeline...")
    pipeline = DocumentPipeline()

    # Find converted .docx files
    docx_files = list(RAW_DIR.glob("*.docx"))

    if not docx_files:
        print("ERROR: No .docx files found!")
        print(f"Please check directory: {RAW_DIR}")
        return

    print(f"\n2. Found {len(docx_files)} documents:")
    for i, f in enumerate(docx_files, 1):
        print(f"   {i}. {f.name}")

    # Process all documents
    print("\n3. Processing all documents...")
    print("-"*60)

    results = pipeline.process_batch(
        docx_files,
        test_mode=False  # Create actual embeddings
    )

    # Test retrieval
    print("\n4. Testing retrieval...")
    print("-"*60)

    test_queries = [
        "공인중개사 자격 요건",
        "부동산 거래 신고",
        "중개수수료",
        "임대차 보호",
        "등기 신청"
    ]

    pipeline.run_retrieval_test(test_queries)

    # Save statistics
    print("\n5. Saving statistics...")
    pipeline.save_processing_stats()

    print("\n" + "="*60)
    print("Embedding pipeline completed successfully!")
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()