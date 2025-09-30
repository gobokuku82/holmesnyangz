#!/usr/bin/env python3
"""
Real Estate Chatbot Test Suite
테스트 및 디버깅을 위한 종합 테스트 코드
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.syntax import Syntax
from rich.live import Live
from rich.layout import Layout
import logging

# Add project root to path
current_file = Path(__file__)
tests_dir = current_file.parent      # tests
service_dir = tests_dir.parent       # service
app_dir = service_dir.parent         # app
backend_dir = app_dir.parent         # backend

if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Also add app.service to path for direct imports
sys.path.insert(0, str(backend_dir / "app" / "service"))

from supervisor.supervisor import RealEstateSupervisor
from core.context import create_default_llm_context, LLMContext
from core.todo_types import get_todo_summary

# Rich console for pretty printing
console = Console()

class ChatbotTester:
    """Enhanced tester with state inspection capabilities"""
    
    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode
        self.supervisor = None
        self.execution_history = []
        self.setup_logging()
    
    def setup_logging(self):
        """Setup enhanced logging"""
        if self.debug_mode:
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        else:
            logging.basicConfig(level=logging.INFO)
    
    async def initialize(self, api_key: Optional[str] = None):
        """Initialize supervisor with optional API key"""
        llm_context = create_default_llm_context()
        if api_key:
            llm_context.api_key = api_key
        
        self.supervisor = RealEstateSupervisor(llm_context=llm_context)
        console.print("[green][OK][/green] Supervisor initialized")
    
    async def test_query(self, query: str, session_id: str = None) -> Dict[str, Any]:
        """
        Test a single query with full state tracking
        
        Args:
            query: User query to test
            session_id: Optional session ID
        
        Returns:
            Complete execution details including state, todos, and response
        """
        if not self.supervisor:
            await self.initialize()
        
        session_id = session_id or f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        console.print(f"\n[bold blue]Testing Query:[/bold blue] {query}")
        console.print(f"[dim]Session ID: {session_id}[/dim]\n")
        
        # Create a custom workflow with state tracking
        app = self.supervisor.workflow.compile()
        
        # Initial state
        initial_state = {
            "query": query,
            "chat_session_id": session_id,
            "shared_context": {},
            "messages": [],
            "todos": [],
            "todo_counter": 0
        }
        
        # Track state changes
        state_history = []
        
        # Custom event handler to capture state changes
        async def event_handler(event):
            if self.debug_mode:
                state_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "event": event
                })
        
        # Execute with state tracking
        start_time = datetime.now()
        
        try:
            # Run the workflow
            final_state = await app.ainvoke(initial_state)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Extract key information
            result = {
                "query": query,
                "session_id": session_id,
                "execution_time": execution_time,
                "status": "success",

                # State information
                "final_state": {
                    "intent": final_state.get("intent"),
                    "intent_type": final_state.get("intent_type"),
                    "intent_confidence": final_state.get("intent_confidence"),
                    "execution_plan": final_state.get("execution_plan"),
                    "selected_agents": final_state.get("selected_agents", []),
                    "agent_results": final_state.get("agent_results", {}),
                    # AnalysisAgent specific fields
                    "analysis_type": final_state.get("analysis_type"),
                    "has_analysis": "analysis_agent" in final_state.get("agent_results", {}),
                },
                
                # TODO tracking
                "todos": final_state.get("todos", []),
                "todo_summary": get_todo_summary(final_state.get("todos", [])),
                
                # Response
                "final_response": final_state.get("final_response"),
                
                # Debug info
                "state_keys": list(final_state.keys()),
                "errors": final_state.get("errors", [])
            }
            
            # Store in history
            self.execution_history.append(result)
            
            return result
            
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            return {
                "query": query,
                "status": "error",
                "error": str(e),
                "execution_time": (datetime.now() - start_time).total_seconds()
            }
    
    def print_result(self, result: Dict[str, Any]):
        """Pretty print test results"""
        
        # 1. Basic Info
        console.print("\n[bold green]=== Execution Summary ===[/bold green]")
        info_table = Table(show_header=False)
        info_table.add_column("Field", style="cyan")
        info_table.add_column("Value")
        
        info_table.add_row("Query", result["query"])
        info_table.add_row("Status", f"[green]{result['status']}[/green]" if result['status'] == 'success' else f"[red]{result['status']}[/red]")
        info_table.add_row("Execution Time", f"{result['execution_time']:.2f}s")
        
        console.print(info_table)
        
        # 2. Intent Analysis
        if result.get("final_state", {}).get("intent"):
            console.print("\n[bold yellow]=== Intent Analysis ===[/bold yellow]")
            intent = result["final_state"]["intent"]
            intent_table = Table()
            intent_table.add_column("Property", style="cyan")
            intent_table.add_column("Value")
            
            intent_table.add_row("Intent Type", str(result["final_state"].get("intent_type", "N/A")))
            confidence = result['final_state'].get('intent_confidence')
            if confidence is not None:
                intent_table.add_row("Confidence", f"{confidence:.2%}")
            else:
                intent_table.add_row("Confidence", "N/A")
            if intent.get("entities"):
                intent_table.add_row("Entities", json.dumps(intent.get("entities"), ensure_ascii=False))
            if intent.get("keywords"):
                intent_table.add_row("Keywords", ", ".join(intent.get("keywords", [])))
            
            console.print(intent_table)
        
        # 3. Execution Plan
        if result.get("final_state", {}).get("execution_plan"):
            console.print("\n[bold magenta]=== Execution Plan ===[/bold magenta]")
            plan = result["final_state"]["execution_plan"]
            
            if plan.get("agents"):
                console.print(f"Selected Agents: {', '.join(plan['agents'])}")
            if plan.get("collection_keywords"):
                console.print(f"Keywords: {', '.join(plan['collection_keywords'])}")
            if plan.get("reasoning"):
                console.print(f"Reasoning: {plan['reasoning']}")
        
        # 4. TODO Progress
        if result.get("todos"):
            console.print("\n[bold cyan]=== TODO Progress ===[/bold cyan]")
            summary = result.get("todo_summary", {})
            
            # Progress bar
            if summary.get("total", 0) > 0:
                completed = summary.get("completed", 0)
                total = summary.get("total", 0)
                progress = summary.get("progress_percent", 0)
                
                progress_bar = f"[{'#' * int(progress/5)}{'.' * (20-int(progress/5))}]"
                console.print(f"Progress: {progress_bar} {completed}/{total} ({progress}%)")
            
            # TODO Tree
            tree = Tree("[bold]TODOs[/bold]")
            self._build_todo_tree(tree, result.get("todos", []))
            console.print(tree)
        
        # 5. Agent Results
        if result.get("final_state", {}).get("agent_results"):
            console.print("\n[bold blue]=== Agent Results ===[/bold blue]")
            for agent_name, agent_result in result["final_state"]["agent_results"].items():
                if agent_name == "analysis_agent":
                    # AnalysisAgent 특별 처리
                    content = f"Status: {agent_result.get('status', 'unknown')}\n"
                    if agent_result.get('final_report'):
                        report = agent_result['final_report']
                        content += f"Summary: {report.get('summary', 'N/A')}\n"
                        if report.get('key_findings'):
                            findings = report['key_findings']
                            content += f"Insights: {len(findings.get('insights', []))} found\n"
                            content += f"Recommendations: {len(findings.get('recommendations', []))} items\n"
                            content += f"Risks: {len(findings.get('risks', []))} identified"
                    if agent_result.get('key_metrics'):
                        metrics = agent_result['key_metrics']
                        content += f"\nKey Metrics: {', '.join(f'{k}={v}' for k, v in list(metrics.items())[:3])}"
                else:
                    # 기존 SearchAgent 및 기타 Agent 처리
                    content = f"Status: {agent_result.get('status', 'unknown')}\n"
                    content += f"Data collected: {len(agent_result.get('collected_data', {}))} sources\n"
                    content += f"Summary: {agent_result.get('search_summary', 'N/A')[:100]}..."

                agent_panel = Panel(content, title=f"[bold]{agent_name}[/bold]")
                console.print(agent_panel)
        
        # 6. Final Response
        if result.get("final_response"):
            console.print("\n[bold green]=== Final Response ===[/bold green]")
            response = result["final_response"]
            
            if isinstance(response, dict):
                if response.get("type") == "error":
                    console.print(f"[red]Error: {response.get('message')}[/red]")
                    if response.get("suggestion"):
                        console.print(f"Suggestion: {response['suggestion']}")
                elif response.get("type") == "irrelevant":
                    console.print(f"[yellow]{response.get('message')}[/yellow]")
                    if response.get("examples"):
                        console.print("Examples:")
                        for ex in response["examples"]:
                            console.print(f"  • {ex}")
                else:
                    # Pretty print JSON response
                    console.print(Syntax(
                        json.dumps(response, ensure_ascii=False, indent=2),
                        "json",
                        theme="monokai"
                    ))
            else:
                console.print(str(response))
        
        # 7. Errors (if any)
        if result.get("errors"):
            console.print("\n[bold red]=== Errors ===[/bold red]")
            for error in result["errors"]:
                console.print(f"  • {error}")
    
    def _build_todo_tree(self, tree: Tree, todos: list, level: int = 0):
        """Recursively build TODO tree"""
        for todo in todos:
            status_icon = {
                "completed": "[DONE]",
                "in_progress": "[...]",
                "failed": "[FAIL]",
                "pending": "[WAIT]",
                "skipped": "[SKIP]"
            }.get(todo.get("status", "pending"), "[?]")
            
            node_text = f"{status_icon} [{todo.get('level', 'unknown')}] {todo.get('task', 'Unknown task')}"
            
            if todo.get("subtodos"):
                branch = tree.add(node_text)
                self._build_todo_tree(branch, todo["subtodos"], level + 1)
            elif todo.get("tool_todos"):
                branch = tree.add(node_text)
                self._build_todo_tree(branch, todo["tool_todos"], level + 1)
            else:
                tree.add(node_text)
    
    async def run_test_suite(self):
        """Run a comprehensive test suite"""
        test_queries = [
            # SearchAgent queries
            ("강남구 아파트 시세 알려줘", "시세 검색"),
            ("서초구 30평대 전세 매물 찾아줘", "매물 검색"),
            ("주택담보대출 조건 알려줘", "대출 정보"),

            # AnalysisAgent queries
            ("부동산 투자 분석해줘", "투자 분석"),
            ("강남구 아파트 시장 분석해줘", "시장 분석"),
            ("서초구와 강남구 비교 분석해줘", "비교 분석"),
            ("부동산 투자 리스크 평가해줘", "리스크 평가"),
            ("최근 부동산 트렌드 분석", "트렌드 분석"),

            # Complex queries (SearchAgent + AnalysisAgent)
            ("서울 부동산 시장 전망과 강남구 아파트 투자 가치 분석해줘", "복합 질의"),

            # Edge cases
            ("안녕하세요", "인사말 처리"),
            ("날씨 어때?", "관련 없는 질의"),
            ("", "빈 쿼리"),
        ]
        
        console.print("\n[bold blue]=== Running Test Suite ===[/bold blue]\n")
        
        results = []
        for query, description in test_queries:
            console.print(f"\n[bold]Test: {description}[/bold]")
            console.rule()
            
            result = await self.test_query(query)
            self.print_result(result)
            results.append(result)
            
            # Short pause between tests
            await asyncio.sleep(1)
        
        # Summary
        self.print_test_summary(results)
    
    def print_test_summary(self, results: list):
        """Print test suite summary"""
        console.print("\n[bold green]=== Test Suite Summary ===[/bold green]")
        
        summary_table = Table()
        summary_table.add_column("Query", style="cyan")
        summary_table.add_column("Status")
        summary_table.add_column("Time (s)")
        summary_table.add_column("Intent")
        summary_table.add_column("Agents")
        
        for result in results:
            summary_table.add_row(
                result["query"][:30] + "..." if len(result["query"]) > 30 else result["query"],
                "[green][OK][/green]" if result["status"] == "success" else "[red][X][/red]",
                f"{result.get('execution_time', 0):.2f}",
                result.get("final_state", {}).get("intent_type", "N/A"),
                ", ".join(result.get("final_state", {}).get("selected_agents", []))
            )
        
        console.print(summary_table)
        
        # Statistics
        success_count = sum(1 for r in results if r["status"] == "success")
        total_time = sum(r.get("execution_time", 0) for r in results)
        
        console.print(f"\nTotal: {len(results)} | Success: {success_count} | Failed: {len(results) - success_count}")
        console.print(f"Total execution time: {total_time:.2f}s | Average: {total_time/len(results):.2f}s")


async def interactive_mode():
    """Interactive testing mode"""
    tester = ChatbotTester(debug_mode=True)
    await tester.initialize()
    
    console.print("[bold green]Real Estate Chatbot Interactive Tester[/bold green]")
    console.print("Type 'exit' to quit, 'history' to see past queries, 'clear' to clear history\n")
    
    while True:
        try:
            query = console.input("[bold blue]Enter query:[/bold blue] ")
            
            if query.lower() == 'exit':
                break
            elif query.lower() == 'history':
                for i, item in enumerate(tester.execution_history, 1):
                    console.print(f"{i}. {item['query']} - {item['status']}")
                continue
            elif query.lower() == 'clear':
                tester.execution_history.clear()
                console.print("History cleared")
                continue
            elif query.strip() == '':
                continue
            
            result = await tester.test_query(query)
            tester.print_result(result)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
    
    console.print("\n[green]Goodbye![/green]")


async def batch_test():
    """Run batch tests from file"""
    tester = ChatbotTester(debug_mode=False)
    await tester.initialize()
    await tester.run_test_suite()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Real Estate Chatbot Tester")
    parser.add_argument("--mode", choices=["interactive", "batch", "single"], default="interactive",
                       help="Test mode")
    parser.add_argument("--query", type=str, help="Single query to test (for single mode)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--api-key", type=str, help="OpenAI API key")
    
    args = parser.parse_args()
    
    if args.mode == "interactive":
        asyncio.run(interactive_mode())
    elif args.mode == "batch":
        asyncio.run(batch_test())
    elif args.mode == "single":
        if not args.query:
            console.print("[red]Error: --query required for single mode[/red]")
            return
        
        async def run_single():
            tester = ChatbotTester(debug_mode=args.debug)
            if args.api_key:
                await tester.initialize(api_key=args.api_key)
            else:
                await tester.initialize()
            result = await tester.test_query(args.query)
            tester.print_result(result)
        
        asyncio.run(run_single())


if __name__ == "__main__":
    main()