"""
Test script for AnalysisAgent
Tests both standalone and integrated (with Supervisor) functionality
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add parent directories to path
current_dir = Path(__file__).parent
service_dir = current_dir.parent
app_dir = service_dir.parent
backend_dir = app_dir.parent

sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(service_dir))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_analysis_agent_standalone():
    """Test AnalysisAgent in standalone mode"""
    logger.info("\n=== Testing AnalysisAgent Standalone ===\n")

    from agents.analysis_agent import AnalysisAgent

    # Create agent
    agent = AnalysisAgent()

    # Prepare test data (simulating SearchAgent output)
    test_input = {
        "original_query": "강남구 아파트 시장 분석해줘",
        "analysis_type": "comprehensive",
        "input_data": {
            "real_estate_search": [
                {"title": "래미안 강남", "price": "25억", "region": "강남구", "size": "35평"},
                {"title": "아크로리버뷰", "price": "30억", "region": "강남구", "size": "40평"},
                {"title": "반포자이", "price": "28억", "region": "서초구", "size": "38평"},
                {"title": "서초트라팰리스", "price": "22억", "region": "서초구", "size": "32평"}
            ],
            "loan_search": [
                {"product": "주택담보대출", "rate": "3.5%", "bank": "KB국민은행"},
                {"product": "전세자금대출", "rate": "3.2%", "bank": "신한은행"}
            ]
        },
        "shared_context": {},
        "chat_session_id": "test_session_001",
        "todos": [],
        "todo_counter": 0
    }

    try:
        # Execute agent
        logger.info("Executing AnalysisAgent...")
        result = await agent.app.ainvoke(test_input)

        # Check results
        logger.info("\n=== Analysis Results ===")
        logger.info(f"Status: {result.get('status')}")
        logger.info(f"Next Action: {result.get('next_action')}")

        if result.get('final_report'):
            report = result['final_report']
            logger.info(f"\n=== Final Report ===")
            logger.info(f"Summary: {report.get('summary')}")

            if report.get('key_findings'):
                findings = report['key_findings']
                logger.info(f"\n--- Insights ---")
                for insight in findings.get('insights', []):
                    logger.info(f"  • {insight}")

                logger.info(f"\n--- Recommendations ---")
                for rec in findings.get('recommendations', []):
                    logger.info(f"  • {rec}")

                logger.info(f"\n--- Risks ---")
                for risk in findings.get('risks', []):
                    logger.info(f"  • {risk}")

                logger.info(f"\n--- Opportunities ---")
                for opp in findings.get('opportunities', []):
                    logger.info(f"  • {opp}")

        if result.get('key_metrics'):
            logger.info(f"\n=== Key Metrics ===")
            for key, value in result['key_metrics'].items():
                logger.info(f"  {key}: {value}")

        logger.info("\n✅ AnalysisAgent standalone test completed successfully")
        return True

    except Exception as e:
        logger.error(f"❌ AnalysisAgent standalone test failed: {e}", exc_info=True)
        return False


async def test_supervisor_with_analysis():
    """Test Supervisor with SearchAgent → AnalysisAgent flow"""
    logger.info("\n=== Testing Supervisor with Analysis Flow ===\n")

    from supervisor.supervisor import RealEstateSupervisor

    # Create supervisor
    supervisor = RealEstateSupervisor()

    # Test queries that should trigger analysis
    test_queries = [
        "강남구 아파트 시장 분석해줘",
        "서초구 부동산 투자 가치 평가해줘",
        "강남구와 서초구 아파트 비교 분석",
        "최근 부동산 시장 트렌드 분석해줘"
    ]

    for query in test_queries:
        logger.info(f"\n--- Testing query: {query} ---")

        try:
            # Process query through supervisor
            result = await supervisor.process_query(
                query=query,
                session_id=f"test_session_{query[:10]}"
            )

            # Check if analysis agent was executed
            agent_results = result.get('agent_results', {})

            if 'search_agent' in agent_results:
                logger.info("✓ SearchAgent executed")
                search_status = agent_results['search_agent'].get('status')
                logger.info(f"  Status: {search_status}")

            if 'analysis_agent' in agent_results:
                logger.info("✓ AnalysisAgent executed")
                analysis_status = agent_results['analysis_agent'].get('status')
                logger.info(f"  Status: {analysis_status}")

                # Check for analysis report
                if agent_results['analysis_agent'].get('final_report'):
                    logger.info("  ✓ Analysis report generated")

            # Check final response
            final_response = result.get('final_response', {})
            if final_response:
                logger.info(f"✓ Final response type: {final_response.get('type')}")

        except Exception as e:
            logger.error(f"❌ Failed to process query '{query}': {e}")
            continue

    logger.info("\n✅ Supervisor with analysis flow test completed")
    return True


async def test_analysis_tools():
    """Test individual analysis tools"""
    logger.info("\n=== Testing Analysis Tools ===\n")

    from tools.analysis_tools import analysis_tool_registry

    # Sample data for testing
    test_data = {
        "real_estate_search": [
            {"title": "아파트1", "price": "10억", "region": "강남구"},
            {"title": "아파트2", "price": "15억", "region": "강남구"},
            {"title": "아파트3", "price": "8억", "region": "서초구"}
        ]
    }

    # Test each tool
    tools = analysis_tool_registry.list_tools()
    logger.info(f"Available tools: {tools}\n")

    for tool_name in tools:
        logger.info(f"--- Testing {tool_name} ---")
        tool = analysis_tool_registry.get(tool_name)

        if tool:
            try:
                result = await tool.execute(test_data)
                logger.info(f"  Status: {result.get('status')}")

                if result.get('status') == 'success':
                    if 'metrics' in result:
                        logger.info(f"  Metrics generated: {len(result['metrics'])} items")
                    if 'analysis' in result:
                        logger.info(f"  Analysis: {result['analysis'][:100]}...")

            except Exception as e:
                logger.error(f"  ❌ Tool {tool_name} failed: {e}")

    logger.info("\n✅ Analysis tools test completed")
    return True


async def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("Starting AnalysisAgent Tests")
    logger.info("=" * 60)

    # Run tests
    results = []

    # Test 1: Standalone AnalysisAgent
    results.append(("Standalone AnalysisAgent", await test_analysis_agent_standalone()))

    # Test 2: Analysis Tools
    results.append(("Analysis Tools", await test_analysis_tools()))

    # Test 3: Supervisor Integration
    results.append(("Supervisor Integration", await test_supervisor_with_analysis()))

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name}: {status}")

    all_passed = all(result[1] for result in results)
    if all_passed:
        logger.info("\n🎉 All tests passed successfully!")
    else:
        logger.info("\n⚠️ Some tests failed. Please check the logs.")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)