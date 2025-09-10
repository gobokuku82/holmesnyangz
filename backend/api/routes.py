"""
FastAPI Routes for Real Estate Chatbot
REST API 엔드포인트 정의
"""

from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any
import asyncio
import json
from datetime import datetime

from backend.api.models import (
    ChatRequest, ChatResponse,
    UserSession, SessionResponse,
    ThreadListResponse, ThreadInfo,
    SystemStatus, AgentInfo,
    ErrorResponse, FeedbackRequest, FeedbackResponse
)
from backend.core.workflow_engine import AsyncWorkflowEngine, WorkflowEngineFactory
from backend.core.context import ContextFactory


# 라우터 생성
router = APIRouter(prefix="/api/v1", tags=["chatbot"])

# 세션 저장소 (실제로는 Redis/DB 사용)
sessions: Dict[str, AsyncWorkflowEngine] = {}


# === 의존성 ===

async def get_session(session_id: str) -> AsyncWorkflowEngine:
    """세션 가져오기"""
    if session_id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    return sessions[session_id]


# === 세션 관리 ===

@router.post("/sessions", response_model=SessionResponse)
async def create_session(request: UserSession) -> SessionResponse:
    """
    새 사용자 세션 생성
    """
    try:
        # 세션 ID 생성
        session_id = f"session_{request.user_id}_{datetime.now().timestamp()}"
        
        # 컨텍스트 생성
        if request.user_role == "admin":
            engine = await WorkflowEngineFactory.create_for_admin(
                user_id=request.user_id,
                user_name=request.user_name
            )
        elif request.user_role == "guest":
            engine = await WorkflowEngineFactory.create_for_guest()
        else:
            engine = await WorkflowEngineFactory.create_for_user(
                user_id=request.user_id,
                user_name=request.user_name
            )
        
        # 세션 저장
        sessions[session_id] = engine
        
        # 응답 생성
        return SessionResponse(
            session_id=session_id,
            user_id=request.user_id,
            user_name=request.user_name,
            user_role=request.user_role,
            created_at=datetime.now().isoformat(),
            available_agents=engine.context.available_agents,
            features=engine.context.features
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> Dict[str, str]:
    """
    세션 종료
    """
    engine = await get_session(session_id)
    
    try:
        await engine.close()
        del sessions[session_id]
        
        return {"message": f"Session {session_id} deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}"
        )


# === 채팅 ===

@router.post("/chat/{session_id}", response_model=ChatResponse)
async def chat(
    session_id: str,
    request: ChatRequest,
    engine: AsyncWorkflowEngine = Depends(get_session)
) -> ChatResponse:
    """
    채팅 메시지 처리
    """
    try:
        # 워크플로우 실행
        result = await engine.execute(
            query=request.query,
            thread_id=request.thread_id,
            streaming=request.streaming
        )
        
        # 응답 생성
        return ChatResponse(
            response=result.get("final_response", "처리 완료"),
            thread_id=result.get("metrics", {}).get("thread_id", ""),
            workflow_status=result.get("workflow_status", "completed"),
            intent=result.get("intent"),
            confidence=result.get("confidence_scores", {}).get("overall"),
            agents_used=result.get("selected_agents"),
            execution_time=result.get("metrics", {}).get("execution_time"),
            error=result.get("error")
        )
        
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Request timeout"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}"
        )


