"""
All-in-One Integration Test (25 queries)
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
    """25개 쿼리 통합 테스트 - 현실적인 완료 시간"""

    def __init__(self):
        self.queries = self._generate_test_queries()

        # LLM Context
        print("\n[1/4] Initializing LLM Context...")
        self.llm_context = create_default_llm_context()

        # TeamSupervisor
        print("[2/4] Initializing TeamSupervisor...")
        self.supervisor = TeamBasedSupervisor(llm_context=self.llm_context)

        # Results
        self.results = []
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "by_category": {},
            "total_time": 0
        }

    def _generate_test_queries(self) -> List[Dict]:
        """25개 대표 쿼리 생성"""
        queries = []

        # 법률 (7개)
        legal_queries = [
            "전세금 5% 인상이 가능한가요?",
            "임대차 계약 갱신 거부할 수 있나요?",
            "보증금 반환 안 받으면 어떻게 하나요?",
            "전세 계약 중 집주인이 바뀌면 어떻게 되나요?",
            "월세를 전세로 전환할 수 있나요?",
            "전입신고를 안 하면 어떤 문제가 있나요?",
            "소액임차인 최우선변제금액은 얼마인가요?"
        ]

        for i, q in enumerate(legal_queries, 1):
            queries.append({
                "id": f"legal_{i:02d}",
                "category": "법률",
                "query": q,
                "expected_intent": "LEGAL_CONSULT"
            })

        # 시세 (6개)
        market_queries = [
            "강남구 아파트 시세 알려주세요",
            "서초구 전세 평균 가격은?",
            "송파구 매매가 동향은?",
            "마포구 아파트 월세 시세는?",
            "용산구 부동산 가격 추이는?",
            "성동구 아파트 매매 시세"
        ]

        for i, q in enumerate(market_queries, 1):
            queries.append({
                "id": f"market_{i:02d}",
                "category": "시세",
                "query": q,
                "expected_intent": "MARKET_INFO"
            })

        # 대출 (6개)
        loan_queries = [
            "주택담보대출 금리 비교해주세요",
            "전세자금대출 조건은?",
            "신용대출과 주택담보대출 차이는?",
            "대출 한도는 어떻게 정해지나요?",
            "주담대 이자율 낮은 은행은?",
            "전세대출 받을 때 준비서류는?"
        ]

        for i, q in enumerate(loan_queries, 1):
            queries.append({
                "id": f"loan_{i:02d}",
                "category": "대출",
                "query": q,
                "expected_intent": "LOAN_INFO"
            })

        # 복합 (6개)
        complex_queries = [
            "강남 아파트 매매가격과 관련 법률 알려주세요",
            "전세 대출 받을 때 주의사항과 금리는?",
            "서초구 아파트 시세와 대출 한도 알려주세요",
            "전세금 반환 보증과 보험 상품 비교",
            "신혼부부 전세자금대출과 적용 조건",
            "강남 아파트 투자 시 세금과 대출 전략"
        ]

        for i, q in enumerate(complex_queries, 1):
            queries.append({
                "id": f"complex_{i:02d}",
                "category": "복합",
                "query": q,
                "expected_intent": "COMPREHENSIVE"
            })

        return queries

    async def run_single_test(self, query_data: Dict, index: int, total: int) -> Dict:
        """단일 쿼리 테스트 (상세 로깅)"""
        query_id = query_data['id']
        query = query_data['query']
        category = query_data['category']

        print(f"\n[{index}/{total}] Testing: {query_id}")
        print(f"  Query: {query}")
        print(f"  Started at: {time.strftime('%H:%M:%S')}")

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

            process_steps.append({
                "step": "1. Initial State Created",
                "time": 0
            })

            # Execute
            print(f"  -> Executing workflow...")
            step_start = time.time()
            final_state = await self.supervisor.app.ainvoke(initial_state)
            execution_time = time.time() - start_time

            # Parse planning results
            planning_state = final_state.get('planning_state', {})
            analyzed_intent = planning_state.get('analyzed_intent', {})

            process_steps.append({
                "step": "2. Planning Agent - Intent Analysis",
                "time": time.time() - step_start,
                "intent": analyzed_intent.get('intent_type', 'N/A'),
                "confidence": analyzed_intent.get('confidence', 0),
                "keywords": analyzed_intent.get('keywords', [])
            })

            # Parse team execution
            step_start = time.time()
            active_teams = final_state.get('active_teams', [])
            completed_teams = final_state.get('completed_teams', [])

            process_steps.append({
                "step": "3. Team Execution",
                "time": time.time() - step_start,
                "active_teams": active_teams,
                "completed_teams": completed_teams
            })

            # Team results
            team_results = final_state.get('team_results', {})
            team_summary = {}
            for team_name, team_data in team_results.items():
                if isinstance(team_data, dict):
                    team_summary[team_name] = {
                        "status": team_data.get('status', 'unknown'),
                        "data_count": len(str(team_data.get('collected_data', {})))
                    }

            process_steps.append({
                "step": "4. Team Results Collection",
                "teams": team_summary
            })

            # Final response
            final_response = final_state.get('final_response')
            response_text = ""
            response_json = None

            if final_response:
                if isinstance(final_response, dict):
                    # Try to extract answer from JSON
                    answer = final_response.get('answer', '')
                    response_text = str(answer) if answer else str(final_response)
                    response_json = final_response
                else:
                    response_text = str(final_response)

            process_steps.append({
                "step": "5. Response Generation",
                "response_length": len(response_text),
                "response_type": final_response.get('type') if isinstance(final_response, dict) else 'unknown'
            })

            result.update({
                "status": "success",
                "execution_time": execution_time,
                "actual_intent": analyzed_intent.get('intent_type'),
                "intent_confidence": analyzed_intent.get('confidence', 0),
                "teams_executed": completed_teams,
                "team_results": team_summary,
                "response_preview": response_text[:200],
                "full_response": response_json,
                "process_steps": process_steps
            })

            print(f"  [OK] Success ({execution_time:.2f}s)")
            print(f"    Intent: {analyzed_intent.get('intent_type', 'N/A')} ({analyzed_intent.get('confidence', 0):.0%})")
            print(f"    Teams: {', '.join(completed_teams) if completed_teams else 'None'}")
            print(f"    Answer: {response_text[:80]}...")

        except Exception as e:
            result.update({
                "status": "failed",
                "error": str(e),
                "execution_time": time.time() - start_time,
                "process_steps": process_steps
            })
            print(f"  [FAIL] Failed: {e}")

        return result

    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("\n" + "="*80)
        print("ALL-IN-ONE INTEGRATION TEST (25 QUERIES)")
        print("="*80)
        print("[3/4] Running tests...")

        total = len(self.queries)
        self.stats['total'] = total
        start_time = time.time()

        for i, query_data in enumerate(self.queries, 1):
            result = await self.run_single_test(query_data, i, total)
            self.results.append(result)

            # Update stats
            if result['status'] == 'success':
                self.stats['success'] += 1
            else:
                self.stats['failed'] += 1

            category = result['category']
            self.stats['by_category'][category] = self.stats['by_category'].get(category, 0) + 1

            # Small delay
            await asyncio.sleep(0.3)

        self.stats['total_time'] = time.time() - start_time
        self.stats['average_time'] = self.stats['total_time'] / total

        print("\n" + "="*80)
        print("TEST COMPLETED")
        print("="*80)
        print(f"Total: {self.stats['total']}")
        print(f"Success: {self.stats['success']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Total Time: {self.stats['total_time']:.2f}s")
        print(f"Average Time: {self.stats['average_time']:.2f}s/query")
        print(f"\nBy Category:")
        for cat, count in self.stats['by_category'].items():
            print(f"  {cat}: {count}")

    def save_reports(self):
        """JSON 및 Markdown 리포트 저장"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        reports_dir = Path(__file__).parent / "reports"
        reports_dir.mkdir(exist_ok=True)

        # JSON 리포트
        json_file = reports_dir / f"allinone_test_25_{timestamp}.json"
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
            }, f, ensure_ascii=False, indent=2)

        print(f"\n[4/4] JSON Report saved: {json_file}")

        # Markdown 리포트
        md_file = reports_dir / f"allinone_test_25_{timestamp}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write("# All-in-One Integration Test Report (25 Queries)\n\n")
            f.write(f"**Test Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Summary
            f.write("## Summary\n\n")
            f.write(f"- **Total Queries**: {self.stats['total']}\n")
            f.write(f"- **Success**: {self.stats['success']}\n")
            f.write(f"- **Failed**: {self.stats['failed']}\n")
            f.write(f"- **Total Time**: {self.stats['total_time']:.2f}s\n")
            f.write(f"- **Average Time**: {self.stats['average_time']:.2f}s/query\n\n")

            f.write("### By Category\n\n")
            for cat, count in self.stats['by_category'].items():
                success = sum(1 for r in self.results if r['category'] == cat and r['status'] == 'success')
                f.write(f"- **{cat}**: {count} queries ({success} success)\n")

            # Detailed Results
            f.write("\n## Detailed Results\n\n")

            for result in self.results:
                f.write(f"### [{result['query_id']}] {result['category']}\n\n")
                f.write(f"**Query**: {result['query']}\n\n")
                f.write(f"**Status**: {result['status']}\n\n")

                if result['status'] == 'success':
                    f.write(f"**Execution Time**: {result['execution_time']:.2f}s\n\n")
                    f.write(f"**Intent Analysis**:\n")
                    f.write(f"- Type: {result['actual_intent']}\n")
                    f.write(f"- Confidence: {result['intent_confidence']:.0%}\n\n")

                    f.write(f"**Teams Executed**: {', '.join(result['teams_executed']) if result['teams_executed'] else 'None'}\n\n")

                    f.write(f"**Process Steps**:\n")
                    for step in result['process_steps']:
                        f.write(f"1. {step['step']}\n")

                    f.write(f"\n**Response Preview**:\n")
                    f.write(f"```\n{result['response_preview']}\n```\n\n")

                else:
                    f.write(f"**Error**: {result['error']}\n\n")

                f.write("---\n\n")

        print(f"      Markdown Report saved: {md_file}")


async def main():
    """메인 실행 함수"""
    test = AllInOneTest()
    await test.run_all_tests()
    test.save_reports()
    print("\n[OK] All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
