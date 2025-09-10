"""
Context Schema for LangGraph 0.6.6 Runtime API
부동산 챗봇의 런타임 의존성 관리
"""

from dataclasses import dataclass, field
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime


@dataclass
class RealEstateContext:
    """
    부동산 챗봇 런타임 컨텍스트
    불변 데이터만 포함 (동적 데이터는 State에서 관리)
    """
    
    # === 필수 사용자 정보 ===
    user_id: str
    user_name: str
    session_id: str
    
    # === 사용자 역할 및 권한 ===
    user_role: Literal["admin", "user", "guest"] = "user"
    
    # === 모델 설정 ===
    model_provider: Literal["openai", "anthropic"] = "openai"
    model_name: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2000
    streaming: bool = False
    
    # === 시스템 설정 ===
    system_message: Optional[str] = None
    available_agents: List[str] = field(default_factory=lambda: [
        "analyzer_agent",
        "planner_agent", 
        "supervisor_agent",
        "price_search_agent",
        "finance_agent",
        "location_agent",
        "legal_agent"
    ])
    
    # === 실행 설정 ===
    execution_strategy: Literal["sequential", "parallel", "hybrid"] = "sequential"
    max_execution_time: int = 60  # seconds
    max_retries: int = 3
    enable_cache: bool = True
    
    # === 외부 리소스 ===
    db_connection_string: Optional[str] = None
    api_endpoints: Dict[str, str] = field(default_factory=dict)
    api_keys: Dict[str, str] = field(default_factory=dict)
    
    # === 메타데이터 ===
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    environment: Literal["development", "staging", "production"] = "development"
    version: str = "1.0.0"
    
    # === 기능 플래그 ===
    features: Dict[str, bool] = field(default_factory=lambda: {
        "enable_memory": True,
        "enable_tools": True,
        "enable_streaming": False,
        "enable_human_in_loop": False,
        "enable_error_recovery": True
    })
    
    def __post_init__(self):
        """초기화 후 처리 및 검증"""
        # 세션 ID가 없으면 user_id 기반으로 생성
        if not self.session_id:
            self.session_id = f"session_{self.user_id}_{datetime.now().timestamp()}"
        
        # 시스템 메시지 기본값 설정
        if not self.system_message:
            self.system_message = self._get_default_system_message()
        
        # API 키 검증 (프로덕션 환경)
        if self.environment == "production":
            self._validate_api_keys()
    
    def _get_default_system_message(self) -> str:
        """기본 시스템 메시지 생성"""
        return f"""당신은 전문적인 부동산 AI 어시스턴트입니다.
사용자: {self.user_name} ({self.user_role})
세션 ID: {self.session_id}

주요 역할:
1. 부동산 시세 정보 제공
2. 금융 상담 (대출, 세금)
3. 입지 분석 및 교통 정보
4. 법률 자문 및 계약 검토

항상 정확하고 신뢰할 수 있는 정보를 제공하며,
필요시 여러 전문 에이전트와 협력하여 종합적인 답변을 제공합니다."""
    
    def _validate_api_keys(self):
        """API 키 검증"""
        if self.model_provider == "openai" and "openai" not in self.api_keys:
            raise ValueError("OpenAI API key is required in production")
        if self.model_provider == "anthropic" and "anthropic" not in self.api_keys:
            raise ValueError("Anthropic API key is required in production")
    
    def to_dict(self) -> Dict[str, Any]:
        """Context를 딕셔너리로 변환"""
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "session_id": self.session_id,
            "user_role": self.user_role,
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "streaming": self.streaming,
            "execution_strategy": self.execution_strategy,
            "available_agents": self.available_agents,
            "features": self.features,
            "environment": self.environment,
            "version": self.version
        }
    
    def get_model_config(self) -> Dict[str, Any]:
        """모델 설정 반환"""
        return {
            "provider": self.model_provider,
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "streaming": self.streaming
        }
    
    def is_agent_available(self, agent_id: str) -> bool:
        """특정 에이전트 사용 가능 여부"""
        return agent_id in self.available_agents
    
    def get_execution_config(self) -> Dict[str, Any]:
        """실행 설정 반환"""
        return {
            "strategy": self.execution_strategy,
            "max_time": self.max_execution_time,
            "max_retries": self.max_retries,
            "enable_cache": self.enable_cache
        }


class ContextFactory:
    """Context 생성 팩토리"""
    
    @staticmethod
    def create_for_user(
        user_id: str,
        user_name: str,
        session_id: Optional[str] = None,
        **kwargs
    ) -> RealEstateContext:
        """일반 사용자용 Context 생성"""
        return RealEstateContext(
            user_id=user_id,
            user_name=user_name,
            session_id=session_id or f"session_{user_id}",
            user_role="user",
            **kwargs
        )
    
    @staticmethod
    def create_for_admin(
        user_id: str,
        user_name: str,
        session_id: Optional[str] = None
    ) -> RealEstateContext:
        """관리자용 Context 생성"""
        return RealEstateContext(
            user_id=user_id,
            user_name=user_name,
            session_id=session_id or f"admin_session_{user_id}",
            user_role="admin",
            model_name="gpt-4",
            temperature=0.3,  # 더 정확한 응답
            max_tokens=4000,  # 더 긴 응답
            features={
                "enable_memory": True,
                "enable_tools": True,
                "enable_streaming": True,
                "enable_human_in_loop": True,
                "enable_error_recovery": True
            }
        )
    
    @staticmethod
    def create_for_guest() -> RealEstateContext:
        """게스트용 Context 생성"""
        import uuid
        guest_id = str(uuid.uuid4())
        
        return RealEstateContext(
            user_id=f"guest_{guest_id}",
            user_name="Guest",
            session_id=f"guest_session_{guest_id}",
            user_role="guest",
            model_name="gpt-3.5-turbo",  # 비용 효율적인 모델
            max_tokens=1000,  # 제한된 토큰
            available_agents=[  # 제한된 에이전트
                "analyzer_agent",
                "price_search_agent"
            ],
            features={
                "enable_memory": False,  # 메모리 비활성화
                "enable_tools": True,
                "enable_streaming": False,
                "enable_human_in_loop": False,
                "enable_error_recovery": True
            }
        )
    
    @staticmethod
    def create_for_testing(
        test_id: str = "test_user"
    ) -> RealEstateContext:
        """테스트용 Context 생성"""
        return RealEstateContext(
            user_id=test_id,
            user_name="Test User",
            session_id=f"test_session_{test_id}",
            user_role="user",
            environment="development",
            model_provider="openai",
            model_name="gpt-3.5-turbo",
            temperature=0.0,  # 일관된 결과
            max_retries=1,  # 빠른 실패
            max_execution_time=10  # 짧은 타임아웃
        )