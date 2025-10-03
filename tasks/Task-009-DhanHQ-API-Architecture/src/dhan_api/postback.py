"""
DhanHQ v2 Postback API Module

Handle webhook postback configuration and processing for order updates.

API Documentation: https://dhanhq.co/docs/v2/postback/
"""

import logging
import hmac
import hashlib
from typing import Optional, Dict, Any, Callable
from dhanhq import dhanhq

logger = logging.getLogger(__name__)


class PostbackHandler:
    """
    DhanHQ v2 Postback (Webhook) handler.
    
    Postback/Webhook:
    - Receive order updates via HTTP POST
    - More reliable than WebSocket for critical updates
    - Requires HTTPS endpoint
    - Signature verification for security
    """
    
    def __init__(self, client: dhanhq, account_type: str, webhook_secret: Optional[str] = None):
        """
        Initialize Postback handler.
        
        Args:
            client: Authenticated DhanHQ client
            account_type: 'leader' or 'follower'
            webhook_secret: Secret key for signature verification
        """
        self.client = client
        self.account_type = account_type
        self.webhook_secret = webhook_secret
        logger.info(f"Postback handler initialized for {account_type}")
    
    def configure_postback_url(self, webhook_url: str) -> Optional[Dict[str, Any]]:
        """
        Configure postback URL for order updates.
        
        Args:
            webhook_url: HTTPS URL to receive postback notifications
        
        Returns:
            Configuration response
        """
        try:
            logger.info(f"Configuring postback URL: {webhook_url}", extra={
                "account_type": self.account_type
            })
            
            response = self.client.configure_postback_url(webhook_url)
            
            if response and response.get('status') == 'success':
                logger.info("Postback URL configured successfully")
                return response
            else:
                logger.error(f"Postback configuration failed: {response}")
                return None
        
        except Exception as e:
            logger.error("Postback configuration error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def verify_signature(self, payload: str, signature: str) -> bool:
        """
        Verify webhook signature for security.
        
        Args:
            payload: Raw webhook payload (string)
            signature: Signature from X-Dhan-Signature header
        
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.webhook_secret:
            logger.warning("No webhook secret configured, skipping signature verification")
            return True
        
        try:
            # Calculate expected signature
            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures (constant-time comparison)
            is_valid = hmac.compare_digest(signature, expected_signature)
            
            if not is_valid:
                logger.error("Invalid webhook signature", extra={
                    "account_type": self.account_type
                })
            
            return is_valid
        
        except Exception as e:
            logger.error("Signature verification error", exc_info=True, extra={
                "error": str(e)
            })
            return False
    
    def process_postback(self, payload: Dict[str, Any], callback: Callable) -> None:
        """
        Process incoming postback notification.
        
        Args:
            payload: Webhook payload dict
            callback: Callback function to handle the order update
        """
        try:
            order_id = payload.get('orderId') or payload.get('dhanOrderId')
            order_status = payload.get('orderStatus', 'UNKNOWN')
            
            logger.info(f"Processing postback for order: {order_id}", extra={
                "account_type": self.account_type,
                "order_id": order_id,
                "status": order_status
            })
            
            # Call the callback function with the payload
            callback(payload)
            
            logger.debug("Postback processed successfully")
        
        except Exception as e:
            logger.error("Postback processing error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e),
                "payload": payload
            })
    
    def disable_postback(self) -> Optional[Dict[str, Any]]:
        """
        Disable postback notifications.
        
        Returns:
            Response confirming postback disabled
        """
        try:
            logger.info("Disabling postback", extra={
                "account_type": self.account_type
            })
            
            response = self.client.disable_postback()
            
            if response:
                logger.info("Postback disabled successfully")
                return response
            else:
                logger.error("Failed to disable postback")
                return None
        
        except Exception as e:
            logger.error("Postback disable error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None


# Flask/FastAPI endpoint example (for reference):
"""
from flask import Flask, request, jsonify

app = Flask(__name__)
postback_handler = PostbackHandler(client, 'leader', webhook_secret='your_secret')

@app.route('/webhook/dhan/orders', methods=['POST'])
def dhan_webhook():
    # Get signature from headers
    signature = request.headers.get('X-Dhan-Signature', '')
    
    # Get raw payload
    payload_str = request.get_data(as_text=True)
    
    # Verify signature
    if not postback_handler.verify_signature(payload_str, signature):
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Parse JSON
    payload = request.get_json()
    
    # Process postback
    postback_handler.process_postback(payload, your_order_update_handler)
    
    return jsonify({'status': 'received'}), 200
"""

