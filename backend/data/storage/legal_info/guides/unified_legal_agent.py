"""
Unified Legal Search Agent
Combines SQLite metadata + ChromaDB vector search for optimal performance

Usage:
    agent = UnifiedLegalAgent()
    answer = agent.answer_question("공인중개사법은 몇 조까지인가요?")
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from legal_query_helper import LegalQueryHelper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UnifiedLegalAgent:
    """
    통합 법률 검색 에이전트
    - SQLite: 메타데이터 빠른 조회 및 필터 생성
    - ChromaDB: 벡터 유사도 검색
    """

    def __init__(
        self,
        chroma_path: Optional[str] = None,
        sqlite_path: Optional[str] = None,
        embedding_model_path: Optional[str] = None
    ):
        """
        Initialize unified agent

        Args:
            chroma_path: ChromaDB 경로 (기본값: 자동 설정)
            sqlite_path: SQLite DB 경로 (기본값: 자동 설정)
            embedding_model_path: 임베딩 모델 경로 (기본값: 자동 설정)
        """
        base_path = Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info")

        # Initialize SQLite helper
        if sqlite_path is None:
            sqlite_path = str(base_path / "sqlite_db" / "legal_metadata.db")
        self.metadata_helper = LegalQueryHelper(sqlite_path)
        logger.info(f"SQLite DB loaded: {sqlite_path}")

        # Initialize ChromaDB
        if chroma_path is None:
            chroma_path = str(base_path / "chroma_db")
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.chroma_client.get_collection("korean_legal_documents")
        logger.info(f"ChromaDB loaded: {chroma_path} ({self.collection.count()} documents)")

        # Initialize embedding model
        if embedding_model_path is None:
            embedding_model_path = str(Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\app\service\models\kure_v1"))

        if Path(embedding_model_path).exists():
            self.embedding_model = SentenceTransformer(embedding_model_path)
            logger.info(f"Embedding model loaded: {embedding_model_path}")
        else:
            logger.warning(f"Embedding model not found at {embedding_model_path}")
            self.embedding_model = None

    def answer_question(self, question: str) -> Dict[str, Any]:
        """
        질문에 답변

        Args:
            question: 사용자 질문

        Returns:
            {
                'answer': 답변 텍스트,
                'source': 'sqlite' | 'chromadb',
                'results': 검색 결과 (있는 경우)
            }
        """
        logger.info(f"Question: {question}")

        # Step 1: 메타데이터 질문인지 확인 (SQLite만 사용)
        metadata_answer = self._try_metadata_query(question)
        if metadata_answer:
            return {
                'answer': metadata_answer,
                'source': 'sqlite',
                'results': None
            }

        # Step 2: 벡터 검색 필요 (SQLite 필터 + ChromaDB)
        if self.embedding_model is None:
            return {
                'answer': "임베딩 모델이 로드되지 않아 벡터 검색을 수행할 수 없습니다.",
                'source': 'error',
                'results': None
            }

        # Build filter from question
        filter_dict = self._build_filter_from_question(question)

        # Vector search
        embedding = self.embedding_model.encode(question).tolist()
        results = self.collection.query(
            query_embeddings=[embedding],
            where=filter_dict if filter_dict else None,
            n_results=5,
            include=['documents', 'metadatas', 'distances']
        )

        # Format answer
        answer = self._format_search_results(results, question)

        return {
            'answer': answer,
            'source': 'chromadb',
            'results': results,
            'filter_used': filter_dict
        }

    def _try_metadata_query(self, question: str) -> Optional[str]:
        """
        메타데이터 질문 처리 (SQLite만 사용)

        Returns:
            답변 문자열 또는 None (메타데이터로 답변 불가능한 경우)
        """
        # Pattern 1: "~법은 몇 조까지?"
        if "몇 조" in question or "몇조" in question:
            law_title = self._extract_law_name(question)
            if law_title:
                total = self.metadata_helper.get_law_total_articles(law_title)
                last = self.metadata_helper.get_law_last_article(law_title)
                if total:
                    return f"{law_title}은(는) 총 {total}개 조항이 있으며, 마지막 조항은 {last}입니다."

        # Pattern 2: "~법은 언제 시행?"
        if ("언제" in question or "시행일" in question) and "시행" in question:
            law_title = self._extract_law_name(question)
            if law_title:
                date = self.metadata_helper.get_law_enforcement_date(law_title)
                if date:
                    return f"{law_title}의 시행일은 {date}입니다."

        # Pattern 3: "~법의 조항 목록"
        if "조항" in question and ("목록" in question or "리스트" in question or "전체" in question):
            law_title = self._extract_law_name(question)
            if law_title:
                articles = self.metadata_helper.get_articles_by_law(law_title, include_deleted=False)
                if articles:
                    article_list = [f"{a['article_number']} ({a['article_title']})" for a in articles[:10]]
                    result = f"{law_title}의 조항 목록:\n" + "\n".join(article_list)
                    if len(articles) > 10:
                        result += f"\n... 외 {len(articles) - 10}개 조항"
                    return result

        return None

    def _extract_law_name(self, question: str) -> Optional[str]:
        """
        질문에서 법률명 추출

        Returns:
            법률명 또는 None
        """
        # 키워드로 검색
        keywords = ["공인중개사법", "주택임대차보호법", "상가건물임대차보호법",
                   "부동산", "임대차", "중개"]

        for keyword in keywords:
            if keyword in question:
                # SQLite에서 검색
                laws = self.metadata_helper.search_laws(keyword)
                if laws:
                    return laws[0]['title']

        return None

    def _build_filter_from_question(self, question: str) -> Optional[Dict[str, Any]]:
        """
        질문에서 ChromaDB 필터 생성

        Returns:
            ChromaDB where 필터 dict 또는 None
        """
        doc_type = None
        category = None
        article_type = None

        # Document type detection
        if "법률" in question and "시행령" not in question and "시행규칙" not in question:
            doc_type = "법률"
        elif "시행령" in question:
            doc_type = "시행령"
        elif "시행규칙" in question:
            doc_type = "시행규칙"

        # Category detection
        if "임대차" in question or "전세" in question or "월세" in question or "임차인" in question:
            category = "2_임대차_전세_월세"
        elif "매매" in question or "분양" in question:
            category = "1_공통 매매_임대차"

        # Article type detection
        if "임차인 보호" in question or "임차인보호" in question:
            article_type = "tenant_protection"
        elif "세금" in question or "과세" in question:
            article_type = "tax_related"
        elif "위임" in question:
            article_type = "delegation"
        elif "벌칙" in question or "처벌" in question:
            article_type = "penalty_related"

        # Build filter
        if doc_type or category or article_type:
            filter_dict = self.metadata_helper.build_chromadb_filter(
                doc_type=doc_type,
                category=category,
                article_type=article_type,
                exclude_deleted=True
            )
            logger.info(f"Filter generated: {filter_dict}")
            return filter_dict

        return None

    def _format_search_results(self, results: Dict[str, Any], question: str) -> str:
        """
        검색 결과 포맷팅

        Args:
            results: ChromaDB 검색 결과
            question: 원본 질문

        Returns:
            포맷팅된 답변
        """
        if not results['ids'][0]:
            return "관련 정보를 찾을 수 없습니다."

        # Build answer from top results
        answer_parts = [f"'{question}'에 대한 검색 결과:\n"]

        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0][:3],
            results['metadatas'][0][:3],
            results['distances'][0][:3]
        ), 1):
            law_title = metadata.get('law_title') or metadata.get('decree_title') or metadata.get('rule_title', 'N/A')
            article_number = metadata.get('article_number', 'N/A')
            article_title = metadata.get('article_title', 'N/A')

            answer_parts.append(
                f"\n{i}. {law_title} {article_number} ({article_title})\n"
                f"   유사도: {1 - distance:.3f}\n"
                f"   내용: {doc[:200]}..."
            )

        return "\n".join(answer_parts)

    def get_statistics(self) -> Dict[str, Any]:
        """
        데이터베이스 통계

        Returns:
            통계 정보 dict
        """
        sqlite_stats = self.metadata_helper.get_statistics()
        chromadb_count = self.collection.count()

        return {
            'sqlite': sqlite_stats,
            'chromadb_total_chunks': chromadb_count,
            'embedding_model_loaded': self.embedding_model is not None
        }

    def close(self):
        """리소스 정리"""
        self.metadata_helper.close()
        logger.info("Agent closed")


# =============================================================================
# Example Usage
# =============================================================================

def main():
    """예제 사용법"""
    print("=" * 70)
    print("Unified Legal Search Agent - Example")
    print("=" * 70)

    # Initialize agent
    agent = UnifiedLegalAgent()

    # Show statistics
    print("\nDatabase Statistics:")
    stats = agent.get_statistics()
    print(f"  SQLite Laws: {stats['sqlite']['total_laws']}")
    print(f"  SQLite Articles: {stats['sqlite']['total_articles']}")
    print(f"  ChromaDB Chunks: {stats['chromadb_total_chunks']}")
    print(f"  Embedding Model: {'Loaded' if stats['embedding_model_loaded'] else 'Not Available'}")

    # Example 1: Metadata query (SQLite only)
    print("\n" + "=" * 70)
    print("Example 1: Metadata Query (SQLite)")
    print("=" * 70)
    question1 = "공인중개사법은 몇 조까지인가요?"
    result1 = agent.answer_question(question1)
    print(f"Q: {question1}")
    print(f"A: {result1['answer']}")
    print(f"Source: {result1['source']}")

    # Example 2: Vector search with filter (SQLite + ChromaDB)
    print("\n" + "=" * 70)
    print("Example 2: Vector Search with Filter (SQLite + ChromaDB)")
    print("=" * 70)
    question2 = "임대차 계약 시 보증금 관련 규정"
    result2 = agent.answer_question(question2)
    print(f"Q: {question2}")
    print(f"A: {result2['answer'][:300]}...")
    print(f"Source: {result2['source']}")
    if result2.get('filter_used'):
        print(f"Filter: {result2['filter_used']}")

    # Close agent
    agent.close()

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
