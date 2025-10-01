"""
Final test for legal search tool
"""

import sys
from pathlib import Path

# Add service directory to path
service_dir = Path(__file__).parent / "backend" / "app" / "service"
sys.path.insert(0, str(service_dir))

from tools import tool_registry

print("=" * 80)
print("Legal Search Tool - Final Test")
print("=" * 80)

# Get legal search tool from registry
legal_tool = tool_registry.get("legal_search")

if legal_tool:
    print(f"\n[OK] Legal Search Tool found in registry")
    print(f"   Name: {legal_tool.name}")
    print(f"   Description: {legal_tool.description}")
    print(f"   Use Mock Data: {legal_tool.use_mock_data}")
    print(f"   Has Embedding Model: {hasattr(legal_tool, 'embedding_model') and legal_tool.embedding_model is not None}")
    print(f"   Has ChromaDB Collection: {hasattr(legal_tool, 'collection') and legal_tool.collection is not None}")
    print(f"   Has Metadata Helper: {hasattr(legal_tool, 'metadata_helper') and legal_tool.metadata_helper is not None}")

    if hasattr(legal_tool, 'collection') and legal_tool.collection:
        print(f"   ChromaDB Documents: {legal_tool.collection.count()}")
else:
    print("\n[ERROR] Legal Search Tool not found!")

print("\n" + "=" * 80)
print("Available tools:", tool_registry.list_tools())
print("=" * 80)
