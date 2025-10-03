"""
DhanHQ v2 Trader's Control API Module

Handle trading controls, kill switch, and account settings.

API Documentation: https://dhanhq.co/docs/v2/traders-control/
"""

import logging
from typing import Optional, Dict, Any
from dhanhq import dhanhq

logger = logging.getLogger(__name__)


class TradersControlAPI:
    """
    DhanHQ v2 Trader's Control API wrapper.
    
    Covers:
    - Kill Switch (disable all trading)
    - Trading limits and controls
    - Account settings
    """
    
    def __init__(self, client: dhanhq, account_type: str):
        """
        Initialize Trader's Control API.
        
        Args:
            client: Authenticated DhanHQ client
            account_type: 'leader' or 'follower'
        """
        self.client = client
        self.account_type = account_type
        logger.info(f"Trader's Control API initialized for {account_type}")
    
    def enable_kill_switch(self) -> Optional[Dict[str, Any]]:
        """
        Enable kill switch (disable all trading).
        
        Emergency stop for all trading activity.
        
        Returns:
            Response confirming kill switch enabled
        """
        try:
            logger.warning("Enabling KILL SWITCH", extra={
                "account_type": self.account_type
            })
            
            response = self.client.enable_kill_switch()
            
            if response and response.get('status') == 'success':
                logger.critical("KILL SWITCH ENABLED - All trading disabled", extra={
                    "account_type": self.account_type
                })
                return response
            else:
                logger.error("Failed to enable kill switch")
                return None
        
        except Exception as e:
            logger.error("Kill switch enable error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def disable_kill_switch(self) -> Optional[Dict[str, Any]]:
        """
        Disable kill switch (re-enable trading).
        
        Returns:
            Response confirming kill switch disabled
        """
        try:
            logger.warning("Disabling kill switch", extra={
                "account_type": self.account_type
            })
            
            response = self.client.disable_kill_switch()
            
            if response and response.get('status') == 'success':
                logger.info("Kill switch disabled - Trading re-enabled", extra={
                    "account_type": self.account_type
                })
                return response
            else:
                logger.error("Failed to disable kill switch")
                return None
        
        except Exception as e:
            logger.error("Kill switch disable error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def get_kill_switch_status(self) -> bool:
        """
        Get kill switch status.
        
        Returns:
            True if kill switch is enabled, False otherwise
        """
        try:
            response = self.client.get_kill_switch_status()
            
            if response:
                status = response.get('enabled', False)
                logger.debug(f"Kill switch status: {'ENABLED' if status else 'DISABLED'}")
                return status
            return False
        
        except Exception as e:
            logger.error("Get kill switch status error", exc_info=True, extra={
                "error": str(e)
            })
            return False
    
    def set_trading_limits(
        self,
        max_loss: Optional[float] = None,
        max_profit: Optional[float] = None,
        max_orders: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Set trading limits for the account.
        
        Args:
            max_loss: Maximum loss allowed (INR)
            max_profit: Maximum profit target (INR)
            max_orders: Maximum number of orders per day
        
        Returns:
            Response confirming limits set
        """
        try:
            logger.info("Setting trading limits", extra={
                "account_type": self.account_type,
                "max_loss": max_loss,
                "max_profit": max_profit,
                "max_orders": max_orders
            })
            
            request = {}
            if max_loss is not None:
                request['max_loss'] = max_loss
            if max_profit is not None:
                request['max_profit'] = max_profit
            if max_orders is not None:
                request['max_orders'] = max_orders
            
            response = self.client.set_trading_limits(**request)
            
            if response:
                logger.info("Trading limits set successfully")
                return response
            else:
                logger.error("Failed to set trading limits")
                return None
        
        except Exception as e:
            logger.error("Set trading limits error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def get_trading_limits(self) -> Optional[Dict[str, Any]]:
        """
        Get current trading limits.
        
        Returns:
            Trading limits dict
        """
        try:
            response = self.client.get_trading_limits()
            
            return response if response else None
        
        except Exception as e:
            logger.error("Get trading limits error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None


# Note: Trader's Control API methods should be verified from official documentation.
# Some methods may not exist or have different names - update after consulting docs.

