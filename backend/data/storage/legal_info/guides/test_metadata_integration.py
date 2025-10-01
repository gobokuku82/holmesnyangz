"""
Test SQLite metadata + ChromaDB integration
Demonstrates how to use metadata filtering to improve search performance
"""

import logging
from pathlib import Path
from legal_query_helper import LegalQueryHelper
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_metadata_queries():
    """Test common metadata queries"""
    print("=" * 70)
    print("Test 1: Metadata Queries")
    print("=" * 70)

    with LegalQueryHelper() as helper:
        # Test 1: 법률 정보 조회
        print("\n[Q1] 공인중개사법은 몇 조까지인가?")
        total = helper.get_law_total_articles("공인중개사법")
        last = helper.get_law_last_article("공인중개사법")
        print(f"[A1] 총 {total}개 조항, 마지막 조항: {last}")

        # Test 2: 시행일 조회
        print("\n[Q2] 공인중개사법은 언제 시행되었나?")
        date = helper.get_law_enforcement_date("공인중개사법")
        print(f"[A2] 시행일: {date}")

        # Test 3: 문서 타입별 법률 수
        print("\n[Q3] 문서 타입별 법률 수는?")
        for doc_type in ['법률', '시행령', '시행규칙', '대법원규칙', '용어집']:
            laws = helper.get_laws_by_doc_type(doc_type)
            print(f"[A3] {doc_type}: {len(laws)}개")

        # Test 4: 특수 조항 수
        print("\n[Q4] 특수 조항 수는?")
        for article_type in ['tenant_protection', 'tax_related', 'delegation', 'penalty_related']:
            articles = helper.get_special_articles(article_type)
            type_name = {
                'tenant_protection': '임차인 보호',
                'tax_related': '세금 관련',
                'delegation': '위임',
                'penalty_related': '벌칙'
            }[article_type]
            print(f"[A4] {type_name}: {len(articles)}개")

        # Test 5: 법률 검색
        print("\n[Q5] '임대차' 관련 법률은?")
        laws = helper.search_laws("임대차")
        for law in laws[:5]:
            print(f"[A5] - {law['title']} ({law['doc_type']})")

        # Test 6: 특정 법률의 조항 수
        print("\n[Q6] 주택임대차보호법의 조항들은?")
        articles = helper.get_articles_by_law("주택임대차보호법", include_deleted=False)
        print(f"[A6] 총 {len(articles)}개 조항")
        for article in articles[:5]:
            print(f"     - {article['article_number']} {article['article_title']}")


def test_chromadb_filter_performance():
    """Test ChromaDB search with and without filters"""
    print("\n" + "=" * 70)
    print("Test 2: ChromaDB Filter Performance")
    print("=" * 70)

    # Skip if model not available
    model_path = Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\kure_v1")
    if not model_path.exists():
        print("\n[SKIP] Embedding model not found - skipping ChromaDB tests")
        return

    # Initialize ChromaDB
    chroma_path = Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info\chroma_db")
    client = chromadb.PersistentClient(
        path=str(chroma_path),
        settings=Settings(anonymized_telemetry=False)
    )
    collection = client.get_collection("korean_legal_documents")

    # Load embedding model
    print("\n[INFO] Loading embedding model...")
    embedding_model = SentenceTransformer(str(model_path))

    query_text = "임대차 계약 보증금"
    query_embedding = embedding_model.encode(query_text).tolist()

    # Test 1: No filter
    print(f"\n[TEST] Query: '{query_text}'")
    print("\n1. Without filter:")
    start = time.time()
    results_no_filter = collection.query(
        query_embeddings=[query_embedding],
        n_results=10,
        include=['metadatas', 'distances']
    )
    time_no_filter = time.time() - start
    print(f"   Time: {time_no_filter:.3f}s")
    print(f"   Results: {len(results_no_filter['ids'][0])}")

    # Test 2: With doc_type filter
    print("\n2. With doc_type='법률' filter:")
    start = time.time()
    results_with_filter = collection.query(
        query_embeddings=[query_embedding],
        n_results=10,
        where={"doc_type": "법률"},
        include=['metadatas', 'distances']
    )
    time_with_filter = time.time() - start
    print(f"   Time: {time_with_filter:.3f}s")
    print(f"   Results: {len(results_with_filter['ids'][0])}")

    # Test 3: With metadata helper filter
    print("\n3. With metadata helper filter (법률 + 임대차 카테고리):")
    with LegalQueryHelper() as helper:
        filter_dict = helper.build_chromadb_filter(
            doc_type="법률",
            category="2_임대차_전세_월세",
            exclude_deleted=True
        )
        print(f"   Filter: {filter_dict}")

        start = time.time()
        results_helper_filter = collection.query(
            query_embeddings=[query_embedding],
            n_results=10,
            where=filter_dict,
            include=['metadatas', 'distances']
        )
        time_helper_filter = time.time() - start
        print(f"   Time: {time_helper_filter:.3f}s")
        print(f"   Results: {len(results_helper_filter['ids'][0])}")

        # Show top results
        print("\n   Top 3 results:")
        for i, (metadata, distance) in enumerate(zip(
            results_helper_filter['metadatas'][0][:3],
            results_helper_filter['distances'][0][:3]
        ), 1):
            law_title = metadata.get('law_title', 'N/A')
            article = metadata.get('article_number', 'N/A')
            article_title = metadata.get('article_title', 'N/A')[:30]
            print(f"   {i}. {law_title} {article} ({article_title}) - Distance: {distance:.3f}")


def test_use_cases():
    """Test real-world use cases"""
    print("\n" + "=" * 70)
    print("Test 3: Real-World Use Cases")
    print("=" * 70)

    with LegalQueryHelper() as helper:
        # Use Case 1: Get chunk IDs for specific law
        print("\n[Use Case 1] 특정 법률의 ChromaDB chunk ID 가져오기")
        chunk_ids = helper.get_chunk_ids_for_law("공인중개사법", include_deleted=False)
        print(f"  공인중개사법 chunk IDs: {len(chunk_ids)}개")
        print(f"  예시: {chunk_ids[:3]}")

        # Use Case 2: Build filter for specific article type
        print("\n[Use Case 2] 임차인 보호 조항만 검색하는 필터 생성")
        filter_dict = helper.build_chromadb_filter(
            article_type="tenant_protection",
            exclude_deleted=True
        )
        print(f"  Filter: {filter_dict}")

        # Use Case 3: Get all articles of a law
        print("\n[Use Case 3] 주택임대차보호법의 모든 조항 조회")
        articles = helper.get_articles_by_law("주택임대차보호법")
        print(f"  총 {len(articles)}개 조항")
        for article in articles[:3]:
            print(f"  - {article['article_number']}: {article['article_title']}")

        # Use Case 4: Find laws by category
        print("\n[Use Case 4] 카테고리별 법률 검색 (임대차)")
        laws = helper.get_laws_by_category("2_임대차_전세_월세")
        print(f"  임대차 카테고리 법률: {len(laws)}개")
        for law in laws:
            print(f"  - {law['title']} ({law['doc_type']})")


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("SQLite Metadata + ChromaDB Integration Test")
    print("=" * 70)

    try:
        # Test 1: Metadata queries
        test_metadata_queries()

        # Test 2: ChromaDB filter performance
        test_chromadb_filter_performance()

        # Test 3: Use cases
        test_use_cases()

        print("\n" + "=" * 70)
        print("All tests completed successfully!")
        print("=" * 70)

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
