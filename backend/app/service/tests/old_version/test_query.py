"""
Query Test with Detailed Tracking
Tracks node execution, LLM decisions, and state changes
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
import sys

# Add parent directories to path
current_dir = Path(__file__).parent
service_dir = current_dir.parent
sys.path.insert(0, str(service_dir))

# Import test config first
from test_config import TestConfig, format_result, print_section_header

# Setup enhanced logging
TestConfig.setup_logging(verbose=True)

# Configure tracking logger
tracking_logger = logging.getLogger("tracking")
tracking_logger.setLevel(logging.DEBUG)

# Now import supervisor and search agent
from supervisor.supervisor import RealEstateSupervisor
from agents.search_agent import SearchAgent
from core.context import LLMContext, create_default_llm_context


@dataclass
class NodeExecution:
    """Track single node execution"""
    node_name: str
    start_time: float
    end_time: Optional[float] = None
    input_state: Dict[str, Any] = field(default_factory=dict)
    output_state: Dict[str, Any] = field(default_factory=dict)
    llm_calls: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return 0.0

    def add_llm_call(self, method: str, input_data: Any, output_data: Any):
        """Record LLM call"""
        self.llm_calls.append({
            "method": method,
            "input": input_data,
            "output": output_data,
            "timestamp": time.time()
        })


@dataclass
class ExecutionTracker:
    """Track entire execution flow"""
    query: str
    start_time: float
    nodes: List[NodeExecution] = field(default_factory=list)
    state_snapshots: List[Dict[str, Any]] = field(default_factory=list)
    current_node: Optional[NodeExecution] = None

    def start_node(self, node_name: str, input_state: Dict[str, Any]):
        """Start tracking a node"""
        self.current_node = NodeExecution(
            node_name=node_name,
            start_time=time.time(),
            input_state=self._clean_state(input_state)
        )
        tracking_logger.debug(f"[NODE START] {node_name}")

    def end_node(self, output_state: Dict[str, Any]):
        """End tracking current node"""
        if self.current_node:
            self.current_node.end_time = time.time()
            self.current_node.output_state = self._clean_state(output_state)
            self.nodes.append(self.current_node)
            tracking_logger.debug(
                f"[NODE END] {self.current_node.node_name} "
                f"(duration: {self.current_node.duration:.2f}s)"
            )
            self.current_node = None

    def add_llm_call(self, method: str, input_data: Any, output_data: Any):
        """Add LLM call to current node"""
        if self.current_node:
            self.current_node.add_llm_call(method, input_data, output_data)
            tracking_logger.debug(f"[LLM CALL] {method}")

    def snapshot_state(self, state: Dict[str, Any], label: str = ""):
        """Take state snapshot"""
        self.state_snapshots.append({
            "timestamp": time.time(),
            "label": label,
            "state": self._clean_state(state)
        })

    def _clean_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Clean state for display (remove large/sensitive data)"""
        if not state:
            return {}

        cleaned = {}
        for key, value in state.items():
            if key in ["shared_context", "agent_results", "collected_data"]:
                # Summarize large data
                if isinstance(value, dict):
                    cleaned[key] = f"<dict with {len(value)} keys>"
                elif isinstance(value, list):
                    cleaned[key] = f"<list with {len(value)} items>"
                else:
                    cleaned[key] = "<data>"
            elif isinstance(value, str) and len(value) > 200:
                cleaned[key] = value[:200] + "..."
            else:
                cleaned[key] = value

        return cleaned

    def print_summary(self):
        """Print execution summary"""
        total_duration = time.time() - self.start_time

        print("\n" + "="*70)
        print("EXECUTION TRACKING SUMMARY")
        print("="*70)
        print(f"Query: {self.query}")
        print(f"Total Duration: {total_duration:.2f}s")
        print(f"Nodes Executed: {len(self.nodes)}")

        # Node execution timeline
        print("\n" + "-"*70)
        print("NODE EXECUTION TIMELINE")
        print("-"*70)

        for i, node in enumerate(self.nodes, 1):
            print(f"\n[{i}] {node.node_name}")
            print(f"    Duration: {node.duration:.2f}s")

            # Show state changes
            if node.input_state and node.output_state:
                changed_keys = set(node.output_state.keys()) - set(node.input_state.keys())
                if changed_keys:
                    print(f"    New State Keys: {', '.join(changed_keys)}")

                # Check for value changes
                for key in node.input_state:
                    if key in node.output_state:
                        if node.input_state[key] != node.output_state[key]:
                            print(f"    Modified: {key}")

            # Show LLM calls
            if node.llm_calls:
                print(f"    LLM Calls: {len(node.llm_calls)}")
                for call in node.llm_calls:
                    print(f"      - {call['method']}")

        # LLM call summary
        total_llm_calls = sum(len(n.llm_calls) for n in self.nodes)
        if total_llm_calls > 0:
            print("\n" + "-"*70)
            print("LLM CALLS SUMMARY")
            print("-"*70)
            print(f"Total LLM Calls: {total_llm_calls}")

            # Group by method
            llm_methods = {}
            for node in self.nodes:
                for call in node.llm_calls:
                    method = call['method']
                    llm_methods[method] = llm_methods.get(method, 0) + 1

            for method, count in llm_methods.items():
                print(f"  {method}: {count} call(s)")

    def print_detailed(self):
        """Print detailed execution trace"""
        print("\n" + "="*70)
        print("DETAILED EXECUTION TRACE")
        print("="*70)

        for i, node in enumerate(self.nodes, 1):
            print(f"\n[Node {i}: {node.node_name}]")
            print(f"Duration: {node.duration:.2f}s")

            # Input state
            print("\nInput State:")
            for key, value in node.input_state.items():
                print(f"  {key}: {self._format_value(value)}")

            # LLM calls
            if node.llm_calls:
                print(f"\nLLM Calls ({len(node.llm_calls)}):")
                for j, call in enumerate(node.llm_calls, 1):
                    print(f"  [{j}] {call['method']}")
                    if isinstance(call['input'], str):
                        print(f"      Input: {call['input'][:100]}...")
                    if call['output']:
                        print(f"      Output: {self._format_value(call['output'])}")

            # Output state changes
            print("\nState Changes:")
            for key, value in node.output_state.items():
                if key not in node.input_state or node.input_state[key] != value:
                    print(f"  {key}: {self._format_value(value)}")

            print("-"*70)

    def _format_value(self, value: Any) -> str:
        """Format value for display"""
        if isinstance(value, dict):
            if len(value) <= 3:
                return str(value)
            return f"{{...{len(value)} keys...}}"
        elif isinstance(value, list):
            if len(value) <= 3:
                return str(value)
            return f"[...{len(value)} items...]"
        elif isinstance(value, str):
            if len(value) <= 100:
                return value
            return value[:100] + "..."
        else:
            return str(value)


