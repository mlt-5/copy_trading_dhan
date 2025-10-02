"""
Copy Trading System - Main Orchestrator

Entry point for the options copy trading application.
Coordinates all components and manages the event loop.
"""

import logging
import signal
import sys
import time
from typing import Dict, Any

from .config import get_config
from .auth import authenticate_accounts
from .database import init_database, get_db
from .position_sizing import initialize_position_sizer, get_position_sizer
from .orders import initialize_order_manager, get_order_manager
from .websocket import initialize_ws_manager, get_ws_manager
from .utils.logger import setup_logging

logger = logging.getLogger(__name__)


class CopyTradingOrchestrator:
    """
    Main orchestrator for copy trading system.
    
    State Machine:
    - INITIALIZING: System startup
    - AUTHENTICATING: Account authentication
    - CONNECTING: WebSocket connection
    - READY: Monitoring and processing
    - SHUTTING_DOWN: Graceful shutdown
    - STOPPED: System stopped
    """
    
    def __init__(self):
        """Initialize orchestrator."""
        self.state = "INITIALIZING"
        self.is_running = False
        
        # Components (initialized later)
        self.auth_manager = None
        self.db = None
        self.position_sizer = None
        self.order_manager = None
        self.ws_manager = None
        
        # Config
        self.leader_config = None
        self.follower_config = None
        self.system_config = None
        
        logger.info("Copy Trading Orchestrator initialized")
    
    def setup(self) -> bool:
        """
        Set up all components.
        
        Returns:
            True if setup successful, False otherwise
        """
        try:
            logger.info("Starting system setup...")
            
            # Load configuration
            logger.info("Loading configuration...")
            self.leader_config, self.follower_config, self.system_config = get_config()
            
            # Check if copy trading is enabled
            if not self.system_config.enable_copy_trading:
                logger.warning("Copy trading is DISABLED in configuration")
                return False
            
            # Initialize database
            logger.info("Initializing database...")
            self.state = "INITIALIZING"
            self.db = init_database()
            logger.info(f"Database initialized: {self.system_config.sqlite_path}")
            
            # Authenticate accounts
            logger.info("Authenticating accounts...")
            self.state = "AUTHENTICATING"
            self.auth_manager = authenticate_accounts()
            logger.info("Both accounts authenticated successfully")
            
            # Initialize position sizer
            logger.info("Initializing position sizer...")
            self.position_sizer = initialize_position_sizer(
                leader_client=self.auth_manager.leader_client,
                follower_client=self.auth_manager.follower_client
            )
            logger.info("Position sizer initialized")
            
            # Initialize order manager
            logger.info("Initializing order manager...")
            self.order_manager = initialize_order_manager(
                follower_client=self.auth_manager.follower_client
            )
            logger.info("Order manager initialized")
            
            # Initialize WebSocket manager
            logger.info("Initializing WebSocket manager...")
            self.ws_manager = initialize_ws_manager(
                on_order_update=self._handle_order_update,
                leader_client=self.auth_manager.leader_client  # ✅ ADDED: For fetching missed orders
            )
            logger.info("WebSocket manager initialized")
            
            logger.info("System setup completed successfully")
            return True
            
        except Exception as e:
            logger.error("System setup failed", exc_info=True, extra={"error": str(e)})
            return False
    
    def start(self) -> None:
        """Start the copy trading system."""
        if not self.setup():
            logger.error("Setup failed, cannot start system")
            sys.exit(1)
        
        try:
            # Connect WebSocket
            logger.info("Connecting to WebSocket...")
            self.state = "CONNECTING"
            self.ws_manager.start()
            
            if not self.ws_manager.is_connected:
                logger.error("Failed to connect WebSocket")
                sys.exit(1)
            
            logger.info("WebSocket connected successfully")
            
            # Enter ready state
            self.state = "READY"
            self.is_running = True
            
            logger.info("="*60)
            logger.info("COPY TRADING SYSTEM STARTED")
            logger.info(f"Environment: {self.system_config.environment.value}")
            logger.info(f"Sizing Strategy: {self.system_config.sizing_strategy.value}")
            logger.info(f"Max Position Size: {self.system_config.max_position_size_pct}%")
            logger.info("Monitoring leader account for new orders...")
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
        
        The actual order updates are handled via WebSocket callbacks.
        This loop performs periodic tasks and health checks.
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
        
        This is called by the WebSocket manager when a new order event is received.
        
        Args:
            order_data: Order update data from WebSocket
        """
        try:
            order_id = order_data.get('orderId') or order_data.get('dhanOrderId')
            order_status = order_data.get('orderStatus', '')
            
            logger.info(f"Processing order update: {order_id} ({order_status})", extra={
                "order_id": order_id,
                "status": order_status,
                "security_id": order_data.get('securityId')
            })
            
            # ✅ FIXED: Handle all order statuses
            
            # New orders - replicate
            if order_status in ('PENDING', 'TRANSIT', 'OPEN'):
                follower_order_id = self.order_manager.replicate_order(order_data)
                
                if follower_order_id:
                    logger.info(f"Order replicated successfully", extra={
                        "leader_order_id": order_id,
                        "follower_order_id": follower_order_id
                    })
                    
                    # ✅ ADDED: Update last processed event timestamp
                    self.db.set_config_value('last_leader_event_ts', str(int(time.time())))
                else:
                    logger.warning(f"Order replication skipped or failed: {order_id}")
            
            # ✅ ADDED: Modifications - replicate changes
            elif order_status == 'MODIFIED':
                success = self.order_manager.modify_order(order_data)
                if success:
                    logger.info(f"Order modified successfully: {order_id}")
                else:
                    logger.warning(f"Order modification failed or not applicable: {order_id}")
            
            # ✅ ADDED: Cancellations - cancel follower order
            elif order_status == 'CANCELLED':
                success = self.order_manager.cancel_order(order_data)
                if success:
                    logger.info(f"Order cancelled successfully: {order_id}")
                else:
                    logger.warning(f"Order cancellation failed or not applicable: {order_id}")
            
            # ✅ ADDED: Executions - track fills
            elif order_status in ('TRADED', 'EXECUTED', 'PARTIALLY_FILLED'):
                self.order_manager.handle_execution(order_data)
            
            # ✅ ADDED: Rejections - log for analysis
            elif order_status == 'REJECTED':
                logger.warning(f"Order rejected: {order_id}", extra={
                    "rejection_reason": order_data.get('rejectionReason', 'Unknown')
                })
                self.order_manager.handle_execution(order_data)  # Still track it
            
            else:
                logger.debug(f"Ignoring order with status: {order_status}")
            
        except Exception as e:
            logger.error("Error handling order update", exc_info=True, extra={
                "error": str(e),
                "order_data": order_data
            })
    
    def shutdown(self) -> None:
        """Graceful shutdown."""
        if self.state == "SHUTTING_DOWN" or self.state == "STOPPED":
            return
        
        logger.info("Initiating graceful shutdown...")
        self.state = "SHUTTING_DOWN"
        self.is_running = False
        
        # Disconnect WebSocket
        if self.ws_manager:
            logger.info("Disconnecting WebSocket...")
            self.ws_manager.disconnect()
        
        # Close database
        if self.db:
            logger.info("Closing database connection...")
            self.db.close()
        
        self.state = "STOPPED"
        logger.info("System shutdown complete")


def signal_handler(signum, frame):
    """Handle termination signals."""
    logger.info(f"Received signal {signum}")
    sys.exit(0)


def main():
    """Main entry point."""
    # Parse command-line arguments (if any)
    # For simplicity, using environment variables only
    
    # Load config to get log level
    _, _, system_config = get_config()
    
    # Setup logging
    setup_logging(log_level=system_config.log_level)
    
    logger.info("Starting Copy Trading System v1.0.0")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start orchestrator
    orchestrator = CopyTradingOrchestrator()
    orchestrator.start()


if __name__ == "__main__":
    main()


