"""
PlanningAgent LLMService 마이그레이션 테스트
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.cognitive_agents.planning_agent import PlanningAgent
from app.service_agent.foundation.context import LLMContext
from app.service_agent.foundation.config import Config


async def test_planning_agent_with_llm_service():
    """PlanningAgent가 LLMService를 올바르게 사용하는지 테스트"""

    print("=" * 60)
    print("PlanningAgent LLMService Migration Test")
    print("=" * 60)

    # Check API key
    api_key = Config.LLM_DEFAULTS.get("api_key")
    if not api_key:
        print("\n[!] No OpenAI API key found")
        print("    Set OPENAI_API_KEY in .env to test LLM calls")
        print("\n[*] Testing with pattern matching fallback...\n")
        llm_context = None
    else:
        print(f"\n[*] API Key found: {api_key[:10]}...\n")
        llm_context = LLMContext(
            api_key=api_key,
            temperature=0.1,
            max_tokens=1000
        )

    # Create PlanningAgent
    planner = PlanningAgent(llm_context=llm_context)
    print(f"[*] PlanningAgent created")
    print(f"[*] LLMService enabled: {planner.llm_service is not None}\n")

    # Test queries
    test_queries = [
        "전세금 5% 인상이 가능한가요?",
        "강남구 아파트 시세 알려주세요",
        "전세자금대출 한도가 얼마인가요?"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}/{len(test_queries)}: {query}")
        print('='*60)

        try:
            # Analyze intent
            intent = await planner.analyze_intent(query)

            print(f"\n[Result]")
            print(f"  Intent Type: {intent.intent_type.value}")
            print(f"  Confidence: {intent.confidence:.2f}")
            print(f"  Keywords: {intent.keywords}")
            print(f"  Suggested Agents: {intent.suggested_agents}")
            print(f"  Fallback Used: {intent.fallback}")
            if intent.reasoning:
                print(f"  Reasoning: {intent.reasoning[:100]}...")

            # Create execution plan
            plan = await planner.create_execution_plan(intent)
            print(f"\n[Execution Plan]")
            print(f"  Strategy: {plan.strategy.value}")
            print(f"  Steps: {len(plan.steps)}")
            print(f"  Estimated Time: {plan.estimated_time:.1f}s")
            for step in plan.steps:
                print(f"    - {step.agent_name} (priority: {step.priority})")

            print(f"\n[OK] Test passed")

        except Exception as e:
            print(f"\n[ERROR] Test failed: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print("All tests completed")
    print('='*60)


if __name__ == "__main__":
    asyncio.run(test_planning_agent_with_llm_service())
