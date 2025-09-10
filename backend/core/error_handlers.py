"""
Error Handlers for Real Estate Chatbot
중앙 집중식 에러 처리
"""

from typing import Dict, Any, Optional, Type
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from datetime import datetime
import traceback

from backend.api.models import ErrorResponse


logger = logging.getLogger(__name__)


class ChatbotException(Exception):
    """챗봇 기본 예외"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "CHATBOT_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class SessionNotFoundException(ChatbotException):
    """세션을 찾을 수 없음"""
    
    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session {session_id} not found",
            error_code="SESSION_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"session_id": session_id}
        )


class ThreadNotFoundException(ChatbotException):
    """스레드를 찾을 수 없음"""
    
    def __init__(self, thread_id: str):
        super().__init__(
            message=f"Thread {thread_id} not found",
            error_code="THREAD_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"thread_id": thread_id}
        )


class AgentExecutionException(ChatbotException):
    """에이전트 실행 실패"""
    
    def __init__(self, agent_id: str, error: str):
        super().__init__(
            message=f"Agent {agent_id} execution failed: {error}",
            error_code="AGENT_EXECUTION_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"agent_id": agent_id, "error": error}
        )


class WorkflowTimeoutException(ChatbotException):
    """워크플로우 타임아웃"""
    
    def __init__(self, timeout: int):
        super().__init__(
            message=f"Workflow execution timeout after {timeout} seconds",
            error_code="WORKFLOW_TIMEOUT",
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            details={"timeout": timeout}
        )


class InvalidRequestException(ChatbotException):
    """잘못된 요청"""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="INVALID_REQUEST",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"field": field} if field else {}
        )


class AuthorizationException(ChatbotException):
    """권한 없음"""
    
    def __init__(self, resource: str):
        super().__init__(
            message=f"Not authorized to access {resource}",
            error_code="UNAUTHORIZED",
            status_code=status.HTTP_403_FORBIDDEN,
            details={"resource": resource}
        )


class RateLimitException(ChatbotException):
    """요청 제한 초과"""
    
    def __init__(self, limit: int, window: int):
        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window} seconds",
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"limit": limit, "window": window}
        )


class ExternalServiceException(ChatbotException):
    """외부 서비스 오류"""
    
    def __init__(self, service: str, error: str):
        super().__init__(
            message=f"External service {service} error: {error}",
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details={"service": service, "error": error}
        )


async def chatbot_exception_handler(request: Request, exc: ChatbotException) -> JSONResponse:
    """챗봇 예외 핸들러"""
    
    # 에러 로깅
    logger.error(
        f"ChatbotException: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    # ErrorResponse 생성
    error_response = ErrorResponse(
        error=exc.message,
        error_code=exc.error_code,
        details=exc.details,
        timestamp=datetime.now().isoformat()
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP 예외 핸들러"""
    
    logger.warning(
        f"HTTPException: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    error_response = ErrorResponse(
        error=str(exc.detail),
        error_code=f"HTTP_{exc.status_code}",
        details={"status_code": exc.status_code},
        timestamp=datetime.now().isoformat()
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """검증 예외 핸들러"""
    
    # 검증 에러 상세 정보 추출
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"][1:]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        f"ValidationError: {len(errors)} validation errors",
        extra={
            "errors": errors,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    error_response = ErrorResponse(
        error="Request validation failed",
        error_code="VALIDATION_ERROR",
        details={"validation_errors": errors},
        timestamp=datetime.now().isoformat()
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump()
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """일반 예외 핸들러"""
    
    # 스택 트레이스 로깅
    logger.error(
        f"Unhandled exception: {type(exc).__name__} - {str(exc)}",
        extra={
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc()
        },
        exc_info=True
    )
    
    # 프로덕션 환경에서는 상세 정보 숨김
    if request.app.debug:
        details = {
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc().split("\n")
        }
        message = str(exc)
    else:
        details = {}
        message = "An internal error occurred"
    
    error_response = ErrorResponse(
        error=message,
        error_code="INTERNAL_SERVER_ERROR",
        details=details,
        timestamp=datetime.now().isoformat()
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump()
    )


def register_error_handlers(app):
    """FastAPI 앱에 에러 핸들러 등록"""
    
    # 커스텀 예외 핸들러
    app.add_exception_handler(ChatbotException, chatbot_exception_handler)
    
    # HTTP 예외 핸들러
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    # 검증 예외 핸들러
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # 일반 예외 핸들러
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Error handlers registered")


class ErrorRecoveryStrategy:
    """에러 복구 전략"""
    
    def __init__(self):
        self.strategies = {
            AgentExecutionException: self._recover_agent_execution,
            WorkflowTimeoutException: self._recover_workflow_timeout,
            ExternalServiceException: self._recover_external_service,
            RateLimitException: self._recover_rate_limit
        }
    
    async def recover(self, exception: Exception, context: Dict[str, Any]) -> Optional[Any]:
        """
        예외에 대한 복구 시도
        
        Args:
            exception: 발생한 예외
            context: 복구 컨텍스트
            
        Returns:
            복구 결과 또는 None
        """
        strategy = self.strategies.get(type(exception))
        
        if strategy:
            logger.info(f"Attempting recovery for {type(exception).__name__}")
            return await strategy(exception, context)
        
        return None
    
    async def _recover_agent_execution(
        self,
        exception: AgentExecutionException,
        context: Dict[str, Any]
    ) -> Optional[Any]:
        """에이전트 실행 실패 복구"""
        
        # 재시도 횟수 확인
        retry_count = context.get("retry_count", 0)
        max_retries = context.get("max_retries", 3)
        
        if retry_count < max_retries:
            logger.info(f"Retrying agent {exception.details['agent_id']} (attempt {retry_count + 1})")
            # 재시도 로직
            return {"action": "retry", "retry_count": retry_count + 1}
        
        # 대체 에이전트 사용
        fallback_agent = context.get("fallback_agent")
        if fallback_agent:
            logger.info(f"Using fallback agent: {fallback_agent}")
            return {"action": "fallback", "agent": fallback_agent}
        
        return None
    
    async def _recover_workflow_timeout(
        self,
        exception: WorkflowTimeoutException,
        context: Dict[str, Any]
    ) -> Optional[Any]:
        """워크플로우 타임아웃 복구"""
        
        # 부분 결과 반환
        partial_results = context.get("partial_results")
        if partial_results:
            logger.info("Returning partial results due to timeout")
            return {"action": "partial", "results": partial_results}
        
        return None
    
    async def _recover_external_service(
        self,
        exception: ExternalServiceException,
        context: Dict[str, Any]
    ) -> Optional[Any]:
        """외부 서비스 오류 복구"""
        
        # 캐시된 결과 사용
        cached_result = context.get("cached_result")
        if cached_result:
            logger.info(f"Using cached result for {exception.details['service']}")
            return {"action": "cache", "result": cached_result}
        
        # 대체 서비스 사용
        alternative_service = context.get("alternative_service")
        if alternative_service:
            logger.info(f"Using alternative service: {alternative_service}")
            return {"action": "alternative", "service": alternative_service}
        
        return None
    
    async def _recover_rate_limit(
        self,
        exception: RateLimitException,
        context: Dict[str, Any]
    ) -> Optional[Any]:
        """요청 제한 초과 복구"""
        
        # 큐에 추가
        if context.get("allow_queue"):
            logger.info("Adding request to queue due to rate limit")
            return {"action": "queue", "retry_after": exception.details["window"]}
        
        return None


# 전역 에러 복구 전략 인스턴스
error_recovery = ErrorRecoveryStrategy()