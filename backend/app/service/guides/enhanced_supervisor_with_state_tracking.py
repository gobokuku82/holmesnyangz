"""
Enhanced Supervisor with State Tracking
기존 supervisor.py에 추가할 수 있는 상태 추적 기능
"""

from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from dataclasses import dataclass, field
import asyncio

@dataclass
class StateSnapshot:
    """State snapshot for tracking"""
    timestamp: datetime
    node: str
    state_diff: Dict[str, Any]
    todos: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


class StateTracker:
    """
    State tracking wrapper for debugging
    기존 Supervisor에 추가할 수 있는 상태 추적 클래스
    """
    
    def __init__(self):
        self.snapshots: List[StateSnapshot] = []
        self.node_execution_times: Dict[str, float] = {}
        self.state_changes: List[Dict[str, Any]] = []
    
    def capture_snapshot(self, node_name: str, state: Dict[str, Any], prev_state: Dict[str, Any] = None):
        """Capture state snapshot"""
        # Calculate state diff
        state_diff = {}
        if prev_state:
            for key in state:
                if key not in prev_state or state[key] != prev_state[key]:
                    state_diff[key] = {
                        "old": prev_state.get(key),
                        "new": state[key]
                    }
        else:
            state_diff = {"initial": state}
        
        snapshot = StateSnapshot(
            timestamp=datetime.now(),
            node=node_name,
            state_diff=state_diff,
            todos=state.get("todos", []).copy(),
            metadata={
                "errors": state.get("errors", []).copy(),
                "agent_results": list(state.get("agent_results", {}).keys())
            }
        )
        
        self.snapshots.append(snapshot)
    
    def get_execution_flow(self) -> List[Dict[str, Any]]:
        """Get execution flow summary"""
        flow = []
        for snapshot in self.snapshots:
            flow.append({
                "timestamp": snapshot.timestamp.isoformat(),
                "node": snapshot.node,
                "changes": list(snapshot.state_diff.keys()),
                "todo_count": len(snapshot.todos),
                "errors": len(snapshot.metadata.get("errors", []))
            })
        return flow
    
    def get_todo_timeline(self) -> List[Dict[str, Any]]:
        """Get TODO progression timeline"""
        timeline = []
        for snapshot in self.snapshots:
            todo_summary = self._summarize_todos(snapshot.todos)
            timeline.append({
                "node": snapshot.node,
                "timestamp": snapshot.timestamp.isoformat(),
                **todo_summary
            })
        return timeline
    
    def _summarize_todos(self, todos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize TODO states"""
        summary = {
            "total": 0,
            "completed": 0,
            "in_progress": 0,
            "failed": 0,
            "pending": 0
        }
        
        def count_todos(todo_list):
            for todo in todo_list:
                summary["total"] += 1
                status = todo.get("status", "pending")
                if status in summary:
                    summary[status] += 1
                
                # Count nested todos
                if "subtodos" in todo:
                    count_todos(todo["subtodos"])
                if "tool_todos" in todo:
                    count_todos(todo["tool_todos"])
        
        count_todos(todos)
        return summary


class EnhancedRealEstateSupervisor(RealEstateSupervisor):
    """
    Enhanced Supervisor with state tracking capabilities
    Inherits from original supervisor and adds tracking
    """
    
    def __init__(self, llm_context: LLMContext = None, enable_tracking: bool = True):
        super().__init__(llm_context)
        self.enable_tracking = enable_tracking
        self.state_tracker = StateTracker() if enable_tracking else None
        self.prev_state = None
    
    async def _track_node_execution(self, node_name: str, node_func, state: Dict[str, Any]) -> Dict[str, Any]:
        """Wrapper to track node execution"""
        if not self.enable_tracking:
            return await node_func(state)
        
        # Capture before state
        self.state_tracker.capture_snapshot(f"{node_name}_start", state, self.prev_state)
        
        # Execute node
        start_time = datetime.now()
        result = await node_func(state)
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Update state with result
        new_state = {**state, **result}
        
        # Capture after state
        self.state_tracker.capture_snapshot(f"{node_name}_end", new_state, state)
        self.state_tracker.node_execution_times[node_name] = execution_time
        
        # Store for next comparison
        self.prev_state = new_state.copy()
        
        return result
    
    # Override each node method to add tracking
    async def analyze_intent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Wrapped analyze_intent_node with tracking"""
        return await self._track_node_execution(
            "analyze_intent",
            super().analyze_intent_node,
            state
        )
    
    async def create_plan_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Wrapped create_plan_node with tracking"""
        return await self._track_node_execution(
            "create_plan",
            super().create_plan_node,
            state
        )
    
    async def execute_agents_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Wrapped execute_agents_node with tracking"""
        return await self._track_node_execution(
            "execute_agents",
            super().execute_agents_node,
            state
        )
    
    async def generate_response_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Wrapped generate_response_node with tracking"""
        return await self._track_node_execution(
            "generate_response",
            super().generate_response_node,
            state
        )
    
    async def process_query_with_tracking(
        self,
        query: str,
        session_id: str = None,
        llm_context: LLMContext = None
    ) -> Dict[str, Any]:
        """
        Process query with full state tracking
        
        Returns:
            Complete execution details including tracking data
        """
        # Reset tracker for new query
        if self.enable_tracking:
            self.state_tracker = StateTracker()
            self.prev_state = None
        
        # Process query
        final_state = await self.process_query(query, session_id, llm_context)
        
        # Compile tracking results
        if self.enable_tracking:
            tracking_data = {
                "execution_flow": self.state_tracker.get_execution_flow(),
                "todo_timeline": self.state_tracker.get_todo_timeline(),
                "node_times": self.state_tracker.node_execution_times,
                "total_snapshots": len(self.state_tracker.snapshots),
                "state_changes": self.state_tracker.state_changes
            }
        else:
            tracking_data = None
        
        return {
            "final_state": final_state,
            "tracking_data": tracking_data
        }
    
    def get_debug_report(self) -> Dict[str, Any]:
        """Generate comprehensive debug report"""
        if not self.enable_tracking:
            return {"error": "Tracking not enabled"}
        
        return {
            "execution_summary": {
                "total_nodes_executed": len(self.state_tracker.node_execution_times),
                "total_execution_time": sum(self.state_tracker.node_execution_times.values()),
                "slowest_node": max(self.state_tracker.node_execution_times.items(), 
                                   key=lambda x: x[1]) if self.state_tracker.node_execution_times else None
            },
            "state_evolution": [
                {
                    "snapshot_index": i,
                    "node": snapshot.node,
                    "timestamp": snapshot.timestamp.isoformat(),
                    "changes_made": len(snapshot.state_diff),
                    "todo_state": self.state_tracker._summarize_todos(snapshot.todos)
                }
                for i, snapshot in enumerate(self.state_tracker.snapshots)
            ],
            "todo_progression": self.state_tracker.get_todo_timeline(),
            "execution_flow": self.state_tracker.get_execution_flow()
        }


# Example usage function
async def test_with_enhanced_tracking():
    """Example of using enhanced supervisor"""
    
    # Create enhanced supervisor
    supervisor = EnhancedRealEstateSupervisor(enable_tracking=True)
    
    # Test query
    query = "강남구 아파트 시세 분석해줘"
    
    print(f"Testing query: {query}\n")
    
    # Process with tracking
    result = await supervisor.process_query_with_tracking(query)
    
    # Get debug report
    debug_report = supervisor.get_debug_report()
    
    # Print results
    print("=== FINAL RESPONSE ===")
    print(json.dumps(result["final_state"].get("final_response"), 
                     ensure_ascii=False, indent=2))
    
    print("\n=== EXECUTION FLOW ===")
    for step in debug_report["execution_flow"]:
        print(f"  {step['node']:20s} | Changes: {len(step['changes']):3d} | TODOs: {step['todo_count']:3d}")
    
    print("\n=== TODO PROGRESSION ===")
    for timeline in debug_report["todo_progression"]:
        print(f"  {timeline['node']:20s} | Total: {timeline['total']:3d} | "
              f"Completed: {timeline['completed']:3d} | "
              f"Progress: {timeline['in_progress']:3d}")
    
    print("\n=== NODE EXECUTION TIMES ===")
    for node, time in supervisor.state_tracker.node_execution_times.items():
        print(f"  {node:20s} | {time:.3f}s")
    
    print("\n=== STATE SNAPSHOTS ===")
    print(f"Total snapshots captured: {len(supervisor.state_tracker.snapshots)}")
    
    return result


if __name__ == "__main__":
    # Run test
    asyncio.run(test_with_enhanced_tracking())