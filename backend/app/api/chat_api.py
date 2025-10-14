"""
Chat API Router
FastAPI WebSocket endpoints for real-time chat with service_agent integration
"""

from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from datetime import datetime
import logging
import asyncio
import json

from app.api.schemas import (
    SessionStartRequest, SessionStartResponse,
    SessionInfo, DeleteSessionResponse,
    ErrorResponse
)
from app.api.session_manager import get_session_manager, SessionManager
from app.api.ws_manager import get_connection_manager, ConnectionManager
from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
logger = logging.getLogger(__name__)

# ============================================================================
# Supervisor Singleton Pattern
# ============================================================================

_supervisor_instance = None
_supervisor_lock = asyncio.Lock()


async def get_supervisor(enable_checkpointing: bool = True) -> TeamBasedSupervisor:
    """
    Supervisor 싱글톤 인스턴스 반환

    Args:
        enable_checkpointing: Checkpointing 활성화 여부

    Returns:
        TeamBasedSupervisor: 싱글톤 인스턴스
    """
    global _supervisor_instance

    async with _supervisor_lock:
        if _supervisor_instance is None:
            logger.info("🚀 Creating singleton TeamBasedSupervisor instance...")

            from app.service_agent.foundation.context import create_default_llm_context
            llm_context = create_default_llm_context()

            _supervisor_instance = TeamBasedSupervisor(
                llm_context=llm_context,
                enable_checkpointing=enable_checkpointing
            )

            logger.info("✅ Singleton TeamBasedSupervisor created successfully")

        return _supervisor_instance


# ============================================================================
# Session Management Endpoints
# ============================================================================

@router.post("/start", response_model=SessionStartResponse)
async def start_session(
    request: SessionStartRequest = SessionStartRequest(),
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """
    새 채팅 세션 시작

    서버가 고유한 UUID 기반 session_id 생성

    Args:
        request: 세션 시작 요청 (선택적 필드)

    Returns:
        SessionStartResponse: 생성된 세션 정보
    """
    try:
        session_id, expires_at = await session_mgr.create_session(
            user_id=request.user_id,
            metadata=request.metadata
        )

        logger.info(
            f"New session created: {session_id} "
            f"(user: {request.user_id or 'anonymous'})"
        )

        return SessionStartResponse(
            session_id=session_id,
            created_at=datetime.now().isoformat(),
            expires_at=expires_at.isoformat()
        )

    except Exception as e:
        logger.error(f"Failed to create session: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create session: {str(e)}"
        )


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session_info(
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """
    세션 정보 조회

    Args:
        session_id: 조회할 세션 ID

    Returns:
        SessionInfo: 세션 정보
    """
    session = await session_mgr.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found or expired: {session_id}"
        )

    return SessionInfo(
        session_id=session["session_id"],
        created_at=session["created_at"].isoformat(),
        expires_at=session["expires_at"].isoformat(),
        last_activity=session["last_activity"].isoformat(),
        metadata=session.get("metadata", {})
    )


@router.delete("/{session_id}", response_model=DeleteSessionResponse)
async def delete_session(
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager),
    conn_mgr: ConnectionManager = Depends(get_connection_manager)
):
    """
    세션 삭제 (로그아웃)

    Args:
        session_id: 삭제할 세션 ID

    Returns:
        DeleteSessionResponse: 삭제 결과
    """
    success = await session_mgr.delete_session(session_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}"
        )

    # WebSocket 연결도 정리
    conn_mgr.cleanup_session(session_id)

    logger.info(f"Session deleted: {session_id}")

    return DeleteSessionResponse(
        message="Session deleted successfully",
        session_id=session_id
    )


# ============================================================================
# WebSocket Chat Endpoint
# ============================================================================

