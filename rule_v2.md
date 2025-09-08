# LangGraph 0.6.6 Development Rules

## 🏗️ Architecture Rules

### 1. Graph Construction
- **MUST** use only `StateGraph`, `START`, `END` from langgraph.graph
- **MUST** inherit from `MessagesState` for state management
- **MUST** use `add_conditional_edges` for routing logic
- **NEVER** use deprecated patterns (MessageGraph, Chain, etc.)

### 2. State Management
```python
# CORRECT
class AgentState(MessagesState):
    current_agent: str
    results: Dict[str, Any]
    context: Dict[str, Any]
    
# WRONG
class AgentState(TypedDict):  # Don't use TypedDict directly
    messages: List[BaseMessage]
```

### 3. Node Functions
- **MUST** return dict from all node functions
- **MUST** include all state fields in return
- **MUST** handle errors and return valid state even on failure

```python
# CORRECT
def agent_node(state: AgentState) -> dict:
    try:
        # processing
        return {"field1": value1, "field2": value2}  # dict return
    except Exception as e:
        return {**state, "errors": [str(e)]}  # Still return dict

# WRONG
async def agent_node(state: AgentState) -> AgentState:  # Wrong return type
    return state  # Should return dict
```

## 🛠️ Tool Implementation Rules

### 1. Tool Definition
- **MUST** use `@tool` decorator from langchain_core.tools
- **MUST** return JSON string for complex data
- **MUST** include comprehensive docstrings
- **SHOULD** validate inputs using Pydantic when possible

```python
@tool
def search_properties(location: str, price_range: Optional[str] = None) -> str:
    """
    Search for properties in a specific location.
    
    Args:
        location: The area to search in
        price_range: Optional price range (e.g., "1M-2M")
    
    Returns:
        JSON string with search results
    """
    # Implementation
    return json.dumps(results, ensure_ascii=False)
```

### 2. Tool Execution
- **PREFER** LLM-based tool selection over hardcoded conditions
- **MUST** handle tool failures gracefully
- **SHOULD** use ToolNode for automatic tool execution

```python
# PREFERRED
from langgraph.prebuilt import ToolNode, create_react_agent

tools = [tool1, tool2, tool3]
tool_node = ToolNode(tools)
graph.add_node("tools", tool_node)

# AVOID
if "search" in query:
    result = search_tool.invoke(...)  # Hardcoded
```

## 🔄 Concurrency Rules

### 1. State Safety
- **MUST** use thread-safe state updates for parallel execution
- **MUST** use locks or async locks for shared resource access
- **NEVER** modify state directly in parallel tasks

```python
# CORRECT
async with state_lock:
    state["results"][agent_name] = result

# WRONG
state["results"][agent_name] = result  # Race condition
```

### 2. Parallel Execution
- **MUST** limit concurrent executions (default: 3)
- **MUST** use `asyncio.gather` with `return_exceptions=True`
- **MUST** implement fallback for failed parallel tasks

```python
# CORRECT
MAX_CONCURRENT = 3
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

async with semaphore:
    result = await agent_func(state)
```

## 🚦 Routing Rules

### 1. Conditional Routing
- **MUST** return string (node name) from routing functions
- **MUST** handle all possible conditions
- **MUST** include END condition

```python
def route_function(state: AgentState) -> str:
    if state.get("is_complete"):
        return END
    elif state.get("needs_search"):
        return "search_agent"
    else:
        return "supervisor"  # Default
```

### 2. Direct Routing
- **PREFER** direct agent-to-agent routing over always returning to supervisor
- **SHOULD** minimize supervisor visits for efficiency

```python
# GOOD
graph.add_edge("document", "compliance")  # Direct routing

# AVOID
graph.add_edge("document", "supervisor")
graph.add_edge("supervisor", "compliance")  # Unnecessary hop
```

## 🔒 Error Handling Rules

### 1. Retry Strategy
- **MUST** implement retry with exponential backoff
- **MUST** have maximum retry limit (default: 3)
- **MUST** provide fallback responses

