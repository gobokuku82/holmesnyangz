# LangGraph 0.6.6 Rules - Quick Reference
**⚠️ THIS PROJECT USES LANGGRAPH 0.6.6 (NOT 0.2.x)**

## 1. Correct Imports (ALWAYS USE THESE)
```python
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
```

## 2. State Definition Pattern
```python
# Option 1: Custom State with Reducer
from typing import Annotated

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]  # Reducer for messages
    current_step: str
    context: dict

# Option 2: Extend MessagesState
class State(MessagesState):
    additional_field: str
    metadata: dict
```

## 3. Graph Construction Pattern
```python
# ALWAYS follow this pattern
graph = StateGraph(State)  # NOT Graph() or MessageGraph()

# Add nodes
graph.add_node("agent", agent_function)

# Add edges
graph.add_edge(START, "agent")  # Entry point
graph.add_edge("agent", END)     # Exit point

# Conditional edges
graph.add_conditional_edges(
    "agent",
    routing_function,  # Returns string matching route keys
    {"route1": "node1", "route2": "node2", "end": END}
)

# Compile with checkpointer
checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer)
```

## 4. Node Function Pattern
```python
# Node functions MUST return dict or State
def agent_node(state: State) -> dict:
    # Process state
    return {
        "messages": [AIMessage(content="response")],
        "current_step": "next"
    }

# Async nodes are supported
async def async_node(state: State) -> dict:
    result = await some_operation()
    return {"messages": [AIMessage(content=result)]}
```

## 5. Execution Pattern
```python
# Invoke
result = app.invoke(
    {"messages": [HumanMessage(content="input")]},
    config={"configurable": {"thread_id": "1"}}
)

# Stream
async for output in app.astream(
    {"messages": [HumanMessage(content="input")]},
    config={"configurable": {"thread_id": "1"}}
):
    print(output)

# Stream with events (0.6.6 feature)
async for event in app.astream_events(
    {"messages": [HumanMessage(content="input")]},
    version="v2"
):
    print(event)
```

## 6. Tool Integration Pattern
```python
from langchain_core.tools import tool

@tool
def my_tool(query: str) -> str:
    """Tool description."""
    return f"Result: {query}"

# Create tool node
tool_node = ToolNode([my_tool])

# Add to graph
graph.add_node("tools", tool_node)
graph.add_conditional_edges(
    "agent",
    tools_condition,  # Prebuilt condition
    {"tools": "tools", END: END}
)
```

## 7. Project-Specific Implementation
```python
class AgentState(MessagesState):
    """State for 영업 지원 AI system"""
    current_agent: str
    task_type: str  # "analyze" | "search" | "document" | "validate"
    progress: Annotated[list[dict], lambda x, y: x + y]  # Accumulate progress

def create_app():
    graph = StateGraph(AgentState)
    
    # Supervisor pattern
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("analytics", analytics_agent)
    graph.add_node("search", search_agent)
    graph.add_node("document", document_agent)
    graph.add_node("compliance", compliance_agent)
    
    # Routing
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_by_task_type,
        {
            "analyze": "analytics",
            "search": "search", 
            "document": "document",
            "end": END
        }
    )
    
    return graph.compile(checkpointer=MemorySaver())
```

## ❌ NEVER USE (0.2.x patterns)
```python
# DON'T USE THESE:
from langgraph.graph import Graph, Chain  # ← OLD
graph = MessageGraph()  # ← OLD
graph.set_entry_point()  # ← OLD
from langgraph.checkpoint.aiosqlite import AsyncSqliteSaver  # ← OLD
```

## ✅ Quick Test
```python
# Verify version
import langgraph
assert langgraph.__version__ >= "0.6.6", f"Wrong version: {langgraph.__version__}"

# Test imports
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
print("✅ LangGraph 0.6.6 ready")
```

## 🎯 Golden Rules
1. **StateGraph**, never Graph or MessageGraph
2. **START/END** for entry/exit points
3. Node functions return **dict**
4. Use **Annotated** for reducers
5. Use **astream_events** for detailed streaming
6. **MemorySaver** for development, **SqliteSaver** for production