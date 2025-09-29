"""
Interactive Test for Real Estate Chatbot
Allows direct query input and real-time testing
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional

# Import test config first to set up paths
from test_config import TestConfig, format_result, print_section_header

# Setup logging
TestConfig.setup_logging(verbose=True)

# Now import supervisor and search agent after paths are configured
from supervisor.supervisor import RealEstateSupervisor
from subgraphs.search_agent import SearchAgent


class InteractiveTester:
    """Interactive test runner for the chatbot"""

    def __init__(self):
        self.supervisor = None
        self.search_agent = None
        self.session_id = f"interactive_test_{int(time.time())}"
        self.query_history = []

    async def initialize(self):
        """Initialize the supervisor and agents"""
        print_section_header("INITIALIZING SYSTEM")

        try:
            # Get LLM context from TestConfig
            llm_context = TestConfig.get_llm_context()

            # Create agent context for testing
            agent_context = TestConfig.create_test_agent_context(
                chat_session_id=self.session_id
            )

            # Initialize supervisor with LLM context
            self.supervisor = RealEstateSupervisor(
                llm_context=llm_context
            )
            print("[OK] Supervisor initialized with LLMContext")

            # Initialize search agent with LLM context
            self.search_agent = SearchAgent(
                llm_context=llm_context
            )
            print("[OK] Search Agent initialized with LLMContext")

            # Store context for later use
            self.agent_context = agent_context
            self.llm_context = llm_context

            # Print current mode
            TestConfig.print_config()

            return True

        except Exception as e:
            print(f"[ERROR] Initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def test_query(self, query: str) -> Dict[str, Any]:
        """
        Test a single query

        Args:
            query: User query to test

        Returns:
            Test result dictionary
        """
        print_section_header(f"TESTING QUERY: {query}")

        # Record start time
        start_time = time.time()

        try:
            # Process query through supervisor with LLM context
            print("\n[PROCESSING] Processing through Supervisor...")
            result = await self.supervisor.process_query(
                query=query,
                session_id=self.session_id,
                llm_context=self.llm_context  # Pass the LLM context
            )

            # Calculate execution time
            execution_time = time.time() - start_time

            # Store in history
            self.query_history.append({
                "query": query,
                "result": result,
                "execution_time": execution_time,
                "status": "success"
            })

            # Display results
            self._display_results(result, execution_time)

            return {
                "status": "success",
                "result": result,
                "execution_time": execution_time
            }

        except Exception as e:
            execution_time = time.time() - start_time

            print(f"\n[ERROR] Error occurred: {e}")

            self.query_history.append({
                "query": query,
                "error": str(e),
                "execution_time": execution_time,
                "status": "error"
            })

            return {
                "status": "error",
                "error": str(e),
                "execution_time": execution_time
            }

    def _display_results(self, result: Dict[str, Any], execution_time: float):
        """Display formatted results"""
        print("\n" + "-"*60)
        print("RESULTS")
        print("-"*60)

        # Check result type
        if isinstance(result, dict):
            result_type = result.get("type", "unknown")
            print(f"Result Type: {result_type}")

            # Display summary if available
            if "summary" in result:
                print(f"\nSummary:\n{result['summary']}")

            # Display data based on type
            if result_type == "direct":
                print("\nDirect Output:")
                content = result.get("content", {})
                print(format_result(content, indent=1))

            elif result_type == "processed":
                print("\nProcessed Results:")
                # Show intent
                if "intent" in result:
                    print(f"  Intent: {result['intent']}")

                # Show data
                if "data" in result:
                    print("\n  Collected Data:")
                    print(format_result(result["data"], indent=2))

                # Show agent results
                if "agent_results" in result:
                    print("\n  Agent Results:")
                    for agent, agent_result in result["agent_results"].items():
                        status = agent_result.get("status", "unknown")
                        print(f"    {agent}: {status}")

            else:
                # Generic display
                print(format_result(result, indent=1))

        else:
            print(f"Result: {result}")

        print(f"\nExecution Time: {execution_time:.2f} seconds")
        print("-"*60)

    async def run_interactive_session(self):
        """Run interactive test session"""
        print("\n" + "="*60)
        print("REAL ESTATE CHATBOT - INTERACTIVE TEST")
        print("="*60)
        print("\nCommands:")
        print("  'quit' or 'exit' - Exit the test")
        print("  'mode <mock/openai>' - Switch LLM mode")
        print("  'history' - Show query history")
        print("  'clear' - Clear screen")
        print("="*60)

        # Initialize system
        if not await self.initialize():
            print("Failed to initialize. Exiting.")
            return

        # Main interaction loop
        while True:
            try:
                # Get user input
                print("\n")
                query = input("Enter your query: ").strip()

                # Check for commands
                if query.lower() in ["quit", "exit"]:
                    print("\nGoodbye!")
                    break

                elif query.lower().startswith("mode "):
                    mode = query[5:].strip()
                    try:
                        TestConfig.set_llm_mode(mode)
                        # Reinitialize with new mode
                        await self.initialize()
                        print(f"[OK] Switched to {mode} mode")
                    except ValueError as e:
                        print(f"[ERROR] {e}")
                    continue

                elif query.lower() == "history":
                    self._show_history()
                    continue

                elif query.lower() == "clear":
                    import os
                    os.system('cls' if os.name == 'nt' else 'clear')
                    continue

                elif not query:
                    continue

                # Process the query
                await self.test_query(query)

            except KeyboardInterrupt:
                print("\n\n[WARNING] Interrupted. Type 'quit' to exit properly.")
                continue

            except Exception as e:
                print(f"\n[ERROR] Unexpected error: {e}")
                continue

        # Show final summary
        self._show_summary()

    def _show_history(self):
        """Show query history"""
        print_section_header("QUERY HISTORY")

        if not self.query_history:
            print("No queries in history")
            return

        for i, item in enumerate(self.query_history, 1):
            status = "[OK]" if item["status"] == "success" else "[FAIL]"
            print(f"\n{i}. {status} {item['query']}")
            print(f"   Time: {item['execution_time']:.2f}s")

            if item["status"] == "error":
                print(f"   Error: {item['error']}")

    def _show_summary(self):
        """Show session summary"""
        print_section_header("SESSION SUMMARY")

        if not self.query_history:
            print("No queries were executed")
            return

        total_queries = len(self.query_history)
        successful = sum(1 for q in self.query_history if q["status"] == "success")
        failed = total_queries - successful
        avg_time = sum(q["execution_time"] for q in self.query_history) / total_queries

        print(f"Total Queries: {total_queries}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Average Time: {avg_time:.2f} seconds")
        print(f"Session ID: {self.session_id}")


async def test_single_query():
    """Test a single query directly"""
    print_section_header("SINGLE QUERY TEST")

    # Get query from command line or use default
    import sys
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "강남구 아파트 매매 시세 알려줘"

    print(f"Testing query: {query}")

    # Initialize and test
    tester = InteractiveTester()
    if await tester.initialize():
        await tester.test_query(query)


def main():
    """Main entry point"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] != "interactive":
        # Single query mode
        asyncio.run(test_single_query())
    else:
        # Interactive mode
        tester = InteractiveTester()
        asyncio.run(tester.run_interactive_session())


if __name__ == "__main__":
    main()