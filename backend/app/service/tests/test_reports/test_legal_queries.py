#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "app" / "service"))

from tools.legal_search_tool import LegalSearchTool
import asyncio

async def test():
    tool = LegalSearchTool()

    queries = [
        "전세금 올려받기",
        "전세계약",
        "전세",
        "임대차",
        "보증금"
    ]

    for query in queries:
        result = await tool.search(query)
        print(f"{query:20s}: {result['total_count']:2d} results")
        if result['total_count'] == 0:
            print(f"  ERROR: No results!")

asyncio.run(test())
