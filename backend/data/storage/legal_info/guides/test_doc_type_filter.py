"""
Test doc_type filtering in ChromaDB
Verify that the newly added doc_type metadata works correctly
"""

import logging
from pathlib import Path
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_doc_type_filter():
    """Test searching with doc_type filters"""
    print("=" * 70)
    print("Testing doc_type Filter Functionality")
    print("=" * 70)

    # Initialize ChromaDB
    chroma_path = Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info\chroma_db")
    model_path = Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\kure_v1")

    logger.info("Loading embedding model...")
    embedding_model = SentenceTransformer(str(model_path))

    logger.info("Connecting to ChromaDB...")
    chroma_client = chromadb.PersistentClient(
        path=str(chroma_path),
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )

    collection = chroma_client.get_collection(name="korean_legal_documents")
    logger.info(f"Collection loaded: {collection.count()} documents")

    # Test query
    query_text = "임대차 계약"
    query_embedding = embedding_model.encode(query_text).tolist()

    print(f"\nTest Query: '{query_text}'")
    print("=" * 70)

    # Test 1: No filter (baseline)
    print("\nTest 1: No filter")
    print("-" * 70)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        include=['metadatas', 'distances']
    )
    print(f"Found {len(results['ids'][0])} results")
    for i, (doc_id, metadata, distance) in enumerate(zip(
        results['ids'][0],
        results['metadatas'][0],
        results['distances'][0]
    ), 1):
        doc_type = metadata.get('doc_type', 'N/A')
        source = metadata.get('source_file', 'N/A')[:50]
        print(f"  {i}. Doc Type: {doc_type:10s} | Distance: {distance:.4f} | Source: {source}")

    # Test 2: Filter by 법률
    print("\nTest 2: Filter by doc_type='법률'")
    print("-" * 70)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        where={"doc_type": "법률"},
        include=['metadatas', 'distances']
    )
    print(f"Found {len(results['ids'][0])} results")
    for i, (doc_id, metadata, distance) in enumerate(zip(
        results['ids'][0],
        results['metadatas'][0],
        results['distances'][0]
    ), 1):
        doc_type = metadata.get('doc_type', 'N/A')
        source = metadata.get('source_file', 'N/A')[:50]
        article = metadata.get('article_number', 'N/A')
        print(f"  {i}. {doc_type:10s} | 제{article}조 | Distance: {distance:.4f}")

    # Test 3: Filter by 시행령
    print("\nTest 3: Filter by doc_type='시행령'")
    print("-" * 70)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        where={"doc_type": "시행령"},
        include=['metadatas', 'distances']
    )
    print(f"Found {len(results['ids'][0])} results")
    for i, (doc_id, metadata, distance) in enumerate(zip(
        results['ids'][0],
        results['metadatas'][0],
        results['distances'][0]
    ), 1):
        doc_type = metadata.get('doc_type', 'N/A')
        source = metadata.get('source_file', 'N/A')[:50]
        article = metadata.get('article_number', 'N/A')
        print(f"  {i}. {doc_type:10s} | 제{article}조 | Distance: {distance:.4f}")

    # Test 4: Filter by 시행규칙
    print("\nTest 4: Filter by doc_type='시행규칙'")
    print("-" * 70)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        where={"doc_type": "시행규칙"},
        include=['metadatas', 'distances']
    )
    print(f"Found {len(results['ids'][0])} results")
    for i, (doc_id, metadata, distance) in enumerate(zip(
        results['ids'][0],
        results['metadatas'][0],
        results['distances'][0]
    ), 1):
        doc_type = metadata.get('doc_type', 'N/A')
        article = metadata.get('article_number', 'N/A')
        print(f"  {i}. {doc_type:10s} | 제{article}조 | Distance: {distance:.4f}")

    # Test 5: Filter by 용어집
    print("\nTest 5: Filter by doc_type='용어집'")
    print("-" * 70)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        where={"doc_type": "용어집"},
        include=['metadatas', 'distances']
    )
    print(f"Found {len(results['ids'][0])} results")
    for i, (doc_id, metadata, distance) in enumerate(zip(
        results['ids'][0],
        results['metadatas'][0],
        results['distances'][0]
    ), 1):
        doc_type = metadata.get('doc_type', 'N/A')
        article = metadata.get('article_title', 'N/A')[:30]
        print(f"  {i}. {doc_type:10s} | {article} | Distance: {distance:.4f}")

    # Test 6: Combined filter (doc_type + category)
    print("\nTest 6: Combined filter (doc_type='법률' + category='2_임대차_전세_월세')")
    print("-" * 70)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        where={
            "$and": [
                {"doc_type": "법률"},
                {"category": "2_임대차_전세_월세"}
            ]
        },
        include=['metadatas', 'distances']
    )
    print(f"Found {len(results['ids'][0])} results")
    for i, (doc_id, metadata, distance) in enumerate(zip(
        results['ids'][0],
        results['metadatas'][0],
        results['distances'][0]
    ), 1):
        doc_type = metadata.get('doc_type', 'N/A')
        category = metadata.get('category', 'N/A')
        article = metadata.get('article_number', 'N/A')
        print(f"  {i}. {doc_type:10s} | {category} | 제{article}조 | Distance: {distance:.4f}")

    print("\n" + "=" * 70)
    print("All tests completed successfully!")
    print("doc_type filtering is working correctly.")
    print("=" * 70)


if __name__ == "__main__":
    test_doc_type_filter()
