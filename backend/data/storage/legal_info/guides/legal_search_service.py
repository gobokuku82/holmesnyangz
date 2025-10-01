"""
Legal Search Service with ChromaDB Integration
Replaces mock data with actual vector search
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .vectordb_service import VectorDBService


class LegalSearchService:
    """
    Enhanced Legal Search Service using ChromaDB
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.vectordb = VectorDBService()
        self.is_initialized = False

    async def initialize(self) -> bool:
        """Initialize the vector database and load documents"""
        try:
            # Initialize ChromaDB
            if not self.vectordb.initialize():
                self.logger.error("Failed to initialize VectorDB")
                return False

            # Load documents if not already loaded
            doc_count = self.vectordb.load_documents()
            self.logger.info(f"VectorDB ready with {doc_count} documents")

            self.is_initialized = True
            return True

        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
            return False

    async def search(
        self,
        query: str,
        doc_type: Optional[List[str]] = None,
        category: Optional[str] = None,
        date_from: Optional[str] = None,
        is_tenant_protection: Optional[bool] = None,
        is_tax_related: Optional[bool] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search legal documents with various filters

        Args:
            query: Search query text
            doc_type: Document types (법률, 시행령, 시행규칙, 용어집)
            category: Category ID (rental_lease, common_transaction, etc.)
            date_from: Minimum enforcement date (YYYY-MM-DD)
            is_tenant_protection: Filter for tenant protection provisions
            is_tax_related: Filter for tax-related provisions
            limit: Maximum number of results

        Returns:
            Search results with relevance scores
        """
        if not self.is_initialized:
            await self.initialize()

        # Build filters
        filters = self._build_filters(
            doc_type=doc_type,
            category=category,
            date_from=date_from,
            is_tenant_protection=is_tenant_protection,
            is_tax_related=is_tax_related
        )

        # Execute hybrid search
        results = self.vectordb.hybrid_search(
            query=query,
            metadata_filters=filters,
            semantic_threshold=0.6,  # Adjust based on testing
            n_results=limit
        )

        # Format results for API response
        return self._format_results(results, query)

    def _build_filters(
        self,
        doc_type: Optional[List[str]] = None,
        category: Optional[str] = None,
        date_from: Optional[str] = None,
        is_tenant_protection: Optional[bool] = None,
        is_tax_related: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Build ChromaDB-compatible filters"""
        filters = {}

        # Always exclude deleted documents
        filters["is_deleted"] = False

        # Document type filter
        if doc_type:
            filters["doc_type"] = doc_type

        # Category filter
        if category:
            # Map category ID to actual folder name
            category_map = {
                "common_transaction": "1_공통 매매_임대차",
                "rental_lease": "2_임대차_전세_월세",
                "supply_management": "3_공급_및_관리_매매_분양",
                "others": "4_기타"
            }
            filters["category"] = category_map.get(category, category)

        # Date filter
        if date_from:
            filters["enforcement_date"] = {"$gte": date_from}

        # Boolean filters
        if is_tenant_protection is not None:
            filters["is_tenant_protection"] = is_tenant_protection

        if is_tax_related is not None:
            filters["is_tax_related"] = is_tax_related

        return filters

    def _format_results(self, results: List[Dict], query: str) -> Dict[str, Any]:
        """Format search results for API response"""
        formatted_results = []

        for result in results:
            metadata = result.get('metadata', {})

            # Parse law references if stored as JSON string
            law_refs = metadata.get('law_references', '[]')
            if isinstance(law_refs, str):
                import json
                try:
                    law_refs = json.loads(law_refs)
                except:
                    law_refs = []

            formatted_result = {
                "id": result['id'],
                "title": self._generate_title(metadata),
                "text": result['text'],
                "relevance_score": result['similarity_score'],
                "metadata": {
                    "doc_type": metadata.get('doc_type', ''),
                    "category": metadata.get('category', ''),
                    "law_title": metadata.get('law_title', ''),
                    "article_number": metadata.get('article_number', ''),
                    "article_title": metadata.get('article_title', ''),
                    "chapter": metadata.get('chapter', ''),
                    "enforcement_date": metadata.get('enforcement_date', ''),
                    "law_references": law_refs,
                    "is_deleted": metadata.get('is_deleted', False)
                }
            }

            # Add special flags if present
            if metadata.get('is_tenant_protection'):
                formatted_result['metadata']['is_tenant_protection'] = True

            if metadata.get('is_tax_related'):
                formatted_result['metadata']['is_tax_related'] = True

            formatted_results.append(formatted_result)

        return {
            "query": query,
            "total_results": len(formatted_results),
            "results": formatted_results,
            "timestamp": datetime.now().isoformat()
        }

    def _generate_title(self, metadata: Dict) -> str:
        """Generate a descriptive title from metadata"""
        parts = []

        if metadata.get('law_title'):
            parts.append(metadata['law_title'])
        elif metadata.get('decree_title'):
            parts.append(metadata['decree_title'])
        elif metadata.get('rule_title'):
            parts.append(metadata['rule_title'])

        if metadata.get('article_number'):
            parts.append(metadata['article_number'])

        if metadata.get('article_title'):
            parts.append(f"({metadata['article_title']})")

        return " ".join(parts) if parts else "법률 조항"

    async def search_by_category(self, category: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search documents by category

        Categories:
        - common_transaction: 공통 매매·임대차
        - rental_lease: 임대차·전세·월세
        - supply_management: 공급 및 관리·매매·분양
        - others: 기타
        """
        # Get category keywords from config
        category_keywords = {
            "common_transaction": "부동산 등기 공인중개사 거래신고 매매 임대차",
            "rental_lease": "임대차 전세 월세 보증금 임차인 임대인",
            "supply_management": "주택 공동주택 아파트 분양 관리 입주자",
            "others": "가격공시 공시지가 분양가 층간소음"
        }

        query = category_keywords.get(category, "부동산 법률")

        return await self.search(
            query=query,
            category=category,
            limit=limit
        )

    async def search_recent_laws(self, days: int = 365, limit: int = 10) -> Dict[str, Any]:
        """Search for recently enacted or amended laws"""
        from datetime import datetime, timedelta

        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        return await self.search(
            query="법률 개정 시행",
            date_from=date_from,
            doc_type=["법률", "시행령"],
            limit=limit
        )

    async def search_tenant_protection(self, limit: int = 15) -> Dict[str, Any]:
        """Search for tenant protection related provisions"""
        return await self.search(
            query="임차인 보호 권리 보증금",
            is_tenant_protection=True,
            category="rental_lease",
            limit=limit
        )

    async def search_tax_provisions(self, limit: int = 15) -> Dict[str, Any]:
        """Search for tax-related provisions"""
        return await self.search(
            query="세금 취득세 양도세 재산세",
            is_tax_related=True,
            limit=limit
        )

    async def get_glossary(self, term: Optional[str] = None) -> Dict[str, Any]:
        """
        Get glossary definitions

        Args:
            term: Specific term to search (optional)

        Returns:
            Glossary entries
        """
        if term:
            query = f"용어 정의 {term}"
            filters = {"doc_type": "용어집"}
        else:
            query = "부동산 용어 정의"
            filters = {"doc_type": "용어집"}

        results = self.vectordb.search(
            query=query,
            filters=filters,
            n_results=50 if not term else 5
        )

        # Format glossary results
        glossary_entries = []
        for result in results:
            metadata = result.get('metadata', {})
            if metadata.get('term_name'):
                glossary_entries.append({
                    "term": metadata.get('term_name'),
                    "definition": result['text'],
                    "category": metadata.get('term_category', '일반'),
                    "relevance": result['similarity_score']
                })

        return {
            "query_term": term,
            "total_terms": len(glossary_entries),
            "entries": glossary_entries
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get search service statistics"""
        return self.vectordb.get_statistics()