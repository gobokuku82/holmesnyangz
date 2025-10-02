"""
HolmesNyang Agent Query Test
전체 에이전트 시스템 테스트 - 쿼리 입력 → 결과 확인

진입점: TeamBasedSupervisor
경로: SearchTeam → AnalysisTeam → DocumentTeam
"""

import asyncio
import sys
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Path setup
current_file = Path(__file__).resolve()
backend_dir = current_file.parent.parent.parent  # service_agent -> app -> backend
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

print(f"[DEBUG] Backend dir: {backend_dir}")
print(f"[DEBUG] sys.path: {sys.path[0]}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('hn_agent_test.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Import after path setup
from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor
from app.service.core.context import create_default_llm_context


class AgentQueryTester:
    """에이전트 쿼리 테스터"""

    def __init__(self):
        """초기화"""
        logger.info("="*80)
        logger.info("HolmesNyang Agent System Initializing...")
        logger.info("="*80)

        # LLM Context 생성
        self.llm_context = create_default_llm_context()

        # TeamBasedSupervisor 초기화 (진입점)
        try:
            self.supervisor = TeamBasedSupervisor(llm_context=self.llm_context)
            logger.info("[OK] TeamBasedSupervisor initialized successfully")
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize TeamBasedSupervisor: {e}")
            raise

    def print_section(self, title: str, char: str = "="):
        """섹션 구분선 출력"""
        line = char * 80
        print(f"\n{line}")
        print(f"{title:^80}")
        print(f"{line}")

    def print_result(self, label: str, value: Any, indent: int = 0):
        """결과 출력 (들여쓰기 지원)"""
        prefix = "  " * indent
        if isinstance(value, (dict, list)):
            print(f"{prefix}{label}:")
            print(f"{prefix}  {json.dumps(value, ensure_ascii=False, indent=2)}")
        else:
            print(f"{prefix}{label}: {value}")

    async def execute_query(self, query: str, session_id: str = None) -> Dict[str, Any]:
        """
        쿼리 실행

        Args:
            query: 사용자 쿼리
            session_id: 세션 ID (선택)

        Returns:
            실행 결과
        """
        if not session_id:
            session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.print_section(f"Query Execution: {query}")

        print(f"\n[1] Input")
        print(f"  Query: {query}")
        print(f"  Session ID: {session_id}")

        # 초기 상태 생성
        initial_state = {
            "query": query,
            "session_id": session_id,
            "status": "pending",
            "start_time": datetime.now(),
            "active_teams": [],
            "completed_teams": [],
            "failed_teams": [],
            "team_results": {},
            "error_log": []
        }

        try:
            print(f"\n[2] Executing TeamBasedSupervisor...")
            print(f"  -> Planning Agent (intent analysis)")
            print(f"  -> Team Execution (search/analysis/document)")
            print(f"  -> Result Aggregation")
            print(f"  -> Response Generation")

            # TeamBasedSupervisor 실행
            start_time = datetime.now()
            result = await self.supervisor.app.ainvoke(initial_state)
            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()

            print(f"\n[3] Execution Completed ({elapsed:.2f}s)")

            return result

        except Exception as e:
            logger.error(f"[ERROR] Query execution failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e),
                "query": query,
                "session_id": session_id
            }

    def display_result(self, result: Dict[str, Any]):
        """결과 표시"""
        self.print_section("Execution Result")

        # 기본 정보
        print(f"\n[Basic Info]")
        self.print_result("Status", result.get("status", "unknown"))
        self.print_result("Session ID", result.get("session_id", "N/A"))
        self.print_result("Current Phase", result.get("current_phase", "N/A"))

        # 실행 시간
        if result.get("start_time") and result.get("end_time"):
            start = result["start_time"]
            end = result["end_time"]
            elapsed = (end - start).total_seconds()
            self.print_result("Execution Time", f"{elapsed:.2f}s")

        # Planning 결과
        if result.get("planning_state"):
            print(f"\n[Planning Result]")
            planning = result["planning_state"]
            self.print_result("Intent Type", planning.get("analyzed_intent", {}).get("intent_type", "N/A"))
            self.print_result("Confidence", planning.get("intent_confidence", 0))
            self.print_result("Execution Strategy", planning.get("execution_strategy", "N/A"))
            self.print_result("Estimated Time", f"{planning.get('estimated_total_time', 0)}s")

            # Execution Steps
            if planning.get("execution_steps"):
                print(f"\n  Execution Steps:")
                for i, step in enumerate(planning["execution_steps"], 1):
                    print(f"    [{i}] {step.get('agent_name', 'N/A')} (Team: {step.get('team', 'N/A')})")

        # 팀 실행 결과
        print(f"\n[Team Execution]")
        self.print_result("Active Teams", result.get("active_teams", []))
        self.print_result("Completed Teams", result.get("completed_teams", []))
        self.print_result("Failed Teams", result.get("failed_teams", []))

        # 팀별 상세 결과
        if result.get("team_results"):
            print(f"\n[Team Results]")
            team_results = result["team_results"]

            # SearchTeam 결과
            if "search" in team_results:
                print(f"\n  [SearchTeam Result]")
                search_result = team_results["search"]

                if isinstance(search_result, dict):
                    # Legal results
                    legal_results = search_result.get("legal_search", [])
                    if legal_results:
                        print(f"    Legal Search: {len(legal_results)} results")
                        for i, legal in enumerate(legal_results[:3], 1):
                            if isinstance(legal, dict):
                                print(f"      [{i}] {legal.get('law_title', 'N/A')} {legal.get('article_number', 'N/A')}")
                                print(f"          {legal.get('article_title', 'N/A')}")
                            else:
                                print(f"      [{i}] {legal}")

                    # Real estate results
                    real_estate_results = search_result.get("real_estate_search", [])
                    if real_estate_results:
                        print(f"    Real Estate Search: {len(real_estate_results)} results")
                        for i, estate in enumerate(real_estate_results[:3], 1):
                            print(f"      [{i}] {estate}")

                    # Loan results
                    loan_results = search_result.get("loan_search", [])
                    if loan_results:
                        print(f"    Loan Search: {len(loan_results)} results")
                        for i, loan in enumerate(loan_results[:3], 1):
                            print(f"      [{i}] {loan}")
                else:
                    print(f"    {search_result}")

            # AnalysisTeam 결과
            if "analysis" in team_results:
                print(f"\n  [AnalysisTeam Result]")
                analysis_result = team_results["analysis"]
                if isinstance(analysis_result, dict):
                    self.print_result("    Report", analysis_result.get("report", "N/A"), indent=2)
                    self.print_result("    Insights", analysis_result.get("insights", []), indent=2)
                else:
                    print(f"    {analysis_result}")

            # DocumentTeam 결과
            if "document" in team_results:
                print(f"\n  [DocumentTeam Result]")
                doc_result = team_results["document"]
                if isinstance(doc_result, dict):
                    document = doc_result.get("document", "")
                    if document:
                        print(f"    Document: {document[:200]}...")
                    review = doc_result.get("review", {})
                    if review:
                        self.print_result("    Review", review, indent=2)
                else:
                    print(f"    {doc_result}")

        # 최종 응답
        if result.get("final_response"):
            print(f"\n[Final Response]")
            response = result["final_response"]
            if isinstance(response, str):
                print(f"  {response[:500]}...")
            else:
                self.print_result("  Response", response)

        # 오류 로그
        if result.get("error_log"):
            print(f"\n[Error Log]")
            for i, error in enumerate(result["error_log"], 1):
                print(f"  [{i}] {error}")

        # 전체 결과 저장
        self.save_result(result)

    def save_result(self, result: Dict[str, Any]):
        """결과를 파일로 저장"""
        try:
            # datetime 객체 직렬화를 위한 처리
            def serialize_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")

            session_id = result.get("session_id", "unknown")
            filename = f"result_{session_id}.json"

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=serialize_datetime)

            print(f"\n[Result Saved] {filename}")

        except Exception as e:
            logger.warning(f"Failed to save result: {e}")

    async def run_interactive(self):
        """대화형 모드"""
        self.print_section("HolmesNyang Agent Interactive Mode")
        print("\nEnter your query (or 'quit' to exit)")
        print("Example queries:")
        print("  - '전세금 5% 인상 제한'")
        print("  - '강남 아파트 시세 분석'")
        print("  - '주택임대차보호법 제7조'")
        print("  - '계약 갱신 요구권'")

        while True:
            try:
                print("\n" + "-"*80)
                query = input("Query > ").strip()

                if not query:
                    continue

                if query.lower() in ['quit', 'exit', 'q']:
                    print("\nExiting...")
                    break

                # 쿼리 실행
                result = await self.execute_query(query)

                # 결과 표시
                self.display_result(result)

            except KeyboardInterrupt:
                print("\n\nInterrupted. Exiting...")
                break
            except Exception as e:
                logger.error(f"Error in interactive mode: {e}")
                import traceback
                traceback.print_exc()

    async def run_batch(self, queries: list):
        """배치 모드"""
        self.print_section("HolmesNyang Agent Batch Mode")
        print(f"\nRunning {len(queries)} queries...")

        results = []
        for i, query in enumerate(queries, 1):
            print(f"\n[Query {i}/{len(queries)}]")

            result = await self.execute_query(query)
            self.display_result(result)

            results.append({
                "query": query,
                "result": result
            })

        # 전체 결과 요약
        self.print_section("Batch Summary")
        successful = sum(1 for r in results if r["result"].get("status") == "completed")
        failed = len(results) - successful

        print(f"\nTotal Queries: {len(results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")

        return results


async def main():
    """메인 함수"""
    print("\n" + "="*80)
    print("HolmesNyang Agent Query Test".center(80))
    print("="*80)

    try:
        # Tester 초기화
        tester = AgentQueryTester()

        # 실행 모드 선택
        if len(sys.argv) > 1:
            # 커맨드라인 인자가 있으면 배치 모드
            queries = sys.argv[1:]
            await tester.run_batch(queries)
        else:
            # 인자가 없으면 대화형 모드
            await tester.run_interactive()

    except Exception as e:
        logger.error(f"[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 사용 예시
    print("\nUsage:")
    print("  Interactive mode: python hn_agent_query_test.py")
    print("  Batch mode:       python hn_agent_query_test.py '전세금 인상' '계약 갱신'")
    print()

    asyncio.run(main())
