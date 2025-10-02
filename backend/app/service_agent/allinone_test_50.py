"""
All-in-One Integration Test (50 queries)
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
    level=logging.WARNING,  # Suppress verbose logs
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AllInOneTest:
    """50개 쿼리 통합 테스트"""

    def __init__(self):
        # Test queries (50개)
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
        """50개 테스트 쿼리 생성"""
        queries = []

        # 법률 (10개)
        legal_queries = [
            "전세금 5% 인상이 가능한가요?",
            "임대차 계약 갱신 거부할 수 있나요?",
            "보증금 반환 안 받으면 어떻게 하나요?",
            "전세 계약 중 집주인이 바뀌면 어떻게 되나요?",
            "월세를 전세로 전환할 수 있나요?",
            "계약 기간 전 퇴거 시 위약금은?",
            "전입신고를 안 하면 어떤 문제가 있나요?",
            "보증금 증액 요구를 거부할 수 있나요?",
            "확정일자를 받지 않으면 어떻게 되나요?",
            "소액임차인 최우선변제금액은 얼마인가요?"
        ]

        for i, q in enumerate(legal_queries, 1):
            queries.append({
                "id": f"legal_{i:02d}",
                "category": "법률",
                "query": q,
                "expected_intent": "LEGAL_CONSULT"
            })

        # 시세 (10개)
        market_queries = [
            "강남구 아파트 시세 알려주세요",
            "서초구 전세 평균 가격은?",
            "송파구 매매가 동향은?",
            "마포구 아파트 월세 시세는?",
            "용산구 부동산 가격 추이는?",
            "성동구 아파트 매매 시세",
            "강남 래미안 아파트 가격은?",
            "헬리오시티 전세가는 얼마인가요?",
            "최근 강남 아파트 시세 변동률은?",
            "서초구 아파트 평당 가격은?"
        ]

        for i, q in enumerate(market_queries, 1):
            queries.append({
                "id": f"market_{i:02d}",
                "category": "시세",
                "query": q,
                "expected_intent": "MARKET_INQUIRY"
            })

        # 대출 (10개)
        loan_queries = [
            "주택담보대출 금리가 얼마인가요?",
            "전세자금대출 조건은?",
            "신용대출 한도는 얼마까지?",
            "버팀목 전세자금대출 신청 방법은?",
            "LTV가 무엇인가요?",
            "DTI 계산 방법은?",
            "주택담보대출 최저 금리 은행은?",
            "대출 한도 계산 방법은?",
            "변동금리 vs 고정금리 어떤 게 나을까요?",
            "생애최초 주택구매 대출 혜택은?"
        ]

        for i, q in enumerate(loan_queries, 1):
            queries.append({
                "id": f"loan_{i:02d}",
                "category": "대출",
                "query": q,
                "expected_intent": "LOAN_CONSULT"
            })

        # 복합 (20개)
        complex_queries = [
            "강남구 아파트 전세 계약 시 법적으로 주의할 점은?",
            "서초구 전세 시세와 임차인 보호 조항 알려주세요",
            "전세금 5억 계약 시 확정일자 받는 방법은?",
            "강남 아파트 전세 시세와 보증금 반환 보장 방법은?",
            "전세 계약 전 등기부등본 확인 방법과 시세 조회",
            "강남구 아파트 매매가와 주택담보대출 한도는?",
            "서초구 아파트 시세와 전세자금대출 금리 비교",
            "15억 아파트 매매 시 대출 가능 금액은?",
            "강남 아파트 전세 시세와 버팀목 대출 한도",
            "아파트 구매 시 LTV 70% 적용하면 대출 얼마?",
            "전세 계약 시 전세자금대출 받는 방법과 법적 절차는?",
            "임대차 계약서와 대출 서류 작성 순서는?",
            "보증금 반환 보증보험 가입과 대출 관계는?",
            "전세금 반환 소송 중 대출 상환은 어떻게?",
            "강남구 아파트 15억 전세 계약과 대출, 법적 주의사항 모두 알려주세요",
            "서초구 아파트 매매 시 시세, 대출 조건, 계약 절차 전체 안내",
            "전세 5억 계약 시 적정 시세인지, 대출 가능 여부, 법적 보호 방법은?",
            "신혼부부 첫 주택 구매 시 시세, 우대 대출, 계약 주의사항",
            "전세 계약 갱신 시 시세 반영률, 대출 연장, 법적 권리는?",
            "생애최초 주택 구매 시 시세 적정성, 우대 대출, 특약 조항"
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
        """단일 쿼리 테스트"""
        query_id = query_data['id']
        query = query_data['query']
        category = query_data['category']

        print(f"\n[{index}/{total}] Testing: {query_id}")
        print(f"  Query: {query[:60]}...")

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
            step_start = time.time()
            final_state = await self.supervisor.app.ainvoke(initial_state)
            execution_time = time.time() - start_time

            # Parse results
            planning_state = final_state.get('planning_state', {})
            analyzed_intent = planning_state.get('analyzed_intent', {})

            process_steps.append({
                "step": "2. Planning Agent - Intent Analysis",
                "time": time.time() - step_start,
                "intent": analyzed_intent.get('intent_type', 'N/A'),
                "confidence": analyzed_intent.get('confidence', 0),
                "keywords": analyzed_intent.get('keywords', [])
            })

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
            response_summary = "No response"

            if final_response:
                if isinstance(final_response, dict):
                    answer = final_response.get('answer', '')
                    response_summary = str(answer)[:200] if answer else "Empty answer"
                else:
                    response_summary = str(final_response)[:200]

            process_steps.append({
                "step": "5. Response Generation",
                "response_preview": response_summary
            })

            result.update({
                "status": "success",
                "execution_time": execution_time,
                "actual_intent": analyzed_intent.get('intent_type'),
                "intent_confidence": analyzed_intent.get('confidence', 0),
                "teams_executed": completed_teams,
                "team_results": team_summary,
                "response_preview": response_summary,
                "process_steps": process_steps
            })

            print(f"  [OK] Success ({execution_time:.2f}s)")
            print(f"    Intent: {analyzed_intent.get('intent_type', 'N/A')} ({analyzed_intent.get('confidence', 0):.0%})")
            print(f"    Teams: {', '.join(completed_teams) if completed_teams else 'None'}")

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
        print("ALL-IN-ONE INTEGRATION TEST (50 QUERIES)")
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
        print(f"Success: {self.stats['success']} ({self.stats['success']/total*100:.1f}%)")
        print(f"Failed: {self.stats['failed']}")
        print(f"Total Time: {self.stats['total_time']:.2f}s")
        print(f"Average Time: {self.stats['average_time']:.2f}s")

    def save_reports(self):
        """리포트 저장"""
        print("\n[4/4] Generating reports...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reports_dir = Path(__file__).parent / "reports"
        reports_dir.mkdir(exist_ok=True)

        # JSON Report
        json_path = reports_dir / f"allinone_test_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "test_name": "All-in-One Integration Test (50 queries)",
                    "timestamp": timestamp,
                    "total_queries": self.stats['total']
                },
                "statistics": self.stats,
                "results": self.results
            }, f, ensure_ascii=False, indent=2)

        print(f"  [OK] JSON Report: {json_path}")

        # Markdown Report
        md_path = reports_dir / f"allinone_test_{timestamp}.md"
        self._generate_markdown_report(md_path)

        print(f"  [OK] Markdown Report: {md_path}")

        return json_path, md_path

    def _generate_markdown_report(self, output_path: Path):
        """마크다운 리포트 생성"""
        lines = []

        lines.append("# All-in-One Integration Test Report")
        lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        lines.append("## Summary Statistics\n")
        lines.append(f"- **Total Queries**: {self.stats['total']}")
        lines.append(f"- **Success**: {self.stats['success']} ({self.stats['success']/self.stats['total']*100:.1f}%)")
        lines.append(f"- **Failed**: {self.stats['failed']}")
        lines.append(f"- **Total Time**: {self.stats['total_time']:.2f}s")
        lines.append(f"- **Average Time**: {self.stats['average_time']:.2f}s\n")

        lines.append("### By Category\n")
        for category, count in self.stats['by_category'].items():
            lines.append(f"- **{category}**: {count} queries")

        lines.append("\n---\n")
        lines.append("## Detailed Results\n")

        for i, result in enumerate(self.results, 1):
            lines.append(f"### {i}. {result['query_id']} - {result['category']}\n")
            lines.append(f"**Question**: {result['query']}\n")
            lines.append(f"**Status**: {'[OK] Success' if result['status'] == 'success' else '[FAIL] Failed'}")
            lines.append(f"**Execution Time**: {result.get('execution_time', 0):.2f}s\n")

            if result['status'] == 'success':
                lines.append("**Process Steps**:\n")
                for step in result.get('process_steps', []):
                    step_name = step.get('step', 'Unknown')
                    lines.append(f"- {step_name}")

                    if 'intent' in step:
                        lines.append(f"  - Intent: {step['intent']} (confidence: {step.get('confidence', 0):.0%})")
                    if 'active_teams' in step:
                        teams = step.get('active_teams', [])
                        lines.append(f"  - Teams: {', '.join(teams) if teams else 'None'}")
                    if 'response_preview' in step:
                        lines.append(f"  - Response: {step['response_preview'][:100]}...")

                lines.append(f"\n**Answer**: {result.get('response_preview', 'N/A')[:300]}...\n")
            else:
                lines.append(f"\n**Error**: {result.get('error', 'Unknown error')}\n")

            lines.append("\n---\n")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))


async def main():
    """메인 실행 함수"""
    test = AllInOneTest()
    await test.run_all_tests()
    test.save_reports()

    print("\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
