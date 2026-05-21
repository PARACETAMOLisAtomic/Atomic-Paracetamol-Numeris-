import logging
from typing import Dict, Any, List
from kiteconnect import KiteConnect
import kiteconnect.exceptions as kite_exc
from backend.services.broker_base import BrokerBase
from backend.core.config import settings

logger = logging.getLogger(__name__)

class ZerodhaBroker(BrokerBase):
    def __init__(self):
        super().__init__()
        self.api_key = settings.ZERODHA_API_KEY
        self.api_secret = settings.ZERODHA_API_SECRET
        self.kite = KiteConnect(api_key=self.api_key)
        self.access_token = None

    def generate_login_url(self) -> str:
        return self.kite.login_url()

    async def complete_login(self, request_token: str) -> bool:
        try:
            data = self.kite.generate_session(request_token, api_secret=self.api_secret)
            self.access_token = data["access_token"]
            self.kite.set_access_token(self.access_token)
            return True
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Zerodha login failed: {e}")
            return False

    async def get_profile(self) -> Dict[str, Any]:
        try:
            return self.kite.profile()
        except kite_exc.TokenException:
            self.last_error = "Session expired"
            return {}
        except Exception as e:
            self.last_error = str(e)
            return {}

    async def get_funds(self) -> Dict[str, Any]:
        try:
            margins = self.kite.margins()
            return margins.get("equity", {})
        except Exception as e:
            self.last_error = str(e)
            return {}

    async def get_positions(self) -> List[Dict[str, Any]]:
        try:
            return self.kite.positions().get("net", [])
        except Exception as e:
            self.last_error = str(e)
            return []

    async def get_holdings(self) -> List[Dict[str, Any]]:
        try:
            holdings = self.kite.holdings()
            for h in holdings:
                h['symbol'] = h.get('tradingsymbol', '').replace('-EQ', '')
            return holdings
        except Exception as e:
            self.last_error = str(e)
            return []

    async def place_order(self, symbol: str, qty: int, side: str, order_type: str, price: float = 0.0) -> Dict[str, Any]:
        try:
            transaction_type = self.kite.TRANSACTION_TYPE_BUY if side.upper() == 'BUY' else self.kite.TRANSACTION_TYPE_SELL
            order_t = self.kite.ORDER_TYPE_MARKET if order_type.upper() == 'MARKET' else self.kite.ORDER_TYPE_LIMIT
            order_id = self.kite.place_order(
                tradingsymbol=f"{symbol}-EQ",
                exchange=self.kite.EXCHANGE_NSE,
                transaction_type=transaction_type,
                quantity=qty,
                order_type=order_t,
                product=self.kite.PRODUCT_CNC,
                price=price
            )
            return {"order_id": order_id}
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Zerodha order failed: {e}")
            return {}

    async def cancel_order(self, order_id: str) -> bool:
        try:
            self.kite.cancel_order(self.kite.VARIETY_REGULAR, order_id)
            return True
        except Exception as e:
            self.last_error = str(e)
            return False

    async def test_connection(self) -> Dict[str, Any]:
        try:
            if not self.access_token:
                return {"connected": False, "error": "No access token"}
            self.kite.profile()
            return {"connected": True, "error": None}
        except Exception as e:
            self.last_error = str(e)
            return {"connected": False, "error": str(e)}

    def is_session_valid(self) -> bool:
        if not self.access_token:
            return False
        try:
            self.kite.profile()
            return True
        except:
            return False
