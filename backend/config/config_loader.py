"""
Configuration Loader for YAML-based Supervisor Settings
Handles loading, validation, and management of agent configurations
"""

import os
import yaml
import re
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, validator
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


# ===== Pydantic Models for Configuration Validation =====

class RetryPolicy(BaseModel):
    """재시도 정책 설정"""
    max_retries: int = 3
    backoff: str = "exponential"  # constant, linear, exponential
    initial_delay: Optional[float] = 1.0
    max_delay: Optional[float] = 30.0


class TriggerConditions(BaseModel):
    """에이전트 트리거 조건"""
    intents: List[str] = []
    entities: List[str] = []
    keywords: List[str] = []


class AgentConfig(BaseModel):
    """개별 에이전트 설정"""
    id: str
    name: str
    description: str
    capabilities: List[str]
    trigger_conditions: TriggerConditions
    tools: List[str]
    max_execution_time: int = 30
    retry_policy: RetryPolicy
    priority: int = 1
    
    @validator('id')
    def validate_id(cls, v):
        if not re.match(r'^[a-z_]+$', v):
            raise ValueError('Agent ID must contain only lowercase letters and underscores')
        return v


class IntentConfig(BaseModel):
    """의도 감지 설정"""
    intent: str
    description: str
    keywords: List[str]
    examples: List[str]
    confidence_threshold: float = 0.7
    
    @validator('confidence_threshold')
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Confidence threshold must be between 0 and 1')
        return v


class EntityExtractionConfig(BaseModel):
    """엔티티 추출 설정"""
    location: Optional[Dict[str, List[str]]] = None
    price: Optional[Dict[str, List[str]]] = None
    property_type: Optional[Dict[str, List[str]]] = None
    transaction_type: Optional[Dict[str, List[str]]] = None
    area: Optional[Dict[str, List[str]]] = None


class QueryAnalyzerConfig(BaseModel):
    """질의 분석기 설정"""
    intent_detection: List[IntentConfig]
    entity_extraction: EntityExtractionConfig


class RoutingRule(BaseModel):
    """라우팅 규칙"""
    name: str
    description: str
    condition: str
    action: str
    agents: Optional[List[str]] = None
    agent_selection: Optional[str] = None
    min_confidence: Optional[float] = None
    max_agents: Optional[int] = None
    priority_boost: Optional[int] = None
    clarification_prompt: Optional[str] = None
    fallback_agent: Optional[str] = None


class ParallelExecutionConfig(BaseModel):
    """병렬 실행 설정"""
    enabled: bool = True
    max_concurrent_agents: int = 3
    timeout: int = 60
    merge_strategy: str = "confidence_weighted"


class SequentialExecutionConfig(BaseModel):
    """순차 실행 설정"""
    enabled: bool = True
    order: str = "by_dependency"
    pass_results: bool = True


class RoutingConfig(BaseModel):
    """라우팅 설정"""
    strategy: str = "confidence_based"
    rules: List[RoutingRule]
    parallel_execution: ParallelExecutionConfig
    sequential_execution: SequentialExecutionConfig


class ErrorHandlingConfig(BaseModel):
    """에러 처리 설정"""
    on_agent_failure: Dict[str, Any]
    on_timeout: Dict[str, Any]
    on_rate_limit: Dict[str, Any]


class ExecutionPoliciesConfig(BaseModel):
    """실행 정책 설정"""
    error_handling: ErrorHandlingConfig
    retry_policies: Dict[str, RetryPolicy]


class ResponseTemplates(BaseModel):
    """응답 템플릿"""
    greeting: str
    clarification: str
    processing: str
    result: str
    error: str
    multi_agent_result: str


class ResponseGenerationConfig(BaseModel):
    """응답 생성 설정"""
    format: str = "structured"
    include_confidence: bool = True
    include_sources: bool = True
    include_execution_time: bool = False
    max_length: int = 2000
    templates: ResponseTemplates


class LoggingConfig(BaseModel):
    """로깅 설정"""
    level: str = "INFO"
    include_user_query: bool = True
    include_agent_decisions: bool = True
    include_tool_calls: bool = True
    log_file: str = "logs/assistant.log"
    max_file_size: str = "100MB"
    backup_count: int = 5


class TracingConfig(BaseModel):
    """트레이싱 설정"""
    enabled: bool = True
    provider: str = "langsmith"
    project_name: str = "real-estate-assistant"
    sample_rate: float = 1.0
    include_prompt: bool = True
    include_response: bool = True


