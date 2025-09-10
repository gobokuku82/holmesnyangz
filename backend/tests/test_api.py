"""
API and FastAPI Tests
API 엔드포인트 테스트
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import FastAPI

from backend.api.models import (
    ChatRequest, ChatResponse,
    UserSession, SessionResponse,
    ThreadInfo, SystemStatus,
    FeedbackRequest
)
from backend.api.routes import router, sessions, server_start_time
from backend.core.workflow_engine import AsyncWorkflowEngine


# 테스트용 FastAPI 앱 생성
app = FastAPI()
app.include_router(router)

# TestClient 생성
client = TestClient(app)


class TestSessionEndpoints:
    """세션 관련 엔드포인트 테스트"""
    
    def test_create_user_session(self):
        """사용자 세션 생성 테스트"""
        with patch('backend.api.routes.WorkflowEngineFactory.create_for_user') as mock_factory:
            mock_engine = Mock(spec=AsyncWorkflowEngine)
            mock_engine.context = Mock(
                available_agents=["analyzer_agent", "price_search_agent"],
                features={"enable_memory": True}
            )
            mock_factory.return_value = mock_engine
            
            response = client.post(
                "/api/v1/sessions",
                json={
                    "user_id": "test_user",
                    "user_name": "Test User",
                    "user_role": "user"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "test_user"
            assert data["user_name"] == "Test User"
            assert "session_id" in data
            assert len(data["available_agents"]) > 0
    
    def test_create_admin_session(self):
        """관리자 세션 생성 테스트"""
        with patch('backend.api.routes.WorkflowEngineFactory.create_for_admin') as mock_factory:
            mock_engine = Mock(spec=AsyncWorkflowEngine)
            mock_engine.context = Mock(
                available_agents=["analyzer_agent", "price_search_agent", "finance_agent"],
                features={"enable_memory": True, "enable_human_in_loop": True}
            )
            mock_factory.return_value = mock_engine
            
            response = client.post(
                "/api/v1/sessions",
                json={
                    "user_id": "admin_user",
                    "user_name": "Admin",
                    "user_role": "admin"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_role"] == "admin"
    
    def test_delete_session(self):
        """세션 삭제 테스트"""
        # 먼저 세션 생성
        mock_engine = Mock(spec=AsyncWorkflowEngine)
        mock_engine.close = AsyncMock()
        sessions["test_session_123"] = mock_engine
        
        response = client.delete("/api/v1/sessions/test_session_123")
        
        assert response.status_code == 200
        assert "test_session_123" not in sessions
    
    def test_delete_nonexistent_session(self):
        """존재하지 않는 세션 삭제 시도"""
        response = client.delete("/api/v1/sessions/nonexistent_session")
        
        assert response.status_code == 404


class TestChatEndpoints:
    """채팅 관련 엔드포인트 테스트"""
    
    def setup_method(self):
        """각 테스트 전 세션 설정"""
        self.mock_engine = Mock(spec=AsyncWorkflowEngine)
        self.mock_engine.execute = AsyncMock(return_value={
            "final_response": "테스트 응답",
            "workflow_status": "completed",
            "intent": "test_intent",
            "confidence_scores": {"overall": 0.9},
            "selected_agents": ["test_agent"],
            "metrics": {
                "thread_id": "test_thread",
                "execution_time": 1.5,
                "agents_called": 1
            }
        })
        sessions["test_session"] = self.mock_engine
    
    def teardown_method(self):
        """각 테스트 후 정리"""
        sessions.clear()
    
    def test_chat_request(self):
        """채팅 요청 테스트"""
        response = client.post(
            "/api/v1/chat/test_session",
            json={
                "query": "테스트 쿼리",
                "streaming": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "테스트 응답"
        assert data["workflow_status"] == "completed"
        assert data["confidence"] == 0.9
    
    def test_chat_with_thread_id(self):
        """스레드 ID와 함께 채팅 요청"""
        response = client.post(
            "/api/v1/chat/test_session",
            json={
                "query": "테스트 쿼리",
                "thread_id": "existing_thread",
                "streaming": False
            }
        )
        
        assert response.status_code == 200
        # execute 메서드가 올바른 thread_id로 호출되었는지 확인
        self.mock_engine.execute.assert_called_with(
            query="테스트 쿼리",
            thread_id="existing_thread",
            streaming=False
        )


class TestThreadEndpoints:
    """스레드 관련 엔드포인트 테스트"""
    
    def setup_method(self):
        """각 테스트 전 세션 설정"""
        self.mock_engine = Mock(spec=AsyncWorkflowEngine)
        sessions["test_session"] = self.mock_engine
    
    def teardown_method(self):
        """각 테스트 후 정리"""
        sessions.clear()
    
    @pytest.mark.asyncio
    async def test_list_threads(self):
        """스레드 목록 조회 테스트"""
        self.mock_engine.list_threads = AsyncMock(return_value=[
            {
                "thread_id": "thread_1",
                "created_at": "2024-01-01T12:00:00",
                "last_update": "2024-01-01T13:00:00",
                "status": "active"
            }
        ])
        self.mock_engine.get_state = AsyncMock(return_value={
            "messages": ["msg1", "msg2"]
        })
        
        response = client.get("/api/v1/sessions/test_session/threads")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["threads"]) == 1
        assert data["threads"][0]["thread_id"] == "thread_1"
    
    def test_get_thread_state(self):
        """스레드 상태 조회 테스트"""
        self.mock_engine.get_state = AsyncMock(return_value={
            "query": "테스트 쿼리",
            "workflow_status": "completed",
            "messages": []
        })
        
        response = client.get("/api/v1/sessions/test_session/threads/thread_1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["thread_id"] == "thread_1"
        assert "state" in data
    
    def test_delete_thread(self):
        """스레드 삭제 테스트"""
        self.mock_engine.delete_thread = AsyncMock(return_value=True)
        
        response = client.delete("/api/v1/sessions/test_session/threads/thread_1")
        
        assert response.status_code == 200
        self.mock_engine.delete_thread.assert_called_with("thread_1")


class TestSystemEndpoints:
    """시스템 관련 엔드포인트 테스트"""
    
    def test_health_check(self):
        """헬스 체크 테스트"""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_system_status(self):
        """시스템 상태 조회 테스트"""
        # Mock 엔진 추가
        mock_engine = Mock(spec=AsyncWorkflowEngine)
        mock_engine.list_threads = AsyncMock(return_value=[
            {"status": "active"},
            {"status": "completed"}
        ])
        sessions["test_session"] = mock_engine
        
        response = client.get("/api/v1/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert len(data["agents"]) > 0
        assert data["total_sessions"] == 1
        
        # 정리
        sessions.clear()


class TestFeedbackEndpoints:
    """피드백 관련 엔드포인트 테스트"""
    
    def test_submit_feedback(self):
        """피드백 제출 테스트"""
        response = client.post(
            "/api/v1/feedback",
            json={
                "thread_id": "test_thread",
                "rating": 5,
                "feedback": "매우 유용했습니다"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["thread_id"] == "test_thread"
        assert data["status"] == "processed"
        assert "feedback_id" in data


class TestErrorHandling:
    """에러 처리 테스트"""
    
    def test_invalid_session_error(self):
        """잘못된 세션 ID 에러"""
        response = client.post(
            "/api/v1/chat/invalid_session",
            json={"query": "테스트"}
        )
        
        assert response.status_code == 404
    
    def test_validation_error(self):
        """검증 에러 테스트"""
        response = client.post(
            "/api/v1/sessions",
            json={
                "user_id": "",  # 빈 user_id
                "user_name": "Test"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_chat_timeout_error(self):
        """채팅 타임아웃 에러"""
        mock_engine = Mock(spec=AsyncWorkflowEngine)
        mock_engine.execute = AsyncMock(side_effect=asyncio.TimeoutError())
        sessions["test_session"] = mock_engine
        
        response = client.post(
            "/api/v1/chat/test_session",
            json={"query": "테스트"}
        )
        
        assert response.status_code == 408  # Request Timeout
        
        sessions.clear()


class TestStreamingEndpoints:
    """스트리밍 관련 엔드포인트 테스트"""
    
    def test_streaming_chat(self):
        """스트리밍 채팅 테스트"""
        mock_engine = Mock(spec=AsyncWorkflowEngine)
        
        async def mock_stream_events(*args, **kwargs):
            yield {"type": "token", "content": "Hello", "timestamp": "2024-01-01T12:00:00"}
            yield {"type": "token", "content": " World", "timestamp": "2024-01-01T12:00:01"}
        
        mock_engine.stream_events = mock_stream_events
        sessions["test_session"] = mock_engine
        
        response = client.post(
            "/api/v1/chat/test_session/stream",
            json={"query": "테스트"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        
        sessions.clear()


class TestModels:
    """Pydantic 모델 테스트"""
    
    def test_chat_request_model(self):
        """ChatRequest 모델 테스트"""
        request = ChatRequest(
            query="테스트 쿼리",
            streaming=True,
            temperature=0.7
        )
        
        assert request.query == "테스트 쿼리"
        assert request.streaming == True
        assert request.temperature == 0.7
    
    def test_chat_request_validation(self):
        """ChatRequest 검증 테스트"""
        # 빈 쿼리
        with pytest.raises(ValueError):
            ChatRequest(query="   ")
        
        # 너무 긴 쿼리
        with pytest.raises(ValueError):
            ChatRequest(query="a" * 2001)
    
    def test_session_response_model(self):
        """SessionResponse 모델 테스트"""
        response = SessionResponse(
            session_id="session_123",
            user_id="user_123",
            user_name="Test User",
            user_role="user",
            created_at=datetime.now().isoformat(),
            available_agents=["agent1", "agent2"],
            features={"memory": True}
        )
        
        assert response.session_id == "session_123"
        assert len(response.available_agents) == 2
    
    def test_feedback_request_model(self):
        """FeedbackRequest 모델 테스트"""
        feedback = FeedbackRequest(
            thread_id="thread_123",
            rating=5,
            feedback="Great service!"
        )
        
        assert feedback.rating == 5
        
        # 잘못된 평점
        with pytest.raises(ValueError):
            FeedbackRequest(thread_id="thread", rating=6)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])