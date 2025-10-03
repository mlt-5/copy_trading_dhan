"""
Copy Trading System - Main Entry Point

DhanHQ v2 API-aligned architecture.
Orchestrates all components and manages the copy trading lifecycle.
"""

import logging
import signal
import sys
import time
from typing import Dict, Any

from core import get_config, init_database
from core.position_sizer import initialize_position_sizer
from core.order_replicator import create_order_replicator
from dhan_api import (
    authenticate_accounts,
    OrdersAPI,
    SuperOrderAPI,
    LiveOrderUpdateManager,
    FundsAPI
)
from utils import setup_logging

logger = logging.getLogger(__name__)


class CopyTradingSystem:
    """
    Main copy trading system orchestrator.
    
    Coordinates:
    - Authentication
    - Database
    - Order replication
    - WebSocket monitoring
    """
    
    def __init__(self):
        """Initialize the copy trading system."""
        self.is_running = False
        
        # Components (initialized later)
        self.auth_manager = None
        self.db = None
        self.leader_orders_api = None
        self.follower_orders_api = None
        self.follower_super_orders_api = None
        self.leader_funds_api = None
        self.follower_funds_api = None
        self.position_sizer = None
        self.order_replicator = None
        self.ws_manager = None
        
        # Configuration
        self.leader_config = None
        self.follower_config = None
        self.system_config = None
        
        logger.info("Copy Trading System v2.0 initialized")
    
    def setup(self) -> bool:
        """
        Set up all system components.
        
        Returns:
            True if setup successful, False otherwise
        """
        try:
            logger.info("="*60)
            logger.info("COPY TRADING SYSTEM v2.0 - SETUP")
            logger.info("="*60)
            
            # Load configuration
            logger.info("Loading configuration...")
            self.leader_config, self.follower_config, self.system_config = get_config()
            
            # Check if copy trading is enabled
            if not self.system_config.enable_copy_trading:
                logger.warning("❌ Copy trading is DISABLED in configuration")
                return False
            
            # Initialize database
            logger.info(f"Initializing database: {self.system_config.sqlite_path}")
            self.db = init_database()
            logger.info("✅ Database initialized")
            
            # Authenticate accounts
            logger.info("Authenticating DhanHQ accounts...")
            self.auth_manager = authenticate_accounts(
                leader_client_id=self.leader_config.client_id,
                leader_access_token=self.leader_config.access_token,
                follower_client_id=self.follower_config.client_id,
                follower_access_token=self.follower_config.access_token
            )
            logger.info("✅ Both accounts authenticated")
            
            # Initialize API modules
            logger.info("Initializing DhanHQ API modules...")
            self.leader_orders_api = OrdersAPI(
                self.auth_manager.leader_client,
                'leader'
            )
            self.follower_orders_api = OrdersAPI(
                self.auth_manager.follower_client,
                'follower'
            )
            self.follower_super_orders_api = SuperOrderAPI(
                self.auth_manager.follower_client,
                'follower'
            )
            self.leader_funds_api = FundsAPI(
                self.auth_manager.leader_client,
                'leader'
            )
            self.follower_funds_api = FundsAPI(
                self.auth_manager.follower_client,
                'follower'
            )
            logger.info("✅ API modules initialized")
            
            # Initialize position sizer
            logger.info("Initializing position sizer...")
            self.position_sizer = initialize_position_sizer(
                leader_funds_api=self.leader_funds_api,
                follower_funds_api=self.follower_funds_api
            )
            logger.info("✅ Position sizer initialized")
            
            # Initialize order replicator
            logger.info("Initializing order replicator...")
            self.order_replicator = create_order_replicator(
                orders_api=self.follower_orders_api,
                super_orders_api=self.follower_super_orders_api,
                position_sizer=self.position_sizer,
                db=self.db
            )
            logger.info("✅ Order replicator initialized")
            
            # Initialize WebSocket manager
            logger.info("Initializing WebSocket manager...")
            self.ws_manager = LiveOrderUpdateManager(
                client_id=self.leader_config.client_id,
                access_token=self.leader_config.access_token,
                on_order_update=self._handle_order_update,
                dhan_client=self.auth_manager.leader_client
            )
            logger.info("✅ WebSocket manager initialized")
            
            logger.info("="*60)
            logger.info("SETUP COMPLETE")
            logger.info("="*60)
            return True
            
        except Exception as e:
            logger.error("❌ Setup failed", exc_info=True, extra={"error": str(e)})
            return False
    
    def start(self) -> None:
        """Start the copy trading system."""
        if not self.setup():
            logger.error("Setup failed, cannot start system")
            sys.exit(1)
        
        try:
            # Connect WebSocket
            logger.info("Connecting to WebSocket...")
            self.ws_manager.start()
            
            if not self.ws_manager.is_connected:
                logger.error("❌ Failed to connect WebSocket")
                sys.exit(1)
            
            logger.info("✅ WebSocket connected")
            
            # System is now running
            self.is_running = True
            
            logger.info("="*60)
            logger.info("🚀 COPY TRADING SYSTEM STARTED")
            logger.info("="*60)
            logger.info(f"Environment: {self.system_config.environment.value}")
            logger.info(f"Sizing Strategy: {self.system_config.sizing_strategy.value}")
            logger.info(f"Max Position Size: {self.system_config.max_position_size_pct}%")
            logger.info("Monitoring leader account for orders...")
            logger.info("="*60)
            
            # Main event loop
            self._run_event_loop()
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            self.shutdown()
        except Exception as e:
            logger.error("System error", exc_info=True, extra={"error": str(e)})
            self.shutdown()
            sys.exit(1)
    
    def _run_event_loop(self) -> None:
        """
        Main event loop.
        
        WebSocket callbacks handle order updates.
        This loop performs health checks and maintenance.
        """
        while self.is_running:
            try:
                # Health check
                if not self.ws_manager.is_connected:
                    logger.warning("WebSocket disconnected, monitoring for reconnection")
                    self.ws_manager.monitor_connection()
                
                # Sleep to avoid busy loop
                time.sleep(5)
                
            except Exception as e:
                logger.error("Error in event loop", exc_info=True, extra={"error": str(e)})
                time.sleep(5)
    
    def _handle_order_update(self, order_data: Dict[str, Any]) -> None:
        """
        Handle order update from WebSocket.
        
        Args:
            order_data: Order update from leader account
        """
        try:
            order_id = order_data.get('orderId') or order_data.get('dhanOrderId')
            order_status = order_data.get('orderStatus', '')
            security_id = order_data.get('securityId', '')
            
            logger.info(f"📥 Order update: {order_id} ({order_status})", extra={
                "order_id": order_id,
                "status": order_status,
                "security_id": security_id
            })
            
            # Replicate new orders
            if order_status in ('PENDING', 'TRANSIT', 'OPEN'):
                follower_order_id = self.order_replicator.replicate_order(order_data)
                
                if follower_order_id:
                    logger.info(f"✅ Order replicated", extra={
                        "leader_order_id": order_id,
                        "follower_order_id": follower_order_id
                    })
                    
                    # Update last processed event timestamp
                    self.db.set_config_value('last_leader_event_ts', str(int(time.time())))
                else:
                    logger.warning(f"⚠️ Order replication skipped or failed: {order_id}")
            else:
                logger.debug(f"Ignoring order with status: {order_status}")
            
        except Exception as e:
            logger.error("Error handling order update", exc_info=True, extra={
                "error": str(e),
                "order_data": order_data
            })
    
    def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("Initiating graceful shutdown...")
        self.is_running = False
        
        # Disconnect WebSocket
        if self.ws_manager:
            logger.info("Disconnecting WebSocket...")
            self.ws_manager.disconnect()
        
        # Close database
        if self.db:
            logger.info("Closing database...")
            self.db.close()
        
        logger.info("="*60)
        logger.info("✅ SYSTEM SHUTDOWN COMPLETE")
        logger.info("="*60)


def signal_handler(signum, frame):
    """Handle termination signals."""
    logger.info(f"Received signal {signum}")
    sys.exit(0)


def main():
    """Main entry point."""
    # Get configuration for log level
    _, _, system_config = get_config()
    
    # Setup logging
    setup_logging(log_level=system_config.log_level)
    
    logger.info("="*60)
    logger.info("COPY TRADING SYSTEM v2.0")
    logger.info("DhanHQ API-Aligned Architecture")
    logger.info("="*60)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start system
    system = CopyTradingSystem()
    system.start()


if __name__ == "__main__":
    main()

