"""
Test specific article search functionality in legal_search_tool.py
Tests the ability to find specific law articles like "주택임대차보호법 제7조"
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Any
import json
from datetime import datetime

# Add parent directory to path for imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Import the legal search tool
from app.service.tools.legal_search_tool import LegalSearchTool


class TestSpecificArticleSearch:
    """Test suite for specific article search functionality"""

    def __init__(self):
        """Initialize test suite"""
        self.tool = LegalSearchTool()
        self.test_cases = self._create_test_cases()
        self.results = []

    def _create_test_cases(self) -> List[Dict[str, Any]]:
        """Create test cases for specific article searches"""
        return [
            {
                "query": "주택임대차보호법 제7조",
                "expected": {
                    "law_title": "주택임대차보호법",
                    "article_number": "제7조",
                    "min_results": 1
                }
            },
            {
                "query": "주택임대차보호법 제7조 내용은?",
                "expected": {
                    "law_title": "주택임대차보호법",
                    "article_number": "제7조",
                    "min_results": 1
                }
            },
            {
                "query": "부동산등기법 제73조",
                "expected": {
                    "law_title": "부동산등기법",
                    "article_number": "제73조",
                    "min_results": 1
                }
            },
            {
                "query": "민법 제618조",
                "expected": {
                    "law_title": "민법",
                    "article_number": "제618조",
                    "min_results": 1
                }
            },
            {
                "query": "공인중개사법 제33조",
                "expected": {
                    "law_title": "공인중개사법",
                    "article_number": "제33조",
                    "min_results": 1
                }
            },
            {
                "query": "주택임대차보호법 제8조",
                "expected": {
                    "law_title": "주택임대차보호법",
                    "article_number": "제8조",
                    "min_results": 1
                }
            },
            {
                "query": "부동산 거래신고 등에 관한 법률 제3조",
                "expected": {
                    "law_title": "부동산 거래신고 등에 관한 법률",
                    "article_number": "제3조",
                    "min_results": 1
                }
            },
            {
                "query": "주택법 제2조",
                "expected": {
                    "law_title": "주택법",
                    "article_number": "제2조",
                    "min_results": 1
                }
            },
            {
                "query": "상가건물 임대차보호법 제10조",
                "expected": {
                    "law_title": "상가건물 임대차보호법",
                    "article_number": "제10조",
                    "min_results": 1
                }
            },
            {
                "query": "공동주택관리법 제14조",
                "expected": {
                    "law_title": "공동주택관리법",
                    "article_number": "제14조",
                    "min_results": 1
                }
            }
        ]

    async def test_single_query(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single specific article query"""
        query = test_case["query"]
        expected = test_case["expected"]

        print(f"\n[Testing] Query: {query}")

        try:
            # Run the search
            result = await self.tool.search(query)

            # Check if search was successful
            if result["status"] != "success":
                print(f"  [FAILED] Search failed with status: {result['status']}")
                return {
                    "query": query,
                    "status": "failed",
                    "error": f"Search status: {result['status']}",
                    "expected": expected,
                    "actual": None
                }

            # Get search results
            data = result.get("data", [])

            # Check if this is an error response (law not found)
            if data and len(data) == 1 and data[0].get("type") == "error":
                print(f"  [NOT FOUND] {data[0]['message']}")
                return {
                    "query": query,
                    "status": "not_found",
                    "message": data[0]['message'],
                    "expected": expected,
                    "actual": None
                }

            result_count = len(data)
            print(f"  Found {result_count} results")

            # Check if we got minimum expected results
            if result_count < expected["min_results"]:
                print(f"  [FAILED] Expected at least {expected['min_results']} results, got {result_count}")
                return {
                    "query": query,
                    "status": "insufficient_results",
                    "result_count": result_count,
                    "expected": expected,
                    "actual": data
                }

            # Check if the correct law and article were found
            correct_match = False
            matched_item = None

            for item in data:
                law_title = item.get("law_title", "")
                article_number = item.get("article_number", "")

                # Check for exact match or partial match for law title
                title_match = (
                    expected["law_title"] in law_title or
                    law_title in expected["law_title"]
                )

                # Check for exact article number match
                article_match = article_number == expected["article_number"]

                if title_match and article_match:
                    correct_match = True
                    matched_item = item
                    break

            if correct_match:
                print(f"  [SUCCESS] Found correct article: {matched_item['law_title']} {matched_item['article_number']}")
                return {
                    "query": query,
                    "status": "success",
                    "result_count": result_count,
                    "expected": expected,
                    "matched_item": matched_item
                }
            else:
                # Log what was actually found
                if data:
                    first_result = data[0]
                    print(f"  [FAILED] Wrong result: {first_result.get('law_title', 'N/A')} {first_result.get('article_number', 'N/A')}")
                else:
                    print(f"  [FAILED] No matching articles found")

                return {
                    "query": query,
                    "status": "wrong_match",
                    "result_count": result_count,
                    "expected": expected,
                    "actual": data[:3] if data else []  # Show first 3 results
                }

        except Exception as e:
            print(f"  [ERROR] Error: {str(e)}")
            return {
                "query": query,
                "status": "error",
                "error": str(e),
                "expected": expected,
                "actual": None
            }

    async def run_all_tests(self):
        """Run all test cases"""
        print("=" * 80)
        print("Starting Specific Article Search Tests")
        print("=" * 80)

        # Track statistics
        success_count = 0
        failure_count = 0
        error_count = 0

        # Run each test case
        for i, test_case in enumerate(self.test_cases, 1):
            print(f"\n[{i}/{len(self.test_cases)}] ", end="")
            result = await self.test_single_query(test_case)
            self.results.append(result)

            # Update statistics
            if result["status"] == "success":
                success_count += 1
            elif result["status"] == "error":
                error_count += 1
            elif result["status"] == "not_found":
                # Not found is expected behavior for non-existent laws
                failure_count += 1
            else:
                failure_count += 1

            # Small delay between queries
            await asyncio.sleep(0.5)

        # Print summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        total = len(self.test_cases)
        success_rate = (success_count / total) * 100 if total > 0 else 0

        print(f"Total tests: {total}")
        print(f"[SUCCESS]: {success_count} ({success_count / total * 100:.1f}%)")
        print(f"[FAILED]: {failure_count} ({failure_count / total * 100:.1f}%)")
        print(f"[ERRORS]: {error_count} ({error_count / total * 100:.1f}%)")
        print(f"\nOverall Success Rate: {success_rate:.1f}%")

        # Show failed cases
        if failure_count > 0 or error_count > 0:
            print("\n" + "-" * 40)
            print("FAILED TEST CASES:")
            for result in self.results:
                if result["status"] != "success":
                    print(f"\n- Query: {result['query']}")
                    print(f"  Status: {result['status']}")
                    if result.get("actual"):
                        if result["actual"]:
                            first = result["actual"][0]
                            print(f"  Got: {first.get('law_title', 'N/A')} {first.get('article_number', 'N/A')}")
                        print(f"  Expected: {result['expected']['law_title']} {result['expected']['article_number']}")

        # Save results to file
        self._save_results()

        return success_rate

    def _save_results(self):
        """Save test results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_specific_article_results_{timestamp}.json"
        filepath = Path(__file__).parent / filename

        report = {
            "test_name": "Specific Article Search Test",
            "timestamp": timestamp,
            "test_count": len(self.test_cases),
            "results": self.results,
            "summary": {
                "total": len(self.test_cases),
                "success": sum(1 for r in self.results if r["status"] == "success"),
                "failed": sum(1 for r in self.results if r["status"] != "success" and r["status"] != "error"),
                "errors": sum(1 for r in self.results if r["status"] == "error")
            }
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\nResults saved to: {filename}")


async def main():
    """Main test runner"""
    tester = TestSpecificArticleSearch()
    success_rate = await tester.run_all_tests()

    # Check if we met the success criteria
    target_rate = 80.0
    if success_rate >= target_rate:
        print(f"\n[TEST PASSED]: Achieved {success_rate:.1f}% success rate (target: {target_rate}%)")
    else:
        print(f"\n[TEST FAILED]: Only {success_rate:.1f}% success rate (target: {target_rate}%)")

    return success_rate >= target_rate


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)