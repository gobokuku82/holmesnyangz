"""
Real Estate Chatbot - Main FastAPI Application
LangGraph 0.6.6 기반 부동산 챗봇 서버
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import json
import logging
from typing import Dict
from datetime import datetime

from backend.api.routes import router as api_router
from backend.api.models import WebSocketMessage
from backend.core.workflow_engine import AsyncWorkflowEngine, WorkflowEngineFactory
from backend.core.logging_config import setup_logging, get_logger
from backend.core.error_handlers import register_error_handlers


# 로깅 설정
setup_logging(log_level="INFO", log_dir="logs")
logger = get_logger(__name__)


# WebSocket 연결 관리
class ConnectionManager:
    """WebSocket 연결 관리자"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_engines: Dict[str, AsyncWorkflowEngine] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """연결 수락"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: {session_id}")
    
    def disconnect(self, session_id: str):
        """연결 해제"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.user_engines:
            del self.user_engines[session_id]
        logger.info(f"WebSocket disconnected: {session_id}")
    
    async def send_message(self, session_id: str, message: WebSocketMessage):
        """메시지 전송"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json(message.model_dump())
    
    async def broadcast(self, message: WebSocketMessage):
        """모든 연결에 브로드캐스트"""
        for session_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message.model_dump())
            except Exception as e:
                logger.error(f"Failed to send to {session_id}: {e}")


# 연결 관리자 인스턴스
manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    
    # 시작 시
    logger.info("Starting Real Estate Chatbot Server...")
    
    # 백그라운드 태스크 시작
    cleanup_task = asyncio.create_task(cleanup_inactive_sessions())
    
    yield
    
    # 종료 시
    logger.info("Shutting down Real Estate Chatbot Server...")
    
    # 백그라운드 태스크 취소
    cleanup_task.cancel()
    
    # 모든 WebSocket 연결 종료
    for session_id in list(manager.active_connections.keys()):
        manager.disconnect(session_id)
    
    # 모든 엔진 종료
    for engine in manager.user_engines.values():
        await engine.close()


# FastAPI 앱 생성
app = FastAPI(
    title="Real Estate Chatbot API",
    description="LangGraph 0.6.6 기반 부동산 전문 AI 챗봇",
    version="1.0.0",
    lifespan=lifespan,
    debug=False  # 프로덕션에서는 False
)


# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React 개발 서버
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 에러 핸들러 등록
register_error_handlers(app)


# API 라우터 포함
app.include_router(api_router)


# === WebSocket 엔드포인트 ===

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket 엔드포인트"""
    
    await manager.connect(websocket, session_id)
    
    try:
        # 연결 확인 메시지
        await manager.send_message(
            session_id,
            WebSocketMessage(
                type="event",
                content="Connected to Real Estate Chatbot",
                metadata={"session_id": session_id}
            )
        )
        
        # 엔진 생성 또는 가져오기
        if session_id not in manager.user_engines:
            # 게스트로 엔진 생성
            engine = await WorkflowEngineFactory.create_for_guest()
            manager.user_engines[session_id] = engine
        else:
            engine = manager.user_engines[session_id]
        
        # 메시지 수신 루프
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 메시지 타입별 처리
            if message["type"] == "query":
                # 쿼리 처리
                await handle_websocket_query(
                    session_id,
                    message["content"],
                    engine
                )
            
            elif message["type"] == "ping":
                # 핑 응답
                await manager.send_message(
                    session_id,
                    WebSocketMessage(type="pong")
                )
            
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        logger.info(f"WebSocket disconnected normally: {session_id}")
        
    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {e}")
        manager.disconnect(session_id)
        
        # 에러 메시지 전송 시도
        try:
            await manager.send_message(
                session_id,
                WebSocketMessage(
                    type="error",
                    content=str(e)
                )
            )
        except:
            pass


async def handle_websocket_query(
    session_id: str,
    query: str,
    engine: AsyncWorkflowEngine
):
    """WebSocket 쿼리 처리"""
    
    try:
        # 스트리밍으로 처리
        thread_id = f"ws_{session_id}_{datetime.now().timestamp()}"
        
        # 처리 시작 알림
        await manager.send_message(
            session_id,
            WebSocketMessage(
                type="event",
                content="Processing query...",
                metadata={"thread_id": thread_id}
            )
        )
        
        # 이벤트 스트리밍
        async for event in engine.stream_events(query, thread_id):
            # 이벤트 타입별 메시지 전송
            if event["type"] == "token":
                # 토큰 스트리밍
                await manager.send_message(
                    session_id,
                    WebSocketMessage(
                        type="response",
                        content=event["content"],
                        metadata={"streaming": True}
                    )
                )
            
            elif event["type"] in ["chain_start", "chain_end", "tool_start", "tool_end"]:
                # 상태 업데이트
                await manager.send_message(
                    session_id,
                    WebSocketMessage(
                        type="event",
                        content=f"{event['type']}: {event.get('name', '')}",
                        metadata=event
                    )
                )
        
        # 완료 메시지
        await manager.send_message(
            session_id,
            WebSocketMessage(
                type="event",
                content="Query processing completed",
                metadata={"thread_id": thread_id}
            )
        )
        
    except Exception as e:
        logger.error(f"Query processing error: {e}")
        await manager.send_message(
            session_id,
            WebSocketMessage(
                type="error",
                content=f"Failed to process query: {str(e)}"
            )
        )


async def cleanup_inactive_sessions():
    """비활성 세션 정리 (백그라운드 태스크)"""
    
    while True:
        try:
            await asyncio.sleep(300)  # 5분마다 실행
            
            # 비활성 세션 확인 및 정리
            # TODO: 실제 구현 필요
            logger.debug("Cleaning up inactive sessions...")
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")


# === 루트 엔드포인트 ===

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "name": "Real Estate Chatbot API",
        "version": "1.0.0",
        "status": "running",
        "documentation": "/docs",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/metrics")
async def metrics():
    """메트릭 엔드포인트"""
    return {
        "active_connections": len(manager.active_connections),
        "active_engines": len(manager.user_engines),
        "timestamp": datetime.now().isoformat()
    }


# === 개발용 엔드포인트 ===

if app.debug:
    @app.get("/debug/connections")
    async def debug_connections():
        """활성 연결 목록 (디버그용)"""
        return {
            "connections": list(manager.active_connections.keys()),
            "engines": list(manager.user_engines.keys())
        }
    
    @app.post("/debug/broadcast")
    async def debug_broadcast(message: str):
        """브로드캐스트 테스트 (디버그용)"""
        await manager.broadcast(
            WebSocketMessage(
                type="event",
                content=message,
                metadata={"broadcast": True}
            )
        )
        return {"message": "Broadcast sent"}


if __name__ == "__main__":
    import uvicorn
    
    # 서버 실행
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 개발 모드
        log_level="info"
    )