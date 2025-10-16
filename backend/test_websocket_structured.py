"""
WebSocket을 통한 구조화된 응답 테스트
"""

import asyncio
import json
import websockets


async def test_structured_response():
    """WebSocket을 통해 구조화된 응답이 제대로 전달되는지 테스트"""

    # 먼저 세션 생성
    import httpx

    async with httpx.AsyncClient() as client:
        # 세션 시작
        response = await client.post("http://localhost:8000/api/v1/chat/start")
        if response.status_code != 200:
            print(f"❌ 세션 생성 실패: {response.status_code}")
            return

        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"✅ 세션 생성: {session_id}")

    # WebSocket 연결 (세션 ID 포함)
    uri = f"ws://localhost:8000/api/v1/chat/ws/{session_id}"

    async with websockets.connect(uri) as websocket:
        # 테스트 메시지 전송
        test_message = {
            "type": "query",
            "query": "전세금을 5% 인상하려고 하는데 가능한가요? 현재 전세금은 3억입니다.",
            "enable_checkpointing": True
        }

        print("=" * 80)
        print("WebSocket 구조화된 응답 테스트")
        print("=" * 80)
        print(f"질문: {test_message['query']}")
        print("-" * 80)
        print("응답 대기중...")

        await websocket.send(json.dumps(test_message))

        # 응답 수신
        while True:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                response_data = json.loads(response)

                # 응답 타입 확인
                if response_data.get("type") == "status":
                    print(f"상태: {response_data.get('status')}")
                    continue

                elif response_data.get("type") == "answer":
                    print("\n✅ 구조화된 응답 수신:")
                    print("-" * 40)

                    # structured_data 확인
                    if "structured_data" in response_data:
                        structured = response_data["structured_data"]

                        # 섹션 출력
                        if "sections" in structured:
                            print("📋 UI 섹션:")
                            for idx, section in enumerate(structured["sections"]):
                                print(f"\n  섹션 {idx + 1}: {section.get('title')}")
                                print(f"    아이콘: {section.get('icon', 'none')}")
                                print(f"    우선순위: {section.get('priority', 'medium')}")

                                content = section.get('content', '')
                                if isinstance(content, list):
                                    print(f"    내용 (리스트):")
                                    for item in content[:3]:  # 처음 3개만 표시
                                        print(f"      - {item}")
                                    if len(content) > 3:
                                        print(f"      ... 외 {len(content)-3}개")
                                else:
                                    print(f"    내용: {content[:100]}..." if len(content) > 100 else f"    내용: {content}")

                        # 메타데이터 출력
                        if "metadata" in structured:
                            meta = structured["metadata"]
                            print(f"\n📊 메타데이터:")
                            print(f"  신뢰도: {meta.get('confidence', 0) * 100:.0f}%")
                            print(f"  의도 타입: {meta.get('intent_type', 'unknown')}")

                            sources = meta.get('sources', [])
                            if sources:
                                print(f"  참고 자료: {', '.join(sources)}")
                    else:
                        print("⚠️ structured_data 필드가 없습니다.")
                        print(f"응답 키: {list(response_data.keys())}")

                    # 사용된 팀 출력
                    if "teams_used" in response_data:
                        print(f"\n🔧 사용된 팀: {', '.join(response_data['teams_used'])}")

                    break

                elif response_data.get("type") == "error":
                    print(f"❌ 에러: {response_data.get('message')}")
                    break

            except asyncio.TimeoutError:
                print("⏱️ 타임아웃: 30초 내에 응답을 받지 못했습니다.")
                break
            except Exception as e:
                print(f"❌ 예외 발생: {e}")
                break

        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_structured_response())