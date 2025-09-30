"""
LangGraph Studio Entry Point
This file serves as a bridge between LangGraph Studio and the actual implementation
"""

import sys
from pathlib import Path

# Add backend to path if needed
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service.supervisor.supervisor import RealEstateSupervisor
from app.service.core.context import create_default_llm_context

# Create supervisor instance with default LLM context
supervisor = RealEstateSupervisor(llm_context=create_default_llm_context())

# Export compiled graph for LangGraph Studio
# LangGraph Studio expects an 'app' variable with the compiled graph
app = supervisor.workflow.compile()

# Optional: Create alias for compatibility with different naming conventions
graph = app

# Optional: Export the supervisor itself if needed for advanced usage
__all__ = ['app', 'graph', 'supervisor']

if __name__ == "__main__":
    # Test that the graph compiles correctly
    print("LangGraph app compiled successfully")
    print(f"Graph nodes: {list(app.nodes.keys())}")
    print("Ready for LangGraph Studio!")