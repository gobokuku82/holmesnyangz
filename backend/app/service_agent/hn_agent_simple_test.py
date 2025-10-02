"""
HolmesNyang Agent Simple Test
간단한 에이전트 시스템 테스트 (의존성 최소화)

진입점: SearchTeam (단독 테스트)
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Path setup
current_file = Path(__file__).resolve()
backend_dir = current_file.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

print(f"Backend dir: {backend_dir}\n")


class SimpleAgentTester:
    """간단한 에이전트 테스터 (SearchTeam만)"""

    def __init__(self):
        """초기화"""
        print("="*80)
        print("HolmesNyang Agent System - Simple Test".center(80))
        print("="*80)
        print("\nInitializing SearchTeam...")

        try:
            from app.service_agent.teams.search_team import SearchTeamSupervisor
            from app.service.core.separated_states import StateManager

            self.SearchTeamSupervisor = SearchTeamSupervisor
            self.StateManager = StateManager

            print("[OK] Modules loaded successfully")

        except Exception as e:
            print(f"[ERROR] Failed to load modules: {e}")
            import traceback
            traceback.print_exc()
            raise

    def print_section(self, title: str):
        """섹션 구분"""
        print(f"\n{'='*80}")
        print(f"{title:^80}")
        print(f"{'='*80}")

    async def test_search_team(self, query: str, search_scope: list = None):
        """SearchTeam 테스트"""
        self.print_section(f"Testing SearchTeam")

        print(f"\n[Input]")
        print(f"  Query: {query}")
        print(f"  Scope: {search_scope or 'auto-detect'}")

        try:
            # SearchTeam 초기화
            print(f"\n[1] Initializing SearchTeam...")
            search_team = self.SearchTeamSupervisor()

            # 공유 상태 생성
            print(f"[2] Creating shared state...")
            shared_state = self.StateManager.create_shared_state(
                query=query,
                session_id=f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

            # SearchTeam 실행
            print(f"[3] Executing SearchTeam...")
            start_time = datetime.now()

            result = await search_team.execute(
                shared_state,
                search_scope=search_scope
            )

            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()

            # 결과 표시
            self.print_section("Result")

            print(f"\n[Execution Info]")
            print(f"  Status: {result.get('status', 'unknown')}")
            print(f"  Time: {elapsed:.2f}s")
            print(f"  Search Time: {result.get('search_time', 0):.2f}s")

            print(f"\n[Search Details]")
            print(f"  Search Scope: {result.get('search_scope', [])}")
            print(f"  Execution Strategy: {result.get('execution_strategy', 'N/A')}")
            print(f"  Keywords: {result.get('keywords', {})}")

            print(f"\n[Results Summary]")
            print(f"  Total Results: {result.get('total_results', 0)}")
            print(f"  Sources Used: {result.get('sources_used', [])}")

            # 법률 검색 결과
            legal_results = result.get('legal_results', [])
            if legal_results:
                print(f"\n[Legal Results] ({len(legal_results)} items)")
                for i, legal in enumerate(legal_results[:5], 1):
                    if isinstance(legal, dict):
                        law_title = legal.get('law_title', 'N/A')
                        article_number = legal.get('article_number', 'N/A')
                        article_title = legal.get('article_title', 'N/A')
                        content = legal.get('content', '')
                        relevance = legal.get('relevance_score', 0)

                        print(f"\n  [{i}] {law_title} {article_number}")
                        print(f"      Title: {article_title}")
                        print(f"      Relevance: {relevance:.3f}")
                        print(f"      Content: {content[:150]}...")
                    else:
                        print(f"  [{i}] {legal}")
            else:
                print(f"\n[Legal Results] No results")

            # 부동산 검색 결과
            real_estate_results = result.get('real_estate_results', [])
            if real_estate_results:
                print(f"\n[Real Estate Results] ({len(real_estate_results)} items)")
                for i, estate in enumerate(real_estate_results[:3], 1):
                    print(f"  [{i}] {estate}")

            # 대출 검색 결과
            loan_results = result.get('loan_results', [])
            if loan_results:
                print(f"\n[Loan Results] ({len(loan_results)} items)")
                for i, loan in enumerate(loan_results[:3], 1):
                    print(f"  [{i}] {loan}")

            # 집계 결과
            if result.get('aggregated_results'):
                print(f"\n[Aggregated Results]")
                agg = result['aggregated_results']
                print(f"  Total Count: {agg.get('total_count', 0)}")
                print(f"  By Type: {agg.get('by_type', {})}")

            # 오류
            if result.get('error'):
                print(f"\n[Error]")
                print(f"  {result['error']}")

            # 검색 진행 상황
            if result.get('search_progress'):
                print(f"\n[Search Progress]")
                for key, value in result['search_progress'].items():
                    print(f"  {key}: {value}")

            # 결과 저장
            self.save_result(query, result)

            return result

        except Exception as e:
            print(f"\n[ERROR] Test failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e),
                "query": query
            }

    def save_result(self, query: str, result: Dict[str, Any]):
        """결과 저장"""
        try:
            # datetime 객체 변환
            def convert_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: convert_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_datetime(v) for v in obj]
                return obj

            result_copy = convert_datetime(result)

            filename = f"search_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    "query": query,
                    "result": result_copy
                }, f, ensure_ascii=False, indent=2)

            print(f"\n[Saved] {filename}")

        except Exception as e:
            print(f"[WARNING] Failed to save result: {e}")

    async def run_interactive(self):
        """대화형 모드"""
        self.print_section("Interactive Mode")

        print("\nAvailable commands:")
        print("  - Enter query to search (e.g., '전세금 5% 인상')")
        print("  - 'legal' - Search legal documents only")
        print("  - 'real_estate' - Search real estate only")
        print("  - 'loan' - Search loan information only")
        print("  - 'all' - Search all categories")
        print("  - 'quit' - Exit")

        print("\nExample queries:")
        print("  - 전세금 5% 인상 제한")
        print("  - 강남 아파트 시세")
        print("  - 주택임대차보호법 제7조")
        print("  - 계약 갱신 요구권")

        current_scope = None

        while True:
            try:
                print("\n" + "-"*80)
                user_input = input("Query > ").strip()

                if not user_input:
                    continue

                # 명령어 처리
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\nExiting...")
                    break
                elif user_input.lower() == 'legal':
                    current_scope = ['legal']
                    print("[Scope] Legal documents only")
                    continue
                elif user_input.lower() == 'real_estate':
                    current_scope = ['real_estate']
                    print("[Scope] Real estate only")
                    continue
                elif user_input.lower() == 'loan':
                    current_scope = ['loan']
                    print("[Scope] Loan information only")
                    continue
                elif user_input.lower() == 'all':
                    current_scope = None
                    print("[Scope] All categories")
                    continue

                # 쿼리 실행
                await self.test_search_team(user_input, current_scope)

            except KeyboardInterrupt:
                print("\n\nInterrupted. Exiting...")
                break
            except Exception as e:
                print(f"\n[ERROR] {e}")
                import traceback
                traceback.print_exc()

    async def run_batch(self, queries: list):
        """배치 모드"""
        self.print_section("Batch Mode")
        print(f"\nRunning {len(queries)} queries...\n")

        results = []
        for i, query in enumerate(queries, 1):
            print(f"\n{'='*80}")
            print(f"Query {i}/{len(queries)}: {query}")
            print(f"{'='*80}")

            result = await self.test_search_team(query)
            results.append({
                "query": query,
                "result": result
            })

        # 요약
        self.print_section("Batch Summary")
        successful = sum(1 for r in results if r["result"].get("status") == "completed")
        failed = len(results) - successful

        print(f"\nTotal Queries: {len(results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")

        return results


async def main():
    """메인 함수"""
    try:
        tester = SimpleAgentTester()

        if len(sys.argv) > 1:
            # 배치 모드
            queries = sys.argv[1:]
            await tester.run_batch(queries)
        else:
            # 대화형 모드
            await tester.run_interactive()

    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\nUsage:")
    print("  Interactive mode: python hn_agent_simple_test.py")
    print("  Batch mode:       python hn_agent_simple_test.py '전세금 인상' '계약 갱신'\n")

    asyncio.run(main())
