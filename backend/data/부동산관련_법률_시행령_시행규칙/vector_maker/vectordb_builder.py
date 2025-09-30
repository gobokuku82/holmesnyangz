"""
  ChromaDB  DB  
- Kure-v1 (BGE-M3 ) 
- ChromaDB   
"""
import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
from tqdm import tqdm
import json

logger = logging.getLogger(__name__)

class VectorDBBuilder:
    """ DB  """
    
    def __init__(
        self,
        embedding_model: str = "BAAI/bge-m3",
        collection_name: str = "real_estate_law",
        persist_directory: str = "./vectordb/chroma",
        distance_metric: str = "cosine"
    ):
        self.embedding_model_name = embedding_model
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.distance_metric = distance_metric
        
        #   
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # ChromaDB  
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        #    
        self._init_collection()
    
    def _init_collection(self):
        """ """
        try:
            #     ()
            # self.client.delete_collection(self.collection_name)
            
            #    
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": self.distance_metric}
            )
            
            logger.info(f"Collection '{self.collection_name}' initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise
    
    def embed_chunks(self, chunks: List[Dict]) -> np.ndarray:
        """  """
        logger.info(f"Embedding {len(chunks)} chunks...")
        
        #  
        texts = []
        for chunk in chunks:
            if isinstance(chunk, dict):
                text = chunk.get('content', '')
            else:
                text = chunk.content
            texts.append(text)
        
        #  
        embeddings = []
        batch_size = 32
        
        for i in tqdm(range(0, len(texts), batch_size), desc="Embedding chunks"):
            batch_texts = texts[i:i+batch_size]
            batch_embeddings = self.embedding_model.encode(
                batch_texts,
                normalize_embeddings=True,  # BGE-M3  
                show_progress_bar=False
            )
            embeddings.extend(batch_embeddings)
        
        return np.array(embeddings)
    
    def add_to_vectordb(
        self, 
        chunks: List[Dict], 
        embeddings: Optional[np.ndarray] = None,
        doc_metadata: Dict = None
    ):
        """ DB  """
        
        #    
        if embeddings is None:
            embeddings = self.embed_chunks(chunks)
        
        # ChromaDB   
        ids = []
        documents = []
        metadatas = []
        embeddings_list = []
        
        for i, chunk in enumerate(chunks):
            #   
            if isinstance(chunk, dict):
                chunk_id = chunk.get('chunk_id', f"chunk_{i}")
                content = chunk.get('content', '')
                metadata = chunk.get('metadata', {})
                chunk_type = chunk.get('chunk_type', 'unknown')
                doc_id = chunk.get('doc_id', 'unknown')
                chunk_index = chunk.get('chunk_index', i)
            else:
                chunk_id = chunk.chunk_id
                content = chunk.content
                metadata = chunk.metadata
                chunk_type = chunk.chunk_type
                doc_id = chunk.doc_id
                chunk_index = chunk.chunk_index
            
            #  
            chunk_metadata = {
                'doc_id': doc_id,
                'chunk_index': chunk_index,
                'chunk_type': chunk_type,
                'char_count': len(content),
                **metadata  #  
            }
            
            #   
            if doc_metadata:
                chunk_metadata.update({
                    f'doc_{k}': v for k, v in doc_metadata.items()
                })
            
            ids.append(chunk_id)
            documents.append(content)
            metadatas.append(chunk_metadata)
            embeddings_list.append(embeddings[i].tolist())
        
        # ChromaDB 
        try:
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings_list
            )
            
            logger.info(f"Added {len(chunks)} chunks to vector database")
            
        except Exception as e:
            logger.error(f"Failed to add chunks to database: {e}")
            raise
    
    def search(
        self, 
        query: str, 
        n_results: int = 5,
        filter_dict: Dict = None
    ) -> Dict[str, Any]:
        """ """
        
        #  
        query_embedding = self.embedding_model.encode(
            [query],
            normalize_embeddings=True
        )[0]
        
        # ChromaDB 
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results,
            where=filter_dict if filter_dict else None,
            include=['documents', 'metadatas', 'distances']
        )
        
        #  
        formatted_results = {
            'query': query,
            'results': []
        }
        
        for i in range(len(results['ids'][0])):
            formatted_results['results'].append({
                'id': results['ids'][0][i],
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i],
                'similarity': 1 - results['distances'][0][i]  #   -> 
            })
        
        return formatted_results
    
    def test_retrieval(self, test_queries: List[str], n_results: int = 3):
        """ """
        print("\n" + "="*50)
        print("  ")
        print("="*50)
        
        for query in test_queries:
            print(f"\n Query: {query}")
            print("-"*40)
            
            results = self.search(query, n_results=n_results)
            
            for i, result in enumerate(results['results'], 1):
                print(f"\n {i}:")
                print(f"  : {result['similarity']:.3f}")
                print(f"   : {result['metadata'].get('chunk_type', 'N/A')}")
                print(f"   ID: {result['metadata'].get('doc_id', 'N/A')}")
                print(f"  : {result['document'][:150]}...")
        
        print("="*50)
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """ """
        count = self.collection.count()
        
        #  
        sample = self.collection.peek(limit=10)
        
        stats = {
            'total_documents': count,
            'collection_name': self.collection_name,
            'embedding_model': self.embedding_model_name,
            'distance_metric': self.distance_metric,
            'sample_metadata': sample['metadatas'] if sample else []
        }
        
        return stats
    
    def print_db_summary(self):
        """DB  """
        stats = self.get_collection_stats()
        
        print("\n" + "="*50)
        print("  DB ")
        print("="*50)
        print(f" : {stats['collection_name']}")
        print(f"  : {stats['total_documents']}")
        print(f" : {stats['embedding_model']}")
        print(f" : {stats['distance_metric']}")
        
        #   
        if stats['sample_metadata']:
            chunk_types = {}
            for metadata in stats['sample_metadata']:
                chunk_type = metadata.get('chunk_type', 'unknown')
                chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
            
            print("\n   :")
            for chunk_type, count in chunk_types.items():
                print(f"  - {chunk_type}: {count}")
        
        print("="*50)
    
    def export_collection(self, output_path: str):
        """ """
        output_path = Path(output_path)
        
        #   
        all_data = self.collection.get()
        
        # JSON 
        export_data = {
            'collection_name': self.collection_name,
            'embedding_model': self.embedding_model_name,
            'total_documents': len(all_data['ids']),
            'documents': []
        }
        
        for i in range(len(all_data['ids'])):
            export_data['documents'].append({
                'id': all_data['ids'][i],
                'document': all_data['documents'][i],
                'metadata': all_data['metadatas'][i]
            })
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Collection exported to {output_path}")
    
    def reset_collection(self):
        """ """
        try:
            self.client.delete_collection(self.collection_name)
            self._init_collection()
            logger.info(f"Collection '{self.collection_name}' reset")
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            raise


