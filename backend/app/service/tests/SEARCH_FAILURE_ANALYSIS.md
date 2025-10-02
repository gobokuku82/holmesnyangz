# Search Failure Analysis: 민법 제618조 and 상가건물 임대차보호법 제10조

**Date**: 2025-10-02
**Analysis By**: Claude Code Debug Session

---

## Executive Summary

Two specific article queries are failing in the legal search system:
1. **민법 제618조** - COMPLETE FAILURE (document doesn't exist in database)
2. **상가건물 임대차보호법 제10조** - PARTIAL FAILURE (document doesn't exist, returns wrong law)

---

## Key Findings

### Database Schema Analysis

The ChromaDB collection uses a **unified `title` field** instead of separate `law_title`, `decree_title`, and `rule_title` fields:

```json
{
  "title_field_analysis": {
    "title": 100,           // All documents use 'title'
    "law_title": 0,         // Legacy field, not used
    "decree_title": 0,      // Legacy field, not used
    "rule_title": 0         // Legacy field, not used
  }
}
```

Sample titles in database:
- "공인중개사법 시행규칙"
- "주택임대차보호법"
- "민간임대주택에 관한 특별법"
- "부동산 가격공시에 관한 법률"

---

## Case 1: 민법 제618조 (COMPLETE FAILURE)

### What Was Searched
- **Query**: "민법 제618조"
- **Expected**: 민법 (Civil Code) Article 618
- **Law Title**: "민법"
- **Article Number**: "제618조"

### Test Results

| Test Method | Result | Details |
|------------|--------|---------|
| Search by Article Number | **0 documents** | No articles with "제618조" exist in DB |
| Search by Title Keyword | **0 documents** | No documents with "민법" in title |
| Exact Match (Title + Article) | **0 exact, 0 partial** | Document doesn't exist |
| Vector Search | **0/20 matches** | No results with article "제618조" |

### Vector Search Top Result
The search returned completely unrelated results:
1. **부동산 가격공시에 관한 법률 시행령 제61조** (relevance: 0.514)
2. **주택법 제98조** (relevance: 0.510)
3. **부동산 거래신고 등에 관한 법률 시행령 제5조** (relevance: 0.496)

### Root Cause
**The document "민법 제618조" does NOT EXIST in the ChromaDB database.**

The database contains 1,700 documents focused on real estate law, but does **NOT** include the general Civil Code (민법). Article 618 of the Civil Code deals with lease contracts, which is related to real estate, but the base law itself was not embedded in the database.

### Why Vector Search Returns Wrong Results
Since the exact document doesn't exist, the vector search falls back to semantic similarity and returns documents that:
- Have similar numeric article numbers (제61조 is numerically close to 제618조)
- Contain related legal concepts (property law, regulations)
- Have mid-range relevance scores (0.48-0.51) indicating poor matches

---

## Case 2: 상가건물 임대차보호법 제10조 (PARTIAL FAILURE)

### What Was Searched
- **Query**: "상가건물 임대차보호법 제10조"
- **Expected**: Commercial Building Lease Protection Act Article 10
- **Law Title**: "상가건물 임대차보호법"
- **Article Number**: "제10조"

### Test Results

| Test Method | Result | Details |
|------------|--------|---------|
| Search by Article Number | **25 documents** | Many laws have "제10조" but none match the title |
| Search by Title Keyword | **0 documents** | No documents with "상가건물 임대차보호법" in title |
| Exact Match (Title + Article) | **0 exact, 0 partial** | Document doesn't exist |
| Vector Search | **6/20 matches article number** | But wrong law titles |

### Documents Found with Article Number "제10조"
The database contains 25 different Article 10s from various laws:
- 공인중개사법 시행규칙 제10조
- 공인중개사법 시행령 제10조
- 공인중개사법 제10조
- 부동산 거래신고 등에 관한 법률 제10조
- **주택임대차보호법 제10조** ← This is what was returned!
- 민간임대주택에 관한 특별법 제10조
- 부동산등기법 제10조
- 공동주택관리법 제10조
- ... (17 more)

### Vector Search Top Results
1. **주택임대차보호법 제10조** - 강행규정 (relevance: 0.619) ← WRONG LAW!
2. **민간임대주택에 관한 특별법 제10조** (relevance: 0.580)
3. 민간임대주택에 관한 특별법 시행령 제9조 (relevance: 0.577)

### Root Cause
**The document "상가건물 임대차보호법 제10조" does NOT EXIST in the database.**

The database contains:
- ✅ **주택임대차보호법** (Residential Lease Protection Act)
- ❌ **상가건물 임대차보호법** (Commercial Building Lease Protection Act)

These are two different laws:
- **주택** = Residential housing
- **상가건물** = Commercial buildings/stores

### Why Vector Search Returns Wrong Results
The vector search returns "주택임대차보호법 제10조" because:
1. Both laws are semantically similar (both protect tenants in lease agreements)
2. The query contains "임대차보호법 제10조" which matches exactly
3. The vector embedding sees "주택임대차보호법" and "상가건물 임대차보호법" as very similar
4. Without the correct document in the database, it returns the closest semantic match

### Evidence from Vector Search Results
- Rank 1: **주택임대차보호법 제10조** (relevance: 0.619) - Very high relevance
- Rank 2: **민간임대주택에 관한 특별법 제10조** (relevance: 0.580)
- Rank 14: **부동산 가격공시에 관한 법률 시행규칙 제10조** (relevance: 0.536)

All top results are lease/rental-related laws with Article 10, showing the search is working correctly but the source data is missing.

---

## Database Content Analysis

### What's IN the Database
The database focuses on **real estate transaction and housing rental laws**:
- 공인중개사법 (Real Estate Broker Act)
- 주택임대차보호법 (Residential Lease Protection Act)
- 부동산등기법 (Real Estate Registration Act)
- 부동산 거래신고 등에 관한 법률 (Real Estate Transaction Reporting Act)
- 주택법 (Housing Act)
- 공동주택관리법 (Apartment Management Act)
- 민간임대주택에 관한 특별법 (Private Rental Housing Special Act)
- 부동산 가격공시에 관한 법률 (Real Estate Price Publication Act)

### What's MISSING from the Database
1. **민법** (Civil Code) - The fundamental private law
2. **상가건물 임대차보호법** (Commercial Building Lease Protection Act)
3. Likely other commercial real estate laws

---

## Search Logic Analysis

### Current Search Flow (from legal_search_tool.py)

1. **Detect if specific article query** (line 90)
   ```python
   article_query = self._is_specific_article_query(query)
   ```

2. **Method 1: ChromaDB Direct Metadata Filtering** (line 96-116)
   - Searches for exact article_number match
   - Filters by law title (partial matching)
   - Uses `collection.get()` and `collection.query()`

3. **Method 2: Enhanced Vector Search** (line 118-159)
   - Creates enhanced query: `"{law_title} {article_number} 내용 조항"`
   - Uses vector embedding
   - Post-filters results for specific article

4. **Fallback: Standard Vector Search** (line 161-191)
   - Uses original query
   - Returns top semantic matches

### Why the Search Logic is NOT at Fault

The search logic is actually working **correctly**:

1. ✅ **Article detection works**: Correctly identifies "민법 제618조" and extracts:
   - law_title: "민법"
   - article_number: "제618조"

2. ✅ **Metadata filtering works**: Successfully filters 25 documents with "제10조"

3. ✅ **Title matching works**: Correctly finds NO documents with "민법" or "상가건물 임대차보호법" in title

4. ✅ **Vector search works**: Returns semantically similar results when exact match fails

5. ✅ **Post-filtering works**: Successfully identifies which results match the target article number

### The Real Problem

The search system is **working as designed**, but it cannot find documents that **don't exist in the database**.

---

## Verification Using Code

### Title Field Check (from legal_search_tool.py line 435)
```python
title = metadata.get('title') or metadata.get('law_title') or metadata.get('decree_title') or metadata.get('rule_title', 'N/A')
```

This shows the code properly handles both:
- New unified `title` field (primary)
- Legacy `law_title`, `decree_title`, `rule_title` fields (fallback)

### Exact Match Logic (line 236-240)
```python
for i, metadata in enumerate(results['metadatas']):
    title = metadata.get('title', '')
    if law_title in title:  # Partial matching
        filtered_ids.append(results['ids'][i])
```

The search uses **partial matching** (`if law_title in title`), so it should find:
- "민법" would match "민법" (if it existed)
- "상가건물 임대차보호법" would match "상가건물 임대차보호법" (if it existed)

---

## Conclusion

### Summary of Findings

| Query | Document Exists? | Search Working? | Issue |
|-------|-----------------|-----------------|-------|
| 민법 제618조 | ❌ NO | ✅ YES | Missing from database |
| 상가건물 임대차보호법 제10조 | ❌ NO | ✅ YES | Missing from database |

### Root Causes

1. **민법 제618조 failure**: The Civil Code (민법) was not included in the embedding/indexing process
2. **상가건물 임대차보호법 제10조 failure**: The Commercial Building Lease Protection Act was not included in the embedding/indexing process

### Why Tests Are Failing

The test file `test_specific_article_search.py` assumes these documents exist in the database, but they don't. The test expectations are incorrect:

```python
{
    "query": "민법 제618조",
    "expected": {
        "law_title": "민법",
        "article_number": "제618조",
        "min_results": 1  # ← This expectation is wrong!
    }
}
```

---

## Recommendations

### 1. Update Test Expectations (Immediate)

Modify `test_specific_article_search.py` to:
- Mark these queries as "expected to fail" or "out of scope"
- Add comments explaining these laws are not in the database
- Or remove these test cases entirely

### 2. Expand Database Coverage (Long-term)

If these laws should be searchable, add them to the database:

**Priority 1: 상가건물 임대차보호법**
- This is directly related to real estate leasing
- Should be in a real estate law database

**Priority 2: 민법 (relevant articles only)**
- The entire Civil Code is massive (1,118 articles)
- Consider embedding only real estate-related sections:
  - 제3편 채권 (Obligations)
    - 제2장 계약 (Contracts)
      - 제8절 임대차 (Lease) - Articles 618-654

### 3. Improve Search Response (Immediate)

When no exact match is found, the search should:
1. Explicitly state the document was not found
2. Suggest the closest matches with a disclaimer
3. Log missing document queries for database expansion

Example response format:
```json
{
  "status": "not_found",
  "message": "민법 제618조 was not found in the database",
  "similar_results": [...],
  "disclaimer": "The following results are semantically similar but not exact matches"
}
```

### 4. Database Completeness Check

Create a script to:
1. List all law titles in the database
2. Check for common laws that might be missing
3. Validate that expected laws are present

---

## Files Analyzed

1. `C:\kdy\Projects\holmesnyangz\beta_v001\backend\app\service\tools\legal_search_tool.py`
2. `C:\kdy\Projects\holmesnyangz\beta_v001\backend\app\service\tests\test_specific_article_search.py`
3. `C:\kdy\Projects\holmesnyangz\beta_v001\backend\app\service\tests\test_specific_article_results_20251002_105214.json`
4. `C:\kdy\Projects\holmesnyangz\beta_v001\backend\app\service\tests\debug_articles_20251002_110010.json`
5. ChromaDB database at: `C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info\chroma_db`

---

## Appendix: Vector Search Behavior

### Why "주택임대차보호법" matches "상가건물 임대차보호법" query

Vector embeddings capture semantic meaning. The terms are very similar:
- **Common**: 임대차보호법 (Lease Protection Act)
- **Different**: 주택 (housing) vs 상가건물 (commercial building)

Since both:
1. Protect tenants in lease agreements
2. Have similar legal structure
3. Share the same article numbering scheme

The vector distance is small (0.381), resulting in high relevance (0.619).

This is actually **correct behavior** for a semantic search system when the exact document doesn't exist!

---

## End of Analysis
