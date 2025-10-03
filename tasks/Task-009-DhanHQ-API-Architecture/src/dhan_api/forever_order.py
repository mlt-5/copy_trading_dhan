"""
DhanHQ v2 Forever Order (GTT) API Module

Handle Good Till Triggered (GTT) orders - standing orders that remain active
until triggered or manually cancelled.

API Documentation: https://dhanhq.co/docs/v2/forever/
"""

import logging
from typing import Optional, Dict, Any, List
from dhanhq import dhanhq

logger = logging.getLogger(__name__)


class ForeverOrderAPI:
    """
    DhanHQ v2 Forever Orders (GTT) API wrapper.
    
    GTT (Good Till Triggered) Orders:
    - Remain active beyond a single trading day
    - Triggered when condition is met
    - Can set stop-loss, target, or both
    - Valid for multiple days until triggered or cancelled
    """
    
    def __init__(self, client: dhanhq, account_type: str):
        """
        Initialize Forever Order API.
        
        Args:
            client: Authenticated DhanHQ client
            account_type: 'leader' or 'follower'
        """
        self.client = client
        self.account_type = account_type
        logger.info(f"Forever Order API initialized for {account_type}")
    
    def create_gtt_order(
        self,
        security_id: str,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        product_type: str,
        price: float,
        trigger_price: float,
        disclosed_quantity: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a GTT (Good Till Triggered) order.
        
        Args:
            security_id: Security ID
            exchange_segment: Exchange segment
            transaction_type: BUY or SELL
            quantity: Order quantity
            product_type: CNC, INTRADAY, MARGIN
            price: Limit price
            trigger_price: Trigger price (condition)
            disclosed_quantity: Disclosed quantity
        
        Returns:
            GTT order response with ID
        """
        try:
            logger.info(f"Creating GTT order ({transaction_type})", extra={
                "account_type": self.account_type,
                "security_id": security_id,
                "trigger_price": trigger_price
            })
            
            # Note: Actual API method name may differ - verify from docs
            # This is a placeholder implementation
            request = {
                'security_id': security_id,
                'exchange_segment': exchange_segment,
                'transaction_type': transaction_type,
                'quantity': quantity,
                'product_type': product_type,
                'price': price,
                'trigger_price': trigger_price
            }
            
            if disclosed_quantity is not None:
                request['disclosed_quantity'] = disclosed_quantity
            
            # API call - method name needs verification from docs
            response = self.client.create_gtt_order(**request)
            
            if response and 'id' in response:
                logger.info(f"GTT order created: {response['id']}", extra={
                    "account_type": self.account_type
                })
                return response
            else:
                logger.error(f"GTT creation failed: {response}")
                return None
        
        except Exception as e:
            logger.error("GTT order creation error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def modify_gtt_order(
        self,
        gtt_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Modify an existing GTT order.
        
        Args:
            gtt_id: GTT order ID
            quantity: New quantity
            price: New price
            trigger_price: New trigger price
        
        Returns:
            Modification response
        """
        try:
            logger.info(f"Modifying GTT order: {gtt_id}", extra={
                "account_type": self.account_type
            })
            
            request = {'gtt_id': gtt_id}
            
            if quantity is not None:
                request['quantity'] = quantity
            if price is not None:
                request['price'] = price
            if trigger_price is not None:
                request['trigger_price'] = trigger_price
            
            response = self.client.modify_gtt_order(**request)
            
            return response if response else None
        
        except Exception as e:
            logger.error("GTT modification error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def cancel_gtt_order(self, gtt_id: str) -> Optional[Dict[str, Any]]:
        """
        Cancel a GTT order.
        
        Args:
            gtt_id: GTT order ID
        
        Returns:
            Cancellation response
        """
        try:
            logger.info(f"Cancelling GTT order: {gtt_id}", extra={
                "account_type": self.account_type
            })
            
            response = self.client.cancel_gtt_order(gtt_id)
            
            if response:
                logger.info(f"GTT order cancelled: {gtt_id}")
                return response
            else:
                logger.error(f"GTT cancellation failed: {response}")
                return None
        
        except Exception as e:
            logger.error("GTT cancellation error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def get_gtt_order_list(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get list of all GTT orders.
        
        Returns:
            List of GTT order dicts
        """
        try:
            response = self.client.get_gtt_order_list()
            
            if response and isinstance(response, list):
                logger.debug(f"Retrieved {len(response)} GTT orders", extra={
                    "account_type": self.account_type
                })
                return response
            else:
                return []
        
        except Exception as e:
            logger.error("Get GTT list error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def get_gtt_order_by_id(self, gtt_id: str) -> Optional[Dict[str, Any]]:
        """
        Get GTT order details by ID.
        
        Args:
            gtt_id: GTT order ID
        
        Returns:
            GTT order details
        """
        try:
            response = self.client.get_gtt_order_by_id(gtt_id)
            
            return response if response else None
        
        except Exception as e:
            logger.error("Get GTT order error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None


# Note: This module provides interface for GTT orders.
# Actual API method names should be verified from official DhanHQ v2 Forever Orders documentation.
# Some methods may not exist or have different names - update after consulting docs.

