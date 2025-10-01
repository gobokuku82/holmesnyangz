import json
import os
import glob
from datetime import datetime
from collections import defaultdict, Counter
import yaml
import re

def analyze_chunked_files(base_path):
    """Analyze all chunked JSON files and generate metadata indices"""

    # Initialize data structures
    metadata_index = {
        "version": "1.0",
        "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_documents": 0,
        "total_chunks": 0,
        "categories": {},
        "documents": []
    }

    document_registry = {
        "version": "1.0",
        "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "law_hierarchy": {},
        "document_relationships": [],
        "latest_amendments": []
    }

    chunk_statistics = {
        "version": "1.0",
        "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "by_category": {},
        "by_document_type": {},
        "metadata_field_usage": Counter(),
        "reference_statistics": {
            "law_references": 0,
            "decree_references": 0,
            "form_references": 0,
            "cross_references": 0
        },
        "special_flags_usage": Counter()
    }

    category_taxonomy = {
        "version": "1.0",
        "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "categories": {
            "1_공통 매매_임대차": {
                "id": "common_transaction",
                "name": "공통 매매·임대차",
                "description": "부동산 거래 및 중개에 관한 공통 법률",
                "domains": ["부동산 등기", "공인중개사", "거래신고"],
                "keywords": ["등기", "중개", "거래", "신고", "매매", "임대차"],
                "priority": 1
            },
            "2_임대차_전세_월세": {
                "id": "rental_lease",
                "name": "임대차·전세·월세",
                "description": "주택 임대차 보호 및 민간임대주택 관련 법률",
                "domains": ["임대차 보호", "민간임대", "전세", "월세"],
                "keywords": ["임대차", "전세", "월세", "보증금", "임차인", "임대인"],
                "priority": 2
            },
            "3_공급_및_관리_매매_분양": {
                "id": "supply_management",
                "name": "공급 및 관리·매매·분양",
                "description": "주택 공급, 공동주택 관리 및 건축물 분양 관련 법률",
                "domains": ["주택 공급", "공동주택 관리", "건축물 분양"],
                "keywords": ["주택", "공동주택", "아파트", "분양", "관리", "입주자"],
                "priority": 3
            },
            "4_기타": {
                "id": "others",
                "name": "기타",
                "description": "부동산 가격공시, 분양가격 산정 및 용어 정의",
                "domains": ["가격공시", "분양가격", "층간소음", "용어정의"],
                "keywords": ["가격공시", "공시지가", "분양가", "층간소음", "부동산 용어"],
                "priority": 4
            }
        }
    }

    # Process each category folder
    categories = ["1_공통 매매_임대차", "2_임대차_전세_월세", "3_공급_및_관리_매매_분양", "4_기타"]

    for category in categories:
        category_path = os.path.join(base_path, category)
        if not os.path.exists(category_path):
            continue

        json_files = glob.glob(os.path.join(category_path, "*.json"))
        category_chunks = 0
        category_docs = []

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    chunks = json.load(f)

                if not chunks:
                    continue

                # Extract document metadata from first chunk
                first_chunk = chunks[0]
                metadata = first_chunk.get('metadata', {})

                # Determine document type and title
                doc_type = ""
                doc_title = ""
                doc_number = ""
                enforcement_date = ""

                if 'law_title' in metadata:
                    doc_type = "법률"
                    doc_title = metadata['law_title']
                    doc_number = metadata.get('law_number', '')
                elif 'decree_title' in metadata:
                    doc_type = "시행령"
                    doc_title = metadata['decree_title']
                    doc_number = metadata.get('decree_number', '')
                elif 'rule_title' in metadata:
                    doc_type = "시행규칙"
                    doc_title = metadata['rule_title']
                    doc_number = metadata.get('rule_number', '')
                elif 'glossary_title' in metadata:
                    doc_type = "용어집"
                    doc_title = metadata['glossary_title']
                    doc_number = "N/A"

                enforcement_date = metadata.get('enforcement_date', '')

                # Count hierarchical structure
                chapters = set()
                sections = set()
                articles = set()
                metadata_fields = set()

                # Analyze all chunks
                for chunk in chunks:
                    chunk_metadata = chunk.get('metadata', {})

                    # Collect metadata fields
                    metadata_fields.update(chunk_metadata.keys())
                    chunk_statistics['metadata_field_usage'].update(chunk_metadata.keys())

                    # Track hierarchy
                    if 'chapter' in chunk_metadata:
                        chapters.add(chunk_metadata['chapter'])
                    if 'section' in chunk_metadata:
                        sections.add(chunk_metadata['section'])
                    if 'article_number' in chunk_metadata:
                        articles.add(chunk_metadata['article_number'])

                    # Track references
                    if 'law_references' in chunk_metadata:
                        chunk_statistics['reference_statistics']['law_references'] += len(chunk_metadata['law_references'])
                    if 'decree_references' in chunk_metadata:
                        chunk_statistics['reference_statistics']['decree_references'] += len(chunk_metadata['decree_references'])
                    if 'form_references' in chunk_metadata:
                        chunk_statistics['reference_statistics']['form_references'] += len(chunk_metadata['form_references'])

                    # Track special flags
                    special_flags = ['is_tenant_protection', 'is_delegation', 'is_court_rule',
                                   'is_tax_related', 'is_financial', 'is_price_disclosure_related',
                                   'is_mediation_related', 'is_penalty_related']
                    for flag in special_flags:
                        if chunk_metadata.get(flag):
                            chunk_statistics['special_flags_usage'][flag] += 1

                # Create document entry
                doc_entry = {
                    "file_name": os.path.basename(json_file),
                    "doc_type": doc_type,
                    "doc_id": f"{doc_type}_{doc_number.replace('제', '').replace('호', '')}",
                    "title": doc_title,
                    "doc_number": doc_number,
                    "chunks": len(chunks),
                    "category": category,
                    "category_id": category_taxonomy['categories'][category]['id'],
                    "enforcement_date": enforcement_date,
                    "hierarchy": {
                        "chapters": len(chapters),
                        "sections": len(sections),
                        "articles": len(articles)
                    },
                    "metadata_fields": sorted(list(metadata_fields)),
                    "file_path": os.path.relpath(json_file, base_path)
                }

                metadata_index['documents'].append(doc_entry)
                category_docs.append(doc_entry)
                category_chunks += len(chunks)

                # Update statistics by document type
                if doc_type not in chunk_statistics['by_document_type']:
                    chunk_statistics['by_document_type'][doc_type] = {
                        "documents": 0,
                        "chunks": 0,
                        "avg_chunks_per_doc": 0
                    }
                chunk_statistics['by_document_type'][doc_type]['documents'] += 1
                chunk_statistics['by_document_type'][doc_type]['chunks'] += len(chunks)

                # Build document relationships
                if doc_type == "법률":
                    base_name = doc_title.replace(" ", "").replace("에관한", "")
                    document_registry['law_hierarchy'][base_name] = {
                        "law": doc_title,
                        "law_number": doc_number,
                        "enforcement_date": enforcement_date,
                        "related_decree": None,
                        "related_rule": None
                    }

            except Exception as e:
                print(f"Error processing {json_file}: {e}")
                continue

        # Update category statistics
        metadata_index['categories'][category] = {
            "name": category_taxonomy['categories'][category]['name'],
            "description": category_taxonomy['categories'][category]['description'],
            "documents": len(category_docs),
            "chunks": category_chunks,
            "avg_chunks_per_doc": round(category_chunks / len(category_docs), 1) if category_docs else 0
        }

        chunk_statistics['by_category'][category] = {
            "documents": len(category_docs),
            "chunks": category_chunks,
            "document_types": Counter([doc['doc_type'] for doc in category_docs])
        }

    # Calculate totals
    metadata_index['total_documents'] = len(metadata_index['documents'])
    metadata_index['total_chunks'] = sum(doc['chunks'] for doc in metadata_index['documents'])

    # Calculate averages for document types
    for doc_type in chunk_statistics['by_document_type']:
        stats = chunk_statistics['by_document_type'][doc_type]
        if stats['documents'] > 0:
            stats['avg_chunks_per_doc'] = round(stats['chunks'] / stats['documents'], 1)

    # Find related documents
    for doc in metadata_index['documents']:
        title = doc['title']
        # Remove variations to find base law name
        base_name = title.replace("시행령", "").replace("시행규칙", "").replace(" ", "").strip()

        related = []
        for other_doc in metadata_index['documents']:
            other_base = other_doc['title'].replace("시행령", "").replace("시행규칙", "").replace(" ", "").strip()
            if base_name == other_base and doc['doc_id'] != other_doc['doc_id']:
                related.append({
                    "title": other_doc['title'],
                    "doc_type": other_doc['doc_type'],
                    "doc_id": other_doc['doc_id']
                })

        if related:
            document_registry['document_relationships'].append({
                "base_document": doc['title'],
                "doc_type": doc['doc_type'],
                "related_documents": related
            })

    # Convert Counter objects to dict for JSON serialization
    chunk_statistics['metadata_field_usage'] = dict(chunk_statistics['metadata_field_usage'])
    chunk_statistics['special_flags_usage'] = dict(chunk_statistics['special_flags_usage'])

    for category in chunk_statistics['by_category']:
        if isinstance(chunk_statistics['by_category'][category]['document_types'], Counter):
            chunk_statistics['by_category'][category]['document_types'] = dict(
                chunk_statistics['by_category'][category]['document_types']
            )

    return metadata_index, document_registry, chunk_statistics, category_taxonomy

