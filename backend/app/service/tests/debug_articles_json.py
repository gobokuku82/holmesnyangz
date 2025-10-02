"""
Debug script to directly query ChromaDB for specific failing articles.
Outputs results to JSON file to avoid console encoding issues.
"""

import sys
from pathlib import Path
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import json
from datetime import datetime

# Paths
backend_dir = Path(__file__).parent.parent.parent.parent
chroma_path = backend_dir / "data" / "storage" / "legal_info" / "chroma_db"
embedding_model_path = backend_dir / "app" / "service" / "models" / "kure_v1"

print("Loading ChromaDB and model...")
client = chromadb.PersistentClient(
    path=str(chroma_path),
    settings=Settings(anonymized_telemetry=False)
)
collection = client.get_collection("korean_legal_documents")
model = SentenceTransformer(str(embedding_model_path))

print(f"Collection loaded: {collection.count()} documents")

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

debug_results = {
    "timestamp": datetime.now().isoformat(),
    "total_documents": collection.count(),
    "title_field_analysis": {},
    "test_cases": []
}

# Analyze title field usage
print("Analyzing title fields...")
sample_results = collection.get(limit=100, include=['metadatas'])
field_usage = {
    'title': 0,
    'law_title': 0,
    'decree_title': 0,
    'rule_title': 0,
    'sample_titles': [],
    'sample_law_titles': []
}

for meta in sample_results['metadatas']:
    if 'title' in meta and meta.get('title'):
        field_usage['title'] += 1
        if len(field_usage['sample_titles']) < 20:
            field_usage['sample_titles'].append(meta['title'])

    if 'law_title' in meta and meta.get('law_title'):
        field_usage['law_title'] += 1
        if len(field_usage['sample_law_titles']) < 20:
            field_usage['sample_law_titles'].append(meta['law_title'])

    if 'decree_title' in meta and meta.get('decree_title'):
        field_usage['decree_title'] += 1

    if 'rule_title' in meta and meta.get('rule_title'):
        field_usage['rule_title'] += 1

debug_results['title_field_analysis'] = field_usage

# Test each case
for test_case in test_cases:
    print(f"\nTesting: {test_case['name']}")

    case_result = {
        "name": test_case['name'],
        "law_title": test_case['law_title'],
        "article_number": test_case['article_number'],
        "tests": {}
    }

    # Test 1: Search by article number only
    print("  - Searching by article number...")
    where_clause = {
        '$and': [
            {'article_number': test_case['article_number']},
            {'is_deleted': {'$ne': 'True'}}
        ]
    }

    article_results = collection.get(
        where=where_clause,
        limit=100,
        include=['metadatas']
    )

    found_docs = []
    for i, meta in enumerate(article_results['metadatas']):
        title = meta.get('title', meta.get('law_title', meta.get('decree_title', meta.get('rule_title', 'Unknown'))))
        found_docs.append({
            'id': article_results['ids'][i],
            'title': title,
            'doc_type': meta.get('doc_type', 'N/A'),
            'article_title': meta.get('article_title', 'N/A'),
            'category': meta.get('category', 'N/A')
        })

    case_result['tests']['search_by_article_number'] = {
        'count': len(found_docs),
        'documents': found_docs
    }

    # Test 2: Search by title keyword (scan approach)
    print("  - Searching by title keyword...")
    all_results = collection.get(
        where={'is_deleted': {'$ne': 'True'}},
        limit=500,
        include=['metadatas']
    )

    title_matches = []
    for i, meta in enumerate(all_results['metadatas']):
        title = meta.get('title', meta.get('law_title', meta.get('decree_title', meta.get('rule_title', ''))))
        if test_case['law_title'] in title:
            title_matches.append({
                'id': all_results['ids'][i],
                'title': title,
                'doc_type': meta.get('doc_type', 'N/A'),
                'article_number': meta.get('article_number', 'N/A'),
                'article_title': meta.get('article_title', 'N/A')
            })

    case_result['tests']['search_by_title_keyword'] = {
        'count': len(title_matches),
        'documents': title_matches[:20]  # First 20
    }

    # Test 3: Exact match (title + article)
    print("  - Searching for exact match...")
    exact_matches = []
    partial_matches = []

    for doc in found_docs:
        if doc['title'] == test_case['law_title']:
            exact_matches.append(doc)
        elif test_case['law_title'] in doc['title'] or doc['title'] in test_case['law_title']:
            partial_matches.append(doc)

    case_result['tests']['exact_match'] = {
        'exact_count': len(exact_matches),
        'partial_count': len(partial_matches),
        'exact_matches': exact_matches,
        'partial_matches': partial_matches[:10]
    }

    # Test 4: Vector search
    print("  - Vector search...")
    query = f"{test_case['law_title']} {test_case['article_number']}"
    embedding = model.encode(query).tolist()

    vector_results = collection.query(
        query_embeddings=[embedding],
        where={'is_deleted': {'$ne': 'True'}},
        n_results=20,
        include=['documents', 'metadatas', 'distances']
    )

    vector_matches = []
    for i, meta in enumerate(vector_results['metadatas'][0]):
        title = meta.get('title', meta.get('law_title', meta.get('decree_title', meta.get('rule_title', 'Unknown'))))
        vector_matches.append({
            'rank': i + 1,
            'title': title,
            'doc_type': meta.get('doc_type', 'N/A'),
            'article_number': meta.get('article_number', 'N/A'),
            'article_title': meta.get('article_title', 'N/A'),
            'distance': vector_results['distances'][0][i],
            'relevance': 1 - vector_results['distances'][0][i],
            'matches_expected_article': meta.get('article_number') == test_case['article_number']
        })

    case_result['tests']['vector_search'] = {
        'query': query,
        'count': len(vector_matches),
        'matches_with_expected_article': len([m for m in vector_matches if m['matches_expected_article']]),
        'results': vector_matches
    }

    debug_results['test_cases'].append(case_result)

# Save to JSON
output_file = Path(__file__).parent / f"debug_articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(debug_results, f, ensure_ascii=False, indent=2)

print(f"\nResults saved to: {output_file.name}")
print("\nSummary:")
for case in debug_results['test_cases']:
    print(f"\n{case['name']}:")
    print(f"  Articles with matching number: {case['tests']['search_by_article_number']['count']}")
    print(f"  Documents with law title: {case['tests']['search_by_title_keyword']['count']}")
    print(f"  Exact matches (title + article): {case['tests']['exact_match']['exact_count']}")
    print(f"  Partial matches (title + article): {case['tests']['exact_match']['partial_count']}")
    print(f"  Vector search matches: {case['tests']['vector_search']['matches_with_expected_article']}/{case['tests']['vector_search']['count']}")
