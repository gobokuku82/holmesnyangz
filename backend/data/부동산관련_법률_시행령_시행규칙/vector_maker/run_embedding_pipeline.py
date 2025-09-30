"""
      
"""
import sys
import os
from pathlib import Path
import logging

#   Python  
sys.path.insert(0, str(Path(__file__).parent))

from main_pipeline import DocumentPipeline
from config import RAW_DIR

#  
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """  """

    print("="*70)
    print("    ")
    print("="*70)

    #  
    print("\n1.  ...")
    pipeline = DocumentPipeline()

    #  .docx  
    docx_files = list(RAW_DIR.glob("*.docx"))

    if not docx_files:
        print("Error: No .docx files found in raw directory!")
        print(f"Directory: {RAW_DIR}")
        return

    print(f"\n2.  : {len(docx_files)}")
    for i, f in enumerate(docx_files[:5], 1):  #  5 
        print(f"   {i}. {f.name}")
    if len(docx_files) > 5:
        print(f"   ...  {len(docx_files)-5}")

    #    
    print("\n3.    ( )")
    print("-"*50)

    test_file = docx_files[0]
    print(f" : {test_file.name}")

    #    (  )
    stats = pipeline.process_single_document(
        test_file,
        test_mode=True
    )

    if stats.get('status') != 'success':
        print(f" : {stats.get('error', 'Unknown error')}")
        return

    #    
    response = input("\n 10  ? (y/n): ")

    if response.lower() != 'y':
        print(" .")
        return

    #  
    print("\n4.    ")
    print("-"*50)

    results = pipeline.process_batch(
        docx_files,
        test_mode=False  #   
    )

    #  
    print("\n5.  ")
    print("-"*50)

    test_queries = [
        "  ",
        "   ",
        " ",
        " ",
        "  ",
        " ",
        "  "
    ]

    pipeline.run_retrieval_test(test_queries)

    #   
    print("\n6.   ")
    pipeline.save_processing_stats()

    print("\n" + "="*70)
    print("  !")
    print("="*70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n .")
    except Exception as e:
        logger.error(f" : {e}", exc_info=True)