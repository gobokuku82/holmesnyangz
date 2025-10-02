#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Team Architecture Integration Test
팀 기반 아키텍처 통합 테스트
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
import time

# Add parent directory to path
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service.supervisor.team_supervisor import TeamBasedSupervisor
from app.service.core.agent_registry import AgentRegistry
from app.service.core.agent_adapter import initialize_agent_system


class TeamArchitectureTest:
    """팀 기반 아키텍처 테스트"""

    def __init__(self):
        self.supervisor = None
        self.test_results = []

    async def setup(self):
        """테스트 환경 설정"""
        print("\n" + "="*80)
        print("Team Architecture Test - Setup")
        print("="*80)

        # Agent 시스템 초기화
        initialize_agent_system(auto_register=True)

        # 등록된 Agent 확인
        registered_agents = AgentRegistry.list_agents()
        print(f"\nRegistered Agents: {registered_agents}")

        # 팀 확인
        teams = AgentRegistry.list_teams()
        print(f"Registered Teams: {teams}")

        # Supervisor 초기화
        self.supervisor = TeamBasedSupervisor()
        print("\nTeamBasedSupervisor initialized")

        # 사용 가능한 팀 확인
        available_teams = list(self.supervisor.teams.keys())
        print(f"Available Teams: {available_teams}")

    async def test_single_team_query(self):
        """단일 팀 쿼리 테스트"""
        print("\n" + "="*80)
        print("Test 1: Single Team Query")
        print("="*80)

        queries = [
            {
                "query": "전세금 인상률 제한은 얼마인가요?",
                "expected_teams": ["search"],
                "description": "법률 검색만 필요한 쿼리"
            },
            {
                "query": "임대차계약서 작성해주세요",
                "expected_teams": ["document"],
                "description": "문서 생성만 필요한 쿼리"
            }
        ]

        for test_case in queries:
            print(f"\n[Test Case] {test_case['description']}")
            print(f"Query: {test_case['query']}")

            start_time = time.time()
            result = await self.supervisor.process_query(
                test_case['query'],
                f"test_single_{datetime.now().timestamp()}"
            )
            execution_time = time.time() - start_time

            # 결과 검증
            status = result.get("status")
            active_teams = result.get("active_teams", [])
            final_response = result.get("final_response", {})

            print(f"Status: {status}")
            print(f"Active Teams: {active_teams}")
            print(f"Execution Time: {execution_time:.2f}s")

            # 응답 확인
            if final_response:
                response_type = final_response.get("type")
                print(f"Response Type: {response_type}")

                if response_type == "answer" and final_response.get("answer"):
                    print(f"Answer Preview: {final_response['answer'][:150]}...")

            # 테스트 결과 저장
            self.test_results.append({
                "test": "single_team",
                "query": test_case['query'],
                "status": status,
                "teams_used": active_teams,
                "execution_time": execution_time,
                "success": status == "completed"
            })

    async def test_multi_team_query(self):
        """다중 팀 쿼리 테스트"""
        print("\n" + "="*80)
        print("Test 2: Multi-Team Query")
        print("="*80)

        queries = [
            {
                "query": "강남구 아파트 시세를 분석하고 투자 추천해주세요",
                "expected_teams": ["search", "analysis"],
                "description": "검색 + 분석이 필요한 쿼리"
            },
            {
                "query": "전세계약서를 작성하고 위험요소를 검토해주세요",
                "expected_teams": ["document"],
                "description": "문서 생성 + 검토가 필요한 쿼리"
            }
        ]

        for test_case in queries:
            print(f"\n[Test Case] {test_case['description']}")
            print(f"Query: {test_case['query']}")

            start_time = time.time()
            result = await self.supervisor.process_query(
                test_case['query'],
                f"test_multi_{datetime.now().timestamp()}"
            )
            execution_time = time.time() - start_time

            # 결과 검증
            status = result.get("status")
            active_teams = result.get("active_teams", [])
            completed_teams = result.get("completed_teams", [])

            print(f"Status: {status}")
            print(f"Active Teams: {active_teams}")
            print(f"Completed Teams: {completed_teams}")
            print(f"Execution Time: {execution_time:.2f}s")

            # 팀별 결과 확인
            team_results = result.get("team_results", {})
            if team_results:
                print("\nTeam Results:")
                for team_name, team_data in team_results.items():
                    if isinstance(team_data, dict):
                        print(f"  - {team_name}: {list(team_data.keys())}")

            # 테스트 결과 저장
            self.test_results.append({
                "test": "multi_team",
                "query": test_case['query'],
                "status": status,
                "teams_used": active_teams,
                "execution_time": execution_time,
                "success": status == "completed"
            })

    async def test_complex_workflow(self):
        """복잡한 워크플로우 테스트"""
        print("\n" + "="*80)
        print("Test 3: Complex Workflow")
        print("="*80)

        query = "전세금 5% 인상이 가능한지 법적 검토하고, 시장 상황을 분석한 후 계약서 수정안을 작성해주세요"

        print(f"Query: {query}")

        start_time = time.time()
        result = await self.supervisor.process_query(
            query,
            f"test_complex_{datetime.now().timestamp()}"
        )
        execution_time = time.time() - start_time

        # 상세 결과 출력
        print("\n[Execution Details]")
        print(f"Status: {result.get('status')}")
        print(f"Current Phase: {result.get('current_phase')}")
        print(f"Active Teams: {result.get('active_teams', [])}")
        print(f"Completed Teams: {result.get('completed_teams', [])}")
        print(f"Failed Teams: {result.get('failed_teams', [])}")
        print(f"Execution Time: {execution_time:.2f}s")

        # Planning 정보
        planning_state = result.get("planning_state", {})
        if planning_state:
            print("\n[Planning Information]")
            intent = planning_state.get("analyzed_intent", {})
            print(f"Intent Type: {intent.get('intent_type')}")
            print(f"Confidence: {intent.get('confidence')}")
            print(f"Execution Strategy: {planning_state.get('execution_strategy')}")
            print(f"Estimated Time: {planning_state.get('estimated_total_time')}s")

        # 최종 응답
        final_response = result.get("final_response", {})
        if final_response:
            print("\n[Final Response]")
            print(f"Type: {final_response.get('type')}")
            if final_response.get("answer"):
                print(f"Answer: {final_response['answer'][:300]}...")
            print(f"Teams Used: {final_response.get('teams_used', [])}")

        # 테스트 결과 저장
        self.test_results.append({
            "test": "complex_workflow",
            "query": query,
            "status": result.get("status"),
            "teams_used": result.get("active_teams", []),
            "execution_time": execution_time,
            "success": result.get("status") == "completed"
        })

    async def test_error_handling(self):
        """에러 처리 테스트"""
        print("\n" + "="*80)
        print("Test 4: Error Handling")
        print("="*80)

        error_queries = [
            {
                "query": "",
                "description": "빈 쿼리"
            },
            {
                "query": "이것은 부동산과 전혀 관련없는 질문입니다",
                "description": "관련없는 쿼리"
            }
        ]

        for test_case in error_queries:
            print(f"\n[Test Case] {test_case['description']}")
            print(f"Query: '{test_case['query']}'")

            try:
                result = await self.supervisor.process_query(
                    test_case['query'],
                    f"test_error_{datetime.now().timestamp()}"
                )

                status = result.get("status")
                error = result.get("error")

                print(f"Status: {status}")
                if error:
                    print(f"Error: {error}")

                # 에러 로그 확인
                error_log = result.get("error_log", [])
                if error_log:
                    print(f"Error Log: {error_log}")

                self.test_results.append({
                    "test": "error_handling",
                    "query": test_case['query'],
                    "status": status,
                    "error": error,
                    "success": True  # 에러를 제대로 처리했으면 성공
                })

            except Exception as e:
                print(f"Exception caught: {e}")
                self.test_results.append({
                    "test": "error_handling",
                    "query": test_case['query'],
                    "status": "exception",
                    "error": str(e),
                    "success": False
                })

    async def test_performance(self):
        """성능 테스트"""
        print("\n" + "="*80)
        print("Test 5: Performance Test")
        print("="*80)

        # 동일한 쿼리를 여러 번 실행하여 평균 시간 측정
        query = "전세금 인상률은 얼마까지 가능한가요?"
        num_iterations = 3

        execution_times = []
        for i in range(num_iterations):
            print(f"\nIteration {i+1}/{num_iterations}")

            start_time = time.time()
            result = await self.supervisor.process_query(
                query,
                f"test_perf_{i}_{datetime.now().timestamp()}"
            )
            execution_time = time.time() - start_time

            execution_times.append(execution_time)
            print(f"Execution Time: {execution_time:.2f}s")

        # 통계
        avg_time = sum(execution_times) / len(execution_times)
        min_time = min(execution_times)
        max_time = max(execution_times)

        print(f"\n[Performance Statistics]")
        print(f"Average Time: {avg_time:.2f}s")
        print(f"Min Time: {min_time:.2f}s")
        print(f"Max Time: {max_time:.2f}s")

        self.test_results.append({
            "test": "performance",
            "avg_time": avg_time,
            "min_time": min_time,
            "max_time": max_time,
            "iterations": num_iterations,
            "success": avg_time < 30  # 30초 이내면 성공
        })

    def print_summary(self):
        """테스트 요약 출력"""
        print("\n" + "="*80)
        print("Test Summary")
        print("="*80)

        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r.get("success"))

        print(f"\nTotal Tests: {total_tests}")
        print(f"Successful: {successful_tests}")
        print(f"Failed: {total_tests - successful_tests}")
        print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")

        print("\n[Test Results Detail]")
        for result in self.test_results:
            test_name = result.get("test")
            success = "PASS" if result.get("success") else "FAIL"
            print(f"[{success}] {test_name}: ", end="")

            if test_name == "performance":
                print(f"Avg: {result.get('avg_time', 0):.2f}s")
            else:
                print(f"Status: {result.get('status', 'N/A')}")

        # 결과를 JSON 파일로 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"test_results_{timestamp}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)

        print(f"\nTest results saved to: {output_file}")

    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("\n" + "="*80)
        print("Running Team Architecture Integration Tests")
        print("="*80)

        try:
            # 환경 설정
            await self.setup()

            # 개별 테스트 실행
            await self.test_single_team_query()
            await self.test_multi_team_query()
            await self.test_complex_workflow()
            await self.test_error_handling()
            await self.test_performance()

            # 요약 출력
            self.print_summary()

        except Exception as e:
            print(f"\n[CRITICAL ERROR] Test suite failed: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """메인 실행 함수"""
    tester = TeamArchitectureTest()
    await tester.run_all_tests()


if __name__ == "__main__":
    print("\n" + "="*80)
    print("Team Architecture Integration Test Suite")
    print("팀 기반 아키텍처 통합 테스트")
    print("="*80)

    asyncio.run(main())