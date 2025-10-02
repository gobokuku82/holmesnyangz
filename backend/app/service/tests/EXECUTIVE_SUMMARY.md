# Executive Summary: Search Failure Investigation

**Investigation Date**: October 2, 2025
**Issue**: Two specific legal article queries failing in search tests

---

## The Question

Why are these queries failing?
1. **민법 제618조** (Civil Code Article 618)
2. **상가건물 임대차보호법 제10조** (Commercial Building Lease Protection Act Article 10)

---

## The Answer

**Both documents DO NOT EXIST in the ChromaDB database.**

This is **NOT a search bug**. The search system is working correctly - it simply cannot find documents that were never added to the database.

---

## Evidence

### Database Contents (28 Unique Laws)

The database contains **1,700 documents** from these laws:

#### Real Estate Transaction Laws
1. **공인중개사법** (Real Estate Broker Act) - 법률, 시행령, 시행규칙
2. **부동산 거래신고 등에 관한 법률** (Real Estate Transaction Reporting Act) - 법률, 시행령, 시행규칙
3. **부동산등기법** (Real Estate Registration Act) - 법률
4. **부동산등기규칙** (Real Estate Registration Rules) - 규칙

#### Housing and Rental Laws
5. **주택법** (Housing Act) - 법률, 시행규칙
6. **주택임대차보호법** (Residential Lease Protection Act) - 법률, 시행령 ✓
7. **민간임대주택에 관한 특별법** (Private Rental Housing Special Act) - 법률, 시행령, 시행규칙

#### Building Management Laws
8. **공동주택관리법** (Apartment Management Act) - 법률, 시행령, 시행규칙
9. **건축물의 분양에 관한 법률** (Building Sale Act) - 법률, 시행령, 시행규칙

#### Property Valuation Laws
10. **부동산 가격공시에 관한 법률** (Real Estate Price Publication Act) - 법률, 시행령, 시행규칙

#### Other Resources
11. **부동산 용어 95가지** (95 Real Estate Terms)
12. **공동주택 분양가격의 산정 등에 관한 규칙** (Apartment Sale Price Calculation Rules)
13. **공동주택 층간소음의 범위와 기준에 관한 규칙** (Apartment Inter-floor Noise Rules)
14. **공인중개사의 매수신청대리인 등록 등에 관한 규칙** (Real Estate Broker Purchase Agent Registration Rules)

### What's MISSING

❌ **민법** (Civil Code) - Not in database
❌ **상가건물 임대차보호법** (Commercial Building Lease Protection Act) - Not in database

---

## Test Results Analysis

### Query 1: "민법 제618조"

| Test | Result | Explanation |
|------|--------|-------------|
| Article number search | 0 docs | No "제618조" exists in DB |
| Title search | 0 docs | No "민법" exists in DB |
| Vector search | 0/20 matches | Returns unrelated docs with similar numbers |

**What the system returns instead:**
- 부동산 가격공시에 관한 법률 시행령 제61조 (relevance: 0.514)
- 주택법 제98조 (relevance: 0.510)

These are **wrong answers**, but they're the best semantic matches available when the correct document doesn't exist.

### Query 2: "상가건물 임대차보호법 제10조"

| Test | Result | Explanation |
|------|--------|-------------|
| Article number search | 25 docs | Many laws have "제10조" but wrong titles |
| Title search | 0 docs | No "상가건물 임대차보호법" exists |
| Vector search | 6/20 with 제10조 | Returns similar law with same article number |

**What the system returns instead:**
- **주택임대차보호법 제10조** (relevance: 0.619) ← Different law!

The system returns the **Residential** Lease Protection Act instead of the **Commercial** Building Lease Protection Act because:
1. Both laws protect tenants in lease agreements
2. Both have similar structure and Article 10
3. The semantic meaning is very close
4. The correct document doesn't exist

---

## Why This Is NOT a Bug

### The Search System IS Working

✅ **Article detection**: Correctly identifies law title and article number
✅ **Metadata filtering**: Successfully filters by article number
✅ **Title matching**: Correctly finds NO matches for missing titles
✅ **Vector search**: Returns semantically similar results when exact match fails
✅ **Post-filtering**: Properly filters results by article number

### The Database IS Limited

The database was designed for **real estate transaction and housing rental** purposes:
- ✓ Residential lease protection (주택임대차보호법)
- ✗ Commercial lease protection (상가건물 임대차보호법)
- ✗ General civil law (민법)

---

## Impact Assessment

### Test Suite
- **Test file**: `test_specific_article_search.py`
- **Total tests**: 10 queries
- **Passing**: 8 queries (80%)
- **Failing**: 2 queries (20%)

The 2 failing queries are asking for documents that don't exist in the database.

### Search System
- **No bugs found** in search logic
- **No bugs found** in metadata filtering
- **No bugs found** in vector search

### Database Coverage
- **Residential real estate**: Well covered
- **Commercial real estate**: Missing key laws
- **General civil law**: Not included

---

## Recommendations

### Option 1: Update Tests (Quick Fix)
Remove or mark these 2 test cases as "expected to fail" with comments explaining the documents are not in the database:

```python
# SKIP: 민법 is not in the real estate law database
# SKIP: 상가건물 임대차보호법 is not in the database (only 주택임대차보호법)
```

### Option 2: Expand Database (Long-term Solution)

**High Priority - Add Commercial Laws:**
- 상가건물 임대차보호법 (Commercial Building Lease Protection Act)
  - 법률
  - 시행령
  - 시행규칙

**Medium Priority - Add Relevant Civil Code Sections:**
- 민법 제3편 채권 제2장 계약 제8절 임대차 (Articles 618-654)
  - These articles cover lease contracts and are directly relevant to real estate

### Option 3: Improve User Feedback

When a document is not found, provide clearer messaging:

```json
{
  "status": "not_found",
  "message": "민법 제618조 was not found in the database",
  "reason": "The database focuses on real estate-specific laws. The general Civil Code is not included.",
  "similar_results": [...],
  "disclaimer": "The following results are semantically similar but not exact matches"
}
```

---

## Files Created During Investigation

1. `debug_specific_articles.py` - Direct ChromaDB query script
2. `debug_articles_json.py` - JSON output version (encoding-safe)
3. `debug_articles_20251002_110010.json` - Detailed test results
4. `list_all_laws.py` - Database inventory script
5. `database_laws_list_20251002_110239.json` - Complete law list
6. `SEARCH_FAILURE_ANALYSIS.md` - Technical deep-dive
7. `EXECUTIVE_SUMMARY.md` - This document

---

## Conclusion

**The search system is working correctly.** The test failures are due to incomplete database coverage, not software bugs.

The two failing queries ask for legal documents that were intentionally or unintentionally excluded from the database during the embedding process:
1. **民法** (Civil Code) - General law, not real estate-specific
2. **상가건물 임대차보호법** (Commercial Lease Protection) - Real estate law, but commercial vs. residential

**Recommended Action**: Either expand the database to include these laws, or update the tests to reflect the actual database scope.

---

## Quick Reference: Database Coverage

| Law Type | Status | Examples |
|----------|--------|----------|
| Real Estate Transaction | ✓ Complete | 공인중개사법, 부동산 거래신고법 |
| Residential Rental | ✓ Complete | 주택임대차보호법, 민간임대주택법 |
| Property Registration | ✓ Complete | 부동산등기법 |
| Building Management | ✓ Complete | 공동주택관리법 |
| Commercial Rental | ✗ Missing | 상가건물 임대차보호법 |
| General Civil Law | ✗ Missing | 민법 |

---

**End of Executive Summary**
