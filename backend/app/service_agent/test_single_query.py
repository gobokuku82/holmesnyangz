"""Single query test to debug team execution"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime

# Path setup
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Enable debug logging
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s'
)

from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor
from app.service_agent.core.separated_states import MainSupervisorState
from app.service_agent.core.context import create_default_llm_context


async def test_single_query():
    """Test a single query"""
    print("\n" + "="*60)
    print("SINGLE QUERY TEST")
    print("="*60)

    # Initialize
    print("\n[1] Initializing...")
    llm_context = create_default_llm_context()
    supervisor = TeamBasedSupervisor(llm_context)

    # Test query
    query = "강남구 아파트 시세 알려주세요"
    print(f"\n[2] Query: {query}")

    # Create initial state
    initial_state = MainSupervisorState(
        query=query,
        session_id="test_single",
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
        metadata={"test": True}
    )

    print("\n[3] Executing...")
    try:
        # Execute
        final_state = await supervisor.app.ainvoke(initial_state)

        # Check results
        print("\n[4] Results:")
        print(f"   Status: {final_state.get('status')}")
        print(f"   Phase: {final_state.get('current_phase')}")

        # Check planning
        planning_state = final_state.get('planning_state', {})
        if planning_state:
            print(f"   Intent: {planning_state.get('analyzed_intent', {}).get('intent_type')}")
            print(f"   Execution steps: {len(planning_state.get('execution_steps', []))}")
            for step in planning_state.get('execution_steps', []):
                print(f"     - {step.get('agent_name')} (team: {step.get('team')})")

        # Check team execution
        print(f"   Active teams: {final_state.get('active_teams', [])}")
        print(f"   Completed teams: {final_state.get('completed_teams', [])}")
        print(f"   Failed teams: {final_state.get('failed_teams', [])}")

        # Check team results
        team_results = final_state.get('team_results', {})
        if team_results:
            print(f"   Team results: {list(team_results.keys())}")
            for team, result in team_results.items():
                if isinstance(result, dict):
                    print(f"     {team}: {result.get('status', 'unknown status')}")

        # Check final response
        final_response = final_state.get('final_response', {})
        if final_response:
            answer = final_response.get('answer', '')
            if answer:
                print(f"\n[5] Answer preview: {answer[:200]}...")
            else:
                print(f"\n[5] No answer generated")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(test_single_query())