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
            embedding_model_path = str(Config.LEGAL_PATHS["embedding_model"])

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
            self.logger.info(f"Specific article query detected: {article_query}")

            # Try ChromaDB direct metadata filtering first
            try:
                # Method 1: Direct ChromaDB metadata filtering with partial matching
                results = self._search_specific_article_chromadb(
                    law_title=article_query['law_title'],
                    article_number=article_query['article_number']
                )

                if results and results['ids'][0]:
                    self.logger.info(f"Found {len(results['ids'][0])} results via ChromaDB metadata filtering")
                    formatted_data = self._format_chromadb_results(results)

                    return self.format_results(
                        data=formatted_data,
                        total_count=len(formatted_data),
                        query=query
                    )
                else:
                    self.logger.info("No results from ChromaDB metadata filtering, trying enhanced vector search")

            except Exception as e:
                self.logger.warning(f"ChromaDB metadata filtering failed: {e}")

            # Method 2: Enhanced vector search for specific article
            try:
                # Build enhanced query for better vector matching
                enhanced_query = f"{article_query['law_title']} {article_query['article_number']} 내용 조항"
                self.logger.info(f"Using enhanced query for vector search: {enhanced_query}")

                # Use standard vector search with enhanced query
                embedding = self.embedding_model.encode(enhanced_query).tolist()

                # Build filter for the specific law (partial matching)
                filter_dict = self._build_filter_dict(
                    doc_type=doc_type,
                    category=category,
                    law_title_contains=article_query['law_title']
                )

                results = self.collection.query(
                    query_embeddings=[embedding],
                    where=filter_dict if filter_dict else None,
                    n_results=limit * 2,  # Get more results for filtering
                    include=['documents', 'metadatas', 'distances']
                )

                # Post-filter for the specific article
                if results['ids'][0]:
                    filtered_results = self._filter_results_for_article(
                        results,
                        article_query['article_number']
                    )

                    if filtered_results['ids'][0]:
                        self.logger.info(f"Found {len(filtered_results['ids'][0])} results via enhanced vector search")
                        formatted_data = self._format_chromadb_results(filtered_results)

                        return self.format_results(
                            data=formatted_data,
                            total_count=len(formatted_data),
                            query=query
                        )

            except Exception as e:
                self.logger.warning(f"Enhanced vector search failed: {e}")

            # If all specific article methods fail, fall back to standard vector search
            self.logger.info("All specific article methods failed, falling back to standard vector search")

        # Standard path: Vector search with metadata filtering
        filter_dict = self._build_filter_dict(
            doc_type=doc_type,
            category=category,
            is_tenant_protection=is_tenant_protection,
            is_tax_related=is_tax_related
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

    def _search_specific_article_chromadb(self, law_title: str, article_number: str) -> Dict[str, Any]:
        """
        ChromaDB에서 특정 조문 직접 검색 (메타데이터 필터링)

        Args:
            law_title: 법률 제목 (e.g., "주택임대차보호법")
            article_number: 조문 번호 (e.g., "제7조")

        Returns:
            ChromaDB query results
        """
        try:
            # Use get() with where clause for direct metadata filtering
            # Note: Using unified 'title' field instead of separate law_title/decree_title/rule_title
            where_clause = {
                '$and': [
                    {'article_number': article_number},
                    {'is_deleted': {'$ne': 'True'}}
                ]
            }

            # Try exact match first
            results = self.collection.get(
                where=where_clause,
                limit=100,  # Get more to filter by title
                include=['documents', 'metadatas']
            )

            # Filter by law title (partial matching since ChromaDB doesn't support $contains in get())
            if results['ids']:
                filtered_ids = []
                filtered_docs = []
                filtered_metadatas = []

                for i, metadata in enumerate(results['metadatas']):
                    # Check if title contains the law_title (partial matching)
                    title = metadata.get('title', '')
                    if law_title in title:
                        filtered_ids.append(results['ids'][i])
                        filtered_docs.append(results['documents'][i] if 'documents' in results else '')
                        filtered_metadatas.append(metadata)

                if filtered_ids:
                    # Convert to query() format for consistency
                    return {
                        'ids': [filtered_ids],
                        'documents': [filtered_docs],
                        'metadatas': [filtered_metadatas],
                        'distances': [[0.0] * len(filtered_ids)]  # Perfect match
                    }

            # If exact match fails, try with query() and more flexible filtering
            where_clause = {
                '$and': [
                    {'article_number': article_number},
                    {'is_deleted': {'$ne': 'True'}}
                ]
            }

            # Create a query that will match the law title
            query_text = f"{law_title} {article_number}"
            embedding = self.embedding_model.encode(query_text).tolist()

            results = self.collection.query(
                query_embeddings=[embedding],
                where=where_clause,
                n_results=20,
                include=['documents', 'metadatas', 'distances']
            )

            # Additional filtering by title
            if results['ids'][0]:
                filtered_results = {'ids': [[]], 'documents': [[]], 'metadatas': [[]], 'distances': [[]]}

                for i, metadata in enumerate(results['metadatas'][0]):
                    title = metadata.get('title', '')
                    if law_title in title:
                        filtered_results['ids'][0].append(results['ids'][0][i])
                        filtered_results['documents'][0].append(results['documents'][0][i])
                        filtered_results['metadatas'][0].append(metadata)
                        filtered_results['distances'][0].append(results['distances'][0][i])

                if filtered_results['ids'][0]:
                    return filtered_results

            return results

        except Exception as e:
            self.logger.error(f"ChromaDB specific article search failed: {e}")
            return {'ids': [[]], 'documents': [[]], 'metadatas': [[]], 'distances': [[]]}

    def _filter_results_for_article(self, results: Dict[str, Any], article_number: str) -> Dict[str, Any]:
        """
        Filter search results for a specific article number

        Args:
            results: ChromaDB query results
            article_number: Article number to filter for (e.g., "제7조")

        Returns:
            Filtered results
        """
        if not results['ids'][0]:
            return results

        filtered = {'ids': [[]], 'documents': [[]], 'metadatas': [[]], 'distances': [[]]}

        for i, metadata in enumerate(results['metadatas'][0]):
            if metadata.get('article_number') == article_number:
                filtered['ids'][0].append(results['ids'][0][i])
                filtered['documents'][0].append(results['documents'][0][i])
                filtered['metadatas'][0].append(metadata)
                filtered['distances'][0].append(results['distances'][0][i])

        return filtered

    def _build_filter_dict(
        self,
        doc_type: Optional[str] = None,
        category: Optional[str] = None,
        is_tenant_protection: Optional[bool] = None,
        is_tax_related: Optional[bool] = None,
        law_title_contains: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Build ChromaDB filter dictionary

        Args:
            doc_type: Document type filter
            category: Category filter
            is_tenant_protection: Tenant protection filter
            is_tax_related: Tax related filter
            law_title_contains: Partial law title match

        Returns:
            Filter dictionary for ChromaDB where clause
        """
        conditions = []

        # Always exclude deleted documents
        conditions.append({'is_deleted': {'$ne': 'True'}})

        if doc_type:
            conditions.append({'doc_type': doc_type})

        if category:
            conditions.append({'category': category})

        if is_tenant_protection is not None:
            conditions.append({'is_tenant_protection': str(is_tenant_protection)})

        if is_tax_related is not None:
            conditions.append({'is_tax_related': str(is_tax_related)})

        # Note: ChromaDB doesn't support $contains in where clause
        # We'll handle title filtering in post-processing

        if len(conditions) == 1:
            return conditions[0]
        elif len(conditions) > 1:
            return {'$and': conditions}
        else:
            return None

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
        """ChromaDB 결과를 표준 포맷으로 변환"""
        if not results['ids'][0]:
            return []

        formatted_data = []

        for doc, metadata, distance, doc_id in zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0],
            results['ids'][0]
        ):
            # Use unified 'title' field (fallback to legacy fields if needed)
            title = metadata.get('title') or metadata.get('law_title') or metadata.get('decree_title') or metadata.get('rule_title', 'N/A')

            formatted_item = {
                "type": "legal_document",
                "doc_id": doc_id,
                "doc_type": metadata.get('doc_type', 'N/A'),
                "law_title": title,  # Use unified title
                "article_number": metadata.get('article_number', 'N/A'),
                "article_title": metadata.get('article_title', 'N/A'),
                "category": metadata.get('category', 'N/A'),
                "content": doc,
                "relevance_score": round(1 - distance, 3),
                "chapter": metadata.get('chapter'),
                "section": metadata.get('section'),
                "is_tenant_protection": metadata.get('is_tenant_protection') == 'True',
                "is_tax_related": metadata.get('is_tax_related') == 'True',
                "enforcement_date": metadata.get('enforcement_date'),
                "number": metadata.get('number'),  # Law number
                "source_file": metadata.get('source_file')
            }

            formatted_data.append(formatted_item)

        return formatted_data