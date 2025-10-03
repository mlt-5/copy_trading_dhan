"""
DhanHQ v2 Portfolio API Module

Handle portfolio operations: holdings and positions.

API Documentation: https://dhanhq.co/docs/v2/portfolio/
"""

import logging
from typing import Optional, Dict, Any, List
from dhanhq import dhanhq

logger = logging.getLogger(__name__)


class PortfolioAPI:
    """
    DhanHQ v2 Portfolio API wrapper.
    
    Covers:
    - Get Holdings (long-term investments)
    - Get Positions (intraday/derivatives)
    - Convert positions (NRML to MIS, etc.)
    """
    
    def __init__(self, client: dhanhq, account_type: str):
        """
        Initialize Portfolio API.
        
        Args:
            client: Authenticated DhanHQ client
            account_type: 'leader' or 'follower'
        """
        self.client = client
        self.account_type = account_type
        logger.info(f"Portfolio API initialized for {account_type}")
    
    def get_holdings(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get holdings (long-term equity holdings).
        
        Returns:
            List of holding dicts with fields:
            - securityId
            - exchangeSegment
            - tradingSymbol
            - quantity
            - averagePrice
            - currentPrice
            - pnl
            - etc.
        """
        try:
            response = self.client.get_holdings()
            
            if response and isinstance(response, list):
                logger.debug(f"Retrieved {len(response)} holdings", extra={
                    "account_type": self.account_type,
                    "count": len(response)
                })
                return response
            else:
                logger.warning("No holdings found or API error", extra={
                    "account_type": self.account_type
                })
                return []
        
        except Exception as e:
            logger.error("Get holdings error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def get_positions(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get positions (intraday and derivatives).
        
        Returns:
            List of position dicts with fields:
            - securityId
            - exchangeSegment
            - productType (MIS, NRML, CNC)
            - buyQty, sellQty, netQty
            - buyAvg, sellAvg
            - realizedProfit
            - unrealizedProfit
            - etc.
        """
        try:
            response = self.client.get_positions()
            
            if response and isinstance(response, list):
                logger.debug(f"Retrieved {len(response)} positions", extra={
                    "account_type": self.account_type,
                    "count": len(response)
                })
                return response
            else:
                logger.warning("No positions found or API error", extra={
                    "account_type": self.account_type
                })
                return []
        
        except Exception as e:
            logger.error("Get positions error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def convert_position(
        self,
        security_id: str,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        from_product_type: str,
        to_product_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Convert position from one product type to another.
        
        Examples:
        - INTRADAY (MIS) → DELIVERY (CNC)
        - MARGIN → NORMAL
        
        Args:
            security_id: Security ID
            exchange_segment: Exchange segment
            transaction_type: BUY or SELL (original position)
            quantity: Quantity to convert
            from_product_type: Current product type (MIS, NRML, etc.)
            to_product_type: Target product type
        
        Returns:
            Conversion response
        """
        try:
            logger.info(f"Converting position: {from_product_type} → {to_product_type}", extra={
                "account_type": self.account_type,
                "security_id": security_id,
                "quantity": quantity
            })
            
            request = {
                'security_id': security_id,
                'exchange_segment': exchange_segment,
                'transaction_type': transaction_type,
                'quantity': quantity,
                'from_product_type': from_product_type,
                'to_product_type': to_product_type
            }
            
            response = self.client.convert_position(**request)
            
            if response and (response.get('status') == 'success' or 'conversionId' in response):
                logger.info("Position converted successfully", extra={
                    "account_type": self.account_type
                })
                return response
            else:
                logger.error(f"Position conversion failed: {response}")
                return None
        
        except Exception as e:
            logger.error("Position conversion error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None

