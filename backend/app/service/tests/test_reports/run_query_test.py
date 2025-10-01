"""
Automated query test runner for predefined tests
"""

import asyncio
import sys
from pathlib import Path

# Setup paths
current_dir = Path(__file__).parent
service_dir = current_dir.parent
backend_dir = service_dir.parent.parent

sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / "app" / "service"))

from query_test import QueryTester

async def run_tests():
    """Run predefined tests automatically"""
    print("\n" + "="*70)
    print("AUTOMATED QUERY TEST")
    print("="*70)

    # Create tester
    tester = QueryTester()

    # Initialize
    if not await tester.initialize():
        print("[FATAL] Failed to initialize")
        return None

    # Run predefined tests
    results = await tester.run_predefined_tests()
    return results

if __name__ == "__main__":
    # Run the async test function
    try:
        results = asyncio.run(run_tests())
        sys.exit(0 if results else 1)
    except Exception as e:
        print(f"\n[FATAL] Test failed: {e}")
        sys.exit(1)