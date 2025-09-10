"""
Logging Configuration for Real Estate Chatbot
중앙 집중식 로깅 설정
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """컬러 출력을 위한 포매터"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_file: bool = True,
    log_dir: str = "logs"
) -> None:
    """
    로깅 설정 초기화
    
    Args:
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 로그 파일 이름 (없으면 자동 생성)
        enable_console: 콘솔 출력 활성화
        enable_file: 파일 출력 활성화
        log_dir: 로그 디렉토리
    """
    
    # 로그 디렉토리 생성
    if enable_file:
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # 기존 핸들러 제거
    root_logger.handlers.clear()
    
    # 포맷 설정
    detailed_format = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    simple_format = "%(asctime)s - %(levelname)s - %(message)s"
    
    # 콘솔 핸들러
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        
        # 개발 환경에서는 컬러 포매터 사용
        if sys.stdout.isatty():
            console_formatter = ColoredFormatter(simple_format)
        else:
            console_formatter = logging.Formatter(simple_format)
        
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # 파일 핸들러
    if enable_file:
        if not log_file:
            log_file = f"chatbot_{datetime.now().strftime('%Y%m%d')}.log"
        
        file_path = log_path / log_file
        
        # 로테이팅 파일 핸들러 (10MB, 5개 백업)
        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # 파일에는 모든 로그 기록
        file_formatter = logging.Formatter(detailed_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # 특정 라이브러리 로그 레벨 조정
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.INFO)
    logging.getLogger("langgraph").setLevel(logging.INFO)
    
    # 초기 로그
    root_logger.info(f"Logging initialized - Level: {log_level}")
    if enable_file:
        root_logger.info(f"Log file: {file_path}")


def get_logger(name: str) -> logging.Logger:
    """
    모듈별 로거 생성
    
    Args:
        name: 로거 이름 (보통 __name__ 사용)
        
    Returns:
        Logger 인스턴스
    """
    return logging.getLogger(name)


class LogContext:
    """로깅 컨텍스트 관리자"""
    
    def __init__(self, logger: logging.Logger, operation: str, **kwargs):
        self.logger = logger
        self.operation = operation
        self.context = kwargs
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"Starting {self.operation}", extra=self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type:
            self.logger.error(
                f"Failed {self.operation} after {duration:.2f}s: {exc_val}",
                extra={**self.context, "duration": duration},
                exc_info=True
            )
        else:
            self.logger.info(
                f"Completed {self.operation} in {duration:.2f}s",
                extra={**self.context, "duration": duration}
            )
        
        return False  # 예외를 전파


# 구조화된 로깅을 위한 어댑터
class StructuredLogger:
    """구조화된 로깅 어댑터"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_event(self, event_type: str, **kwargs):
        """이벤트 로깅"""
        self.logger.info(
            f"Event: {event_type}",
            extra={"event_type": event_type, **kwargs}
        )
    
    def log_metric(self, metric_name: str, value: float, **kwargs):
        """메트릭 로깅"""
        self.logger.info(
            f"Metric: {metric_name}={value}",
            extra={"metric_name": metric_name, "value": value, **kwargs}
        )
    
    def log_error(self, error: Exception, context: str = "", **kwargs):
        """에러 로깅"""
        self.logger.error(
            f"Error in {context}: {str(error)}",
            extra={"error_type": type(error).__name__, "context": context, **kwargs},
            exc_info=True
        )
    
    def log_api_call(self, method: str, endpoint: str, status_code: int, duration: float, **kwargs):
        """API 호출 로깅"""
        level = logging.INFO if 200 <= status_code < 400 else logging.WARNING
        self.logger.log(
            level,
            f"API {method} {endpoint} - {status_code} ({duration:.2f}s)",
            extra={
                "method": method,
                "endpoint": endpoint,
                "status_code": status_code,
                "duration": duration,
                **kwargs
            }
        )
    
    def log_agent_execution(self, agent_id: str, status: str, duration: float, **kwargs):
        """에이전트 실행 로깅"""
        self.logger.info(
            f"Agent {agent_id} - {status} ({duration:.2f}s)",
            extra={
                "agent_id": agent_id,
                "status": status,
                "duration": duration,
                **kwargs
            }
        )


# 전역 설정 함수
def configure_logging_for_environment(environment: str = "development"):
    """
    환경별 로깅 설정
    
    Args:
        environment: 환경 (development, staging, production)
    """
    configs = {
        "development": {
            "log_level": "DEBUG",
            "enable_console": True,
            "enable_file": True,
            "log_dir": "logs/dev"
        },
        "staging": {
            "log_level": "INFO",
            "enable_console": True,
            "enable_file": True,
            "log_dir": "logs/staging"
        },
        "production": {
            "log_level": "WARNING",
            "enable_console": False,
            "enable_file": True,
            "log_dir": "logs/prod"
        }
    }
    
    config = configs.get(environment, configs["development"])
    setup_logging(**config)


# 사용 예시
if __name__ == "__main__":
    # 로깅 설정
    setup_logging(log_level="DEBUG")
    
    # 로거 생성
    logger = get_logger(__name__)
    structured = StructuredLogger(logger)
    
    # 로깅 예시
    logger.info("Application started")
    
    # 구조화된 로깅
    structured.log_event("user_login", user_id="user123", session_id="session456")
    structured.log_metric("response_time", 0.125, endpoint="/api/chat")
    
    # 컨텍스트 매니저 사용
    with LogContext(logger, "database_query", query="SELECT * FROM users"):
        # 작업 수행
        pass