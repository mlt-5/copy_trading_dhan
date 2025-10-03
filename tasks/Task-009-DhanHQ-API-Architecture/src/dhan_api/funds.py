"""
DhanHQ v2 Funds API Module

Handle fund limits, balance, margin calculations, and fund operations.

API Documentation: https://dhanhq.co/docs/v2/funds/
"""

import logging
from typing import Optional, Dict, Any
from dhanhq import dhanhq

logger = logging.getLogger(__name__)


class FundsAPI:
    """
    DhanHQ v2 Funds API wrapper.
    
    Covers:
    - Get Fund Limits
    - Get Margin Calculator
    - Fund Transfer operations (if supported)
    """
    
    def __init__(self, client: dhanhq, account_type: str):
        """
        Initialize Funds API.
        
        Args:
            client: Authenticated DhanHQ client
            account_type: 'leader' or 'follower'
        """
        self.client = client
        self.account_type = account_type
        logger.info(f"Funds API initialized for {account_type}")
    
    def get_fund_limits(self) -> Optional[Dict[str, Any]]:
        """
        Get fund limits and balance.
        
        Per DhanHQ v2 Funds API, returns:
        - availableBalance: Available balance for trading
        - sodLimit: Start of day limit
        - collateralAmount: Collateral amount
        - utilizedAmount: Margin utilized
        - receivedAmount: Funds received
        - blockedPayoutAmount: Blocked payout
        - etc.
        
        Returns:
            Fund limits dict
        """
        try:
            response = self.client.get_fund_limits()
            
            if response:
                # Extract key fields for logging
                available = response.get('availableBalance', 0)
                utilized = response.get('utilizedAmount', 0)
                
                logger.debug("Fund limits retrieved", extra={
                    "account_type": self.account_type,
                    "available_balance": available,
                    "utilized_amount": utilized
                })
                
                return response
            else:
                logger.error("Failed to retrieve fund limits", extra={
                    "account_type": self.account_type
                })
                return None
        
        except Exception as e:
            logger.error("Get fund limits error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def calculate_margin(
        self,
        security_id: str,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        product_type: str,
        order_type: str,
        price: float
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate margin requirement for an order.
        
        Args:
            security_id: Security ID
            exchange_segment: Exchange segment
            transaction_type: BUY or SELL
            quantity: Order quantity
            product_type: Product type (MIS, NRML, CNC)
            order_type: Order type (MARKET, LIMIT)
            price: Price (for limit orders)
        
        Returns:
            Margin calculation dict with:
            - requiredMargin
            - availableMargin
            - exposureMargin
            - etc.
        """
        try:
            logger.debug("Calculating margin requirement", extra={
                "account_type": self.account_type,
                "security_id": security_id,
                "quantity": quantity
            })
            
            request = {
                'security_id': security_id,
                'exchange_segment': exchange_segment,
                'transaction_type': transaction_type,
                'quantity': quantity,
                'product_type': product_type,
                'order_type': order_type,
                'price': price
            }
            
            # Note: API method name may differ - verify from docs
            response = self.client.calculate_margin(**request)
            
            if response:
                required_margin = response.get('requiredMargin', 0)
                logger.debug(f"Margin required: {required_margin}", extra={
                    "account_type": self.account_type
                })
                return response
            else:
                logger.error("Margin calculation failed")
                return None
        
        except Exception as e:
            logger.error("Margin calculation error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def get_available_balance(self) -> float:
        """
        Get available balance (convenience method).
        
        Returns:
            Available balance as float, or 0.0 if error
        """
        try:
            funds = self.get_fund_limits()
            if funds:
                return float(funds.get('availableBalance', 0.0))
            return 0.0
        except Exception as e:
            logger.error(f"Error getting available balance: {e}")
            return 0.0
    
    def get_margin_used(self) -> float:
        """
        Get utilized margin (convenience method).
        
        Returns:
            Utilized margin as float, or 0.0 if error
        """
        try:
            funds = self.get_fund_limits()
            if funds:
                return float(funds.get('utilizedAmount', 0.0))
            return 0.0
        except Exception as e:
            logger.error(f"Error getting margin used: {e}")
            return 0.0