def create_search_config():
    """Create search configuration for vector DB"""

    search_config = {
        'version': '1.0',
        'created_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'vector_db': {
            'name': 'ChromaDB',
            'collection_name': 'korean_real_estate_laws',
            'embedding_model': 'multilingual-e5-large',
            'distance_metric': 'cosine'
        },
        'indexing': {
            'primary_fields': {
                'text': {
                    'description': 'Main content of the chunk',
                    'type': 'text',
                    'vectorize': True,
                    'weight': 1.0
                },
                'article_title': {
                    'description': 'Title of the article',
                    'type': 'text',
                    'vectorize': True,
                    'weight': 0.8
                }
            },
            'metadata_fields': {
                'doc_type': {
                    'description': 'Document type (법률/시행령/시행규칙/용어집)',
                    'type': 'keyword',
                    'filterable': True,
                    'facetable': True
                },
                'category': {
                    'description': 'Category folder',
                    'type': 'keyword',
                    'filterable': True,
                    'facetable': True
                },
                'enforcement_date': {
                    'description': 'Enforcement date',
                    'type': 'date',
                    'filterable': True,
                    'sortable': True
                },
                'chapter': {
                    'description': 'Chapter information',
                    'type': 'keyword',
                    'filterable': True,
                    'hierarchical': True
                },
                'section': {
                    'description': 'Section information',
                    'type': 'keyword',
                    'filterable': True,
                    'hierarchical': True
                },
                'article_number': {
                    'description': 'Article number',
                    'type': 'keyword',
                    'filterable': True,
                    'sortable': True
                },
                'is_deleted': {
                    'description': 'Deletion flag',
                    'type': 'boolean',
                    'filterable': True,
                    'default': False
                }
            },
            'reference_fields': {
                'law_references': {
                    'description': 'References to other laws',
                    'type': 'keyword_array',
                    'searchable': True
                },
                'decree_references': {
                    'description': 'References to decrees',
                    'type': 'keyword_array',
                    'searchable': True
                },
                'form_references': {
                    'description': 'References to forms',
                    'type': 'keyword_array',
                    'searchable': True
                }
            },
            'special_flags': {
                'is_tenant_protection': {
                    'description': 'Tenant protection related',
                    'type': 'boolean',
                    'filterable': True
                },
                'is_delegation': {
                    'description': 'Delegation provisions',
                    'type': 'boolean',
                    'filterable': True
                },
                'is_tax_related': {
                    'description': 'Tax-related provisions',
                    'type': 'boolean',
                    'filterable': True
                },
                'is_price_disclosure_related': {
                    'description': 'Price disclosure related',
                    'type': 'boolean',
                    'filterable': True
                }
            }
        },
        'search': {
            'default_limit': 10,
            'max_limit': 100,
            'similarity_threshold': 0.7,
            'reranking': {
                'enabled': True,
                'model': 'cross-encoder/ms-marco-MiniLM-L-12-v2'
            },
            'filters': {
                'default_filters': [],
                'common_filters': [
                    {'field': 'is_deleted', 'value': False},
                    {'field': 'doc_type', 'values': ['법률', '시행령', '시행규칙']}
                ]
            }
        },
        'query_expansion': {
            'enabled': True,
            'methods': ['synonym_expansion', 'legal_term_mapping'],
            'synonym_dict': {
                '임대': ['임차', '전세', '월세', '렌트'],
                '매매': ['매수', '매도', '거래', '양도'],
                '주택': ['아파트', '집', '주거', '거주지'],
                '공시': ['고시', '발표', '공개']
            }
        }
    }

    return search_config

