#!/usr/bin/env python3
"""
Final metadata quality check before ChromaDB regeneration
"""
import json
from pathlib import Path
from collections import defaultdict

print("=" * 80)
print("FINAL METADATA CHECK - Chunked JSON Files")
print("=" * 80)

base_path = Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info\chunked")

categories = [
    "1_공통 매매_임대차",
    "2_임대차_전세_월세",
    "3_공급_및_관리_매매_분양",
    "4_기타"
]

# Statistics
total_chunks = 0
metadata_stats = {
    'has_is_tenant_protection_true': 0,
    'has_is_tenant_protection_false': 0,
    'has_is_tax_related_true': 0,
    'has_is_tax_related_false': 0,
    'has_is_delegation_true': 0,
    'has_is_delegation_false': 0,
    'has_is_penalty_related_true': 0,
    'has_is_penalty_related_false': 0,
    'has_is_deleted_true': 0,
    'has_is_deleted_false': 0,
    'missing_is_tenant_protection': 0,
    'missing_is_tax_related': 0,
    'missing_is_delegation': 0,
    'missing_is_penalty_related': 0,
    'missing_is_deleted': 0,
}

doc_type_distribution = defaultdict(int)
files_processed = []

print("\nProcessing chunked JSON files...\n")

for category in categories:
    category_path = base_path / category
    if not category_path.exists():
        print(f"⚠️  Category not found: {category}")
        continue

    json_files = list(category_path.glob("*.json"))
    print(f"[{category}]: {len(json_files)} files")

    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                chunks = json.load(f)

            files_processed.append(json_file.name)

            for chunk in chunks:
                total_chunks += 1
                metadata = chunk.get('metadata', {})

                # Check boolean fields
                # is_tenant_protection
                if 'is_tenant_protection' in metadata:
                    if metadata['is_tenant_protection'] is True:
                        metadata_stats['has_is_tenant_protection_true'] += 1
                    elif metadata['is_tenant_protection'] is False:
                        metadata_stats['has_is_tenant_protection_false'] += 1
                else:
                    metadata_stats['missing_is_tenant_protection'] += 1

                # is_tax_related
                if 'is_tax_related' in metadata:
                    if metadata['is_tax_related'] is True:
                        metadata_stats['has_is_tax_related_true'] += 1
                    elif metadata['is_tax_related'] is False:
                        metadata_stats['has_is_tax_related_false'] += 1
                else:
                    metadata_stats['missing_is_tax_related'] += 1

                # is_delegation
                if 'is_delegation' in metadata:
                    if metadata['is_delegation'] is True:
                        metadata_stats['has_is_delegation_true'] += 1
                    elif metadata['is_delegation'] is False:
                        metadata_stats['has_is_delegation_false'] += 1
                else:
                    metadata_stats['missing_is_delegation'] += 1

                # is_penalty_related
                if 'is_penalty_related' in metadata:
                    if metadata['is_penalty_related'] is True:
                        metadata_stats['has_is_penalty_related_true'] += 1
                    elif metadata['is_penalty_related'] is False:
                        metadata_stats['has_is_penalty_related_false'] += 1
                else:
                    metadata_stats['missing_is_penalty_related'] += 1

                # is_deleted
                if 'is_deleted' in metadata:
                    if metadata['is_deleted'] is True:
                        metadata_stats['has_is_deleted_true'] += 1
                    elif metadata['is_deleted'] is False:
                        metadata_stats['has_is_deleted_false'] += 1
                else:
                    metadata_stats['missing_is_deleted'] += 1

                # Doc type (from filename)
                if '시행규칙' in json_file.name:
                    doc_type_distribution['시행규칙'] += 1
                elif '시행령' in json_file.name:
                    doc_type_distribution['시행령'] += 1
                elif '법률' in json_file.name or '법(' in json_file.name:
                    doc_type_distribution['법률'] += 1
                elif '대법원규칙' in json_file.name:
                    doc_type_distribution['대법원규칙'] += 1
                elif '용어' in json_file.name:
                    doc_type_distribution['용어집'] += 1
                else:
                    doc_type_distribution['기타'] += 1

        except Exception as e:
            print(f"❌ Error processing {json_file.name}: {e}")

print("\n" + "=" * 80)
print("RESULTS")
print("=" * 80)

print(f"\nTotal chunks: {total_chunks}")
print(f"Files processed: {len(files_processed)}")

print("\n--- Doc Type Distribution (from filenames) ---")
for doc_type, count in sorted(doc_type_distribution.items(), key=lambda x: -x[1]):
    pct = (count / total_chunks) * 100
    print(f"  {doc_type}: {count} ({pct:.1f}%)")

