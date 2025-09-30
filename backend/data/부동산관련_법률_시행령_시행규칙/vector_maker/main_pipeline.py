"""
   DB   
"""
import os
import sys
from pathlib import Path
import logging
from typing import List, Dict, Any
import json
from datetime import datetime

#  
from config import *
from document_analyzer import DocumentAnalyzer
from document_preprocessor import DocumentPreprocessor
from document_chunker import DocumentChunker, Chunk
from vectordb_builder import VectorDBBuilder, EmbeddingValidator

#  
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DocumentPipeline:
    """  """
    
    def __init__(self):
        self.analyzer = DocumentAnalyzer()
        self.preprocessor = DocumentPreprocessor()
        self.chunker = DocumentChunker(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            min_chunk_size=MIN_CHUNK_SIZE
        )
        self.vectordb = VectorDBBuilder(
            embedding_model=EMBEDDING_MODEL,
            collection_name=COLLECTION_NAME,
            persist_directory=CHROMA_PERSIST_DIR
        )
        
        self.processing_stats = []
    
    def process_single_document(
        self, 
        file_path: str,
        doc_id: str = None,
        test_mode: bool = False
    ) -> Dict[str, Any]:
        """  """
        
        file_path = Path(file_path)
        if not doc_id:
            doc_id = file_path.stem
        
        logger.info(f"Processing document: {file_path.name}")
        
        stats = {
            'doc_id': doc_id,
            'file_name': file_path.name,
            'start_time': datetime.now().isoformat(),
            'stages': {}
        }
        
        try:
            # 1.   
            print(f"\nProcessing: {file_path.name}")
            print("-" * 40)
            
            structure = self.analyzer.analyze(file_path)
            self.analyzer.print_structure_summary(structure)
            stats['stages']['analysis'] = {
                'doc_type': structure.doc_type,
                'table_count': structure.table_count,
                'status': 'success'
            }
            
            # 2. 
            processed_data = self.preprocessor.preprocess(
                file_path,
                structure_info=structure.__dict__
            )
            self.preprocessor.print_preprocessing_summary(processed_data)
            
            #   
            processed_path = PROCESSED_DIR / f"{doc_id}_processed"
            self.preprocessor.save_processed_data(processed_data, str(processed_path))
            stats['stages']['preprocessing'] = {
                'table_count': len(processed_data['tables']),
                'paragraph_count': len(processed_data['paragraphs']),
                'status': 'success'
            }
            
            # 3. 
            chunks = self.chunker.chunk_document(processed_data, doc_id)
            self.chunker.print_chunking_summary(chunks)
            
            #  
            chunks_path = CHUNKS_DIR / f"{doc_id}_chunks.json"
            self.chunker.save_chunks(chunks, str(chunks_path))
            stats['stages']['chunking'] = {
                'chunk_count': len(chunks),
                'avg_tokens': sum(c.token_count for c in chunks) / len(chunks) if chunks else 0,
                'status': 'success'
            }
            
            #    
            if test_mode:
                print("\nTest mode: Stopping before embedding")
                self._run_chunking_test(chunks)
                stats['test_mode'] = True
                return stats
            
            # 4.  
            print("\nCreating embeddings...")
            embeddings = self.vectordb.embed_chunks(chunks)
            stats['stages']['embedding'] = {
                'embedding_count': len(embeddings),
                'embedding_dim': embeddings.shape[1],
                'status': 'success'
            }
            
            # 5.  
            validator = EmbeddingValidator(embeddings, chunks)
            validator.print_validation_report()
            
            # 6. DB 
            doc_metadata = {
                'file_name': file_path.name,
                'doc_type': structure.doc_type,
                'processed_date': datetime.now().isoformat()
            }
            self.vectordb.add_to_vectordb(chunks, embeddings, doc_metadata)
            self.vectordb.print_db_summary()
            stats['stages']['vectordb'] = {
                'documents_added': len(chunks),
                'status': 'success'
            }
            
            stats['end_time'] = datetime.now().isoformat()
            stats['status'] = 'success'
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to process {file_path.name}: {e}")
            stats['error'] = str(e)
            stats['status'] = 'failed'
            return stats
    
    def process_batch(
        self, 
        file_paths: List[str],
        test_mode: bool = False
    ) -> List[Dict]:
        """  """
        
        results = []
        
        for i, file_path in enumerate(file_paths):
            print(f"\n{'='*50}")
            print(f"Processing {i+1}/{len(file_paths)}")
            print('='*50)
            
            result = self.process_single_document(
                file_path,
                test_mode=test_mode
            )
            results.append(result)
            self.processing_stats.append(result)
        
        self._print_batch_summary(results)
        return results
    
    def _run_chunking_test(self, chunks: List[Chunk]):
        """  """
        print("\n" + "="*50)
        print("Chunking Test")
        print("="*50)
        
        #    
        sample_count = min(3, len(chunks))
        print(f"\n  ({sample_count}):")
        
        for i in range(sample_count):
            chunk = chunks[i]
            print(f"\n---  {i+1} ---")
            print(f"ID: {chunk.chunk_id}")
            print(f": {chunk.chunk_type}")
            print(f" : {chunk.token_count}")
            print(f" : {chunk.char_count}")
            print(f": ={chunk.overlap_with_previous}, ={chunk.overlap_with_next}")
            print(f":\n{chunk.content[:300]}...")
            
            if chunk.metadata:
                print(f": {list(chunk.metadata.keys())}")
    
    def run_retrieval_test(self, test_queries: List[str] = None):
        """  """
        
        if test_queries is None:
            #   
            test_queries = [
                "",
                "  ",
                " ",
                "",
                "   ",
                "",
                "  "
            ]
        
        self.vectordb.test_retrieval(test_queries)
    
    def _print_batch_summary(self, results: List[Dict]):
        """  """
        print("\n" + "="*50)
        print("Batch Processing Summary")
        print("="*50)
        
        success_count = sum(1 for r in results if r.get('status') == 'success')
        failed_count = len(results) - success_count
        
        print(f" : {len(results)}")
        print(f": {success_count}")
        print(f": {failed_count}")
        
        if failed_count > 0:
            print("\n :")
            for r in results:
                if r.get('status') == 'failed':
                    print(f"  - {r['file_name']}: {r.get('error', 'Unknown error')}")
        
        # 
        total_chunks = sum(
            r['stages'].get('chunking', {}).get('chunk_count', 0)
            for r in results
            if 'stages' in r
        )
        
        print(f"\n  : {total_chunks}")
    
    def save_processing_stats(self, output_path: str = None):
        """  """
        if not output_path:
            output_path = BASE_DIR / f"processing_stats_{datetime.now():%Y%m%d_%H%M%S}.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.processing_stats, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Processing stats saved to {output_path}")


def main():
    """  """
    
    #  
    pipeline = DocumentPipeline()
    
    #    
    # file_path = RAW_DIR / "example_document.docx"
    # stats = pipeline.process_single_document(
    #     file_path,
    #     test_mode=True  #   
    # )
    
    #   
    # doc_files = list(RAW_DIR.glob("*.docx"))
    # results = pipeline.process_batch(doc_files[:5], test_mode=False)
    
    #  
    # pipeline.run_retrieval_test()
    
    #  
    # pipeline.save_processing_stats()
    
    print("\nPipeline ready! Use the following methods:")
    print("  - pipeline.process_single_document(file_path, test_mode=True)")
    print("  - pipeline.process_batch(file_paths)")
    print("  - pipeline.run_retrieval_test()")
    
    return pipeline


if __name__ == "__main__":
    pipeline = main()