def main():
    """Main function to generate all metadata files"""

    base_path = r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info\chunked"

    print("Analyzing chunked files...")
    metadata_index, document_registry, chunk_statistics, category_taxonomy = analyze_chunked_files(base_path)

    print("Creating search configuration...")
    search_config = create_search_config()

    # Save metadata_index.json
    output_path = os.path.join(base_path, "metadata_index.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metadata_index, f, ensure_ascii=False, indent=2)
    print(f"Created: {output_path}")

    # Save document_registry.json
    output_path = os.path.join(base_path, "document_registry.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(document_registry, f, ensure_ascii=False, indent=2)
    print(f"Created: {output_path}")

    # Save chunk_statistics.json
    output_path = os.path.join(base_path, "chunk_statistics.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(chunk_statistics, f, ensure_ascii=False, indent=2)
    print(f"Created: {output_path}")

    # Save category_taxonomy.json
    output_path = os.path.join(base_path, "category_taxonomy.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(category_taxonomy, f, ensure_ascii=False, indent=2)
    print(f"Created: {output_path}")

    # Save search_config.yaml
    output_path = os.path.join(base_path, "search_config.yaml")
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(search_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"Created: {output_path}")

    # Print summary
    print("\n" + "="*50)
    print("Metadata Generation Summary")
    print("="*50)
    print(f"Total Documents: {metadata_index['total_documents']}")
    print(f"Total Chunks: {metadata_index['total_chunks']}")
    print(f"Categories: {len(metadata_index['categories'])}")
    print(f"Document Types: {len(chunk_statistics['by_document_type'])}")
    print(f"Metadata Fields: {len(chunk_statistics['metadata_field_usage'])}")
    print(f"Reference Types: {sum(chunk_statistics['reference_statistics'].values())} total references")
    print("="*50)

if __name__ == "__main__":
    main()