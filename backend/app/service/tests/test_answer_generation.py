#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify LLM-based answer generation
Tests if the system now generates natural language answers instead of raw data
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from app.service.supervisor.supervisor import RealEstateSupervisor


async def test_answer_generation():
    """Test if the system generates natural language answers"""

    print("=" * 80)
    print("Testing LLM-based Answer Generation")
    print("=" * 80)

    # Initialize supervisor
    supervisor = RealEstateSupervisor()

    # Test queries
    test_queries = [
        {
            "query": "전세금 얼마나 올릴 수 있어? 지금 5억이야",
            "description": "전세금 인상률 질문"
        },
        {
            "query": "상가임대차보호법에서 권리금 회수 기회 보호는 어떻게 되어 있어?",
            "description": "법률 조항 검색 및 설명"
        },
        {
            "query": "강남구 아파트 시세가 어떻게 되나요?",
            "description": "부동산 시세 정보"
        }
    ]

    for test_case in test_queries:
        print(f"\n{'=' * 60}")
        print(f"테스트: {test_case['description']}")
        print(f"질문: {test_case['query']}")
        print("-" * 60)

        try:
            # Process query
            result = await supervisor.process_query(
                query=test_case['query'],
                session_id="test_answer_generation"
            )

            # Check if response contains natural language answer
            if "response" in result:
                response = result["response"]

                # Check response structure
                print("\n응답 구조:")
                if isinstance(response, dict):
                    print(f"  - Type: {response.get('type', 'N/A')}")

                    # Check for natural language answer
                    if "answer" in response:
                        print(f"  - Natural Language Answer: YES")
                        print(f"\n생성된 답변:")
                        print("-" * 40)
                        print(response["answer"])
                        print("-" * 40)
                    else:
                        print(f"  - Natural Language Answer: NO")
                        print(f"  - Raw Data Only: {list(response.keys())}")

                    # Check for sources
                    if "sources" in response:
                        print(f"\n출처:")
                        for source in response["sources"][:3]:
                            print(f"  - {source}")

                    # Check if data is still available
                    if "data" in response:
                        print(f"\n원본 데이터: Available (for reference)")
                else:
                    print(f"응답 타입: {type(response)}")
                    print(f"응답 내용: {str(response)[:200]}...")

            else:
                print("WARNING: 'response' 키가 결과에 없습니다")
                print(f"사용 가능한 키: {list(result.keys())}")

        except Exception as e:
            print(f"ERROR 발생: {e}")

    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_answer_generation())