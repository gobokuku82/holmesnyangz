"""
API Request/Response Schemas
Pydantic models for FastAPI endpoints
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# === Session Management ===

class SessionStartRequest(BaseModel):
    """세션 시작 요청 (선택적 필드)"""
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user-123",
                "metadata": {"device": "mobile", "version": "1.0"}
            }
        }


class SessionStartResponse(BaseModel):
    """세션 생성 응답"""
    session_id: str
    created_at: str
    expires_at: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session-550e8400-e29b-41d4-a716-446655440000",
                "created_at": "2025-10-08T14:30:00.000Z",
                "expires_at": "2025-10-09T14:30:00.000Z"
            }
        }


# === Chat ===

class ChatRequest(BaseModel):
    """채팅 요청"""
    query: str = Field(..., min_length=1, max_length=5000, description="사용자 질문")
    session_id: str = Field(..., description="세션 ID (필수)")
    enable_checkpointing: bool = Field(default=True, description="Checkpoint 활성화 여부")
    user_context: Optional[Dict[str, Any]] = Field(default={}, description="추가 컨텍스트")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "강남구 아파트 시세 알려줘",
                "session_id": "session-550e8400-e29b-41d4-a716-446655440000",
                "enable_checkpointing": True,
                "user_context": {}
            }
        }


class ProcessFlowStep(BaseModel):
    """
    프론트엔드 ProcessFlow용 단계
    StepMapper에서 생성됨
    """
    step: str = Field(..., description="단계 타입 (planning, searching, analyzing, generating)")
    label: str = Field(..., description="한글 레이블 (계획, 검색, 분석, 생성)")
    agent: str = Field(..., description="담당 agent 이름")
    status: str = Field(..., description="상태 (pending, in_progress, completed, failed)")
    progress: int = Field(..., description="진행률 0-100")


class ChatResponse(BaseModel):
    """
    채팅 응답 - 상세 정보 포함 (Option B)
    추후 프로덕션 배포 시 요약 버전으로 변경 예정
    """
    # 기본 정보
    session_id: str = Field(..., description="세션 ID")
    request_id: str = Field(..., description="요청 ID")
    status: str = Field(..., description="처리 상태 (success, error, processing)")

    # 최종 응답
    response: Dict[str, Any] = Field(..., description="최종 사용자 응답 (final_response)")

    # 상세 정보 (Option B - 디버깅/개발용)
    planning_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="계획 정보 (execution_steps, strategy 등)"
    )
    team_results: Optional[Dict[str, Any]] = Field(
        default=None,
        description="각 팀의 상세 실행 결과"
    )
    search_results: Optional[List[Dict]] = Field(
        default=None,
        description="검색 결과 원본 데이터"
    )
    analysis_metrics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="분석 지표 (평균, 표준편차 등)"
    )

    # ProcessFlow (NEW - 프론트엔드 시각화용)
    process_flow: Optional[List[ProcessFlowStep]] = Field(
        default=None,
        description="프론트엔드 ProcessFlow 시각화 데이터"
    )

    # 실행 메타데이터
    execution_time_ms: Optional[int] = Field(
        default=None,
        description="총 실행 시간 (밀리초)"
    )
    teams_executed: List[str] = Field(
        default=[],
        description="실행된 팀 목록"
    )
    execution_phases: List[str] = Field(
        default=[],
        description="실행 단계 목록"
    )

    # Checkpoint 정보
    checkpoint_id: Optional[str] = Field(
        default=None,
        description="Checkpoint ID (복원용)"
    )

    # 에러 정보
    error: Optional[str] = Field(
        default=None,
        description="에러 메시지 (있는 경우)"
    )
    error_details: Optional[Dict] = Field(
        default=None,
        description="상세 에러 정보"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "session_id": "session-550e8400-e29b-41d4-a716-446655440000",
                "request_id": "req_1696789200.123",
                "status": "success",
                "response": {
                    "type": "answer",
                    "content": "강남구 아파트 평균 시세는 10억원입니다.",
                    "data": {
                        "average_price": 1000000000,
                        "region": "강남구"
                    }
                },
                "planning_info": {
                    "execution_steps": [
                        {"agent": "search_team", "status": "completed"},
                        {"agent": "analysis_team", "status": "completed"}
                    ],
                    "execution_strategy": "sequential"
                },
                "execution_time_ms": 3500,
                "teams_executed": ["search", "analysis"],
                "error": None
            }
        }


# === Error Handling ===

class ErrorResponse(BaseModel):
    """표준 에러 응답"""
    status: str = Field(default="error", description="응답 상태")
    error_code: str = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    details: Optional[Dict] = Field(default=None, description="상세 정보")
    timestamp: str = Field(..., description="에러 발생 시각")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "error_code": "INVALID_INPUT",
                "message": "Query cannot be empty",
                "details": {"field": "query"},
                "timestamp": "2025-10-08T14:30:00.000Z"
            }
        }


# === Session Info ===

class SessionInfo(BaseModel):
    """세션 정보 응답"""
    session_id: str
    created_at: str
    expires_at: str
    last_activity: str
    metadata: Dict[str, Any] = {}

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session-550e8400-e29b-41d4-a716-446655440000",
                "created_at": "2025-10-08T14:30:00.000Z",
                "expires_at": "2025-10-09T14:30:00.000Z",
                "last_activity": "2025-10-08T15:45:00.000Z",
                "metadata": {"user_id": "user-123"}
            }
        }


class DeleteSessionResponse(BaseModel):
    """세션 삭제 응답"""
    message: str
    session_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Session deleted",
                "session_id": "session-550e8400-e29b-41d4-a716-446655440000"
            }
        }
