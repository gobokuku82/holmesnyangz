"""
Quick 5-query test to diagnose performance
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
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


async def run_test():
    """5개 쿼리 빠른 테스트"""

    # Test queries
    queries = [
        {"query": "전세금 5% 인상이 가능한가요?", "category": "법률"},
        {"query": "강남구 아파트 시세 알려주세요", "category": "시세"},
        {"query": "주택담보대출 금리 비교해주세요", "category": "대출"},
        {"query": "강남 아파트 매매가격과 관련 법률 알려주세요", "category": "법률+시세"},
        {"query": "전세 대출 받을 때 주의사항과 금리는?", "category": "법률+대출"}
    ]

    print("\n" + "="*80)
    print("5-Query Performance Test")
    print("="*80)

    # Initialize
    print("\n[1/2] Initializing LLM Context...")
    llm_context = create_default_llm_context()

    print("[2/2] Initializing TeamSupervisor...")
    supervisor = TeamBasedSupervisor(llm_context=llm_context)

    print("\n" + "="*80)
    print("Starting Tests")
    print("="*80)

    total_start = time.time()
    results = []

    for idx, query_data in enumerate(queries, 1):
        query = query_data['query']
        category = query_data['category']

        print(f"\n[Test {idx}/5] Category: {category}")
        print(f"Query: {query}")

        test_start = time.time()

        try:
            # Create state
            initial_state = MainSupervisorState(
                user_query=query,
                session_id=f"test_{idx}_{int(time.time())}",
                messages=[],
                next="planning"
            )

            # Execute
            print(f"  -> Starting execution at {time.strftime('%H:%M:%S')}...")
            final_state = await supervisor.app.ainvoke(initial_state)

            # Get answer
            final_response = final_state.get('final_response', {})
            if isinstance(final_response, dict):
                answer_text = final_response.get('answer', 'No answer field')
            else:
                answer_text = str(final_response)

            elapsed = time.time() - test_start

            print(f"  -> Completed in {elapsed:.2f}s")
            print(f"  -> Answer: {answer_text[:100]}...")

            results.append({
                "query": query,
                "category": category,
                "elapsed": elapsed,
                "success": True,
                "answer_length": len(answer_text),
                "response_type": final_response.get('type') if isinstance(final_response, dict) else 'unknown'
            })

        except Exception as e:
            elapsed = time.time() - test_start
            print(f"  -> [FAIL] Error in {elapsed:.2f}s: {str(e)[:100]}")
            results.append({
                "query": query,
                "category": category,
                "elapsed": elapsed,
                "success": False,
                "error": str(e)
            })

    total_elapsed = time.time() - total_start

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total queries: 5")
    print(f"Successful: {sum(1 for r in results if r['success'])}")
    print(f"Failed: {sum(1 for r in results if not r['success'])}")
    print(f"Total time: {total_elapsed:.2f}s")
    print(f"Average time per query: {total_elapsed/5:.2f}s")
    print(f"\nTime breakdown:")
    for idx, result in enumerate(results, 1):
        status = "[OK]" if result['success'] else "[FAIL]"
        print(f"  Query {idx}: {result['elapsed']:.2f}s {status}")

    # Save results
    output_file = Path(__file__).parent / "reports" / f"quick_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_time": total_elapsed,
            "avg_time": total_elapsed / 5,
            "results": results
        }, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(run_test())
