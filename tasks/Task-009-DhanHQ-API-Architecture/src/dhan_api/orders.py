"""
DhanHQ v2 Orders API Module

Handle basic order operations: place, modify, cancel, get orders, and trade book.

Implements all 9 DhanHQ v2 Orders API endpoints:
- POST /orders - Place order
- POST /orders/slicing - Place slice order (over freeze limit)
- PUT /orders/{order-id} - Modify order
- DELETE /orders/{order-id} - Cancel order
- GET /orders - Get order book (order list)
- GET /orders/{order-id} - Get order by ID
- GET /orders/external/{correlation-id} - Get order by correlation ID
- GET /trades - Get trade book (all trades for the day)
- GET /trades/{order-id} - Get trades of an order

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
    
    Covers all 9 Orders API endpoints:
    - Place Order
    - Place Slice Order (over freeze limit)
    - Modify Order
    - Cancel Order
    - Get Order Book (order list)
    - Get Order by ID
    - Get Order by Correlation ID
    - Get Trade Book (all trades)
    - Get Trades of an Order
    
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
        after_market_order: bool = False,
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
            after_market_order: Flag for after market orders (AMO)
            amo_time: PRE_OPEN, OPEN, OPEN_30, OPEN_60 (timing for AMO orders)
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
            if after_market_order:
                request['after_market_order'] = after_market_order
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
    
    def place_slice_order(
        self,
        security_id: str,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        order_type: str,
        product_type: str,
        price: Optional[float] = None,
        validity: str = 'DAY',
        trigger_price: Optional[float] = None,
        disclosed_quantity: Optional[int] = None,
        after_market_order: bool = False,
        amo_time: Optional[str] = None,
        bo_profit_value: Optional[float] = None,
        bo_stop_loss_value: Optional[float] = None,
        correlation_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Place a sliced order (for quantities over freeze limit).
        
        This API helps slice order requests into multiple orders to allow 
        placement over freeze limit quantity for F&O instruments.
        
        Parameters are the same as place_order().
        
        Per DhanHQ v2 Orders API:
        https://dhanhq.co/docs/v2/orders/#order-slicing
        
        Args:
            security_id: Security/instrument ID
            exchange_segment: Exchange segment (NSE_EQ, NSE_FNO, etc.)
            transaction_type: BUY or SELL
            quantity: Total quantity (will be sliced if over freeze limit)
            order_type: LIMIT, MARKET, STOP_LOSS, STOP_LOSS_MARKET
            product_type: CNC, INTRADAY, MARGIN, MTF, CO, BO
            price: Limit price (required for LIMIT orders)
            validity: DAY or IOC
            trigger_price: Trigger price (for SL/SL-M orders)
            disclosed_quantity: Disclosed quantity
            after_market_order: AMO flag
            amo_time: AMO timing (PRE_OPEN/OPEN/OPEN_30/OPEN_60)
            bo_profit_value: BO profit value
            bo_stop_loss_value: BO stop loss value
            correlation_id: User-generated tracking ID
        
        Returns:
            Response dict with orderId and orderStatus, or None if failed
        """
        try:
            logger.info(f"Placing slice order for {security_id}", extra={
                "account_type": self.account_type,
                "quantity": quantity,
                "side": transaction_type
            })
            
            # Build request (same structure as place_order)
            request = {
                'security_id': security_id,
                'exchange_segment': exchange_segment,
                'transaction_type': transaction_type,
                'quantity': quantity,
                'order_type': order_type,
                'product_type': product_type,
                'validity': validity
            }
            
            # Optional fields
            if correlation_id is not None:
                request['correlation_id'] = correlation_id
            if price is not None:
                request['price'] = price
            if trigger_price is not None:
                request['trigger_price'] = trigger_price
            if disclosed_quantity is not None:
                request['disclosed_quantity'] = disclosed_quantity
            if after_market_order:
                request['after_market_order'] = after_market_order
            if amo_time is not None:
                request['amo_time'] = amo_time
            if bo_profit_value is not None:
                request['bo_profit_value'] = bo_profit_value
            if bo_stop_loss_value is not None:
                request['bo_stop_loss_value'] = bo_stop_loss_value
            
            # Call slice order API
            response = self.client.place_slice_order(request)
            
            if response and (response.get('status') == 'success' or 'orderId' in response):
                logger.info(f"Slice order placed successfully", extra={
                    "account_type": self.account_type,
                    "order_id": response.get('orderId')
                })
                return response
            else:
                logger.error(f"Slice order placement failed: {response}", extra={
                    "account_type": self.account_type
                })
                return None
        
        except Exception as e:
            logger.error("Slice order placement error", exc_info=True, extra={
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
    
    def get_order_by_correlation_id(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get order details by correlation ID.
        
        Per DhanHQ v2 Orders API:
        GET /orders/external/{correlation-id}
        
        Args:
            correlation_id: User/partner generated tracking ID
        
        Returns:
            Order details dict, or None if failed
        """
        try:
            logger.debug(f"Getting order by correlation_id: {correlation_id}", extra={
                "account_type": self.account_type,
                "correlation_id": correlation_id
            })
            
            response = self.client.get_order_by_correlation_id(correlation_id)
            
            if response:
                logger.debug(f"Order found for correlation_id: {correlation_id}", extra={
                    "account_type": self.account_type
                })
                return response
            else:
                logger.warning(f"Order not found for correlation_id: {correlation_id}", extra={
                    "account_type": self.account_type
                })
                return None
        
        except Exception as e:
            logger.error("Get order by correlation_id error", exc_info=True, extra={
                "account_type": self.account_type,
                "correlation_id": correlation_id,
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
    
    def get_trade_book(self, order_id: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get Trade Book (filled orders/executions).
        
        API Endpoints:
        - GET /trades - Get all trades for the day (Trade Book)
        - GET /trades/{order-id} - Get trades for specific order (Trades of an Order)
        
        Maps all 18 Trade Book API fields to standardized format.
        API Reference: https://dhanhq.co/docs/v2/orders/ (Trade Book section)
        
        Args:
            order_id: Optional order ID to filter trades for specific order
        
        Returns:
            List of trade dicts with all 18 fields mapped, or None if failed
        
        Example:
            # Get all trades for the day
            all_trades = orders_api.get_trade_book()
            
            # Get trades for specific order
            order_trades = orders_api.get_trade_book(order_id='112111182045')
        """
        try:
            if order_id:
                response = self.client.get_trade_book(order_id)
            else:
                response = self.client.get_trade_book()
            
            if response and isinstance(response, list):
                # Map API response to standardized format with all 18 fields
                mapped_trades = [self._map_trade_response(trade) for trade in response]
                
                logger.debug(f"Retrieved {len(mapped_trades)} trades", extra={
                    "account_type": self.account_type,
                    "count": len(mapped_trades)
                })
                return mapped_trades
            else:
                return []
        
        except Exception as e:
            logger.error("Get trade history error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def _map_trade_response(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map DhanHQ Trade Book API response to standardized format with all 18 fields.
        
        API Fields → Mapped Fields:
        - dhanClientId → account_type (leader/follower)
        - orderId → order_id
        - exchangeOrderId → exchange_order_id
        - exchangeTradeId → exchange_trade_id
        - transactionType → transaction_type
        - exchangeSegment → exchange_segment
        - productType → product_type
        - orderType → order_type
        - tradingSymbol → trading_symbol
        - securityId → security_id
        - tradedQuantity → quantity
        - tradedPrice → price
        - createTime → created_at (converted to epoch)
        - updateTime → updated_at (converted to epoch)
        - exchangeTime → exchange_time (converted to epoch)
        - drvExpiryDate → drv_expiry_date
        - drvOptionType → drv_option_type
        - drvStrikePrice → drv_strike_price
        
        Args:
            trade: Raw API response dict
            
        Returns:
            Mapped trade dict with all 18 fields
        """
        import time
        from datetime import datetime
        
        def parse_timestamp(time_str: Optional[str]) -> Optional[int]:
            """Convert timestamp string to epoch."""
            if not time_str:
                return None
            try:
                # DhanHQ format: "2021-11-25 17:35:12"
                dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                return int(dt.timestamp())
            except (ValueError, TypeError):
                return None
        
        # Use exchangeTradeId as primary ID, fallback to orderId
        trade_id = trade.get('exchangeTradeId') or trade.get('orderId', '')
        
        return {
            # Primary identification
            'id': trade_id,
            'order_id': trade.get('orderId', ''),
            'account_type': self.account_type,
            
            # Exchange identifiers
            'exchange_order_id': trade.get('exchangeOrderId'),
            'exchange_trade_id': trade.get('exchangeTradeId'),
            
            # Instrument details
            'security_id': trade.get('securityId', ''),
            'exchange_segment': trade.get('exchangeSegment', ''),
            'trading_symbol': trade.get('tradingSymbol'),
            
            # Transaction details
            'transaction_type': trade.get('transactionType', ''),
            'product_type': trade.get('productType', ''),
            'order_type': trade.get('orderType', ''),
            
            # Quantity and pricing
            'quantity': trade.get('tradedQuantity', 0),
            'price': trade.get('tradedPrice', 0.0),
            
            # Timestamps
            'trade_ts': parse_timestamp(trade.get('exchangeTime')) or int(time.time()),
            'created_at': parse_timestamp(trade.get('createTime')) or 0,
            'updated_at': parse_timestamp(trade.get('updateTime')),
            'exchange_time': parse_timestamp(trade.get('exchangeTime')),
            
            # F&O derivatives info
            'drv_expiry_date': trade.get('drvExpiryDate'),
            'drv_option_type': trade.get('drvOptionType'),
            'drv_strike_price': trade.get('drvStrikePrice'),
            
            # Raw data for debugging
            'raw_data': str(trade)
        }

