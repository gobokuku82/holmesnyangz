"""
Vector Database Service for Legal Document Search
Uses ChromaDB with BGE-M3 embeddings
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np
from datetime import datetime

class VectorDBService:
    """
    ChromaDB based vector search service for legal documents
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Base paths
        self.base_path = Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info")
        self.chunked_path = self.base_path / "chunked"
        self.chroma_path = self.base_path / "chroma_db"
        self.metadata_path = self.chunked_path / "metadata_index"

        # Model paths
        self.embedding_model_path = Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\app\service\models\kure_v1")
        self.reranker_model_path = Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\app\service\models\bge-reranker-v2-m3-ko")

        # Initialize ChromaDB
        self.chroma_client = None
        self.collection = None

        # Initialize embedding model
        self.embedding_model = None

        # Load configuration
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load search configuration from YAML"""
        config_path = self.metadata_path / "search_config.yaml"
        if config_path.exists():
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}

    def initialize(self):
        """Initialize ChromaDB and embedding model"""
        try:
            # Create ChromaDB directory if not exists
            self.chroma_path.mkdir(parents=True, exist_ok=True)

            # Initialize ChromaDB client
            self.chroma_client = chromadb.PersistentClient(
                path=str(self.chroma_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Create or get collection
            collection_name = "korean_legal_documents"
            try:
                self.collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"description": "Korean real estate legal documents"}
                )
                self.logger.info(f"Created new collection: {collection_name}")
            except:
                self.collection = self.chroma_client.get_collection(name=collection_name)
                self.logger.info(f"Using existing collection: {collection_name}")

            # Initialize embedding model
            self._initialize_embedding_model()

            self.logger.info("VectorDB service initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize VectorDB: {e}")
            return False

    def _initialize_embedding_model(self):
        """Initialize BGE-M3 embedding model"""
        try:
            # Try to use local model first
            if self.embedding_model_path.exists():
                model_name = str(self.embedding_model_path)
            else:
                # Fallback to downloading from HuggingFace
                model_name = "BAAI/bge-m3"

            self.embedding_model = SentenceTransformer(model_name)
            self.logger.info(f"Loaded embedding model: {model_name}")

        except Exception as e:
            self.logger.error(f"Failed to load embedding model: {e}")
            raise

    def load_documents(self) -> int:
        """
        Load all chunked documents into ChromaDB
        Returns: Number of documents loaded
        """
        if not self.collection:
            self.logger.error("Collection not initialized")
            return 0

        # Check if documents already loaded
        existing_count = self.collection.count()
        if existing_count > 0:
            self.logger.info(f"Collection already contains {existing_count} documents")
            return existing_count

        documents = []
        embeddings = []
        ids = []
        metadatas = []

        # Categories to load
        categories = [
            "1_공통 매매_임대차",
            "2_임대차_전세_월세",
            "3_공급_및_관리_매매_분양",
            "4_기타"
        ]

        chunk_id = 0
        for category in categories:
            category_path = self.chunked_path / category
            if not category_path.exists():
                continue

            # Process each JSON file in category
            for json_file in category_path.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        chunks = json.load(f)

                    for chunk in chunks:
                        chunk_id += 1

                        # Extract text and metadata
                        text = chunk.get('text', '')
                        metadata = chunk.get('metadata', {})

                        # Add category information
                        metadata['category'] = category
                        metadata['source_file'] = json_file.name
                        metadata['chunk_index'] = chunk_id

                        # Extract and add doc_type from source_file
                        metadata['doc_type'] = self._extract_doc_type(json_file.name)

                        # Clean metadata for ChromaDB
                        metadata = self._clean_metadata(metadata)

                        # Prepare for batch insert
                        documents.append(text)
                        ids.append(f"chunk_{chunk_id}")
                        metadatas.append(metadata)

                        # Batch embed and insert every 100 documents
                        if len(documents) >= 100:
                            self._batch_insert(documents, ids, metadatas)
                            documents = []
                            ids = []
                            metadatas = []

                except Exception as e:
                    self.logger.error(f"Error processing {json_file}: {e}")
                    continue

        # Insert remaining documents
        if documents:
            self._batch_insert(documents, ids, metadatas)

        final_count = self.collection.count()
        self.logger.info(f"Loaded {final_count} chunks into ChromaDB")
        return final_count

    def _extract_doc_type(self, source_file: str) -> str:
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

    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean metadata for ChromaDB compatibility
        - Skip None values (don't add them to metadata)
        - Convert lists to strings
        - Ensure all values are primitive types

        IMPORTANT: Boolean fields (is_tenant_protection, is_tax_related, etc.)
        should only be added if they are explicitly True or False.
        If a field is missing or None, we skip it entirely.
        """
        cleaned = {}
        for key, value in metadata.items():
            if value is None:
                # SKIP None values - don't add to cleaned metadata
                continue
            elif isinstance(value, list):
                cleaned[key] = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, (bool, int, float)):
                cleaned[key] = value
            elif isinstance(value, datetime):
                cleaned[key] = value.isoformat()
            else:
                cleaned[key] = str(value)
        return cleaned

    def _batch_insert(self, documents: List[str], ids: List[str], metadatas: List[Dict]):
        """Batch insert documents with embeddings"""
        try:
            # Generate embeddings
            embeddings = self.embedding_model.encode(documents, convert_to_numpy=True)

            # Add to collection
            self.collection.add(
                documents=documents,
                embeddings=embeddings.tolist(),
                ids=ids,
                metadatas=metadatas
            )

            self.logger.info(f"Inserted batch of {len(documents)} documents")

        except Exception as e:
            self.logger.error(f"Error in batch insert: {e}")
            raise

    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        n_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search for legal documents using ChromaDB native filtering

        Args:
            query: Search query text
            filters: Metadata filters in ChromaDB format
            n_results: Number of results to return

        Returns:
            List of search results with text, metadata, and scores
        """
        if not self.collection:
            self.logger.error("Collection not initialized")
            return []

        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)

            # Prepare where clause for ChromaDB
            where_clause = self._build_where_clause(filters) if filters else None

            # Execute search
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=n_results,
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'similarity_score': 1 - results['distances'][0][i],  # Convert distance to similarity
                    'distance': results['distances'][0][i]
                })

            return formatted_results

        except Exception as e:
            self.logger.error(f"Search error: {e}")
            return []

    def _build_where_clause(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build ChromaDB where clause from filters

        Example filters:
        {
            "category": "1_공통 매매_임대차",
            "doc_type": ["법률", "시행령"],
            "is_deleted": False,
            "enforcement_date": {"$gte": "2024-01-01"}
        }
        """
        where_clause = {}

        for key, value in filters.items():
            if isinstance(value, list):
                # Convert to $in operator
                where_clause[key] = {"$in": value}
            elif isinstance(value, dict):
                # Already in operator format
                where_clause[key] = value
            elif isinstance(value, bool):
                # Boolean equality
                where_clause[key] = {"$eq": value}
            else:
                # Simple equality
                where_clause[key] = {"$eq": str(value)}

        # Support $and, $or operators
        if len(where_clause) > 1 and not any(k.startswith('$') for k in where_clause):
            # Wrap in $and for multiple conditions
            return {"$and": [{k: v} for k, v in where_clause.items()]}

        return where_clause

    def hybrid_search(
        self,
        query: str,
        metadata_filters: Optional[Dict[str, Any]] = None,
        semantic_threshold: float = 0.7,
        n_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining semantic search with metadata filtering

        Args:
            query: Search query text
            metadata_filters: Structured metadata filters
            semantic_threshold: Minimum similarity score threshold
            n_results: Number of results to return

        Returns:
            Filtered and ranked search results
        """
        # First, get semantically similar results with filters
        results = self.search(query, metadata_filters, n_results * 2)  # Get more for filtering

        # Apply semantic threshold
        filtered_results = [
            r for r in results
            if r['similarity_score'] >= semantic_threshold
        ]

        # Apply query expansion if configured
        if self.config.get('query_expansion', {}).get('enabled'):
            expanded_results = self._apply_query_expansion(query, filtered_results)
            filtered_results = expanded_results

        # Return top N results
        return filtered_results[:n_results]

    def _apply_query_expansion(self, query: str, results: List[Dict]) -> List[Dict]:
        """Apply synonym expansion to improve recall"""
        synonym_dict = self.config.get('query_expansion', {}).get('synonym_dict', {})

        # Check if query contains synonyms
        query_tokens = query.lower().split()
        for token in query_tokens:
            if token in synonym_dict:
                # Re-score results based on synonym matches
                synonyms = synonym_dict[token]
                for result in results:
                    text_lower = result['text'].lower()
                    # Boost score if synonyms found
                    for synonym in synonyms:
                        if synonym in text_lower:
                            result['similarity_score'] *= 1.1  # 10% boost
                            break

        # Re-sort by updated scores
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the vector database"""
        if not self.collection:
            return {"status": "not_initialized"}

        return {
            "status": "initialized",
            "total_chunks": self.collection.count(),
            "collection_name": self.collection.name,
            "chroma_path": str(self.chroma_path),
            "embedding_model": "BAAI/bge-m3"
        }