"""Configuration module for the Real Estate Assistant"""

from .config_loader import (
    ConfigManager,
    get_config_manager,
    reload_config,
    validate_config_file,
    SupervisorConfig,
    AgentConfig,
    IntentConfig,
    RoutingConfig
)
from .settings import Settings

# Create settings instance
settings = Settings()

__all__ = [
    'ConfigManager',
    'get_config_manager',
    'reload_config',
    'validate_config_file',
    'SupervisorConfig',
    'AgentConfig',
    'IntentConfig',
    'RoutingConfig',
    'Settings',
    'settings'
]