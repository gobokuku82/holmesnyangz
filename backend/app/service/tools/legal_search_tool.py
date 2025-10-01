"""
Legal Search Tool
Searches for legal information related to real estate using ChromaDB
"""

from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
import sys
import re
from pathlib import Path
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# Import Config for paths
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from config import Config

# Import legal_query_helper
backend_dir = Path(__file__).parent.parent.parent.parent
legal_guides_path = backend_dir / "data" / "storage" / "legal_info" / "guides"
if str(legal_guides_path) not in sys.path:
    sys.path.insert(0, str(legal_guides_path))

from legal_query_helper import LegalQueryHelper


class LegalSearchTool(BaseTool):
    """
    Tool for searching legal information using ChromaDB vector search
    - Real estate laws (법률)
    - Presidential decrees (시행령)
    - Ministerial rules (시행규칙)
    - Legal glossary (용어집)
    """

    def __init__(self):
        super().__init__(
            name="legal_search",
            description="법률 정보 검색 - 부동산 관련 법률, 시행령, 시행규칙, 용어 등",
            use_mock_data=False  # Always use real DB
        )

        # Initialize legal search resources directly
        try:
            # Get paths from Config
            chroma_path = str(Config.LEGAL_PATHS["chroma_db"])
            sqlite_path = str(Config.LEGAL_PATHS["sqlite_db"])
            embedding_model_path = str(Config.LEGAL_PATHS["embedding_model"])

            # Initialize SQLite metadata helper
            self.metadata_helper = LegalQueryHelper(sqlite_path)
            self.logger.info(f"SQLite DB loaded: {sqlite_path}")

            # Initialize ChromaDB
            self.chroma_client = chromadb.PersistentClient(
                path=chroma_path,
                settings=Settings(anonymized_telemetry=False)
            )
            self.collection = self.chroma_client.get_collection("korean_legal_documents")
            self.logger.info(f"ChromaDB loaded: {chroma_path} ({self.collection.count()} documents)")

            # Initialize embedding model
            if Path(embedding_model_path).exists():
                self.embedding_model = SentenceTransformer(embedding_model_path)
                self.logger.info(f"Embedding model loaded: {embedding_model_path}")
            else:
                raise FileNotFoundError(f"Embedding model not found: {embedding_model_path}")

        except Exception as e:
            self.logger.error(f"Failed to initialize legal search resources: {e}")
            raise RuntimeError(f"Legal search initialization failed: {e}")

    async def search(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Search legal documents using ChromaDB vector search

        Args:
            query: Search query
            params: Additional parameters including:
                - doc_type: 문서 타입 (법률/시행령/시행규칙/대법원규칙/용어집/기타)
                - category: 카테고리 (1_공통 매매_임대차, 2_임대차_전세_월세, etc.)
                - is_tenant_protection: 임차인 보호 조항 필터
                - is_tax_related: 세금 관련 조항 필터
                - limit: Number of results

        Returns:
            Search results from vector database
        """
        # Extract parameters
        params = params or {}

        # Auto-detect filters from query if not provided
        doc_type = params.get('doc_type') or self._detect_doc_type(query)
        category = params.get('category') or self._detect_category(query)
        is_tenant_protection = params.get('is_tenant_protection')
        is_tax_related = params.get('is_tax_related')
        limit = params.get('limit', 10)

        self.logger.info(f"Searching legal DB - query: {query}, doc_type: {doc_type}, category: {category}")

        # Check if this is a specific article query (e.g., "주택임대차보호법 제7조")
        article_query = self._is_specific_article_query(query)

        if article_query:
            # Fast path: Direct SQL lookup → ChromaDB get by chunk_ids (200x faster)
            self.logger.info(f"Specific article query detected: {article_query}")
            try:
                chunk_ids = self.metadata_helper.get_article_chunk_ids(
                    title=article_query['law_title'],
                    article_number=article_query['article_number']
                )

                if chunk_ids:
                    self.logger.info(f"Found {len(chunk_ids)} chunks via SQL direct lookup")
                    # Direct get from ChromaDB (no vector search needed)
                    results = self.collection.get(
                        ids=chunk_ids,
                        include=['documents', 'metadatas']
                    )

                    # Convert get() results to query() format for consistency
                    results = {
                        'ids': [results['ids']],
                        'documents': [results['documents']],
                        'metadatas': [results['metadatas']],
                        'distances': [[0.0] * len(results['ids'])]  # Perfect match (distance=0)
                    }

                    formatted_data = self._format_chromadb_results(results)

                    return self.format_results(
                        data=formatted_data,
                        total_count=len(formatted_data),
                        query=query
                    )
                else:
                    self.logger.info(f"No chunks found via SQL, falling back to vector search")
            except Exception as e:
                self.logger.warning(f"SQL direct lookup failed: {e}, falling back to vector search")

        # Standard path: Vector search with metadata filtering
        # Build filter using metadata helper
        # Use LLM's category selection to reduce search scope by 70%
        filter_dict = self.metadata_helper.build_chromadb_filter(
            doc_type=doc_type if doc_type else None,
            category=category if category else None,  # Use LLM's category selection
            article_type=self._detect_article_type(query),
            exclude_deleted=True
        )

        self.logger.debug(f"Filter dict: {filter_dict}")

        # Execute vector search
        embedding = self.embedding_model.encode(query).tolist()

        results = self.collection.query(
            query_embeddings=[embedding],
            where=filter_dict if filter_dict else None,
            n_results=limit,
            include=['documents', 'metadatas', 'distances']
        )

        # Format results
        formatted_data = self._format_chromadb_results(results)

        return self.format_results(
            data=formatted_data,
            total_count=len(formatted_data),
            query=query
        )

    async def get_mock_data(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Mock data method (not used - legal search always uses real DB)
        Required by BaseTool abstract class
        """
        raise NotImplementedError("Legal search tool does not support mock data mode")

    def _detect_doc_type(self, query: str) -> Optional[str]:
        """질문에서 문서 타입 감지"""
        if "시행령" in query:
            return "시행령"
        elif "시행규칙" in query:
            return "시행규칙"
        elif "법률" in query and "시행령" not in query and "시행규칙" not in query:
            return "법률"
        elif "대법원" in query:
            return "대법원규칙"
        elif "용어" in query:
            return "용어집"
        return None

    def _detect_category(self, query: str) -> Optional[str]:
        """질문에서 카테고리 감지"""
        if any(keyword in query for keyword in ["임대차", "전세", "월세", "임차인", "임대인"]):
            return "2_임대차_전세_월세"
        elif any(keyword in query for keyword in ["매매", "분양", "공급"]):
            return "1_공통 매매_임대차"
        elif any(keyword in query for keyword in ["관리", "수선", "시설"]):
            return "3_공급_및_관리_매매_분양"
        return None

    def _detect_article_type(self, query: str) -> Optional[str]:
        """질문에서 특수 조항 타입 감지

        NOTE: Disabled to avoid 0 results.
        Most documents have None for these boolean fields.
        Only use if explicitly provided in params.
        """
        # AUTO-DETECTION DISABLED
        # Reason: "전세금" contains "세금" → wrong filter → 0 results
        return None

    def _is_specific_article_query(self, query: str) -> Optional[Dict[str, str]]:
        """
        특정 조문 쿼리인지 감지 (예: "주택임대차보호법 제7조")

        Returns:
            {"law_title": "주택임대차보호법", "article_number": "제7조"} or None
        """
        # Pattern: 법률명 + 제N조[의N]
        patterns = [
            r'(.+?)\s*제(\d+)조(?:의(\d+))?',  # "주택임대차보호법 제7조" or "민법 제618조의2"
            r'(.+?)\s*(\d+)조(?:의(\d+))?',    # "주택임대차보호법 7조"
        ]

        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                law_title = match.group(1).strip()
                article_num = match.group(2)
                sub_num = match.group(3)

                # Build article number
                if sub_num:
                    article_number = f"제{article_num}조의{sub_num}"
                else:
                    article_number = f"제{article_num}조"

                return {
                    'law_title': law_title,
                    'article_number': article_number
                }

        return None

    def _format_chromadb_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """ChromaDB 결과를 표준 포맷으로 변환 + SQL 메타데이터 보강"""
        if not results['ids'][0]:
            return []

        formatted_data = []

        for doc, metadata, distance, doc_id in zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0],
            results['ids'][0]
        ):
            law_title = (
                metadata.get('law_title') or
                metadata.get('decree_title') or
                metadata.get('rule_title', 'N/A')
            )

            formatted_item = {
                "type": "legal_document",
                "doc_id": doc_id,
                "doc_type": metadata.get('doc_type', 'N/A'),
                "law_title": law_title,
                "article_number": metadata.get('article_number', 'N/A'),
                "article_title": metadata.get('article_title', 'N/A'),
                "category": metadata.get('category', 'N/A'),
                "content": doc,
                "relevance_score": round(1 - distance, 3),
                "chapter": metadata.get('chapter'),
                "section": metadata.get('section'),
                "is_tenant_protection": metadata.get('is_tenant_protection') == 'True',
                "is_tax_related": metadata.get('is_tax_related') == 'True',
                "enforcement_date": metadata.get('enforcement_date')
            }

            # Enrich with SQL metadata (total articles, law number, etc.)
            if law_title != 'N/A':
                try:
                    law_info = self.metadata_helper.get_law_by_title(law_title, fuzzy=True)
                    if law_info:
                        formatted_item['total_articles'] = law_info.get('total_articles')
                        formatted_item['law_number'] = law_info.get('law_number')
                        formatted_item['last_article'] = law_info.get('last_article')
                        # Override enforcement_date from SQL if available (more accurate)
                        if law_info.get('enforcement_date'):
                            formatted_item['enforcement_date'] = law_info['enforcement_date']
                except Exception as e:
                    # If SQL query fails, continue without enrichment
                    self.logger.debug(f"SQL enrichment failed for {law_title}: {e}")

            formatted_data.append(formatted_item)

        return formatted_data