class EmbeddingValidator:
    """  """
    
    def __init__(self, embeddings: np.ndarray, chunks: List[Dict]):
        self.embeddings = embeddings
        self.chunks = chunks
    
    def validate_dimensions(self) -> bool:
        """ """
        expected_dim = self.embeddings.shape[1]
        for i, emb in enumerate(self.embeddings):
            if len(emb) != expected_dim:
                logger.error(f"Dimension mismatch at chunk {i}")
                return False
        return True
    
    def check_similarity_distribution(self) -> Dict[str, float]:
        """  """
        #  
        sample_size = min(100, len(self.embeddings))
        sample_indices = np.random.choice(
            len(self.embeddings), 
            sample_size, 
            replace=False
        )
        
        #   
        similarities = []
        for i in range(sample_size):
            for j in range(i+1, sample_size):
                sim = np.dot(
                    self.embeddings[sample_indices[i]], 
                    self.embeddings[sample_indices[j]]
                )
                similarities.append(sim)
        
        return {
            'mean': np.mean(similarities),
            'std': np.std(similarities),
            'min': np.min(similarities),
            'max': np.max(similarities)
        }
    
    def find_duplicate_embeddings(self, threshold: float = 0.99) -> List[Tuple[int, int]]:
        """  """
        duplicates = []
        
        for i in range(len(self.embeddings)):
            for j in range(i+1, len(self.embeddings)):
                sim = np.dot(self.embeddings[i], self.embeddings[j])
                if sim > threshold:
                    duplicates.append((i, j))
        
        return duplicates
    
    def print_validation_report(self):
        """  """
        print("\n" + "="*50)
        print("   ")
        print("="*50)
        
        #  
        dim_valid = self.validate_dimensions()
        print(f" : {'' if dim_valid else ''}")
        print(f" : {self.embeddings.shape[1]}")
        
        #  
        sim_dist = self.check_similarity_distribution()
        print(f"\n :")
        print(f"  - : {sim_dist['mean']:.3f}")
        print(f"  - : {sim_dist['std']:.3f}")
        print(f"  - : {sim_dist['min']:.3f}")
        print(f"  - : {sim_dist['max']:.3f}")
        
        #  
        duplicates = self.find_duplicate_embeddings()
        print(f"\n : {len(duplicates)}")
        
        if duplicates[:3]:  #  3 
            print("   :")
            for i, j in duplicates[:3]:
                print(f"    -  {i} <->  {j}")
        
        print("="*50)
