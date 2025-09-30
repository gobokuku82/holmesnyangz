"""
Test agent selection with improved prompts
"""

import asyncio
import json
from pathlib import Path
import sys

# Add parent directories to path
current_dir = Path(__file__).parent
service_dir = current_dir.parent
sys.path.insert(0, str(service_dir))

from test_config import TestConfig
from supervisor.supervisor import RealEstateSupervisor

async def test_agent_selection():
    """Test various queries to see agent selection"""

    # Test cases with expected agent selection
    test_cases = [
        {
            "query": "강남구 아파트 매매 시세 알려줘",
            "expected_agent": "search_agent",
            "description": "시세 조회 - search_agent 선택되어야 함"
        },
        {
            "query": "전세 대출 조건이 뭐야?",
            "expected_agent": "search_agent",
            "description": "대출 정보 - search_agent 선택되어야 함"
        },
        {
            "query": "부동산 계약서 작성 방법",
            "expected_agent": "search_agent",
            "description": "법률 정보 - search_agent 선택되어야 함"
        },
        {
            "query": "서초구와 강남구 아파트 가격 비교 분석해줘",
            "expected_agent": "search_agent",  # analysis_agent가 없으므로
            "description": "분석 요청 - 현재는 search_agent만 가능"
        },
        {
            "query": "투자하기 좋은 아파트 추천해줘",
            "expected_agent": "search_agent",  # recommendation_agent가 없으므로
            "description": "추천 요청 - 현재는 search_agent만 가능"
        }
    ]

    print("="*70)
    print("AGENT SELECTION TEST")
    print("="*70)

    # Initialize supervisor
    print("\nInitializing supervisor...")
    supervisor = RealEstateSupervisor(llm_context=TestConfig.get_llm_context())
    print("[OK] Supervisor initialized\n")

    # Test each case
    for test in test_cases:
        print("-"*70)
        print(f"Test: {test['description']}")
        print(f"Query: {test['query']}")
        print(f"Expected: {test['expected_agent']}")

        try:
            # Process query to get execution plan
            result = await supervisor.process_query(
                query=test['query'],
                session_id="test",
                llm_context=TestConfig.get_llm_context()
            )

            # Extract selected agents
            execution_plan = result.get('execution_plan', {})
            selected_agents = execution_plan.get('agents', [])
            reasoning = execution_plan.get('reasoning', 'N/A')
            capabilities_used = execution_plan.get('agent_capabilities_used', [])

            print(f"Selected: {selected_agents}")
            print(f"Reasoning: {reasoning}")

            if capabilities_used:
                print(f"Capabilities: {', '.join(capabilities_used)}")

            # Check if correct agent was selected
            if test['expected_agent'] in selected_agents:
                print("[SUCCESS] Correct agent selected")
            else:
                print(f"[WARNING] Expected {test['expected_agent']}, got {selected_agents}")

        except Exception as e:
            print(f"[ERROR] {e}")

        print()
        # Small delay between tests
        await asyncio.sleep(2)

    print("="*70)
    print("[OK] Test complete")

if __name__ == "__main__":
    asyncio.run(test_agent_selection())