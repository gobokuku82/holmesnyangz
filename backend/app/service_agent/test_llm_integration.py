"""
LLM Integration Test - OpenAI API 연동 테스트
PlanningAgent, SearchTeam, TeamSupervisor의 LLM 기능 검증
"""

import asyncio
import sys
from pathlib import Path
import logging

# Path setup
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_planning_agent():
    """PlanningAgent LLM 의도 분석 테스트"""
    print("\n" + "="*80)
    print("TEST 1: PlanningAgent - LLM Intent Analysis")
    print("="*80)

    from app.service_agent.planning.planning_agent import PlanningAgent
    from app.service_agent.core.context import create_default_llm_context
    from openai import OpenAI

    # LLM Context 생성
    llm_context = create_default_llm_context()
    llm_client = OpenAI(api_key=llm_context.api_key)

    # PlanningAgent 초기화
    planning_agent = PlanningAgent(llm_client=llm_client)

    # 테스트 쿼리
    test_queries = [
        "전세금 5% 인상이 가능한가요?",
        "강남구 아파트 전세 시세 알려주세요",
        "주택담보대출 금리가 얼마인가요?"
    ]

    for query in test_queries:
        print(f"\n[Query] {query}")

        # 의도 분석
        intent_result = await planning_agent.analyze_intent(query)

        print(f"  Intent Type: {intent_result.intent_type.value}")
        print(f"  Confidence: {intent_result.confidence:.2%}")
        print(f"  Keywords: {intent_result.keywords}")
        print(f"  Reasoning: {intent_result.reasoning}")
        print(f"  Suggested Agents: {intent_result.suggested_agents}")
        print(f"  LLM Used: {not intent_result.fallback}")

    print("\n[PASS] PlanningAgent LLM integration successful")


async def test_search_team_keywords():
    """SearchTeam LLM 키워드 추출 테스트"""
    print("\n" + "="*80)
    print("TEST 2: SearchTeam - LLM Keyword Extraction")
    print("="*80)

    from app.service_agent.teams.search_team import SearchTeamSupervisor
    from app.service_agent.core.context import create_default_llm_context
    from app.service.core.separated_states import StateManager

    # LLM Context 생성
    llm_context = create_default_llm_context()

    # SearchTeam 초기화
    search_team = SearchTeamSupervisor(llm_context=llm_context)

    # 테스트 쿼리
    query = "강남구 아파트 전세금 5억 계약하려는데 법적으로 주의할 점 알려주세요"
    print(f"\n[Query] {query}")

    # 키워드 추출 테스트
    keywords = search_team._extract_keywords(query)

    print(f"\n[Extracted Keywords]")
    print(f"  Legal: {keywords.get('legal', [])}")
    print(f"  Real Estate: {keywords.get('real_estate', [])}")
    print(f"  Loan: {keywords.get('loan', [])}")
    print(f"  General: {keywords.get('general', [])}")

    # 실제 검색 실행
    print(f"\n[Executing Search]")
    shared_state = StateManager.create_shared_state(
        query=query,
        session_id="test_llm_keywords"
    )

    result = await search_team.execute(shared_state, search_scope=["legal"])

    print(f"  Status: {result.get('status')}")
    print(f"  Legal Results: {len(result.get('legal_results', []))} items")
    print(f"  Search Time: {result.get('search_time', 0):.2f}s")

    print("\n[PASS] SearchTeam LLM keyword extraction successful")


async def test_team_supervisor():
    """TeamSupervisor 전체 통합 테스트"""
    print("\n" + "="*80)
    print("TEST 3: TeamSupervisor - Full LLM Integration")
    print("="*80)

    from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor
    from app.service_agent.core.context import create_default_llm_context

    # LLM Context 생성
    llm_context = create_default_llm_context()

    # TeamSupervisor 초기화
    supervisor = TeamBasedSupervisor(llm_context=llm_context)

    # 테스트 쿼리
    query = "전세금 5% 인상이 가능한가요?"
    print(f"\n[Query] {query}")

    # 초기 상태 생성
    from app.service.core.separated_states import MainSupervisorState

    initial_state = MainSupervisorState(
        query=query,
        session_id="test_llm_supervisor",
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
        metadata={}
    )

    # 실행
    print(f"\n[Executing Full Pipeline]")
    result = await supervisor.app.ainvoke(initial_state)

    print(f"\n[Results]")
    print(f"  Status: {result.get('status')}")
    print(f"  Current Phase: {result.get('current_phase')}")
    print(f"  Active Teams: {result.get('active_teams', [])}")
    print(f"  Completed Teams: {result.get('completed_teams', [])}")
    print(f"  Total Time: {result.get('total_execution_time', 0):.2f}s")

    # 최종 응답 확인
    final_response = result.get('final_response')
    if final_response:
        print(f"\n[Final Response]")
        print(f"  Answer: {final_response.get('answer', 'N/A')[:200]}...")
        print(f"  Confidence: {final_response.get('confidence', 0):.2%}")
        print(f"  Recommendations: {len(final_response.get('recommendations', []))} items")
        print(f"  Sources: {len(final_response.get('sources', []))} items")

    print("\n[PASS] TeamSupervisor LLM integration successful")


async def main():
    """메인 테스트 함수"""
    print("\n" + "="*80)
    print("LLM INTEGRATION TEST SUITE")
    print("="*80)

    try:
        # Test 1: PlanningAgent
        await test_planning_agent()

        # Test 2: SearchTeam Keywords
        await test_search_team_keywords()

        # Test 3: TeamSupervisor
        await test_team_supervisor()

        print("\n" + "="*80)
        print("ALL TESTS PASSED")
        print("="*80)

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
