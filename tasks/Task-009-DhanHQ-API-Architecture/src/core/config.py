"""
Configuration Management Module

Centralized configuration, authentication credentials, and environment management
per DhanHQ v2 integration rules.
"""

import os
from dataclasses import dataclass
from typing import Optional, Literal
from enum import Enum


class Environment(str, Enum):
    """DhanHQ environment types."""
    PRODUCTION = "prod"
    SANDBOX = "sandbox"


class SizingStrategy(str, Enum):
    """Position sizing strategies."""
    CAPITAL_PROPORTIONAL = "capital_proportional"
    FIXED_RATIO = "fixed_ratio"
    RISK_BASED = "risk_based"


@dataclass
class AccountConfig:
    """
    Configuration for a DhanHQ account (leader or follower).
    
    Attributes:
        client_id: DhanHQ client ID
        access_token: DhanHQ access token (redacted in logs)
        account_type: 'leader' or 'follower'
    """
    client_id: str
    access_token: str
    account_type: Literal['leader', 'follower']
    
    def __repr__(self) -> str:
        """Redact access token in string representation."""
        token_preview = f"{self.access_token[:8]}...{self.access_token[-4:]}" if self.access_token else "None"
        return f"AccountConfig(client_id={self.client_id}, access_token={token_preview}, account_type={self.account_type})"


@dataclass
class SystemConfig:
    """
    Global system configuration.
    
    Attributes:
        environment: Production or sandbox
        base_url: DhanHQ API base URL
        ws_url: DhanHQ WebSocket URL
        timeout: HTTP request timeout in seconds
        retry_attempts: Maximum retry attempts for idempotent operations
        retry_delay: Initial retry delay in seconds
        retry_backoff_multiplier: Exponential backoff multiplier
        rate_limit_per_second: Client-side rate limiting
        circuit_breaker_threshold: Failures before opening circuit
        circuit_breaker_timeout: Seconds before attempting recovery
        sqlite_path: Path to SQLite database file
        sizing_strategy: Default position sizing strategy
        copy_ratio: Fixed ratio for fixed_ratio strategy (optional)
        max_position_size_pct: Maximum position size as % of capital
        enable_copy_trading: Global enable/disable flag
        log_level: Logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
    """
    environment: Environment = Environment.PRODUCTION
    base_url: str = "https://api.dhan.co"
    ws_url: str = "wss://api-feed.dhan.co"
    timeout: int = 10
    retry_attempts: int = 3
    retry_delay: float = 1.0
    retry_backoff_multiplier: float = 2.0
    rate_limit_per_second: int = 10
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    sqlite_path: str = "./copy_trading.db"
    sizing_strategy: SizingStrategy = SizingStrategy.CAPITAL_PROPORTIONAL
    copy_ratio: Optional[float] = None
    max_position_size_pct: float = 10.0
    enable_copy_trading: bool = True
    log_level: str = "INFO"


