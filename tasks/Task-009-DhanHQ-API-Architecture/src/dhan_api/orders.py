"""
DhanHQ v2 Orders API Module

Handle basic order operations: place, modify, cancel, get orders.
Does NOT include Super Orders (CO/BO) or Forever Orders (GTT).

API Documentation: https://dhanhq.co/docs/v2/orders/
"""

import logging
import time
from typing import Optional, Dict, Any, List
from dhanhq import dhanhq

logger = logging.getLogger(__name__)


class OrdersAPI:
    """
    DhanHQ v2 Orders API wrapper.
    
    Covers:
    - Place Order
    - Modify Order
    - Cancel Order
    - Get Order by ID
    - Get Order List
    - Get Order History
    
    Does NOT cover:
    - Cover Orders (CO) - see super_order.py
    - Bracket Orders (BO) - see super_order.py
    - GTT Orders - see forever_order.py
    """
    
    def __init__(self, client: dhanhq, account_type: str):
        """
        Initialize Orders API.
        
        Args:
            client: Authenticated DhanHQ client
            account_type: 'leader' or 'follower'
        """
        self.client = client
        self.account_type = account_type
        logger.info(f"Orders API initialized for {account_type}")
    
    def place_order(
        self,
        security_id: str,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        order_type: str,
        product_type: str,
        price: float = 0.0,
        trigger_price: Optional[float] = None,
        disclosed_quantity: Optional[int] = None,
        validity: str = 'DAY',
        amo_time: Optional[str] = None,
        bo_profit_value: Optional[float] = None,
        bo_stop_loss_value: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Place a new order.
        
        Per DhanHQ v2 Orders API:
        
        Args:
            security_id: Security ID (from instruments API)
            exchange_segment: NSE_EQ, NSE_FNO, BSE_EQ, MCX_COMM, CDS_FUT, etc.
            transaction_type: BUY or SELL
            quantity: Order quantity (must be in multiples of lot size)
            order_type: MARKET, LIMIT, STOP_LOSS, STOP_LOSS_MARKET
            product_type: CNC, INTRADAY, MARGIN, MTF, CO, BO
            price: Limit price (required for LIMIT, STOP_LOSS)
            trigger_price: Trigger price (required for STOP_LOSS, STOP_LOSS_MARKET)
            disclosed_quantity: Disclosed quantity for iceberg orders
            validity: DAY, IOC
            amo_time: OPEN, OPEN_30, OPEN_60 (for AMO orders)
            bo_profit_value: Profit value for BO orders
            bo_stop_loss_value: Stop loss value for BO orders
        
        Returns:
            Order response dict with orderId, or None if failed
        """
        try:
            logger.info(f"Placing {transaction_type} order", extra={
                "account_type": self.account_type,
                "security_id": security_id,
                "quantity": quantity,
                "order_type": order_type,
                "product_type": product_type
            })
            
            # Build request
            request = {
                'security_id': security_id,
                'exchange_segment': exchange_segment,
                'transaction_type': transaction_type,
                'quantity': quantity,
                'order_type': order_type,
                'product_type': product_type,
                'price': price,
                'validity': validity
            }
            
            # Optional fields
            if trigger_price is not None:
                request['trigger_price'] = trigger_price
            if disclosed_quantity is not None:
                request['disclosed_quantity'] = disclosed_quantity
            if amo_time is not None:
                request['amo_time'] = amo_time
            if bo_profit_value is not None:
                request['bo_profit_value'] = bo_profit_value
            if bo_stop_loss_value is not None:
                request['bo_stop_loss_value'] = bo_stop_loss_value
            
            start_time = time.time()
            response = self.client.place_order(**request)
            duration_ms = int((time.time() - start_time) * 1000)
            
            if response and 'orderId' in response:
                logger.info(f"Order placed successfully: {response['orderId']}", extra={
                    "account_type": self.account_type,
                    "order_id": response['orderId'],
                    "duration_ms": duration_ms
                })
                return response
            else:
                logger.error(f"Order placement failed: {response}", extra={
                    "account_type": self.account_type
                })
                return None
        
        except Exception as e:
            logger.error("Order placement error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def modify_order(
        self,
        order_id: str,
        order_type: str,
        leg_name: Optional[str] = None,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        disclosed_quantity: Optional[int] = None,
        trigger_price: Optional[float] = None,
        validity: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Modify an existing order.
        
        Per DhanHQ v2 Orders API:
        - Can modify quantity, price, order type, validity
        - Cannot modify security, exchange, transaction type
        
        Args:
            order_id: Order ID to modify
            order_type: New order type (LIMIT, MARKET, STOP_LOSS, STOP_LOSS_MARKET)
            leg_name: For BO/CO orders (ENTRY_LEG, STOP_LOSS_LEG, TARGET_LEG)
            quantity: New quantity
            price: New limit price
            disclosed_quantity: New disclosed quantity
            trigger_price: New trigger price
            validity: New validity
        
        Returns:
            Response dict, or None if failed
        """
        try:
            logger.info(f"Modifying order: {order_id}", extra={
                "account_type": self.account_type,
                "order_id": order_id
            })
            
            # Build request
            request = {
                'order_id': order_id,
                'order_type': order_type
            }
            
            # Optional fields
            if leg_name is not None:
                request['leg_name'] = leg_name
            if quantity is not None:
                request['quantity'] = quantity
            if price is not None:
                request['price'] = price
            if disclosed_quantity is not None:
                request['disclosed_quantity'] = disclosed_quantity
            if trigger_price is not None:
                request['trigger_price'] = trigger_price
            if validity is not None:
                request['validity'] = validity
            
            response = self.client.modify_order(**request)
            
            if response and (response.get('status') == 'success' or 'orderId' in response):
                logger.info(f"Order modified successfully: {order_id}", extra={
                    "account_type": self.account_type
                })
                return response
            else:
                logger.error(f"Order modification failed: {response}", extra={
                    "account_type": self.account_type
                })
                return None
        
        except Exception as e:
            logger.error("Order modification error", exc_info=True, extra={
                "account_type": self.account_type,
                "order_id": order_id,
                "error": str(e)
            })
            return None
    
    def cancel_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Cancel an existing order.
        
        Args:
            order_id: Order ID to cancel
        
        Returns:
            Response dict, or None if failed
        """
        try:
            logger.info(f"Cancelling order: {order_id}", extra={
                "account_type": self.account_type,
                "order_id": order_id
            })
            
            response = self.client.cancel_order(order_id)
            
            if response and (response.get('status') == 'success' or 'orderId' in response):
                logger.info(f"Order cancelled successfully: {order_id}", extra={
                    "account_type": self.account_type
                })
                return response
            else:
                logger.error(f"Order cancellation failed: {response}", extra={
                    "account_type": self.account_type
                })
                return None
        
        except Exception as e:
            logger.error("Order cancellation error", exc_info=True, extra={
                "account_type": self.account_type,
                "order_id": order_id,
                "error": str(e)
            })
            return None
    
    def get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get order details by order ID.
        
        Args:
            order_id: Order ID
        
        Returns:
            Order details dict, or None if failed
        """
        try:
            response = self.client.get_order_by_id(order_id)
            
            if response:
                return response
            else:
                logger.warning(f"Order not found: {order_id}", extra={
                    "account_type": self.account_type
                })
                return None
        
        except Exception as e:
            logger.error("Get order error", exc_info=True, extra={
                "account_type": self.account_type,
                "order_id": order_id,
                "error": str(e)
            })
            return None
    
    def get_order_list(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get list of all orders for the day.
        
        Returns:
            List of order dicts, or None if failed
        """
        try:
            response = self.client.get_order_list()
            
            if response and isinstance(response, list):
                logger.debug(f"Retrieved {len(response)} orders", extra={
                    "account_type": self.account_type,
                    "count": len(response)
                })
                return response
            else:
                logger.warning("No orders found or API error", extra={
                    "account_type": self.account_type,
                    "response": response
                })
                return []
        
        except Exception as e:
            logger.error("Get order list error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def get_trade_history(self, order_id: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get trade history (filled orders).
        
        Args:
            order_id: Optional order ID to filter trades
        
        Returns:
            List of trade dicts, or None if failed
        """
        try:
            if order_id:
                response = self.client.get_trade_book(order_id)
            else:
                response = self.client.get_trade_book()
            
            if response and isinstance(response, list):
                logger.debug(f"Retrieved {len(response)} trades", extra={
                    "account_type": self.account_type,
                    "count": len(response)
                })
                return response
            else:
                return []
        
        except Exception as e:
            logger.error("Get trade history error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None

