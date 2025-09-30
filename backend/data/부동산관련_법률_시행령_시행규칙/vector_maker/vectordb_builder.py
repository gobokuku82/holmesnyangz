"""
임베딩 및 ChromaDB 벡터 DB 구축 모듈
- Kure-v1 (BGE-M3 기반) 임베딩
- ChromaDB 저장 및 관리
"""
import os
from typing import List, Dict, Any, Optional
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
    """벡터 DB 구축 클래스"""
    
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
        
        # 임베딩 모델 로드
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # ChromaDB 클라이언트 초기화
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # 컬렉션 생성 또는 로드
        self._init_collection()
    
    def _init_collection(self):
        """컬렉션 초기화"""
        try:
            # 기존 컬렉션 삭제 옵션 (필요시)
            # self.client.delete_collection(self.collection_name)
            
            # 컬렉션 생성 또는 가져오기
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": self.distance_metric}
            )
            
            logger.info(f"Collection '{self.collection_name}' initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise
    
    def embed_chunks(self, chunks: List[Dict]) -> np.ndarray:
        """청크 임베딩 생성"""
        logger.info(f"Embedding {len(chunks)} chunks...")
        
        # 텍스트 추출
        texts = []
        for chunk in chunks:
            if isinstance(chunk, dict):
                text = chunk.get('content', '')
            else:
                text = chunk.content
            texts.append(text)
        
        # 배치 임베딩
        embeddings = []
        batch_size = 32
        
        for i in tqdm(range(0, len(texts), batch_size), desc="Embedding chunks"):
            batch_texts = texts[i:i+batch_size]
            batch_embeddings = self.embedding_model.encode(
                batch_texts,
                normalize_embeddings=True,  # BGE-M3는 정규화 권장
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
        """벡터 DB에 청크 추가"""
        
        # 임베딩이 제공되지 않으면 생성
        if embeddings is None:
            embeddings = self.embed_chunks(chunks)
        
        # ChromaDB에 추가할 데이터 준비
        ids = []
        documents = []
        metadatas = []
        embeddings_list = []
        
        for i, chunk in enumerate(chunks):
            # 청크 데이터 추출
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
            
            # 메타데이터 구성
            chunk_metadata = {
                'doc_id': doc_id,
                'chunk_index': chunk_index,
                'chunk_type': chunk_type,
                'char_count': len(content),
                **metadata  # 추가 메타데이터
            }
            
            # 문서 메타데이터 추가
            if doc_metadata:
                chunk_metadata.update({
                    f'doc_{k}': v for k, v in doc_metadata.items()
                })
            
            ids.append(chunk_id)
            documents.append(content)
            metadatas.append(chunk_metadata)
            embeddings_list.append(embeddings[i].tolist())
        
        # ChromaDB에 추가
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
        """벡터 검색"""
        
        # 쿼리 임베딩
        query_embedding = self.embedding_model.encode(
            [query],
            normalize_embeddings=True
        )[0]
        
        # ChromaDB 검색
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results,
            where=filter_dict if filter_dict else None,
            include=['documents', 'metadatas', 'distances']
        )
        
        # 결과 포맷팅
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
                'similarity': 1 - results['distances'][0][i]  # 코사인 거리 -> 유사도
            })
        
        return formatted_results
    
    def test_retrieval(self, test_queries: List[str], n_results: int = 3):
        """검색 테스트"""
        print("\n" + "="*50)
        print("🔍 검색 테스트")
        print("="*50)
        
        for query in test_queries:
            print(f"\n📌 Query: {query}")
            print("-"*40)
            
            results = self.search(query, n_results=n_results)
            
            for i, result in enumerate(results['results'], 1):
                print(f"\n결과 {i}:")
                print(f"  유사도: {result['similarity']:.3f}")
                print(f"  청크 타입: {result['metadata'].get('chunk_type', 'N/A')}")
                print(f"  문서 ID: {result['metadata'].get('doc_id', 'N/A')}")
                print(f"  내용: {result['document'][:150]}...")
        
        print("="*50)
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계"""
        count = self.collection.count()
        
        # 메타데이터 샘플링
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
        """DB 요약 출력"""
        stats = self.get_collection_stats()
        
        print("\n" + "="*50)
        print("🗄️ 벡터 DB 요약")
        print("="*50)
        print(f"컬렉션 이름: {stats['collection_name']}")
        print(f"총 문서 수: {stats['total_documents']}")
        print(f"임베딩 모델: {stats['embedding_model']}")
        print(f"거리 메트릭: {stats['distance_metric']}")
        
        # 청크 타입 분포
        if stats['sample_metadata']:
            chunk_types = {}
            for metadata in stats['sample_metadata']:
                chunk_type = metadata.get('chunk_type', 'unknown')
                chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
            
            print("\n샘플 청크 타입 분포:")
            for chunk_type, count in chunk_types.items():
                print(f"  - {chunk_type}: {count}개")
        
        print("="*50)
    
    def export_collection(self, output_path: str):
        """컬렉션 내보내기"""
        output_path = Path(output_path)
        
        # 전체 데이터 가져오기
        all_data = self.collection.get()
        
        # JSON으로 저장
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
        """컬렉션 초기화"""
        try:
            self.client.delete_collection(self.collection_name)
            self._init_collection()
            logger.info(f"Collection '{self.collection_name}' reset")
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            raise


class EmbeddingValidator:
    """임베딩 품질 검증"""
    
    def __init__(self, embeddings: np.ndarray, chunks: List[Dict]):
        self.embeddings = embeddings
        self.chunks = chunks
    
    def validate_dimensions(self) -> bool:
        """차원 검증"""
        expected_dim = self.embeddings.shape[1]
        for i, emb in enumerate(self.embeddings):
            if len(emb) != expected_dim:
                logger.error(f"Dimension mismatch at chunk {i}")
                return False
        return True
    
    def check_similarity_distribution(self) -> Dict[str, float]:
        """유사도 분포 확인"""
        # 랜덤 샘플링
        sample_size = min(100, len(self.embeddings))
        sample_indices = np.random.choice(
            len(self.embeddings), 
            sample_size, 
            replace=False
        )
        
        # 코사인 유사도 계산
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
        """중복 임베딩 찾기"""
        duplicates = []
        
        for i in range(len(self.embeddings)):
            for j in range(i+1, len(self.embeddings)):
                sim = np.dot(self.embeddings[i], self.embeddings[j])
                if sim > threshold:
                    duplicates.append((i, j))
        
        return duplicates
    
    def print_validation_report(self):
        """검증 보고서 출력"""
        print("\n" + "="*50)
        print("✅ 임베딩 검증 보고서")
        print("="*50)
        
        # 차원 검증
        dim_valid = self.validate_dimensions()
        print(f"차원 일관성: {'✓' if dim_valid else '✗'}")
        print(f"임베딩 차원: {self.embeddings.shape[1]}")
        
        # 유사도 분포
        sim_dist = self.check_similarity_distribution()
        print(f"\n유사도 분포:")
        print(f"  - 평균: {sim_dist['mean']:.3f}")
        print(f"  - 표준편차: {sim_dist['std']:.3f}")
        print(f"  - 최소: {sim_dist['min']:.3f}")
        print(f"  - 최대: {sim_dist['max']:.3f}")
        
        # 중복 검사
        duplicates = self.find_duplicate_embeddings()
        print(f"\n중복 임베딩: {len(duplicates)}개")
        
        if duplicates[:3]:  # 처음 3개만 표시
            print("  중복 예시:")
            for i, j in duplicates[:3]:
                print(f"    - 청크 {i} <-> 청크 {j}")
        
        print("="*50)
