"""
Legal Search Tool
Searches for legal information related to real estate using ChromaDB
"""

from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
import random
import sys
import os
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
        Mock search returning sample legal data

        Args:
            query: Search query
            params: Additional parameters

        Returns:
            Mock legal search results
        """
        query_lower = query.lower() if query else ""

        mock_data = []

        # Contract-related results
        if "계약" in query_lower or "contract" in query_lower:
            mock_data.extend([
                {
                    "type": "legal_document",
                    "title": "부동산 매매계약서 작성 가이드",
                    "category": "계약서",
                    "content": "부동산 매매계약서 작성 시 필수 포함 사항: 1) 매매대금 및 지급방법, 2) 계약금/중도금/잔금 일정, 3) 소유권 이전 시기, 4) 특약사항",
                    "important_points": [
                        "계약금은 통상 매매대금의 10%",
                        "특약사항은 명확하게 기재",
                        "등기부등본 확인 필수"
                    ],
                    "related_laws": ["민법", "부동산등기법"],
                    "last_updated": "2024-01-15"
                },
                {
                    "type": "legal_template",
                    "title": "표준 부동산 임대차계약서",
                    "category": "계약서",
                    "content": "주택임대차보호법에 따른 표준 임대차계약서 양식",
                    "download_url": "mock://templates/lease_contract.pdf",
                    "key_clauses": [
                        "임대차 기간 (최소 2년 보장)",
                        "보증금 및 월세",
                        "수선의무 범위"
                    ]
                }
            ])

        # Tax-related results
        if "세금" in query_lower or "tax" in query_lower:
            mock_data.extend([
                {
                    "type": "tax_info",
                    "title": "부동산 취득세 계산 방법",
                    "category": "세금",
                    "content": "취득세 = (취득가액 × 세율) + 지방교육세 + 농어촌특별세",
                    "tax_rates": {
                        "주택_1호": "1~3%",
                        "주택_2호": "1~3%",
                        "주택_3호_이상": "12%",
                        "비주택": "4%"
                    },
                    "additional_info": "취득 후 60일 이내 신고 및 납부",
                    "related_laws": ["지방세법"]
                },
                {
                    "type": "tax_guide",
                    "title": "양도소득세 비과세 요건",
                    "category": "세금",
                    "content": "1세대 1주택 비과세 요건: 2년 이상 보유 + 2년 이상 거주",
                    "exceptions": [
                        "9억원 초과 주택은 초과분에 대해 과세",
                        "조정대상지역은 거주요건 강화"
                    ]
                }
            ])

        # Procedure-related results
        if "절차" in query_lower or "procedure" in query_lower:
            mock_data.extend([
                {
                    "type": "legal_procedure",
                    "title": "부동산 매매 절차 안내",
                    "category": "절차",
                    "steps": [
                        "1. 매매계약 체결",
                        "2. 계약금 지급 (통상 10%)",
                        "3. 중도금 지급",
                        "4. 잔금 지급 및 소유권 이전",
                        "5. 취득세 납부",
                        "6. 등기 완료"
                    ],
                    "estimated_time": "2-3개월",
                    "required_documents": [
                        "인감증명서",
                        "주민등록등본",
                        "등기부등본"
                    ]
                }
            ])

        # Law-related results
        if "법" in query_lower or "law" in query_lower:
            mock_data.extend([
                {
                    "type": "law_summary",
                    "title": "주택임대차보호법 주요 내용",
                    "category": "법률",
                    "key_provisions": [
                        "임차인 대항력: 주택 인도 + 전입신고",
                        "우선변제권: 확정일자",
                        "임대차 기간: 최소 2년 보장",
                        "보증금 증액: 5% 이내 제한"
                    ],
                    "recent_amendments": "2023년 개정: 계약갱신청구권 행사 횟수 조정"
                }
            ])

        # Default mock data if no specific match
        if not mock_data:
            mock_data = [
                {
                    "type": "general_info",
                    "title": "부동산 거래 관련 일반 법률 정보",
                    "category": "일반",
                    "content": f"'{query}'에 대한 법률 정보입니다.",
                    "tips": [
                        "계약 전 등기부등본 확인 필수",
                        "특약사항은 서면으로 명시",
                        "전문가 상담 권장"
                    ]
                }
            ]

        # Add relevance scores
        for item in mock_data:
            item["relevance_score"] = random.uniform(0.7, 1.0)

        # Sort by relevance
        mock_data.sort(key=lambda x: x["relevance_score"], reverse=True)

        return self.format_results(
            data=mock_data[:5],  # Return top 5 results
            total_count=len(mock_data),
            query=query
        )

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