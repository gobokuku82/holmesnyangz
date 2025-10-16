"""
구조화된 JSON 응답 테스트 스크립트
"""

import asyncio
import json
from pathlib import Path
import sys

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from app.service_agent.llm_manager.llm_service import LLMService
from app.service_agent.llm_manager.prompt_manager import PromptManager


async def test_structured_response():
    """구조화된 응답 생성 테스트"""

    # LLM 서비스 초기화
    llm = LLMService()
    prompt_manager = PromptManager()

    # 테스트 질문
    test_query = "전세금 5% 인상이 가능한가요? 현재 전세금은 3억입니다."

    print("=" * 80)
    print("구조화된 JSON 응답 테스트")
    print("=" * 80)
    print(f"질문: {test_query}")
    print("-" * 80)

    # 프롬프트 생성
    prompt = prompt_manager.get(
        "response_synthesis",
        {
            "query": test_query,
            "intent": "legal_consult",
            "legal_info": "주택임대차보호법 제7조에 따르면 전세금 인상률은 5% 이내로 제한됩니다.",
            "market_info": "해당 지역 평균 전세가는 3.2억원입니다.",
            "loan_info": "전세 대출 한도는 일반적으로 전세금의 80%까지 가능합니다."
        }
    )

    try:
        # 구조화된 JSON 응답 생성
        response = await llm.complete_json_async(
            prompt_name="response_synthesis",
            variables={
                "query": test_query,
                "intent_type": "legal_consult",
                "intent_confidence": "95%",
                "keywords": "전세금 인상, 법적 제한",
                "aggregated_results": json.dumps({
                    "legal": {
                        "info": "주택임대차보호법 제7조에 따르면 전세금 인상률은 5% 이내로 제한됩니다.",
                        "relevant_laws": ["주택임대차보호법"]
                    },
                    "market": {
                        "avg_price": "3.2억원",
                        "trend": "상승세"
                    }
                }, ensure_ascii=False)
            },
            temperature=0.7,
            max_tokens=1000
        )

        print("✅ JSON 응답 생성 성공!")
        print(json.dumps(response, indent=2, ensure_ascii=False))

        # 섹션 생성 테스트
        intent_info = {
            "intent_type": "legal_consult",
            "confidence": 0.95,
            "keywords": ["전세금 인상", "법적 제한"]
        }
        sections = llm._create_sections(response, intent_info)
        print("\n" + "-" * 80)
        print("생성된 UI 섹션:")
        for idx, section in enumerate(sections):
            print(f"\n섹션 {idx + 1}:")
            print(f"  제목: {section['title']}")
            print(f"  아이콘: {section.get('icon', 'none')}")
            print(f"  우선순위: {section.get('priority', 'medium')}")
            print(f"  타입: {section.get('type', 'text')}")
            if isinstance(section['content'], list):
                print(f"  내용 (리스트):")
                for item in section['content']:
                    print(f"    - {item}")
            else:
                print(f"  내용: {section['content'][:100]}..." if len(section['content']) > 100 else f"  내용: {section['content']}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_structured_response())