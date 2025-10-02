"""
Order Manager Module

Handle order placement, validation, tracking, and replication logic.
"""

import logging
import time
import json
import threading
from collections import deque
from typing import Optional, Dict, Any
from dhanhq import dhanhq

from ..config import get_config
from ..database import DatabaseManager, get_db, Order, OrderEvent, CopyMapping
from ..position_sizing import PositionSizer, get_position_sizer

logger = logging.getLogger(__name__)


class OrderManager:
    """
    Manage order operations for both leader and follower accounts.
    
    Responsibilities:
    - Validate order parameters
    - Place orders via DhanHQ API
    - Track order lifecycle
    - Handle replication logic
    """
    
    def __init__(
        self,
        follower_client: dhanhq,
        db: DatabaseManager,
        position_sizer: PositionSizer
    ):
        """
        Initialize order manager.
        
        Args:
            follower_client: DhanHQ client for follower account
            db: Database manager
            position_sizer: Position sizing engine
        """
        self.follower_client = follower_client
        self.db = db
        self.position_sizer = position_sizer
        
        # ✅ ADDED: Rate limiting
        self.request_timestamps = deque()  # Track request times
        self.request_lock = threading.Lock()
        self.max_requests_per_second = 10  # DhanHQ limit
        
        logger.info("Order manager initialized with rate limiting")
    
    def _is_market_open(self, exchange_segment: str) -> bool:
        """
        ✅ ADDED: Check if market is open for the given exchange.
        
        Args:
            exchange_segment: Exchange segment (NSE_EQ, NSE_FNO, BSE_EQ, etc.)
        
        Returns:
            True if market is open, False otherwise
        
        Note: This is a basic implementation. For production, fetch exact timings
        from DhanHQ API or maintain a holiday calendar.
        """
        try:
            from datetime import datetime
            import pytz
            
            # Indian timezone
            ist = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist)
            
            # Check if weekend
            if now.weekday() >= 5:  # Saturday=5, Sunday=6
                logger.debug("Market closed: Weekend")
                return False
            
            # Market hours (simplified)
            # NSE/BSE Equity: 9:15 AM - 3:30 PM
            # NSE F&O: 9:15 AM - 3:30 PM
            # MCX: 9:00 AM - 11:30 PM (with breaks)
            # CDS: 9:00 AM - 5:00 PM
            
            current_time = now.time()
            
            if 'NSE' in exchange_segment or 'BSE' in exchange_segment:
                from datetime import time as dt_time
                market_open = dt_time(9, 15)
                market_close = dt_time(15, 30)
                
                if current_time < market_open or current_time > market_close:
                    logger.debug(f"Market closed: Outside hours for {exchange_segment}")
                    return False
            
            # TODO: Add holiday calendar check
            # For now, assume market is open if not weekend and within hours
            return True
            
        except Exception as e:
            logger.warning(f"Error checking market hours: {e}, assuming market is open")
            return True  # Fail open - let API reject if needed
    
    def _wait_for_rate_limit(self) -> None:
        """
        ✅ ADDED: Wait if necessary to respect rate limits.
        """
        with self.request_lock:
            now = time.time()
            
            # Remove timestamps older than 1 second
            while self.request_timestamps and now - self.request_timestamps[0] > 1.0:
                self.request_timestamps.popleft()
            
            # Check if we're at the limit
            if len(self.request_timestamps) >= self.max_requests_per_second:
                # Calculate wait time
                oldest = self.request_timestamps[0]
                wait_time = 1.0 - (now - oldest) + 0.01  # Add small buffer
                
                if wait_time > 0:
                    logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                    time.sleep(wait_time)
                    now = time.time()
            
            # Add current request timestamp
            self.request_timestamps.append(now)
    
    def replicate_order(self, leader_order_data: Dict[str, Any]) -> Optional[str]:
        """
        Replicate a leader order to follower account.
        
        Args:
            leader_order_data: Leader order details from WebSocket event
        
        Returns:
            Follower order ID if successful, None otherwise
        """
        try:
            # Parse leader order details
            leader_order_id = leader_order_data.get('orderId') or leader_order_data.get('dhanOrderId')
            security_id = leader_order_data.get('securityId')
            exchange_segment = leader_order_data.get('exchangeSegment')
            transaction_type = leader_order_data.get('transactionType')
            quantity = leader_order_data.get('quantity')
            order_type = leader_order_data.get('orderType')
            product_type = leader_order_data.get('productType')
            price = leader_order_data.get('price', 0)
            trigger_price = leader_order_data.get('triggerPrice')
            validity = leader_order_data.get('validity', 'DAY')
            disclosed_qty = leader_order_data.get('disclosedQuantity')
            # ✅ TASK-006: Cover Order (CO) parameters
            co_stop_loss_value = leader_order_data.get('coStopLossValue')
            co_trigger_price = leader_order_data.get('coTriggerPrice')
            # ✅ TASK-006: Bracket Order (BO) parameters
            bo_profit_value = leader_order_data.get('boProfitValue')
            bo_stop_loss_value = leader_order_data.get('boStopLossValue')
            bo_order_type = leader_order_data.get('boOrderType')
            
            if not all([leader_order_id, security_id, exchange_segment, transaction_type, quantity]):
                logger.error("Missing required order fields", extra={"order": leader_order_data})
                return None
            
            logger.info(f"Replicating leader order: {leader_order_id}", extra={
                "security_id": security_id,
                "side": transaction_type,
                "quantity": quantity
            })
            
            # Save leader order to database
            leader_order = self._create_order_from_data(leader_order_data, 'leader')
            self.db.save_order(leader_order)
            
            # Check if already replicated
            existing_mapping = self.db.get_copy_mapping_by_leader(leader_order_id)
            if existing_mapping and existing_mapping.status == 'placed':
                logger.info(f"Order {leader_order_id} already replicated")
                return existing_mapping.follower_order_id
            
            # Check if instrument is an option
            instrument = self.db.get_instrument(security_id)
            if instrument and not instrument.is_option():
                logger.info(f"Order {leader_order_id} is not an option, skipping (options-only mode)")
                return None
            
            # ✅ ADDED: Check market hours (optional - can be disabled for testing)
            if not self._is_market_open(exchange_segment):
                logger.warning(f"Market closed for {exchange_segment}, order may be rejected")
                # Still proceed - let DhanHQ API handle rejection with proper error
            
            # Calculate follower quantity
            premium = price if price > 0 else None
            follower_quantity = self.position_sizer.calculate_quantity(
                leader_quantity=quantity,
                security_id=security_id,
                premium=premium
            )
            
            # ✅ ADDED: Calculate proportional disclosed quantity
            follower_disclosed_qty = None
            if disclosed_qty and follower_quantity > 0:
                disclosed_ratio = disclosed_qty / quantity
                follower_disclosed_qty = int(follower_quantity * disclosed_ratio)
                # Ensure it doesn't exceed total quantity
                follower_disclosed_qty = min(follower_disclosed_qty, follower_quantity)
                # Ensure it's at least 1 lot if original had disclosed qty
                if follower_disclosed_qty == 0 and disclosed_qty > 0:
                    instrument = self.db.get_instrument(security_id)
                    if instrument:
                        follower_disclosed_qty = instrument.lot_size
            
            if follower_quantity == 0:
                logger.warning(f"Calculated quantity is 0 for order {leader_order_id}, skipping")
                # Create failed mapping
                self._create_copy_mapping(
                    leader_order_id=leader_order_id,
                    leader_quantity=quantity,
                    follower_quantity=0,
                    status='failed',
                    error_message="Calculated quantity is 0"
                )
                return None
            
            # Validate sufficient margin
            is_valid, error_msg = self.position_sizer.validate_sufficient_margin(
                quantity=follower_quantity,
                security_id=security_id,
                premium=premium
            )
            
            if not is_valid:
                logger.warning(f"Insufficient margin for order {leader_order_id}: {error_msg}")
                self._create_copy_mapping(
                    leader_order_id=leader_order_id,
                    leader_quantity=quantity,
                    follower_quantity=follower_quantity,
                    status='failed',
                    error_message=error_msg
                )
                return None
            
            # Place follower order
            follower_order_id = self._place_follower_order(
                security_id=security_id,
                exchange_segment=exchange_segment,
                transaction_type=transaction_type,
                quantity=follower_quantity,
                order_type=order_type,
                product_type=product_type,
                price=price,
                trigger_price=trigger_price,
                validity=validity,
                disclosed_qty=follower_disclosed_qty,
                # ✅ TASK-006: CO/BO parameters
                co_stop_loss_value=co_stop_loss_value,
                co_trigger_price=co_trigger_price,
                bo_profit_value=bo_profit_value,
                bo_stop_loss_value=bo_stop_loss_value,
                bo_order_type=bo_order_type
            )
            
            if follower_order_id:
                # Update copy mapping
                self.db.update_copy_mapping_status(
                    leader_order_id=leader_order_id,
                    status='placed',
                    follower_order_id=follower_order_id
                )
                
                logger.info(f"Successfully replicated order", extra={
                    "leader_order_id": leader_order_id,
                    "follower_order_id": follower_order_id,
                    "leader_qty": quantity,
                    "follower_qty": follower_quantity
                })
                
                return follower_order_id
            else:
                self.db.update_copy_mapping_status(
                    leader_order_id=leader_order_id,
                    status='failed',
                    error_message="Failed to place follower order"
                )
                return None
            
        except Exception as e:
            logger.error(f"Error replicating order", exc_info=True, extra={
                "error": str(e),
                "order": leader_order_data
            })
            return None
    
    def _place_follower_order(
        self,
        security_id: str,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        order_type: str,
        product_type: str,
        price: float = 0,
        trigger_price: Optional[float] = None,
        validity: str = 'DAY',
        disclosed_qty: Optional[int] = None,
        # ✅ TASK-006: Cover Order parameters
        co_stop_loss_value: Optional[float] = None,
        co_trigger_price: Optional[float] = None,
        # ✅ TASK-006: Bracket Order parameters
        bo_profit_value: Optional[float] = None,
        bo_stop_loss_value: Optional[float] = None,
        bo_order_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Place order in follower account.
        
        Args:
            security_id: Security ID
            exchange_segment: Exchange segment
            transaction_type: BUY or SELL
            quantity: Order quantity
            order_type: Order type (MARKET/LIMIT/etc)
            product_type: Product type (MIS/CNC/NRML)
            price: Limit price
            trigger_price: Trigger price for SL orders
            validity: Order validity (DAY/IOC/GTT)
            disclosed_qty: Disclosed quantity for iceberg orders
        
        Returns:
            Order ID if successful, None otherwise
        """
        try:
            # ✅ ADDED: Wait for rate limit
            self._wait_for_rate_limit()
            
            start_time = time.time()
            
            logger.info("Placing follower order", extra={
                "security_id": security_id,
                "exchange": exchange_segment,
                "side": transaction_type,
                "quantity": quantity,
                "order_type": order_type,
                "product": product_type,
                "price": price,
                "trigger_price": trigger_price,  # ✅ ADDED to log
                "validity": validity,  # ✅ ADDED to log
                "disclosed_qty": disclosed_qty  # ✅ ADDED to log
            })
            
            # ✅ MODIFIED: Build API params with all parameters
            api_params = {
                'security_id': security_id,
                'exchange_segment': exchange_segment,
                'transaction_type': transaction_type,
                'quantity': quantity,
                'order_type': order_type,
                'product_type': product_type,
                'price': price if price > 0 else 0,
                'validity': validity  # ✅ ADDED
            }
            
            # ✅ ADDED: Include trigger price for SL orders
            if trigger_price and order_type in ('SL', 'SL-M'):
                api_params['trigger_price'] = trigger_price
            
            # ✅ ADDED: Include disclosed quantity if specified
            if disclosed_qty:
                api_params['disclosed_quantity'] = disclosed_qty
            
            # ✅ TASK-006: Include Cover Order parameters
            if co_stop_loss_value is not None:
                api_params['coStopLossValue'] = co_stop_loss_value
                logger.info(f"CO order detected: SL={co_stop_loss_value}")
            
            if co_trigger_price is not None:
                api_params['coTriggerPrice'] = co_trigger_price
            
            # ✅ TASK-006: Include Bracket Order parameters
            if bo_profit_value is not None:
                api_params['boProfitValue'] = bo_profit_value
                logger.info(f"BO order detected: Profit={bo_profit_value}, SL={bo_stop_loss_value}")
            
            if bo_stop_loss_value is not None:
                api_params['boStopLossValue'] = bo_stop_loss_value
            
            if bo_order_type is not None:
                api_params['boOrderType'] = bo_order_type
            
            # Call DhanHQ API
            response = self.follower_client.place_order(**api_params)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log to audit
            self.db.log_audit(
                action='place_order',
                account_type='follower',
                request_data={
                    'security_id': security_id,
                    'exchange_segment': exchange_segment,
                    'transaction_type': transaction_type,
                    'quantity': quantity,
                    'order_type': order_type,
                    'product_type': product_type,
                    'price': price
                },
                response_data=response,
                status_code=200 if response else None,
                duration_ms=duration_ms
            )
            
            # Parse response
            if response and 'orderId' in response:
                order_id = response['orderId']
                
                # Save follower order
                follower_order = Order(
                    id=str(order_id),
                    account_type='follower',
                    status='PENDING',
                    side=transaction_type,
                    product=product_type,
                    order_type=order_type,
                    validity=validity,  # ✅ FIXED: Use parameter instead of hardcoded 'DAY'
                    security_id=security_id,
                    exchange_segment=exchange_segment,
                    quantity=quantity,
                    price=price if price > 0 else None,
                    trigger_price=trigger_price,  # ✅ FIXED: Use parameter instead of None
                    disclosed_qty=disclosed_qty,  # ✅ FIXED: Use parameter instead of None
                    created_at=int(time.time()),
                    updated_at=int(time.time()),
                    raw_response=json.dumps(response)
                )
                self.db.save_order(follower_order)
                
                # Log order event
                event = OrderEvent(
                    order_id=str(order_id),
                    event_type='PLACED',
                    event_data=json.dumps(response),
                    event_ts=int(time.time()),
                    sequence=1
                )
                self.db.save_order_event(event)
                
                logger.info(f"Follower order placed successfully: {order_id}")
                
                return str(order_id)
            else:
                logger.error(f"Failed to place follower order: {response}")
                return None
            
        except Exception as e:
            logger.error("Error placing follower order", exc_info=True, extra={
                "error": str(e),
                "security_id": security_id
            })
            
            # Log failed audit
            self.db.log_audit(
                action='place_order',
                account_type='follower',
                request_data={
                    'security_id': security_id,
                    'quantity': quantity
                },
                error_message=str(e)
            )
            
            return None
    
    def _create_order_from_data(self, order_data: Dict[str, Any], account_type: str) -> Order:
        """
        Create Order object from API data.
        
        Args:
            order_data: Order data from API
            account_type: 'leader' or 'follower'
        
        Returns:
            Order object
        """
        order_id = order_data.get('orderId') or order_data.get('dhanOrderId')
        
        return Order(
            id=str(order_id),
            account_type=account_type,
            status=order_data.get('orderStatus', 'PENDING'),
            side=order_data.get('transactionType', ''),
            product=order_data.get('productType', ''),
            order_type=order_data.get('orderType', ''),
            validity=order_data.get('validity', 'DAY'),
            security_id=order_data.get('securityId', ''),
            exchange_segment=order_data.get('exchangeSegment', ''),
            quantity=order_data.get('quantity', 0),
            price=order_data.get('price'),
            trigger_price=order_data.get('triggerPrice'),
            disclosed_qty=order_data.get('disclosedQuantity'),
            created_at=int(time.time()),
            updated_at=int(time.time()),
            raw_response=json.dumps(order_data)
        )
    
    def _create_copy_mapping(
        self,
        leader_order_id: str,
        leader_quantity: int,
        follower_quantity: int,
        status: str,
        follower_order_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Create copy mapping record.
        
        Args:
            leader_order_id: Leader order ID
            leader_quantity: Leader quantity
            follower_quantity: Follower quantity
            status: Mapping status
            follower_order_id: Follower order ID (optional)
            error_message: Error message (optional)
        """
        _, _, system_config = get_config()
        
        capital_ratio = self.position_sizer.get_capital_ratio()
        
        mapping = CopyMapping(
            leader_order_id=leader_order_id,
            follower_order_id=follower_order_id,
            leader_quantity=leader_quantity,
            follower_quantity=follower_quantity,
            sizing_strategy=system_config.sizing_strategy.value,
            capital_ratio=capital_ratio,
            status=status,
            error_message=error_message,
            created_at=int(time.time()),
            updated_at=int(time.time())
        )
        
        self.db.save_copy_mapping(mapping)
    
    def cancel_order(self, leader_order_data: Dict[str, Any]) -> bool:
        """
        ✅ ADDED: Cancel follower order when leader cancels (includes BO leg cancellation).
        
        Args:
            leader_order_data: Leader order cancellation data
        
        Returns:
            True if cancellation successful, False otherwise
        """
        try:
            leader_order_id = leader_order_data.get('orderId') or leader_order_data.get('dhanOrderId')
            
            logger.info(f"Processing cancellation for leader order: {leader_order_id}")
            
            # Update leader order status
            self.db.update_order_status(leader_order_id, 'CANCELLED')
            
            # Find corresponding follower order
            mapping = self.db.get_copy_mapping_by_leader(leader_order_id)
            
            if not mapping:
                logger.warning(f"No mapping found for leader order {leader_order_id}")
                return False
            
            if not mapping.follower_order_id:
                logger.info(f"No follower order placed yet for {leader_order_id}")
                return False
            
            # Get follower order status
            follower_order = self.db.get_order(mapping.follower_order_id)
            
            if not follower_order:
                logger.error(f"Follower order {mapping.follower_order_id} not found in DB")
                return False
            
            # Check if already in terminal state
            if follower_order.status in ('EXECUTED', 'TRADED', 'CANCELLED', 'REJECTED'):
                logger.info(f"Follower order {mapping.follower_order_id} already in terminal state: {follower_order.status}")
                return False
            
            # ✅ TASK-006: If this is a BO, cancel all pending legs
            if getattr(follower_order, 'bo_profit_value', None) is not None:
                logger.info(f"Detected BO order, checking for legs to cancel")
                self._cancel_bracket_order_legs(mapping.follower_order_id)
            
            # Cancel follower order via API
            logger.info(f"Cancelling follower order: {mapping.follower_order_id}")
            
            # ✅ ADDED: Wait for rate limit
            self._wait_for_rate_limit()
            
            response = self.follower_client.cancel_order(mapping.follower_order_id)
            
            # Log to audit
            self.db.log_audit(
                action='cancel_order',
                account_type='follower',
                request_data={'order_id': mapping.follower_order_id},
                response_data=response
            )
            
            if response and (response.get('status') == 'success' or 'orderId' in response):
                # Update follower order status
                self.db.update_order_status(mapping.follower_order_id, 'CANCELLED')
                
                # Update copy mapping
                self.db.update_copy_mapping_status(
                    leader_order_id=leader_order_id,
                    status='cancelled',
                    error_message='Leader order cancelled'
                )
                
                logger.info(f"Successfully cancelled follower order {mapping.follower_order_id}")
                return True
            else:
                logger.error(f"Failed to cancel follower order: {response}")
                return False
        
        except Exception as e:
            logger.error("Error cancelling order", exc_info=True, extra={
                "error": str(e),
                "order_data": leader_order_data
            })
            return False
    
    def _cancel_bracket_order_legs(self, parent_order_id: str) -> None:
        """
        ✅ TASK-006: Cancel all pending legs of a bracket order.
        
        Args:
            parent_order_id: The parent BO order ID
        """
        try:
            legs = self.db.get_bracket_order_legs(parent_order_id)
            
            for leg in legs:
                if leg['status'] not in ('EXECUTED', 'TRADED', 'CANCELLED', 'REJECTED'):
                    logger.info(f"Cancelling BO leg: {leg['order_id']} (type: {leg['leg_type']})")
                    
                    try:
                        self._wait_for_rate_limit()
                        self.follower_client.cancel_order(leg['order_id'])
                        self.db.update_bracket_order_leg_status(leg['id'], 'CANCELLED')
                    except Exception as e:
                        logger.error(f"Failed to cancel BO leg {leg['order_id']}: {e}")
        
        except Exception as e:
            logger.error(f"Error cancelling BO legs: {e}", exc_info=True)
    
    def modify_order(self, leader_order_data: Dict[str, Any]) -> bool:
        """
        ✅ ADDED: Modify follower order when leader modifies.
        
        Args:
            leader_order_data: Leader order modification data
        
        Returns:
            True if modification successful, False otherwise
        """
        try:
            leader_order_id = leader_order_data.get('orderId') or leader_order_data.get('dhanOrderId')
            
            logger.info(f"Processing modification for leader order: {leader_order_id}")
            
            # Find corresponding follower order
            mapping = self.db.get_copy_mapping_by_leader(leader_order_id)
            
            if not mapping or not mapping.follower_order_id:
                logger.warning(f"No follower order to modify for {leader_order_id}")
                return False
            
            # Get current follower order
            follower_order = self.db.get_order(mapping.follower_order_id)
            
            if not follower_order:
                logger.error(f"Follower order {mapping.follower_order_id} not found")
                return False
            
            # Check if modifiable
            if follower_order.status not in ('PENDING', 'OPEN'):
                logger.info(f"Follower order {mapping.follower_order_id} not in modifiable state: {follower_order.status}")
                return False
            
            # Extract modification details
            new_quantity = leader_order_data.get('quantity')
            new_price = leader_order_data.get('price')
            new_trigger_price = leader_order_data.get('triggerPrice')
            new_order_type = leader_order_data.get('orderType')
            
            # ✅ TASK-006: Extract CO/BO modification parameters
            new_co_stop_loss = leader_order_data.get('coStopLossValue')
            new_co_trigger = leader_order_data.get('coTriggerPrice')
            new_bo_profit = leader_order_data.get('boProfitValue')
            new_bo_stop_loss = leader_order_data.get('boStopLossValue')
            
            # Calculate adjusted follower quantity
            if new_quantity:
                follower_quantity = self.position_sizer.calculate_quantity(
                    leader_quantity=new_quantity,
                    security_id=follower_order.security_id,
                    premium=new_price
                )
            else:
                follower_quantity = follower_order.quantity
            
            # Modify via API (DhanHQ v2 uses TOTAL quantity, not delta)
            modify_params = {
                'order_id': mapping.follower_order_id,
                'quantity': follower_quantity,
                'order_type': new_order_type or follower_order.order_type,
                'validity': follower_order.validity,
                'price': new_price if new_price else follower_order.price
            }
            
            if new_trigger_price:
                modify_params['trigger_price'] = new_trigger_price
            
            # ✅ TASK-006: Include CO parameters if modified
            if new_co_stop_loss is not None:
                modify_params['coStopLossValue'] = new_co_stop_loss
                logger.info(f"Modifying CO stop-loss to {new_co_stop_loss}")
            
            if new_co_trigger is not None:
                modify_params['coTriggerPrice'] = new_co_trigger
            
            # ✅ TASK-006: Include BO parameters if modified
            if new_bo_profit is not None:
                modify_params['boProfitValue'] = new_bo_profit
                logger.info(f"Modifying BO profit target to {new_bo_profit}")
            
            if new_bo_stop_loss is not None:
                modify_params['boStopLossValue'] = new_bo_stop_loss
            
            logger.info(f"Modifying follower order with params: {modify_params}")
            
            # ✅ ADDED: Wait for rate limit
            self._wait_for_rate_limit()
            
            response = self.follower_client.modify_order(**modify_params)
            
            # Log to audit
            self.db.log_audit(
                action='modify_order',
                account_type='follower',
                request_data=modify_params,
                response_data=response
            )
            
            if response and (response.get('status') == 'success' or 'orderId' in response):
                # Update DB
                follower_order.quantity = follower_quantity
                if new_price:
                    follower_order.price = new_price
                if new_trigger_price:
                    follower_order.trigger_price = new_trigger_price
                follower_order.updated_at = int(time.time())
                
                self.db.save_order(follower_order)
                
                logger.info(f"Successfully modified follower order {mapping.follower_order_id}")
                return True
            else:
                logger.error(f"Failed to modify follower order: {response}")
                return False
        
        except Exception as e:
            logger.error("Error modifying order", exc_info=True, extra={
                "error": str(e),
                "order_data": leader_order_data
            })
            return False
    
    def handle_execution(self, execution_data: Dict[str, Any]) -> None:
        """
        ✅ TASK-006: Handle order execution event with BO OCO logic.
        
        Args:
            execution_data: Execution event data
        """
        try:
            order_id = execution_data.get('orderId') or execution_data.get('dhanOrderId')
            fill_qty = execution_data.get('filledQty', 0)
            fill_price = execution_data.get('averagePrice', 0)
            order_status = execution_data.get('orderStatus', 'EXECUTED')
            
            logger.info(f"Processing execution for order: {order_id}", extra={
                "order_id": order_id,
                "fill_qty": fill_qty,
                "fill_price": fill_price,
                "status": order_status
            })
            
            # Update order status
            self.db.update_order_status(order_id, order_status)
            
            # Check if this is a leader or follower order
            order = self.db.get_order(order_id)
            if not order:
                logger.warning(f"Order {order_id} not found in database")
                return
            
            # ✅ TASK-006: Implement OCO logic for Bracket Orders
            if getattr(order, 'bo_profit_value', None) is not None:
                logger.info(f"Detected BO execution, triggering OCO logic")
                self._handle_bracket_order_oco(order_id, execution_data)
            
            # Log execution event
            event = OrderEvent(
                order_id=order_id,
                event_type=order_status,
                event_data=json.dumps(execution_data),
                event_ts=int(time.time())
            )
            self.db.save_order_event(event)
            
            # Log execution for analytics
            self.db.log_audit(
                action='order_executed',
                account_type=order.account_type,
                request_data={
                    'order_id': order_id,
                    'fill_qty': fill_qty,
                    'fill_price': fill_price
                }
            )
            
            # If leader order, check follower order status
            if order.account_type == 'leader':
                mapping = self.db.get_copy_mapping_by_leader(order_id)
                if mapping and mapping.follower_order_id:
                    follower_order = self.db.get_order(mapping.follower_order_id)
                    if follower_order:
                        logger.info(f"Leader order {order_id} executed. Follower order {mapping.follower_order_id} status: {follower_order.status}")
                        
                        # Optional: Alert on large execution time difference
                        time_diff = abs(order.updated_at - follower_order.updated_at)
                        if time_diff > 60:  # More than 1 minute
                            logger.warning(f"Large execution time difference: {time_diff}s between leader and follower orders")
        
        except Exception as e:
            logger.error("Error handling execution", exc_info=True, extra={
                "error": str(e),
                "execution_data": execution_data
            })
    
    def _handle_bracket_order_oco(self, parent_order_id: str, execution_data: Dict[str, Any]) -> None:
        """
        ✅ TASK-006: Implement One-Cancels-Other (OCO) logic for Bracket Orders.
        
        When one leg (target or stop-loss) executes, automatically cancel the other.
        
        Args:
            parent_order_id: The parent BO order ID
            execution_data: Data about which leg was executed
        """
        try:
            legs = self.db.get_bracket_order_legs(parent_order_id)
            
            if not legs:
                logger.debug(f"No BO legs found for order {parent_order_id}")
                return
            
            # Determine which leg executed (try to infer from data)
            executed_leg_type = execution_data.get('legType')  # 'target' or 'stop_loss'
            
            if not executed_leg_type:
                # Try to infer from price movement or other indicators
                logger.warning(f"No leg type in execution data for BO {parent_order_id}, skipping OCO")
                return
            
            logger.info(f"BO {parent_order_id}: {executed_leg_type} leg executed, cancelling other leg")
            
            # Cancel the opposite leg
            opposite_leg_type = 'stop_loss' if executed_leg_type == 'target' else 'target'
            
            for leg in legs:
                if leg['leg_type'] == opposite_leg_type and leg['status'] not in ('EXECUTED', 'TRADED', 'CANCELLED', 'REJECTED'):
                    logger.info(f"OCO: Cancelling {opposite_leg_type} leg {leg['order_id']}")
                    
                    try:
                        self._wait_for_rate_limit()
                        self.follower_client.cancel_order(leg['order_id'])
                        self.db.update_bracket_order_leg_status(leg['id'], 'CANCELLED')
                        
                        logger.info(f"OCO: Successfully cancelled {opposite_leg_type} leg")
                    except Exception as e:
                        logger.error(f"OCO: Failed to cancel {opposite_leg_type} leg: {e}")
        
        except Exception as e:
            logger.error(f"Error in BO OCO logic: {e}", exc_info=True)
    
    def update_order_status(self, order_id: str, status: str, account_type: str) -> None:
        """
        Update order status.
        
        Args:
            order_id: Order ID
            status: New status
            account_type: 'leader' or 'follower'
        """
        self.db.update_order_status(order_id, status)
        
        # Log event
        event = OrderEvent(
            order_id=order_id,
            event_type=status,
            event_data=json.dumps({'account_type': account_type}),
            event_ts=int(time.time())
        )
        self.db.save_order_event(event)
        
        logger.debug(f"Updated order {order_id} status to {status}")


# Global order manager instance
_order_manager: Optional[OrderManager] = None


def initialize_order_manager(follower_client: dhanhq) -> OrderManager:
    """
    Initialize order manager (singleton).
    
    Args:
        follower_client: Follower DhanHQ client
    
    Returns:
        OrderManager instance
    """
    global _order_manager
    
    db = get_db()
    position_sizer = get_position_sizer()
    
    _order_manager = OrderManager(
        follower_client=follower_client,
        db=db,
        position_sizer=position_sizer
    )
    
    return _order_manager


def get_order_manager() -> OrderManager:
    """
    Get order manager instance.
    
    Returns:
        OrderManager instance
    
    Raises:
        ValueError: If not initialized
    """
    if _order_manager is None:
        raise ValueError("Order manager not initialized")
    return _order_manager


