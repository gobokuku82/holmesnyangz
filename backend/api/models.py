"""
FastAPI Pydantic Models for Real Estate Chatbot
요청/응답 모델 정의
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """사용자 역할"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class ModelProvider(str, Enum):
    """모델 제공자"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class ExecutionStrategy(str, Enum):
    """실행 전략"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"


class ChatRequest(BaseModel):
    """채팅 요청 모델"""
    query: str = Field(..., min_length=1, max_length=2000, description="사용자 질문")
    thread_id: Optional[str] = Field(None, description="대화 스레드 ID")
    streaming: bool = Field(False, description="스트리밍 응답 여부")
    
    # 선택적 컨텍스트 오버라이드
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0, description="응답 온도")
    max_tokens: Optional[int] = Field(None, ge=100, le=4000, description="최대 토큰 수")
    
    @validator("query")
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    response: str = Field(..., description="AI 응답")
    thread_id: str = Field(..., description="대화 스레드 ID")
    workflow_status: str = Field(..., description="워크플로우 상태")
    
    # 메타데이터
    intent: Optional[str] = Field(None, description="감지된 의도")
    confidence: Optional[float] = Field(None, description="신뢰도 점수")
    agents_used: Optional[List[str]] = Field(None, description="사용된 에이전트 목록")
    execution_time: Optional[float] = Field(None, description="실행 시간(초)")
    
    # 에러 정보
    error: Optional[str] = Field(None, description="에러 메시지")
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "강남구 아파트 평균 시세는 평당 5,000만원입니다.",
                "thread_id": "thread_123456",
                "workflow_status": "completed",
                "intent": "price_inquiry",
                "confidence": 0.95,
                "agents_used": ["price_search_agent"],
                "execution_time": 2.3
            }
        }


class StreamEvent(BaseModel):
    """스트리밍 이벤트 모델"""
    type: Literal["token", "chain_start", "chain_end", "tool_start", "tool_end", "error"]
    content: Optional[str] = Field(None, description="이벤트 내용")
    name: Optional[str] = Field(None, description="체인/도구 이름")
    timestamp: str = Field(..., description="이벤트 타임스탬프")
    metadata: Optional[Dict[str, Any]] = Field(None, description="추가 메타데이터")


class UserSession(BaseModel):
    """사용자 세션 생성 요청"""
    user_id: str = Field(..., min_length=1, max_length=100, description="사용자 ID")
    user_name: str = Field(..., min_length=1, max_length=100, description="사용자 이름")
    user_role: UserRole = Field(UserRole.USER, description="사용자 역할")
    
    # 선택적 설정
    model_provider: ModelProvider = Field(ModelProvider.OPENAI, description="모델 제공자")
    model_name: str = Field("gpt-4", description="모델 이름")
    temperature: float = Field(0.7, ge=0.0, le=1.0, description="응답 온도")
    max_tokens: int = Field(2000, ge=100, le=4000, description="최대 토큰 수")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "user_name": "홍길동",
                "user_role": "user",
                "model_provider": "openai",
                "model_name": "gpt-4"
            }
        }


class SessionResponse(BaseModel):
    """세션 생성 응답"""
    session_id: str = Field(..., description="세션 ID")
    user_id: str = Field(..., description="사용자 ID")
    user_name: str = Field(..., description="사용자 이름")
    user_role: UserRole = Field(..., description="사용자 역할")
    created_at: str = Field(..., description="생성 시간")
    expires_at: Optional[str] = Field(None, description="만료 시간")
    
    # 사용 가능한 기능
    available_agents: List[str] = Field(..., description="사용 가능한 에이전트")
    features: Dict[str, bool] = Field(..., description="활성화된 기능")


class ThreadInfo(BaseModel):
    """대화 스레드 정보"""
    thread_id: str = Field(..., description="스레드 ID")
    created_at: str = Field(..., description="생성 시간")
    last_update: str = Field(..., description="마지막 업데이트")
    message_count: int = Field(..., description="메시지 수")
    status: str = Field(..., description="스레드 상태")


class ThreadListResponse(BaseModel):
    """스레드 목록 응답"""
    threads: List[ThreadInfo] = Field(..., description="스레드 목록")
    total_count: int = Field(..., description="전체 스레드 수")
    page: int = Field(1, description="현재 페이지")
    page_size: int = Field(10, description="페이지 크기")


class AgentInfo(BaseModel):
    """에이전트 정보"""
    agent_id: str = Field(..., description="에이전트 ID")
    name: str = Field(..., description="에이전트 이름")
    description: str = Field(..., description="에이전트 설명")
    capabilities: List[str] = Field(..., description="에이전트 기능")
    status: Literal["active", "inactive", "error"] = Field(..., description="에이전트 상태")


class SystemStatus(BaseModel):
    """시스템 상태"""
    status: Literal["healthy", "degraded", "error"] = Field(..., description="시스템 상태")
    version: str = Field(..., description="시스템 버전")
    uptime: float = Field(..., description="가동 시간(초)")
    
    # 에이전트 상태
    agents: List[AgentInfo] = Field(..., description="에이전트 목록")
    
    # 리소스 상태
    database_connected: bool = Field(..., description="DB 연결 상태")
    checkpoint_enabled: bool = Field(..., description="체크포인팅 활성화")
    
    # 메트릭
    total_sessions: int = Field(..., description="전체 세션 수")
    active_threads: int = Field(..., description="활성 스레드 수")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "uptime": 3600.0,
                "agents": [
                    {
                        "agent_id": "price_search_agent",
                        "name": "부동산 시세 검색",
                        "description": "실거래가 및 시세 정보 제공",
                        "capabilities": ["시세 조회", "가격 분석"],
                        "status": "active"
                    }
                ],
                "database_connected": True,
                "checkpoint_enabled": True,
                "total_sessions": 150,
                "active_threads": 25
            }
        }


class ErrorResponse(BaseModel):
    """에러 응답"""
    error: str = Field(..., description="에러 메시지")
    error_code: str = Field(..., description="에러 코드")
    details: Optional[Dict[str, Any]] = Field(None, description="상세 정보")
    timestamp: str = Field(..., description="에러 발생 시간")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Invalid request",
                "error_code": "INVALID_REQUEST",
                "details": {"field": "query", "issue": "Query too long"},
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }


class WebSocketMessage(BaseModel):
    """WebSocket 메시지"""
    type: Literal["query", "response", "event", "error", "ping", "pong"]
    content: Optional[str] = Field(None, description="메시지 내용")
    metadata: Optional[Dict[str, Any]] = Field(None, description="메타데이터")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class FeedbackRequest(BaseModel):
    """사용자 피드백"""
    thread_id: str = Field(..., description="스레드 ID")
    message_id: Optional[str] = Field(None, description="메시지 ID")
    rating: int = Field(..., ge=1, le=5, description="평점 (1-5)")
    feedback: Optional[str] = Field(None, max_length=1000, description="피드백 내용")
    
    class Config:
        json_schema_extra = {
            "example": {
                "thread_id": "thread_123",
                "rating": 5,
                "feedback": "매우 유용한 정보였습니다"
            }
        }


class FeedbackResponse(BaseModel):
    """피드백 응답"""
    feedback_id: str = Field(..., description="피드백 ID")
    thread_id: str = Field(..., description="스레드 ID")
    received_at: str = Field(..., description="수신 시간")
    status: Literal["received", "processed"] = Field(..., description="처리 상태")