"""
Integration Test: SearchExecutor with RealEstateSearchTool
Phase 3 검증 테스트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import asyncio
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_search_executor():
    """SearchExecutor 통합 테스트"""
    try:
        from app.service_agent.execution_agents.search_executor import SearchExecutor
        from app.service_agent.foundation.separated_states import SharedState

        print("\n" + "="*80)
        print("Phase 3 Integration Test: SearchExecutor with RealEstateSearchTool")
        print("="*80)

        # SearchExecutor 초기화
        print("\n[1] SearchExecutor 초기화 중...")
        executor = SearchExecutor()

        # 초기화 확인
        print("\n[2] Tool 초기화 상태 확인:")
        print(f"  - legal_search_tool: {'✅' if executor.legal_search_tool else '❌'}")
        print(f"  - market_data_tool: {'✅' if executor.market_data_tool else '❌'}")
        print(f"  - real_estate_search_tool: {'✅' if executor.real_estate_search_tool else '❌'}")
        print(f"  - loan_data_tool: {'✅' if executor.loan_data_tool else '❌'}")

        # _get_available_tools() 테스트
        print("\n[3] 사용 가능한 Tool 확인:")
        available_tools = executor._get_available_tools()
        for tool_name, tool_info in available_tools.items():
            print(f"  - {tool_name}: {tool_info['description']}")

        # 테스트 쿼리
        test_queries = [
            "강남구 아파트 매물 검색해줘",
            "송파구 5억 이하 오피스텔 찾아줘",
            "서초구 지하철역 근처 빌라"
        ]

        print("\n[4] 테스트 쿼리 실행:")
        for i, query in enumerate(test_queries, 1):
            print(f"\n  [{i}] Query: {query}")

            # SharedState 생성
            shared_state = SharedState(
                query=query,
                session_id=f"test_integration_{i}",
                user_id=1
            )

            try:
                # LLM Tool 선택 테스트
                tool_selection = await executor._select_tools_with_llm(query)
                selected = tool_selection.get("selected_tools", [])
                reasoning = tool_selection.get("reasoning", "")
                confidence = tool_selection.get("confidence", 0.0)

                print(f"      Selected tools: {selected}")
                print(f"      Confidence: {confidence:.2f}")
                print(f"      Reasoning: {reasoning[:100]}...")

                # real_estate_search가 선택되었는지 확인
                if "real_estate_search" in selected:
                    print("      ✅ RealEstateSearchTool이 선택되었습니다!")
                else:
                    print("      ⚠️  RealEstateSearchTool이 선택되지 않았습니다.")

            except Exception as e:
                print(f"      ❌ Error: {e}")

        print("\n" + "="*80)
        print("Integration Test 완료!")
        print("="*80)

        return True

    except Exception as e:
        logger.error(f"Integration test failed: {e}", exc_info=True)
        return False


async def main():
    """메인 함수"""
    success = await test_search_executor()

    if success:
        print("\n✅ Phase 3 통합 테스트 성공!")
        return 0
    else:
        print("\n❌ Phase 3 통합 테스트 실패!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
