"""
Import Test for Supervisor Module
Tests all supervisor-related imports to ensure modules are properly accessible
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
print("SUPERVISOR IMPORT TEST")
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
test_import("core.states", "RealEstateMainState")
test_import("core.context", "LLMContext")
test_import("core.context", "create_default_llm_context")
test_import("core.config", "Config")
test_import("core.todo_types", "create_todo_dict")
test_import("core.todo_types", "update_todo_status")
test_import("core.todo_types", "find_todo")
test_import("core.todo_types", "get_todo_summary")
test_import("core.todo_types", "merge_todos")

print("\n" + "-"*70)
print("TESTING SUPERVISOR MODULE")
print("-"*70)

# Test supervisor module and classes
supervisor_ok = test_import("supervisor.supervisor")

if supervisor_ok:
    test_import("supervisor.supervisor", "RealEstateSupervisor")
    test_import("supervisor.supervisor", "LLMManager")

    # Test if we can instantiate the classes
    try:
        from supervisor.supervisor import RealEstateSupervisor, LLMManager
        from core.context import create_default_llm_context

        # Try to create LLMManager instance
        llm_context = create_default_llm_context()
        llm_manager = LLMManager(context=llm_context)
        print(f"[OK] Created LLMManager instance")
        results.append(("OK", "LLMManager instantiation"))

        # Try to create Supervisor instance
        supervisor = RealEstateSupervisor(llm_context=llm_context)
        print(f"[OK] Created RealEstateSupervisor instance")
        results.append(("OK", "RealEstateSupervisor instantiation"))

        # Check if workflow is built
        if supervisor.workflow:
            print(f"[OK] Supervisor workflow graph built")
            results.append(("OK", "Workflow graph"))
        else:
            print(f"[WARN] Supervisor workflow not built")
            results.append(("WARN", "Workflow graph"))

    except Exception as e:
        print(f"[FAIL] Could not instantiate supervisor classes: {e}")
        failed_imports.append(("instantiation", None, str(e)))
        results.append(("FAIL", "Class instantiation"))

print("\n" + "-"*70)
print("TESTING LANGGRAPH DEPENDENCIES")
print("-"*70)

# Test LangGraph imports used by supervisor
test_import("langgraph.graph", "StateGraph")
test_import("langgraph.graph", "START")
test_import("langgraph.graph", "END")

print("\n" + "-"*70)
print("TESTING OPTIONAL DEPENDENCIES")
print("-"*70)

# Test agent imports that supervisor might use
test_import("agents.search_agent", "SearchAgent")
test_import("core.agent_specifications")  # If exists
test_import("core.base_agent", "BaseAgent")  # If exists

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
    print("[SUCCESS] All supervisor imports working correctly!")
else:
    print(f"[WARNING] {failed + errors} import(s) failed. Review the errors above.")
print("="*70)

# Return status for CI/CD
import sys
sys.exit(0 if (failed == 0 and errors == 0) else 1)