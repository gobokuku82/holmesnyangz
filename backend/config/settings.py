"""
Application Settings and Environment Configuration
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    
    # === Application Settings ===
    app_name: str = Field(default="Real Estate AI Assistant", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")  # development, staging, production
    
    # === API Settings ===
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    cors_origins: list = Field(default=["http://localhost:3000", "http://localhost:3001"], env="CORS_ORIGINS")
    
    # === LLM API Keys ===
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    langchain_api_key: Optional[str] = Field(default=None, env="LANGCHAIN_API_KEY")
    
    # === LangSmith Configuration ===
    langchain_tracing_v2: bool = Field(default=True, env="LANGCHAIN_TRACING_V2")
    langchain_project: str = Field(default="real-estate-assistant", env="LANGCHAIN_PROJECT")
    langchain_endpoint: str = Field(default="https://api.smith.langchain.com", env="LANGCHAIN_ENDPOINT")
    
    # === Database Configuration ===
    database_url: Optional[str] = Field(
        default="postgresql://user:password@localhost:5432/realestate",
        env="DATABASE_URL"
    )
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # === ChromaDB Configuration ===
    chroma_persist_directory: str = Field(default="./chroma_db", env="CHROMA_PERSIST_DIRECTORY")
    chroma_collection_name: str = Field(default="real_estate_docs", env="CHROMA_COLLECTION_NAME")
    
    # === Security Settings ===
    secret_key: str = Field(
        default="your-secret-key-change-this-in-production",
        env="SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=60, env="JWT_EXPIRATION_MINUTES")
    
    # === Rate Limiting ===
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    
    # === Logging Configuration ===
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/app.log", env="LOG_FILE")
    log_max_size: str = Field(default="100MB", env="LOG_MAX_SIZE")
    log_backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    
    # === Model Configuration ===
    default_model: str = Field(default="gpt-4", env="DEFAULT_MODEL")
    fallback_model: str = Field(default="gpt-3.5-turbo", env="FALLBACK_MODEL")
    model_temperature: float = Field(default=0.7, env="MODEL_TEMPERATURE")
    model_max_tokens: int = Field(default=2000, env="MODEL_MAX_TOKENS")
    
    # === Agent Configuration ===
    max_agent_execution_time: int = Field(default=60, env="MAX_AGENT_EXECUTION_TIME")
    max_concurrent_agents: int = Field(default=3, env="MAX_CONCURRENT_AGENTS")
    agent_retry_attempts: int = Field(default=3, env="AGENT_RETRY_ATTEMPTS")
    
    # === Cache Configuration ===
    cache_enabled: bool = Field(default=True, env="CACHE_ENABLED")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")  # seconds
    
    # === Real Estate API Keys (외부 서비스) ===
    naver_api_key: Optional[str] = Field(default=None, env="NAVER_API_KEY")
    kakao_api_key: Optional[str] = Field(default=None, env="KAKAO_API_KEY")
    data_go_kr_api_key: Optional[str] = Field(default=None, env="DATA_GO_KR_API_KEY")
    
    # === File Paths ===
    upload_dir: str = Field(default="uploads", env="UPLOAD_DIR")
    static_dir: str = Field(default="static", env="STATIC_DIR")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def validate_required_keys(self) -> tuple[bool, list[str]]:
        """
        필수 API 키 검증
        
        Returns:
            (is_valid, missing_keys)
        """
        missing_keys = []
        
        # LLM API 키 중 하나는 필수
        if not (self.openai_api_key or self.anthropic_api_key):
            missing_keys.append("Either OPENAI_API_KEY or ANTHROPIC_API_KEY is required")
        
        # Production 환경에서 필수 키
        if self.environment == "production":
            if self.secret_key == "your-secret-key-change-this-in-production":
                missing_keys.append("SECRET_KEY must be changed in production")
            
            if not self.database_url:
                missing_keys.append("DATABASE_URL is required in production")
        
        return len(missing_keys) == 0, missing_keys
    
    def get_llm_config(self) -> dict:
        """LLM 설정 반환"""
        config = {
            "temperature": self.model_temperature,
            "max_tokens": self.model_max_tokens,
        }
        
        if self.openai_api_key:
            config["openai_api_key"] = self.openai_api_key
            config["model"] = self.default_model
        elif self.anthropic_api_key:
            config["anthropic_api_key"] = self.anthropic_api_key
            config["model"] = "claude-3-opus-20240229"
        
        return config
    
    def get_database_config(self) -> dict:
        """데이터베이스 설정 반환"""
        return {
            "database_url": self.database_url,
            "redis_url": self.redis_url,
            "chroma_persist_directory": self.chroma_persist_directory,
            "chroma_collection_name": self.chroma_collection_name,
        }
    
    def get_security_config(self) -> dict:
        """보안 설정 반환"""
        return {
            "secret_key": self.secret_key,
            "jwt_algorithm": self.jwt_algorithm,
            "jwt_expiration_minutes": self.jwt_expiration_minutes,
            "rate_limit_enabled": self.rate_limit_enabled,
            "rate_limit_requests_per_minute": self.rate_limit_requests_per_minute,
        }
    
    def create_directories(self) -> None:
        """필요한 디렉토리 생성"""
        directories = [
            self.upload_dir,
            self.static_dir,
            self.chroma_persist_directory,
            os.path.dirname(self.log_file),
        ]
        
        for directory in directories:
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)


# Singleton pattern for settings
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get application settings (singleton)
    
    Returns:
        Settings instance
    """
    global _settings
    
    if _settings is None:
        _settings = Settings()
        _settings.create_directories()
        
        # 설정 검증
        is_valid, missing_keys = _settings.validate_required_keys()
        if not is_valid:
            import warnings
            for key in missing_keys:
                warnings.warn(f"Missing configuration: {key}")
    
    return _settings


def reload_settings() -> Settings:
    """
    Reload settings from environment
    
    Returns:
        New Settings instance
    """
    global _settings
    _settings = None
    return get_settings()


# Export settings instance
settings = get_settings()


if __name__ == "__main__":
    # 설정 테스트
    import json
    
    test_settings = get_settings()
    print("=== Application Settings ===")
    print(f"App Name: {test_settings.app_name}")
    print(f"Environment: {test_settings.environment}")
    print(f"Debug Mode: {test_settings.debug}")
    print(f"API Host: {test_settings.api_host}:{test_settings.api_port}")
    
    print("\n=== LLM Configuration ===")
    print(json.dumps(test_settings.get_llm_config(), indent=2))
    
    print("\n=== Validation ===")
    is_valid, missing = test_settings.validate_required_keys()
    if is_valid:
        print("✅ All required keys are present")
    else:
        print("❌ Missing keys:")
        for key in missing:
            print(f"  - {key}")