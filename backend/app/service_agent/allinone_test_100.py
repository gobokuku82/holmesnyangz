"""
100 Query Comprehensive Test
질문-세부과정-답변 전체 프로세스 로깅 및 상세 리포트 생성
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
from app.service_agent.core.separated_states import MainSupervisorState
from app.service_agent.core.context import create_default_llm_context

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_100_queries.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ComprehensiveTestRunner:
    """100개 쿼리 종합 테스트 실행기"""

    def __init__(self):
        self.queries = []
        self.results = []
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'by_category': {},
            'by_intent': {},
            'total_time': 0,
            'average_time': 0
        }
        self.supervisor = None
        self.llm_context = None

    def load_queries(self, query_file="test_queries_100.json"):
        """쿼리 파일 로드"""
        query_path = Path(__file__).parent / query_file
        with open(query_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.queries = data['queries']
            self.stats['total'] = len(self.queries)
        print(f"\n[1/5] Loaded {len(self.queries)} test queries")

    async def initialize_supervisor(self):
        """Supervisor 초기화"""
        print("[2/5] Initializing LLM Context and TeamSupervisor...")
        self.llm_context = create_default_llm_context()
        self.supervisor = TeamBasedSupervisor(self.llm_context)
        print("      Initialization complete")

    async def run_single_test(self, query_data: Dict, index: int, total: int) -> Dict[str, Any]:
        """단일 쿼리 테스트 실행 및 상세 프로세스 로깅"""

        query_id = query_data['query_id']
        category = query_data['category']
        query = query_data['query']

        print(f"\n[{index}/{total}] {query_id}")
        print(f"  Query: {query}")
        print(f"  Category: {category} | Expected: {query_data.get('expected_intent')}")

        result = {
            "query_id": query_id,
            "category": category,
            "query": query,
            "expected_intent": query_data.get('expected_intent'),
            "timestamp": datetime.now().isoformat()
        }

        start_time = time.time()

        # 상세 프로세스 로깅
        process_log = {
            "phase_1_initialization": {},
            "phase_2_planning": {},
            "phase_3_team_execution": {},
            "phase_4_aggregation": {},
            "phase_5_response_generation": {}
        }

        try:
            # PHASE 1: 초기화
            process_log["phase_1_initialization"]["start_time"] = datetime.now().isoformat()
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
                metadata={"query_id": query_id, "test_index": index}
            )
            process_log["phase_1_initialization"]["status"] = "completed"

            # PHASE 2~5: Supervisor 실행
            print(f"  [Executing...]")
            final_state = await self.supervisor.app.ainvoke(initial_state)
            execution_time = time.time() - start_time

            # PHASE 2: Planning 결과 추출
            planning_state = final_state.get('planning_state', {})
            analyzed_intent = planning_state.get('analyzed_intent', {})
            execution_steps = planning_state.get('execution_steps', [])

            process_log["phase_2_planning"] = {
                "intent_type": analyzed_intent.get('intent_type', 'unknown'),
                "confidence": analyzed_intent.get('confidence', 0),
                "keywords": analyzed_intent.get('keywords', []),
                "entities": analyzed_intent.get('entities', {}),
                "execution_steps_count": len(execution_steps),
                "execution_steps": [
                    {
                        "agent_name": step.get('agent_name'),
                        "team": step.get('team'),
                        "priority": step.get('priority'),
                        "required": step.get('required', True)
                    }
                    for step in execution_steps
                ]
            }

            # PHASE 3: Team 실행 결과
            active_teams = final_state.get('active_teams', [])
            completed_teams = final_state.get('completed_teams', [])
            failed_teams = final_state.get('failed_teams', [])
            team_results = final_state.get('team_results', {})

            process_log["phase_3_team_execution"] = {
                "active_teams": active_teams,
                "completed_teams": completed_teams,
                "failed_teams": failed_teams,
                "team_count": len(completed_teams) + len(failed_teams),
                "team_details": {}
            }

            # 각 팀의 상세 결과
            for team_name, team_result in team_results.items():
                if isinstance(team_result, dict):
                    team_detail = {
                        "status": team_result.get('status', 'unknown'),
                        "result_count": 0,
                        "data_sources": []
                    }

                    # 검색 결과 카운트
                    if 'legal_results' in team_result:
                        team_detail["result_count"] += len(team_result.get('legal_results', []))
                        team_detail["data_sources"].append("legal_db")
                    if 'real_estate_results' in team_result:
                        team_detail["result_count"] += len(team_result.get('real_estate_results', []))
                        team_detail["data_sources"].append("real_estate_db")
                    if 'loan_results' in team_result:
                        team_detail["result_count"] += len(team_result.get('loan_results', []))
                        team_detail["data_sources"].append("loan_db")

                    process_log["phase_3_team_execution"]["team_details"][team_name] = team_detail

            # PHASE 4: Aggregation
            aggregated_results = final_state.get('aggregated_results', {})
            process_log["phase_4_aggregation"] = {
                "total_results": sum(len(v) if isinstance(v, list) else 0 for v in aggregated_results.values()),
                "result_types": list(aggregated_results.keys()) if aggregated_results else []
            }

            # PHASE 5: Response Generation
            final_response = final_state.get('final_response', {})
            if isinstance(final_response, dict):
                answer_text = final_response.get('answer', '')
            else:
                answer_text = str(final_response)

            process_log["phase_5_response_generation"] = {
                "answer_length": len(answer_text),
                "has_answer": bool(answer_text),
                "response_format": "json" if isinstance(final_response, dict) else "text"
            }

            # 결과 정리
            result.update({
                "status": "success",
                "execution_time": execution_time,
                "actual_intent": analyzed_intent.get('intent_type'),
                "intent_confidence": analyzed_intent.get('confidence', 0),
                "teams_executed": completed_teams,
                "teams_failed": failed_teams,
                "total_data_sources": len(set(
                    source
                    for team_detail in process_log["phase_3_team_execution"]["team_details"].values()
                    for source in team_detail["data_sources"]
                )),
                "response_preview": answer_text[:300] if answer_text else "",
                "full_answer": answer_text,
                "process_log": process_log
            })

            print(f"  [OK] {execution_time:.2f}s | Intent: {analyzed_intent.get('intent_type', 'N/A')} ({analyzed_intent.get('confidence', 0):.0%}) | Teams: {', '.join(completed_teams)}")

        except Exception as e:
            execution_time = time.time() - start_time
            result.update({
                "status": "failed",
                "error": str(e),
                "execution_time": execution_time,
                "process_log": process_log
            })
            print(f"  [FAIL] {e}")

        return result

    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("\n" + "="*80)
        print("100 QUERY COMPREHENSIVE TEST")
        print("="*80)
        print("[3/5] Running tests...")

        start_time = time.time()

        for i, query_data in enumerate(self.queries, 1):
            result = await self.run_single_test(query_data, i, len(self.queries))
            self.results.append(result)

            if result['status'] == 'success':
                self.stats['success'] += 1
            else:
                self.stats['failed'] += 1

            category = result['category']
            self.stats['by_category'][category] = self.stats['by_category'].get(category, 0) + 1

            # Intent 통계
            if 'actual_intent' in result:
                intent = result['actual_intent']
                self.stats['by_intent'][intent] = self.stats['by_intent'].get(intent, 0) + 1

            # 진행률 출력
            if i % 10 == 0:
                print(f"\n  Progress: {i}/{len(self.queries)} ({i/len(self.queries)*100:.1f}%)")

            await asyncio.sleep(0.1)  # Rate limiting

        self.stats['total_time'] = time.time() - start_time
        self.stats['average_time'] = self.stats['total_time'] / len(self.queries)

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
        print("\n[4/5] Generating reports...")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        reports_dir = Path(__file__).parent / "reports"
        reports_dir.mkdir(exist_ok=True)

        # JSON 리포트
        json_file = reports_dir / f"test_100_queries_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                "test_info": self.stats,
                "results": self.results
            }, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)

        print(f"      JSON Report: {json_file.name}")

        # Markdown 리포트 (상세 프로세스 포함)
        md_file = reports_dir / f"test_100_queries_{timestamp}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            self._write_markdown_report(f)

        print(f"      Markdown Report: {md_file.name}")

        return json_file, md_file

    def _write_markdown_report(self, f):
        """상세 Markdown 리포트 작성"""

        f.write("# 100 Query Comprehensive Test Report\n\n")
        f.write(f"**Test Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Total Queries**: {self.stats['total']}\n\n")

        # Summary
        f.write("## Summary\n\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"|--------|-------|\n")
        f.write(f"| Total Queries | {self.stats['total']} |\n")
        f.write(f"| Success | {self.stats['success']} |\n")
        f.write(f"| Failed | {self.stats['failed']} |\n")
        f.write(f"| Success Rate | {self.stats['success']/self.stats['total']*100:.1f}% |\n")
        f.write(f"| Total Time | {self.stats['total_time']:.2f}s |\n")
        f.write(f"| Average Time | {self.stats['average_time']:.2f}s/query |\n\n")

        # Category Distribution
        f.write("## Distribution by Category\n\n")
        for category, count in self.stats['by_category'].items():
            f.write(f"- **{category}**: {count} queries\n")
        f.write("\n")

        # Intent Distribution
        f.write("## Distribution by Detected Intent\n\n")
        for intent, count in sorted(self.stats['by_intent'].items(), key=lambda x: x[1], reverse=True):
            f.write(f"- **{intent}**: {count} queries\n")
        f.write("\n")

        # 상세 결과 (질문-과정-답변 형식)
        f.write("## Detailed Results (Question - Process - Answer)\n\n")

        for i, result in enumerate(self.results, 1):
            f.write(f"### {i}. {result['query_id']}\n\n")

            # 질문
            f.write(f"**Query**: {result['query']}\n\n")
            f.write(f"- Category: `{result['category']}`\n")
            f.write(f"- Expected Intent: `{result.get('expected_intent', 'N/A')}`\n")
            f.write(f"- Status: **{result['status'].upper()}**\n")
            f.write(f"- Execution Time: {result.get('execution_time', 0):.2f}s\n\n")

            if result['status'] == 'success':
                process_log = result.get('process_log', {})

                # 세부 과정
                f.write("#### Process Details\n\n")

                # Phase 1: Initialization
                f.write("**Phase 1: Initialization**\n")
                f.write("- State initialized successfully\n\n")

                # Phase 2: Planning
                planning = process_log.get('phase_2_planning', {})
                f.write("**Phase 2: Intent Analysis & Planning**\n")
                f.write(f"- Detected Intent: `{planning.get('intent_type', 'unknown')}`\n")
                f.write(f"- Confidence: {planning.get('confidence', 0):.0%}\n")
                f.write(f"- Keywords: {', '.join(planning.get('keywords', []))}\n")
                f.write(f"- Execution Steps: {planning.get('execution_steps_count', 0)}\n")

                if planning.get('execution_steps'):
                    f.write("- Planned Teams:\n")
                    for step in planning['execution_steps']:
                        f.write(f"  - {step['agent_name']} (team: {step['team']}, priority: {step['priority']})\n")
                f.write("\n")

                # Phase 3: Team Execution
                team_exec = process_log.get('phase_3_team_execution', {})
                f.write("**Phase 3: Team Execution**\n")
                f.write(f"- Completed Teams: {', '.join(team_exec.get('completed_teams', []))}\n")
                f.write(f"- Failed Teams: {', '.join(team_exec.get('failed_teams', []))}\n")

                if team_exec.get('team_details'):
                    f.write("- Team Results:\n")
                    for team_name, detail in team_exec['team_details'].items():
                        f.write(f"  - **{team_name}**: {detail['status']} | ")
                        f.write(f"{detail['result_count']} results from {', '.join(detail['data_sources'])}\n")
                f.write("\n")

                # Phase 4: Aggregation
                aggregation = process_log.get('phase_4_aggregation', {})
                f.write("**Phase 4: Result Aggregation**\n")
                f.write(f"- Total Results: {aggregation.get('total_results', 0)}\n")
                f.write(f"- Result Types: {', '.join(aggregation.get('result_types', []))}\n\n")

                # Phase 5: Response Generation
                response_gen = process_log.get('phase_5_response_generation', {})
                f.write("**Phase 5: Response Generation**\n")
                f.write(f"- Answer Length: {response_gen.get('answer_length', 0)} characters\n")
                f.write(f"- Response Format: {response_gen.get('response_format', 'unknown')}\n\n")

                # 답변
                f.write("#### Final Answer\n\n")
                answer = result.get('full_answer', result.get('response_preview', ''))
                if answer:
                    # 첫 500자만 표시
                    if len(answer) > 500:
                        f.write(f"```\n{answer[:500]}...\n```\n\n")
                    else:
                        f.write(f"```\n{answer}\n```\n\n")
                else:
                    f.write("*No answer generated*\n\n")

            else:
                # 실패한 경우
                f.write(f"**Error**: {result.get('error', 'Unknown error')}\n\n")

            f.write("---\n\n")


async def main():
    """메인 실행 함수"""
    print("\n" + "="*80)
    print("100 QUERY COMPREHENSIVE TEST SUITE")
    print("="*80)

    runner = ComprehensiveTestRunner()

    try:
        runner.load_queries()
        await runner.initialize_supervisor()
        await runner.run_all_tests()
        json_file, md_file = runner.save_reports()

        print("\n[5/5] Test suite completed successfully!")
        print(f"      JSON: {json_file}")
        print(f"      Markdown: {md_file}")

    except Exception as e:
        print(f"\n[ERROR] Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