class ConfigLoader:
    """
    Load configuration from environment variables.
    
    Environment Variables:
        # Required
        LEADER_CLIENT_ID: Leader account client ID
        LEADER_ACCESS_TOKEN: Leader account access token
        FOLLOWER_CLIENT_ID: Follower account client ID
        FOLLOWER_ACCESS_TOKEN: Follower account access token
        
        # Optional
        DHAN_ENV: prod or sandbox (default: prod)
        DHAN_API_BASE_URL: Override default base URL
        DHAN_WS_URL: Override default WebSocket URL
        COPY_RATIO: Fixed ratio for position sizing
        MAX_POSITION_SIZE_PCT: Maximum position size % (default: 10.0)
        SIZING_STRATEGY: capital_proportional/fixed_ratio/risk_based
        ENABLE_COPY_TRADING: true/false (default: true)
        SQLITE_PATH: Database file path (default: ./copy_trading.db)
        LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL (default: INFO)
    """
    
    @staticmethod
    def load_leader_config() -> AccountConfig:
        """Load leader account configuration from environment."""
        client_id = os.getenv("LEADER_CLIENT_ID")
        access_token = os.getenv("LEADER_ACCESS_TOKEN")
        
        if not client_id or not access_token:
            raise ValueError(
                "Missing required environment variables: LEADER_CLIENT_ID and/or LEADER_ACCESS_TOKEN"
            )
        
        return AccountConfig(
            client_id=client_id,
            access_token=access_token,
            account_type='leader'
        )
    
    @staticmethod
    def load_follower_config() -> AccountConfig:
        """Load follower account configuration from environment."""
        client_id = os.getenv("FOLLOWER_CLIENT_ID")
        access_token = os.getenv("FOLLOWER_ACCESS_TOKEN")
        
        if not client_id or not access_token:
            raise ValueError(
                "Missing required environment variables: FOLLOWER_CLIENT_ID and/or FOLLOWER_ACCESS_TOKEN"
            )
        
        return AccountConfig(
            client_id=client_id,
            access_token=access_token,
            account_type='follower'
        )
    
    @staticmethod
    def load_system_config() -> SystemConfig:
        """Load system configuration from environment."""
        env_str = os.getenv("DHAN_ENV", "prod").lower()
        environment = Environment.PRODUCTION if env_str == "prod" else Environment.SANDBOX
        
        base_url = os.getenv("DHAN_API_BASE_URL", "https://api.dhan.co")
        ws_url = os.getenv("DHAN_WS_URL", "wss://api-feed.dhan.co")
        
        sizing_strategy_str = os.getenv("SIZING_STRATEGY", "capital_proportional").lower()
        try:
            sizing_strategy = SizingStrategy(sizing_strategy_str)
        except ValueError:
            sizing_strategy = SizingStrategy.CAPITAL_PROPORTIONAL
        
        copy_ratio_str = os.getenv("COPY_RATIO")
        copy_ratio = float(copy_ratio_str) if copy_ratio_str else None
        
        max_position_pct_str = os.getenv("MAX_POSITION_SIZE_PCT", "10.0")
        max_position_size_pct = float(max_position_pct_str)
        
        enable_copy_str = os.getenv("ENABLE_COPY_TRADING", "true").lower()
        enable_copy_trading = enable_copy_str in ("true", "1", "yes", "on")
        
        sqlite_path = os.getenv("SQLITE_PATH", "./copy_trading.db")
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        
        return SystemConfig(
            environment=environment,
            base_url=base_url,
            ws_url=ws_url,
            sqlite_path=sqlite_path,
            sizing_strategy=sizing_strategy,
            copy_ratio=copy_ratio,
            max_position_size_pct=max_position_size_pct,
            enable_copy_trading=enable_copy_trading,
            log_level=log_level
        )
    
    @classmethod
    def load_all(cls) -> tuple[AccountConfig, AccountConfig, SystemConfig]:
        """
        Load all configurations.
        
        Returns:
            Tuple of (leader_config, follower_config, system_config)
        """
        leader = cls.load_leader_config()
        follower = cls.load_follower_config()
        system = cls.load_system_config()
        
        return leader, follower, system


# Global configuration instance (singleton pattern)
_config_instance: Optional[tuple[AccountConfig, AccountConfig, SystemConfig]] = None


def get_config() -> tuple[AccountConfig, AccountConfig, SystemConfig]:
    """
    Get configuration singleton instance.
    
    Returns:
        Tuple of (leader_config, follower_config, system_config)
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = ConfigLoader.load_all()
    
    return _config_instance


def reload_config() -> tuple[AccountConfig, AccountConfig, SystemConfig]:
    """
    Force reload configuration from environment (for token rotation).
    
    Returns:
        Tuple of (leader_config, follower_config, system_config)
    """
    global _config_instance
    _config_instance = ConfigLoader.load_all()
    return _config_instance

