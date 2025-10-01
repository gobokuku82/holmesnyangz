"""
Query Test - Interactive Query Testing System
Allows users to input queries and see the full execution process with TODO tracking
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
import logging

# Setup paths
current_dir = Path(__file__).parent
service_dir = current_dir.parent
backend_dir = service_dir.parent.parent

sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / "app" / "service"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import required modules
try:
    from supervisor.supervisor import RealEstateSupervisor
    from core.context import create_default_llm_context
    from core.todo_types import get_todo_summary, find_todo
    from dotenv import load_dotenv

    # Load environment
    env_path = backend_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[OK] Loaded environment from: {env_path}")
    else:
        print(f"[WARNING] No .env file found at: {env_path}")

except ImportError as e:
    print(f"[FATAL] Import error: {e}")
    sys.exit(1)


class QueryTester:
    """Interactive query testing system"""

    def __init__(self):
        """Initialize the query tester"""
        self.supervisor = None
        self.llm_context = None
        self.session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.query_history = []

    async def initialize(self):
        """Initialize supervisor and context"""
        print("\n" + "="*70)
        print("INITIALIZING QUERY TESTER")
        print("="*70)

        try:
            # Create LLM context
            self.llm_context = create_default_llm_context()
            print("[OK] LLM context created")

            # Create supervisor
            self.supervisor = RealEstateSupervisor(llm_context=self.llm_context)
            print("[OK] Supervisor initialized")
            print(f"[OK] Session ID: {self.session_id}")

            return True

        except Exception as e:
            print(f"[ERROR] Initialization failed: {e}")
            return False

    def display_todos(self, todos, indent=0):
        """Display TODO hierarchy"""
        if not todos:
            return

        for todo in todos:
            status_symbol = {
                "completed": "✓",
                "in_progress": "→",
                "pending": "○",
                "failed": "✗"
            }.get(todo.get("status", "pending"), "?")

            prefix = "  " * indent
            print(f"{prefix}[{status_symbol}] {todo.get('task', 'Unknown')} (ID: {todo.get('id', 'N/A')})")

            # Display subtodos
            if "subtodos" in todo and todo["subtodos"]:
                self.display_todos(todo["subtodos"], indent + 1)

            # Display tool todos
            if "tool_todos" in todo and todo["tool_todos"]:
                self.display_todos(todo["tool_todos"], indent + 1)

    async def test_query(self, query: str, show_details: bool = True):
        """Test a single query"""
        print("\n" + "="*70)
        print(f"TESTING QUERY: {query}")
        print("="*70)

        # Add to history
        self.query_history.append({
            "query": query,
            "timestamp": datetime.now().isoformat()
        })

        try:
            # Process query
            print("\n[1] STARTING QUERY PROCESSING")
            print("-"*50)

            start_time = datetime.now()

            result = await self.supervisor.process_query(
                query=query,
                session_id=self.session_id,
                llm_context=self.llm_context
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Show execution time
            print(f"\n[2] EXECUTION COMPLETED")
            print(f"Duration: {duration:.2f} seconds")
            print("-"*50)

            # Show intent analysis
            if "intent" in result:
                print("\n[3] INTENT ANALYSIS")
                print("-"*50)
                intent = result["intent"]
                print(f"Intent Type: {intent.get('intent_type', 'unknown')}")
                print(f"Confidence: {intent.get('confidence', 0):.2f}")

                if intent.get("entities"):
                    print("Entities:")
                    for key, value in intent["entities"].items():
                        if value:
                            print(f"  - {key}: {value}")

            # Show execution plan
            if "execution_plan" in result:
                print("\n[4] EXECUTION PLAN")
                print("-"*50)
                plan = result["execution_plan"]
                if "agents" in plan:
                    print(f"Selected Agents: {plan['agents']}")
                if "collection_keywords" in plan:
                    print(f"Keywords: {plan['collection_keywords']}")
                if "reasoning" in plan:
                    print(f"Reasoning: {plan['reasoning']}")

            # Show TODO progress
            if "todos" in result and result["todos"]:
                print("\n[5] TODO TRACKING")
                print("-"*50)

                todos = result["todos"]
                summary = get_todo_summary(todos)

                print(f"Progress: {summary['summary']}")
                print(f"  - Total: {summary['total']}")
                print(f"  - Completed: {summary['completed']}")
                print(f"  - In Progress: {summary['in_progress']}")
                print(f"  - Pending: {summary['pending']}")
                print(f"  - Failed: {summary['failed']}")

                if show_details:
                    print("\nTODO Hierarchy:")
                    self.display_todos(todos)

            # Show agent results
            if "agent_results" in result:
                print("\n[6] AGENT RESULTS")
                print("-"*50)

                for agent_name, agent_result in result["agent_results"].items():
                    print(f"\n{agent_name}:")
                    print(f"  Status: {agent_result.get('status', 'unknown')}")

                    if "collected_data" in agent_result:
                        data = agent_result["collected_data"]
                        for source, items in data.items():
                            if isinstance(items, list):
                                print(f"  {source}: {len(items)} results")
                            else:
                                print(f"  {source}: Data collected")

                    if "data_summary" in agent_result:
                        print(f"  Summary: {agent_result['data_summary']}")

            # Show final response
            if "final_response" in result:
                print("\n[7] FINAL RESPONSE")
                print("-"*50)

                response = result["final_response"]

                if "type" in response:
                    print(f"Response Type: {response['type']}")

                if "message" in response:
                    print(f"\nMessage: {response['message']}")

                if "data" in response and response["data"]:
                    print(f"\nData Sources: {len(response['data'])}")
                    for source, items in response["data"].items():
                        if isinstance(items, list):
                            print(f"  - {source}: {len(items)} items")
                            # Show first item as sample
                            if items and show_details:
                                print(f"    Sample: {json.dumps(items[0], ensure_ascii=False, indent=2)[:200]}...")

                if "suggestion" in response:
                    print(f"\nSuggestion: {response['suggestion']}")

                if "examples" in response:
                    print("\nExamples:")
                    for example in response["examples"]:
                        print(f"  - {example}")

            return result

        except Exception as e:
            print(f"\n[ERROR] Query processing failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def run_interactive(self):
        """Run interactive query testing mode"""
        print("\n" + "="*70)
        print("INTERACTIVE QUERY TESTING MODE")
        print("="*70)
        print("\nCommands:")
        print("  'quit' or 'exit' - Exit the program")
        print("  'history' - Show query history")
        print("  'details on/off' - Toggle detailed output")
        print("  'clear' - Clear screen")
        print("  Any other text - Test as query")
        print("="*70)

        show_details = True

        while True:
            try:
                # Get user input
                print("\n")
                query = input("Enter query > ").strip()

                if not query:
                    continue

                # Handle commands
                if query.lower() in ['quit', 'exit']:
                    print("\nExiting...")
                    break

                elif query.lower() == 'history':
                    print("\n" + "-"*50)
                    print("QUERY HISTORY")
                    print("-"*50)
                    for i, h in enumerate(self.query_history, 1):
                        print(f"{i}. [{h['timestamp']}] {h['query']}")
                    continue

                elif query.lower() == 'details on':
                    show_details = True
                    print("[OK] Detailed output enabled")
                    continue

                elif query.lower() == 'details off':
                    show_details = False
                    print("[OK] Detailed output disabled")
                    continue

                elif query.lower() == 'clear':
                    import os
                    os.system('cls' if os.name == 'nt' else 'clear')
                    continue

                # Process the query
                await self.test_query(query, show_details)

            except KeyboardInterrupt:
                print("\n\nInterrupted by user")
                break

            except Exception as e:
                print(f"\n[ERROR] {e}")
                continue

        # Show final statistics
        print("\n" + "="*70)
        print("SESSION SUMMARY")
        print("="*70)
        print(f"Total queries tested: {len(self.query_history)}")
        print(f"Session ID: {self.session_id}")

    async def run_predefined_tests(self):
        """Run predefined test queries"""
        print("\n" + "="*70)
        print("RUNNING PREDEFINED TESTS")
        print("="*70)

        test_queries = [
            # Normal queries
            ("강남구 아파트 시세 알려줘", "Real estate price query"),
            ("전세 대출 조건이 뭐야?", "Loan information query"),
            ("부동산 계약서 작성 방법", "Legal information query"),

            # Edge cases
            ("바부야", "Irrelevant query - should be filtered"),
            ("안녕하세요", "Greeting - should be filtered"),
            ("오늘 날씨 어때?", "Off-topic - should be filtered"),

            # Complex queries
            ("강남구와 서초구 아파트 가격 비교 분석해줘", "Analysis query"),
            ("투자하기 좋은 지역 추천해줘", "Recommendation query"),
        ]

        results = []

        for query, description in test_queries:
            print(f"\n[TEST] {description}")
            print(f"Query: {query}")

            result = await self.test_query(query, show_details=False)

            if result:
                intent_type = result.get("intent", {}).get("intent_type", "unknown")
                final_type = result.get("final_response", {}).get("type", "unknown")

                results.append({
                    "query": query,
                    "description": description,
                    "intent": intent_type,
                    "response_type": final_type,
                    "success": True
                })

                print(f"Result: Intent={intent_type}, Response={final_type}")
            else:
                results.append({
                    "query": query,
                    "description": description,
                    "success": False
                })
                print(f"Result: FAILED")

        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)

        success_count = sum(1 for r in results if r["success"])
        print(f"Total tests: {len(results)}")
        print(f"Successful: {success_count}")
        print(f"Failed: {len(results) - success_count}")

        # Show details
        print("\nResults by query:")
        for r in results:
            status = "OK" if r["success"] else "FAIL"
            print(f"  [{status}] {r['query'][:30]}...")
            if r["success"]:
                print(f"        Intent: {r['intent']}, Response: {r['response_type']}")

        return results


async def main():
    """Main entry point"""
    print("\n" + "="*70)
    print("QUERY TEST SYSTEM")
    print("="*70)

    # Create tester
    tester = QueryTester()

    # Initialize
    if not await tester.initialize():
        print("[FATAL] Failed to initialize")
        return

    # Ask for mode
    print("\nSelect mode:")
    print("1. Interactive mode (input queries manually)")
    print("2. Predefined tests (run test suite)")
    print("3. Single query test")

    choice = input("\nEnter choice (1/2/3) > ").strip()

    if choice == "1":
        await tester.run_interactive()

    elif choice == "2":
        await tester.run_predefined_tests()

    elif choice == "3":
        query = input("Enter query to test > ").strip()
        if query:
            await tester.test_query(query, show_details=True)

    else:
        print("Invalid choice")

    print("\n[END] Query test completed")


if __name__ == "__main__":
    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user")
    except Exception as e:
        print(f"\n[FATAL] Program error: {e}")
        import traceback
        traceback.print_exc()