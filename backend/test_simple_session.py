"""
Simple session creation test
"""

import httpx
import asyncio


async def test_session():
    """Test session creation"""

    async with httpx.AsyncClient() as client:
        # Create session
        print("Creating session...")
        response = await client.post("http://localhost:8000/api/v1/chat/start")

        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Session created: {data['session_id']}")
            print(f"   Created at: {data['created_at']}")
            print(f"   Expires at: {data['expires_at']}")
        else:
            print(f"❌ Failed: {response.text}")


if __name__ == "__main__":
    asyncio.run(test_session())