```python
MAX_RETRIES = 3
BASE_DELAY = 1  # seconds

for attempt in range(MAX_RETRIES):
    try:
        return await agent_func(state)
    except Exception as e:
        if attempt < MAX_RETRIES - 1:
            delay = BASE_DELAY * (2 ** attempt)
            await asyncio.sleep(delay)
        else:
            return create_fallback_response(state)
```

### 2. Circuit Breaker
- **SHOULD** implement circuit breaker for external services
- **SHOULD** track failure rates per service
- **MUST** have timeout and reset mechanisms

## 📊 Monitoring Rules

### 1. Logging
- **MUST** use structured logging (loguru or similar)
- **MUST** log agent entry/exit
- **MUST** log tool usage
- **SHOULD** log performance metrics

```python
logger.info(f"Agent {name} started", extra={"agent": name, "state_id": state_id})
```

### 2. Metrics
- **SHOULD** track execution time per agent
- **SHOULD** track tool usage frequency
- **SHOULD** monitor memory usage for parallel execution

## 🗄️ Database Rules

### 1. Connection Management
- **MUST** use connection pooling
- **MUST** close connections properly
- **MUST** handle connection failures

```python
# CORRECT
from contextlib import contextmanager

@contextmanager
def get_db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

### 2. Data Operations
- **MUST** use parameterized queries (no string concatenation)
- **MUST** validate data before insertion
- **SHOULD** use batch operations for bulk data

## 🔌 WebSocket Rules

### 1. Message Ordering
- **MUST** maintain message order during parallel execution
- **MUST** use message queues for coordination
- **SHOULD** include sequence numbers in messages

```python
message = {
    "type": "agent_output",
    "sequence": message_counter,
    "agent": agent_name,
    "data": data
}
```

### 2. Connection Management
- **MUST** handle disconnections gracefully
- **MUST** implement heartbeat/ping-pong
- **SHOULD** limit concurrent connections

## 🧪 Testing Rules

### 1. Unit Tests
- **MUST** test each agent independently
- **MUST** mock external dependencies
- **MUST** test error conditions

### 2. Integration Tests
- **MUST** test full graph execution
- **MUST** test parallel execution paths
- **SHOULD** test with realistic data volumes

## 📝 Documentation Rules

### 1. Code Documentation
- **MUST** include docstrings for all public functions
- **MUST** document state schema changes
- **SHOULD** include usage examples

### 2. Architecture Documentation
- **MUST** maintain graph visualization
- **MUST** document agent dependencies
- **SHOULD** include sequence diagrams

## 🚀 Deployment Rules

### 1. Environment Variables
- **MUST** use environment variables for configuration
- **NEVER** hardcode credentials
- **MUST** validate required env vars on startup

### 2. Resource Limits
- **MUST** set memory limits for containers
- **MUST** implement request timeouts
- **SHOULD** use autoscaling based on metrics

## ⚡ Performance Rules

### 1. Optimization
- **SHOULD** cache frequently accessed data
- **SHOULD** use batch processing where possible
- **MUST** profile before optimizing

### 2. Scalability
- **SHOULD** design for horizontal scaling
- **MUST** avoid global state
- **SHOULD** use message queues for async processing

## 🔐 Security Rules

### 1. Input Validation
- **MUST** validate all user inputs
- **MUST** sanitize data before database operations
- **MUST** implement rate limiting

### 2. Authentication
- **MUST** use secure token mechanisms
- **MUST** implement session timeouts
- **SHOULD** log security events

## 📋 Checklist for New Agent Development

- [ ] State schema defined with proper types
- [ ] Agent function returns dict
- [ ] Error handling with fallback
- [ ] Tools properly decorated with @tool
- [ ] Routing logic covers all cases
- [ ] Thread-safety for parallel execution
- [ ] Logging at entry/exit points
- [ ] Unit tests written
- [ ] Documentation updated
- [ ] Performance baseline measured