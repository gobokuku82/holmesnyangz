"""
Legal Search Tool
Searches for legal information related to real estate using ChromaDB
"""

from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
import sys
from pathlib import Path

# Add legal info guides path for unified_legal_agent import
backend_dir = Path(__file__).parent.parent.parent.parent
legal_guides_path = backend_dir / "data" / "storage" / "legal_info" / "guides"
if str(legal_guides_path) not in sys.path:
    sys.path.insert(0, str(legal_guides_path))

# Import UnifiedLegalAgent for real DB access
try:
    from unified_legal_agent import UnifiedLegalAgent
    UNIFIED_AGENT_AVAILABLE = True
except ImportError:
    UNIFIED_AGENT_AVAILABLE = False


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
        # Use UnifiedLegalAgent for real DB access
        if UNIFIED_AGENT_AVAILABLE:
            try:
                self.search_agent = UnifiedLegalAgent()
                self.logger.info("UnifiedLegalAgent initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize UnifiedLegalAgent: {e}")
                raise RuntimeError(f"Legal search requires UnifiedLegalAgent: {e}")
        else:
            raise ImportError("UnifiedLegalAgent not available. Check import paths.")

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

        # Build filter using metadata helper
        filter_dict = self.search_agent.metadata_helper.build_chromadb_filter(
            doc_type=doc_type,
            category=category,
            article_type=self._detect_article_type(query),
            exclude_deleted=True
        )

        # Execute vector search
        embedding = self.search_agent.embedding_model.encode(query).tolist()

        results = self.search_agent.collection.query(
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
        """질문에서 특수 조항 타입 감지"""
        if "임차인 보호" in query or "임차인보호" in query:
            return "tenant_protection"
        elif "세금" in query or "과세" in query:
            return "tax_related"
        elif "위임" in query:
            return "delegation"
        elif "벌칙" in query or "처벌" in query:
            return "penalty_related"
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

            formatted_data.append(formatted_item)

        return formatted_data