"""
List all unique law titles in the ChromaDB database to verify contents
"""

import sys
from pathlib import Path
import chromadb
from chromadb.config import Settings
import json
from datetime import datetime

# Paths
backend_dir = Path(__file__).parent.parent.parent.parent
chroma_path = backend_dir / "data" / "storage" / "legal_info" / "chroma_db"

print("Loading ChromaDB...")
client = chromadb.PersistentClient(
    path=str(chroma_path),
    settings=Settings(anonymized_telemetry=False)
)
collection = client.get_collection("korean_legal_documents")

print(f"Collection: {collection.count()} total documents")
print("\nScanning all documents for unique law titles...")

# Get all documents in batches
all_titles = set()
doc_types = {}
batch_size = 500
offset = 0
total_count = collection.count()

while offset < total_count:
    results = collection.get(
        limit=batch_size,
        offset=offset,
        include=['metadatas']
    )

    for meta in results['metadatas']:
        title = meta.get('title', meta.get('law_title', meta.get('decree_title', meta.get('rule_title', ''))))
        doc_type = meta.get('doc_type', 'N/A')

        if title:
            all_titles.add(title)
            if title not in doc_types:
                doc_types[title] = set()
            doc_types[title].add(doc_type)

    offset += batch_size
    print(f"  Processed {min(offset, total_count)}/{total_count} documents...")

print(f"\n{'='*80}")
print(f"Found {len(all_titles)} unique law titles")
print(f"{'='*80}\n")

# Group by base law name (remove doc type suffixes)
base_laws = {}
for title in all_titles:
    # Remove common suffixes to find base law
    base = title
    for suffix in [' 시행령', ' 시행규칙']:
        base = base.replace(suffix, '')

    if base not in base_laws:
        base_laws[base] = []
    base_laws[base].append(title)

print("Laws in database (grouped by base law):\n")
for i, (base, variants) in enumerate(sorted(base_laws.items()), 1):
    print(f"{i}. {base}")
    for variant in sorted(variants):
        types = ', '.join(sorted(doc_types[variant]))
        print(f"   └─ {variant} ({types})")
    print()

# Check for specific missing laws
print(f"\n{'='*80}")
print("Checking for specific laws:")
print(f"{'='*80}\n")

search_for = [
    "민법",
    "상가건물 임대차보호법",
    "상가건물임대차보호법",
    "상가 임대차보호법"
]

for search_term in search_for:
    found = [title for title in all_titles if search_term in title]
    if found:
        print(f"[FOUND] '{search_term}':")
        for title in found:
            print(f"  - {title}")
    else:
        print(f"[NOT FOUND] '{search_term}' in database")
    print()

# Save to file
output = {
    "timestamp": datetime.now().isoformat(),
    "total_documents": total_count,
    "unique_titles_count": len(all_titles),
    "all_titles": sorted(list(all_titles)),
    "base_laws": {k: sorted(v) for k, v in base_laws.items()}
}

output_file = Path(__file__).parent / f"database_laws_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Full list saved to: {output_file.name}")
