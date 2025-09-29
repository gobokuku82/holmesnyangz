"""
Predefined Test Cases for Real Estate Chatbot
Automated testing with pre-configured queries
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Import test config first to set up paths
from test_config import TestConfig, format_result, print_section_header

# Setup logging
TestConfig.setup_logging(verbose=False)

# Now import supervisor and search agent after paths are configured
from supervisor.supervisor import RealEstateSupervisor
from subgraphs.search_agent import SearchAgent


@dataclass
class TestCase:
    """Test case definition"""
    id: str
    category: str
    query: str
    expected_intent: str
    expected_agents: List[str]
    description: str
    validate_fields: List[str] = None


class PredefinedTester:
    """Automated test runner with predefined test cases"""

    def __init__(self):
        self.supervisor = None
        self.test_cases = self._define_test_cases()
        self.results = []
        self.session_id = f"automated_test_{int(time.time())}"

    def _define_test_cases(self) -> List[TestCase]:
        """Define all test cases"""
        return [
            # Search Intent Tests
            TestCase(
                id="TC001",
                category="검색",
                query="강남구 아파트 매매 시세 알려줘",
                expected_intent="search",
                expected_agents=["search_agent"],
                description="기본 부동산 시세 검색",
                validate_fields=["final_response", "response_type"]
            ),

            TestCase(
                id="TC002",
                category="검색",
                query="서초구 30평대 전세 매물 찾아줘",
                expected_intent="search",
                expected_agents=["search_agent"],
                description="조건부 매물 검색",
                validate_fields=["final_response", "collection_keywords"]
            ),

            # Legal Intent Tests
            TestCase(
                id="TC003",
                category="법률",
                query="부동산 계약시 주의사항은?",
                expected_intent="legal",
                expected_agents=["search_agent"],
                description="법률 정보 검색",
                validate_fields=["final_response", "intent"]
            ),

            TestCase(
                id="TC004",
                category="법률",
                query="양도소득세 계산 방법 알려줘",
                expected_intent="legal",
                expected_agents=["search_agent"],
                description="세금 관련 법률 정보",
                validate_fields=["final_response"]
            ),

            # Loan Intent Tests
            TestCase(
                id="TC005",
                category="대출",
                query="주택담보대출 금리 비교해줘",
                expected_intent="loan",
                expected_agents=["search_agent"],
                description="대출 금리 비교",
                validate_fields=["final_response", "collection_keywords"]
            ),

            TestCase(
                id="TC006",
                category="대출",
                query="신혼부부 전세자금대출 조건은?",
                expected_intent="loan",
                expected_agents=["search_agent"],
                description="특정 대출 상품 조회",
                validate_fields=["final_response"]
            ),

            # Regulation Intent Tests
            TestCase(
                id="TC007",
                category="규정",
                query="LTV DTI 규제 현황 알려줘",
                expected_intent="general",  # May be classified differently
                expected_agents=["search_agent"],
                description="금융 규제 정보",
                validate_fields=["final_response"]
            ),

            TestCase(
                id="TC008",
                category="규정",
                query="강남구 재건축 규제 정보",
                expected_intent="general",
                expected_agents=["search_agent"],
                description="지역 개발 규제",
                validate_fields=["final_response"]
            ),

            # Complex Query Tests
            TestCase(
                id="TC009",
                category="복합",
                query="서초구 전세 매물과 대출 정보 알려줘",
                expected_intent="search",  # Primary intent
                expected_agents=["search_agent"],
                description="복합 정보 요청",
                validate_fields=["final_response", "collection_keywords"]
            ),

            TestCase(
                id="TC010",
                category="복합",
                query="강남 부동산 투자 시 법적 주의사항과 세금 정보",
                expected_intent="legal",
                expected_agents=["search_agent"],
                description="투자 관련 복합 정보",
                validate_fields=["final_response"]
            ),

            # Analysis Intent Tests
            TestCase(
                id="TC011",
                category="분석",
                query="강남 부동산 시장 동향 분석해줘",
                expected_intent="analysis",
                expected_agents=["search_agent"],  # May include analysis_agent
                description="시장 분석 요청",
                validate_fields=["final_response"]
            ),

            # Recommendation Intent Tests
            TestCase(
                id="TC012",
                category="추천",
                query="신혼부부에게 적합한 지역 추천해줘",
                expected_intent="recommendation",
                expected_agents=["search_agent"],
                description="맞춤 추천 요청",
                validate_fields=["final_response"]
            ),
        ]

    async def initialize(self):
        """Initialize the supervisor and agents"""
        try:
            # Get LLM context from TestConfig
            self.llm_context = TestConfig.get_llm_context()

            # Create agent context for testing
            self.agent_context = TestConfig.create_test_agent_context(
                chat_session_id=self.session_id
            )

            # Initialize supervisor with LLM context
            self.supervisor = RealEstateSupervisor(
                llm_context=self.llm_context
            )
            print("[OK] System initialized with LLMContext")
            return True
        except Exception as e:
            print(f"[ERROR] Initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def run_test_case(self, test_case: TestCase) -> Dict[str, Any]:
        """
        Run a single test case

        Args:
            test_case: Test case to run

        Returns:
            Test result dictionary
        """
        print(f"\n[TEST] [{test_case.id}] {test_case.description}")
        print(f"   Query: {test_case.query}")

        start_time = time.time()
        result = {
            "test_id": test_case.id,
            "category": test_case.category,
            "query": test_case.query,
            "status": "pending"
        }

        try:
            # Process query with LLM context
            response = await self.supervisor.process_query(
                query=test_case.query,
                session_id=self.session_id,
                llm_context=self.llm_context  # Pass the LLM context
            )

            execution_time = time.time() - start_time

            # Validate response
            validation_results = self._validate_response(response, test_case)

            # Determine test status
            test_passed = all(validation_results.values())

            result.update({
                "status": "passed" if test_passed else "failed",
                "response": response,
                "execution_time": execution_time,
                "validation": validation_results
            })

            # Display result
            status_icon = "[PASS]" if test_passed else "[FAIL]"
            print(f"   Result: {status_icon} ({execution_time:.2f}s)")

            if not test_passed:
                failed_checks = [k for k, v in validation_results.items() if not v]
                print(f"   Failed checks: {', '.join(failed_checks)}")

        except Exception as e:
            result.update({
                "status": "error",
                "error": str(e),
                "execution_time": time.time() - start_time
            })
            print(f"   Result: [ERROR] - {str(e)[:50]}")

        return result

    def _validate_response(
        self,
        response: Dict[str, Any],
        test_case: TestCase
    ) -> Dict[str, bool]:
        """
        Validate response against expected values

        Args:
            response: Response from supervisor
            test_case: Test case with expectations

        Returns:
            Validation results
        """
        validations = {}

        # Check if response is not None
        validations["response_exists"] = response is not None

        # Check required fields
        if test_case.validate_fields:
            for field in test_case.validate_fields:
                if field in response or self._nested_field_exists(response, field):
                    validations[f"field_{field}"] = True
                else:
                    validations[f"field_{field}"] = False

        # Check response type
        if "type" in response:
            validations["has_type"] = True
        else:
            validations["has_type"] = isinstance(response, dict)

        # Check for data content
        if isinstance(response, dict):
            # Check in final_response if it exists
            final_resp = response.get("final_response", response)
            has_content = bool(
                final_resp.get("content") if isinstance(final_resp, dict) else False or
                final_resp.get("data") if isinstance(final_resp, dict) else False or
                final_resp.get("summary") if isinstance(final_resp, dict) else False
            )
            validations["has_content"] = has_content

        return validations

    def _nested_field_exists(self, data: Dict, field: str) -> bool:
        """Check if a field exists in nested dictionary"""
        if not isinstance(data, dict):
            return False

        if field in data:
            return True

        for value in data.values():
            if isinstance(value, dict):
                if self._nested_field_exists(value, field):
                    return True

        return False

    async def run_all_tests(self, categories: List[str] = None):
        """
        Run all test cases or specific categories

        Args:
            categories: List of categories to test (None for all)
        """
        print_section_header("AUTOMATED TEST SUITE")
        TestConfig.print_config()

        # Filter test cases by category if specified
        test_cases = self.test_cases
        if categories:
            test_cases = [tc for tc in test_cases if tc.category in categories]

        print(f"\nRunning {len(test_cases)} test cases")
        print("="*60)

        # Initialize system
        if not await self.initialize():
            print("Failed to initialize system")
            return

        # Run each test case
        self.results = []
        for test_case in test_cases:
            result = await self.run_test_case(test_case)
            self.results.append(result)

            # Small delay between tests
            await asyncio.sleep(0.5)

        # Display summary
        self._display_summary()

    def _display_summary(self):
        """Display test summary"""
        print_section_header("TEST SUMMARY")

        if not self.results:
            print("No test results available")
            return

        # Calculate statistics
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "passed")
        failed = sum(1 for r in self.results if r["status"] == "failed")
        errors = sum(1 for r in self.results if r["status"] == "error")

        # Display overall stats
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")
        print(f"Errors: {errors} ({errors/total*100:.1f}%)")

        # Calculate timing stats
        valid_times = [r["execution_time"] for r in self.results if "execution_time" in r]
        if valid_times:
            avg_time = sum(valid_times) / len(valid_times)
            min_time = min(valid_times)
            max_time = max(valid_times)
            print(f"\nTiming Statistics:")
            print(f"   Average: {avg_time:.2f}s")
            print(f"   Min: {min_time:.2f}s")
            print(f"   Max: {max_time:.2f}s")

        # Display failures
        if failed > 0 or errors > 0:
            print("\nFailed/Error Tests:")
            for result in self.results:
                if result["status"] in ["failed", "error"]:
                    print(f"   [{result['test_id']}] {result['query'][:50]}")
                    if result["status"] == "error":
                        print(f"      Error: {result.get('error', 'Unknown')[:100]}")
                    else:
                        failed_validations = [
                            k for k, v in result.get("validation", {}).items() if not v
                        ]
                        if failed_validations:
                            print(f"      Failed: {', '.join(failed_validations)}")

        # Display by category
        print("\nResults by Category:")
        categories = {}
        for result in self.results:
            cat = result["category"]
            if cat not in categories:
                categories[cat] = {"passed": 0, "failed": 0, "error": 0}
            categories[cat][result["status"]] += 1

        for cat, stats in categories.items():
            total_cat = sum(stats.values())
            passed_cat = stats["passed"]
            print(f"   {cat}: {passed_cat}/{total_cat} passed")

    def save_results(self, filename: str = None):
        """Save test results to file"""
        if not filename:
            filename = f"test_results_{self.session_id}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"\nResults saved to: {filename}")


async def run_category_tests(category: str):
    """Run tests for a specific category"""
    tester = PredefinedTester()
    await tester.run_all_tests(categories=[category])


async def run_quick_test():
    """Run a quick smoke test with essential cases"""
    print_section_header("QUICK SMOKE TEST")

    quick_cases = [
        TestCase(
            id="QUICK001",
            category="검색",
            query="강남구 아파트 시세",
            expected_intent="search",
            expected_agents=["search_agent"],
            description="Basic search test",
            validate_fields=["final_response"]
        ),
        TestCase(
            id="QUICK002",
            category="법률",
            query="부동산 계약 주의사항",
            expected_intent="legal",
            expected_agents=["search_agent"],
            description="Basic legal test",
            validate_fields=["final_response"]
        ),
        TestCase(
            id="QUICK003",
            category="대출",
            query="주택담보대출 금리",
            expected_intent="loan",
            expected_agents=["search_agent"],
            description="Basic loan test",
            validate_fields=["final_response"]
        ),
    ]

    tester = PredefinedTester()
    tester.test_cases = quick_cases
    await tester.run_all_tests()


def main():
    """Main entry point"""
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "quick":
            # Quick smoke test
            asyncio.run(run_quick_test())
        elif command == "category" and len(sys.argv) > 2:
            # Test specific category
            category = sys.argv[2]
            asyncio.run(run_category_tests(category))
        elif command == "openai":
            # Run with OpenAI
            TestConfig.set_llm_mode("openai")
            tester = PredefinedTester()
            asyncio.run(tester.run_all_tests())
        elif command == "mock":
            # Run with Mock
            TestConfig.set_llm_mode("mock")
            tester = PredefinedTester()
            asyncio.run(tester.run_all_tests())
        else:
            print("Usage:")
            print("  python test_predefined.py          # Run all tests")
            print("  python test_predefined.py quick    # Quick smoke test")
            print("  python test_predefined.py category <name>  # Test specific category")
            print("  python test_predefined.py openai   # Run with OpenAI")
            print("  python test_predefined.py mock     # Run with Mock")
    else:
        # Run all tests with default settings
        tester = PredefinedTester()
        asyncio.run(tester.run_all_tests())


if __name__ == "__main__":
    main()