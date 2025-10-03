"""
DhanHQ v2 Statement API Module

Handle trade statements, ledger, and transaction history.

API Documentation: https://dhanhq.co/docs/v2/statements/
"""

import logging
from typing import Optional, Dict, Any, List
from dhanhq import dhanhq

logger = logging.getLogger(__name__)


class StatementAPI:
    """
    DhanHQ v2 Statement API wrapper.
    
    Covers:
    - Trade statements
    - Ledger (fund movements)
    - Transaction history
    """
    
    def __init__(self, client: dhanhq, account_type: str):
        """
        Initialize Statement API.
        
        Args:
            client: Authenticated DhanHQ client
            account_type: 'leader' or 'follower'
        """
        self.client = client
        self.account_type = account_type
        logger.info(f"Statement API initialized for {account_type}")
    
    def get_trade_statement(
        self,
        from_date: str,
        to_date: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get trade statement for a date range.
        
        Args:
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
        
        Returns:
            List of trade dicts
        """
        try:
            logger.info(f"Fetching trade statement: {from_date} to {to_date}", extra={
                "account_type": self.account_type
            })
            
            response = self.client.get_trade_statement(from_date, to_date)
            
            if response and isinstance(response, list):
                logger.debug(f"Retrieved {len(response)} trades", extra={
                    "account_type": self.account_type
                })
                return response
            else:
                return []
        
        except Exception as e:
            logger.error("Get trade statement error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def get_ledger(
        self,
        from_date: str,
        to_date: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get ledger (fund movements) for a date range.
        
        Args:
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
        
        Returns:
            List of ledger entry dicts
        """
        try:
            logger.info(f"Fetching ledger: {from_date} to {to_date}", extra={
                "account_type": self.account_type
            })
            
            response = self.client.get_ledger(from_date, to_date)
            
            if response and isinstance(response, list):
                logger.debug(f"Retrieved {len(response)} ledger entries", extra={
                    "account_type": self.account_type
                })
                return response
            else:
                return []
        
        except Exception as e:
            logger.error("Get ledger error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def get_transaction_history(
        self,
        from_date: str,
        to_date: str,
        page: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Get transaction history with pagination.
        
        Args:
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            page: Page number
        
        Returns:
            Transaction history dict with transactions list and pagination info
        """
        try:
            logger.debug(f"Fetching transaction history page {page}", extra={
                "account_type": self.account_type
            })
            
            response = self.client.get_transaction_history(from_date, to_date, page)
            
            return response if response else None
        
        except Exception as e:
            logger.error("Get transaction history error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None
    
    def download_contract_note(self, trade_date: str) -> Optional[str]:
        """
        Download contract note for a trading day.
        
        Args:
            trade_date: Trade date (YYYY-MM-DD)
        
        Returns:
            URL or file path to contract note PDF
        """
        try:
            logger.info(f"Downloading contract note for {trade_date}", extra={
                "account_type": self.account_type
            })
            
            response = self.client.download_contract_note(trade_date)
            
            if response:
                url = response.get('url') or response.get('file_path')
                logger.info(f"Contract note available: {url}")
                return url
            else:
                logger.error("Contract note download failed")
                return None
        
        except Exception as e:
            logger.error("Contract note download error", exc_info=True, extra={
                "account_type": self.account_type,
                "error": str(e)
            })
            return None


# Note: Statement API methods should be verified from official documentation.
# Method names and parameters may differ - update after consulting docs.