@router.post("/chat/{session_id}/stream")
async def chat_stream(
    session_id: str,
    request: ChatRequest,
    engine: AsyncWorkflowEngine = Depends(get_session)
):
    """
    스트리밍 채팅 (SSE)
    """
    async def event_generator():
        try:
            async for event in engine.stream_events(
                query=request.query,
                thread_id=request.thread_id
            ):
                # SSE 형식으로 변환
                data = json.dumps(event)
                yield f"data: {data}\n\n"
                
        except Exception as e:
            error_event = {
                "type": "error",
                "content": str(e),
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


# === 스레드 관리 ===

@router.get("/sessions/{session_id}/threads", response_model=ThreadListResponse)
async def list_threads(
    session_id: str,
    page: int = 1,
    page_size: int = 10,
    engine: AsyncWorkflowEngine = Depends(get_session)
) -> ThreadListResponse:
    """
    세션의 스레드 목록 조회
    """
    try:
        threads = await engine.list_threads(limit=page_size)
        
        # ThreadInfo 변환
        thread_infos = [
            ThreadInfo(
                thread_id=t["thread_id"],
                created_at=t.get("created_at", ""),
                last_update=t.get("last_update", ""),
                message_count=0,  # TODO: 실제 메시지 수 계산
                status=t.get("status", "active")
            )
            for t in threads
        ]
        
        return ThreadListResponse(
            threads=thread_infos,
            total_count=len(thread_infos),
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list threads: {str(e)}"
        )


@router.get("/sessions/{session_id}/threads/{thread_id}")
async def get_thread_state(
    session_id: str,
    thread_id: str,
    engine: AsyncWorkflowEngine = Depends(get_session)
) -> Dict[str, Any]:
    """
    스레드 상태 조회
    """
    try:
        state = await engine.get_state(thread_id)
        
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Thread {thread_id} not found"
            )
        
        return {
            "thread_id": thread_id,
            "state": state,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get thread state: {str(e)}"
        )


@router.delete("/sessions/{session_id}/threads/{thread_id}")
async def delete_thread(
    session_id: str,
    thread_id: str,
    engine: AsyncWorkflowEngine = Depends(get_session)
) -> Dict[str, str]:
    """
    스레드 삭제
    """
    try:
        success = await engine.delete_thread(thread_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Thread {thread_id} not found or could not be deleted"
            )
        
        return {"message": f"Thread {thread_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete thread: {str(e)}"
        )


# === 시스템 상태 ===

@router.get("/status", response_model=SystemStatus)
async def get_system_status() -> SystemStatus:
    """
    시스템 상태 조회
    """
    # 에이전트 정보 (하드코딩, 실제로는 동적으로 수집)
    agents = [
        AgentInfo(
            agent_id="analyzer_agent",
            name="쿼리 분석기",
            description="사용자 의도 및 엔티티 추출",
            capabilities=["의도 분석", "엔티티 추출"],
            status="active"
        ),
        AgentInfo(
            agent_id="price_search_agent",
            name="시세 검색",
            description="부동산 가격 정보 제공",
            capabilities=["실거래가 조회", "시세 분석"],
            status="active"
        ),
        AgentInfo(
            agent_id="finance_agent",
            name="금융 상담",
            description="대출 및 세금 계산",
            capabilities=["대출 계산", "세금 계산"],
            status="active"
        ),
        AgentInfo(
            agent_id="location_agent",
            name="입지 분석",
            description="교통 및 편의시설 정보",
            capabilities=["교통 분석", "편의시설 검색"],
            status="active"
        ),
        AgentInfo(
            agent_id="legal_agent",
            name="법률 자문",
            description="계약 및 규제 안내",
            capabilities=["계약 검토", "규제 확인"],
            status="active"
        )
    ]
    
    return SystemStatus(
        status="healthy",
        version="1.0.0",
        uptime=0.0,  # TODO: 실제 uptime 계산
        agents=agents,
        database_connected=True,
        checkpoint_enabled=True,
        total_sessions=len(sessions),
        active_threads=0  # TODO: 실제 활성 스레드 수 계산
    )


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    헬스 체크
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


# === 피드백 ===

@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest) -> FeedbackResponse:
    """
    사용자 피드백 제출
    """
    # TODO: 피드백을 데이터베이스에 저장
    
    feedback_id = f"feedback_{request.thread_id}_{datetime.now().timestamp()}"
    
    return FeedbackResponse(
        feedback_id=feedback_id,
        thread_id=request.thread_id,
        received_at=datetime.now().isoformat(),
        status="received"
    )


# === 에러 핸들러 ===

@router.get("/error-test")
async def error_test():
    """
    에러 테스트 엔드포인트
    """
    raise HTTPException(
        status_code=status.HTTP_418_IM_A_TEAPOT,
        detail="I'm a teapot"
    )