print("\n--- Boolean Fields Status ---")
print("\nis_tenant_protection:")
print(f"  True:    {metadata_stats['has_is_tenant_protection_true']:4d}")
print(f"  False:   {metadata_stats['has_is_tenant_protection_false']:4d}")
print(f"  Missing: {metadata_stats['missing_is_tenant_protection']:4d} ({metadata_stats['missing_is_tenant_protection']/total_chunks*100:.1f}%)")

print("\nis_tax_related:")
print(f"  True:    {metadata_stats['has_is_tax_related_true']:4d}")
print(f"  False:   {metadata_stats['has_is_tax_related_false']:4d}")
print(f"  Missing: {metadata_stats['missing_is_tax_related']:4d} ({metadata_stats['missing_is_tax_related']/total_chunks*100:.1f}%)")

print("\nis_delegation:")
print(f"  True:    {metadata_stats['has_is_delegation_true']:4d}")
print(f"  False:   {metadata_stats['has_is_delegation_false']:4d}")
print(f"  Missing: {metadata_stats['missing_is_delegation']:4d} ({metadata_stats['missing_is_delegation']/total_chunks*100:.1f}%)")

print("\nis_penalty_related:")
print(f"  True:    {metadata_stats['has_is_penalty_related_true']:4d}")
print(f"  False:   {metadata_stats['has_is_penalty_related_false']:4d}")
print(f"  Missing: {metadata_stats['missing_is_penalty_related']:4d} ({metadata_stats['missing_is_penalty_related']/total_chunks*100:.1f}%)")

print("\nis_deleted:")
print(f"  True:    {metadata_stats['has_is_deleted_true']:4d}")
print(f"  False:   {metadata_stats['has_is_deleted_false']:4d}")
print(f"  Missing: {metadata_stats['missing_is_deleted']:4d} ({metadata_stats['missing_is_deleted']/total_chunks*100:.1f}%)")

print("\n" + "=" * 80)
print("QUALITY ASSESSMENT")
print("=" * 80)

issues = []
warnings = []

# Check if metadata is mostly missing
if metadata_stats['missing_is_tenant_protection'] > total_chunks * 0.9:
    issues.append("ISSUE: is_tenant_protection: 90%+ missing")
elif metadata_stats['missing_is_tenant_protection'] > total_chunks * 0.5:
    warnings.append("WARNING: is_tenant_protection: 50%+ missing")
else:
    print("OK: is_tenant_protection: Available")

if metadata_stats['missing_is_tax_related'] > total_chunks * 0.9:
    issues.append("ISSUE: is_tax_related: 90%+ missing")
elif metadata_stats['missing_is_tax_related'] > total_chunks * 0.5:
    warnings.append("WARNING: is_tax_related: 50%+ missing")
else:
    print("OK: is_tax_related: Available")

if metadata_stats['missing_is_delegation'] > total_chunks * 0.9:
    issues.append("ISSUE: is_delegation: 90%+ missing")
elif metadata_stats['missing_is_delegation'] > total_chunks * 0.5:
    warnings.append("WARNING: is_delegation: 50%+ missing")
else:
    print("OK: is_delegation: Available")

if metadata_stats['missing_is_deleted'] > total_chunks * 0.5:
    issues.append("ISSUE: is_deleted: 50%+ missing - CRITICAL!")

if issues:
    print("\nCRITICAL ISSUES:")
    for issue in issues:
        print(f"  {issue}")

if warnings:
    print("\nWARNINGS:")
    for warning in warnings:
        print(f"  {warning}")

print("\n" + "=" * 80)
print("RECOMMENDATION")
print("=" * 80)

if metadata_stats['has_is_tenant_protection_true'] >= 20 and \
   metadata_stats['has_is_delegation_true'] >= 100:
    print("\nOK - Source data quality is GOOD")
    print("OK - Metadata fields are properly populated in chunked JSON")
    print("OK - Ready to regenerate ChromaDB with fixed loader script")
    print("\nExpected improvements after regeneration:")
    print(f"  - is_tenant_protection: {metadata_stats['has_is_tenant_protection_true']} documents will be searchable")
    print(f"  - is_tax_related: {metadata_stats['has_is_tax_related_true']} documents will be searchable")
    print(f"  - is_delegation: {metadata_stats['has_is_delegation_true']} documents will be searchable")
else:
    print("\nERROR - Source data quality is POOR")
    print("ERROR - Need to fix chunked JSON files before regenerating ChromaDB")

print("\n" + "=" * 80)