class QueryTester:
    """Test queries with detailed tracking"""

    def __init__(self, track_nodes: bool = True, track_llm: bool = True, track_state: bool = True):
        self.supervisor = None
        self.tracker = None
        self.track_nodes = track_nodes
        self.track_llm = track_llm
        self.track_state = track_state
        self.session_id = f"test_{int(time.time())}"

    async def initialize(self):
        """Initialize supervisor with tracking"""
        print_section_header("INITIALIZING QUERY TESTER")

        try:
            # Get LLM context
            llm_context = TestConfig.get_llm_context()

            # Create supervisor
            self.supervisor = RealEstateSupervisor(llm_context=llm_context)

            # Patch supervisor for tracking if enabled
            if self.track_nodes or self.track_llm:
                self._patch_supervisor_tracking()

            print("[OK] Query Tester initialized with tracking")
            print(f"  Track Nodes: {self.track_nodes}")
            print(f"  Track LLM: {self.track_llm}")
            print(f"  Track State: {self.track_state}")

            return True

        except Exception as e:
            print(f"[ERROR] Initialization failed: {e}")
            return False

    def _patch_supervisor_tracking(self):
        """Monkey-patch supervisor methods for tracking"""
        # Save original methods
        original_analyze = self.supervisor.analyze_intent_node
        original_plan = self.supervisor.create_plan_node
        original_execute = self.supervisor.execute_agents_node
        original_response = self.supervisor.generate_response_node

        # Create wrapped versions
        async def tracked_analyze_intent(state):
            if self.tracker and self.track_nodes:
                self.tracker.start_node("analyze_intent", state)

            # Track LLM calls
            if self.tracker and self.track_llm:
                original_llm_method = self.supervisor.llm_manager.analyze_intent
                async def tracked_llm(query):
                    result = await original_llm_method(query)
                    self.tracker.add_llm_call("analyze_intent", query, result)
                    return result
                self.supervisor.llm_manager.analyze_intent = tracked_llm

            result = await original_analyze(state)

            if self.tracker and self.track_nodes:
                self.tracker.end_node(result)

            return result

        async def tracked_plan(state):
            if self.tracker and self.track_nodes:
                self.tracker.start_node("create_plan", state)

            if self.tracker and self.track_llm:
                original_llm_method = self.supervisor.llm_manager.create_plan
                async def tracked_llm(intent, query):
                    result = await original_llm_method(intent, query)
                    self.tracker.add_llm_call("create_plan", {"intent": intent, "query": query}, result)
                    return result
                self.supervisor.llm_manager.create_plan = tracked_llm

            result = await original_plan(state)

            if self.tracker and self.track_nodes:
                self.tracker.end_node(result)

            return result

        async def tracked_execute(state):
            if self.tracker and self.track_nodes:
                self.tracker.start_node("execute_agents", state)

            result = await original_execute(state)

            if self.tracker and self.track_nodes:
                self.tracker.end_node(result)

            return result

        async def tracked_response(state):
            if self.tracker and self.track_nodes:
                self.tracker.start_node("generate_response", state)

            if self.tracker and self.track_llm:
                original_llm_method = self.supervisor.llm_manager.generate_response
                async def tracked_llm(state):
                    result = await original_llm_method(state)
                    self.tracker.add_llm_call("generate_response",
                                             {"query": state.get("query"),
                                              "intent": state.get("intent_type")},
                                             result)
                    return result
                self.supervisor.llm_manager.generate_response = tracked_llm

            result = await original_response(state)

            if self.tracker and self.track_nodes:
                self.tracker.end_node(result)

            return result

        # Apply patches
        self.supervisor.analyze_intent_node = tracked_analyze_intent
        self.supervisor.create_plan_node = tracked_plan
        self.supervisor.execute_agents_node = tracked_execute
        self.supervisor.generate_response_node = tracked_response

    async def test_query(self, query: str, detailed: bool = False) -> Dict[str, Any]:
        """
        Test a query with tracking

        Args:
            query: Query to test
            detailed: Show detailed trace

        Returns:
            Test results
        """
        print_section_header(f"TESTING: {query}")

        # Create tracker
        self.tracker = ExecutionTracker(query=query, start_time=time.time())

        try:
            # Execute query
            print("\n[EXECUTING] Running query through supervisor...")

            result = await self.supervisor.process_query(
                query=query,
                session_id=self.session_id,
                llm_context=TestConfig.get_llm_context()
            )

            # Print tracking summary
            if self.track_nodes or self.track_llm:
                self.tracker.print_summary()

                if detailed:
                    self.tracker.print_detailed()

            # Print result
            print("\n" + "-"*70)
            print("QUERY RESULT")
            print("-"*70)
            print(format_result(result))

            return {
                "status": "success",
                "result": result,
                "tracking": {
                    "nodes_executed": len(self.tracker.nodes),
                    "total_duration": time.time() - self.tracker.start_time,
                    "llm_calls": sum(len(n.llm_calls) for n in self.tracker.nodes)
                }
            }

        except Exception as e:
            print(f"\n[ERROR] Query execution failed: {e}")

            if self.tracker and self.tracker.nodes:
                print("\nPartial execution trace:")
                self.tracker.print_summary()

            return {
                "status": "error",
                "error": str(e)
            }


