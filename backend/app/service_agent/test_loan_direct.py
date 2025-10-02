import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.service_agent.tools.loan_data_tool import LoanDataTool

async def test():
    tool = LoanDataTool()
    result = await tool.search('주택담보대출 금리', {})
    print(result)

asyncio.run(test())
