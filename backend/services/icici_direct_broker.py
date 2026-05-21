"""
Session token instructions for ICICI Direct:
1. Generate session token from ICICI Direct developer portal.
2. Store the session token in your database.
"""

import logging
from typing import Dict, Any, List
from backend.services.broker_base import BrokerBase
from backend.core.config import settings

logger = logging.getLogger(__name__)

try:
    from breeze_connect import BreezeConnect
except ImportError:
    BreezeConnect = None

class ICICIDirectBroker(BrokerBase):
    def __init__(self):
        super().__init__()
        self.api_key = settings.ICICI_DIRECT_KEY
        self.api_secret = settings.ICICI_DIRECT_SECRET
        if BreezeConnect:
            self.breeze = BreezeConnect(api_key=self.api_key)
        else:
            self.breeze = None
        self.session_token = None

    def generate_login_url(self) -> str:
        return f"https://api.icicidirect.com/apiuser/login?api_key={self.api_key}"

    async def complete_login(self, request_token: str) -> bool:
        try:
            if not self.breeze:
                raise Exception("BreezeConnect not installed")
            self.breeze.generate_session(api_secret=self.api_secret, session_token=request_token)
            self.session_token = request_token
            return True
        except Exception as e:
            self.last_error = str(e)
            return False

    async def get_profile(self) -> Dict[str, Any]:
        try:
            return self.breeze.get_customer_details(api_session=self.session_token)
        except Exception as e:
            self.last_error = str(e)
            return {}

    async def get_funds(self) -> Dict[str, Any]:
        try:
            return self.breeze.get_funds()
        except Exception as e:
            self.last_error = str(e)
            return {}

    async def get_positions(self) -> List[Dict[str, Any]]:
        try:
            return self.breeze.get_portfolio_positions().get('Success', [])
        except Exception as e:
            self.last_error = str(e)
            return []

    async def get_holdings(self) -> List[Dict[str, Any]]:
        try:
            return self.breeze.get_portfolio_holdings().get('Success', [])
        except Exception as e:
            self.last_error = str(e)
            return []

    async def place_order(self, symbol: str, qty: int, side: str, order_type: str, price: float = 0.0) -> Dict[str, Any]:
        try:
            resp = self.breeze.place_order(stock_code=symbol,
                                           exchange_code="NSE",
                                           product="cash",
                                           action=side.lower(),
                                           order_type=order_type.lower(),
                                           stoploss="",
                                           quantity=str(qty),
                                           price=str(price) if price else "",
                                           validity="day")
            return {"order_id": resp.get('Success', {}).get('order_id', '')}
        except Exception as e:
            self.last_error = str(e)
            return {}

    async def cancel_order(self, order_id: str) -> bool:
        try:
            self.breeze.cancel_order(exchange_code="NSE", order_id=order_id)
            return True
        except Exception as e:
            self.last_error = str(e)
            return False

    async def test_connection(self) -> Dict[str, Any]:
        try:
            if not self.session_token:
                return {"connected": False, "error": "No session"}
            self.breeze.get_funds()
            return {"connected": True, "error": None}
        except Exception as e:
            self.last_error = str(e)
            return {"connected": False, "error": str(e)}

    def is_session_valid(self) -> bool:
        return self.session_token is not None