@router.websocket("/ws/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager),
    conn_mgr: ConnectionManager = Depends(get_connection_manager)
):
    """
    실시간 채팅 WebSocket 엔드포인트

    Protocol:
        Client → Server:
            - {"type": "query", "query": "...", "enable_checkpointing": true}
            - {"type": "interrupt_response", "action": "approve|modify", "modified_todos": [...]}
            - {"type": "todo_skip", "todo_id": "..."}

        Server → Client:
            - {"type": "connected", "session_id": "..."}
            - {"type": "planning_start", "message": "계획을 수립하고 있습니다..."}
            - {"type": "plan_ready", "intent": "...", "execution_steps": [...], "estimated_total_time": ..., "keywords": [...]}
            - {"type": "execution_start", "message": "작업 실행을 시작합니다...", "execution_steps": [...]}
            - {"type": "todo_created", "execution_steps": [...]}
            - {"type": "todo_updated", "execution_steps": [...]}
            - {"type": "step_start", "agent": "...", "task": "..."}
            - {"type": "step_progress", "agent": "...", "progress": 50}
            - {"type": "step_complete", "agent": "...", "result": {...}}
            - {"type": "final_response", "response": {...}}
            - {"type": "error", "error": "...", "details": {...}}

    Args:
        websocket: WebSocket 연결
        session_id: 세션 ID
    """
    # 1. 세션 검증
    if not await session_mgr.validate_session(session_id):
        await websocket.close(code=4004, reason="Session not found or expired")
        logger.warning(f"WebSocket rejected: invalid session {session_id}")
        return

    # 2. WebSocket 연결
    await conn_mgr.connect(session_id, websocket)

    # 3. 연결 확인 메시지
    await conn_mgr.send_message(session_id, {
        "type": "connected",
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    })

    # 4. Supervisor 인스턴스 가져오기
    supervisor = await get_supervisor(enable_checkpointing=True)

    try:
        # 5. 메시지 수신 루프
        while True:
            try:
                # 메시지 수신 (JSON)
                data = await websocket.receive_json()
                message_type = data.get("type")

                logger.info(f"📥 Received from {session_id}: {message_type}")

                # === Query 처리 ===
                if message_type == "query":
                    query = data.get("query")
                    enable_checkpointing = data.get("enable_checkpointing", True)

                    if not query:
                        await conn_mgr.send_message(session_id, {
                            "type": "error",
                            "error": "Query cannot be empty",
                            "timestamp": datetime.now().isoformat()
                        })
                        continue

                    # Progress callback 정의
                    async def progress_callback(event_type: str, event_data: dict):
                        """실시간 진행 상황 전송"""
                        await conn_mgr.send_message(session_id, {
                            "type": event_type,
                            **event_data,
                            "timestamp": datetime.now().isoformat()
                        })

                    # 비동기 쿼리 처리 시작
                    asyncio.create_task(
                        _process_query_async(
                            supervisor=supervisor,
                            query=query,
                            session_id=session_id,
                            enable_checkpointing=enable_checkpointing,
                            progress_callback=progress_callback,
                            conn_mgr=conn_mgr
                        )
                    )

                # === Interrupt Response (계획 승인/수정) ===
                elif message_type == "interrupt_response":
                    # TODO: LangGraph interrupt 처리 (추후 구현)
                    action = data.get("action")  # "approve" or "modify"
                    modified_todos = data.get("modified_todos", [])

                    logger.info(f"Interrupt response: {action}")
                    # 현재는 로그만, 추후 LangGraph Command로 전달

                # === Todo Skip (실행 중 작업 건너뛰기) ===
                elif message_type == "todo_skip":
                    todo_id = data.get("todo_id")
                    logger.info(f"Todo skip requested: {todo_id}")
                    # TODO: 추후 구현

                # === 알 수 없는 메시지 ===
                else:
                    await conn_mgr.send_message(session_id, {
                        "type": "error",
                        "error": f"Unknown message type: {message_type}",
                        "timestamp": datetime.now().isoformat()
                    })

            except json.JSONDecodeError:
                await conn_mgr.send_message(session_id, {
                    "type": "error",
                    "error": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")

    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {e}", exc_info=True)
        await conn_mgr.send_message(session_id, {
            "type": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })

    finally:
        # 6. 연결 해제
        conn_mgr.disconnect(session_id)
        logger.info(f"WebSocket closed: {session_id}")


async def _process_query_async(
    supervisor: TeamBasedSupervisor,
    query: str,
    session_id: str,
    enable_checkpointing: bool,
    progress_callback,
    conn_mgr: ConnectionManager
):
    """
    비동기로 쿼리 처리 (백그라운드 태스크)

    Args:
        supervisor: TeamBasedSupervisor 인스턴스
        query: 사용자 질문
        session_id: 세션 ID
        enable_checkpointing: Checkpoint 활성화 여부
        progress_callback: 진행 상황 콜백
        conn_mgr: ConnectionManager
    """
    try:
        logger.info(f"Processing query for {session_id}: {query[:100]}...")

        # Streaming 방식으로 쿼리 처리
        result = await supervisor.process_query_streaming(
            query=query,
            session_id=session_id,
            progress_callback=progress_callback
        )

        # 최종 응답 전송
        # final_response만 추출 (result에는 datetime 필드가 있어 JSON 직렬화 불가)
        final_response = result.get("final_response", {})

        await conn_mgr.send_message(session_id, {
            "type": "final_response",
            "response": final_response,
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"Query completed for {session_id}")

    except Exception as e:
        logger.error(f"Query processing failed for {session_id}: {e}", exc_info=True)

        await conn_mgr.send_message(session_id, {
            "type": "error",
            "error": "Query processing failed",
            "details": {"error": str(e)},
            "timestamp": datetime.now().isoformat()
        })


# ============================================================================
# Utility Endpoints
# ============================================================================

@router.get("/stats/sessions")
async def get_session_stats(
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """세션 통계 조회"""
    active_count = await session_mgr.get_active_session_count()

    return {
        "active_sessions": active_count,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/stats/websockets")
async def get_websocket_stats(
    conn_mgr: ConnectionManager = Depends(get_connection_manager)
):
    """WebSocket 연결 통계 조회"""
    return {
        "active_connections": conn_mgr.get_active_count(),
        "timestamp": datetime.now().isoformat()
    }


@router.post("/cleanup/sessions")
async def cleanup_expired_sessions(
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """만료된 세션 정리"""
    cleaned = await session_mgr.cleanup_expired_sessions()

    logger.info(f"Cleaned up {cleaned} expired sessions")

    return {
        "cleaned_sessions": cleaned,
        "timestamp": datetime.now().isoformat()
    }
