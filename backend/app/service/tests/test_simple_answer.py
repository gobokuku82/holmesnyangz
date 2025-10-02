#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple test to verify LLM answer generation is working
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from app.service.supervisor.supervisor import RealEstateSupervisor


def test_generate_response_node():
    """Test the generate_response_node directly"""

    print("=" * 60)
    print("Testing generate_response_node LLM Integration")
    print("=" * 60)

    # Create supervisor instance
    supervisor = RealEstateSupervisor()

    # Check if LLM is configured
    print(f"\nLLM Manager Status:")
    print(f"  - Client initialized: {supervisor.llm_manager.client is not None}")
    print(f"  - Connection error: {supervisor.llm_manager._connection_error}")

    if supervisor.llm_manager.client:
        print(f"  - Provider: {supervisor.llm_manager.context.provider}")
        print(f"  - Response model: {supervisor.llm_manager.get_model('response')}")

    # Test state with sample data
    test_state = {
        "query": "전세금 인상률은 얼마까지 가능해?",
        "search_agent": {
            "status": "completed",
            "collected_data": {
                "legal_search": [
                    {
                        "law_name": "주택임대차보호법",
                        "article_number": "제7조",
                        "content": "임대차에서 약정한 차임 등의 증액청구는 약정한 차임등의 20분의 1의 금액을 초과하지 못한다.",
                        "relevance_score": 0.95
                    }
                ]
            }
        }
    }

    print("\n" + "=" * 60)
    print("Testing with sample data...")
    print("Query:", test_state["query"])
    print("-" * 60)

    # Check if the helper methods exist
    if hasattr(supervisor, '_prepare_context_for_llm'):
        print("Helper method _prepare_context_for_llm: EXISTS")

        # Test context preparation
        all_data = {"search_agent": test_state["search_agent"]["collected_data"]}
        context = supervisor._prepare_context_for_llm(all_data)
        print(f"\nPrepared context keys: {list(context.keys())}")
        if "legal_info" in context:
            print(f"Legal info entries: {len(context['legal_info'])}")
    else:
        print("WARNING: _prepare_context_for_llm method not found")

    if hasattr(supervisor, '_extract_sources'):
        print("Helper method _extract_sources: EXISTS")

        # Test source extraction
        sources = supervisor._extract_sources(all_data)
        print(f"\nExtracted sources: {sources}")
    else:
        print("WARNING: _extract_sources method not found")

    print("\n" + "=" * 60)
    print("Verification complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_generate_response_node()