class MonitoringConfig(BaseModel):
    """모니터링 설정"""
    metrics: List[str]
    logging: LoggingConfig
    tracing: TracingConfig


class CachingConfig(BaseModel):
    """캐싱 설정"""
    enabled: bool = True
    provider: str = "redis"
    ttl: int = 3600
    cache_similar_queries: bool = True
    similarity_threshold: float = 0.95
    max_cache_size: str = "1GB"


class RateLimitingConfig(BaseModel):
    """레이트 리미팅 설정"""
    enabled: bool = True
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10
    by_user: bool = True


class ModelConfig(BaseModel):
    """모델 설정"""
    default_model: str = "gpt-4"
    fallback_model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 2000
    streaming: bool = True


class OptimizationConfig(BaseModel):
    """최적화 설정"""
    caching: CachingConfig
    rate_limiting: RateLimitingConfig
    batching: Dict[str, Any]
    model_config: ModelConfig


class InputValidationConfig(BaseModel):
    """입력 검증 설정"""
    enabled: bool = True
    max_query_length: int = 1000
    sanitize_html: bool = True
    block_patterns: List[str]


class SecurityConfig(BaseModel):
    """보안 설정"""
    input_validation: InputValidationConfig
    api_keys: Dict[str, Any]
    authentication: Dict[str, Any]


class MetadataConfig(BaseModel):
    """메타데이터"""
    name: str
    description: str
    language: str
    domain: str
    created_by: str
    created_date: str


class SupervisorConfig(BaseModel):
    """전체 Supervisor 설정"""
    version: str
    metadata: MetadataConfig
    query_analyzer: QueryAnalyzerConfig
    agents: List[AgentConfig]
    routing: RoutingConfig
    execution_policies: ExecutionPoliciesConfig
    response_generation: ResponseGenerationConfig
    monitoring: MonitoringConfig
    optimization: OptimizationConfig
    security: SecurityConfig


# ===== Configuration Manager =====

