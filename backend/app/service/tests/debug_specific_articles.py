"""
Debug script to directly query ChromaDB for specific failing articles:
- 민법 제618조
- 상가건물 임대차보호법 제10조

This script will:
1. Check if these exact documents exist in ChromaDB
2. Examine what title formats are used in the database
3. Test different query approaches to understand why searches fail
"""

import sys
from pathlib import Path
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import json

# Paths
backend_dir = Path(__file__).parent.parent.parent.parent
chroma_path = backend_dir / "data" / "storage" / "legal_info" / "chroma_db"
embedding_model_path = backend_dir / "app" / "service" / "models" / "kure_v1"

print("=" * 80)
print("DEBUG: Specific Article Search Failures")
print("=" * 80)

# Initialize ChromaDB
print(f"\nLoading ChromaDB from: {chroma_path}")
client = chromadb.PersistentClient(
    path=str(chroma_path),
    settings=Settings(anonymized_telemetry=False)
)
collection = client.get_collection("korean_legal_documents")
print(f"Collection loaded: {collection.count()} documents")

# Load embedding model
print(f"\nLoading embedding model from: {embedding_model_path}")
model = SentenceTransformer(str(embedding_model_path))
print("Model loaded successfully")

# Test cases
test_cases = [
    {
        "name": "민법 제618조",
        "law_title": "민법",
        "article_number": "제618조"
    },
    {
        "name": "상가건물 임대차보호법 제10조",
        "law_title": "상가건물 임대차보호법",
        "article_number": "제10조"
    }
]


def search_by_article_number(article_number: str, limit: int = 50):
    """Search for all documents with a specific article number"""
    print(f"\n  Searching for article_number = '{article_number}'...")

    where_clause = {
        '$and': [
            {'article_number': article_number},
            {'is_deleted': {'$ne': 'True'}}
        ]
    }

    try:
        results = collection.get(
            where=where_clause,
            limit=limit,
            include=['metadatas']
        )

        print(f"  Found {len(results['ids'])} documents with article_number='{article_number}'")

        if results['ids']:
            # Group by title
            by_title = {}
            for i, meta in enumerate(results['metadatas']):
                title = meta.get('title', meta.get('law_title', meta.get('decree_title', meta.get('rule_title', 'Unknown'))))
                doc_type = meta.get('doc_type', 'N/A')
                key = f"{title} ({doc_type})"

                if key not in by_title:
                    by_title[key] = []
                by_title[key].append({
                    'id': results['ids'][i],
                    'article_title': meta.get('article_title', 'N/A'),
                    'metadata': meta
                })

            print(f"\n  Documents grouped by title:")
            for title, docs in sorted(by_title.items()):
                print(f"    - {title}: {len(docs)} doc(s)")
                for doc in docs[:2]:  # Show first 2
                    print(f"      * {doc['article_title']}")

        return results

    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def search_by_title_contains(title_keyword: str, limit: int = 100):
    """Search for all documents where title contains a keyword"""
    print(f"\n  Searching for documents with title containing '{title_keyword}'...")

    try:
        # Get all documents (up to limit)
        results = collection.get(
            where={'is_deleted': {'$ne': 'True'}},
            limit=limit,
            include=['metadatas']
        )

        # Filter by title
        matching = []
        for i, meta in enumerate(results['metadatas']):
            title = meta.get('title', meta.get('law_title', meta.get('decree_title', meta.get('rule_title', ''))))
            if title_keyword in title:
                matching.append({
                    'id': results['ids'][i],
                    'title': title,
                    'doc_type': meta.get('doc_type', 'N/A'),
                    'article_number': meta.get('article_number', 'N/A'),
                    'article_title': meta.get('article_title', 'N/A')
                })

        print(f"  Found {len(matching)} documents with '{title_keyword}' in title")

        if matching:
            # Group by article number
            by_article = {}
            for doc in matching:
                article = doc['article_number']
                if article not in by_article:
                    by_article[article] = []
                by_article[article].append(doc)

            print(f"\n  Sample articles (first 10):")
            for article, docs in sorted(by_article.items())[:10]:
                print(f"    {article}: {len(docs)} doc(s)")
                for doc in docs[:1]:  # Show first one
                    print(f"      - {doc['title']} ({doc['doc_type']})")
                    print(f"        {doc['article_title']}")

        return matching

    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def search_exact_match(law_title: str, article_number: str):
    """Search for exact law title + article number match"""
    print(f"\n  Searching for EXACT match: title='{law_title}', article_number='{article_number}'")

    try:
        # Try with get()
        where_clause = {
            '$and': [
                {'article_number': article_number},
                {'is_deleted': {'$ne': 'True'}}
            ]
        }

        results = collection.get(
            where=where_clause,
            limit=200,
            include=['metadatas']
        )

        # Filter by exact title match
        exact_matches = []
        partial_matches = []

        for i, meta in enumerate(results['metadatas']):
            title = meta.get('title', meta.get('law_title', meta.get('decree_title', meta.get('rule_title', ''))))

            if title == law_title:
                exact_matches.append({
                    'id': results['ids'][i],
                    'title': title,
                    'doc_type': meta.get('doc_type', 'N/A'),
                    'article_title': meta.get('article_title', 'N/A'),
                    'metadata': meta
                })
            elif law_title in title or title in law_title:
                partial_matches.append({
                    'id': results['ids'][i],
                    'title': title,
                    'doc_type': meta.get('doc_type', 'N/A'),
                    'article_title': meta.get('article_title', 'N/A'),
                    'metadata': meta
                })

        print(f"  Exact matches: {len(exact_matches)}")
        if exact_matches:
            for doc in exact_matches:
                print(f"    - {doc['title']} ({doc['doc_type']}): {doc['article_title']}")

        print(f"  Partial matches: {len(partial_matches)}")
        if partial_matches:
            for doc in partial_matches[:5]:  # Show first 5
                print(f"    - {doc['title']} ({doc['doc_type']}): {doc['article_title']}")

        return exact_matches, partial_matches

    except Exception as e:
        print(f"  ERROR: {e}")
        return [], []


