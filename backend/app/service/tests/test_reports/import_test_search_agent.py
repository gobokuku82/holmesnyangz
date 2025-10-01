"""
Import Test for Search Agent Module
Tests all search agent-related imports to ensure modules are properly accessible
"""

import sys
from pathlib import Path

# Setup paths
current_dir = Path(__file__).parent
service_dir = current_dir.parent
app_dir = service_dir.parent
backend_dir = app_dir.parent

sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / "app" / "service"))

print("="*70)
print("SEARCH AGENT IMPORT TEST")
print("="*70)
print(f"\nTest directory: {current_dir}")
print(f"Service directory: {service_dir}")
print(f"Backend directory: {backend_dir}\n")

# Track results
results = []
failed_imports = []

def test_import(module_name, item_name=None):
    """Test importing a module or specific item from module"""
    try:
        if item_name:
            exec(f"from {module_name} import {item_name}")
            print(f"[OK] Imported {item_name} from {module_name}")
            results.append(("OK", f"{module_name}.{item_name}"))
        else:
            exec(f"import {module_name}")
            print(f"[OK] Imported module: {module_name}")
            results.append(("OK", module_name))
        return True
    except ImportError as e:
        print(f"[FAIL] Import error: {module_name}{f'.{item_name}' if item_name else ''}")
        print(f"       Error: {e}")
        failed_imports.append((module_name, item_name, str(e)))
        results.append(("FAIL", f"{module_name}{f'.{item_name}' if item_name else ''}"))
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error importing {module_name}: {e}")
        failed_imports.append((module_name, item_name, str(e)))
        results.append(("ERROR", f"{module_name}{f'.{item_name}' if item_name else ''}"))
        return False

print("-"*70)
print("TESTING CORE DEPENDENCIES")
print("-"*70)

# Test core modules first
test_import("core.states", "SearchAgentState")
test_import("core.context", "LLMContext")
test_import("core.context", "create_default_llm_context")
test_import("core.config", "Config")
test_import("core.todo_types", "create_todo_dict")
test_import("core.todo_types", "update_todo_status")
test_import("core.todo_types", "find_todo")

print("\n" + "-"*70)
print("TESTING TOOLS MODULE")
print("-"*70)

# Test tools module
tools_ok = test_import("tools")
if tools_ok:
    test_import("tools", "tool_registry")
    test_import("tools", "BaseTool")

    # Test individual tools
    test_import("tools.legal_search", "LegalSearchTool")
    test_import("tools.regulation_search", "RegulationSearchTool")
    test_import("tools.loan_search", "LoanSearchTool")
    test_import("tools.real_estate_search", "RealEstateSearchTool")

print("\n" + "-"*70)
print("TESTING SEARCH AGENT MODULE")
print("-"*70)

# Test search agent module and classes
agent_ok = test_import("agents.search_agent")

if agent_ok:
    test_import("agents.search_agent", "SearchAgent")
    test_import("agents.search_agent", "SearchAgentLLM")

    # Test if we can instantiate the classes
    try:
        from agents.search_agent import SearchAgent, SearchAgentLLM
        from core.context import create_default_llm_context

        # Try to create SearchAgentLLM instance
        llm_context = create_default_llm_context()
        llm_client = SearchAgentLLM(context=llm_context)
        print(f"[OK] Created SearchAgentLLM instance")
        results.append(("OK", "SearchAgentLLM instantiation"))

        # Try to create SearchAgent instance
        agent = SearchAgent(llm_context=llm_context)
        print(f"[OK] Created SearchAgent instance")
        results.append(("OK", "SearchAgent instantiation"))

        # Check if workflow is built
        if agent.workflow:
            print(f"[OK] SearchAgent workflow graph built")
            results.append(("OK", "Agent workflow graph"))
        else:
            print(f"[WARN] SearchAgent workflow not built")
            results.append(("WARN", "Agent workflow graph"))

        # Check if app is compiled
        if agent.app:
            print(f"[OK] SearchAgent app compiled")
            results.append(("OK", "Agent app compilation"))
        else:
            print(f"[WARN] SearchAgent app not compiled")
            results.append(("WARN", "Agent app compilation"))

    except Exception as e:
        print(f"[FAIL] Could not instantiate search agent classes: {e}")
        failed_imports.append(("instantiation", None, str(e)))
        results.append(("FAIL", "Class instantiation"))

print("\n" + "-"*70)
print("TESTING LANGGRAPH DEPENDENCIES")
print("-"*70)

# Test LangGraph imports used by search agent
test_import("langgraph.graph", "StateGraph")
test_import("langgraph.graph", "START")
test_import("langgraph.graph", "END")

print("\n" + "-"*70)
print("TESTING AGENT WORKFLOW NODES")
print("-"*70)

# Test if nodes are accessible
if agent_ok:
    try:
        from agents.search_agent import SearchAgent
        from core.context import create_default_llm_context

        llm_context = create_default_llm_context()
        agent = SearchAgent(llm_context=llm_context)

        # Check if nodes exist
        nodes_to_check = [
            "create_search_plan_node",
            "execute_tools_node",
            "process_results_node",
            "decide_next_action_node"
        ]

        for node_name in nodes_to_check:
            if hasattr(agent, node_name):
                print(f"[OK] Node method exists: {node_name}")
                results.append(("OK", f"Node: {node_name}"))
            else:
                print(f"[FAIL] Node method missing: {node_name}")
                results.append(("FAIL", f"Node: {node_name}"))

    except Exception as e:
        print(f"[ERROR] Could not check nodes: {e}")
        results.append(("ERROR", "Node verification"))

print("\n" + "-"*70)
print("TESTING TOOL REGISTRY")
print("-"*70)

# Test tool registry contents
try:
    from tools import tool_registry

    registered_tools = list(tool_registry._tools.keys())
    print(f"Registered tools: {registered_tools}")

    expected_tools = ["legal_search", "regulation_search", "loan_search", "real_estate_search"]

    for tool_name in expected_tools:
        if tool_name in registered_tools:
            print(f"[OK] Tool registered: {tool_name}")
            results.append(("OK", f"Tool: {tool_name}"))
        else:
            print(f"[FAIL] Tool not registered: {tool_name}")
            results.append(("FAIL", f"Tool: {tool_name}"))

except Exception as e:
    print(f"[ERROR] Could not check tool registry: {e}")
    results.append(("ERROR", "Tool registry check"))

print("\n" + "="*70)
print("TEST SUMMARY")
print("="*70)

# Calculate statistics
total_tests = len(results)
successful = len([r for r in results if r[0] == "OK"])
failed = len([r for r in results if r[0] == "FAIL"])
errors = len([r for r in results if r[0] == "ERROR"])
warnings = len([r for r in results if r[0] == "WARN"])

print(f"\nTotal tests: {total_tests}")
print(f"Successful: {successful}")
print(f"Failed: {failed}")
print(f"Errors: {errors}")
print(f"Warnings: {warnings}")
print(f"Success rate: {(successful/total_tests*100):.1f}%")

if failed_imports:
    print("\n" + "-"*70)
    print("FAILED IMPORTS DETAIL")
    print("-"*70)
    for module, item, error in failed_imports:
        if item:
            print(f"\n{module}.{item}:")
        else:
            print(f"\n{module}:")
        print(f"  {error}")

# Final verdict
print("\n" + "="*70)
if failed == 0 and errors == 0:
    print("[SUCCESS] All search agent imports working correctly!")
else:
    print(f"[WARNING] {failed + errors} import(s) failed. Review the errors above.")
print("="*70)

# Return status for CI/CD
import sys
sys.exit(0 if (failed == 0 and errors == 0) else 1)