class ConfigManager:
    """
    설정 파일 로드 및 관리
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager
        
        Args:
            config_path: Path to YAML configuration file
        """
        if config_path is None:
            config_path = self._get_default_config_path()
        
        self.config_path = Path(config_path)
        self.config: Optional[SupervisorConfig] = None
        self._load_config()
    
    def _get_default_config_path(self) -> str:
        """기본 설정 파일 경로 반환"""
        return os.path.join(
            os.path.dirname(__file__),
            "supervisor_config.yaml"
        )
    
    def _load_config(self) -> None:
        """YAML 설정 파일 로드"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Pydantic 모델로 검증 및 파싱
            self.config = SupervisorConfig(**data)
            logger.info(f"Configuration loaded successfully from {self.config_path}")
            
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def reload_config(self) -> None:
        """설정 파일 다시 로드"""
        logger.info("Reloading configuration...")
        self._load_config()
    
    # ===== Agent Management =====
    
    def get_agent_by_id(self, agent_id: str) -> Optional[AgentConfig]:
        """ID로 에이전트 검색"""
        for agent in self.config.agents:
            if agent.id == agent_id:
                return agent
        return None
    
    def get_agents_by_intent(self, intent: str) -> List[AgentConfig]:
        """의도에 맞는 에이전트 목록 반환"""
        matching_agents = []
        for agent in self.config.agents:
            if intent in agent.trigger_conditions.intents:
                matching_agents.append(agent)
        return sorted(matching_agents, key=lambda x: x.priority)
    
    def get_agents_by_keywords(self, text: str) -> List[AgentConfig]:
        """텍스트에 포함된 키워드로 에이전트 검색"""
        matching_agents = []
        text_lower = text.lower()
        
        for agent in self.config.agents:
            keywords = agent.trigger_conditions.keywords
            if any(keyword.lower() in text_lower for keyword in keywords):
                matching_agents.append(agent)
        
        return sorted(matching_agents, key=lambda x: x.priority)
    
    def get_agents_by_entity(self, entity_type: str) -> List[AgentConfig]:
        """엔티티 타입으로 에이전트 검색"""
        matching_agents = []
        for agent in self.config.agents:
            if entity_type in agent.trigger_conditions.entities:
                matching_agents.append(agent)
        return sorted(matching_agents, key=lambda x: x.priority)
    
    # ===== Intent Management =====
    
    def get_intent_config(self, intent_name: str) -> Optional[IntentConfig]:
        """특정 의도 설정 반환"""
        for intent_config in self.config.query_analyzer.intent_detection:
            if intent_config.intent == intent_name:
                return intent_config
        return None
    
    def get_all_intents(self) -> List[str]:
        """모든 의도 이름 목록 반환"""
        return [i.intent for i in self.config.query_analyzer.intent_detection]
    
    # ===== Routing Management =====
    
    def get_routing_rule(self, condition: str) -> Optional[RoutingRule]:
        """조건에 맞는 라우팅 규칙 반환"""
        for rule in self.config.routing.rules:
            if rule.condition == condition:
                return rule
        return None
    
    def get_routing_strategy(self) -> str:
        """라우팅 전략 반환"""
        return self.config.routing.strategy
    
    # ===== Template Management =====
    
    def get_response_template(self, template_name: str) -> str:
        """응답 템플릿 반환"""
        templates = self.config.response_generation.templates
        return getattr(templates, template_name, "")
    
    def format_response(self, template_name: str, **kwargs) -> str:
        """템플릿에 값 채워서 응답 생성"""
        template = self.get_response_template(template_name)
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            return template
    
    # ===== Utility Methods =====
    
    def get_max_concurrent_agents(self) -> int:
        """최대 동시 실행 에이전트 수 반환"""
        return self.config.routing.parallel_execution.max_concurrent_agents
    
    def get_retry_policy(self, policy_name: str = "default") -> RetryPolicy:
        """재시도 정책 반환"""
        policies = self.config.execution_policies.retry_policies
        return policies.get(policy_name, policies.get("default"))
    
    def validate_query_length(self, query: str) -> bool:
        """질의 길이 검증"""
        max_length = self.config.security.input_validation.max_query_length
        return len(query) <= max_length
    
    def get_blocked_patterns(self) -> List[str]:
        """차단된 패턴 목록 반환"""
        return self.config.security.input_validation.block_patterns
    
    def to_dict(self) -> dict:
        """설정을 딕셔너리로 변환"""
        return self.config.dict() if self.config else {}
    
    def save_config(self, path: Optional[str] = None) -> None:
        """설정을 YAML 파일로 저장"""
        save_path = path or self.config_path
        with open(save_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.to_dict(), f, allow_unicode=True, default_flow_style=False)
        logger.info(f"Configuration saved to {save_path}")


# ===== Singleton Pattern for Global Config =====

_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """
    싱글톤 패턴으로 ConfigManager 인스턴스 반환
    
    Args:
        config_path: Optional path to configuration file
    
    Returns:
        ConfigManager instance
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    
    return _config_manager


def reload_config() -> None:
    """전역 설정 다시 로드"""
    global _config_manager
    if _config_manager:
        _config_manager.reload_config()


# ===== Testing and Validation =====

def validate_config_file(config_path: str) -> tuple[bool, List[str]]:
    """
    설정 파일 유효성 검증
    
    Returns:
        (is_valid, error_messages)
    """
    errors = []
    
    try:
        manager = ConfigManager(config_path)
        
        # 에이전트 중복 체크
        agent_ids = [a.id for a in manager.config.agents]
        if len(agent_ids) != len(set(agent_ids)):
            errors.append("Duplicate agent IDs found")
        
        # 필수 에이전트 체크
        required_agents = ["price_search_agent", "finance_agent", 
                          "location_agent", "legal_agent"]
        for req_agent in required_agents:
            if req_agent not in agent_ids:
                errors.append(f"Required agent missing: {req_agent}")
        
        # 의도 중복 체크
        intents = manager.get_all_intents()
        if len(intents) != len(set(intents)):
            errors.append("Duplicate intent names found")
        
    except Exception as e:
        errors.append(f"Configuration validation failed: {str(e)}")
    
    return len(errors) == 0, errors


if __name__ == "__main__":
    # 테스트 코드
    try:
        config = get_config_manager()
        print(f"Configuration loaded: {config.config.metadata.name}")
        print(f"Version: {config.config.version}")
        print(f"Agents: {len(config.config.agents)}")
        
        # 에이전트 검색 테스트
        agents = config.get_agents_by_keywords("시세")
        print(f"Agents for '시세': {[a.name for a in agents]}")
        
    except Exception as e:
        print(f"Error: {e}")