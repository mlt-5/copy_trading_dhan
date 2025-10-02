"""
Authentication Module

Handle DhanHQ authentication for both leader and follower accounts.
Implements credential validation, client initialization, and token management.
"""

import logging
from typing import Optional
from dhanhq import dhanhq

from ..config import AccountConfig, get_config

logger = logging.getLogger(__name__)


class DhanAuthManager:
    """
    Manage DhanHQ authentication for leader and follower accounts.
    
    Attributes:
        leader_client: Initialized DhanHQ client for leader account
        follower_client: Initialized DhanHQ client for follower account
    """
    
    def __init__(self, leader_config: AccountConfig, follower_config: AccountConfig):
        """
        Initialize authentication manager.
        
        Args:
            leader_config: Leader account configuration
            follower_config: Follower account configuration
        """
        self.leader_config = leader_config
        self.follower_config = follower_config
        self.leader_client: Optional[dhanhq] = None
        self.follower_client: Optional[dhanhq] = None
    
    def authenticate_leader(self) -> dhanhq:
        """
        Initialize and authenticate leader account client.
        
        Returns:
            Initialized DhanHQ client for leader account
        
        Raises:
            ValueError: If credentials are invalid
            Exception: If authentication fails
        """
        logger.info("Authenticating leader account", extra={
            "client_id": self.leader_config.client_id,
            "account_type": "leader"
        })
        
        try:
            self.leader_client = dhanhq(
                self.leader_config.client_id,
                self.leader_config.access_token
            )
            
            # Validate credentials by fetching fund limits
            funds = self.leader_client.get_fund_limits()
            
            if funds is None or 'status' in funds and funds['status'] == 'failure':
                raise ValueError(f"Leader authentication failed: {funds}")
            
            logger.info("Leader account authenticated successfully", extra={
                "client_id": self.leader_config.client_id
            })
            
            return self.leader_client
            
        except Exception as e:
            logger.error("Leader authentication failed", extra={
                "client_id": self.leader_config.client_id,
                "error": str(e)
            }, exc_info=True)
            raise
    
    def authenticate_follower(self) -> dhanhq:
        """
        Initialize and authenticate follower account client.
        
        Returns:
            Initialized DhanHQ client for follower account
        
        Raises:
            ValueError: If credentials are invalid
            Exception: If authentication fails
        """
        logger.info("Authenticating follower account", extra={
            "client_id": self.follower_config.client_id,
            "account_type": "follower"
        })
        
        try:
            self.follower_client = dhanhq(
                self.follower_config.client_id,
                self.follower_config.access_token
            )
            
            # Validate credentials by fetching fund limits
            funds = self.follower_client.get_fund_limits()
            
            if funds is None or 'status' in funds and funds['status'] == 'failure':
                raise ValueError(f"Follower authentication failed: {funds}")
            
            logger.info("Follower account authenticated successfully", extra={
                "client_id": self.follower_config.client_id
            })
            
            return self.follower_client
            
        except Exception as e:
            logger.error("Follower authentication failed", extra={
                "client_id": self.follower_config.client_id,
                "error": str(e)
            }, exc_info=True)
            raise
    
    def authenticate_all(self) -> tuple[dhanhq, dhanhq]:
        """
        Authenticate both leader and follower accounts.
        
        Returns:
            Tuple of (leader_client, follower_client)
        
        Raises:
            Exception: If either authentication fails
        """
        leader = self.authenticate_leader()
        follower = self.authenticate_follower()
        
        logger.info("Both accounts authenticated successfully")
        
        return leader, follower
    
    def validate_connection(self, client: dhanhq, account_type: str) -> bool:
        """
        Validate that the client connection is still active.
        
        Args:
            client: DhanHQ client to validate
            account_type: 'leader' or 'follower'
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            funds = client.get_fund_limits()
            if funds is None or 'status' in funds and funds['status'] == 'failure':
                logger.warning(f"{account_type} connection validation failed", extra={
                    "account_type": account_type,
                    "response": funds
                })
                return False
            return True
        except Exception as e:
            logger.error(f"{account_type} connection validation error", extra={
                "account_type": account_type,
                "error": str(e)
            })
            return False
    
    def rotate_tokens(self, new_leader_token: Optional[str] = None, 
                      new_follower_token: Optional[str] = None) -> None:
        """
        Rotate access tokens without restart (hot reload).
        
        Args:
            new_leader_token: New access token for leader (if rotating)
            new_follower_token: New access token for follower (if rotating)
        """
        if new_leader_token:
            logger.info("Rotating leader access token")
            self.leader_config.access_token = new_leader_token
            self.leader_client = None
            self.authenticate_leader()
        
        if new_follower_token:
            logger.info("Rotating follower access token")
            self.follower_config.access_token = new_follower_token
            self.follower_client = None
            self.authenticate_follower()


# Global auth manager instance
_auth_manager: Optional[DhanAuthManager] = None


def authenticate_accounts() -> DhanAuthManager:
    """
    Initialize and authenticate both accounts (singleton pattern).
    
    Returns:
        Authenticated DhanAuthManager instance
    
    Raises:
        Exception: If authentication fails
    """
    global _auth_manager
    
    if _auth_manager is None:
        leader_config, follower_config, _ = get_config()
        _auth_manager = DhanAuthManager(leader_config, follower_config)
        _auth_manager.authenticate_all()
    
    return _auth_manager


def get_leader_client() -> dhanhq:
    """
    Get authenticated leader client.
    
    Returns:
        Leader DhanHQ client
    
    Raises:
        ValueError: If not authenticated yet
    """
    if _auth_manager is None or _auth_manager.leader_client is None:
        raise ValueError("Leader client not authenticated. Call authenticate_accounts() first.")
    return _auth_manager.leader_client


def get_follower_client() -> dhanhq:
    """
    Get authenticated follower client.
    
    Returns:
        Follower DhanHQ client
    
    Raises:
        ValueError: If not authenticated yet
    """
    if _auth_manager is None or _auth_manager.follower_client is None:
        raise ValueError("Follower client not authenticated. Call authenticate_accounts() first.")
    return _auth_manager.follower_client


