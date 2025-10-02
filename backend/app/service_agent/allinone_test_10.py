"""
All-in-One Integration Test (10 queries) - Quick comprehensive test
질문-과정-답변 전체 로깅 및 리포트 생성
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import time


class DateTimeEncoder(json.JSONEncoder):
    """JSON Encoder that handles datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Path setup
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor
from app.service_agent.core.context import create_default_llm_context
from app.service.core.separated_states import MainSupervisorState

# Setup logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AllInOneTest:
    """10개 쿼리 통합 테스트 - 빠른 검증용"""

    def __init__(self):
        self.queries = [
            # 법률 (3개)
            {"id": "legal_01", "category": "법률", "query": "전세금 5% 인상이 가능한가요?", "expected_intent": "LEGAL_CONSULT"},
            {"id": "legal_02", "category": "법률", "query": "보증금 반환 안 받으면 어떻게 하나요?", "expected_intent": "LEGAL_CONSULT"},
            {"id": "legal_03", "category": "법률", "query": "소액임차인 최우선변제금액은 얼마인가요?", "expected_intent": "LEGAL_CONSULT"},

            # 시세 (2개)
            {"id": "market_01", "category": "시세", "query": "강남구 아파트 시세 알려주세요", "expected_intent": "MARKET_INFO"},
            {"id": "market_02", "category": "시세", "query": "서초구 전세 평균 가격은?", "expected_intent": "MARKET_INFO"},

            # 대출 (2개)
            {"id": "loan_01", "category": "대출", "query": "주택담보대출 금리 비교해주세요", "expected_intent": "LOAN_INFO"},
            {"id": "loan_02", "category": "대출", "query": "전세자금대출 조건은?", "expected_intent": "LOAN_INFO"},

            # 복합 (3개)
            {"id": "complex_01", "category": "복합", "query": "강남 아파트 매매가격과 관련 법률 알려주세요", "expected_intent": "COMPREHENSIVE"},
            {"id": "complex_02", "category": "복합", "query": "전세 대출 받을 때 주의사항과 금리는?", "expected_intent": "COMPREHENSIVE"},
            {"id": "complex_03", "category": "복합", "query": "서초구 아파트 시세와 대출 한도 알려주세요", "expected_intent": "COMPREHENSIVE"}
        ]

        # LLM Context
        print("\n[1/4] Initializing LLM Context...")
        self.llm_context = create_default_llm_context()

        # TeamSupervisor
        print("[2/4] Initializing TeamSupervisor...")
        self.supervisor = TeamBasedSupervisor(llm_context=self.llm_context)

        # Results
        self.results = []
        self.stats = {
            "total": 10,
            "success": 0,
            "failed": 0,
            "by_category": {},
            "total_time": 0
        }

    async def run_single_test(self, query_data: Dict, index: int, total: int) -> Dict:
        """단일 쿼리 테스트"""
        query_id = query_data['id']
        query = query_data['query']
        category = query_data['category']

        print(f"\n[{index}/{total}] {query_id}")
        print(f"  Query: {query}")

        result = {
            "query_id": query_id,
            "category": category,
            "query": query,
            "expected_intent": query_data.get('expected_intent'),
            "timestamp": datetime.now().isoformat()
        }

        start_time = time.time()
        process_steps = []

        try:
            # Create initial state
            initial_state = MainSupervisorState(
                query=query,
                session_id=f"test_{query_id}",
                user_id=None,
                status="pending",
                current_phase="initialization",
                planning_state=None,
                execution_plan=None,
                active_teams=[],
                completed_teams=[],
                failed_teams=[],
                team_results={},
                aggregated_results={},
                final_response=None,
                error_log=[],
                start_time=None,
                end_time=None,
                total_execution_time=None,
                metadata={"query_id": query_id}
            )

            process_steps.append({"step": "1. Initial State Created", "time": 0})

            # Execute
            final_state = await self.supervisor.app.ainvoke(initial_state)
            execution_time = time.time() - start_time

            # Parse results
            planning_state = final_state.get('planning_state', {})
            analyzed_intent = planning_state.get('analyzed_intent', {})
            completed_teams = final_state.get('completed_teams', [])
            final_response = final_state.get('final_response', {})

            # Extract answer
            if isinstance(final_response, dict):
                answer_text = final_response.get('answer', '')
            else:
                answer_text = str(final_response)

            process_steps.append({
                "step": "2. Planning - Intent Analysis",
                "intent": analyzed_intent.get('intent_type', 'N/A'),
                "confidence": analyzed_intent.get('confidence', 0)
            })

            process_steps.append({
                "step": "3. Team Execution",
                "teams": completed_teams
            })

            process_steps.append({
                "step": "4. Response Generation",
                "answer_length": len(answer_text)
            })

            # Extract only serializable data and handle potential datetime objects
            def make_serializable(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: make_serializable(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [make_serializable(item) for item in obj]
                else:
                    return obj

            serializable_response = {
                "answer": answer_text,
                "sources": make_serializable(final_response.get('sources', [])) if isinstance(final_response, dict) else [],
                "metadata": make_serializable(final_response.get('metadata', {})) if isinstance(final_response, dict) else {}
            }

            # Safely update result with JSON-serializable data
            try:
                # Test JSON serialization before updating
                test_data = {
                    "status": "success",
                    "execution_time": execution_time,
                    "actual_intent": analyzed_intent.get('intent_type'),
                    "intent_confidence": analyzed_intent.get('confidence', 0),
                    "teams_executed": completed_teams,
                    "response_preview": answer_text[:200] if answer_text else "",
                    "full_response": serializable_response,
                    "process_steps": process_steps
                }
                # Test serialization
                json.dumps(test_data, cls=DateTimeEncoder)
                # If successful, update result
                result.update(test_data)
            except Exception as json_error:
                # Fallback to minimal success result
                result.update({
                    "status": "success",
                    "execution_time": execution_time,
                    "actual_intent": str(analyzed_intent.get('intent_type', 'unknown')),
                    "teams_executed": list(completed_teams) if completed_teams else [],
                    "response_preview": "Response generated but serialization failed"
                })

            print(f"  [OK] {execution_time:.2f}s | Intent: {analyzed_intent.get('intent_type', 'N/A')} | Teams: {', '.join(completed_teams)}")

        except Exception as e:
            # Try to create a JSON-safe error result
            try:
                result.update({
                    "status": "failed",
                    "error": str(e),
                    "execution_time": time.time() - start_time,
                    "process_steps": process_steps
                })
            except:
                # Fallback if even the error handling fails
                result = {
                    "query_id": query_id,
                    "category": category,
                    "query": query,
                    "status": "failed",
                    "error": "JSON serialization error",
                    "execution_time": time.time() - start_time
                }
            print(f"  [FAIL] {e}")

        return result

    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("\n" + "="*80)
        print("ALL-IN-ONE INTEGRATION TEST (10 QUERIES)")
        print("="*80)
        print("[3/4] Running tests...")

        start_time = time.time()

        for i, query_data in enumerate(self.queries, 1):
            result = await self.run_single_test(query_data, i, 10)
            self.results.append(result)

            if result['status'] == 'success':
                self.stats['success'] += 1
            else:
                self.stats['failed'] += 1

            category = result['category']
            self.stats['by_category'][category] = self.stats['by_category'].get(category, 0) + 1

            await asyncio.sleep(0.2)

        self.stats['total_time'] = time.time() - start_time
        self.stats['average_time'] = self.stats['total_time'] / 10

        print("\n" + "="*80)
        print("TEST COMPLETED")
        print("="*80)
        print(f"Total: {self.stats['total']}")
        print(f"Success: {self.stats['success']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Total Time: {self.stats['total_time']:.2f}s")
        print(f"Average Time: {self.stats['average_time']:.2f}s/query")

    def save_reports(self):
        """JSON 및 Markdown 리포트 저장"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        reports_dir = Path(__file__).parent / "reports"
        reports_dir.mkdir(exist_ok=True)

        # JSON 리포트
        json_file = reports_dir / f"allinone_test_10_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                "test_info": {
                    "total_queries": self.stats['total'],
                    "success_count": self.stats['success'],
                    "failed_count": self.stats['failed'],
                    "total_time": self.stats['total_time'],
                    "average_time": self.stats['average_time'],
                    "by_category": self.stats['by_category']
                },
                "results": self.results
            }, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)

        print(f"\n[4/4] JSON Report: {json_file.name}")

        # Markdown 리포트
        md_file = reports_dir / f"allinone_test_10_{timestamp}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write("# All-in-One Integration Test Report\n\n")
            f.write(f"**Test Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Queries**: 10\n\n")

            # Summary
            f.write("## Summary\n\n")
            f.write(f"| Metric | Value |\n")
            f.write(f"|--------|-------|\n")
            f.write(f"| Total Queries | {self.stats['total']} |\n")
            f.write(f"| Success | {self.stats['success']} |\n")
            f.write(f"| Failed | {self.stats['failed']} |\n")
            f.write(f"| Total Time | {self.stats['total_time']:.2f}s |\n")
            f.write(f"| Average Time | {self.stats['average_time']:.2f}s/query |\n\n")

            # By Category
            f.write("## Results by Category\n\n")
            for cat, count in self.stats['by_category'].items():
                success = sum(1 for r in self.results if r['category'] == cat and r['status'] == 'success')
                f.write(f"- **{cat}**: {success}/{count} success\n")

            # Details
            f.write("\n## Detailed Results\n\n")

            for result in self.results:
                f.write(f"### {result['query_id']}: {result['category']}\n\n")
                f.write(f"**Query**: {result['query']}\n\n")

                if result['status'] == 'success':
                    f.write(f"**Time**: {result['execution_time']:.2f}s\n\n")
                    f.write(f"**Intent**: {result['actual_intent']} ({result['intent_confidence']:.0%})\n\n")
                    f.write(f"**Teams**: {', '.join(result['teams_executed'])}\n\n")

                    f.write(f"**Process**:\n")
                    for step in result['process_steps']:
                        f.write(f"- {step['step']}\n")

                    f.write(f"\n**Answer** (preview):\n```\n{result['response_preview']}\n```\n\n")

                else:
                    f.write(f"**Status**: FAILED\n")
                    f.write(f"**Error**: {result['error']}\n\n")

                f.write("---\n\n")

        print(f"      Markdown Report: {md_file.name}")


async def main():
    """메인 실행"""
    test = AllInOneTest()
    await test.run_all_tests()
    test.save_reports()
    print("\n[OK] Test completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
