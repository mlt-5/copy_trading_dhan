"""
DhanHQ v2 Super Order API Module

Handle Cover Orders (CO) and Bracket Orders (BO) specific operations.

API Documentation: https://dhanhq.co/docs/v2/super-order/
"""

import logging
from typing import Optional, Dict, Any
from dhanhq import dhanhq

logger = logging.getLogger(__name__)


class SuperOrderAPI:
    """
    DhanHQ v2 Super Orders API wrapper.
    
    Covers:
    - Cover Orders (CO)
    - Bracket Orders (BO)
    - Modify CO/BO legs
    - Cancel CO/BO legs
    
    Key Differences from Basic Orders:
    - productType must be 'CO' or 'BO'
    - Additional parameters for stop-loss and target
    - OCO (One-Cancels-Other) logic for BO
    """
    
    def __init__(self, client: dhanhq, account_type: str):
        """
        Initialize Super Order API.
        
        Args:
            client: Authenticated DhanHQ client
            account_type: 'leader' or 'follower'
        """
        self.client = client
        self.account_type = account_type
        logger.info(f"Super Order API initialized for {account_type}")
    
    def place_cover_order(
        self,
        security_id: str,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        order_type: str,
        price: float,
        stop_loss_value: float,
        trigger_price: Optional[float] = None,
        disclosed_quantity: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Place a Cover Order (CO).
        
        Per DhanHQ v2 Super Order API:
        - productType = 'CO'
        - Must include stop_loss_value (absolute or percentage)
        - Entry order placed first, then stop-loss leg auto-created
        
        Args:
            security_id: Security ID
            exchange_segment: Exchange segment
            transaction_type: BUY or SELL
            quantity: Order quantity
            order_type: LIMIT or MARKET
            price: Entry price
            stop_loss_value: Stop-loss value (absolute or % based on API)
            trigger_price: Trigger price for entry if stop-loss order
            disclosed_quantity: Disclosed quantity
        
        Returns:
            Order response with parent orderId
        """
        try:
            logger.info(f"Placing Cover Order ({transaction_type})", extra={
                "account_type": self.account_type,
                "security_id": security_id,
                "quantity": quantity,
                "stop_loss": stop_loss_value
            })
            
            request = {
                'security_id': security_id,
                'exchange_segment': exchange_segment,
                'transaction_type': transaction_type,
                'quantity': quantity,
                'order_type': order_type,
                'product_type': 'CO',  # Cover Order
                'price': price,
                'validity': 'DAY',
                'stop_loss_value': stop_loss_value
            }
            
            if trigger_price is not None:
                request['trigger_price'] = trigger_price
            if disclosed_quantity is not None:
                request['disclosed_quantity'] = disclosed_quantity
            
            response = self.client.place_order(**request)
            
            if response and 'orderId' in response:
                logger.info(f"Cover Order placed: {response['orderId']}", extra={
                    "account_type": self.account_type,
                    "order_id": response['orderId']
                })
                return response
            else:
                logger.error(f"CO placement failed: {response}")
                return None
        
        except Exception as e:
            logger.error("Cover Order placement error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def place_bracket_order(
        self,
        security_id: str,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        order_type: str,
        price: float,
        stop_loss_value: float,
        profit_value: float,
        disclosed_quantity: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Place a Bracket Order (BO).
        
        Per DhanHQ v2 Super Order API:
        - productType = 'BO'
        - Must include both stop_loss_value and profit_value
        - Three legs: Entry, Stop-Loss, Target (profit)
        - OCO logic: If one leg executes, the other cancels
        
        Args:
            security_id: Security ID
            exchange_segment: Exchange segment
            transaction_type: BUY or SELL
            quantity: Order quantity
            order_type: LIMIT or MARKET
            price: Entry price
            stop_loss_value: Stop-loss value (absolute or %)
            profit_value: Target profit value (absolute or %)
            disclosed_quantity: Disclosed quantity
        
        Returns:
            Order response with parent orderId
        """
        try:
            logger.info(f"Placing Bracket Order ({transaction_type})", extra={
                "account_type": self.account_type,
                "security_id": security_id,
                "quantity": quantity,
                "stop_loss": stop_loss_value,
                "target": profit_value
            })
            
            request = {
                'security_id': security_id,
                'exchange_segment': exchange_segment,
                'transaction_type': transaction_type,
                'quantity': quantity,
                'order_type': order_type,
                'product_type': 'BO',  # Bracket Order
                'price': price,
                'validity': 'DAY',
                'stop_loss_value': stop_loss_value,
                'profit_value': profit_value
            }
            
            if disclosed_quantity is not None:
                request['disclosed_quantity'] = disclosed_quantity
            
            response = self.client.place_order(**request)
            
            if response and 'orderId' in response:
                logger.info(f"Bracket Order placed: {response['orderId']}", extra={
                    "account_type": self.account_type,
                    "order_id": response['orderId']
                })
                return response
            else:
                logger.error(f"BO placement failed: {response}")
                return None
        
        except Exception as e:
            logger.error("Bracket Order placement error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def modify_cover_order(
        self,
        order_id: str,
        leg_name: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        stop_loss_value: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Modify Cover Order leg.
        
        Args:
            order_id: Parent order ID
            leg_name: ENTRY_LEG or STOP_LOSS_LEG
            quantity: New quantity
            price: New price
            trigger_price: New trigger price
            stop_loss_value: New stop-loss value
        
        Returns:
            Modification response
        """
        try:
            logger.info(f"Modifying CO leg: {leg_name}", extra={
                "account_type": self.account_type,
                "order_id": order_id
            })
            
            request = {
                'order_id': order_id,
                'leg_name': leg_name,
                'order_type': 'LIMIT'  # Default, adjust as needed
            }
            
            if quantity is not None:
                request['quantity'] = quantity
            if price is not None:
                request['price'] = price
            if trigger_price is not None:
                request['trigger_price'] = trigger_price
            if stop_loss_value is not None:
                request['stop_loss_value'] = stop_loss_value
            
            response = self.client.modify_order(**request)
            
            return response if response else None
        
        except Exception as e:
            logger.error("CO modification error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def modify_bracket_order(
        self,
        order_id: str,
        leg_name: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        stop_loss_value: Optional[float] = None,
        profit_value: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Modify Bracket Order leg.
        
        Args:
            order_id: Parent order ID
            leg_name: ENTRY_LEG, STOP_LOSS_LEG, or TARGET_LEG
            quantity: New quantity
            price: New price
            trigger_price: New trigger price
            stop_loss_value: New stop-loss value
            profit_value: New profit target value
        
        Returns:
            Modification response
        """
        try:
            logger.info(f"Modifying BO leg: {leg_name}", extra={
                "account_type": self.account_type,
                "order_id": order_id
            })
            
            request = {
                'order_id': order_id,
                'leg_name': leg_name,
                'order_type': 'LIMIT'
            }
            
            if quantity is not None:
                request['quantity'] = quantity
            if price is not None:
                request['price'] = price
            if trigger_price is not None:
                request['trigger_price'] = trigger_price
            if stop_loss_value is not None:
                request['stop_loss_value'] = stop_loss_value
            if profit_value is not None:
                request['profit_value'] = profit_value
            
            response = self.client.modify_order(**request)
            
            return response if response else None
        
        except Exception as e:
            logger.error("BO modification error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def cancel_super_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Cancel Cover or Bracket Order (cancels all legs).
        
        Args:
            order_id: Parent order ID
        
        Returns:
            Cancellation response
        """
        try:
            logger.info(f"Cancelling Super Order: {order_id}", extra={
                "account_type": self.account_type
            })
            
            response = self.client.cancel_order(order_id)
            
            if response:
                logger.info(f"Super Order cancelled: {order_id}")
                return response
            else:
                logger.error(f"Cancellation failed: {response}")
                return None
        
        except Exception as e:
            logger.error("Super Order cancellation error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None

