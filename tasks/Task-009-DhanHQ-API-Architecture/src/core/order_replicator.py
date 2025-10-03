"""
Order Replication Manager

Handles replication of leader orders to follower account using new DhanHQ API modules.
Integrates position sizing, margin validation, and order placement.
"""

import logging
import time
from typing import Dict, Any, Optional

from .config import get_config
from .database import DatabaseManager
from .position_sizer import PositionSizer
from .models import Order, CopyMapping

logger = logging.getLogger(__name__)


class OrderReplicator:
    """
    Replicate leader orders to follower account.
    
    Uses new DhanHQ API modules:
    - OrdersAPI for basic orders
    - SuperOrderAPI for CO/BO orders
    - FundsAPI for margin checks (via PositionSizer)
    """
    
    def __init__(
        self,
        orders_api,  # OrdersAPI instance for follower
        super_orders_api,  # SuperOrderAPI instance for follower
        position_sizer: PositionSizer,
        db: DatabaseManager
    ):
        """
        Initialize order replicator.
        
        Args:
            orders_api: OrdersAPI instance for follower
            super_orders_api: SuperOrderAPI instance for follower
            position_sizer: Position sizer for quantity calculation
            db: Database manager
        """
        self.orders_api = orders_api
        self.super_orders_api = super_orders_api
        self.position_sizer = position_sizer
        self.db = db
        
        _, _, self.system_config = get_config()
        
        logger.info("Order replicator initialized")
    
    def replicate_order(self, leader_order_data: Dict[str, Any]) -> Optional[str]:
        """
        Replicate a leader order to follower account.
        
        Args:
            leader_order_data: Leader order details from WebSocket or API
        
        Returns:
            Follower order ID if successful, None otherwise
        """
        try:
            # Extract order details
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
            
            # Validate required fields
            if not all([leader_order_id, security_id, exchange_segment, transaction_type, quantity]):
                logger.error("Missing required order fields", extra={"order": leader_order_data})
                return None
            
            logger.info(f"Replicating order: {leader_order_id}", extra={
                "security_id": security_id,
                "side": transaction_type,
                "quantity": quantity,
                "product": product_type
            })
            
            # Check if already replicated
            existing_mapping = self.db.get_copy_mapping_by_leader(leader_order_id)
            if existing_mapping and existing_mapping.status == 'placed':
                logger.info(f"Order {leader_order_id} already replicated")
                return existing_mapping.follower_order_id
            
            # Calculate follower quantity
            follower_quantity = self.position_sizer.calculate_quantity(
                leader_quantity=quantity,
                security_id=security_id,
                premium=price if price > 0 else None
            )
            
            if follower_quantity == 0:
                logger.warning(f"Calculated quantity is 0 for order {leader_order_id}, skipping")
                self._save_failed_mapping(leader_order_id, quantity, 0, "Calculated quantity is 0")
                return None
            
            # Validate sufficient margin
            is_valid, error_msg = self.position_sizer.validate_sufficient_margin(
                quantity=follower_quantity,
                security_id=security_id,
                premium=price if price > 0 else None
            )
            
            if not is_valid:
                logger.warning(f"Insufficient margin: {error_msg}")
                self._save_failed_mapping(leader_order_id, quantity, follower_quantity, error_msg)
                return None
            
            # Calculate proportional disclosed quantity
            follower_disclosed_qty = None
            if disclosed_qty and follower_quantity > 0:
                disclosed_ratio = disclosed_qty / quantity
                follower_disclosed_qty = int(follower_quantity * disclosed_ratio)
                follower_disclosed_qty = min(follower_disclosed_qty, follower_quantity)
            
            # Place order based on product type
            if product_type == 'CO':
                # Cover Order
                follower_order_id = self._place_cover_order(
                    leader_order_data, follower_quantity, follower_disclosed_qty
                )
            elif product_type == 'BO':
                # Bracket Order
                follower_order_id = self._place_bracket_order(
                    leader_order_data, follower_quantity, follower_disclosed_qty
                )
            else:
                # Basic order
                follower_order_id = self._place_basic_order(
                    security_id=security_id,
                    exchange_segment=exchange_segment,
                    transaction_type=transaction_type,
                    quantity=follower_quantity,
                    order_type=order_type,
                    product_type=product_type,
                    price=price,
                    trigger_price=trigger_price,
                    validity=validity,
                    disclosed_qty=follower_disclosed_qty
                )
            
            if follower_order_id:
                # Save copy mapping
                self._save_copy_mapping(
                    leader_order_id=leader_order_id,
                    follower_order_id=follower_order_id,
                    leader_quantity=quantity,
                    follower_quantity=follower_quantity,
                    status='placed'
                )
                
                logger.info(f"✅ Order replicated successfully", extra={
                    "leader_order_id": leader_order_id,
                    "follower_order_id": follower_order_id,
                    "leader_qty": quantity,
                    "follower_qty": follower_quantity
                })
                
                return follower_order_id
            else:
                self._save_failed_mapping(
                    leader_order_id, quantity, follower_quantity,
                    "Failed to place follower order"
                )
                return None
            
        except Exception as e:
            logger.error("Error replicating order", exc_info=True, extra={
                "error": str(e),
                "order": leader_order_data
            })
            return None
    
    def _place_basic_order(
        self,
        security_id: str,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        order_type: str,
        product_type: str,
        price: float,
        trigger_price: Optional[float],
        validity: str,
        disclosed_qty: Optional[int]
    ) -> Optional[str]:
        """Place basic order using OrdersAPI."""
        try:
            response = self.orders_api.place_order(
                security_id=security_id,
                exchange_segment=exchange_segment,
                transaction_type=transaction_type,
                quantity=quantity,
                order_type=order_type,
                product_type=product_type,
                price=price,
                trigger_price=trigger_price,
                disclosed_quantity=disclosed_qty,
                validity=validity
            )
            
            if response and 'orderId' in response:
                return str(response['orderId'])
            return None
            
        except Exception as e:
            logger.error(f"Error placing basic order: {e}")
            return None
    
    def _place_cover_order(
        self,
        leader_order_data: Dict[str, Any],
        follower_quantity: int,
        follower_disclosed_qty: Optional[int]
    ) -> Optional[str]:
        """Place cover order using SuperOrderAPI."""
        try:
            security_id = leader_order_data['securityId']
            exchange_segment = leader_order_data['exchangeSegment']
            transaction_type = leader_order_data['transactionType']
            order_type = leader_order_data['orderType']
            price = leader_order_data.get('price', 0)
            trigger_price = leader_order_data.get('triggerPrice')
            stop_loss_value = leader_order_data.get('stopLossValue') or leader_order_data.get('coStopLossValue')
            
            if not stop_loss_value:
                logger.error("Cover Order missing stop_loss_value")
                return None
            
            response = self.super_orders_api.place_cover_order(
                security_id=security_id,
                exchange_segment=exchange_segment,
                transaction_type=transaction_type,
                quantity=follower_quantity,
                order_type=order_type,
                price=price,
                stop_loss_value=stop_loss_value,
                trigger_price=trigger_price,
                disclosed_quantity=follower_disclosed_qty
            )
            
            if response and 'orderId' in response:
                return str(response['orderId'])
            return None
            
        except Exception as e:
            logger.error(f"Error placing cover order: {e}")
            return None
    
    def _place_bracket_order(
        self,
        leader_order_data: Dict[str, Any],
        follower_quantity: int,
        follower_disclosed_qty: Optional[int]
    ) -> Optional[str]:
        """Place bracket order using SuperOrderAPI."""
        try:
            security_id = leader_order_data['securityId']
            exchange_segment = leader_order_data['exchangeSegment']
            transaction_type = leader_order_data['transactionType']
            order_type = leader_order_data['orderType']
            price = leader_order_data.get('price', 0)
            stop_loss_value = leader_order_data.get('boStopLossValue')
            profit_value = leader_order_data.get('boProfitValue')
            
            if not stop_loss_value or not profit_value:
                logger.error("Bracket Order missing stop_loss_value or profit_value")
                return None
            
            response = self.super_orders_api.place_bracket_order(
                security_id=security_id,
                exchange_segment=exchange_segment,
                transaction_type=transaction_type,
                quantity=follower_quantity,
                order_type=order_type,
                price=price,
                stop_loss_value=stop_loss_value,
                profit_value=profit_value,
                disclosed_quantity=follower_disclosed_qty
            )
            
            if response and 'orderId' in response:
                return str(response['orderId'])
            return None
            
        except Exception as e:
            logger.error(f"Error placing bracket order: {e}")
            return None
    
    def _save_copy_mapping(
        self,
        leader_order_id: str,
        follower_order_id: str,
        leader_quantity: int,
        follower_quantity: int,
        status: str
    ) -> None:
        """Save copy mapping to database."""
        capital_ratio = self.position_sizer.get_capital_ratio()
        
        mapping = CopyMapping(
            leader_order_id=leader_order_id,
            follower_order_id=follower_order_id,
            leader_quantity=leader_quantity,
            follower_quantity=follower_quantity,
            sizing_strategy=self.system_config.sizing_strategy.value,
            capital_ratio=capital_ratio,
            status=status,
            error_message=None,
            created_at=int(time.time()),
            updated_at=int(time.time())
        )
        
        self.db.save_copy_mapping(mapping)
    
    def _save_failed_mapping(
        self,
        leader_order_id: str,
        leader_quantity: int,
        follower_quantity: int,
        error_message: str
    ) -> None:
        """Save failed copy mapping to database."""
        capital_ratio = self.position_sizer.get_capital_ratio()
        
        mapping = CopyMapping(
            leader_order_id=leader_order_id,
            follower_order_id=None,
            leader_quantity=leader_quantity,
            follower_quantity=follower_quantity,
            sizing_strategy=self.system_config.sizing_strategy.value,
            capital_ratio=capital_ratio,
            status='failed',
            error_message=error_message,
            created_at=int(time.time()),
            updated_at=int(time.time())
        )
        
        self.db.save_copy_mapping(mapping)


def create_order_replicator(
    orders_api,
    super_orders_api,
    position_sizer: PositionSizer,
    db: DatabaseManager
) -> OrderReplicator:
    """
    Factory function to create OrderReplicator.
    
    Args:
        orders_api: OrdersAPI instance
        super_orders_api: SuperOrderAPI instance
        position_sizer: PositionSizer instance
        db: DatabaseManager instance
    
    Returns:
        OrderReplicator instance
    """
    return OrderReplicator(
        orders_api=orders_api,
        super_orders_api=super_orders_api,
        position_sizer=position_sizer,
        db=db
    )