def test_vector_search(query: str, article_number: str, limit: int = 20):
    """Test vector search with post-filtering"""
    print(f"\n  Vector search for query: '{query}'")

    try:
        embedding = model.encode(query).tolist()

        results = collection.query(
            query_embeddings=[embedding],
            where={'is_deleted': {'$ne': 'True'}},
            n_results=limit,
            include=['documents', 'metadatas', 'distances']
        )

        print(f"  Found {len(results['ids'][0])} results")

        # Check if article_number is in results
        matching_articles = []
        for i, meta in enumerate(results['metadatas'][0]):
            if meta.get('article_number') == article_number:
                title = meta.get('title', meta.get('law_title', meta.get('decree_title', meta.get('rule_title', 'Unknown'))))
                matching_articles.append({
                    'rank': i + 1,
                    'title': title,
                    'doc_type': meta.get('doc_type', 'N/A'),
                    'article_title': meta.get('article_title', 'N/A'),
                    'distance': results['distances'][0][i],
                    'relevance': 1 - results['distances'][0][i]
                })

        print(f"  Results matching article_number '{article_number}': {len(matching_articles)}")
        for doc in matching_articles[:5]:
            print(f"    Rank {doc['rank']}: {doc['title']} ({doc['doc_type']}) - relevance: {doc['relevance']:.3f}")
            print(f"      {doc['article_title']}")

        # Show top 3 overall results
        print(f"\n  Top 3 overall results:")
        for i in range(min(3, len(results['ids'][0]))):
            meta = results['metadatas'][0][i]
            title = meta.get('title', meta.get('law_title', meta.get('decree_title', meta.get('rule_title', 'Unknown'))))
            print(f"    {i+1}. {title} {meta.get('article_number', 'N/A')} ({meta.get('doc_type', 'N/A')})")
            print(f"       Relevance: {1 - results['distances'][0][i]:.3f}")
            print(f"       {meta.get('article_title', 'N/A')}")

        return matching_articles

    except Exception as e:
        print(f"  ERROR: {e}")
        return []


def analyze_title_field():
    """Analyze what fields are used for titles in the database"""
    print(f"\n{'='*80}")
    print("ANALYZING TITLE FIELDS IN DATABASE")
    print(f"{'='*80}")

    try:
        results = collection.get(
            limit=100,
            include=['metadatas']
        )

        field_usage = {
            'title': 0,
            'law_title': 0,
            'decree_title': 0,
            'rule_title': 0,
            'both_title_and_law': 0,
            'title_values': set(),
            'law_title_values': set()
        }

        for meta in results['metadatas']:
            if 'title' in meta and meta['title']:
                field_usage['title'] += 1
                field_usage['title_values'].add(meta['title'][:50])  # First 50 chars

            if 'law_title' in meta and meta['law_title']:
                field_usage['law_title'] += 1
                field_usage['law_title_values'].add(meta['law_title'][:50])

            if 'decree_title' in meta and meta['decree_title']:
                field_usage['decree_title'] += 1

            if 'rule_title' in meta and meta['rule_title']:
                field_usage['rule_title'] += 1

            if 'title' in meta and meta['title'] and 'law_title' in meta and meta['law_title']:
                field_usage['both_title_and_law'] += 1

        print(f"\nField usage (out of {len(results['metadatas'])} docs):")
        print(f"  'title' field: {field_usage['title']} docs")
        print(f"  'law_title' field: {field_usage['law_title']} docs")
        print(f"  'decree_title' field: {field_usage['decree_title']} docs")
        print(f"  'rule_title' field: {field_usage['rule_title']} docs")
        print(f"  Both 'title' and 'law_title': {field_usage['both_title_and_law']} docs")

        print(f"\nSample 'title' values:")
        for val in sorted(field_usage['title_values'])[:10]:
            print(f"  - {val}")

        print(f"\nSample 'law_title' values:")
        for val in sorted(field_usage['law_title_values'])[:10]:
            print(f"  - {val}")

    except Exception as e:
        print(f"ERROR: {e}")


# Run analysis
print("\n" + "=" * 80)
print("STEP 1: Analyze title field usage")
print("=" * 80)
analyze_title_field()

# Run tests for each case
for test_case in test_cases:
    print("\n" + "=" * 80)
    print(f"TESTING: {test_case['name']}")
    print("=" * 80)

    print(f"\n[Method 1] Search by article number only")
    search_by_article_number(test_case['article_number'])

    print(f"\n[Method 2] Search by title keyword")
    search_by_title_contains(test_case['law_title'])

    print(f"\n[Method 3] Search for exact match")
    exact, partial = search_exact_match(test_case['law_title'], test_case['article_number'])

    print(f"\n[Method 4] Vector search with query")
    query = f"{test_case['law_title']} {test_case['article_number']}"
    test_vector_search(query, test_case['article_number'])

print("\n" + "=" * 80)
print("DEBUG COMPLETE")
print("=" * 80)