async def run_interactive(tester, detailed=False):
    """Run interactive query test mode"""
    print("\n" + "="*60)
    print("INTERACTIVE QUERY TEST MODE")
    print("="*60)
    print("Commands:")
    print("  'quit' or 'exit' - Exit the program")
    print("  'detailed on/off' - Toggle detailed mode")
    print("  'clear' - Clear screen")
    print("  Any other text - Test as query")
    print("="*60)

    current_detailed = detailed

    while True:
        try:
            query = input("\nEnter query: ").strip()

            if not query:
                continue

            if query.lower() in ['quit', 'exit']:
                print("\nGoodbye!")
                break

            elif query.lower().startswith('detailed'):
                parts = query.split()
                if len(parts) > 1:
                    if parts[1].lower() == 'on':
                        current_detailed = True
                        print("[OK] Detailed mode: ON")
                    elif parts[1].lower() == 'off':
                        current_detailed = False
                        print("[OK] Detailed mode: OFF")
                    else:
                        print(f"[INFO] Detailed mode is {'ON' if current_detailed else 'OFF'}")
                else:
                    print(f"[INFO] Detailed mode is {'ON' if current_detailed else 'OFF'}")

            elif query.lower() == 'clear':
                import os
                os.system('cls' if os.name == 'nt' else 'clear')
                print("\n" + "="*60)
                print("INTERACTIVE QUERY TEST MODE")
                print("="*60)

            else:
                # Test the query
                await tester.test_query(query, detailed=current_detailed)

        except KeyboardInterrupt:
            print("\n\n[WARNING] Interrupted. Type 'quit' to exit.")
            continue
        except Exception as e:
            print(f"\n[ERROR] Unexpected error: {e}")
            continue


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Test query with tracking")
    parser.add_argument("query", nargs="?", default=None,
                       help="Query to test (optional if using interactive mode)")
    parser.add_argument("--no-track-nodes", action="store_true",
                       help="Disable node tracking")
    parser.add_argument("--no-track-llm", action="store_true",
                       help="Disable LLM tracking")
    parser.add_argument("--no-track-state", action="store_true",
                       help="Disable state tracking")
    parser.add_argument("--detailed", action="store_true",
                       help="Show detailed trace")
    parser.add_argument("-i", "--interactive", action="store_true",
                       help="Interactive mode - enter queries manually")

    args = parser.parse_args()

    # Create tester
    tester = QueryTester(
        track_nodes=not args.no_track_nodes,
        track_llm=not args.no_track_llm,
        track_state=not args.no_track_state
    )

    # Initialize
    if not await tester.initialize():
        print("Failed to initialize tester")
        return

    # Check mode and run
    if args.interactive or args.query is None:
        # Run interactive mode
        print("[INFO] Starting interactive mode...")
        await run_interactive(tester, detailed=args.detailed)
    else:
        # Test single query
        await tester.test_query(args.query, detailed=args.detailed)


if __name__ == "__main__":
    asyncio.run(main())